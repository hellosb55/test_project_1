"""
Slack notification channel using webhooks.
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


class SlackChannel(BaseChannel):
    """Slack notification channel via webhooks"""

    def __init__(self, config: Dict):
        """
        Initialize Slack channel.

        Args:
            config: Slack configuration dict with webhook_url
        """
        if requests is None:
            raise ImportError("requests library required for Slack channel. Install with: pip install requests")

        self.webhook_url = config['webhook_url']
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'Metrics Agent')
        self.icon_emoji = config.get('icon_emoji', ':rotating_light:')

        logger.info(f"Slack channel initialized (channel: {self.channel})")

    def send(self, rule, value: float, labels: Dict[str, str]) -> bool:
        """
        Send Slack notification.

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

            # Create Slack payload
            payload = self._create_slack_payload(rule, value, labels, message_content)

            # Send to webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response.raise_for_status()

            logger.info(f"Slack notification sent for alert: {rule.name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification for alert {rule.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    def _create_slack_payload(self, rule, value: float, labels: Dict[str, str],
                             message_content: Dict[str, str]) -> Dict:
        """Create Slack webhook payload"""
        severity_colors = {
            'info': '#0066cc',
            'warning': '#ff9900',
            'critical': '#cc0000',
        }
        color = severity_colors.get(rule.severity, '#666666')

        # Format labels for display
        labels_text = ""
        if labels:
            labels_text = "\n" + "\n".join(f"• *{k}:* {v}" for k, v in labels.items())

        # Build fields
        fields = [
            {
                "title": "Severity",
                "value": rule.severity.upper(),
                "short": True
            },
            {
                "title": "Current Value",
                "value": f"{value:.2f}",
                "short": True
            },
            {
                "title": "Threshold",
                "value": f"{rule.operator} {rule.threshold}",
                "short": True
            },
            {
                "title": "Metric",
                "value": rule.metric_name,
                "short": True
            },
        ]

        # Create attachment
        attachment = {
            "color": color,
            "title": message_content['summary'],
            "text": message_content['description'] + labels_text,
            "fields": fields,
            "footer": "Metrics Monitoring Agent",
            "ts": int(datetime.now().timestamp()),
        }

        # Add @channel mention for critical alerts
        text = ""
        if rule.severity == 'critical':
            text = "<!channel> Critical Alert"

        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "text": text,
            "attachments": [attachment]
        }

        return payload


# Import datetime for timestamp
from datetime import datetime
