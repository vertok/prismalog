"""Global test configuration for prismalog."""

import io
import logging
import multiprocessing
import os
import sys
import tempfile
from contextlib import contextmanager
from queue import Queue

import pytest

from prismalog.config import LoggingConfig
from prismalog.log import ColoredLogger, CriticalExitHandler, get_logger


class TestCaptureIO:
    """IO-like class that captures text written to it for testing purposes."""

    def __init__(self):
        self.captured = []

    def write(self, text):
        self.captured.append(text)

    def flush(self):
        pass

    def getvalue(self):
        return "".join(self.captured)

    def clear(self):
        self.captured = []


# Create global capture streams for tests
test_stdout = TestCaptureIO()
test_stderr = TestCaptureIO()


@contextmanager
def capture_stdout():
    """Context manager to capture stdout during tests."""
    original_stdout = sys.stdout
    try:
        sys.stdout = test_stdout
        test_stdout.clear()
        yield test_stdout
    finally:
        sys.stdout = original_stdout


@pytest.fixture
def stdout_capture():
    """Pytest fixture for capturing stdout."""
    with capture_stdout() as captured:
        yield captured


@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """Initial test session setup that:
    1. Enables test mode
    2. Preserves original config
    3. Restores config after all tests
    """
    # Ensure test mode is enabled for the entire session
    LoggingConfig.initialize(
        use_cli_args=False,
        **{
            "test_mode": True,
        },
    )

    # Store original state to restore after all tests
    orig_config = LoggingConfig._config.copy()

    yield

    # Restore original config after all tests
    LoggingConfig._config = orig_config


@pytest.fixture(scope="module", autouse=True)
def reset_between_modules():
    """Resets logger state between test modules:
    1. Clears initialized loggers
    2. Closes file handlers
    3. Forces complete logger reset
    """
    # Reset ColoredLogger's internal state
    ColoredLogger._initialized_loggers = {}
    if hasattr(ColoredLogger, "_file_handler") and ColoredLogger._file_handler:
        ColoredLogger._file_handler.close()
        ColoredLogger._file_handler = None

    # Force ColoredLogger to reinitialize completely
    ColoredLogger.reset(new_file=True)

    yield  # Run the tests in the module


@pytest.fixture
def setup_test_handlers():
    """Set up handlers for test output capture."""
    # Clear test capture buffers before setting handlers
    test_stdout.clear()
    test_stderr.clear()

    # Replace stdout handlers with test_stdout handlers for all loggers
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)

        # Only modify loggers with handlers
        if not logger.handlers:
            continue

        # Replace stdout handlers with test_stdout handlers
        for handler in list(logger.handlers):
            if (
                isinstance(handler, logging.StreamHandler)
                and not isinstance(handler, CriticalExitHandler)
                and hasattr(handler, "stream")
                and handler.stream is sys.stdout
            ):
                # Remove the original handler
                logger.removeHandler(handler)

                # Add a new handler that uses test_stdout
                new_handler = logging.StreamHandler(test_stdout)
                new_handler.setLevel(handler.level)
                new_handler.setFormatter(handler.formatter)
                logger.addHandler(new_handler)

    return {"stdout": test_stdout, "stderr": test_stderr}


@pytest.fixture(scope="function", autouse=True)
def reset_config_for_each_test(request):
    """
    Reset LoggingConfig to default state before each test.

    This fixture preserves certain environment variables needed for specific tests.
    """
    # Reset the configuration to defaults
    LoggingConfig.reset()

    # Store any environment variables we'll modify
    env_vars_to_watch = {}
    env_var_prefixes = ["LOG_", "GITHUB_LOG_"]

    # Check if we need to preserve LOG_DIR for specific test classes
    preserve_log_dir = False
    if hasattr(request, "instance") and request.instance:
        class_name = request.instance.__class__.__name__
        if class_name == "TestColoredLogger":
            preserve_log_dir = True

    # Save and clear environment variables
    for var in list(os.environ.keys()):
        if any(var.startswith(prefix) for prefix in env_var_prefixes):
            env_vars_to_watch[var] = os.environ[var]
            # Skip clearing LOG_DIR for TestColoredLogger
            if not (preserve_log_dir and var == "LOG_DIR"):
                os.environ.pop(var, None)

    # Ensure the configuration is not initialized
    LoggingConfig._initialized = False

    # Clear output buffers
    test_stdout.clear()
    test_stderr.clear()

    # Reset log handlers for most tests, but preserve for specific ones
    should_reset_logger = True
    if hasattr(request, "function"):
        function_name = request.function.__name__
        if function_name in ["test_log_file_creation", "test_file_handler_rotation"] and preserve_log_dir:
            should_reset_logger = False

    if should_reset_logger:
        ColoredLogger.reset(new_file=True)

    # Run the test
    yield

    # Restore the original environment variables
    for var in env_vars_to_watch:
        os.environ[var] = env_vars_to_watch[var]


@pytest.fixture(scope="session")
def temp_log_dir(tmp_path_factory):
    """Create a temporary directory for logs that persists for the whole test session."""
    log_dir = tmp_path_factory.mktemp("logs")
    os.environ["LOG_DIR"] = str(log_dir)
    yield log_dir
    # Cleanup after all tests
    try:
        for handler in logging.root.handlers[:]:
            handler.close()
    except:
        pass


@pytest.fixture
def logger(temp_log_dir):
    """Fixture to create a logger instance."""
    return get_logger(name="test_logger", verbose="DEBUG")


@pytest.fixture
def captured_output():
    """Fixture to get captured output from the test streams."""

    class CaptureResult:
        @property
        def out(self):
            return test_stdout.getvalue()

        @property
        def err(self):
            return test_stderr.getvalue()

    test_stdout.clear()
    test_stderr.clear()
    return CaptureResult()


def replace_handlers_for_logger(logger):
    """Replace stdout handlers with test_stdout handlers for a logger."""
    if not logger.handlers:
        return

    for handler in list(logger.handlers):
        if (
            isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, CriticalExitHandler)
            and hasattr(handler, "stream")
            and handler.stream is sys.stdout
        ):
            # Remove the original handler
            logger.removeHandler(handler)

            # Add a new handler that uses test_stdout
            new_handler = logging.StreamHandler(test_stdout)
            new_handler.setLevel(handler.level)
            new_handler.setFormatter(handler.formatter)
            logger.addHandler(new_handler)


@pytest.fixture
def setup_test_output(request):
    """Setup special handlers for test output capture."""
    # First check ColoredLogger's initialized loggers
    for name in list(ColoredLogger._initialized_loggers.keys()):
        logger = logging.getLogger(name)
        replace_handlers_for_logger(logger)

    # Also check other loggers that might exist
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name not in ColoredLogger._initialized_loggers:
            logger = logging.getLogger(name)
            replace_handlers_for_logger(logger)

    test_stdout.clear()
    test_stderr.clear()

    yield

    test_stdout.clear()
    test_stderr.clear()


def cleanup_test_logs(log_dir):
    """Clean up log files in the specified directory."""
    if not os.path.exists(log_dir):
        return

    for file in os.listdir(log_dir):
        if file.endswith(".log"):
            try:
                file_path = os.path.join(log_dir, file)
                os.remove(file_path)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to remove log file {file}: {e}")


@pytest.fixture(autouse=True)
def reset_logging_config(request, temp_log_dir):
    """Per-test logging reset that:
    1. Preserves original environment
    2. Cleans handlers safely
    3. Initializes test-specific config
    4. Restores state after test
    5. Cleans up test log files
    """
    # Store original state
    orig_env = {k: v for k, v in os.environ.items() if k.startswith(("LOG_", "GITHUB_LOG_"))}
    orig_handlers = []
    for h in logging.root.handlers:
        if h:
            orig_handlers.append(h)

    # Clean environment and loggers
    for k in list(os.environ):
        if k.startswith(("LOG_", "GITHUB_LOG_")):
            del os.environ[k]

    # Reset loggers safely
    for name in list(logging.root.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            try:
                if hasattr(handler, "_handler"):
                    handler._handler.flush()
                handler.flush()
            except:
                pass
            logger.removeHandler(handler)

    logging.root.handlers = []
    ColoredLogger._initialized_loggers.clear()

    # Close existing file handler if any
    if ColoredLogger._file_handler:
        try:
            if hasattr(ColoredLogger._file_handler, "_handler"):
                ColoredLogger._file_handler._handler.close()
            ColoredLogger._file_handler.close()
        except:
            pass
        ColoredLogger._file_handler = None

    # Initialize with test-specific configuration
    LoggingConfig.initialize(
        use_cli_args=False,
        **{
            "colored_console": True,
            "exit_on_critical": request.function.__name__ == "test_critical_exit_handler",
            "log_dir": str(temp_log_dir),
        },
    )

    # Disable exit by default, except for critical test
    CriticalExitHandler.disable_exit(request.function.__name__ != "test_critical_exit_handler")

    yield

    # Cleanup handlers safely
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            try:
                if hasattr(handler, "_handler"):
                    handler._handler.flush()
                    handler._handler.close()
                handler.flush()
                handler.close()
            except:
                pass
            logger.removeHandler(handler)

    # Clean up test log files
    cleanup_test_logs(str(temp_log_dir))

    # Restore original state
    os.environ.update(orig_env)
    logging.root.handlers = orig_handlers
    ColoredLogger.reset(new_file=True)


@pytest.fixture
def capture_logs(capsys):
    """Output capture that:
    1. Captures both direct and pytest output
    2. Provides combined output access
    3. Cleans up handlers properly
    """
    output_stream = io.StringIO()
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]

    # Add capture handler
    capture_handler = logging.StreamHandler(output_stream)
    capture_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(capture_handler)

    def get_combined_output():
        """Get both direct and pytest-captured output."""
        direct = output_stream.getvalue()
        captured = capsys.readouterr()
        return direct + captured.out

    # Add helper method
    output_stream.get_combined_output = get_combined_output

    yield output_stream

    # Cleanup
    root_logger.removeHandler(capture_handler)
    root_logger.handlers = original_handlers


@pytest.fixture(scope="session", autouse=True)
def cleanup_logging_on_exit():
    """Ensure proper cleanup of logging handlers at session end."""
    yield

    # Cleanup all loggers
    for name in list(logging.root.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            try:
                if hasattr(handler, "flush"):
                    handler.flush()
                if hasattr(handler, "_handler") and handler._handler:
                    handler._handler.flush()
                    handler._handler.close()
                if hasattr(handler, "close"):
                    handler.close()
            except:
                pass
            logger.removeHandler(handler)

    # Cleanup ColoredLogger's file handler
    if hasattr(ColoredLogger, "_file_handler") and ColoredLogger._file_handler:
        try:
            if hasattr(ColoredLogger._file_handler, "_handler"):
                ColoredLogger._file_handler._handler.close()
            ColoredLogger._file_handler.close()
        except:
            pass
        ColoredLogger._file_handler = None

    # Clear initialized loggers
    ColoredLogger._initialized_loggers.clear()

    # Reset root logger
    logging.root.handlers = []


@pytest.fixture
def thread_test_env():
    """Set up environment for multithreading tests.

    Provides:
    - Temporary log directory
    - Thread-safe queue for results
    - Clean logger state
    - Log file path for verification
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="log_thread_test_")

    # Initialize with thread-safe configuration
    LoggingConfig.initialize(
        use_cli_args=False,
        **{
            "log_dir": temp_dir,
            "default_level": "DEBUG",
            "rotation_size_mb": 1,
            "colored_console": False,  # Disable colors for testing
            "exit_on_critical": False,  # Don't exit on critical logs
        },
    )

    # Reset logger state
    ColoredLogger.reset(new_file=True)

    # Create result queue
    result_queue = Queue()

    # Return test environment
    env = {"temp_dir": temp_dir, "log_file": ColoredLogger._log_file_path, "result_queue": result_queue}

    yield env

    # Cleanup
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, file))
            except:
                pass
        os.rmdir(temp_dir)


@pytest.fixture
def mixed_concurrency_env():
    """Set up environment for mixed concurrency tests.

    Provides:
    - Temporary log directory
    - Process-safe queue
    - Log file path
    - Clean logger state
    """
    # Create temp directory
    temp_log_dir = tempfile.mkdtemp(prefix="log_mixed_test_")

    # Initialize test configuration
    LoggingConfig.initialize(
        use_cli_args=False,
        **{
            "log_dir": temp_log_dir,
            "default_level": "DEBUG",
            "rotation_size_mb": 5,
            "colored_console": False,
            "exit_on_critical": False,
        },
    )

    # Reset logger state
    ColoredLogger.reset(new_file=True)

    # Create environment package
    env = {"temp_dir": temp_log_dir, "log_file": ColoredLogger._log_file_path, "result_queue": multiprocessing.Queue()}

    yield env

    # Cleanup
    if os.path.exists(temp_log_dir):
        for file in os.listdir(temp_log_dir):
            try:
                os.remove(os.path.join(temp_log_dir, file))
            except:
                pass
        os.rmdir(temp_log_dir)
