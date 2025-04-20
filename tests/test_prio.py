"""
Priority Order Test for prismalog Configuration

This script tests the configuration priority order of prismalog,
verifying that command-line arguments take precedence over
configuration from YAML files.
"""

import os
import tempfile

import pytest

from prismalog.argparser import extract_logging_args, get_argument_parser
from prismalog.log import LoggingConfig, get_logger


class TestConfigPriority:
    """Test class for verifying configuration priority in prismalog"""

    @pytest.fixture
    def yaml_config_file(self):
        """Create a temporary YAML config file for testing"""
        yaml_config = """
        default_level: ERROR
        log_dir: yaml_logs
        colored_console: false
        exit_on_critical: false
        log_format: '%(asctime)s [YAML] %(message)s'
        external_loggers:
          requests: CRITICAL
        """

        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        temp.write(yaml_config)
        temp.close()

        yield temp.name

        # Clean up
        if os.path.exists(temp.name):
            os.unlink(temp.name)

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset LoggingConfig before and after each test"""
        LoggingConfig.reset()
        yield
        LoggingConfig.reset()

    def test_yaml_config_only(self, yaml_config_file):
        """Test that YAML configuration is properly loaded"""
        print("\n=== Test: YAML Config Only ===")
        LoggingConfig.initialize(config_file=yaml_config_file)

        level = LoggingConfig.get("default_level")
        log_dir = LoggingConfig.get("log_dir")
        colored = LoggingConfig.get("colored_console")
        requests_level = LoggingConfig.get("external_loggers", {}).get("requests")

        print(f"Log level: {level} (should be ERROR)")
        print(f"Log dir: {log_dir} (should be yaml_logs)")
        print(f"Colored console: {colored} (should be False)")
        print(f"Requests logger level: {requests_level} (should be CRITICAL)")

        assert level == "ERROR", f"Expected ERROR level, got {level}"
        assert log_dir == "yaml_logs", f"Expected yaml_logs dir, got {log_dir}"
        assert colored is False, f"Expected colored_console False, got {colored}"
        assert requests_level == "CRITICAL", f"Expected CRITICAL for requests, got {requests_level}"

    def test_cli_args_only(self):
        """Test that CLI arguments are properly parsed"""
        print("\n=== Test: CLI Arguments Only ===")
        parser = get_argument_parser()
        cli_args = ["--log-level", "DEBUG", "--log-dir", "cli_logs"]
        args = parser.parse_args(cli_args)
        logging_args = extract_logging_args(args)

        print(f"Extracted logging args: {logging_args}")
        LoggingConfig.initialize(use_cli_args=True, **logging_args)

        level = LoggingConfig.get("default_level")
        log_dir = LoggingConfig.get("log_dir")

        print(f"Log level: {level} (should be DEBUG)")
        print(f"Log dir: {log_dir} (should be cli_logs)")

        assert level == "DEBUG", f"Expected DEBUG level, got {level}"
        assert log_dir == "cli_logs", f"Expected cli_logs dir, got {log_dir}"

    def test_cli_args_override_yaml(self, yaml_config_file):
        """Test that CLI args override YAML config settings"""
        print("\n=== Test: CLI Arguments Override YAML ===")
        parser = get_argument_parser()
        cli_args = [
            "--log-level",
            "INFO",  # Should override YAML's ERROR
            "--log-dir",
            "override_logs",  # Should override YAML's yaml_logs
            "--log-config",
            yaml_config_file,  # Load the YAML config too
            "--exit-on-critical",  # Should override YAML's exit_on_critical
        ]
        args = parser.parse_args(cli_args)
        logging_args = extract_logging_args(args)

        print(f"Extracted logging args with config file: {logging_args}")
        LoggingConfig.initialize(use_cli_args=True, **logging_args)

        level = LoggingConfig.get("default_level")
        log_dir = LoggingConfig.get("log_dir")
        colored = LoggingConfig.get("colored_console")
        exit_critical = LoggingConfig.get("exit_on_critical")

        print(f"Log level: {level} (should be INFO, not ERROR)")
        print(f"Log dir: {log_dir} (should be override_logs, not yaml_logs)")
        print(f"Colored console: {colored} (should be False from YAML)")
        print(f"Exit on critical: {exit_critical} (should be True from CLI)")

        # CLI args should take precedence
        assert level == "INFO", f"Expected INFO level, got {level}"
        assert log_dir == "override_logs", f"Expected override_logs dir, got {log_dir}"

        # YAML values not specified in CLI should be preserved
        assert colored is True, f"Expected colored_console True, got {colored}"
        assert exit_critical is True, f"Expected exit_on_critical True, got {exit_critical}"

    def test_env_vars_with_cli_override(self, monkeypatch):
        """Test that CLI args override environment variables"""
        print("\n=== Test: Environment Variables with CLI Override ===")
        # Set environment variables
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("LOG_DIR", "env_logs")

        print("Set environment variables: LOG_LEVEL=WARNING, LOG_DIR=env_logs")

        # Parse CLI args that override LOG_LEVEL but not LOG_DIR
        parser = get_argument_parser()
        cli_args = ["--log-level", "DEBUG"]
        args = parser.parse_args(cli_args)
        logging_args = extract_logging_args(args)

        print(f"Extracted logging args: {logging_args}")
        LoggingConfig.initialize(use_cli_args=True, **logging_args)

        level = LoggingConfig.get("default_level")
        log_dir = LoggingConfig.get("log_dir")

        print(f"Log level: {level} (should be DEBUG, not WARNING)")
        print(f"Log dir: {log_dir} (should be env_logs)")

        # CLI log level should override env var
        assert level == "DEBUG", f"Expected DEBUG level, got {level}"

        # Env var log_dir should be used since not specified in CLI
        assert log_dir == "env_logs", f"Expected env_logs dir, got {log_dir}"
