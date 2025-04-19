"""Tests for edge cases in prismalog using unittest style.

This test suite uses unittest style testing because:
1. It deals with complex setup/teardown patterns
2. Has systematic test scenarios
3. Requires fine-grained control over resource cleanup
4. Focuses on edge cases that benefit from unittest's structured approach
"""

import os
import shutil
import tempfile
import unittest

from prismalog.log import ColoredLogger, LoggingConfig, get_logger


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual scenarios."""

    def setUp(self):
        """Set up test environment."""
        if ColoredLogger._file_handler:
            ColoredLogger._file_handler.close()
            ColoredLogger._file_handler = None

        self.temp_dir = tempfile.mkdtemp(prefix="log_edge_test_")
        LoggingConfig.reset()

    def tearDown(self):
        """Clean up after test."""
        try:
            if ColoredLogger._file_handler:
                ColoredLogger._file_handler.close()
                ColoredLogger._file_handler = None

            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        finally:
            LoggingConfig.reset()

    def test_very_large_message(self):
        """Test logging extremely large messages."""
        LoggingConfig.initialize(use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False})

        logger = get_logger("large_message_test")

        # Test with increasingly large messages
        sizes = [1_000, 10_000, 100_000, 1_000_000]  # Up to 1MB message

        for size in sizes:
            # Create a large message
            large_message = f"Large message test {size}: " + "X" * size

            # Should handle without error
            try:
                logger.info(large_message)
                # If it doesn't raise, this is success
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"Failed to log message of size {size}: {e}")

    def test_rapid_creation(self):
        """Test creating many loggers in rapid succession."""
        LoggingConfig.initialize(use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False})

        # Create many loggers rapidly
        loggers = []
        for i in range(1000):
            loggers.append(get_logger(f"rapid_test_{i}"))

        # Log with each logger to ensure they all work
        for i, logger in enumerate(loggers):
            logger.info(f"Test message from logger {i}")

        # Success criteria is simply not crashing
        self.assertEqual(len(loggers), 1000)

    def test_null_chars_in_log(self):
        """Test logging messages with null characters."""
        LoggingConfig.initialize(use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False})

        logger = get_logger("null_char_test")

        # Log message with null characters
        message = "Message with \x00 null \x00 characters"
        logger.info(message)

        # Check the log file
        log_file = ColoredLogger._log_file_path
        with open(log_file, "r", errors="ignore") as f:
            content = f.read()

        # Should have sanitized or properly escaped the null chars
        self.assertIn("Message with ", content)
        self.assertIn("null", content)
        self.assertIn("characters", content)

    def test_non_ascii_messages(self):
        """Test logging messages with non-ASCII characters."""
        LoggingConfig.initialize(use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False})

        logger = get_logger("unicode_test")

        # Unicode test messages
        messages = [
            "Unicode: \u3053\u3093\u306b\u3061\u306f",  # Japanese
            "Emoji: 🚀 🔥 🎉 🐍",  # Emoji
            "Math: ∑(x²+y²) = ∫∫ρ²",  # Mathematical symbols
            "Russian: Привет, мир!",  # Cyrillic
            "Arabic: مرحبا بالعالم",  # Right-to-left
        ]

        for message in messages:
            logger.info(message)

        # Check log file to see if encoding handled properly
        log_file = ColoredLogger._log_file_path
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify messages were preserved
            for message in messages:
                # Extract just the message part
                msg_content = message.split(": ", 1)[1]
                self.assertIn(msg_content, content, f"Missing unicode content: {message}")
        except UnicodeDecodeError:
            self.fail("Unicode handling failed - log file not readable as UTF-8")
