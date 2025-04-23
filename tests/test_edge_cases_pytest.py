"""Tests for edge cases in prismalog using pytest style."""

import logging
import os

import pytest

from prismalog.log import ColoredLogger, LoggingConfig, get_logger


@pytest.fixture
def log_dir(tmp_path, capture_logs, capsys):
    """Create a temporary log directory with logging capture."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Reset logging state completely
    LoggingConfig.reset()
    ColoredLogger._initialized_loggers.clear()
    if ColoredLogger._file_handler:
        ColoredLogger._file_handler.close()
        ColoredLogger._file_handler = None

    # Clear all existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)

    # Initialize logging with our capture handler
    LoggingConfig.initialize(
        use_cli_args=False, log_dir=str(log_dir), colored_console=False  # Disable colored output for testing
    )

    # Add capture handler that writes to our StringIO
    capture_handler = logging.StreamHandler(capture_logs)
    capture_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(capture_handler)

    yield log_dir

    # Cleanup handlers
    for handler in root.handlers[:]:
        try:
            handler.flush()
            handler.close()
            root.removeHandler(handler)
        except:
            pass

    if ColoredLogger._file_handler:
        try:
            ColoredLogger._file_handler.close()
        except:
            pass
        ColoredLogger._file_handler = None

    LoggingConfig.reset()


def test_permission_handling(log_dir, capture_logs, capsys):
    """Test handling when log directory permissions are restricted."""
    if os.name == "nt":
        pytest.skip("Skipping permission test on Windows")

    # Clear any previous output
    capture_logs.seek(0)
    capture_logs.truncate()

    # Get initial logger and test
    logger = get_logger("permission_test")
    logger.info("Pre-restriction test")

    # Make directory read-only and verify logger fallback
    log_dir.chmod(0o444)
    logger.warning("Test restricted permissions")

    # Get and combine outputs (both direct and captured)
    output = capture_logs.getvalue()
    captured = capsys.readouterr()
    combined_output = output + captured.out

    print(f"Direct capture: {output!r}")
    print(f"Pytest capture: {captured.out!r}")

    assert "Pre-restriction test" in combined_output, "Should log before restriction"
    assert "Test restricted permissions" in combined_output, "Should log after restriction"
    assert logger.handlers, "Logger should have fallback handlers"


def test_logging_capture_chain(tmp_path, capture_logs):
    """Test to understand the logging capture chain."""
    # Create logger
    LoggingConfig.initialize(use_cli_args=False, log_dir=str(tmp_path), colored_console=True)

    logger = get_logger("capture_test")

    print("\nLogger Configuration:")
    print(f"Logger handlers: {len(logger.handlers)}")
    for idx, h in enumerate(logger.handlers):
        print(f"\nHandler {idx}:")
        print(f"Type: {type(h)}")
        print(f"Stream: {getattr(h, 'stream', 'No stream')}")
        print(f"Formatter: {type(h.formatter)}")

    print("\nRoot Logger Configuration:")
    root = logging.getLogger()
    print(f"Root handlers: {len(root.handlers)}")
    for idx, h in enumerate(root.handlers):
        print(f"\nRoot Handler {idx}:")
        print(f"Type: {type(h)}")
        print(f"Stream: {getattr(h, 'stream', 'No stream')}")

    # Test capture
    capture_logs.seek(0)
    capture_logs.truncate()

    logger.info("Test capture")
    output = capture_logs.getvalue()
    print(f"\nCaptured: {output!r}")
