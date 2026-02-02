"""
Alert rule data structures and loading utilities.
"""

import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    metric_name: str
    operator: str  # >, <, >=, <=, ==, !=
    threshold: float
    for_duration_minutes: int
    severity: str  # info, warning, critical
    channels: List[str]
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    label_selector: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    cooldown_minutes: int = 15
    description: str = ""

    def __post_init__(self):
        """Validate rule configuration"""
        # Validate operator
        valid_operators = ['>', '<', '>=', '<=', '==', '!=']
        if self.operator not in valid_operators:
            raise ValueError(f"Invalid operator: {self.operator}. Must be one of {valid_operators}")

        # Validate severity
        valid_severities = ['info', 'warning', 'critical']
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}. Must be one of {valid_severities}")

        # Validate duration
        if self.for_duration_minutes < 0:
            raise ValueError(f"for_duration_minutes must be >= 0, got {self.for_duration_minutes}")

        # Validate cooldown
        if self.cooldown_minutes < 0:
            raise ValueError(f"cooldown_minutes must be >= 0, got {self.cooldown_minutes}")

        # Validate channels
        if not self.channels:
            raise ValueError("At least one channel must be specified")

    def generate_alert_id(self, labels: Optional[Dict[str, str]] = None) -> str:
        """
        Generate unique alert ID based on rule name and labels.

        Args:
            labels: Metric labels for this specific alert instance

        Returns:
            Unique alert ID string
        """
        label_str = ""
        if labels:
            # Sort for consistency
            sorted_labels = sorted(labels.items())
            label_str = "_".join(f"{k}={v}" for k, v in sorted_labels)

        if label_str:
            return f"{self.name}_{label_str}"
        return self.name


def load_alert_rules(rules_file: str) -> List[AlertRule]:
    """
    Load alert rules from YAML file.

    Args:
        rules_file: Path to YAML configuration file

    Returns:
        List of AlertRule objects

    Raises:
        FileNotFoundError: If rules file doesn't exist
        ValueError: If rules file has invalid format
    """
    try:
        with open(rules_file, 'r') as f:
            config = yaml.safe_load(f)

        if not config or 'alert_rules' not in config:
            logger.warning(f"No alert_rules found in {rules_file}")
            return []

        rules = []
        for rule_config in config['alert_rules']:
            try:
                # Extract condition
                condition = rule_config.get('condition', {})

                # Create rule object
                rule = AlertRule(
                    name=rule_config['name'],
                    metric_name=rule_config['metric_name'],
                    operator=condition.get('operator', '>'),
                    threshold=float(condition.get('threshold', 0)),
                    for_duration_minutes=rule_config.get('for_duration_minutes', 1),
                    severity=rule_config.get('severity', 'warning'),
                    channels=rule_config.get('channels', []),
                    enabled=rule_config.get('enabled', True),
                    labels=rule_config.get('labels', {}),
                    label_selector=rule_config.get('label_selector', {}),
                    annotations=rule_config.get('annotations', {}),
                    cooldown_minutes=rule_config.get('cooldown_minutes', 15),
                    description=rule_config.get('description', ''),
                )
                rules.append(rule)
                logger.debug(f"Loaded alert rule: {rule.name}")

            except (KeyError, ValueError) as e:
                logger.error(f"Failed to load rule {rule_config.get('name', 'unknown')}: {e}")
                continue

        logger.info(f"Loaded {len(rules)} alert rules from {rules_file}")
        return rules

    except FileNotFoundError:
        logger.error(f"Alert rules file not found: {rules_file}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file {rules_file}: {e}")
        raise ValueError(f"Invalid YAML format: {e}")
