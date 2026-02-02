"""Process metrics collector"""

import psutil
from prometheus_client import Gauge
from src.collectors.base import BaseCollector


class ProcessCollector(BaseCollector):
    """Collector for process metrics"""

    def register_metrics(self, registry):
        """Register Prometheus metrics"""
        self.process_cpu_percent = Gauge(
            'process_cpu_percent',
            'Process CPU usage percentage',
            ['pid', 'name', 'user'],
            registry=registry
        )
        self.process_memory_bytes = Gauge(
            'process_memory_bytes',
            'Process memory usage in bytes (RSS)',
            ['pid', 'name', 'user'],
            registry=registry
        )
        self.process_runtime_seconds = Gauge(
            'process_runtime_seconds',
            'Process runtime in seconds',
            ['pid', 'name', 'user'],
            registry=registry
        )

    def collect(self):
        """Collect process metrics"""
        top_n = self.config.get('top_n', 20)

        try:
            # Get all processes with required attributes
            processes = []

            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'create_time']):
                try:
                    info = proc.info
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'] or 'unknown',
                        'user': info['username'] or 'unknown',
                        'cpu_percent': info['cpu_percent'] or 0.0,
                        'memory_bytes': info['memory_info'].rss if info['memory_info'] else 0,
                        'create_time': info['create_time'] or 0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process terminated or access denied, skip it
                    continue
                except Exception as e:
                    self.logger.debug(f"Error getting process info: {e}")
                    continue

            # Sort by CPU usage
            processes_by_cpu = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:top_n]

            # Sort by memory usage
            processes_by_mem = sorted(processes, key=lambda p: p['memory_bytes'], reverse=True)[:top_n]

            # Combine and deduplicate
            top_processes = {p['pid']: p for p in processes_by_cpu}
            for p in processes_by_mem:
                if p['pid'] not in top_processes:
                    top_processes[p['pid']] = p

            # Update metrics
            import time
            current_time = time.time()

            for proc_info in top_processes.values():
                pid_str = str(proc_info['pid'])
                name = proc_info['name'][:50]  # Limit name length
                user = proc_info['user'][:30]  # Limit user length

                self.process_cpu_percent.labels(
                    pid=pid_str,
                    name=name,
                    user=user
                ).set(proc_info['cpu_percent'])

                self.process_memory_bytes.labels(
                    pid=pid_str,
                    name=name,
                    user=user
                ).set(proc_info['memory_bytes'])

                runtime = current_time - proc_info['create_time']
                self.process_runtime_seconds.labels(
                    pid=pid_str,
                    name=name,
                    user=user
                ).set(runtime)

            self.logger.debug(f"Collected metrics for {len(top_processes)} top processes")

        except Exception as e:
            self.logger.error(f"Failed to collect process metrics: {e}")
            raise
