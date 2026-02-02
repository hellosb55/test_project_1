"""
Utility for reading metrics from Prometheus registry.
"""

import logging
from typing import Dict, List, Tuple, Optional
from prometheus_client import CollectorRegistry

logger = logging.getLogger(__name__)


class MetricReader:
    """Reads current metric values from Prometheus registry"""

    def __init__(self, registry: CollectorRegistry):
        """
        Initialize metric reader.

        Args:
            registry: Prometheus CollectorRegistry instance
        """
        self.registry = registry

    def get_metric_value(self, metric_name: str,
                        label_selector: Optional[Dict[str, str]] = None) -> List[Tuple[float, Dict[str, str]]]:
        """
        Get current values for a metric with optional label filtering.

        Args:
            metric_name: Name of the metric to read
            label_selector: Dict of label key-value pairs to filter by

        Returns:
            List of (value, labels) tuples for matching metric samples

        Example:
            >>> reader.get_metric_value('cpu_usage_percent')
            [(45.2, {})]

            >>> reader.get_metric_value('disk_usage_percent', {'mount_point': '/'})
            [(78.5, {'mount_point': '/', 'device': '/dev/sda1'})]
        """
        results = []

        try:
            # Collect all metrics from registry
            for metric_family in self.registry.collect():
                if metric_family.name != metric_name:
                    continue

                # Iterate through samples
                for sample in metric_family.samples:
                    # Sample format: (name, labels_dict, value)
                    sample_name = sample.name
                    sample_labels = sample.labels
                    sample_value = sample.value

                    # Apply label selector filter
                    if label_selector:
                        if not self._match_labels(sample_labels, label_selector):
                            continue

                    results.append((sample_value, dict(sample_labels)))

                # Found the metric family, no need to continue
                break

            if not results:
                logger.debug(f"No values found for metric {metric_name} with selector {label_selector}")

            return results

        except Exception as e:
            logger.error(f"Error reading metric {metric_name}: {e}")
            return []

    def _match_labels(self, sample_labels: Dict[str, str],
                     selector: Dict[str, str]) -> bool:
        """
        Check if sample labels match selector.

        Args:
            sample_labels: Labels from metric sample
            selector: Required label key-value pairs

        Returns:
            True if all selector labels match sample labels
        """
        for key, value in selector.items():
            if sample_labels.get(key) != value:
                return False
        return True

    def get_all_metric_names(self) -> List[str]:
        """
        Get list of all available metric names in registry.

        Returns:
            List of metric names
        """
        metric_names = set()

        try:
            for metric_family in self.registry.collect():
                metric_names.add(metric_family.name)
        except Exception as e:
            logger.error(f"Error getting metric names: {e}")

        return sorted(metric_names)
