"""CPU metrics collector"""

import psutil
import platform
from prometheus_client import Gauge
from src.collectors.base import BaseCollector


class CPUCollector(BaseCollector):
    """Collector for CPU metrics"""

    def register_metrics(self, registry):
        """Register Prometheus metrics"""
        # Overall CPU usage
        self.cpu_usage_percent = Gauge(
            'cpu_usage_percent',
            'Overall CPU usage percentage',
            registry=registry
        )

        # Per-core CPU usage
        self.cpu_usage_per_core = Gauge(
            'cpu_usage_percent_per_core',
            'CPU usage percentage per core',
            ['core'],
            registry=registry
        )

        # Load averages (Unix-like systems only)
        self.cpu_load_average = Gauge(
            'cpu_load_average',
            'CPU load average',
            ['period'],
            registry=registry
        )

        # CPU times
        self.cpu_time_seconds = Gauge(
            'cpu_time_seconds',
            'CPU time in seconds by mode',
            ['mode'],
            registry=registry
        )

    def collect(self):
        """Collect CPU metrics"""
        # Overall CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.cpu_usage_percent.set(cpu_percent)

        # Per-core usage (if enabled)
        if self.config.get('per_cpu', True):
            per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            for i, percent in enumerate(per_cpu):
                self.cpu_usage_per_core.labels(core=str(i)).set(percent)

        # Load averages (Unix-like systems only)
        if hasattr(psutil, 'getloadavg'):
            try:
                load1, load5, load15 = psutil.getloadavg()
                self.cpu_load_average.labels(period='1m').set(load1)
                self.cpu_load_average.labels(period='5m').set(load5)
                self.cpu_load_average.labels(period='15m').set(load15)
            except (AttributeError, OSError):
                self.logger.debug("Load average not available on this platform")

        # CPU times breakdown
        cpu_times = psutil.cpu_times()
        if hasattr(cpu_times, 'user'):
            self.cpu_time_seconds.labels(mode='user').set(cpu_times.user)
        if hasattr(cpu_times, 'system'):
            self.cpu_time_seconds.labels(mode='system').set(cpu_times.system)
        if hasattr(cpu_times, 'idle'):
            self.cpu_time_seconds.labels(mode='idle').set(cpu_times.idle)
        if hasattr(cpu_times, 'iowait'):
            self.cpu_time_seconds.labels(mode='iowait').set(cpu_times.iowait)

        self.logger.debug(f"Collected CPU metrics: {cpu_percent:.1f}% used")
