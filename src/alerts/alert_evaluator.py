"""
Alert evaluator for checking rule conditions against metrics.
"""

import logging
from typing import List
from prometheus_client import CollectorRegistry

from src.alerts.alert_rule import AlertRule
from src.alerts.alert_manager import AlertManager
from src.utils.metric_reader import MetricReader

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """Evaluates alert rules against current metrics"""

    def __init__(self, rules: List[AlertRule], registry: CollectorRegistry,
                 alert_manager: AlertManager):
        """
        Initialize alert evaluator.

        Args:
            rules: List of alert rules to evaluate
            registry: Prometheus CollectorRegistry for reading metrics
            alert_manager: AlertManager for processing alerts
        """
        self.rules = rules
        self.metric_reader = MetricReader(registry)
        self.alert_manager = alert_manager

        logger.info(f"Alert evaluator initialized with {len(rules)} rules")

    def evaluate_all_rules(self) -> None:
        """Evaluate all enabled rules against current metrics"""
        for rule in self.rules:
            if not rule.enabled:
                logger.debug(f"Skipping disabled rule: {rule.name}")
                continue

            try:
                self._evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}", exc_info=True)

    def _evaluate_rule(self, rule: AlertRule) -> None:
        """
        Evaluate a single rule.

        Args:
            rule: Alert rule to evaluate
        """
        # Read metric values
        metric_values = self.metric_reader.get_metric_value(
            rule.metric_name,
            rule.label_selector
        )

        if not metric_values:
            logger.debug(f"No metric values found for rule {rule.name} (metric: {rule.metric_name})")
            return

        # Evaluate condition for each label combination
        for value, labels in metric_values:
            condition_met = self._evaluate_condition(rule, value)

            if condition_met:
                # Alert condition is true
                logger.debug(f"Rule {rule.name} condition met: {value} {rule.operator} {rule.threshold}")
                self.alert_manager.process_alert(rule, value, labels)
            else:
                # Alert condition is false - check if we should resolve
                logger.debug(f"Rule {rule.name} condition not met: {value} {rule.operator} {rule.threshold}")
                self.alert_manager.resolve_alert(rule, labels)

    def _evaluate_condition(self, rule: AlertRule, value: float) -> bool:
        """
        Evaluate rule condition against metric value.

        Args:
            rule: Alert rule with operator and threshold
            value: Current metric value

        Returns:
            True if condition is met, False otherwise
        """
        operators = {
            '>': lambda v, t: v > t,
            '<': lambda v, t: v < t,
            '>=': lambda v, t: v >= t,
            '<=': lambda v, t: v <= t,
            '==': lambda v, t: v == t,
            '!=': lambda v, t: v != t,
        }

        operator_func = operators.get(rule.operator)
        if not operator_func:
            logger.error(f"Unknown operator: {rule.operator}")
            return False

        try:
            return operator_func(value, rule.threshold)
        except Exception as e:
            logger.error(f"Error evaluating condition for rule {rule.name}: {e}")
            return False

    def add_rule(self, rule: AlertRule) -> None:
        """
        Add a new rule to the evaluator.

        Args:
            rule: Alert rule to add
        """
        self.rules.append(rule)
        logger.info(f"Added new alert rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove a rule by name.

        Args:
            rule_name: Name of rule to remove

        Returns:
            True if rule was removed, False if not found
        """
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                logger.info(f"Removed alert rule: {rule_name}")
                return True

        logger.warning(f"Rule not found: {rule_name}")
        return False

    def get_rule_count(self) -> int:
        """Get total number of rules"""
        return len(self.rules)

    def get_enabled_rule_count(self) -> int:
        """Get number of enabled rules"""
        return sum(1 for rule in self.rules if rule.enabled)
