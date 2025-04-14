import os
import pytest
import logging
import sys
from unittest import mock
from datetime import datetime, timedelta
from prismalog.log import ColoredLogger, CriticalExitHandler, MultiProcessingLog, get_logger
from prismalog.config import LoggingConfig
from tests.conftest import test_stdout, test_stderr


class TestColoredLogger:
    """Test suite for the ColoredLogger and related functionality."""

    @pytest.fixture(scope="class")
    def temp_log_dir(self, tmp_path_factory):
        """Fixture to create a temporary directory for logs."""
        log_dir = tmp_path_factory.mktemp("logs")
        os.environ["LOGGING_DIR"] = str(log_dir)
        return log_dir

    @pytest.fixture(scope="class")
    def logger(self, temp_log_dir):
        """Fixture to create a logger instance."""
        return get_logger(name="test_logger", verbose="DEBUG")

    @pytest.fixture(autouse=True)
    def setup_test_method(self, request):
        """Set up fresh environment for each test."""
        # Configure specifically for this test
        LoggingConfig.initialize(parse_args=False, **{
            "colored_console": True,
            "exit_on_critical": request.function.__name__ == "test_critical_exit_handler"
        })

        # Disable exit by default, except for critical test
        CriticalExitHandler.disable_exit(request.function.__name__ != "test_critical_exit_handler")

        # For tests that check output, replace stdout handlers
        if request.function.__name__ in ["test_logger_initialization_stdout",
                                         "test_log_message_format",
                                         "test_log_levels",
                                         "test_colored_formatter_output"]:
            self._setup_test_handlers()

        yield

    def _setup_test_handlers(self):
        """Set up special handlers for test output capture."""
        # First check ColoredLogger's initialized loggers
        for name in list(ColoredLogger._initialized_loggers.keys()):
            logger = logging.getLogger(name)
            self._replace_handlers_for_logger(logger)

        # Also check other loggers that might exist
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name not in ColoredLogger._initialized_loggers:
                logger = logging.getLogger(name)
                self._replace_handlers_for_logger(logger)

    def _replace_handlers_for_logger(self, logger):
        """Replace stdout handlers with test_stdout handlers for a logger."""
        if not logger.handlers:
            return

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

    def test_logger_initialization_stdout(self):
        """Test that the logger initializes correctly."""
        # Clear output before test
        test_stdout.clear()

        # Get a fresh logger
        logger = get_logger("test_stdout", verbose="DEBUG")

        # Access the underlying Python logger object
        python_logger = logger.logger

        # Replace stdout handlers with test_stdout handlers
        for handler in list(python_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, CriticalExitHandler):
                python_logger.removeHandler(handler)
                test_handler = logging.StreamHandler(test_stdout)
                test_handler.setFormatter(handler.formatter)
                test_handler.setLevel(handler.level)
                python_logger.addHandler(test_handler)

        # Log a message
        logger.info("Test message")

        # Force handlers to flush
        for handler in python_logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()

        # Check the output
        output = test_stdout.getvalue()
        assert "Test message" in output, f"Expected 'Test message' but got: {output!r}"

    def test_logger_initialization(self, logger):
        """Test logger initialization sets up the proper handlers."""
        # Verify the presence of a right handlers
        assert len(logger.handlers) >= 2, "Logger should have at least 2 handlers"

        # Check that at least one handler is a StreamHandler
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) > 0, "Logger should have at least one StreamHandler"

        # Verify the presence of a file handler
        file_handlers = [h for h in logger.handlers if isinstance(h, MultiProcessingLog)]
        assert len(file_handlers) > 0, "Logger should have a MultiProcessingLog handler"

    def test_logger_no_redundant_handlers(self, logger):
        """Test that the logger does not add redundant handlers."""
        initial_handler_count = len(logger.logger.handlers)
        logger2 = get_logger(name="test_logger", verbose="DEBUG")
        assert len(logger2.logger.handlers) == initial_handler_count

    def test_log_file_creation(self, temp_log_dir, logger):
        """Test that the log file is created in the correct directory."""
        logger.info("Trigger logger initialization")
        log_file_path = ColoredLogger._log_file_path
        assert log_file_path is not None, "Log file path is not set"
        assert os.path.exists(log_file_path), "Log file does not exist"
        assert log_file_path.startswith(str(temp_log_dir)), "Log file is not in the temporary directory"

    def test_log_message_format(self, logger, captured_output):
        """Test that log messages are formatted correctly."""
        logger.info("Test message")
        assert "Test message" in captured_output.out
        assert "INFO" in captured_output.out

    def test_log_levels(self):
        """Test that all log levels work as expected."""
        # Clear output
        test_stdout.clear()

        # Get a fresh logger with DEBUG level
        logger = get_logger("levels_test", verbose="DEBUG")

        # Replace stdout handlers with test_stdout handlers
        self._replace_handlers_for_logger(logger.logger)

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
            if hasattr(handler, 'flush'):
                handler.flush()

        # Get output
        output = test_stdout.getvalue()

        # Check messages
        assert "Debug message" in output
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output
        assert "Critical message" in output

    def test_multiprocessing_logging(self, temp_log_dir):
        """Test that multiprocessing logging works without redundancy."""
        from multiprocessing import Process

        def worker_process(worker_id):
            logger = get_logger(f"worker_{worker_id}", verbose="DEBUG")
            logger.info(f"Worker {worker_id} started")
            logger.info(f"Worker {worker_id} finished")

        processes = []
        for i in range(4):
            p = Process(target=worker_process, args=(i,))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        # Verify the log file contains entries from all processes
        log_file_path = ColoredLogger._log_file_path
        with open(log_file_path, "r") as f:
            log_content = f.read()

        for i in range(4):
            assert f"Worker {i} started" in log_content
            assert f"Worker {i} finished" in log_content

    def test_logger_reset(self, temp_log_dir):
        """Test that resetting the logger works as expected."""
        logger = get_logger(name="test_logger", verbose="DEBUG")
        initial_log_file = ColoredLogger._log_file_path

        with mock.patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=1)
            ColoredLogger.reset(new_file=True)
            new_log_file = ColoredLogger._log_file_path
            assert initial_log_file != new_log_file

    def test_critical_exit_handler(self):
        """Test that the CriticalExitHandler exits on critical logs."""
        LoggingConfig.initialize(parse_args=False, **{
            "exit_on_critical": True
        })

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
        LoggingConfig.initialize(parse_args=False, **{
            "colored_console": True
        })

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
            if hasattr(handler, 'flush'):
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

        rotated_files = [
            f for f in os.listdir(temp_log_dir) if f.startswith("app_") and f.endswith(".log")
        ]
        assert len(rotated_files) > 1  # Ensure rotation occurred
