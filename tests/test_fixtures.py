"""Test suite for verifying pytest fixture behavior in prismalog testing."""

import logging
import os
from pathlib import Path

import pytest

from prismalog.log import ColoredLogger, CriticalExitHandler, LoggingConfig, get_logger


def test_session_setup():
    """Verify session-level fixture setup."""
    LoggingConfig.initialize(use_cli_args=False, test_mode=True)
    assert LoggingConfig._config.get("test_mode") is True, "Test mode not enabled"
    assert LoggingConfig._initialized, "LoggingConfig not initialized"


def test_module_reset(reset_between_modules):
    """Verify module-level reset works correctly."""
    assert not ColoredLogger._initialized_loggers, "Loggers not cleared"
    assert ColoredLogger._file_handler is None, "File handler not cleared"


def test_logging_config_reset(reset_logging_config, temp_log_dir):
    """Verify per-test logging reset."""
    # Check environment cleaning
    env_vars = [k for k in os.environ if k.startswith(("LOG_", "GITHUB_LOG_"))]
    assert not env_vars, f"Environment not clean: {env_vars}"

    # Check logger state
    root = logging.getLogger()
    assert root.handlers, "Root logger has no handlers"

    # Verify temp directory
    assert Path(temp_log_dir).exists(), "Temp log directory not created"


def test_capture_logs_functionality(capture_logs):
    """Verify log capture functionality."""
    # Direct logging
    logger = get_logger("capture_test")
    logger.info("Direct message")

    # Print statement
    print("Print message")

    # Get combined output
    output = capture_logs.get_combined_output()
    assert "Direct message" in output, "Direct log not captured"
    assert "Print message" in output, "Print not captured"


def test_handler_cleanup(temp_log_dir):
    """Verify proper handler cleanup between tests."""
    # Create a logger with multiple handlers
    logger = get_logger("cleanup_test")
    initial_handlers = len(logger.logger.handlers)  # Access underlying logger

    # Add another handler
    handler = logging.StreamHandler()
    logger.logger.addHandler(handler)  # Add to underlying logger

    # Let fixture cleanup happen
    # Next test should start with clean state
    assert len(logger.logger.handlers) > initial_handlers, "Handler not added"


def test_handler_state_after_cleanup(temp_log_dir):
    """Verify handler state is clean after previous test."""
    logger = get_logger("cleanup_test")
    assert len(logger.handlers) == 2, f"Unexpected handler count: {len(logger.handlers)}"


def test_environment_preservation():
    """Verify environment variable handling."""
    # Set a test variable
    os.environ["LOG_TEST"] = "test_value"

    # Let fixture cleanup happen
    # Next test should not see this variable
    assert "LOG_TEST" in os.environ


def test_environment_clean():
    """Verify environment is clean after previous test."""
    assert "LOG_TEST" not in os.environ, "Environment variable leaked"


def test_critical_handler_preservation():
    """Verify critical handlers are preserved when needed."""
    # Initialize with exit_on_critical enabled
    LoggingConfig.initialize(use_cli_args=False, exit_on_critical=True)

    logger = get_logger("critical_test")

    # Count handlers that are CriticalExitHandler
    critical_handlers = [h for h in logger.logger.handlers if isinstance(h, CriticalExitHandler)]

    # Debug output
    print("\nHandler types:")
    for h in logger.logger.handlers:
        print(f"- {type(h).__name__}")

    assert len(critical_handlers) == 1, "Critical handler not preserved"


@pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING", "ERROR"])
def test_log_level_persistence(capture_logs, log_level):
    """Verify log levels are maintained correctly."""
    logger = get_logger("level_test", verbose=log_level)
    logger.logger.setLevel(getattr(logging, log_level))  # Access underlying logger

    test_message = "Test message"
    getattr(logger, log_level.lower())(test_message)

    output = capture_logs.get_combined_output()
    assert test_message in output, f"Log level {log_level} not working"
