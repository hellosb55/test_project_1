"""Prometheus HTTP exporter"""

from prometheus_client import start_http_server, REGISTRY, Gauge, Counter, generate_latest
from prometheus_client.core import CollectorRegistry
import threading
from src.utils.logger import get_logger


class PrometheusExporter:
    """Prometheus HTTP server for exposing metrics"""

    def __init__(self, config, collectors):
        """
        Initialize Prometheus exporter

        Args:
            config: Configuration dictionary
            collectors: List of metric collectors
        """
        self.config = config
        self.collectors = collectors
        self.logger = get_logger(self.__class__.__name__)

        self.host = config.get('prometheus', {}).get('host', '0.0.0.0')
        self.port = config.get('prometheus', {}).get('port', 9100)

        self.registry = CollectorRegistry()
        self.server_thread = None
        self.running = False

        # Register agent self-monitoring metrics
        self._setup_agent_metrics()

        # Register all collector metrics
        self._register_collectors()

    def _setup_agent_metrics(self):
        """Setup agent self-monitoring metrics"""
        self.agent_info = Gauge(
            'agent_info',
            'Agent information',
            ['version', 'hostname'],
            registry=self.registry
        )

        self.agent_collector_last_success = Gauge(
            'agent_collector_last_success_timestamp',
            'Last successful collection timestamp',
            ['collector'],
            registry=self.registry
        )

        self.agent_collector_errors = Counter(
            'agent_collector_errors_total',
            'Total number of collection errors',
            ['collector'],
            registry=self.registry
        )

        self.agent_collector_duration = Gauge(
            'agent_collector_duration_seconds',
            'Collection duration in seconds',
            ['collector'],
            registry=self.registry
        )

        self.agent_collector_status = Gauge(
            'agent_collector_status',
            'Collector status (1=healthy, 0=unhealthy)',
            ['collector'],
            registry=self.registry
        )

    def _register_collectors(self):
        """Register metrics for all collectors"""
        for collector in self.collectors:
            try:
                collector.register_metrics(self.registry)
                self.logger.info(f"Registered metrics for {collector.get_name()}")
            except Exception as e:
                self.logger.error(f"Failed to register metrics for {collector.get_name()}: {e}")

    def start(self):
        """Start HTTP server"""
        try:
            self.logger.info(f"Starting Prometheus HTTP server on {self.host}:{self.port}")
            start_http_server(self.port, addr=self.host, registry=self.registry)
            self.running = True
            self.logger.info(f"Prometheus HTTP server started successfully")
            self.logger.info(f"Metrics available at http://{self.host}:{self.port}/metrics")
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus HTTP server: {e}")
            raise

    def stop(self):
        """Stop HTTP server"""
        self.running = False
        self.logger.info("Prometheus HTTP server stopped")

    def update_agent_metrics(self, collectors):
        """
        Update agent self-monitoring metrics

        Args:
            collectors: List of collectors to update metrics for
        """
        for collector in collectors:
            collector_name = collector.get_name()

            # Update last success timestamp
            if collector.last_success:
                self.agent_collector_last_success.labels(
                    collector=collector_name
                ).set(collector.last_success)

            # Update collection duration
            self.agent_collector_duration.labels(
                collector=collector_name
            ).set(collector.last_collection_duration)

            # Update collector status
            status = 1 if collector.is_healthy() else 0
            self.agent_collector_status.labels(
                collector=collector_name
            ).set(status)

            # Update error count (if there were new errors)
            if collector.error_count > 0:
                self.agent_collector_errors.labels(
                    collector=collector_name
                ).inc()
