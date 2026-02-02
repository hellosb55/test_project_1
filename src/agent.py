"""Main agent orchestration"""

import time
import signal
import threading
import psutil
import os
from typing import List, Dict, Any

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
