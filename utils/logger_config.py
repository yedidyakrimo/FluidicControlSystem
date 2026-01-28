"""
Centralized logging configuration for Fluidic Control System
Provides consistent logging across all modules with configurable levels
"""

import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional


class RepeatedMessageFilter(logging.Filter):
    """
    Filter to suppress repeated identical messages within a time window
    Prevents spam from repeated "device not connected" messages
    """
    
    def __init__(self, time_window_seconds=5, max_repeats=3):
        """
        Args:
            time_window_seconds: Time window to track messages (default 5 seconds)
            max_repeats: Maximum number of identical messages to show (default 3)
        """
        super().__init__()
        self.time_window = timedelta(seconds=time_window_seconds)
        self.max_repeats = max_repeats
        self.message_history = defaultdict(list)  # message -> list of timestamps
    
    def filter(self, record):
        """Filter log records to suppress repeated messages"""
        message = record.getMessage()
        now = datetime.now()
        
        # Clean old entries
        cutoff = now - self.time_window
        if message in self.message_history:
            self.message_history[message] = [
                ts for ts in self.message_history[message] if ts > cutoff
            ]
        
        # Count occurrences in time window
        count = len(self.message_history[message])
        
        if count >= self.max_repeats:
            # Suppress this message
            return False
        
        # Record this message
        self.message_history[message].append(now)
        return True


def setup_logging(
    level: str = "WARNING",
    format_string: Optional[str] = None,
    suppress_repeats: bool = True
) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Default: WARNING (only warnings and errors)
        format_string: Custom format string for log messages
        suppress_repeats: Enable filter to suppress repeated messages (default True)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    
    # Default format
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create formatter
    formatter = logging.Formatter(format_string, datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    
    # Add filter to suppress repeated messages
    if suppress_repeats:
        repeat_filter = RepeatedMessageFilter(time_window_seconds=5, max_repeats=3)
        console_handler.addFilter(repeat_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set levels for specific loggers
    # Hardware modules: WARNING by default (can be overridden)
    logging.getLogger('hardware').setLevel(numeric_level)
    logging.getLogger('hardware.smu').setLevel(numeric_level)
    logging.getLogger('hardware.pump').setLevel(numeric_level)
    logging.getLogger('hardware.ni_daq').setLevel(numeric_level)
    
    # Experiment modules: WARNING by default
    logging.getLogger('experiments').setLevel(numeric_level)
    
    # GUI modules: WARNING by default
    logging.getLogger('gui').setLevel(numeric_level)
    
    # Utils: INFO by default (file operations are important)
    logging.getLogger('utils').setLevel(logging.INFO if numeric_level <= logging.INFO else numeric_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience function to set logging level at runtime
def set_logging_level(level: str) -> None:
    """
    Change logging level at runtime
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    logging.getLogger().setLevel(numeric_level)
    # Also update all child loggers
    for logger_name in ['hardware', 'experiments', 'gui', 'utils']:
        logging.getLogger(logger_name).setLevel(numeric_level)

