"""
Priority Order Test for prismalog Configuration

This script tests the configuration priority order of prismalog,
verifying that command-line arguments take precedence over
configuration from YAML files.
"""

import os
import sys
import tempfile
from unittest.mock import patch

import pytest

from prismalog.argparser import extract_logging_args, get_argument_parser
from prismalog.log import LoggingConfig


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

    def test_env_wins_when_cli_absent_with_kwargs(self, monkeypatch):
        """
        Test priority: Env should win when CLI arg is absent, even with use_cli_args=True and **logging_args.
        Scenario: LOG_FILENAME env var set, --log-filename CLI arg NOT set.
        """
        print("\n=== Test: Env Var Wins When CLI Absent (with kwargs init) ===")
        env_value = "env_log_filename"
        default_value = LoggingConfig.DEFAULT_CONFIG.get("log_filename", "app")

        # Set environment variable
        monkeypatch.setenv("LOG_FILENAME", env_value)
        print(f"Set environment variable: LOG_FILENAME={env_value}")

        # Simulate parsing CLI args *without* --log-filename
        parser = get_argument_parser()
        cli_args = []  # No relevant CLI args
        args = parser.parse_args(cli_args)
        logging_args = extract_logging_args(args)

        print(f"Extracted logging args (should not contain log_filename): {logging_args}")
        assert "log_filename" not in logging_args, "Precondition failed: log_filename should not be in extracted args"

        # Initialize using the pattern from example.py
        LoggingConfig.initialize(use_cli_args=True, **logging_args)

        # Retrieve the value
        retrieved_value = LoggingConfig.get("log_filename")
        print(f"Retrieved log_filename: {retrieved_value} (should be {env_value})")

        # Assert: The environment variable's value should be used
        assert retrieved_value == env_value, f"Expected '{env_value}' from env var, got '{retrieved_value}'"
        assert retrieved_value != default_value, "Default value should not be used"

    def test_cli_wins_over_env_with_kwargs(self, monkeypatch):
        """
        Test priority: CLI should win over Env when both are present, with use_cli_args=True and **logging_args.
        Scenario: LOG_FILENAME env var set, --log-filename CLI arg IS set.
        """
        print("\n=== Test: CLI Wins Over Env Var (with kwargs init) ===")
        env_value = "env_should_lose"
        cli_value = "cli_should_win"
        default_value = LoggingConfig.DEFAULT_CONFIG.get("log_filename", "app")

        # Set environment variable
        monkeypatch.setenv("LOG_FILENAME", env_value)
        print(f"Set environment variable: LOG_FILENAME={env_value}")

        # Simulate parsing CLI args *with* --log-filename
        parser = get_argument_parser()
        cli_args = ["--log-filename", cli_value]  # CLI arg IS present
        args = parser.parse_args(cli_args)
        logging_args = extract_logging_args(args)

        print(f"Extracted logging args (should contain log_filename): {logging_args}")
        assert (
            logging_args.get("log_filename") == cli_value
        ), "Precondition failed: log_filename from CLI should be in extracted args"

        # Initialize using the pattern from example.py
        LoggingConfig.initialize(use_cli_args=True, **logging_args)

        # Retrieve the value
        retrieved_value = LoggingConfig.get("log_filename")
        print(f"Retrieved log_filename: {retrieved_value} (should be {cli_value})")

        # Assert: The CLI argument's value should be used
        assert retrieved_value == cli_value, f"Expected '{cli_value}' from CLI arg, got '{retrieved_value}'"
        assert retrieved_value != env_value, "Environment variable value should not be used"
        assert retrieved_value != default_value, "Default value should not be used"

    def test_env_wins_when_cli_absent_simplified_init(self, monkeypatch):
        """
        Test priority: Env should win when CLI arg is absent using simplified initialize(use_cli_args=True).
        Scenario: LOG_FILENAME env var set, --log-filename CLI arg NOT set.
        """
        print("\n=== Test: Env Var Wins When CLI Absent (simplified init) ===")
        env_value = "env_log_filename_simple"
        default_value = LoggingConfig.DEFAULT_CONFIG.get("log_filename", "app")

        # Set environment variable
        monkeypatch.setenv("LOG_FILENAME", env_value)
        print(f"Set environment variable: LOG_FILENAME={env_value}")

        # Simulate running the script *without* --log-filename CLI arg
        # We need to mock sys.argv for initialize(use_cli_args=True) to read it
        with patch.object(sys, "argv", ["script_name.py"]):  # No relevant CLI args
            print(f"Mocked sys.argv: {sys.argv}")

            # Initialize using the simplified pattern
            LoggingConfig.reset()  # Ensure clean state
            LoggingConfig.initialize(use_cli_args=True)

        # Retrieve the value
        retrieved_value = LoggingConfig.get("log_filename")
        print(f"Retrieved log_filename: {retrieved_value} (should be {env_value})")

        # Assert: The environment variable's value should be used
        assert retrieved_value == env_value, f"Expected '{env_value}' from env var, got '{retrieved_value}'"
        assert retrieved_value != default_value, "Default value should not be used"

    def test_load_raw_cli_args_without_filename(self, monkeypatch):
        """
        Verify _load_raw_cli_args doesn't include log_filename if not in sys.argv.
        """
        print("\n=== Test: _load_raw_cli_args without --log-filename ===")
        # Simulate running the script *without* --log-filename CLI arg
        with patch.object(sys, "argv", ["script_name.py"]):  # No relevant CLI args
            print(f"Mocked sys.argv: {sys.argv}")
            LoggingConfig.reset()  # Ensure clean state for internal parser
            # Call the internal method directly
            raw_cli_config = LoggingConfig._load_raw_cli_args()

        print(f"Raw CLI config loaded: {raw_cli_config}")
        # Assert that log_filename is NOT in the dictionary returned by _load_raw_cli_args
        # because it wasn't in sys.argv and has no argparse default anymore.
        assert (
            "log_filename" not in raw_cli_config
        ), "_load_raw_cli_args should not contain log_filename if not provided via CLI"

    def test_initialize_steps_env_no_cli_with_kwargs(self, monkeypatch):
        """
        Trace the config state through initialize steps with env var set, no CLI arg, using kwargs pattern.
        """
        print("\n=== Test: Initialize Steps - Env Wins When CLI Absent (with kwargs init) ===")
        env_value = "env_trace_log"
        default_value = LoggingConfig.DEFAULT_CONFIG.get("log_filename", "app")

        # Set environment variable
        monkeypatch.setenv("LOG_FILENAME", env_value)
        print(f"Set environment variable: LOG_FILENAME={env_value}")

        # Simulate parsing CLI args *without* --log-filename
        parser = get_argument_parser()
        cli_args_list = []
        args = parser.parse_args(cli_args_list)
        logging_args_extracted = extract_logging_args(args)  # Will not contain log_filename

        print(f"Extracted logging_args: {logging_args_extracted}")
        assert "log_filename" not in logging_args_extracted

        # Simulate running the script *without* --log-filename for internal parsing
        with patch.object(sys, "argv", ["script_name.py"]):
            print(f"Mocked sys.argv for initialize: {sys.argv}")

            # Initialize using the pattern from example.py
            LoggingConfig.reset()

            # 1. Collect sources
            sources = LoggingConfig._collect_configurations(
                config_file=None, use_cli_args=True, kwargs=logging_args_extracted
            )
            print(f"Collected sources: {sources}")

            # Check state after env var collection
            assert sources.get("env", {}).get("log_filename") == env_value, "Env var not collected correctly"
            # Check state after cli collection (should be empty or not contain log_filename)
            assert "log_filename" not in sources.get("cli", {}), "CLI source incorrectly contains log_filename"
            # Check state of kwargs source
            assert "log_filename" not in sources.get("kwargs", {}), "kwargs source incorrectly contains log_filename"

            # 2. Apply configurations (this is where the priority logic happens)
            LoggingConfig._apply_configurations(sources)

        # Retrieve the final value after initialize completes
        retrieved_value = LoggingConfig.get("log_filename")
        print(f"Final retrieved log_filename: {retrieved_value} (should be {env_value})")

        # Assert: The environment variable's value should be the final result
        assert retrieved_value == env_value, f"Expected '{env_value}' from env var, got '{retrieved_value}'"
        assert retrieved_value != default_value, "Default value should not be used"

    def test_github_env_wins_when_log_env_absent(self, monkeypatch):
        """
        Test priority: GITHUB_LOG_FILENAME should win when LOG_FILENAME is absent.
        """
        print("\n=== Test: GITHUB_ Env Var Wins When LOG_ Env Absent ===")
        github_env_value = "github_log_filename"
        default_value = LoggingConfig.DEFAULT_CONFIG.get("log_filename", "app")

        # Set ONLY the GITHUB_ environment variable
        monkeypatch.delenv("LOG_FILENAME", raising=False)  # Ensure LOG_FILENAME is not set
        monkeypatch.setenv("GITHUB_LOG_FILENAME", github_env_value)
        print(f"Set environment variable: GITHUB_LOG_FILENAME={github_env_value}")
        print(f"Ensured LOG_FILENAME is unset: {os.environ.get('LOG_FILENAME')}")

        # Simulate initialization without CLI args or kwargs affecting filename
        with patch.object(sys, "argv", ["script_name.py"]):
            LoggingConfig.reset()
            # Use simplified init to focus on env var loading
            LoggingConfig.initialize(use_cli_args=True)

        # Retrieve the value
        retrieved_value = LoggingConfig.get("log_filename")
        print(f"Retrieved log_filename: {retrieved_value} (should be {github_env_value})")

        # Assert: The GITHUB_ environment variable's value should be used
        assert (
            retrieved_value == github_env_value
        ), f"Expected '{github_env_value}' from GITHUB_ env var, got '{retrieved_value}'"
        assert retrieved_value != default_value, "Default value should not be used"

    def test_log_env_wins_over_github_env(self, monkeypatch):
        """
        Test priority: LOG_FILENAME should win over GITHUB_LOG_FILENAME when both are present.
        (Based on the current loop order in _load_raw_env_config)
        """
        print("\n=== Test: LOG_ Env Var Wins Over GITHUB_ Env Var ===")
        log_env_value = "log_filename_wins"
        github_env_value = "github_filename_loses"
        default_value = LoggingConfig.DEFAULT_CONFIG.get("log_filename", "app")

        # Set BOTH environment variables
        monkeypatch.setenv("LOG_FILENAME", log_env_value)
        monkeypatch.setenv("GITHUB_LOG_FILENAME", github_env_value)
        print(f"Set environment variable: LOG_FILENAME={log_env_value}")
        print(f"Set environment variable: GITHUB_LOG_FILENAME={github_env_value}")

        # Simulate initialization without CLI args or kwargs affecting filename
        with patch.object(sys, "argv", ["script_name.py"]):
            LoggingConfig.reset()
            # Use simplified init to focus on env var loading
            LoggingConfig.initialize(use_cli_args=True)

        # Retrieve the value
        retrieved_value = LoggingConfig.get("log_filename")
        print(f"Retrieved log_filename: {retrieved_value} (should be {log_env_value})")

        # Assert: The LOG_ environment variable's value should be used due to order
        assert (
            retrieved_value == log_env_value
        ), f"Expected '{log_env_value}' from LOG_ env var, got '{retrieved_value}'"
        assert retrieved_value != github_env_value, "GITHUB_ env var value should not be used"
        assert retrieved_value != default_value, "Default value should not be used"
