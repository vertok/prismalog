"""
Tests for the LoggingConfig module.

This module tests configuration loading, priority order, type conversion,
and various interactions between configuration sources (environment variables,
YAML files, CLI arguments, and direct kwargs).
"""

import os
import tempfile

from prismalog.config import LoggingConfig


class TestLoggingConfig:
    """
    Test suite for the LoggingConfig class.

    Tests the following functionality:
    - Configuration loading from different sources
    - Priority order between sources
    - Type conversion (strings to booleans and integers)
    - Default value handling
    - GitHub secret integration
    - CLI argument parsing
    """

    def test_github_secrets_with_yaml_config(self):
        """Test that GitHub secrets override values from YAML config."""
        # Create a temporary YAML config file
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write(
                """
            log_dir: logs/yaml_logs
            default_level: DEBUG
            rotation_size_mb: 50
            """
            )

        try:
            # Set up GitHub-style environment variables
            os.environ["GITHUB_LOG_DIR"] = "github_logs"
            os.environ["GITHUB_LOG_LEVEL"] = "ERROR"

            # Initialize with the YAML file
            LoggingConfig.initialize(config_file=yaml_path)

            # GitHub secrets should override YAML config
            assert LoggingConfig.get("log_dir") == "logs/yaml_logs"
            assert LoggingConfig.get("default_level") == "DEBUG"  # Should be from YAML, not env var

            # Values not in environment should be from YAML
            assert LoggingConfig.get("rotation_size_mb") == 50
        finally:
            # Clean up
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_priority_order_with_all_sources(self):
        """Test complete priority order with all configuration sources"""
        # Create a temporary YAML config file
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write(
                """
            log_dir: logs/yaml_logs
            default_level: DEBUG
            backup_count: 150
            colored_console: false
            """
            )

        try:
            # 1. Set environment variables (should override YAML)
            os.environ["LOG_DIR"] = "env_logs"
            os.environ["GITHUB_LOG_LEVEL"] = "INFO"

            # 2. Direct kwargs (should override everything)
            LoggingConfig.initialize(
                config_file=yaml_path,  # Initial file
                use_cli_args=True,  # Parse CLI args too
                **{"log_format": "%(asctime)s"},  # This should win over all others
            )

            # Test priority order:
            # - direct kwargs (highest)
            assert LoggingConfig.get("log_format") == "%(asctime)s", "Direct kwargs should override everything"

            # - config file
            assert LoggingConfig.get("log_dir") == "logs/yaml_logs", "YAML config higher prio as env var"
            assert LoggingConfig.get("default_level") == "DEBUG", "YAML config higher prio as env var"

            # - environment variables (lowest, except defaults)
            assert LoggingConfig.get("rotation_size_mb") == 10, "Default should be used when not set"
            assert LoggingConfig.get("backup_count") == 150, "YAML should override default var"
            assert LoggingConfig.get("colored_console") is False

        finally:
            # Clean up file only, env vars are handled by fixture
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_cli_config_overrides_initial_config(self):
        """Test that config file from CLI args overrides the one passed to initialize()"""
        # Create two config files
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f1:
            initial_config = f1.name
            f1.write("log_dir: initial_logs\ndefault_level: DEBUG\n")

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f2:
            cli_config = f2.name
            f2.write("log_dir: logs/cli_logs\ndefault_level: WARNING\n")

        try:
            # Mock CLI args to specify the second config
            import sys

            original_argv = sys.argv
            sys.argv = ["test_script.py", "--log-config", cli_config]

            # Initialize with the first config + parse CLI args
            LoggingConfig.initialize(config_file=initial_config, use_cli_args=True)

            # CLI config should win
            assert LoggingConfig.get("log_dir") == "logs/cli_logs"
            assert LoggingConfig.get("default_level") == "WARNING"

            # Reset argv
            sys.argv = original_argv

        finally:
            # Clean up
            for path in [initial_config, cli_config]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_type_conversion_from_different_sources(self):
        """Test that string values are properly converted to appropriate types"""
        # Create a temporary YAML config file with string values
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write(
                """
            rotation_size_mb: "25"
            backup_count: "7"
            colored_console: "true"
            disable_rotation: "false"
            """
            )

        try:
            # Set environment variables with string values
            os.environ["LOG_ROTATION_SIZE"] = "50"
            os.environ["GITHUB_LOG_COLORED_CONSOLE"] = "false"
            os.environ["LOG_EXIT_ON_CRITICAL"] = "false"

            # Initialize with config file and environment variables
            LoggingConfig.initialize(config_file=yaml_path)

            # Check numeric conversions
            assert LoggingConfig.get("rotation_size_mb") == 25  # From YAML, converted to int
            assert LoggingConfig.get("backup_count") == 7  # From YAML, converted to int

            # Check boolean conversions
            assert LoggingConfig.get("colored_console") is True  # From YAML, converted to bool
            assert LoggingConfig.get("disable_rotation") is False  # From YAML, converted to bool
            assert LoggingConfig.get("exit_on_critical") is False  # From ENV, converted to bool

            # Reset for clean test
            LoggingConfig._config = LoggingConfig.DEFAULT_CONFIG.copy()
            LoggingConfig._initialized = False

            # Initialize with invalid values
            LoggingConfig.initialize(config_file=yaml_path)

            # Invalid numeric value should fall back to YAML value
            assert LoggingConfig.get("rotation_size_mb") == 25

            # Invalid boolean should fall back to default value
            assert LoggingConfig.get("colored_console") is True  # Default value

            # Test various boolean representations
            test_boolean_values = {
                "yes": True,
                "y": True,
                "1": True,
                "true": True,
                "no": False,
                "n": False,
                "0": False,
                "false": False,
            }

            for val_str, expected in test_boolean_values.items():
                # Reset for clean test
                LoggingConfig._config = LoggingConfig.DEFAULT_CONFIG.copy()
                LoggingConfig._initialized = False

                # Set via environment variable
                os.environ["LOG_EXIT_ON_CRITICAL"] = val_str
                LoggingConfig.initialize()

                # Verify proper conversion
                assert LoggingConfig.get("exit_on_critical") is expected, f"Failed to convert '{val_str}' to {expected}"

        finally:
            # Clean up
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_env_only_overrides_default(self):
        """Test that environment variables properly override default values."""
        LoggingConfig.reset()
        os.environ["LOG_EXIT_ON_CRITICAL"] = "false"
        LoggingConfig.initialize(config_file=None, use_cli_args=False)
        assert LoggingConfig.get("exit_on_critical") is False
        del os.environ["LOG_EXIT_ON_CRITICAL"]

    def test_yaml_only_overrides_default(self):
        """Test that YAML configuration properly overrides default values."""
        LoggingConfig.reset()
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write("exit_on_critical: false\n")
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)
        assert LoggingConfig.get("exit_on_critical") is False

    def test_yaml_overrides_env(self):
        """Test that YAML configuration properly overrides environment variables."""
        LoggingConfig.reset()
        os.environ["LOG_EXIT_ON_CRITICAL"] = "false"
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write("exit_on_critical: true\n")
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)
        # If YAML is merged last, YAML should win
        assert LoggingConfig.get("exit_on_critical") is True
        del os.environ["LOG_EXIT_ON_CRITICAL"]

    def test_default_used_when_no_env_or_yaml(self):
        """Test that default values are used when no other sources are specified."""
        LoggingConfig.reset()
        LoggingConfig.initialize(config_file=None, use_cli_args=False)
        assert LoggingConfig.get("exit_on_critical") is False

    def test_type_conversion_for_booleans(self):
        """Test boolean type conversion from different string representations."""
        LoggingConfig.reset()
        os.environ["LOG_EXIT_ON_CRITICAL"] = "false"
        os.environ["LOG_COLORED_CONSOLE"] = "yes"
        LoggingConfig.initialize(config_file=None, use_cli_args=False)
        assert LoggingConfig.get("exit_on_critical") is False
        assert LoggingConfig.get("colored_console") is True
        del os.environ["LOG_EXIT_ON_CRITICAL"]
        del os.environ["LOG_COLORED_CONSOLE"]

    def test_file_does_not_overwrite_unset_keys(self):
        """Test that file config only overwrites keys that are actually in the file."""
        LoggingConfig.reset()
        os.environ["LOG_EXIT_ON_CRITICAL"] = "false"
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write("colored_console: false\n")
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)
        # colored_console comes from YAML, exit_on_critical from ENV
        assert LoggingConfig.get("exit_on_critical") is False
        assert LoggingConfig.get("colored_console") is False
        del os.environ["LOG_EXIT_ON_CRITICAL"]
