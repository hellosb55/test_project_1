"""Memory metrics collector"""

import psutil
from prometheus_client import Gauge
from src.collectors.base import BaseCollector


class MemoryCollector(BaseCollector):
    """Collector for memory metrics"""

    def register_metrics(self, registry):
        """Register Prometheus metrics"""
        # Physical memory metrics
        self.memory_total = Gauge(
            'memory_total_bytes',
            'Total physical memory in bytes',
            registry=registry
        )
        self.memory_used = Gauge(
            'memory_used_bytes',
            'Used memory in bytes',
            registry=registry
        )
        self.memory_available = Gauge(
            'memory_available_bytes',
            'Available memory in bytes',
            registry=registry
        )
        self.memory_cached = Gauge(
            'memory_cached_bytes',
            'Cached memory in bytes',
            registry=registry
        )
        self.memory_usage_percent = Gauge(
            'memory_usage_percent',
            'Memory usage percentage',
            registry=registry
        )

        # Swap memory metrics
        self.swap_total = Gauge(
            'swap_total_bytes',
            'Total swap memory in bytes',
            registry=registry
        )
        self.swap_used = Gauge(
            'swap_used_bytes',
            'Used swap memory in bytes',
            registry=registry
        )
        self.swap_usage_percent = Gauge(
            'swap_usage_percent',
            'Swap usage percentage',
            registry=registry
        )

    def collect(self):
        """Collect memory metrics"""
        # Collect virtual memory
        vm = psutil.virtual_memory()
        self.memory_total.set(vm.total)
        self.memory_used.set(vm.used)
        self.memory_available.set(vm.available)
        self.memory_usage_percent.set(vm.percent)

        # Cached memory (platform dependent)
        if hasattr(vm, 'cached'):
            self.memory_cached.set(vm.cached)
        elif hasattr(vm, 'buffers'):
            self.memory_cached.set(vm.buffers)

        # Collect swap memory
        swap = psutil.swap_memory()
        self.swap_total.set(swap.total)
        self.swap_used.set(swap.used)
        self.swap_usage_percent.set(swap.percent)

        self.logger.debug(
            f"Collected memory metrics: {vm.percent:.1f}% used, "
            f"swap {swap.percent:.1f}% used"
        )
