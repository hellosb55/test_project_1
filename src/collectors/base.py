"""Base collector abstract class"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import time
from src.utils.logger import get_logger


class BaseCollector(ABC):
    """Abstract base class for metric collectors"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize collector

        Args:
            config: Collector configuration
        """
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
        self.error_count = 0
        self.last_success = None
        self.last_collection_duration = 0

    @abstractmethod
    def collect(self):
        """
        Collect metrics and update Prometheus metrics

        This method should be implemented by subclasses
        """
        pass

    @abstractmethod
    def register_metrics(self, registry):
        """
        Register Prometheus metrics with the registry

        Args:
            registry: Prometheus registry

        This method should be implemented by subclasses
        """
        pass

    def get_interval(self) -> int:
        """
        Get collection interval in seconds

        Returns:
            Interval in seconds
        """
        return self.config.get('interval', 5)

    def run_collection(self):
        """
        Run collection with timing and error handling

        Returns:
            True if collection succeeded, False otherwise
        """
        start_time = time.time()

        try:
            self.collect()
            self.last_success = time.time()
            self.last_collection_duration = time.time() - start_time
            self.error_count = 0

            self.logger.debug(
                f"Collection completed in {self.last_collection_duration:.3f}s"
            )
            return True

        except Exception as e:
            self.error_count += 1
            self.logger.error(
                f"Collection failed (error #{self.error_count}): {e}",
                exc_info=True
            )
            return False

    def is_healthy(self) -> bool:
        """
        Check if collector is healthy

        Returns:
            True if healthy, False otherwise
        """
        # Collector is unhealthy if it has failed 3 consecutive times
        return self.error_count < 3

    def get_name(self) -> str:
        """
        Get collector name

        Returns:
            Collector name
        """
        return self.__class__.__name__.replace('Collector', '').lower()
