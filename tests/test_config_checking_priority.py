"""Test the loading order and priority of different configuration sources."""

import os
import shutil
import tempfile
import unittest

from prismalog.log import LoggingConfig


class TestConfigurationLoading(unittest.TestCase):
    """Test configuration loading from different sources and their priority."""

    def setUp(self):
        """Set up temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp(prefix="config_loading_test_")

    def tearDown(self):
        """Clean up temporary directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_yaml_loading_sequence_verbose(self):
        """Test the exact sequence of configuration loading with detailed output."""
        yaml_path = os.path.join(self.temp_dir, "config.yaml")

        # Create a YAML file with specific values
        with open(yaml_path, "w") as f:
            f.write(
                """
            log_dir: logs/yaml_logs
            default_level: DEBUG
            rotation_size_mb: 50
            backup_count: 8
            """
            )

        # Step 1: Load the config_file directly and check values
        direct_config = LoggingConfig.load_from_file(yaml_path)
        self.assertEqual(direct_config.get("log_dir"), "logs/yaml_logs")
        self.assertEqual(direct_config.get("default_level"), "DEBUG")
        self.assertEqual(direct_config.get("rotation_size_mb"), 50)
        self.assertEqual(direct_config.get("backup_count"), 8)

        # Reset for clean state
        LoggingConfig.reset()

        # Step 2: Initialize with the config_file parameter
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)
        full_config = LoggingConfig.get_config()
        self.assertEqual(LoggingConfig.get("log_dir"), "logs/yaml_logs")
        self.assertEqual(LoggingConfig.get("default_level"), "DEBUG")
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50)
        self.assertEqual(LoggingConfig.get("backup_count"), 8)

        # Reset for clean state
        LoggingConfig.reset()

        # Step 3: Set environment variables AND use config_file
        os.environ["GITHUB_LOG_DIR"] = "github_logs"
        os.environ["GITHUB_LOG_LEVEL"] = "ERROR"

        # Initialize with both sources
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)

        # Environment variables should not override YAML values
        self.assertEqual(
            LoggingConfig.get("log_dir"), "logs/yaml_logs", "GitHub env var should not override log_dir from YAML"
        )
        self.assertEqual(
            LoggingConfig.get("default_level"), "DEBUG", "GitHub env var should not override YAML configurations"
        )

        # But values not in environment should come from YAML
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50, "rotation_size_mb should still be 50 from YAML")
        self.assertEqual(LoggingConfig.get("backup_count"), 8, "backup_count should still be 8 from YAML")

        # Step 4: Add another env var for rotation_size_mb
        os.environ["LOG_ROTATION_SIZE"] = "25"

        # Reset and initialize again
        LoggingConfig.reset()
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)

        # All env vars should not override YAML
        self.assertEqual(LoggingConfig.get("log_dir"), "logs/yaml_logs")
        self.assertEqual(LoggingConfig.get("default_level"), "DEBUG")
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50)
        self.assertEqual(LoggingConfig.get("backup_count"), 8)

        # Step 5: Direct kwargs should have highest priority
        LoggingConfig.reset()
        LoggingConfig.initialize(
            config_file=yaml_path, use_cli_args=False, **{"rotation_size_mb": 100, "backup_count": 10}
        )
        kwargs_config = LoggingConfig.get_config()
        print(f"Config after kwargs + env vars + YAML: {kwargs_config}")

        self.assertEqual(LoggingConfig.get("log_dir"), "logs/yaml_logs", "log_dir should be from YAML")
        self.assertEqual(LoggingConfig.get("default_level"), "DEBUG", "default_level should be DEBUG from YAML")
        self.assertEqual(
            LoggingConfig.get("rotation_size_mb"), 100, "rotation_size_mb should be 100 from kwargs_config"
        )
        self.assertEqual(LoggingConfig.get("backup_count"), 10, "backup_count should be 10 from kwargs_config")

    def create_yaml_config(self, config_dict):
        """Create a temporary YAML config file with the given contents."""
        import yaml

        yaml_path = os.path.join(self.temp_dir, "test_config.yaml")

        with open(yaml_path, "w") as f:
            yaml.dump(config_dict, f)

        return yaml_path

    def test_yaml_values_preserved(self):
        """Test that YAML values not in environment are preserved."""
        # Create YAML with multiple values
        yaml_path = self.create_yaml_config(
            {
                "log_dir": "logs/yaml_logs",
                "default_level": "DEBUG",
                "rotation_size_mb": 50,
                "backup_count": 8,
                "colored_console": False,
            }
        )

        # Set only some environment variables
        os.environ["GITHUB_LOG_DIR"] = "github_logs"
        os.environ["GITHUB_LOG_LEVEL"] = "ERROR"

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)

        # Values from environment should override YAML
        self.assertEqual(LoggingConfig.get("log_dir"), "logs/yaml_logs", "YAML variable should override env")
        self.assertEqual(LoggingConfig.get("default_level"), "DEBUG", "YAML variable should override env")

        # Values not in environment should be preserved from YAML
        self.assertEqual(
            LoggingConfig.get("rotation_size_mb"), 50, "YAML value should be preserved when not in environment"
        )
        self.assertEqual(LoggingConfig.get("backup_count"), 8, "YAML value should be preserved when not in environment")
        self.assertEqual(
            LoggingConfig.get("colored_console"), False, "YAML value should be preserved when not in environment"
        )

    def test_standard_env_vars(self):
        """Test that standard (non-GitHub) environment variables override YAML."""
        # Create YAML config
        yaml_path = self.create_yaml_config(
            {"log_dir": "logs/yaml_logs", "default_level": "DEBUG", "rotation_size_mb": 50}
        )

        # Set standard environment variable
        os.environ["LOG_ROTATION_SIZE"] = "25"

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)

        # Standard environment variable should override YAML
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50, "YAML variable should override env")

        # Other YAML values should be preserved
        self.assertEqual(LoggingConfig.get("log_dir"), "logs/yaml_logs", "YAML value should be preserved")
        self.assertEqual(LoggingConfig.get("default_level"), "DEBUG", "YAML value should be preserved")

    def test_environment_priority(self):
        """Test the priority between different environment variable formats."""
        # Create simple YAML config
        yaml_path = self.create_yaml_config({"log_dir": "logs/yaml_logs", "default_level": "WARNING"})

        # Set multiple environment variables for the same setting
        os.environ["LOG_DIR"] = "standard_logs"
        os.environ["LOG_BACKUP_COUNT"] = "25"
        os.environ["GITHUB_LOG_DIR"] = "github_logs"
        os.environ["GITHUB_LOG_ROTATION_SIZE"] = "30"

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False, **{"log_format": "%(asctime)s"})

        self.assertEqual(LoggingConfig.get("log_format"), "%(asctime)s", "CLI variables should override all sources")
        self.assertEqual(
            LoggingConfig.get("backup_count"), 25, "converted ENV variables should have priority over standard ones"
        )
        self.assertEqual(
            LoggingConfig.get("rotation_size_mb"),
            30,
            "converted GITHUB variables should have priority over standard ones",
        )
        self.assertEqual(LoggingConfig.get("log_dir"), "logs/yaml_logs", "YAML variables should have priority")

    def test_kwargs_override_all(self):
        """Test that direct kwargs override both YAML and environment variables."""
        # Create YAML config
        yaml_path = self.create_yaml_config(
            {"log_dir": "logs/yaml_logs", "default_level": "WARNING", "rotation_size_mb": 50}
        )

        # Set environment variables
        os.environ["GITHUB_LOG_DIR"] = "github_logs"
        os.environ["LOG_ROTATION_SIZE"] = "25"

        # Initialize with config file, env vars, and direct kwargs
        LoggingConfig.initialize(
            config_file=yaml_path, use_cli_args=False, log_dir="logs/kwarg_logs", default_level="DEBUG"
        )

        # Direct kwargs should override everything
        self.assertEqual(
            LoggingConfig.get("log_dir"), "logs/kwarg_logs", "Direct kwargs should override environment variables"
        )
        self.assertEqual(LoggingConfig.get("default_level"), "DEBUG", "Direct kwargs should override YAML")

        # Environment should override YAML for non-kwarg values
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50, "YAML should override env for values not in kwargs")

    def test_numeric_conversion(self):
        """Test that numeric values are properly converted."""
        # Create YAML with string and numeric values
        yaml_path = self.create_yaml_config(
            {"rotation_size_mb": "50", "backup_count": 8}  # String in YAML  # Number in YAML
        )

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)

        # Both should be converted to integers
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50), "YAML should be used"
        self.assertIsInstance(
            LoggingConfig.get("rotation_size_mb"), int, "String from environment should be converted to int"
        )

        # When no environment variable exists, YAML value should be used and converted
        self.assertEqual(LoggingConfig.get("backup_count"), 8), "YAML should be used"
        self.assertIsInstance(LoggingConfig.get("backup_count"), int, "Numeric YAML value should remain as int")
