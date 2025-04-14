import os
import tempfile
from prismalog.config import LoggingConfig

class TestLoggingConfig:

    def setup_method(self):
        """Reset LoggingConfig before each test"""
        LoggingConfig._config = LoggingConfig.DEFAULT_CONFIG.copy()
        LoggingConfig._initialized = False

    def test_github_secrets_with_yaml_config(self):
        """Test that GitHub secrets override values from YAML config"""
        # Create a temporary YAML config file
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            yaml_path = f.name
            f.write("""
            log_dir: yaml_logs
            default_level: DEBUG
            rotation_size_mb: 50
            """)

        try:
            # Set up GitHub-style environment variables
            os.environ["GITHUB_LOGGING_DIR"] = "github_logs"
            os.environ["GITHUB_LOGGING_VERBOSE"] = "ERROR"

            # Initialize with the YAML file
            LoggingConfig.initialize(config_file=yaml_path)

            # GitHub secrets should override YAML config
            assert LoggingConfig.get("log_dir") == "github_logs"
            assert LoggingConfig.get("default_level") == "ERROR"

            # Values not in environment should be from YAML
            assert LoggingConfig.get("rotation_size_mb") == 50
        finally:
            # Clean up
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)
            os.environ.pop("GITHUB_LOGGING_DIR", None)
            os.environ.pop("GITHUB_LOGGING_VERBOSE", None)

    def test_priority_order_with_all_sources(self):
        """Test complete priority order with all configuration sources"""
        # Create a temporary YAML config file
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            yaml_path = f.name
            f.write("""
            log_dir: yaml_logs
            default_level: DEBUG
            rotation_size_mb: 50
            backup_count: 10
            colored_console: false
            """)

        try:
            # 1. Set environment variables (should override YAML)
            os.environ["LOGGING_DIR"] = "env_logs"
            os.environ["GITHUB_LOGGING_VERBOSE"] = "INFO"

            # 2. Create command line args (should override env vars)
            # Mock sys.argv for parse_args
            import sys
            original_argv = sys.argv
            sys.argv = ["test_script.py", "--log-config", "cli_config.yaml"]

            # 3. Direct kwargs (should override everything)
            LoggingConfig.initialize(
                config_file=yaml_path,  # Initial file
                default_level="CRITICAL",  # This should win over all others
                parse_args=True  # Parse CLI args too
            )

            # Test priority order:
            # - direct kwargs (highest)
            assert LoggingConfig.get("default_level") == "CRITICAL"

            # - environment variables
            assert LoggingConfig.get("log_dir") == "env_logs"

            # - config file (lowest, except defaults)
            assert LoggingConfig.get("rotation_size_mb") == 50
            assert LoggingConfig.get("backup_count") == 10
            assert LoggingConfig.get("colored_console") is False

            # defaults (for values not in any other source)
            assert LoggingConfig.get("multiprocess_safe") is True

            # Reset argv
            sys.argv = original_argv

        finally:
            # Clean up
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)
            os.environ.pop("LOGGING_DIR", None)
            os.environ.pop("GITHUB_LOGGING_VERBOSE", None)

    def test_cli_config_overrides_initial_config(self):
        """Test that config file from CLI args overrides the one passed to initialize()"""
        # Create two config files
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f1:
            initial_config = f1.name
            f1.write("log_dir: initial_logs\ndefault_level: DEBUG\n")

        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f2:
            cli_config = f2.name
            f2.write("log_dir: cli_logs\ndefault_level: WARNING\n")

        try:
            # Mock CLI args to specify the second config
            import sys
            original_argv = sys.argv
            sys.argv = ["test_script.py", "--log-config", cli_config]

            # Initialize with the first config + parse CLI args
            LoggingConfig.initialize(config_file=initial_config, parse_args=True)

            # CLI config should win
            assert LoggingConfig.get("log_dir") == "cli_logs"
            assert LoggingConfig.get("default_level") == "WARNING"

            # Reset argv
            sys.argv = original_argv

        finally:
            # Clean up
            for path in [initial_config, cli_config]:
                if os.path.exists(path):
                    os.unlink(path)