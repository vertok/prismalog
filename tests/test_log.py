""" Test suite for log module issues in prismalog. """

import logging
import os
import time
from datetime import datetime, timedelta
from unittest import mock

import pytest
from conftest import replace_handlers_for_logger, test_stderr, test_stdout

from prismalog.config import LoggingConfig
from prismalog.log import ColoredLogger, CriticalExitHandler, MultiProcessingLog, get_logger


class TestColoredLogger:
    """Test suite for the ColoredLogger and related functionality."""

    @pytest.fixture(autouse=True)
    def setup_test_method(self, request, temp_log_dir):  # reuse temp_log_dir from conftest.py
        """Set up fresh environment for each test."""
        # Store original handlers
        self.original_handlers = []
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            self.original_handlers.extend(logger.handlers[:])
            logger.handlers.clear()

        # Configure for this test
        LoggingConfig.initialize(
            use_cli_args=False,
            **{
                "colored_console": True,
                "exit_on_critical": request.function.__name__ == "test_critical_exit_handler",
                "log_dir": str(temp_log_dir),  # Use temp_log_dir instead of env var
            },
        )

        yield

        # Cleanup: close handlers properly before removing them
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                try:
                    # Check if handler is already closed before flushing
                    if hasattr(handler, "stream") and not getattr(handler.stream, "closed", True):
                        handler.flush()
                    handler.close()
                except (AttributeError, IOError, ValueError):
                    pass  # Ignore closed handlers
                logger.removeHandler(handler)

        # Restore original handlers
        for handler in self.original_handlers:
            if handler:
                logging.root.addHandler(handler)

        # Reset ColoredLogger state
        if hasattr(ColoredLogger, "_file_handler") and ColoredLogger._file_handler:
            try:
                # Check if file handler stream is closed before flushing
                if hasattr(ColoredLogger._file_handler, "stream") and not getattr(
                    ColoredLogger._file_handler.stream, "closed", True
                ):
                    ColoredLogger._file_handler.flush()
                ColoredLogger._file_handler.close()
            except (AttributeError, IOError, ValueError):
                pass  # Ignore closed handlers
            ColoredLogger._file_handler = None

        ColoredLogger._initialized_loggers.clear()
        LoggingConfig.reset()

    def _setup_test_handlers(self):
        """Set up special handlers for test output capture."""
        # First check ColoredLogger's initialized loggers
        for name in list(ColoredLogger._initialized_loggers.keys()):
            logger = logging.getLogger(name)
            replace_handlers_for_logger(logger)

        # Also check other loggers that might exist
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name not in ColoredLogger._initialized_loggers:
                logger = logging.getLogger(name)
                replace_handlers_for_logger(logger)

    @pytest.fixture
    def captured_output(self):
        """Fixture to get captured output from the test streams."""

        class CaptureResult:
            @property
            def out(self):
                return test_stdout.getvalue()

            @property
            def err(self):
                return test_stderr.getvalue()

        return CaptureResult()

    def test_logger_initialization_stdout(self, capture_logs):  # use capture_logs from conftest.py
        """Test that the logger initializes correctly."""
        logger = get_logger("test_stdout", verbose="DEBUG")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        assert "Test message" in output, f"Expected 'Test message' but got: {output!r}"

    def test_logger_initialization(self, temp_log_dir):  # use temp_log_dir from conftest.py
        """Test logger initialization sets up the proper handlers."""
        log_dir = temp_log_dir

        LoggingConfig.initialize(use_cli_args=False, log_dir=str(log_dir))

        logger = get_logger("test_init")

        # Print handler info for debugging
        print("\nHandler Configuration:")
        for idx, handler in enumerate(logger.handlers):
            print(f"Handler {idx}: {type(handler).__name__}")

        # Verify handlers
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        file_handlers = [h for h in logger.handlers if hasattr(h, "_handler")]  # MultiProcessingLog check

        assert len(console_handlers) >= 1, "No console handler found"
        assert len(file_handlers) >= 1, "No file handler found"
        assert len(logger.handlers) >= 2, "Logger should have at least 2 handlers"

    def test_logger_no_redundant_handlers(self, logger):
        """Test that the logger does not add redundant handlers."""
        # Get initial logger and count its handlers
        initial_logger = get_logger(name="test_no_redundant", verbose="DEBUG")
        initial_handler_count = len(initial_logger.handlers)

        print(f"\nInitial handler configuration:")
        for idx, handler in enumerate(initial_logger.handlers):
            print(f"Handler {idx}: {type(handler).__name__}")

        # Get another logger with the same name
        second_logger = get_logger(name="test_no_redundant", verbose="DEBUG")
        second_handler_count = len(second_logger.handlers)

        print(f"\nSecond logger handler configuration:")
        for idx, handler in enumerate(second_logger.handlers):
            print(f"Handler {idx}: {type(handler).__name__}")

        # Verify no new handlers were added
        assert second_handler_count == initial_handler_count, (
            f"Handler count changed from {initial_handler_count} to {second_handler_count}. "
            f"Initial handlers: {[type(h).__name__ for h in initial_logger.handlers]}, "
            f"Second handlers: {[type(h).__name__ for h in second_logger.handlers]}"
        )

    def test_log_file_creation_with_logger(self, temp_log_dir, logger):
        """Test that the log file is created in the correct directory."""
        logger.info("Trigger logger initialization")
        log_file_path = ColoredLogger._log_file_path
        assert log_file_path is not None, "Log file path is not set"
        assert os.path.exists(log_file_path), "Log file does not exist"
        assert log_file_path.startswith(str(temp_log_dir)), "Log file is not in the temporary directory"

    def test_log_file_creation(self, tmp_path):
        """Test log file creation."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)

        LoggingConfig.initialize(use_cli_args=False, log_dir=str(log_dir))

        logger = get_logger("test_file")
        logger.info("Test message")

        # Force flush and wait
        for handler in logger.handlers:
            handler.flush()
        time.sleep(0.2)

        # Check for log file
        log_files = list(log_dir.glob("*.log"))
        assert log_files, f"No log files found in {log_dir}"

        content = log_files[0].read_text()
        assert "Test message" in content

    def test_log_message_format(self, capture_logs):
        """Test that log messages are formatted correctly."""
        logger = get_logger("format_test")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        assert "Test message" in output, f"Message not found in output: {output!r}"
        assert "format_test" in output, f"Logger name not found in output: {output!r}"
        assert "INFO" in output, f"Log level not found in output: {output!r}"

    def test_log_levels(self):
        """Test that all log levels work as expected."""
        # Clear output
        test_stdout.clear()

        # Get a fresh logger with DEBUG level
        logger = get_logger("levels_test", verbose="DEBUG")

        # Replace stdout handlers with test_stdout handlers
        replace_handlers_for_logger(logger.logger)

        # Make sure all handlers capture DEBUG level
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, CriticalExitHandler):
                handler.setLevel(logging.DEBUG)

        # Log messages
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Disable SystemExit on critical messages
        CriticalExitHandler.disable_exit(True)
        logger.critical("Critical message")

        # Force flush all handlers
        for handler in logger.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Get output
        output = test_stdout.getvalue()

        # Check messages
        assert "Debug message" in output
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output
        assert "Critical message" in output

    def test_multiprocessing_logging(self, tmp_path, capture_logs, capsys):
        """Test logging in multiprocessing context."""
        import time
        from multiprocessing import Process, Queue

        log_dir = tmp_path / "mp_logs"
        log_dir.mkdir()

        def worker(q, log_dir):
            LoggingConfig.initialize(use_cli_args=False, log_dir=str(log_dir), colored_console=False)
            logger = get_logger("worker")
            logger.info("Worker 0 started")
            q.put(True)

        q = Queue()
        p = Process(target=worker, args=(q, log_dir))
        p.start()
        p.join()

        # Wait for log file
        time.sleep(0.2)

        # Check both output and log file
        output = capture_logs.getvalue() + capsys.readouterr().out
        log_files = list(log_dir.glob("*.log"))

        assert log_files, "No log files created"
        log_content = log_files[0].read_text()

        assert (
            "Worker 0 started" in output or "Worker 0 started" in log_content
        ), f"Worker message not found in output: {output} or file: {log_content}"

    def test_logger_reset(self, temp_log_dir):
        """Test that resetting the logger works as expected."""
        logger = get_logger(name="test_logger", verbose="DEBUG")
        initial_log_file = ColoredLogger._log_file_path

        with mock.patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=1)
            ColoredLogger.reset(new_file=True)
            new_log_file = ColoredLogger._log_file_path
            assert initial_log_file != new_log_file

    def test_critical_exit_handler(self):
        """Test that the CriticalExitHandler exits on critical logs."""
        LoggingConfig.initialize(use_cli_args=False, **{"exit_on_critical": True})

        # Make sure the handler isn't disabled
        CriticalExitHandler.disable_exit(False)

        # Reset logger configuration to pick up changes
        ColoredLogger.reset(new_file=True)

        # Get a fresh logger
        logger = get_logger("critical_test", verbose="DEBUG")

        with pytest.raises(SystemExit):
            logger.critical("Critical error occurred")

    def test_colored_formatter_output(self):
        """Test that the ColoredFormatter adds colors to log levels."""
        # For this test require colored console output configuration
        LoggingConfig.initialize(use_cli_args=False, **{"colored_console": True})

        # Reset with fresh state
        ColoredLogger.reset(new_file=True)
        test_stdout.clear()

        # Get new logger
        logger = get_logger("color_test", verbose="DEBUG")

        # Replace the stdout handler
        python_logger = logger.logger

        for handler in list(python_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, CriticalExitHandler):
                python_logger.removeHandler(handler)
                test_handler = logging.StreamHandler(test_stdout)
                test_handler.setFormatter(handler.formatter)
                test_handler.setLevel(handler.level)
                python_logger.addHandler(test_handler)

        # Log and verify format
        logger.info("Colored message")

        # Force flush
        for handler in python_logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        output = test_stdout.getvalue()

        # Check for color codes
        assert "\033[92m" in output
        assert "Colored message" in output

    def test_file_handler_rotation(self, temp_log_dir):
        """Test that the file handler rotates logs correctly."""
        log_file_path = ColoredLogger._log_file_path
        logger = get_logger("rotation_test", verbose="DEBUG")

        # Write enough messages to trigger rotation
        for i in range(1000):
            logger.info(f"Message {i}")

        rotated_files = [f for f in os.listdir(temp_log_dir) if f.startswith("app_") and f.endswith(".log")]
        assert len(rotated_files) > 1  # Ensure rotation occurred

    def test_update_logger_level(self):
        """Test that update_logger_level changes the log level of an existing logger."""
        # Clear existing test output
        test_stdout.clear()

        # Create a logger with INFO level
        logger1 = get_logger("test_update_level", "INFO")
        assert logger1.level == logging.INFO

        # Replace handlers to use test_stdout
        replace_handlers_for_logger(logger1.logger)

        # Log messages at different levels
        logger1.info("This should appear")
        logger1.debug("This should not appear")

        # Force flush handlers
        for handler in logger1.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check output
        output = test_stdout.getvalue()
        assert "This should appear" in output
        assert "This should not appear" not in output

        # Clear output for next test
        test_stdout.clear()

        # Update the log level to DEBUG
        ColoredLogger.update_logger_level("test_update_level", "DEBUG")
        assert logger1.level == logging.DEBUG

        # Log messages again
        logger1.info("This should still appear")
        logger1.debug("This should now appear")

        # Force flush handlers
        for handler in logger1.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check output again
        output = test_stdout.getvalue()
        assert "This should still appear" in output
        assert "This should now appear" in output

        # Clear output for next test
        test_stdout.clear()

        # Update to a more restrictive level
        ColoredLogger.update_logger_level("test_update_level", "WARNING")
        assert logger1.level == logging.WARNING

        # Log messages again
        logger1.warning("This warning should appear")
        logger1.info("This info should not appear")

        # Force flush handlers
        for handler in logger1.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check output again
        output = test_stdout.getvalue()
        assert "This warning should appear" in output
        assert "This info should not appear" not in output

    def test_level_setter(self):
        """Test that the level setter properly updates console handlers."""
        # Clear existing test output
        test_stdout.clear()

        # Create a logger with an initial level
        logger = get_logger("test_level_setter", "INFO")

        # Replace handlers to use test_stdout
        replace_handlers_for_logger(logger.logger)

        # Log messages at different levels
        logger.info("Info message should appear")
        logger.debug("Debug message should not appear")

        # Force flush handlers
        for handler in logger.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check output
        output = test_stdout.getvalue()
        assert "Info message should appear" in output
        assert "Debug message should not appear" not in output

        # Clear output for next test
        test_stdout.clear()

        # Use the level setter to change the level
        logger.level = logging.DEBUG

        # Log message at DEBUG level
        logger.debug("Debug message should now appear")

        # Force flush handlers
        for handler in logger.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check output
        output = test_stdout.getvalue()
        assert "Debug message should now appear" in output

        # Test that it doesn't affect file handlers
        # Save the current file handler level
        file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, MultiProcessingLog):
                file_handler = handler
                original_level = handler.level
                break

        # Clear output for next test
        test_stdout.clear()

        # Set a more restrictive level
        logger.level = logging.ERROR

        # Verify file handler level is unchanged
        if file_handler:
            assert file_handler.level == original_level, "File handler level should not change"

        # Log messages
        logger.warning("Warning should not appear")
        logger.error("Error should appear")

        # Force flush handlers
        for handler in logger.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Check output
        output = test_stdout.getvalue()
        assert "Warning should not appear" not in output
        assert "Error should appear" in output

    def test_level_setter_affects_only_console_handlers(self):
        """Test that level setter only affects console handlers, not file or critical handlers."""
        # Create a logger
        logger = get_logger("test_level_setter_handlers", "INFO")

        # Count handlers by type before update
        console_handlers = []
        file_handlers = []
        critical_handlers = []

        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, CriticalExitHandler):
                console_handlers.append(handler)
            elif isinstance(handler, MultiProcessingLog):
                file_handlers.append(handler)
            elif isinstance(handler, CriticalExitHandler):
                critical_handlers.append(handler)

        # Record original levels
        original_console_levels = [h.level for h in console_handlers]
        original_file_levels = [h.level for h in file_handlers]
        original_critical_levels = [h.level for h in critical_handlers]

        # Change the level
        logger.level = logging.WARNING

        # Verify console handlers changed
        for i, handler in enumerate(console_handlers):
            assert handler.level == logging.WARNING, "Console handler level should be updated"
            assert handler.level != original_console_levels[i], "Console handler level should have changed"

        # Verify file handlers didn't change
        for i, handler in enumerate(file_handlers):
            assert handler.level == original_file_levels[i], "File handler level should not change"

        # Verify critical handlers didn't change
        for i, handler in enumerate(critical_handlers):
            assert handler.level == original_critical_levels[i], "Critical handler level should not change"
