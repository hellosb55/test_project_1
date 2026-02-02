"""Disk metrics collector"""

import psutil
import time
from prometheus_client import Gauge, Counter
from src.collectors.base import BaseCollector


class DiskCollector(BaseCollector):
    """Collector for disk metrics"""

    def __init__(self, config):
        super().__init__(config)
        # State for rate calculation
        self.prev_io_counters = {}
        self.prev_io_time = None

    def register_metrics(self, registry):
        """Register Prometheus metrics"""
        # Disk usage metrics
        self.disk_usage_bytes = Gauge(
            'disk_usage_bytes',
            'Disk usage in bytes',
            ['mount_point', 'type'],
            registry=registry
        )
        self.disk_usage_percent = Gauge(
            'disk_usage_percent',
            'Disk usage percentage',
            ['mount_point'],
            registry=registry
        )

        # Disk I/O metrics (counters for rate calculation)
        self.disk_io_read_bytes = Counter(
            'disk_io_read_bytes_total',
            'Total bytes read from disk',
            ['device'],
            registry=registry
        )
        self.disk_io_write_bytes = Counter(
            'disk_io_write_bytes_total',
            'Total bytes written to disk',
            ['device'],
            registry=registry
        )
        self.disk_io_read_operations = Counter(
            'disk_io_read_operations_total',
            'Total read operations',
            ['device'],
            registry=registry
        )
        self.disk_io_write_operations = Counter(
            'disk_io_write_operations_total',
            'Total write operations',
            ['device'],
            registry=registry
        )

    def collect(self):
        """Collect disk metrics"""
        self._collect_usage()
        self._collect_io()

    def _collect_usage(self):
        """Collect disk usage metrics"""
        exclude_fs = self.config.get('exclude_filesystems', [])
        exclude_mounts = self.config.get('exclude_mount_points', [])

        for partition in psutil.disk_partitions(all=False):
            # Filter out excluded filesystems
            if partition.fstype in exclude_fs:
                continue

            # Filter out excluded mount points
            if any(partition.mountpoint.startswith(mp) for mp in exclude_mounts):
                continue

            try:
                usage = psutil.disk_usage(partition.mountpoint)

                self.disk_usage_bytes.labels(
                    mount_point=partition.mountpoint,
                    type='total'
                ).set(usage.total)

                self.disk_usage_bytes.labels(
                    mount_point=partition.mountpoint,
                    type='used'
                ).set(usage.used)

                self.disk_usage_bytes.labels(
                    mount_point=partition.mountpoint,
                    type='free'
                ).set(usage.free)

                self.disk_usage_percent.labels(
                    mount_point=partition.mountpoint
                ).set(usage.percent)

            except (PermissionError, OSError) as e:
                self.logger.debug(f"Cannot access {partition.mountpoint}: {e}")

    def _collect_io(self):
        """Collect disk I/O metrics"""
        try:
            io_counters = psutil.disk_io_counters(perdisk=True)
            current_time = time.time()

            for device, counters in io_counters.items():
                # Update counters (Prometheus will calculate rates)
                self.disk_io_read_bytes.labels(device=device).inc(
                    counters.read_bytes - self.prev_io_counters.get(device, {}).get('read_bytes', 0)
                    if device in self.prev_io_counters else 0
                )

                self.disk_io_write_bytes.labels(device=device).inc(
                    counters.write_bytes - self.prev_io_counters.get(device, {}).get('write_bytes', 0)
                    if device in self.prev_io_counters else 0
                )

                self.disk_io_read_operations.labels(device=device).inc(
                    counters.read_count - self.prev_io_counters.get(device, {}).get('read_count', 0)
                    if device in self.prev_io_counters else 0
                )

                self.disk_io_write_operations.labels(device=device).inc(
                    counters.write_count - self.prev_io_counters.get(device, {}).get('write_count', 0)
                    if device in self.prev_io_counters else 0
                )

                # Store current counters for next iteration
                self.prev_io_counters[device] = {
                    'read_bytes': counters.read_bytes,
                    'write_bytes': counters.write_bytes,
                    'read_count': counters.read_count,
                    'write_count': counters.write_count,
                }

            self.prev_io_time = current_time

        except Exception as e:
            self.logger.warning(f"Failed to collect disk I/O metrics: {e}")

        self.logger.debug("Collected disk metrics")
