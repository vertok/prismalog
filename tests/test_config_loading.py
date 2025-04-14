"""Test the loading order and priority of different configuration sources."""

import unittest
import tempfile
import os
import shutil
from prismalog import LoggingConfig

class TestConfigurationLoading(unittest.TestCase):
    """Test configuration loading from different sources and their priority."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="config_loading_test_")
        LoggingConfig.reset()

        # Save original environment variables to restore later
        self.original_env = {}
        for env_var in ['LOG_DIR', 'LOG_LEVEL', 'GITHUB_LOGGING_DIR',
                        'GITHUB_LOGGING_VERBOSE', 'LOG_ROTATION_SIZE_MB']:
            if env_var in os.environ:
                self.original_env[env_var] = os.environ[env_var]

        # Clear environment variables for clean testing
        for env_var in self.original_env:
            del os.environ[env_var]

    def tearDown(self):
        """Clean up after tests."""
        # Restore environment variables
        for env_var, value in self.original_env.items():
            os.environ[env_var] = value

        # Remove any added environment variables
        env_vars_to_clean = [
            'LOG_DIR', 'LOG_LEVEL', 'LOG_ROTATION_SIZE_MB',
            'GITHUB_LOGGING_DIR', 'GITHUB_LOGGING_VERBOSE'
        ]

        for env_var in env_vars_to_clean:
            if env_var in os.environ and env_var not in self.original_env:
                del os.environ[env_var]

        # Clean up temp directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Reset config for other tests
        LoggingConfig.reset()

    def test_yaml_loading_sequence_verbose(self):
        """Test the exact sequence of configuration loading with detailed output."""
        yaml_path = os.path.join(self.temp_dir, "config.yaml")

        # Create a YAML file with specific values
        with open(yaml_path, 'w') as f:
            f.write("""
            log_dir: yaml_logs
            default_level: DEBUG
            rotation_size_mb: 50
            backup_count: 8
            """)

        # Step 1: Load the config_file directly and check values
        print("\n--- Step 1: Direct load_from_file ---")
        direct_config = LoggingConfig.load_from_file(yaml_path)
        print(f"Config after direct load: {direct_config}")
        self.assertEqual(direct_config.get("log_dir"), "yaml_logs")
        self.assertEqual(direct_config.get("default_level"), "DEBUG")
        self.assertEqual(direct_config.get("rotation_size_mb"), 50)
        self.assertEqual(direct_config.get("backup_count"), 8)

        # Reset for clean state
        LoggingConfig.reset()

        # Step 2: Initialize with the config_file parameter
        print("\n--- Step 2: Initialize with config_file ---")
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False)
        full_config = LoggingConfig.get_config()
        print(f"Config after initialize with YAML: {full_config}")
        self.assertEqual(LoggingConfig.get("log_dir"), "yaml_logs")
        self.assertEqual(LoggingConfig.get("default_level"), "DEBUG")
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50)
        self.assertEqual(LoggingConfig.get("backup_count"), 8)

        # Reset for clean state
        LoggingConfig.reset()

        # Step 3: Set environment variables AND use config_file
        print("\n--- Step 3: Env vars + config_file (GitHub secrets style) ---")
        os.environ["GITHUB_LOGGING_DIR"] = "github_logs"
        os.environ["GITHUB_LOGGING_VERBOSE"] = "ERROR"

        # Initialize with both sources
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False)
        github_config = LoggingConfig.get_config()
        print(f"Config after env vars + YAML: {github_config}")

        # Environment variables should override YAML values
        self.assertEqual(LoggingConfig.get("log_dir"), "github_logs",
                        "GitHub env var should override YAML log_dir")
        self.assertEqual(LoggingConfig.get("default_level"), "ERROR",
                        "GitHub env var should override YAML default_level")

        # But values not in environment should come from YAML
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 50,
                        "rotation_size_mb should still be 50 from YAML")
        self.assertEqual(LoggingConfig.get("backup_count"), 8,
                        "backup_count should still be 8 from YAML")

        # Step 4: Add another env var for rotation_size_mb
        print("\n--- Step 4: Adding more env vars ---")
        os.environ["LOG_ROTATION_SIZE_MB"] = "25"

        # Reset and initialize again
        LoggingConfig.reset()
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False)
        updated_config = LoggingConfig.get_config()
        print(f"Config after all env vars + YAML: {updated_config}")

        # All env vars should override YAML, but other YAML values remain
        self.assertEqual(LoggingConfig.get("log_dir"), "github_logs")
        self.assertEqual(LoggingConfig.get("default_level"), "ERROR")
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 25)
        self.assertEqual(LoggingConfig.get("backup_count"), 8)

        # Step 5: Direct kwargs should have highest priority
        LoggingConfig.reset()
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False, **{
            "rotation_size_mb": 100,
            "backup_count": 10
        })
        kwargs_config = LoggingConfig.get_config()
        print(f"Config after kwargs + env vars + YAML: {kwargs_config}")

        self.assertEqual(LoggingConfig.get("log_dir"), "github_logs")
        self.assertEqual(LoggingConfig.get("default_level"), "ERROR")
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), 100)
        self.assertEqual(LoggingConfig.get("backup_count"), 10)

    def create_yaml_config(self, config_dict):
        """Create a temporary YAML config file with the given contents."""
        import yaml
        yaml_path = os.path.join(self.temp_dir, "test_config.yaml")

        with open(yaml_path, 'w') as f:
            yaml.dump(config_dict, f)

        return yaml_path

    def test_yaml_values_preserved(self):
        """Test that YAML values not in environment are preserved."""
        # Create YAML with multiple values
        yaml_path = self.create_yaml_config({
            'log_dir': 'yaml_logs',
            'default_level': 'DEBUG',
            'rotation_size_mb': 50,
            'backup_count': 8,
            'colored_console': False
        })

        # Set only some environment variables
        os.environ['GITHUB_LOGGING_DIR'] = 'github_logs'
        os.environ['GITHUB_LOGGING_VERBOSE'] = 'ERROR'

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False)

        # Values from environment should override YAML
        self.assertEqual(LoggingConfig.get('log_dir'), 'github_logs',
                        "Environment variable should override YAML")
        self.assertEqual(LoggingConfig.get('default_level'), 'ERROR',
                        "Environment variable should override YAML")

        # Values not in environment should be preserved from YAML
        self.assertEqual(LoggingConfig.get('rotation_size_mb'), 50,
                        "YAML value should be preserved when not in environment")
        self.assertEqual(LoggingConfig.get('backup_count'), 8,
                        "YAML value should be preserved when not in environment")
        self.assertEqual(LoggingConfig.get('colored_console'), False,
                        "YAML value should be preserved when not in environment")

    def test_standard_env_vars(self):
        """Test that standard (non-GitHub) environment variables override YAML."""
        # Create YAML config
        yaml_path = self.create_yaml_config({
            'log_dir': 'yaml_logs',
            'default_level': 'DEBUG',
            'rotation_size_mb': 50
        })

        # Set standard environment variable
        os.environ['LOG_ROTATION_SIZE_MB'] = '25'

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False)

        # Standard environment variable should override YAML
        self.assertEqual(LoggingConfig.get('rotation_size_mb'), 25,
                        "Standard environment variable should override YAML")

        # Other YAML values should be preserved
        self.assertEqual(LoggingConfig.get('log_dir'), 'yaml_logs',
                        "YAML value should be preserved")
        self.assertEqual(LoggingConfig.get('default_level'), 'DEBUG',
                        "YAML value should be preserved")

    def test_environment_priority(self):
        """Test the priority between different environment variable formats."""
        # Create simple YAML config
        yaml_path = self.create_yaml_config({
            'log_dir': 'yaml_logs',
            'default_level': 'WARNING'
        })

        # Set multiple environment variables for the same setting
        os.environ['LOG_DIR'] = 'standard_logs'
        os.environ['GITHUB_LOGGING_DIR'] = 'github_logs'

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False)

        # GitHub variables should have higher priority than standard ones
        self.assertEqual(LoggingConfig.get('log_dir'), 'github_logs',
                        "GitHub environment variables should have priority")

    def test_kwargs_override_all(self):
        """Test that direct kwargs override both YAML and environment variables."""
        # Create YAML config
        yaml_path = self.create_yaml_config({
            'log_dir': 'yaml_logs',
            'default_level': 'WARNING',
            'rotation_size_mb': 50
        })

        # Set environment variables
        os.environ['GITHUB_LOGGING_DIR'] = 'github_logs'
        os.environ['LOG_ROTATION_SIZE_MB'] = '25'

        # Initialize with config file, env vars, and direct kwargs
        LoggingConfig.initialize(
            config_file=yaml_path,
            parse_args=False,
            log_dir='kwarg_logs',
            default_level='DEBUG'
        )

        # Direct kwargs should override everything
        self.assertEqual(LoggingConfig.get('log_dir'), 'kwarg_logs',
                        "Direct kwargs should override environment variables")
        self.assertEqual(LoggingConfig.get('default_level'), 'DEBUG',
                        "Direct kwargs should override YAML")

        # Environment should override YAML for non-kwarg values
        self.assertEqual(LoggingConfig.get('rotation_size_mb'), 25,
                        "Environment should override YAML for values not in kwargs")

    def test_numeric_conversion(self):
        """Test that numeric values are properly converted."""
        # Create YAML with string and numeric values
        yaml_path = self.create_yaml_config({
            'rotation_size_mb': '50',  # String in YAML
            'backup_count': 8          # Number in YAML
        })

        # Set environment variable as string
        os.environ['LOG_ROTATION_SIZE_MB'] = '25'

        # Initialize with config file
        LoggingConfig.initialize(config_file=yaml_path, parse_args=False)

        # Both should be converted to integers
        self.assertEqual(LoggingConfig.get('rotation_size_mb'), 25)
        self.assertIsInstance(LoggingConfig.get('rotation_size_mb'), int,
                             "String from environment should be converted to int")

        # When no environment variable exists, YAML value should be used and converted
        self.assertEqual(LoggingConfig.get('backup_count'), 8)
        self.assertIsInstance(LoggingConfig.get('backup_count'), int,
                             "Numeric YAML value should remain as int")
