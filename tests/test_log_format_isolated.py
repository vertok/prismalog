""" Test suite for log formatting issues in prismalog. """

import io
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import TestCase

import pytest

from prismalog.log import ColoredLogger, LoggingConfig, get_logger


@pytest.mark.usefixtures("tmp_path")
class TestLogFormattingIsolated(TestCase):
    """Isolated test suite for log formatting issues."""

    # Add color code constants
    ANSI_GREEN = "\x1b[92m"
    ANSI_RESET = "\x1b[0m"

    def setUp(self):
        """Set up test environment."""
        # Clear any existing logging configuration
        logging.root.handlers = []
        # Clear environment variables
        for k in list(os.environ):
            if k.startswith("LOG_"):
                del os.environ[k]
        # Reset logging config
        LoggingConfig.reset()

        # Create string buffer for capturing output
        self.console_output = io.StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.console_output

    def tearDown(self):
        """Clean up after each test."""
        sys.stdout = self.original_stdout
        LoggingConfig.reset()
        logging.root.handlers = []

    def test_basic_format(self):
        """Test basic log format without any configuration."""
        logger = get_logger("test_basic")
        logger.info("Basic message")
        output = self.console_output.getvalue()
        print(f"Captured output: {output!r}")
        assert "Basic message" in output

    def test_standard_format(self):
        """Test standard logging format."""
        os.environ["LOG_FORMAT"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        LoggingConfig.initialize(use_cli_args=False)

        logger = get_logger("test_format")
        logger.info("Standard format test")

        output = self.console_output.getvalue()
        print(f"Captured output: {output!r}")

        # Check parts separately to handle timestamp flexibility
        assert "test_format" in output
        assert f"{self.ANSI_GREEN}INFO{self.ANSI_RESET}" in output
        assert "Standard format test" in output

    def test_simple_format(self):
        """Test simple logging format."""
        os.environ["LOG_FORMAT"] = "%(levelname)s - %(message)s"
        LoggingConfig.initialize(use_cli_args=False)

        logger = get_logger("test_simple")
        logger.info("Simple format test")

        output = self.console_output.getvalue()
        print(f"Captured output: {output!r}")

        # Account for colored output in levelname
        expected = "\x1b[92mINFO\x1b[0m - Simple format test"
        assert expected in output

    def test_env_format(self):
        """Test log format from environment variable."""
        os.environ["LOG_FORMAT"] = "%(levelname)s - %(message)s"
        LoggingConfig.initialize(use_cli_args=False)

        logger = get_logger("test_env")
        logger.info("Environment format")

        output = self.console_output.getvalue()
        print(f"Captured output: {output!r}")

        expected = f"{self.ANSI_GREEN}INFO{self.ANSI_RESET} - Environment format"
        assert expected in output

    def test_console_vs_file_format(self):
        """Test if console and file formats are handled differently."""
        os.environ["LOG_FORMAT"] = "CONSOLE: %(levelname)s - %(message)s"
        LoggingConfig.initialize(use_cli_args=False)

        logger = get_logger("test_formats")
        logger.info("Format test")

        output = self.console_output.getvalue()
        print(f"Console output: {output!r}")

        expected = f"CONSOLE: {self.ANSI_GREEN}INFO{self.ANSI_RESET} - Format test"
        assert expected in output

    def test_capture_mechanism(self):
        """Test if our capture mechanism works correctly."""
        # Direct stdout write
        print("Direct stdout write")
        # Logger write
        logger = get_logger("test_capture")
        logger.info("Logger write")

        output = self.console_output.getvalue()
        print(f"Complete captured output: {output!r}")
        assert "Direct stdout write" in output
        assert "Logger write" in output

    def test_handler_formats(self):
        """Test how different handlers format the same message."""
        # Create both string and file output
        file_output = io.StringIO()
        file_handler = logging.StreamHandler(file_output)
        console_handler = logging.StreamHandler(self.console_output)

        # Set different formats
        file_handler.setFormatter(logging.Formatter("FILE: %(levelname)s - %(message)s"))
        console_handler.setFormatter(logging.Formatter("CONSOLE: %(levelname)s - %(message)s"))

        # Create logger with both handlers
        logger = logging.getLogger("test_handlers")
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)

        # Log a message
        logger.info("Test message")

        console_out = self.console_output.getvalue()
        file_out = file_output.getvalue()
        print(f"Console output: {console_out!r}")
        print(f"File output: {file_out!r}")

    def test_colored_formatter_behavior(self):
        """Test how ColoredFormatter affects the output."""
        from prismalog.log import ColoredFormatter

        logger = logging.getLogger("test_color")
        handler = logging.StreamHandler(self.console_output)
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("Color test")
        output = self.console_output.getvalue()
        print(f"Colored output: {output!r}")
        assert self.ANSI_GREEN in output
        assert self.ANSI_RESET in output

    def test_config_format_inheritance(self):
        """Test how format changes propagate through the logging system."""
        # Set initial format
        os.environ["LOG_FORMAT"] = "Initial: %(levelname)s - %(message)s"
        LoggingConfig.initialize(use_cli_args=False)

        logger1 = get_logger("test_format1")
        logger1.info("First message")

        # Change format
        os.environ["LOG_FORMAT"] = "Changed: %(levelname)s - %(message)s"
        LoggingConfig.initialize(use_cli_args=False)

        logger2 = get_logger("test_format2")
        logger2.info("Second message")

        output = self.console_output.getvalue()
        print(f"Sequential format output: {output!r}")

    def test_log_file_creation_and_format(self):
        """Test file logging with format verification."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            print("\nTest Setup:")
            print(f"Temp directory: {tmp_path}")

            # Ensure directory exists and is writable
            tmp_path.mkdir(parents=True, exist_ok=True)
            assert tmp_path.exists(), "Temp directory does not exist"
            assert os.access(tmp_path, os.W_OK), "Temp directory is not writable"

            # Configure logging with absolute path
            log_dir = str(tmp_path.resolve())
            print(f"Using log directory: {log_dir}")

            # Reset logging configuration
            ColoredLogger._file_handler = None
            LoggingConfig.reset()

            # Initialize with test configuration
            LoggingConfig.initialize(use_cli_args=False, log_dir=log_dir, log_format="%(levelname)s - %(message)s")

            # Verify config
            config = LoggingConfig.get_config()
            print("\nLogging Configuration:")
            print(f"log_dir: {config.get('log_dir')}")
            print(f"log_format: {config.get('log_format')}")

            # Create logger and inspect its configuration
            logger = get_logger("test_file")
            print("\nLogger Configuration:")
            print(f"Logger name: {logger.name}")
            print(f"Logger level: {logger.level}")
            print(f"Number of handlers: {len(logger.handlers)}")

            for idx, handler in enumerate(logger.handlers):
                print(f"\nHandler {idx + 1}:")
                print(f"Type: {type(handler)}")
                print(f"Level: {handler.level}")
                if hasattr(handler, "baseFilename"):
                    print(f"Base filename: {handler.baseFilename}")
                    print(f"Mode: {handler.mode}")
                    print(f"Encoding: {handler.encoding}")
                print(f"Formatter: {handler.formatter}")

            # Log multiple messages at different levels
            logger.debug("Debug test message")
            logger.info("Info test message")
            logger.warning("Warning test message")
            logger.error("Error test message")

            # Force flush all handlers
            for handler in logger.handlers:
                handler.flush()

            # Wait for file operations
            time.sleep(0.5)

            # Check directory contents
            print("\nDirectory Contents:")
            all_files = list(tmp_path.iterdir())
            print(f"All files: {[f.name for f in all_files]}")

            log_files = list(tmp_path.glob("app_*.log"))  # Check for default pattern
            print(f"Log files: {[f.name for f in log_files]}")

            if not log_files:
                print("\nFile Handler Status:")
                if hasattr(ColoredLogger, "_file_handler"):
                    fh = ColoredLogger._file_handler
                    print(f"File handler exists: {fh is not None}")
                    if fh:
                        print(f"File handler path: {getattr(fh, 'baseFilename', 'No baseFilename')}")
                        print(f"File handler mode: {getattr(fh, 'mode', 'No mode')}")
                        print(f"Is handler closed: {getattr(fh, 'closed', 'Unknown')}")

            # Assert file creation
            assert log_files, f"No log files found in {tmp_path}"

            # Verify file content
            log_file = log_files[0]
            content = log_file.read_text()
            print(f"\nFile content: {content!r}")
            assert "test message" in content.lower(), "Log messages not found in file"

    def test_handler_initialization(self):
        """Test how handlers are initialized and attached to loggers."""
        LoggingConfig.initialize(use_cli_args=False)
        logger = get_logger("test_handlers")

        print("\nHandler Configuration:")
        print(f"Number of handlers: {len(logger.handlers)}")
        for idx, handler in enumerate(logger.handlers):
            print(f"\nHandler {idx + 1}:")
            print(f"Type: {type(handler)}")
            print(f"Level: {handler.level}")
            print(f"Formatter: {type(handler.formatter)}")
            if hasattr(handler, "stream"):
                print(f"Stream type: {type(handler.stream)}")

        assert len(logger.handlers) >= 2, "Logger should have at least console and file handlers"
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers), "No StreamHandler found"

    def test_output_capture_mechanics(self):
        """Test the exact mechanics of output capture."""
        # Create both a string buffer and file for comparison
        string_output = io.StringIO()
        temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)

        try:
            # Create handlers for both outputs
            string_handler = logging.StreamHandler(string_output)
            file_handler = logging.StreamHandler(temp_file)

            # Create logger and add both handlers
            logger = logging.getLogger("test_capture")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(string_handler)
            logger.addHandler(file_handler)

            # Log some messages
            logger.info("Direct to handler")
            print("Direct to stdout", file=string_output)

            # Force flush
            string_output.flush()
            temp_file.flush()

            # Check captured output
            string_content = string_output.getvalue()
            temp_file.seek(0)
            file_content = temp_file.read()

            print("\nCapture Comparison:")
            print(f"String buffer content: {string_content!r}")
            print(f"File content: {file_content!r}")

            assert "Direct to handler" in string_content, "Handler output not captured"
            assert "Direct to stdout" in string_content, "Stdout not captured"

        finally:
            temp_file.close()
            os.unlink(temp_file.name)

    def test_colored_logger_handler_inheritance(self):
        """Test how ColoredLogger inherits and manages handlers."""
        LoggingConfig.initialize(use_cli_args=False)

        # Create multiple loggers
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")

        print("\nLogger Configuration:")
        print(f"Logger1 handlers: {len(logger1.handlers)}")
        print(f"Logger2 handlers: {len(logger2.handlers)}")

        # Log messages from both loggers
        logger1.info("Message from logger1")
        logger2.info("Message from logger2")

        # Check handler counts
        assert len(logger1.handlers) == len(logger2.handlers), "Loggers have different numbers of handlers"
        assert len(logger1.handlers) >= 2, "Logger missing expected handlers"

    def test_root_logger_interaction(self):
        """Test interaction between root logger and ColoredLogger."""
        # Store initial state
        root = logging.getLogger()
        initial_handlers = len(root.handlers)

        print(f"\nInitial root handlers: {initial_handlers}")

        # Initialize config and create logger
        LoggingConfig.initialize(use_cli_args=False)
        logger = get_logger("test_root")

        print(f"Root handlers after logger creation: {len(root.handlers)}")
        print(f"Test logger handlers: {len(logger.handlers)}")

        # Log messages
        logger.info("Test message")

        # Check handler propagation
        assert not logger.propagate, "Logger should not propagate to root"
        assert len(logger.handlers) >= 2, "Logger missing handlers"

    def test_multiprocess_handler_setup(self):
        """Test handler setup in multiprocessing context."""
        from multiprocessing import Process, Queue

        def worker(q):
            logger = get_logger("worker")
            logger.info("Worker started")
            q.put(logger.handlers[0].formatter._fmt)

        q = Queue()
        p = Process(target=worker, args=(q,))
        p.start()
        p.join()

        # Get formatter from worker process
        worker_format = q.get()
        print(f"\nWorker process formatter: {worker_format}")
        assert worker_format is not None, "Worker process logger not properly configured"

    def test_logger_propagation(self):
        """Test propagation control in ColoredLogger."""
        # Create root logger
        root = logging.getLogger()
        root_output = io.StringIO()
        root_handler = logging.StreamHandler(root_output)
        root.addHandler(root_handler)

        # Initialize our logger
        LoggingConfig.initialize(use_cli_args=False)
        logger = get_logger("test_propagate")

        # Set propagate attribute (should add this to ColoredLogger)
        logger.propagate = False

        # Log a message
        logger.info("Test propagation")

        # Check outputs
        root_content = root_output.getvalue()
        our_content = self.console_output.getvalue()

        print("\nLogger Propagation Test:")
        print(f"Root logger output: {root_content!r}")
        print(f"Our logger output: {our_content!r}")

        # Message should appear in our output but not in root's
        assert "Test propagation" in our_content
        assert "Test propagation" not in root_content
