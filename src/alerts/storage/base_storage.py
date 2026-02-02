"""
Base storage interface for alert history.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json


class AlertState:
    """Alert state constants"""
    TRIGGERED = 'triggered'  # Condition met, tracking duration
    ACTIVE = 'active'        # Duration met, notifications sent
    RESOLVED = 'resolved'    # Condition no longer met


@dataclass
class Alert:
    """Alert instance data"""
    alert_id: str
    rule_name: str
    state: str
    severity: str
    metric_name: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    resolved_at: Optional[datetime] = None
    last_notified_at: Optional[datetime] = None
    notification_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'alert_id': self.alert_id,
            'rule_name': self.rule_name,
            'state': self.state,
            'severity': self.severity,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'labels': json.dumps(self.labels),
            'annotations': json.dumps(self.annotations),
            'triggered_at': self.triggered_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'last_notified_at': self.last_notified_at.isoformat() if self.last_notified_at else None,
            'notification_count': self.notification_count,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Alert':
        """Create Alert from dictionary"""
        return cls(
            alert_id=data['alert_id'],
            rule_name=data['rule_name'],
            state=data['state'],
            severity=data['severity'],
            metric_name=data['metric_name'],
            metric_value=data['metric_value'],
            threshold=data['threshold'],
            labels=json.loads(data['labels']) if isinstance(data['labels'], str) else data['labels'],
            annotations=json.loads(data['annotations']) if isinstance(data['annotations'], str) else data['annotations'],
            triggered_at=datetime.fromisoformat(data['triggered_at']) if isinstance(data['triggered_at'], str) else data['triggered_at'],
            resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') and isinstance(data['resolved_at'], str) else data.get('resolved_at'),
            last_notified_at=datetime.fromisoformat(data['last_notified_at']) if data.get('last_notified_at') and isinstance(data['last_notified_at'], str) else data.get('last_notified_at'),
            notification_count=data.get('notification_count', 0),
        )


class BaseStorage(ABC):
    """Abstract base class for alert storage backends"""

    @abstractmethod
    def save_alert(self, alert: Alert) -> None:
        """
        Save a new alert to storage.

        Args:
            alert: Alert instance to save
        """
        pass

    @abstractmethod
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Retrieve alert by ID.

        Args:
            alert_id: Unique alert identifier

        Returns:
            Alert instance or None if not found
        """
        pass

    @abstractmethod
    def update_alert_state(self, alert_id: str, state: str,
                          resolved_at: Optional[datetime] = None) -> None:
        """
        Update alert state.

        Args:
            alert_id: Alert identifier
            state: New state (triggered, active, resolved)
            resolved_at: Resolution timestamp (for resolved state)
        """
        pass

    @abstractmethod
    def update_notification_info(self, alert_id: str, notified_at: datetime) -> None:
        """
        Update notification information.

        Args:
            alert_id: Alert identifier
            notified_at: Timestamp of notification
        """
        pass

    @abstractmethod
    def get_active_alerts(self) -> List[Alert]:
        """
        Get all alerts in triggered or active state.

        Returns:
            List of active Alert instances
        """
        pass

    @abstractmethod
    def get_alerts_by_rule(self, rule_name: str, limit: int = 100) -> List[Alert]:
        """
        Get recent alerts for a specific rule.

        Args:
            rule_name: Name of the alert rule
            limit: Maximum number of alerts to return

        Returns:
            List of Alert instances
        """
        pass

    @abstractmethod
    def cleanup_old_alerts(self, days: int) -> int:
        """
        Delete alerts older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of alerts deleted
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close storage connection and cleanup resources"""
        pass
