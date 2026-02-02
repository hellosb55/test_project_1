"""
Alert manager for tracking alert state and sending notifications.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from collections import defaultdict

from src.alerts.alert_rule import AlertRule
from src.alerts.storage.base_storage import BaseStorage, Alert, AlertState

logger = logging.getLogger(__name__)


class AlertTracker:
    """Tracks state for individual alert instance"""

    def __init__(self, alert_id: str, rule: AlertRule, metric_value: float, labels: Dict[str, str]):
        self.alert_id = alert_id
        self.rule = rule
        self.first_triggered_at = datetime.now()
        self.last_triggered_at = datetime.now()
        self.last_notified_at: Optional[datetime] = None
        self.last_value = metric_value
        self.labels = labels
        self.state = AlertState.TRIGGERED
        self.notification_count = 0

    def update(self, metric_value: float):
        """Update tracker with new metric value"""
        self.last_triggered_at = datetime.now()
        self.last_value = metric_value

    def should_notify(self) -> bool:
        """Check if notification should be sent based on duration and cooldown"""
        now = datetime.now()

        # Check duration requirement
        duration_met = (now - self.first_triggered_at) >= timedelta(minutes=self.rule.for_duration_minutes)
        if not duration_met:
            return False

        # Check cooldown
        if self.last_notified_at:
            cooldown_met = (now - self.last_notified_at) >= timedelta(minutes=self.rule.cooldown_minutes)
            if not cooldown_met:
                return False

        return True

    def mark_notified(self):
        """Mark alert as notified"""
        self.last_notified_at = datetime.now()
        self.state = AlertState.ACTIVE
        self.notification_count += 1


class AlertManager:
    """Manages alert lifecycle and notifications"""

    def __init__(self, config: Dict, storage: BaseStorage):
        """
        Initialize alert manager.

        Args:
            config: Alerting configuration dict
            storage: Storage backend for alert history
        """
        self.config = config
        self.storage = storage

        # In-memory tracking of active alerts
        self.alert_trackers: Dict[str, AlertTracker] = {}

        # Initialize notification channels
        self.channels = self._init_channels()

        # Load active alerts from storage
        self._restore_active_alerts()

        logger.info("Alert manager initialized")

    def _init_channels(self) -> Dict:
        """Initialize notification channels based on config"""
        channels = {}
        channel_config = self.config.get('channels', {})

        # Import and initialize enabled channels
        if channel_config.get('email', {}).get('enabled', False):
            try:
                from src.alerts.channels.email_channel import EmailChannel
                channels['email'] = EmailChannel(channel_config['email'])
                logger.info("Email channel initialized")
            except Exception as e:
                logger.error(f"Failed to initialize email channel: {e}")

        if channel_config.get('slack', {}).get('enabled', False):
            try:
                from src.alerts.channels.slack_channel import SlackChannel
                channels['slack'] = SlackChannel(channel_config['slack'])
                logger.info("Slack channel initialized")
            except Exception as e:
                logger.error(f"Failed to initialize slack channel: {e}")

        if channel_config.get('webhook', {}).get('enabled', False):
            try:
                from src.alerts.channels.webhook_channel import WebhookChannel
                channels['webhook'] = WebhookChannel(channel_config['webhook'])
                logger.info("Webhook channel initialized")
            except Exception as e:
                logger.error(f"Failed to initialize webhook channel: {e}")

        if not channels:
            logger.warning("No notification channels enabled")

        return channels

    def _restore_active_alerts(self):
        """Restore active alert trackers from storage"""
        try:
            active_alerts = self.storage.get_active_alerts()
            logger.info(f"Restoring {len(active_alerts)} active alerts from storage")

            # Note: Full restoration would require rule objects, which we don't have here
            # This is a simplified version - in production, you might want to store
            # rule definitions in the database as well
        except Exception as e:
            logger.error(f"Failed to restore active alerts: {e}")

    def process_alert(self, rule: AlertRule, metric_value: float, labels: Dict[str, str]) -> None:
        """
        Process alert condition being met.

        Args:
            rule: Alert rule that triggered
            metric_value: Current metric value
            labels: Metric labels
        """
        alert_id = rule.generate_alert_id(labels)

        # Get or create tracker
        if alert_id not in self.alert_trackers:
            # New alert triggered
            tracker = AlertTracker(alert_id, rule, metric_value, labels)
            self.alert_trackers[alert_id] = tracker

            # Save to storage
            alert = Alert(
                alert_id=alert_id,
                rule_name=rule.name,
                state=AlertState.TRIGGERED,
                severity=rule.severity,
                metric_name=rule.metric_name,
                metric_value=metric_value,
                threshold=rule.threshold,
                triggered_at=tracker.first_triggered_at,
                labels=labels,
                annotations=rule.annotations,
            )
            self.storage.save_alert(alert)

            logger.info(f"Alert triggered: {alert_id} ({rule.name})")
        else:
            # Update existing tracker
            tracker = self.alert_trackers[alert_id]
            tracker.update(metric_value)

        # Check if we should send notification
        if tracker.should_notify():
            self._send_notifications(tracker)

    def resolve_alert(self, rule: AlertRule, labels: Dict[str, str]) -> None:
        """
        Mark alert as resolved (condition no longer met).

        Args:
            rule: Alert rule
            labels: Metric labels
        """
        alert_id = rule.generate_alert_id(labels)

        if alert_id in self.alert_trackers:
            tracker = self.alert_trackers[alert_id]

            # Update storage
            self.storage.update_alert_state(
                alert_id,
                AlertState.RESOLVED,
                resolved_at=datetime.now()
            )

            # Remove from tracking
            del self.alert_trackers[alert_id]

            logger.info(f"Alert resolved: {alert_id} ({rule.name})")

            # Optionally send resolution notification
            if self.config.get('send_resolved_notifications', False):
                self._send_resolution_notifications(tracker)

    def _send_notifications(self, tracker: AlertTracker) -> None:
        """
        Send notifications through configured channels.

        Args:
            tracker: Alert tracker with notification details
        """
        rule = tracker.rule
        metric_value = tracker.last_value
        labels = tracker.labels

        logger.info(f"Sending notifications for alert: {tracker.alert_id}")

        # Send through each configured channel
        for channel_name in rule.channels:
            channel = self.channels.get(channel_name)
            if not channel:
                logger.warning(f"Channel {channel_name} not available")
                continue

            try:
                success = channel.send(rule, metric_value, labels)
                if success:
                    logger.info(f"Sent notification via {channel_name} for {tracker.alert_id}")
                else:
                    logger.error(f"Failed to send notification via {channel_name}")
            except Exception as e:
                logger.error(f"Error sending notification via {channel_name}: {e}")

        # Update tracker and storage
        tracker.mark_notified()
        self.storage.update_notification_info(tracker.alert_id, tracker.last_notified_at)
        self.storage.update_alert_state(tracker.alert_id, AlertState.ACTIVE)

    def _send_resolution_notifications(self, tracker: AlertTracker) -> None:
        """Send resolution notifications"""
        # Implementation for resolution notifications
        logger.debug(f"Resolution notification for {tracker.alert_id} (not implemented)")

    def get_active_alert_count(self) -> int:
        """Get count of currently active alerts"""
        return len(self.alert_trackers)

    def get_alerts_by_severity(self) -> Dict[str, int]:
        """Get active alert counts by severity"""
        severity_counts = defaultdict(int)
        for tracker in self.alert_trackers.values():
            severity_counts[tracker.rule.severity] += 1
        return dict(severity_counts)

    def cleanup_old_alerts(self) -> None:
        """Cleanup old resolved alerts from storage"""
        try:
            retention_days = self.storage.retention_days
            deleted_count = self.storage.cleanup_old_alerts(retention_days)
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old alerts")
        except Exception as e:
            logger.error(f"Failed to cleanup old alerts: {e}")

    def shutdown(self) -> None:
        """Shutdown alert manager and cleanup resources"""
        logger.info("Shutting down alert manager")

        # Close storage
        self.storage.close()

        # Clear trackers
        self.alert_trackers.clear()
