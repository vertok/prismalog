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

import logging
import os
import sys
import time
from datetime import datetime
from logging import LogRecord, StreamHandler
from logging.handlers import RotatingFileHandler
from multiprocessing import Lock
from types import FrameType
from typing import Any, Dict, List, Literal, Optional, Type, Union, cast

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
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[91m\033[1m",  # Bright Red
    }
    RESET = "\033[0m"  # Reset color

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: Literal["%", "{", "$"] = "%",
        colored: bool = True,
    ) -> None:
        """
        Initialize the ColoredFormatter.

        Args:
            fmt: Format string for log messages
            datefmt: Format string for dates
            style: Style of the format string ('%', '{', or '$')
            colored: Whether to apply ANSI color codes to level names
        """
        super().__init__(fmt, datefmt, style)
        self.colored = colored

    def format(self, record: LogRecord) -> str:
        """Format log record with optional color coding."""
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
    file_lock = Lock()
    # Track the active log file across all processes
    active_log_file = None

    def __init__(self, filename: str, mode: str = "a", maxBytes: int = 0, backupCount: int = 0) -> None:
        """
        Initialize the handler with the specified file and rotation settings.

        Args:
            filename: Path to the log file
            mode: File opening mode
            maxBytes: Maximum size in bytes before rotation
            backupCount: Number of backup files to keep
        """
        logging.Handler.__init__(self)
        self.filename = filename
        self.mode = mode
        self.maxBytes = maxBytes  # pylint: disable=invalid-name
        self.backupCount = backupCount  # pylint: disable=invalid-name
        self._handler: Optional[RotatingFileHandler] = None  # Add type annotation

        # Update the class-level active log file
        with self.__class__.file_lock:
            self.__class__.active_log_file = filename

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Create the rotating file handler
        self._create_handler()

    def _create_handler(self) -> None:
        """Create or recreate the underlying rotating file handler"""
        # Close existing handler if it exists
        if hasattr(self, "_handler") and self._handler is not None:
            try:
                self._handler.close()
            except (IOError, OSError) as e:
                # Most likely errors when closing a handler are I/O related
                LoggingConfig.debug_print(f"Warning: I/O error closing log handler: {e}")
            except ValueError as e:
                # ValueError can happen if handler is already closed
                LoggingConfig.debug_print(f"Warning: Handler already closed: {e}")
            except Exception as e:
                # Fallback for unexpected errors, with specific error type
                LoggingConfig.debug_print(
                    f"Warning: Unexpected error ({type(e).__name__}) " f"closing log handler: {e}"
                )

        # Create new handler
        self._handler = RotatingFileHandler(self.filename, self.mode, self.maxBytes, self.backupCount)

        # Copy the formatter if one is set for the handler
        if hasattr(self, "formatter") and self.formatter:
            self._handler.setFormatter(self.formatter)

    def emit(self, record: LogRecord) -> None:
        """Process a log record and write it to the log file."""
        # Use the lock to prevent concurrent writes
        with self.__class__.file_lock:
            # Always check if the filename matches the current active log file
            if self.filename != self.__class__.active_log_file:
                # Another process has created a new log file, switch to it
                if self.__class__.active_log_file is not None:
                    self.filename = self.__class__.active_log_file
                self._create_handler()

            # Ensure handler exists
            if self._handler is None:
                self._create_handler()

            # Now emit the record
            try:
                # Check if rotation needed before emitting
                if self.maxBytes > 0 and os.path.exists(self.filename):
                    try:
                        # Check file size
                        size = os.path.getsize(self.filename)
                        if size >= self.maxBytes and self._handler is not None:
                            self.doRollover()
                    except:
                        # If checking size fails, continue with emit
                        pass

                if self._handler is not None:
                    self._handler.emit(record)
            except Exception:
                # If any error occurs, try to recreate the handler
                self._create_handler()

                try:
                    if self._handler is not None:
                        self._handler.emit(record)
                    else:
                        self.handleError(record)
                except:
                    self.handleError(record)

    def close(self) -> None:
        """Close the file handler."""
        if self._handler is not None:
            self._handler.close()
        logging.Handler.close(self)

    def setFormatter(self, fmt: Optional[logging.Formatter]) -> None:
        """Set formatter for the handler and underlying rotating handler."""
        logging.Handler.setFormatter(self, fmt)
        if hasattr(self, "_handler") and self._handler is not None and fmt is not None:
            self._handler.setFormatter(fmt)

    def doRollover(self) -> None:  # pylint: disable=invalid-name
        """Force a rollover and create a new log file"""
        with self.__class__.file_lock:
            try:
                # First, ensure handler exists
                if self._handler is None:
                    self._create_handler()

                # Let the RotatingFileHandler do its rollover if it exists
                if self._handler is not None:
                    self._handler.doRollover()

                # Log files with rotation typically use pattern: filename.1, filename.2, etc.
                # Ensure all processes start using the new (empty) log file
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                unique_suffix = str(os.getpid() % 10000)  # Use last 4 digits of PID for uniqueness
                log_dir = os.path.dirname(self.filename)
                new_filename = os.path.join(log_dir, f"app_{timestamp}_{unique_suffix}.log")

                # Update the filename used by this instance
                self.filename = new_filename

                # Update the class-level active log file for all processes
                self.__class__.active_log_file = new_filename

                # Create a new handler with the new file
                self._create_handler()

                # Log the rotation event to the new file
                if self._handler is not None:
                    record = logging.LogRecord(
                        name="LogRotation",
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg="Log file rotated",
                        args=(),
                        exc_info=None,
                    )
                    # Emit directly using the handler to avoid recursion
                    self._handler.emit(record)

            except Exception as e:
                # If rotation fails, log the error but continue
                LoggingConfig.debug_print(f"Error during log rotation: {e}")

    def __repr__(self) -> str:
        """
        Return a string representation of the MultiProcessingLog instance.

        Returns:
            str: A string representation of the instance.
        """
        # Add explicit cast to ensure the return is a string
        return cast(str, f"<MultiProcessingLog ({self.level_name})>")

    @property
    def level_name(self) -> str:
        """
        Get the name of the current log level.

        This property retrieves the human-readable name of the log level
        (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") based on
        the numeric log level value.

        Returns:
            str: The name of the current log level.
        """
        # Use cast to ensure the return type is str
        return cast(str, logging.getLevelName(self.level))


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
    exit_disabled = False

    def __init__(self) -> None:
        """Initialize the CriticalExitHandler with CRITICAL log level."""
        super().__init__(level=logging.CRITICAL)

    @classmethod
    def disable_exit(cls, disable: bool = True) -> None:
        """
        Control exit functionality for testing.

        When exits are disabled, critical logs will not cause the program to
        terminate, allowing tests to safely check critical error paths.

        Args:
            disable: If True (default), disable exits. If False, enable exits.
        """
        cls.exit_disabled = disable

    @classmethod
    def enable_exit(cls) -> None:
        """Re-enable exit functionality after testing."""
        cls.exit_disabled = False

    def emit(self, record: LogRecord) -> None:
        """
        Process a log record and potentially exit the program.

        Args:
            record: The log record to process
        """
        # First check if explicitly disabled for tests
        if self.__class__.exit_disabled:
            return

        # If set to True, critical log will lead to system exit
        exit_on_critical = LoggingConfig.get("exit_on_critical", True)

        # Exit if configured to do so (and not disabled)
        if exit_on_critical:
            sys.exit(1)


class ColoredLogger:
    """Logger with colored output support."""

    # Class-level attributes for shared resources
    _initialized_loggers: Dict[str, "ColoredLogger"] = {}
    _log_file_path: Optional[str] = None
    _file_handler: Optional[MultiProcessingLog] = None
    _root_logger: Optional[logging.Logger] = None
    _loggers: Dict[str, "ColoredLogger"] = {}

    def __init__(self, name: str, verbose: Optional[str] = None) -> None:
        """Initialize colored logger."""
        self.name = name
        self.verbose = verbose
        self._propagate = False  # Default to False like standard logger
        self._configured_level = LoggingConfig.get_level(name, verbose)
        self.logger = self._setup_logger()

        # Only add CriticalExitHandler if configured to exit on critical
        exit_on_critical = LoggingConfig.get("exit_on_critical", True)
        if exit_on_critical:
            # Add the handler that will exit on critical
            self.handlers.append(CriticalExitHandler())
            self.logger.addHandler(self.handlers[-1])

    @property
    def propagate(self) -> bool:
        """Control whether messages are propagated to parent loggers."""
        return self._propagate

    @propagate.setter
    def propagate(self, value: bool) -> None:
        """
        Set propagation value and update internal logger.

        Args:
            value: Boolean indicating whether to propagate messages to parent loggers
        """
        self._propagate = bool(value)
        if hasattr(self, "logger"):
            self.logger.propagate = self._propagate

    def _setup_logger(self) -> logging.Logger:
        """Set up the internal logger."""
        logger = logging.getLogger(self.name)
        logger.propagate = self._propagate
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

        # Get format string from config
        log_format = LoggingConfig.get("log_format", "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s")

        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(ColoredFormatter(fmt=log_format, colored=LoggingConfig.get("colored_console", True)))
        ch.setLevel(self._configured_level)
        logger.addHandler(ch)

        # File Handler
        if not self.__class__._file_handler:
            self.__class__._file_handler = self.__class__.setup_file_handler()

        if self.__class__._file_handler:
            # Set the same format for file handler
            self.__class__._file_handler.setFormatter(
                ColoredFormatter(fmt=log_format, colored=LoggingConfig.get("colored_file", False))
            )
            logger.addHandler(self.__class__._file_handler)

    @classmethod
    def setup_file_handler(cls, log_file_path: Optional[str] = None) -> Optional[MultiProcessingLog]:
        """
        Set up the file handler using LoggingConfig.

        Args:
            log_file_path: Optional explicit path for the log file

        Returns:
            The configured MultiProcessingLog handler or None if setup fails
        """
        # If a file handler already exists and no specific path is requested, return existing
        if cls._file_handler and not log_file_path:
            return cls._file_handler

        # --- Determine Log File Path ---
        if log_file_path is None:
            # Get log directory from config, default to "logs"
            log_dir = LoggingConfig.get("log_dir", "logs")
            os.makedirs(log_dir, exist_ok=True)

            # Generate filename (keeping existing logic)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            unique_suffix = str(os.getpid() % 1000)
            log_file_path = os.path.join(log_dir, f"app_{timestamp}_{unique_suffix}.log")

        cls._log_file_path = log_file_path  # Store the determined path

        # --- Rotation Settings from Config ---
        disable_rotation = LoggingConfig.get("disable_rotation", False)
        # Also check env var for compatibility if needed, though config should be primary
        # disable_rotation = disable_rotation or os.environ.get("LOG_DISABLE_ROTATION") == "1"

        handler: MultiProcessingLog  # Type hint

        if disable_rotation:
            LoggingConfig.debug_print("Log rotation is disabled via config")
            handler = MultiProcessingLog(log_file_path, "a", 0, 0)  # No rotation
        else:
            # Get rotation size from config, default 10MB
            rotation_size_mb = LoggingConfig.get("rotation_size_mb", 10)
            # Ensure minimum size (e.g., 1KB)
            rotation_size_bytes = max(1024, int(rotation_size_mb * 1024 * 1024))

            # Get backup count from config, default 5
            backup_count = LoggingConfig.get("backup_count", 5)
            # Ensure minimum count (e.g., 1)
            backup_count = max(1, backup_count)

            LoggingConfig.debug_print(
                "Setting up log rotation via config: "
                f"maxSize={rotation_size_bytes} bytes ({rotation_size_mb}MB), "
                f"backups={backup_count}"
            )
            handler = MultiProcessingLog(log_file_path, "a", rotation_size_bytes, backup_count)

        # --- Formatter from Config ---
        default_format = "%(asctime)s - %(filename)s - %(name)s - [%(levelname)s] - %(message)s"
        log_format = LoggingConfig.get("log_format", default_format)

        # Get color setting for file handler from config, default to False
        use_file_color = LoggingConfig.get("colored_file", False)

        # Use the config setting for 'colored'
        handler.setFormatter(ColoredFormatter(log_format, colored=use_file_color))

        # --- Level ---
        # File handler always logs at DEBUG level as per original design
        handler.setLevel(logging.DEBUG)

        return handler

    @classmethod
    def reset(cls, new_file: bool = False) -> Type["ColoredLogger"]:
        """
        Reset all active loggers and optionally create a new log file.

        This method is useful when reconfigure logging is required or when
        testing different logging configurations. It closes all existing handlers,
        clears the internal registry, and optionally creates a new log file.

        Args:
            new_file: If True, generate a new unique log file. If False, reuse the existing one.

        Returns:
            The ColoredLogger class for method chaining
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
            cls._log_file_path = os.path.join(log_dir, f"app_{timestamp}_{unique_suffix}.log")

        # Create a new file handler
        if cls._file_handler is None:
            cls._file_handler = cls.setup_file_handler(cls._log_file_path)

        # Reinitialize loggers that were previously registered
        for name in logger_names:
            get_logger(name)

        return cls

    @classmethod
    def update_logger_level(cls, name: str, level: Union[int, str]) -> None:
        """
        Update the log level of an existing logger.

        Args:
            name: Name of the logger to update
            level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if name in cls._initialized_loggers:
            logger_instance = cls._initialized_loggers[name]

            if isinstance(level, int):
                # If it's already an integer level, use it directly
                level_value = level
            else:
                # If it's a string, use map_level to convert it
                level_value = LoggingConfig.map_level(level)

            # Update the level in both the wrapper and the underlying logger
            logger_instance.level = level_value
            logger_instance.logger.setLevel(level_value)

    @property
    def handlers(self) -> List[logging.Handler]:
        """
        Return the handlers from the underlying logger.

        Returns:
            List of handlers attached to the logger
        """
        return self.logger.handlers

    @property
    def level(self) -> int:
        """
        Return the effective level for the logger (for testing).

        Returns:
            The configured log level as an integer
        """
        # This abstracts the implementation details from the tests
        # For tests, report the configured level, not the actual logger level
        return self._configured_level

    @level.setter
    def level(self, value: int) -> None:
        """
        Set the configured level and update console handlers.

        Args:
            value: The new log level to set
        """
        self._configured_level = value

        # Update console handlers only
        if hasattr(self, "logger") and self.logger:
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
        """
        Logs a warning message.

        Args:
            msg: The message to log
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs an error message.

        Args:
            msg: The message to log
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a critical message.

        Note: If exit_on_critical=True in config, this will terminate the program.

        Args:
            msg: The message to log
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an exception message."""
        self.logger.exception(msg, *args, **kwargs)


# At module level
_EXTERNAL_LOGGERS_CONFIGURED = False


def configure_external_loggers(external_loggers: Dict[str, str]) -> None:
    """Configure external library loggers with specified levels."""
    external_loggers = LoggingConfig.get("external_loggers", {})

    for logger_name, level in external_loggers.items():
        # Get the logger for this package
        logger = logging.getLogger(logger_name)

        # Convert level string to logging constant
        level_value = LoggingConfig.map_level(level)

        # Set the level
        logger.setLevel(level_value)

        # Disable propagation to avoid duplicate messages
        logger.propagate = False

        LoggingConfig.debug_print(f"Set external logger '{logger_name}' to level {level}")


def register_exception_hook(exit_on_critical: bool = True) -> None:
    """Register a custom exception hook to log unhandled exceptions."""

    def default_exception_handler(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        """Default exception handler that logs unhandled exceptions."""
        logger = get_logger("UnhandledException")
        logger.error("Unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))
        if exit_on_critical:
            sys.exit(1)

    sys.excepthook = default_exception_handler


def create_logger(
    name: str,
    log_dir: Optional[str] = None,
    level: Optional[Union[int, str]] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Create a new logger with console and optional file output."""
    logger = logging.getLogger(name)
    logger.setLevel(level or logging.INFO)

    # Console handler
    console_handler = StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter(fmt=format_string or "%(message)s"))
    logger.addHandler(console_handler)

    # File handler
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, f"{name}.log")
        file_handler = RotatingFileHandler(file_path, maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter(fmt=format_string or "%(message)s"))
        logger.addHandler(file_handler)

    return logger


def handle_critical_exception(message: str, exit_code: int = 1) -> None:
    """Log a critical error and exit the application."""
    logger = get_logger("CriticalException")
    logger.critical(message)
    sys.exit(exit_code)


def init_root_logger(
    level: Optional[Union[int, str]] = None,
    log_dir: Optional[str] = None,
    format_string: Optional[str] = None,
    colored_console: bool = True,
) -> logging.Logger:
    """Initialize and configure the root logger."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level or logging.INFO)

    # Console handler
    console_handler = StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter(fmt=format_string or "%(message)s", colored=colored_console))
    root_logger.addHandler(console_handler)

    # File handler
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, "root.log")
        file_handler = RotatingFileHandler(file_path, maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter(fmt=format_string or "%(message)s"))
        root_logger.addHandler(file_handler)

    return root_logger


def enable_debug_logging(logger_names: Optional[List[str]] = None) -> None:
    """
    Enable DEBUG level logging for specified loggers.

    Args:
        logger_names: List of logger names to set to DEBUG level
    """
    if logger_names is None:
        logger_names = [logging.getLogger().name]

    for name in logger_names:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)


def get_caller_frame(depth: int = 1) -> FrameType:
    """Get the caller's frame at the specified depth."""
    return sys._getframe(depth)


def get_module_name() -> str:
    """
    Get the name of the calling module.

    Returns:
        The name of the calling module
    """
    module_name = get_caller_frame(1).f_globals["__name__"]
    return cast(str, module_name)


def get_class_logger() -> Union[ColoredLogger, logging.Logger]:
    """
    Get a logger named after the calling class.

    Returns:
        A logger instance named after the calling class
    """
    class_name = sys._getframe(1).f_globals["__name__"]
    return get_logger(class_name)


def log_to_file(message: str, level: str = "INFO", file_path: Optional[str] = None) -> None:
    """
    Log a message directly to a file without using the logging system.

    Args:
        message: The message to log
        level: Log level as a string
        file_path: Path to the log file
    """
    file_path = file_path or "default.log"
    with open(file_path, mode="a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now()} - {level} - {message}\n")


def get_logger(name: str, verbose: Optional[str] = None) -> Union[ColoredLogger, logging.Logger]:
    """
    Get a configured logger instance.

    Args:
        name: Name for the logger, typically module name
        verbose: Optional override for log level

    Returns:
        A logger instance configured according to settings
    """
    global _EXTERNAL_LOGGERS_CONFIGURED

    # Configure external loggers only once
    if not _EXTERNAL_LOGGERS_CONFIGURED:
        configure_external_loggers(LoggingConfig.get("external_loggers", {}))
        _EXTERNAL_LOGGERS_CONFIGURED = True

    # Check if logger already exists
    if name in ColoredLogger._initialized_loggers:
        existing_logger = ColoredLogger._initialized_loggers[name]

        # If explicit verbose parameter is provided, always apply it
        if verbose is not None:
            original_level = existing_logger.level
            ColoredLogger.update_logger_level(name, verbose)
            if original_level != existing_logger.level:
                LoggingConfig.debug_print(
                    f"Warning: Logger '{name}' level changed from "
                    f"{logging.getLevelName(original_level)} to {logging.getLevelName(existing_logger.level)} "
                    f"due to explicit parameter"
                )
            return existing_logger

        # Check if there's a specific config for this logger in external_loggers
        external_loggers = LoggingConfig.get("external_loggers", {})
        if name in external_loggers:
            original_level = existing_logger.level
            ColoredLogger.update_logger_level(name, external_loggers[name])
            if original_level != existing_logger.level:
                LoggingConfig.debug_print(
                    f"Warning: Logger '{name}' level changed from "
                    f"{logging.getLevelName(original_level)} to {logging.getLevelName(existing_logger.level)} "
                    f"due to external_loggers configuration"
                )
            return existing_logger

        # Check if there's a module-specific level that should be applied
        module_levels = LoggingConfig.get("module_levels", {})
        if name in module_levels:
            original_level = existing_logger.level
            ColoredLogger.update_logger_level(name, module_levels[name])
            if original_level != existing_logger.level:
                LoggingConfig.debug_print(
                    f"Warning: Logger '{name}' level changed from "
                    f"{logging.getLevelName(original_level)} to {logging.getLevelName(existing_logger.level)} "
                    f"due to module_levels configuration"
                )

        return existing_logger

    # Use explicit level, then check external_loggers config, then check module_levels, then use default
    if verbose is None:
        external_loggers = LoggingConfig.get("external_loggers", {})
        module_levels = LoggingConfig.get("module_levels", {})

        if name in external_loggers:
            verbose = external_loggers[name]
        elif name in module_levels:
            verbose = module_levels[name]
        else:
            verbose = LoggingConfig.get("default_level", "INFO")

    # Create new logger
    logger = ColoredLogger(name, verbose)
    return logger
