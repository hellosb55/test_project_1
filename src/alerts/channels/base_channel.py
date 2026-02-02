"""
Base notification channel interface.
"""

from abc import ABC, abstractmethod
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BaseChannel(ABC):
    """Abstract base class for notification channels"""

    @abstractmethod
    def send(self, rule, value: float, labels: Dict[str, str]) -> bool:
        """
        Send alert notification.

        Args:
            rule: AlertRule instance
            value: Current metric value that triggered alert
            labels: Metric labels

        Returns:
            True if notification sent successfully, False otherwise
        """
        pass

    def format_message(self, rule, value: float, labels: Dict[str, str]) -> Dict[str, str]:
        """
        Format alert message from rule annotations.

        Args:
            rule: AlertRule instance
            value: Current metric value
            labels: Metric labels

        Returns:
            Dict with 'summary' and 'description' keys
        """
        annotations = rule.annotations or {}

        # Format summary
        summary = annotations.get('summary', f"Alert: {rule.name}")
        summary = self._substitute_template(summary, value, rule.threshold, labels)

        # Format description
        description = annotations.get('description', f"{rule.metric_name} {rule.operator} {rule.threshold}")
        description = self._substitute_template(description, value, rule.threshold, labels)

        return {
            'summary': summary,
            'description': description,
        }

    def _substitute_template(self, template: str, value: float,
                            threshold: float, labels: Dict[str, str]) -> str:
        """
        Substitute template variables.

        Supports:
            {{ value }} - Current metric value
            {{ threshold }} - Alert threshold
            {{ labels.key }} - Label values

        Args:
            template: Template string
            value: Metric value
            threshold: Alert threshold
            labels: Label dict

        Returns:
            Formatted string
        """
        try:
            # Simple template substitution
            result = template.replace('{{ value }}', f'{value:.2f}')
            result = result.replace('{{ threshold }}', f'{threshold:.2f}')

            # Substitute labels
            for key, val in labels.items():
                result = result.replace(f'{{{{ labels.{key} }}}}', str(val))

            return result

        except Exception as e:
            logger.error(f"Error substituting template: {e}")
            return template
