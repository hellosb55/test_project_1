"""Tests for AlertRule data class and loading"""

import pytest
import tempfile
import os
from pathlib import Path

from src.alerts.alert_rule import AlertRule, load_alert_rules


class TestAlertRule:
    """Test AlertRule data class"""

    def test_create_valid_rule(self):
        """Test creating a valid alert rule"""
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            operator=">",
            threshold=80.0,
            for_duration_minutes=5,
            severity="warning",
            channels=["email"],
        )

        assert rule.name == "test_rule"
        assert rule.metric_name == "test_metric"
        assert rule.operator == ">"
        assert rule.threshold == 80.0
        assert rule.enabled is True

    def test_invalid_operator(self):
        """Test that invalid operator raises error"""
        with pytest.raises(ValueError, match="Invalid operator"):
            AlertRule(
                name="test",
                metric_name="test",
                operator="??",
                threshold=80.0,
                for_duration_minutes=5,
                severity="warning",
                channels=["email"],
            )

    def test_invalid_severity(self):
        """Test that invalid severity raises error"""
        with pytest.raises(ValueError, match="Invalid severity"):
            AlertRule(
                name="test",
                metric_name="test",
                operator=">",
                threshold=80.0,
                for_duration_minutes=5,
                severity="extreme",
                channels=["email"],
            )

    def test_negative_duration(self):
        """Test that negative duration raises error"""
        with pytest.raises(ValueError, match="for_duration_minutes"):
            AlertRule(
                name="test",
                metric_name="test",
                operator=">",
                threshold=80.0,
                for_duration_minutes=-1,
                severity="warning",
                channels=["email"],
            )

    def test_no_channels(self):
        """Test that empty channels list raises error"""
        with pytest.raises(ValueError, match="At least one channel"):
            AlertRule(
                name="test",
                metric_name="test",
                operator=">",
                threshold=80.0,
                for_duration_minutes=5,
                severity="warning",
                channels=[],
            )

    def test_generate_alert_id(self):
        """Test alert ID generation"""
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            operator=">",
            threshold=80.0,
            for_duration_minutes=5,
            severity="warning",
            channels=["email"],
        )

        # Without labels
        alert_id = rule.generate_alert_id()
        assert alert_id == "test_rule"

        # With labels
        labels = {"host": "server1", "env": "prod"}
        alert_id = rule.generate_alert_id(labels)
        assert "test_rule" in alert_id
        assert "host=server1" in alert_id or "env=prod" in alert_id


class TestLoadAlertRules:
    """Test loading alert rules from YAML"""

    def test_load_valid_rules(self):
        """Test loading valid alert rules from YAML"""
        yaml_content = """
alert_rules:
  - name: "test_rule"
    metric_name: "cpu_usage"
    condition:
      operator: ">"
      threshold: 80.0
    for_duration_minutes: 5
    severity: "warning"
    channels:
      - email
    enabled: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            rules = load_alert_rules(temp_file)
            assert len(rules) == 1
            assert rules[0].name == "test_rule"
            assert rules[0].metric_name == "cpu_usage"
            assert rules[0].operator == ">"
            assert rules[0].threshold == 80.0
        finally:
            os.unlink(temp_file)

    def test_load_empty_file(self):
        """Test loading empty YAML file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            rules = load_alert_rules(temp_file)
            assert len(rules) == 0
        finally:
            os.unlink(temp_file)

    def test_load_missing_file(self):
        """Test loading non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_alert_rules("/nonexistent/file.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_alert_rules(temp_file)
        finally:
            os.unlink(temp_file)

    def test_load_multiple_rules(self):
        """Test loading multiple rules"""
        yaml_content = """
alert_rules:
  - name: "rule1"
    metric_name: "cpu"
    condition:
      operator: ">"
      threshold: 80
    for_duration_minutes: 5
    severity: "warning"
    channels: [email]
  - name: "rule2"
    metric_name: "memory"
    condition:
      operator: ">"
      threshold: 90
    for_duration_minutes: 10
    severity: "critical"
    channels: [slack]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            rules = load_alert_rules(temp_file)
            assert len(rules) == 2
            assert rules[0].name == "rule1"
            assert rules[1].name == "rule2"
        finally:
            os.unlink(temp_file)
