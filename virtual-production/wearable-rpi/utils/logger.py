"""
Logging Utilities Module
Provides centralized logging configuration and utilities
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
import colorlog


def setup_logging(config: dict) -> logging.Logger:
    """
    Setup logging configuration

    Args:
        config: Configuration dictionary

    Returns:
        Configured logger instance
    """
    # Get logging configuration
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_file = log_config.get('file', 'logs/wearable_sensor.log')
    max_size = log_config.get('max_size', 10485760)  # 10MB default
    backup_count = log_config.get('backup_count', 5)
    console_output = log_config.get('console_output', True)

    # Create logs directory if it doesn't exist
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers
    logger.handlers = []

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Console handler with color output
    if console_output:
        # Use colorlog for colored console output
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Log initial setup
    logger.info("=" * 60)
    logger.info(f"Logging initialized - Level: {log_level}")
    logger.info(f"Log file: {log_file if log_file else 'None'}")
    logger.info(f"Device ID: {config.get('system', {}).get('device_id', 'Unknown')}")
    logger.info("=" * 60)

    return logger


class EventLogger:
    """
    Specialized logger for behavior events
    """

    def __init__(self, log_file: str = "logs/events.log"):
        """
        Initialize event logger

        Args:
            log_file: Path to event log file
        """
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Create dedicated event logger
        self.logger = logging.getLogger('events')
        self.logger.setLevel(logging.INFO)

        # Create handler for event file
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5242880,  # 5MB
            backupCount=10
        )

        # JSON-like format for events
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def log_event(self, behavior: str, metadata: dict = None):
        """
        Log a behavior event

        Args:
            behavior: Behavior type
            metadata: Additional event metadata
        """
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'behavior': behavior,
            'metadata': metadata or {}
        }

        # Log as JSON string
        import json
        self.logger.info(json.dumps(event))

    def get_recent_events(self, count: int = 10) -> list:
        """
        Get recent events from log

        Args:
            count: Number of events to retrieve

        Returns:
            List of recent events
        """
        if not os.path.exists(self.log_file):
            return []

        events = []
        try:
            import json
            with open(self.log_file, 'r') as f:
                lines = f.readlines()[-count:]
                for line in lines:
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except:
                        continue
        except Exception as e:
            logging.error(f"Failed to read events: {e}")

        return events


class PerformanceLogger:
    """
    Logger for performance metrics
    """

    def __init__(self):
        """Initialize performance logger"""
        self.logger = logging.getLogger('performance')
        self.metrics = {}

    def log_metric(self, name: str, value: float, unit: str = ""):
        """
        Log a performance metric

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
        """
        self.metrics[name] = {
            'value': value,
            'unit': unit,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.logger.debug(f"Metric: {name} = {value} {unit}")

    def log_timing(self, name: str, duration: float):
        """
        Log timing information

        Args:
            name: Operation name
            duration: Duration in seconds
        """
        self.log_metric(name, duration * 1000, "ms")

    def get_metrics(self) -> dict:
        """
        Get all performance metrics

        Returns:
            Dictionary of metrics
        """
        return self.metrics.copy()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)