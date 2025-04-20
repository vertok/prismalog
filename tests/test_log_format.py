"""
Test suite for validating log format functionality in prismalog.

This module verifies that the log format configuration works correctly,
including:
- Setting format via environment variables
- Setting format via configuration file
- Setting format via direct kwargs
"""

import io
import logging
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import pytest

from prismalog.log import LoggingConfig, get_logger


class TestLogFormat:
    """Test class for log format functionality in prismalog."""

    def test_default_log_format(self, capture_logs):
        """Test default log format."""
        LoggingConfig.initialize(use_cli_args=False)
        logger = get_logger("test_default")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        assert "test_default" in output
        assert "INFO" in output
        assert "Test message" in output

    def test_custom_log_format_via_kwargs(self, capture_logs):
        """Test setting log format via direct keyword arguments."""
        custom_format = "%(levelname)s - %(name)s: %(message)s"

        LoggingConfig.initialize(use_cli_args=False, log_format=custom_format, colored_console=False)

        logger = get_logger("test_custom")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        expected = "INFO - test_custom: Test message"

        assert expected in output, f"Log entry doesn't match custom format. Output: {output!r}"

    def test_log_format_via_env_var(self, capture_logs):
        """Test setting log format via environment variable."""
        os.environ["LOG_FORMAT"] = "ENV: %(levelname)s - %(message)s"

        LoggingConfig.initialize(use_cli_args=False, colored_console=False)

        logger = get_logger("test_env")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        print(f"\nCaptured output: {output!r}")

        plain_expected = "ENV: INFO - Test message"
        color_expected = f"ENV: \x1b[92mINFO\x1b[0m - Test message"

        assert any(
            exp in output for exp in [plain_expected, color_expected]
        ), f"Log entry doesn't match environment-set format. Output: {output!r}"

    def test_log_format_priority(self, capture_logs):
        """Test that log format follows the correct priority order."""
        os.environ["LOG_FORMAT"] = "ENV: %(levelname)s - %(message)s"

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write("log_format: 'FILE: %(levelname)s - %(message)s'\n")

        try:
            kwargs_format = "KWARGS: %(levelname)s - %(message)s"

            LoggingConfig.initialize(
                use_cli_args=False, config_file=yaml_path, log_format=kwargs_format, colored_console=False
            )

            capture_logs.seek(0)
            capture_logs.truncate()

            logger = get_logger("test_priority")
            logger.info("Test priority message")

            output = capture_logs.get_combined_output()
            print(f"\nCaptured output: {output!r}")

            assert (
                "KWARGS: INFO - Test priority message" in output
            ), f"Highest priority format not used. Output: {output!r}"
            assert "FILE: INFO" not in output
            assert "ENV: INFO" not in output

        finally:
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_file_logging_works(self, tmp_path):
        """Test file logging."""
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
        assert log_files, f"No log files in {log_dir}"

        content = log_files[0].read_text()
        assert "Test message" in content
