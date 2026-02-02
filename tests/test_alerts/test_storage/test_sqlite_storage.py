"""Tests for SQLite storage backend"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from src.alerts.storage.sqlite_storage import SQLiteStorage
from src.alerts.storage.base_storage import Alert, AlertState


class TestSQLiteStorage:
    """Test SQLite storage backend"""

    @pytest.fixture
    def storage(self):
        """Create temporary SQLite storage"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        config = {
            'sqlite_path': temp_db.name,
            'retention_days': 30,
        }
        storage = SQLiteStorage(config)

        yield storage

        storage.close()
        os.unlink(temp_db.name)

    def test_save_and_get_alert(self, storage):
        """Test saving and retrieving an alert"""
        alert = Alert(
            alert_id="test_alert",
            rule_name="test_rule",
            state=AlertState.TRIGGERED,
            severity="warning",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            triggered_at=datetime.now(),
            labels={"host": "server1"},
            annotations={"summary": "High CPU"},
        )

        storage.save_alert(alert)

        retrieved = storage.get_alert("test_alert")
        assert retrieved is not None
        assert retrieved.alert_id == "test_alert"
        assert retrieved.rule_name == "test_rule"
        assert retrieved.state == AlertState.TRIGGERED
        assert retrieved.metric_value == 85.0

    def test_update_alert_state(self, storage):
        """Test updating alert state"""
        alert = Alert(
            alert_id="test_alert",
            rule_name="test_rule",
            state=AlertState.TRIGGERED,
            severity="warning",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            triggered_at=datetime.now(),
        )

        storage.save_alert(alert)

        # Update state
        storage.update_alert_state("test_alert", AlertState.ACTIVE)

        retrieved = storage.get_alert("test_alert")
        assert retrieved.state == AlertState.ACTIVE

    def test_update_notification_info(self, storage):
        """Test updating notification information"""
        alert = Alert(
            alert_id="test_alert",
            rule_name="test_rule",
            state=AlertState.ACTIVE,
            severity="warning",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            triggered_at=datetime.now(),
        )

        storage.save_alert(alert)

        # Update notification info
        notified_at = datetime.now()
        storage.update_notification_info("test_alert", notified_at)

        retrieved = storage.get_alert("test_alert")
        assert retrieved.last_notified_at is not None
        assert retrieved.notification_count == 1

        # Update again
        storage.update_notification_info("test_alert", datetime.now())
        retrieved = storage.get_alert("test_alert")
        assert retrieved.notification_count == 2

    def test_get_active_alerts(self, storage):
        """Test retrieving active alerts"""
        # Create triggered alert
        alert1 = Alert(
            alert_id="alert1",
            rule_name="rule1",
            state=AlertState.TRIGGERED,
            severity="warning",
            metric_name="cpu",
            metric_value=85.0,
            threshold=80.0,
            triggered_at=datetime.now(),
        )

        # Create active alert
        alert2 = Alert(
            alert_id="alert2",
            rule_name="rule2",
            state=AlertState.ACTIVE,
            severity="critical",
            metric_name="memory",
            metric_value=95.0,
            threshold=90.0,
            triggered_at=datetime.now(),
        )

        # Create resolved alert
        alert3 = Alert(
            alert_id="alert3",
            rule_name="rule3",
            state=AlertState.RESOLVED,
            severity="warning",
            metric_name="disk",
            metric_value=70.0,
            threshold=80.0,
            triggered_at=datetime.now(),
            resolved_at=datetime.now(),
        )

        storage.save_alert(alert1)
        storage.save_alert(alert2)
        storage.save_alert(alert3)

        active = storage.get_active_alerts()
        assert len(active) == 2
        assert any(a.alert_id == "alert1" for a in active)
        assert any(a.alert_id == "alert2" for a in active)

    def test_get_alerts_by_rule(self, storage):
        """Test retrieving alerts by rule name"""
        for i in range(3):
            alert = Alert(
                alert_id=f"alert{i}",
                rule_name="test_rule",
                state=AlertState.TRIGGERED,
                severity="warning",
                metric_name="cpu",
                metric_value=85.0,
                threshold=80.0,
                triggered_at=datetime.now(),
            )
            storage.save_alert(alert)

        alerts = storage.get_alerts_by_rule("test_rule")
        assert len(alerts) == 3

    def test_cleanup_old_alerts(self, storage):
        """Test cleaning up old alerts"""
        # Create old resolved alert
        old_alert = Alert(
            alert_id="old_alert",
            rule_name="rule1",
            state=AlertState.RESOLVED,
            severity="warning",
            metric_name="cpu",
            metric_value=85.0,
            threshold=80.0,
            triggered_at=datetime.now() - timedelta(days=40),
            resolved_at=datetime.now() - timedelta(days=35),
        )

        # Create recent alert
        recent_alert = Alert(
            alert_id="recent_alert",
            rule_name="rule2",
            state=AlertState.RESOLVED,
            severity="warning",
            metric_name="memory",
            metric_value=85.0,
            threshold=80.0,
            triggered_at=datetime.now() - timedelta(days=5),
            resolved_at=datetime.now() - timedelta(days=4),
        )

        storage.save_alert(old_alert)
        storage.save_alert(recent_alert)

        # Cleanup alerts older than 30 days
        deleted = storage.cleanup_old_alerts(30)
        assert deleted == 1

        # Verify old alert is gone
        assert storage.get_alert("old_alert") is None
        # Verify recent alert still exists
        assert storage.get_alert("recent_alert") is not None
