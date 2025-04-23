"""
Test suite for configuration processing in prismalog.

This module tests how different types of configuration values are processed
from various sources including environment variables, command-line arguments, and configuration files.
"""

import os
from unittest.mock import patch

import pytest

from prismalog.log import LoggingConfig, get_logger


class TestConfigProcessing:
    """Test configuration processing functionality."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        # Clear any environment variables that might affect tests
        self.original_env = {}
        for key in list(os.environ.keys()):
            if key.startswith("LOG_") or key.startswith("GITHUB_LOG_"):
                self.original_env[key] = os.environ[key]
                del os.environ[key]

        # Reset configuration before each test
        LoggingConfig.reset()

        # Provide the fixture result
        yield

        # Teardown - restore environment variables
        for key, value in self.original_env.items():
            os.environ[key] = value

        # Reset configuration after each test
        LoggingConfig.reset()

    def test_string_config_from_env(self):
        """Test that string configurations from environment variables are processed correctly."""
        # Test log format as a string value
        os.environ["LOG_FORMAT"] = "ENV: %(levelname)s - %(message)s"

        # Initialize with environment variable configuration
        LoggingConfig.initialize(use_cli_args=False)

        # Get the config value directly
        actual_format = LoggingConfig.get("log_format")
        expected_format = "ENV: %(levelname)s - %(message)s"

        # Print for debugging
        print(f"Expected: {expected_format}")
        print(f"Actual: {actual_format}")

        assert actual_format == expected_format, f"Format not correctly loaded from env var: {actual_format}"

    def test_numeric_config_from_env(self):
        """Test that numeric configurations from environment variables are processed correctly."""
        # Set rotation size as a numeric value
        os.environ["LOG_ROTATION_SIZE"] = "25"

        # Initialize with environment variable configuration
        LoggingConfig.initialize(use_cli_args=False)

        # Get the config value directly
        rotation_size = LoggingConfig.get("rotation_size_mb")

        # Print for debugging
        print(f"Expected: 25")
        print(f"Actual: {rotation_size}")
        print(f"Type: {type(rotation_size)}")

        assert rotation_size == 25, f"Numeric value not correctly loaded: {rotation_size}"
        assert isinstance(rotation_size, int), f"Numeric value not converted to int: {type(rotation_size)}"

    def test_bool_config_from_env(self):
        """Test that boolean configurations from environment variables are processed correctly."""
        # Test a boolean value
        os.environ["LOG_COLORED_CONSOLE"] = "false"

        # Initialize with environment variable configuration
        LoggingConfig.initialize(use_cli_args=False)

        # Get the config value directly
        colored_console = LoggingConfig.get("colored_console")

        # Print for debugging
        print(f"Expected: False")
        print(f"Actual: {colored_console}")
        print(f"Type: {type(colored_console)}")

        assert colored_console is False, f"Boolean value not correctly loaded: {colored_console}"
        assert isinstance(colored_console, bool), f"Boolean value not converted to bool: {type(colored_console)}"

    @patch("sys.argv", ["test_script.py", "--log-format", "CLI: %(levelname)s - %(message)s"])
    def test_string_config_from_cli(self):
        """Test that string configurations from CLI arguments are processed correctly."""
        # Initialize with CLI argument support
        LoggingConfig.initialize(use_cli_args=True)

        # Get the config value directly
        actual_format = LoggingConfig.get("log_format")
        expected_format = "CLI: %(levelname)s - %(message)s"

        # Print for debugging
        print(f"Expected: {expected_format}")
        print(f"Actual: {actual_format}")

        assert actual_format == expected_format, f"Format not correctly loaded from CLI: {actual_format}"

    def test_format_used_in_logging(self, capture_logs):
        """Test that the loaded format is actually used in logging."""
        # Set format in environment
        test_format = "%(levelname)s - %(message)s"
        os.environ["LOG_FORMAT"] = test_format

        LoggingConfig.initialize(use_cli_args=False, colored_console=False)  # Disable colors for consistent testing

        logger = get_logger("test_format")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        expected = "INFO - Test message"

        assert expected in output, f"Expected format not used in actual logging. Output: {output!r}"

    def test_config_file_loading(self, capture_logs, tmp_path):
        """Test loading configuration from YAML file."""
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(
            """
log_format: 'FILE: %(levelname)s - %(message)s'
colored_console: false
log_level: INFO
        """
        )

        LoggingConfig.initialize(use_cli_args=False, config_file=str(config_path))

        logger = get_logger("test_config")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        assert "FILE: INFO - Test message" in output, f"Config file format not used. Output: {output!r}"

    def test_config_priority(self, capture_logs, tmp_path):
        """Test configuration source priorities."""
        # 1. Environment variable (lowest)
        os.environ["LOG_FORMAT"] = "ENV: %(levelname)s - %(message)s"

        # 2. Config file (middle)
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text("log_format: 'FILE: %(levelname)s - %(message)s'")

        # 3. Direct kwargs (highest)
        kwargs_format = "KWARGS: %(levelname)s - %(message)s"

        LoggingConfig.initialize(
            use_cli_args=False, config_file=str(config_path), log_format=kwargs_format, colored_console=False
        )

        logger = get_logger("test_priority")
        logger.info("Test message")

        output = capture_logs.get_combined_output()
        assert "KWARGS: INFO - Test message" in output
        assert "FILE: INFO" not in output
        assert "ENV: INFO" not in output
