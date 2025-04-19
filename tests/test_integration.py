"""Tests for integration points in prismalog."""

import os
import shutil
import tempfile
import unittest

from conftest import capture_stdout

from prismalog.log import ColoredLogger, LoggingConfig, get_logger


class TestIntegration(unittest.TestCase):
    """Test integration with Python's standard library and other modules."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="log_integration_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_stdout_redirection(self):
        """Test logging with stdout redirection."""
        # Reset state
        LoggingConfig.reset()

        # Configure logging
        LoggingConfig.initialize(
            use_cli_args=False,
            **{
                "log_dir": self.temp_dir,
                "colored_console": False,  # Disable colors for easier testing
                "console_level": "DEBUG",  # Ensure all messages go to console
            },
        )

        # Test with the capture_stdout context manager
        with capture_stdout() as captured:
            # Get a logger and write some messages
            logger = get_logger("stdout_test")
            logger.info("Test info message")
            logger.error("Test error message")

            for i in range(5):
                logger.info(f"Message to be captured {i}")
                logger.error(f"Error to be captured {i}")

            # Check that output was captured
            output = captured.getvalue()
            self.assertTrue(len(output) > 0, "No output was captured")
            self.assertIn("Test info message", output)
            self.assertIn("Error to be captured", output)

    def test_exception_logging(self):
        """Test logging of exceptions."""
        LoggingConfig.initialize(use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False})

        logger = get_logger("exception_test")

        try:
            # Generate exception
            0 / 0  # Division by zero
        except Exception as e:
            logger.exception("Caught an exception")

        # Check log file
        log_file = ColoredLogger._log_file_path
        with open(log_file, "r") as f:
            content = f.read()

        # Should contain exception details
        self.assertIn("Caught an exception", content)
        self.assertIn("ZeroDivisionError", content)
        self.assertIn("Traceback", content)

    def test_env_var_config(self):
        """Test configuration through environment variables."""
        # Set environment variables
        os.environ["LOG_DIR"] = self.temp_dir
        os.environ["LOG_LEVEL"] = "WARNING"
        os.environ["LOG_COLORED_CONSOLE"] = "0"

        # Initialize without explicit config to use env vars
        LoggingConfig.initialize()

        # Verify settings were applied
        self.assertEqual(LoggingConfig.get("log_dir"), self.temp_dir)
        self.assertEqual(LoggingConfig.get("default_level"), "WARNING")
        self.assertEqual(LoggingConfig.get("colored_console"), False)

        # Clean up
        del os.environ["LOG_DIR"]
        del os.environ["LOG_LEVEL"]
        del os.environ["LOG_COLORED_CONSOLE"]
