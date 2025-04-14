"""Global test configuration for prismalog."""
import pytest
import logging
import sys
from contextlib import contextmanager
from prismalog.log import ColoredLogger, CriticalExitHandler
from prismalog.config import LoggingConfig

class TestCaptureIO:
    """
    IO-like class that captures text written to it for testing purposes.

    This class mimics a file object's write/flush interface but stores written
    text in memory, allowing tests to inspect what would have been written to
    stdout or stderr.
    """
    def __init__(self):
        self.captured = []

    def write(self, text):
        self.captured.append(text)

    def flush(self):
        pass

    def getvalue(self):
        return ''.join(self.captured)

    def clear(self):
        self.captured = []

# Create global capture streams for tests
test_stdout = TestCaptureIO()
test_stderr = TestCaptureIO()

@contextmanager
def capture_stdout():
    """
    Context manager to capture stdout during tests.

    Usage:
        with capture_stdout() as captured:
            print("This will be captured")
            logger.info("This too!")

        assert "captured" in captured.getvalue()
    """
    original_stdout = sys.stdout
    try:
        sys.stdout = test_stdout
        test_stdout.clear()
        yield test_stdout
    finally:
        sys.stdout = original_stdout

@pytest.fixture
def stdout_capture():
    """
    Pytest fixture for capturing stdout.

    Usage:
        def test_example(stdout_capture):
            print("This will be captured")
            assert "captured" in stdout_capture.getvalue()
    """
    with capture_stdout() as captured:
        yield captured

@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """Setup for all tests at the beginning of the test session."""
    # Ensure test mode is enabled for the entire session
    LoggingConfig.initialize(parse_args=False, **{
        "test_mode": True,
    })

    # Store original state to restore after all tests
    orig_config = LoggingConfig._config.copy()
    orig_handlers = {}

    # Record original handlers for all loggers
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        if logger.handlers:
            orig_handlers[name] = list(logger.handlers)

    yield

    # Restore original config after all tests
    LoggingConfig._config = orig_config

@pytest.fixture(scope="module", autouse=True)
def reset_between_modules():
    """Reset loggers between test modules."""
    # Store original config before any changes
    orig_config = LoggingConfig._config.copy()

    # Before each module runs:
    # 1. Clear all existing loggers
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        if logger.handlers:
            logger.handlers.clear()  # Remove all handlers

    # 2. Reset ColoredLogger's internal state
    ColoredLogger._initialized_loggers = {}
    if hasattr(ColoredLogger, '_file_handler') and ColoredLogger._file_handler:
        ColoredLogger._file_handler.close()
        ColoredLogger._file_handler = None

    # 3. Reset test capture objects
    test_stdout.clear()
    test_stderr.clear()

    # 4. Force ColoredLogger to reinitialize completely
    ColoredLogger.reset(new_file=True)

    yield  # Run the tests in the module

    # After module completes, reset again to not affect next module
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        if logger.handlers:
            logger.handlers.clear()

    # Restore original config
    LoggingConfig._config = orig_config

@pytest.fixture(scope="function", autouse=True)
def reset_test_env():
    """Reset test environment before each test."""
    # Clear test capture buffers
    test_stdout.clear()
    test_stderr.clear()

    # Ensure fresh logger state
    ColoredLogger.reset(new_file=True)

    yield

    # Clean up after test
    test_stdout.clear()
    test_stderr.clear()

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
            if (isinstance(handler, logging.StreamHandler) and
                not isinstance(handler, CriticalExitHandler) and
                hasattr(handler, 'stream') and
                handler.stream is sys.stdout):

                # Remove the original handler
                logger.removeHandler(handler)

                # Add a new handler that uses test_stdout
                new_handler = logging.StreamHandler(test_stdout)
                new_handler.setLevel(handler.level)
                new_handler.setFormatter(handler.formatter)
                logger.addHandler(new_handler)

    return {
        "stdout": test_stdout,
        "stderr": test_stderr
    }
