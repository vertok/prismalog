"""
Logging functionality for the prismalog package.

This module provides a high-performance, feature-rich logging system designed
specifically for multiprocessing and multithreading environments. It extends
Python's standard logging with colored output, automatic log rotation, and
improved handling of critical errors.

Key components:
- ColoredFormatter: Adds color-coding to console output based on log levels
- MultiProcessingLog: Thread-safe and process-safe log handler with rotation support
- CriticalExitHandler: Optional handler that exits the program on critical errors
- ColoredLogger: Main logger class with enhanced functionality
- get_logger: Factory function to obtain properly configured loggers

Features:
- Up to 29K msgs/sec in multiprocessing mode
- Colored console output for improved readability
- Automatic log file rotation based on size
- Process-safe and thread-safe logging
- Special handling for critical errors
- Configurable verbosity levels for different modules
- Zero external dependencies

Example:
    >>> from prismalog import get_logger
    >>> logger = get_logger("my_module")
    >>> logger.info("Application started")
    >>> logger.debug("Detailed debugging information")
    >>> logger.error("Something went wrong")
"""
import os
import sys
import time
import logging
from typing import Any, Dict, Optional
from datetime import datetime
from multiprocessing import Lock
from logging.handlers import RotatingFileHandler
from .config import LoggingConfig


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds ANSI color codes to log level names in console output.

    This enhances readability by color-coding log messages based on their severity:
      - DEBUG: Blue
      - INFO: Green
      - WARNING: Yellow
      - ERROR: Red
      - CRITICAL: Bright Red

    Colors are only applied when the formatter is initialized with colored=True
    and when the output stream supports ANSI color codes.

    Args:
        fmt: Format string for log messages
        datefmt: Format string for dates
        style: Style of the format string ('%', '{', or '$')
        colored: Whether to apply ANSI color codes to level names
    """
    # ANSI color codes
    COLORS = {
        'DEBUG':    '\033[94m',         # Blue
        'INFO':     '\033[92m',         # Green
        'WARNING':  '\033[93m',         # Yellow
        'ERROR':    '\033[91m',         # Red
        'CRITICAL': '\033[91m\033[1m',  # Bright Red
    }
    RESET =         '\033[0m'           # Reset color

    def __init__(self, fmt=None, datefmt=None, style='%', colored=True):
        super().__init__(fmt, datefmt, style)
        self.colored = colored

    def format(self, record):
        # Save the original levelname
        original_levelname = record.levelname

        if self.colored and original_levelname in self.COLORS:
            # Add color to the levelname
            record.levelname = f"{self.COLORS[original_levelname]}{record.levelname}{self.RESET}"

        # Use the original formatter to do the formatting
        result = super().format(record)

        # Restore the original levelname
        record.levelname = original_levelname

        return result

class MultiProcessingLog(logging.Handler):
    """
    Thread-safe and process-safe logging handler based on RotatingFileHandler.

    This handler ensures consistent log file access across multiple processes
    by using a Lock to coordinate file operations. It automatically handles log
    file rotation and ensures all processes write to the current active log file.
    """
    # Class-level lock shared across all instances
    _file_lock = Lock()
    # Track the active log file across all processes
    _active_log_file = None

    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0):
        logging.Handler.__init__(self)
        self.filename = filename
        self.mode = mode
        self.maxBytes = maxBytes        # pylint: disable=invalid-name
        self.backupCount = backupCount  # pylint: disable=invalid-name
        self._handler = None

        # Update the class-level active log file
        with self.__class__._file_lock:
            self.__class__._active_log_file = filename

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Create the rotating file handler
        self._create_handler()

    def _create_handler(self):
        """Create or recreate the underlying rotating file handler"""
        # Close existing handler if it exists
        if hasattr(self, '_handler') and self._handler:
            try:
                self._handler.close()
            except:
                pass

        # Create new handler
        self._handler = RotatingFileHandler(
            self.filename,
            self.mode,
            self.maxBytes,
            self.backupCount
        )

        # Copy the formatter if one is set for the handler
        if hasattr(self, 'formatter') and self.formatter:
            self._handler.setFormatter(self.formatter)

    def emit(self, record):
        """Process a log record and write it to the log file."""
        # Use the lock to prevent concurrent writes
        with self.__class__._file_lock:
            # Always check if the filename matches the current active log file
            if self.filename != self.__class__._active_log_file:
                # Another process has created a new log file, switch to it
                self.filename = self.__class__._active_log_file
                self._create_handler()

            # Now emit the record
            try:
                # Check if rotation needed before emitting
                if self.maxBytes > 0 and os.path.exists(self.filename):
                    try:
                        # Check file size
                        size = os.path.getsize(self.filename)
                        if size >= self.maxBytes:
                            self.doRollover()
                    except:
                        # If checking size fails, continue with emit
                        pass

                self._handler.emit(record)
            except Exception:
                # If any error occurs, try to recreate the handler
                self._create_handler()

                try:
                    self._handler.emit(record)
                except:
                    self.handleError(record)

    def close(self):
        self._handler.close()
        logging.Handler.close(self)

    def setFormatter(self, fmt):
        logging.Handler.setFormatter(self, fmt)
        if hasattr(self, '_handler') and self._handler:
            self._handler.setFormatter(fmt)

    def doRollover(self):  # pylint: disable=invalid-name
        """Force a rollover and create a new log file"""
        with self.__class__._file_lock:
            try:
                # First, let the RotatingFileHandler do its rollover
                self._handler.doRollover()

                # Log files with rotation typically use pattern: filename.1, filename.2, etc.
                # Ensure all processes start using the new (empty) log file
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                unique_suffix = str(os.getpid() % 10000)  # Use last 4 digits of PID for uniqueness
                log_dir = os.path.dirname(self.filename)
                new_filename = os.path.join(log_dir, f'app_{timestamp}_{unique_suffix}.log')

                # Update the filename used by this instance
                self.filename = new_filename

                # Update the class-level active log file for all processes
                self.__class__._active_log_file = new_filename

                # Create a new handler with the new file
                self._create_handler()

                # Log the rotation event to the new file
                record = logging.LogRecord(
                    name="LogRotation",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="Log file rotated",
                    args=(),
                    exc_info=None
                )
                # Emit directly using the handler to avoid recursion
                self._handler.emit(record)

            except Exception as e:
                # If rotation fails, log the error but continue
                LoggingConfig._debug_print(f"Error during log rotation: {e}")

    def __repr__(self):
        """
        Return a string representation of the MultiProcessingLog instance.

        This includes the current log level name and the filename being used
        for logging, which can be helpful for debugging.

        Returns:
            str: A string representation of the instance.
        """
        return f"<MultiProcessingLog ({self.level_name})>"

    @property
    def level_name(self):
        """
        Get the name of the current log level.

        This property retrieves the human-readable name of the log level
        (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") based on
        the numeric log level value.

        Returns:
            str: The name of the current log level.
        """
        return logging.getLevelName(self.level)

class CriticalExitHandler(logging.Handler):
    """
    Handler that exits the program when a critical message is logged.

    This handler only processes CRITICAL level log messages. When such a message
    is received, it checks the exit_on_critical configuration setting and calls
    sys.exit(1) if enabled.

    The handler can be temporarily disabled for testing purposes.

    Class methods:
        disable_exit(): Temporarily disable program exit on critical logs
        enable_exit(): Re-enable program exit on critical logs
    """
    # Class variable to disable exit functionality for tests
    _exit_disabled = False

    def __init__(self):
        super().__init__(level=logging.CRITICAL)

    @classmethod
    def disable_exit(cls, disable=True):
        """
        Control exit functionality for testing.

        When exits are disabled, critical logs will not cause the program to
        terminate, allowing tests to safely check critical error paths.

        Args:
            disable: If True (default), disable exits. If False, enable exits.
        """
        cls._exit_disabled = disable

    @classmethod
    def enable_exit(cls):
        """Re-enable exit functionality after testing."""
        cls._exit_disabled = False

    def emit(self, record):
        # First check if explicitly disabled for tests
        if self.__class__._exit_disabled:
            return

        # If set to True, critical log will lead to system exit
        exit_on_critical = LoggingConfig.get("exit_on_critical", True)

        # Exit if configured to do so (and not disabled)
        if exit_on_critical:
            sys.exit(1)

class ColoredLogger:
    """
    Custom logger that adds colors to console output and supports multiprocess logging.

    This class wraps the standard Python logging functionality with additional features:
    - Colored console output for improved readability
    - File logging with automatic rotation
    - Multi-process safe logging
    - Configurable critical message behavior

    This is the main logging class used by the prismalog package. Users
    should generally not instantiate this directly but use get_logger() instead.

    Args:
        name: The logger name, typically __name__ or a module name
        verbose: Optional log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Class-level attributes for shared resources
    _initialized_loggers: Dict[str, 'ColoredLogger'] = {}
    _log_file_path: Optional[str] = None
    _file_handler: Optional[MultiProcessingLog] = None
    _root_logger: Optional[logging.Logger] = None
    _loggers: Dict[str, 'ColoredLogger'] = {}

    def __init__(self, name: str, verbose: Optional[str] = None) -> None:
        """Initialize logger with name and verbosity level."""
        self.name = name

        # Store the configured level (for tests and console output)
        self._configured_level = LoggingConfig.get_level(name, verbose)

        # Set up the logger
        self.logger = self._setup_logger()

        # Only add CriticalExitHandler if configured to exit on critical
        exit_on_critical = LoggingConfig.get("exit_on_critical", True)
        if exit_on_critical:
            # Add the handler that will exit on critical
            self.handlers.append(CriticalExitHandler())
            self.logger.addHandler(self.handlers[-1])

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with handlers and formatters."""
        # Get or create the logger
        logger = logging.getLogger(self.name)
        logger.propagate = False  # Don't propagate to parent loggers
        logger.setLevel(logging.DEBUG)

        # Always clean up any existing handlers to avoid duplicates
        if logger.handlers:
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

        # Add handlers to the logger
        self._add_handlers_to_logger(logger)

        # Store in initialized loggers dictionary
        self.__class__._initialized_loggers[self.name] = self

        return logger

    def _add_handlers_to_logger(self, logger: logging.Logger) -> None:
        """Add necessary handlers to the logger."""

        # Console handler (colored output)
        ch = logging.StreamHandler(sys.stdout)

        # Check for explicit console_level in config first, otherwise use self.level
        console_level_name = LoggingConfig.get("console_level", None)
        if console_level_name is not None:
            console_level = LoggingConfig.map_level(console_level_name)
            ch.setLevel(console_level)
        else:
            ch.setLevel(self.level)

        ch.setFormatter(ColoredFormatter(
            '%(asctime)s - %(filename)s - %(name)s - [%(levelname)s] - %(message)s',
            colored=LoggingConfig.get("colored_console", True)  # Use config for colored output
        ))
        logger.addHandler(ch)

        # File handler (all levels, no color, saved with timestamp)
        if not self.__class__._file_handler:
            self.__class__._file_handler = self.__class__._setup_file_handler()
        logger.addHandler(self.__class__._file_handler)

    @classmethod
    def _setup_file_handler(cls, log_file_path=None):
        """Set up the file handler for logging to a file."""
        # If a file handler already exists and no specific path is requested,
        # return the existing handler
        if cls._file_handler and not log_file_path:
            return cls._file_handler

        # Always ensure a log file path exists
        if log_file_path is None:
            # Get log directory from config
            log_dir = LoggingConfig.get("log_dir", "logs")
            os.makedirs(log_dir, exist_ok=True)

            # Use seconds precision with unique suffix for log file names
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            unique_suffix = str(os.getpid() % 1000)  # Use last 3 digits of PID for uniqueness
            log_file_path = os.path.join(log_dir, f'app_{timestamp}_{unique_suffix}.log')

        # Update the class-level log file path
        cls._log_file_path = log_file_path

        # Create the file handler with configured rotation settings
        disable_rotation = LoggingConfig.get("disable_rotation", False)

        # Check both config and environment variable
        if disable_rotation or os.environ.get('LOG_DISABLE_ROTATION') == '1':
            # For performance tests, disable rotation completely
            LoggingConfig._debug_print("Log rotation is disabled")
            handler = MultiProcessingLog(log_file_path, 'a', 0, 0)  # No rotation
        else:
            # Calculate rotation size in bytes (ensure it's not zero)
            rotation_size_mb = LoggingConfig.get("rotation_size_mb", 10)
            rotation_size_bytes = max(1024, int(rotation_size_mb * 1024 * 1024))  # At least 1KB

            # Get backup count (ensure it's at least 1)
            backup_count = max(1, LoggingConfig.get("backup_count", 5))

            # Create handler with explicit rotation parameters
            LoggingConfig._debug_print(
                "Setting up log rotation: "
                f"maxSize={rotation_size_bytes} bytes ({rotation_size_mb}MB), "
                f"backups={backup_count}"
            )
            handler = MultiProcessingLog(log_file_path, 'a', rotation_size_bytes, backup_count)

        # Use format from config
        log_format = LoggingConfig.get("log_format",
                     "%(asctime)s - %(filename)s - %(name)s - [%(levelname)s] - %(message)s")

        handler.setFormatter(ColoredFormatter(
            log_format,
            colored=False
        ))
        handler.setLevel(logging.DEBUG)  # File handler always uses DEBUG
        return handler

    @classmethod
    def reset(cls, new_file=False):
        """
        Reset all active loggers and optionally create a new log file.

        This method is useful when reconfigure logging is required or when
        testing different logging configurations. It closes all existing handlers,
        clears the internal registry, and optionally creates a new log file.

        Args:
            new_file: If True, generate a new unique log file. If False, reuse the existing one.

        Returns:
            str: The path to the active log file
        """
        # Store logger names before clearing
        logger_names = list(cls._initialized_loggers.keys())

        # Remove all initialized loggers
        for name in logger_names:
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass

        # Clear the initialized loggers dictionary
        cls._initialized_loggers.clear()

        # Close and clear the shared file handler
        if cls._file_handler:
            try:
                cls._file_handler.close()
            except Exception:
                pass
            cls._file_handler = None

        # For test_logger_reset test, ensure a different path is generated
        if new_file:
            # ensure CLI args have been processed
            log_dir = LoggingConfig.get("log_dir", "logs")

            # Make absolute path if needed
            if not os.path.isabs(log_dir):
                log_dir = os.path.abspath(log_dir)

            os.makedirs(log_dir, exist_ok=True)

            # Use time.time() to ensure uniqueness, even for fast successive calls
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            unique_suffix = str(int(time.time() * 1000) % 10000)  # Use milliseconds as unique ID
            cls._log_file_path = os.path.join(log_dir, f'app_{timestamp}_{unique_suffix}.log')

        # Create a new file handler
        if cls._file_handler is None:
            cls._file_handler = cls._setup_file_handler(cls._log_file_path)

        # Reinitialize loggers that were previously registered
        for name in logger_names:
            get_logger(name)

        return cls._log_file_path

    @classmethod
    def update_logger_level(cls, name, level):
        """
        Update the log level of an existing logger.

        This allows dynamically changing the verbosity of a specific logger
        at runtime, which is useful for focusing on specific components during
        debugging or reducing noise from verbose components.

        Args:
            name: Name of the logger to update
            level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if name in cls._initialized_loggers:
            logger_instance = cls._initialized_loggers[name]
            level_value = LoggingConfig.map_level(level)

            # Update the level in both the wrapper and the underlying logger
            logger_instance.level = level_value
            logger_instance.logger.setLevel(level_value)

            # Update console handler level
            for handler in logger_instance.handlers:
                # Check if the handler is a StreamHandler but not a CriticalExitHandler
                is_stream_handler = isinstance(handler, logging.StreamHandler)
                is_not_critical_exit_handler = not isinstance(handler, CriticalExitHandler)

                if is_stream_handler and is_not_critical_exit_handler:
                    handler.setLevel(level_value)

    @property
    def handlers(self):
        """Return the handlers from the underlying logger."""
        return self.logger.handlers

    @property
    def level(self):
        """Return the effective level for the logger (for testing)."""
        # This abstracts the implementation details from the tests
        # For tests, report the configured level, not the actual logger level
        return self._configured_level

    @level.setter
    def level(self, value):
        """Set the configured level and update console handlers."""
        self._configured_level = value

        # Update console handlers only
        if hasattr(self, 'logger') and self.logger:
            for handler in self.logger.handlers:
                is_stream_handler = isinstance(handler, logging.StreamHandler)
                is_not_multiprocessing_log = not isinstance(handler, MultiProcessingLog)

                if is_stream_handler and is_not_multiprocessing_log:
                    handler.setLevel(value)

    # Logger methods - delegate to the underlying logger
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs a debug message."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an info message."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs a warning message."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an error message."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a critical message.
        Note: If exit_on_critical=True in config (default), this will terminate the program.
        """
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an exception message."""
        self.logger.exception(msg, *args, **kwargs)

# At module level
_EXTERNAL_LOGGERS_CONFIGURED = False

def get_logger(name: str, verbose: Optional[str] = None) -> ColoredLogger:
    """
    Get a configured logger instance.

    Creates a new logger or returns an existing one with the given name.
    The logger includes colored console output and file logging with
    automatic rotation.

    Args:
        name: The name of the logger, usually __name__ or module name
        verbose: Optional override for log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                 If not provided, uses the level from configuration

    Returns:
        A ColoredLogger instance configured according to settings

    Examples:
        >>> logger = get_logger("my_module")
        >>> logger.info("Application started")

        >>> debug_logger = get_logger("debug_module", "DEBUG")
        >>> debug_logger.debug("Detailed information")
    """
    global _EXTERNAL_LOGGERS_CONFIGURED
    # Configure external loggers if they haven't been configured yet
    if not _EXTERNAL_LOGGERS_CONFIGURED:
        configure_external_loggers()
        _EXTERNAL_LOGGERS_CONFIGURED = True

    # Check if logger already exists
    if name in ColoredLogger._initialized_loggers:
        # Check if there's a specific config for this logger in external_loggers
        external_loggers = LoggingConfig.get("external_loggers", {})
        if name in external_loggers and verbose is None:
            # Update the existing logger with the configured level
            ColoredLogger.update_logger_level(name, external_loggers[name])
        return ColoredLogger._initialized_loggers[name]

    # Use explicit level, then check external_loggers config, then use default
    if verbose is None:
        external_loggers = LoggingConfig.get("external_loggers", {})
        if name in external_loggers:
            verbose = external_loggers[name]
        else:
            verbose = LoggingConfig.get("default_level", "INFO")

    # Create new logger
    logger = ColoredLogger(name, verbose)
    return logger

def configure_external_loggers():
    """
    Configure log levels for external packages based on configuration.

    This adjusts the verbosity of third-party libraries based on the 'external_loggers'
    section of the configuration. This is useful for reducing noise from verbose
    libraries while maintaining detailed logging.

    The configuration looks like:
        ```yaml
        external_loggers:
        nltk: WARNING
        urllib3: ERROR
        requests: INFO
        ```

    This function is automatically called when get_logger is first called,
    ensuring all external libraries are properly configured before any logging happens.
    """
    # Get external loggers configuration from LoggingConfig
    external_loggers = LoggingConfig.get("external_loggers", {})

    # Apply configuration to each logger specified in config
    for logger_name, level in external_loggers.items():
        # Get the root logger for the package
        package_logger = logging.getLogger(logger_name)

        level_value = LoggingConfig.map_level(level)

        # Set the level for this package's root logger
        package_logger.setLevel(level_value)

        # For all packages, ensure propagation is properly set
        package_logger.propagate = False

        # Only add a handler if there are none
        if not package_logger.handlers:
            # Simple handler to capture messages
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter('%(name)s - [%(levelname)s] - %(message)s'))
            handler.setLevel(level_value)
            package_logger.addHandler(handler)
