"""Network metrics collector"""

import psutil
import time
from prometheus_client import Counter, Gauge
from src.collectors.base import BaseCollector


class NetworkCollector(BaseCollector):
    """Collector for network metrics"""

    def __init__(self, config):
        super().__init__(config)
        # State for rate calculation
        self.prev_net_counters = {}
        self.prev_net_time = None

    def register_metrics(self, registry):
        """Register Prometheus metrics"""
        # Network I/O counters
        self.network_receive_bytes = Counter(
            'network_receive_bytes_total',
            'Total bytes received',
            ['interface'],
            registry=registry
        )
        self.network_transmit_bytes = Counter(
            'network_transmit_bytes_total',
            'Total bytes transmitted',
            ['interface'],
            registry=registry
        )
        self.network_receive_packets = Counter(
            'network_receive_packets_total',
            'Total packets received',
            ['interface'],
            registry=registry
        )
        self.network_transmit_packets = Counter(
            'network_transmit_packets_total',
            'Total packets transmitted',
            ['interface'],
            registry=registry
        )
        self.network_receive_errors = Counter(
            'network_receive_errors_total',
            'Total receive errors',
            ['interface'],
            registry=registry
        )
        self.network_transmit_errors = Counter(
            'network_transmit_errors_total',
            'Total transmit errors',
            ['interface'],
            registry=registry
        )
        self.network_receive_drop = Counter(
            'network_receive_drop_total',
            'Total received packets dropped',
            ['interface'],
            registry=registry
        )
        self.network_transmit_drop = Counter(
            'network_transmit_drop_total',
            'Total transmitted packets dropped',
            ['interface'],
            registry=registry
        )

        # Connection states
        self.network_connections = Gauge(
            'network_connections',
            'Number of network connections by state',
            ['state'],
            registry=registry
        )

    def collect(self):
        """Collect network metrics"""
        self._collect_io()

        if self.config.get('collect_connections', True):
            self._collect_connections()

    def _collect_io(self):
        """Collect network I/O metrics"""
        exclude_interfaces = self.config.get('exclude_interfaces', [])

        try:
            net_io = psutil.net_io_counters(pernic=True)
            current_time = time.time()

            for interface, counters in net_io.items():
                # Filter out excluded interfaces
                if interface in exclude_interfaces:
                    continue

                # Calculate deltas and update counters
                if interface in self.prev_net_counters:
                    prev = self.prev_net_counters[interface]

                    bytes_recv_delta = max(0, counters.bytes_recv - prev['bytes_recv'])
                    bytes_sent_delta = max(0, counters.bytes_sent - prev['bytes_sent'])
                    packets_recv_delta = max(0, counters.packets_recv - prev['packets_recv'])
                    packets_sent_delta = max(0, counters.packets_sent - prev['packets_sent'])
                    errin_delta = max(0, counters.errin - prev['errin'])
                    errout_delta = max(0, counters.errout - prev['errout'])
                    dropin_delta = max(0, counters.dropin - prev['dropin'])
                    dropout_delta = max(0, counters.dropout - prev['dropout'])

                    self.network_receive_bytes.labels(interface=interface).inc(bytes_recv_delta)
                    self.network_transmit_bytes.labels(interface=interface).inc(bytes_sent_delta)
                    self.network_receive_packets.labels(interface=interface).inc(packets_recv_delta)
                    self.network_transmit_packets.labels(interface=interface).inc(packets_sent_delta)
                    self.network_receive_errors.labels(interface=interface).inc(errin_delta)
                    self.network_transmit_errors.labels(interface=interface).inc(errout_delta)
                    self.network_receive_drop.labels(interface=interface).inc(dropin_delta)
                    self.network_transmit_drop.labels(interface=interface).inc(dropout_delta)

                # Store current counters
                self.prev_net_counters[interface] = {
                    'bytes_recv': counters.bytes_recv,
                    'bytes_sent': counters.bytes_sent,
                    'packets_recv': counters.packets_recv,
                    'packets_sent': counters.packets_sent,
                    'errin': counters.errin,
                    'errout': counters.errout,
                    'dropin': counters.dropin,
                    'dropout': counters.dropout,
                }

            self.prev_net_time = current_time

        except Exception as e:
            self.logger.warning(f"Failed to collect network I/O metrics: {e}")

    def _collect_connections(self):
        """Collect network connection state metrics"""
        try:
            connections = psutil.net_connections(kind='inet')

            # Count connections by state
            state_counts = {}
            for conn in connections:
                state = conn.status
                state_counts[state] = state_counts.get(state, 0) + 1

            # Update metrics
            for state, count in state_counts.items():
                self.network_connections.labels(state=state).set(count)

            self.logger.debug(f"Collected {len(connections)} network connections")

        except (psutil.AccessDenied, PermissionError) as e:
            self.logger.debug(f"Cannot access network connections (requires elevated privileges): {e}")
        except Exception as e:
            self.logger.warning(f"Failed to collect network connection metrics: {e}")
