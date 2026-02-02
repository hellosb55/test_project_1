"""Utility helper functions"""

import socket
import platform


def get_hostname():
    """Get system hostname"""
    try:
        return socket.gethostname()
    except Exception:
        return platform.node() or "unknown"


def format_bytes(bytes_value):
    """Format bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def safe_divide(a, b, default=0.0):
    """Safely divide two numbers, returning default if division by zero"""
    try:
        if b == 0:
            return default
        return a / b
    except (TypeError, ZeroDivisionError):
        return default


def calculate_rate(current, previous, interval):
    """Calculate rate per second from two counter values and time interval"""
    if previous is None or interval <= 0:
        return 0.0

    delta = current - previous
    # Handle counter reset (wrap-around)
    if delta < 0:
        delta = current

    return safe_divide(delta, interval)
