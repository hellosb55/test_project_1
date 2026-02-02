"""Main agent orchestration"""

import time
import signal
import threading
import psutil
import os
from typing import List, Dict, Any, Optional

from src.config.settings import load_config
from src.utils.logger import setup_logger, get_logger
from src.utils.helpers import get_hostname
from src.collectors.base import BaseCollector
from src.collectors.cpu_collector import CPUCollector
from src.collectors.memory_collector import MemoryCollector
from src.collectors.disk_collector import DiskCollector
from src.collectors.network_collector import NetworkCollector
from src.collectors.process_collector import ProcessCollector
from src.exporters.prometheus_exporter import PrometheusExporter


class Agent:
    """Main agent class for orchestrating metric collection"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize agent

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
        self.running = False
        self.collectors: List[BaseCollector] = []
        self.exporter = None
        self.collector_threads = []
        self.self_monitor_thread = None

        # Alerting system
        self.alert_manager = None
        self.alert_evaluator = None
        self.alert_evaluator_thread = None

        # Setup hostname
        if config['agent']['hostname'] == 'auto':
            self.hostname = get_hostname()
        else:
            self.hostname = config['agent']['hostname']

        self.logger.info(f"Initializing agent for host: {self.hostname}")

        # Initialize collectors
        self._init_collectors()

        # Initialize Prometheus exporter
        self.exporter = PrometheusExporter(config, self.collectors)

        # Initialize alerting system (if enabled)
        if config.get('alerting', {}).get('enabled', False):
            self._init_alerting()

        # Setup signal handlers
        self._setup_signal_handlers()

    def _init_collectors(self):
        """Initialize all enabled collectors"""
        collector_classes = {
            'cpu': CPUCollector,
            'memory': MemoryCollector,
            'disk': DiskCollector,
            'network': NetworkCollector,
            'process': ProcessCollector,
        }

        for collector_name, collector_class in collector_classes.items():
            collector_config = self.config['collectors'].get(collector_name, {})

            if collector_config.get('enabled', False):
                try:
                    collector = collector_class(collector_config)
                    self.collectors.append(collector)
                    self.logger.info(f"Initialized {collector_name} collector")
                except Exception as e:
                    self.logger.error(f"Failed to initialize {collector_name} collector: {e}")

        if not self.collectors:
            raise ValueError("No collectors enabled! Check your configuration.")

    def _init_alerting(self):
        """Initialize alerting system"""
        try:
            from src.alerts.alert_manager import AlertManager
            from src.alerts.alert_evaluator import AlertEvaluator
            from src.alerts.alert_rule import load_alert_rules
            from src.alerts.storage.sqlite_storage import SQLiteStorage

            self.logger.info("Initializing alerting system...")

            # Initialize storage
            storage_config = self.config['alerting']['storage']
            storage = SQLiteStorage(storage_config)

            # Initialize alert manager
            self.alert_manager = AlertManager(
                self.config['alerting'],
                storage
            )

            # Load alert rules
            rules_file = self.config['alerting'].get('alert_rules_file')
            if rules_file:
                rules = load_alert_rules(rules_file)
            else:
                rules = []
                self.logger.warning("No alert rules file specified")

            # Initialize alert evaluator
            self.alert_evaluator = AlertEvaluator(
                rules,
                self.exporter.registry,
                self.alert_manager
            )

            self.logger.info(f"Alerting system initialized with {len(rules)} rules")

        except Exception as e:
            self.logger.error(f"Failed to initialize alerting system: {e}", exc_info=True)
            raise

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self):
        """Start the agent"""
        self.logger.info("Starting agent...")
        self.running = True

        try:
            # Start Prometheus HTTP server
            self.exporter.start()
            self.exporter.agent_info.labels(
                version='1.0.0',
                hostname=self.hostname
            ).set(1)

            # Start collector threads
            for collector in self.collectors:
                thread = threading.Thread(
                    target=self._run_collector_loop,
                    args=(collector,),
                    daemon=True,
                    name=f"collector-{collector.get_name()}"
                )
                thread.start()
                self.collector_threads.append(thread)
                self.logger.info(f"Started {collector.get_name()} collector thread")

            # Start self-monitoring thread
            self.self_monitor_thread = threading.Thread(
                target=self._self_monitor_loop,
                daemon=True,
                name="self-monitor"
            )
            self.self_monitor_thread.start()
            self.logger.info("Started self-monitoring thread")

            # Start alert evaluator thread (if enabled)
            if self.alert_evaluator:
                self.alert_evaluator_thread = threading.Thread(
                    target=self._run_alert_evaluator_loop,
                    daemon=True,
                    name="alert-evaluator"
                )
                self.alert_evaluator_thread.start()
                self.logger.info("Started alert evaluator thread")

            self.logger.info("Agent started successfully")
            self.logger.info(f"Prometheus metrics available at http://{self.config['prometheus']['host']}:{self.config['prometheus']['port']}/metrics")

            # Keep main thread alive
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            self.stop()
        except Exception as e:
            self.logger.error(f"Agent error: {e}", exc_info=True)
            self.stop()
            raise

    def stop(self):
        """Stop the agent"""
        if not self.running:
            return

        self.logger.info("Stopping agent...")
        self.running = False

        # Wait for collector threads to finish
        for thread in self.collector_threads:
            thread.join(timeout=5)

        # Wait for self-monitor thread
        if self.self_monitor_thread:
            self.self_monitor_thread.join(timeout=2)

        # Wait for alert evaluator thread
        if self.alert_evaluator_thread:
            self.alert_evaluator_thread.join(timeout=2)

        # Cleanup alert manager
        if self.alert_manager:
            self.alert_manager.shutdown()

        # Stop Prometheus exporter
        if self.exporter:
            self.exporter.stop()

        self.logger.info("Agent stopped")

    def _run_collector_loop(self, collector: BaseCollector):
        """
        Run collector loop

        Args:
            collector: Collector to run
        """
        collector_name = collector.get_name()
        interval = collector.get_interval()

        self.logger.debug(f"Starting collection loop for {collector_name} (interval: {interval}s)")

        while self.running:
            try:
                # Run collection
                success = collector.run_collection()

                # Update agent metrics
                self.exporter.update_agent_metrics([collector])

                # Check if collector is unhealthy
                if not collector.is_healthy():
                    self.logger.warning(
                        f"{collector_name} collector is unhealthy "
                        f"(failed {collector.error_count} consecutive times)"
                    )

                # Sleep until next collection
                time.sleep(interval)

            except Exception as e:
                self.logger.error(f"Error in {collector_name} collector loop: {e}", exc_info=True)
                time.sleep(interval)

    def _self_monitor_loop(self):
        """Monitor agent's own resource usage"""
        check_interval = self.config['resource_limits']['check_interval']
        max_cpu = self.config['resource_limits']['max_cpu_percent']
        max_memory_mb = self.config['resource_limits']['max_memory_mb']
        action = self.config['resource_limits']['action_on_exceed']

        # Get agent process
        agent_process = psutil.Process(os.getpid())

        while self.running:
            try:
                # Measure CPU usage (over 1 second)
                cpu_percent = agent_process.cpu_percent(interval=1.0)

                # Measure memory usage
                memory_info = agent_process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                self.logger.debug(f"Agent resource usage: CPU={cpu_percent:.2f}%, Memory={memory_mb:.2f}MB")

                # Check limits
                if cpu_percent > max_cpu:
                    self.logger.warning(
                        f"Agent CPU usage ({cpu_percent:.2f}%) exceeds limit ({max_cpu}%)"
                    )
                    if action == 'stop':
                        self.logger.error("Stopping agent due to CPU limit exceeded")
                        self.stop()

                if memory_mb > max_memory_mb:
                    self.logger.warning(
                        f"Agent memory usage ({memory_mb:.2f}MB) exceeds limit ({max_memory_mb}MB)"
                    )
                    if action == 'stop':
                        self.logger.error("Stopping agent due to memory limit exceeded")
                        self.stop()

                # Sleep until next check
                time.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Error in self-monitoring: {e}")
                time.sleep(check_interval)

    def _run_alert_evaluator_loop(self):
        """Run alert evaluator loop"""
        interval = self.config['alerting']['evaluation_interval']

        self.logger.debug(f"Starting alert evaluator loop (interval: {interval}s)")

        while self.running:
            try:
                # Evaluate all rules
                self.alert_evaluator.evaluate_all_rules()

                # Cleanup old alerts (every 100 evaluations)
                if hasattr(self, '_alert_cleanup_counter'):
                    self._alert_cleanup_counter += 1
                else:
                    self._alert_cleanup_counter = 0

                if self._alert_cleanup_counter >= 100:
                    self.alert_manager.cleanup_old_alerts()
                    self._alert_cleanup_counter = 0

                # Sleep until next evaluation
                time.sleep(interval)

            except Exception as e:
                self.logger.error(f"Error in alert evaluator loop: {e}", exc_info=True)
                time.sleep(interval)
