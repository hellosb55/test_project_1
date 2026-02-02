"""
Custom webhook notification channel.
"""

import logging
import json
from typing import Dict
try:
    import requests
except ImportError:
    requests = None

from src.alerts.channels.base_channel import BaseChannel

logger = logging.getLogger(__name__)


class WebhookChannel(BaseChannel):
    """Custom webhook notification channel"""

    def __init__(self, config: Dict):
        """
        Initialize webhook channel.

        Args:
            config: Webhook configuration dict with url, method, headers
        """
        if requests is None:
            raise ImportError("requests library required for Webhook channel. Install with: pip install requests")

        self.url = config['url']
        self.method = config.get('method', 'POST').upper()
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 10)

        # Ensure Content-Type is set
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/json'

        logger.info(f"Webhook channel initialized (url: {self.url}, method: {self.method})")

    def send(self, rule, value: float, labels: Dict[str, str]) -> bool:
        """
        Send webhook notification.

        Args:
            rule: AlertRule instance
            value: Current metric value
            labels: Metric labels

        Returns:
            True if sent successfully
        """
        try:
            # Format message
            message_content = self.format_message(rule, value, labels)

            # Create payload
            payload = self._create_webhook_payload(rule, value, labels, message_content)

            # Send HTTP request
            if self.method == 'POST':
                response = requests.post(
                    self.url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )
            elif self.method == 'PUT':
                response = requests.put(
                    self.url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )
            else:
                logger.error(f"Unsupported HTTP method: {self.method}")
                return False

            response.raise_for_status()

            logger.info(f"Webhook notification sent for alert: {rule.name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send webhook notification for alert {rule.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False

    def _create_webhook_payload(self, rule, value: float, labels: Dict[str, str],
                               message_content: Dict[str, str]) -> Dict:
        """Create webhook payload"""
        from datetime import datetime

        payload = {
            "alert": {
                "name": rule.name,
                "severity": rule.severity,
                "status": "firing",
                "timestamp": datetime.now().isoformat(),
            },
            "metric": {
                "name": rule.metric_name,
                "value": value,
                "threshold": rule.threshold,
                "operator": rule.operator,
            },
            "labels": labels,
            "annotations": {
                "summary": message_content['summary'],
                "description": message_content['description'],
            }
        }

        return payload
