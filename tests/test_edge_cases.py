"""Tests for edge cases in prismalog."""

import unittest
import tempfile
import os
import shutil
from prismalog import get_logger, LoggingConfig, ColoredLogger

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual scenarios."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="log_edge_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_very_large_message(self):
        """Test logging extremely large messages."""
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "colored_console": False
        })

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
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "colored_console": False
        })

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
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "colored_console": False
        })

        logger = get_logger("null_char_test")

        # Log message with null characters
        message = "Message with \x00 null \x00 characters"
        logger.info(message)

        # Check the log file
        log_file = ColoredLogger._log_file_path
        with open(log_file, 'r', errors='ignore') as f:
            content = f.read()

        # Should have sanitized or properly escaped the null chars
        self.assertIn("Message with ", content)
        self.assertIn("null", content)
        self.assertIn("characters", content)

    def test_non_ascii_messages(self):
        """Test logging messages with non-ASCII characters."""
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "colored_console": False
        })

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
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Verify messages were preserved
            for message in messages:
                # Extract just the message part
                msg_content = message.split(": ", 1)[1]
                self.assertIn(msg_content, content,
                             f"Missing unicode content: {message}")
        except UnicodeDecodeError:
            self.fail("Unicode handling failed - log file not readable as UTF-8")

    def test_permission_handling(self):
        """Test handling when log directory permissions are restricted."""
        if os.name == 'nt':  # Skip on Windows as permission model is different
            self.skipTest("Skipping permission test on Windows")

        # Create a directory with restricted permissions
        restricted_dir = os.path.join(self.temp_dir, "restricted")
        os.makedirs(restricted_dir)

        # Make it read-only
        os.chmod(restricted_dir, 0o500)  # Read + execute, but not write

        try:
            # Should handle gracefully
            LoggingConfig.initialize(parse_args=False, **{
                "log_dir": restricted_dir,
                "colored_console": True  # Should fall back to console
            })

            logger = get_logger("permission_test")
            logger.warning("This should go to console if file can't be written")

            # The test passes if previous line didn't raise an error
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Failed to handle restricted permissions: {e}")
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o700)