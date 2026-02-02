"""Logging configuration"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger


def setup_logger(config):
    """
    Setup logger with configuration

    Args:
        config: Configuration dictionary with logging settings
    """
    log_level = config.get('agent', {}).get('log_level', 'INFO').upper()
    log_file = config.get('agent', {}).get('log_file')
    log_format = config.get('agent', {}).get('log_format', 'text')

    # Create root logger
    logger = logging.getLogger('agent')
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))

    if log_format == 'json':
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'levelname': 'level', 'name': 'logger', 'asctime': 'timestamp'}
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if configured)
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level, logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")

    return logger


def get_logger(name):
    """Get logger instance"""
    return logging.getLogger(f'agent.{name}')
