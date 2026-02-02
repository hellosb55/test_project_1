"""Configuration management"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


def get_default_config() -> Dict[str, Any]:
    """Get default configuration"""
    return {
        'agent': {
            'hostname': 'auto',
            'log_level': 'INFO',
            'log_file': None,
            'log_format': 'text',
        },
        'prometheus': {
            'port': 9100,
            'host': '0.0.0.0',
        },
        'collectors': {
            'cpu': {
                'enabled': True,
                'interval': 5,
                'per_cpu': True,
            },
            'memory': {
                'enabled': True,
                'interval': 5,
            },
            'disk': {
                'enabled': True,
                'usage_interval': 30,
                'io_interval': 5,
                'exclude_filesystems': ['tmpfs', 'devtmpfs', 'squashfs'],
                'exclude_mount_points': ['/snap'],
            },
            'network': {
                'enabled': True,
                'interval': 5,
                'exclude_interfaces': ['lo'],
                'collect_connections': True,
            },
            'process': {
                'enabled': True,
                'interval': 10,
                'top_n': 20,
                'include_threads': False,
            },
        },
        'resource_limits': {
            'max_cpu_percent': 2.0,
            'max_memory_mb': 50,
            'check_interval': 60,
            'action_on_exceed': 'log',  # log, disable_collectors, or stop
        },
    }


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from file and environment variables

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Configuration dictionary
    """
    # Start with defaults
    config = get_default_config()

    # Load from YAML file if provided
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    config = merge_configs(config, yaml_config)
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")

    # Override with environment variables
    config = override_from_env(config)

    # Validate configuration
    validate_config(config)

    return config


def merge_configs(base: Dict, override: Dict) -> Dict:
    """Recursively merge two configuration dictionaries"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def override_from_env(config: Dict) -> Dict:
    """Override configuration from environment variables"""

    # Agent settings
    if 'AGENT_HOSTNAME' in os.environ:
        config['agent']['hostname'] = os.environ['AGENT_HOSTNAME']
    if 'LOG_LEVEL' in os.environ:
        config['agent']['log_level'] = os.environ['LOG_LEVEL'].upper()
    if 'LOG_FILE' in os.environ:
        config['agent']['log_file'] = os.environ['LOG_FILE']
    if 'LOG_FORMAT' in os.environ:
        config['agent']['log_format'] = os.environ['LOG_FORMAT'].lower()

    # Prometheus settings
    if 'PROMETHEUS_PORT' in os.environ:
        config['prometheus']['port'] = int(os.environ['PROMETHEUS_PORT'])
    if 'PROMETHEUS_HOST' in os.environ:
        config['prometheus']['host'] = os.environ['PROMETHEUS_HOST']

    # Collector settings
    for collector in ['cpu', 'memory', 'disk', 'network', 'process']:
        env_prefix = f'COLLECTOR_{collector.upper()}'

        # Enabled flag
        enabled_key = f'{env_prefix}_ENABLED'
        if enabled_key in os.environ:
            config['collectors'][collector]['enabled'] = os.environ[enabled_key].lower() == 'true'

        # Interval
        interval_key = f'{env_prefix}_INTERVAL'
        if interval_key in os.environ:
            config['collectors'][collector]['interval'] = int(os.environ[interval_key])

    return config


def validate_config(config: Dict):
    """
    Validate configuration values

    Raises:
        ValueError: If configuration is invalid
    """
    # Validate Prometheus port
    port = config['prometheus']['port']
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid Prometheus port: {port}. Must be between 1 and 65535")

    # Validate log level
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_level = config['agent']['log_level'].upper()
    if log_level not in valid_log_levels:
        raise ValueError(f"Invalid log level: {log_level}. Must be one of {valid_log_levels}")

    # Validate collector intervals
    for collector_name, collector_config in config['collectors'].items():
        if collector_config.get('enabled', False):
            interval = collector_config.get('interval', 0)
            if interval <= 0:
                raise ValueError(f"Invalid interval for {collector_name}: {interval}. Must be > 0")

            # Warn if interval is too aggressive
            if interval < 1:
                import warnings
                warnings.warn(f"Collection interval for {collector_name} is very aggressive: {interval}s")

    # Validate process collector top_n
    if config['collectors']['process']['enabled']:
        top_n = config['collectors']['process']['top_n']
        if not (0 < top_n < 1000):
            raise ValueError(f"Invalid top_n for process collector: {top_n}. Must be between 1 and 999")

    # Validate resource limits
    max_cpu = config['resource_limits']['max_cpu_percent']
    if max_cpu <= 0:
        raise ValueError(f"Invalid max_cpu_percent: {max_cpu}. Must be > 0")

    max_memory = config['resource_limits']['max_memory_mb']
    if max_memory <= 0:
        raise ValueError(f"Invalid max_memory_mb: {max_memory}. Must be > 0")

    valid_actions = ['log', 'disable_collectors', 'stop']
    action = config['resource_limits']['action_on_exceed']
    if action not in valid_actions:
        raise ValueError(f"Invalid action_on_exceed: {action}. Must be one of {valid_actions}")
