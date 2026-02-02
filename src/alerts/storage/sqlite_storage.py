"""
SQLite storage backend for alert history.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from src.alerts.storage.base_storage import BaseStorage, Alert, AlertState

logger = logging.getLogger(__name__)


class SQLiteStorage(BaseStorage):
    """SQLite implementation of alert storage"""

    def __init__(self, config: Dict):
        """
        Initialize SQLite storage.

        Args:
            config: Storage configuration dict with 'sqlite_path' key
        """
        self.db_path = config.get('sqlite_path', './data/alerts.db')
        self.retention_days = config.get('retention_days', 30)

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.conn = None
        self._init_db()

        logger.info(f"Initialized SQLite storage at {self.db_path}")

    def _init_db(self):
        """Create database tables and indexes"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        self.conn.execute("PRAGMA journal_mode=WAL")

        # Create alert_history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id VARCHAR(255) NOT NULL,
                rule_name VARCHAR(255) NOT NULL,
                state VARCHAR(20) NOT NULL,
                severity VARCHAR(20),
                metric_name VARCHAR(255),
                metric_value REAL,
                threshold REAL,
                labels TEXT,
                annotations TEXT,
                triggered_at TIMESTAMP NOT NULL,
                resolved_at TIMESTAMP,
                last_notified_at TIMESTAMP,
                notification_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_id ON alert_history(alert_id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_state ON alert_history(state)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_triggered_at ON alert_history(triggered_at)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rule_name ON alert_history(rule_name)"
        )

        self.conn.commit()

    def save_alert(self, alert: Alert) -> None:
        """Save a new alert"""
        try:
            data = alert.to_dict()

            self.conn.execute("""
                INSERT INTO alert_history (
                    alert_id, rule_name, state, severity, metric_name,
                    metric_value, threshold, labels, annotations,
                    triggered_at, resolved_at, last_notified_at, notification_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['alert_id'],
                data['rule_name'],
                data['state'],
                data['severity'],
                data['metric_name'],
                data['metric_value'],
                data['threshold'],
                data['labels'],
                data['annotations'],
                data['triggered_at'],
                data['resolved_at'],
                data['last_notified_at'],
                data['notification_count'],
            ))

            self.conn.commit()
            logger.debug(f"Saved alert: {alert.alert_id}")

        except sqlite3.Error as e:
            logger.error(f"Failed to save alert {alert.alert_id}: {e}")
            self.conn.rollback()
            raise

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Retrieve alert by ID (most recent)"""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM alert_history
                WHERE alert_id = ?
                ORDER BY triggered_at DESC
                LIMIT 1
            """, (alert_id,))

            row = cursor.fetchone()
            if row:
                return Alert.from_dict(dict(row))
            return None

        except sqlite3.Error as e:
            logger.error(f"Failed to get alert {alert_id}: {e}")
            return None

    def update_alert_state(self, alert_id: str, state: str,
                          resolved_at: Optional[datetime] = None) -> None:
        """Update alert state"""
        try:
            if resolved_at:
                self.conn.execute("""
                    UPDATE alert_history
                    SET state = ?, resolved_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE alert_id = ? AND resolved_at IS NULL
                """, (state, resolved_at.isoformat(), alert_id))
            else:
                self.conn.execute("""
                    UPDATE alert_history
                    SET state = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE alert_id = ? AND resolved_at IS NULL
                """, (state, alert_id))

            self.conn.commit()
            logger.debug(f"Updated alert {alert_id} state to {state}")

        except sqlite3.Error as e:
            logger.error(f"Failed to update alert state {alert_id}: {e}")
            self.conn.rollback()
            raise

    def update_notification_info(self, alert_id: str, notified_at: datetime) -> None:
        """Update notification information"""
        try:
            self.conn.execute("""
                UPDATE alert_history
                SET last_notified_at = ?,
                    notification_count = notification_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE alert_id = ? AND resolved_at IS NULL
            """, (notified_at.isoformat(), alert_id))

            self.conn.commit()
            logger.debug(f"Updated notification info for {alert_id}")

        except sqlite3.Error as e:
            logger.error(f"Failed to update notification info {alert_id}: {e}")
            self.conn.rollback()
            raise

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM alert_history
                WHERE state IN (?, ?)
                AND resolved_at IS NULL
                ORDER BY triggered_at DESC
            """, (AlertState.TRIGGERED, AlertState.ACTIVE))

            alerts = []
            for row in cursor.fetchall():
                alerts.append(Alert.from_dict(dict(row)))

            return alerts

        except sqlite3.Error as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []

    def get_alerts_by_rule(self, rule_name: str, limit: int = 100) -> List[Alert]:
        """Get recent alerts for a specific rule"""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM alert_history
                WHERE rule_name = ?
                ORDER BY triggered_at DESC
                LIMIT ?
            """, (rule_name, limit))

            alerts = []
            for row in cursor.fetchall():
                alerts.append(Alert.from_dict(dict(row)))

            return alerts

        except sqlite3.Error as e:
            logger.error(f"Failed to get alerts for rule {rule_name}: {e}")
            return []

    def cleanup_old_alerts(self, days: int) -> int:
        """Delete alerts older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            cursor = self.conn.execute("""
                DELETE FROM alert_history
                WHERE triggered_at < ?
                AND state = ?
            """, (cutoff_date.isoformat(), AlertState.RESOLVED))

            deleted_count = cursor.rowcount
            self.conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old alerts (>{days} days)")

            return deleted_count

        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup old alerts: {e}")
            self.conn.rollback()
            return 0

    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
                logger.debug("Closed SQLite connection")
            except sqlite3.Error as e:
                logger.error(f"Error closing SQLite connection: {e}")
