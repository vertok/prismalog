"""
Priority Order Test for prismalog Configuration

This script tests the configuration priority order of prismalog,
verifying that command-line arguments take precedence over
configuration from YAML files.

Tests:
1. YAML config only
2. CLI args only
3. CLI args overriding YAML config
4. Environment variables with lower priority than CLI/YAML
"""

import os
import tempfile

from prismalog.argparser import extract_logging_args, get_argument_parser
from prismalog.log import LoggingConfig, get_logger


def create_test_config(config_content):
    """Create a temporary config file with the given content"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    temp.write(config_content)
    temp.close()
    return temp.name


def run_priority_test():
    """Run tests to verify configuration priority order"""
    log = get_logger("priority_test")

    # Create test config with different values than defaults
    yaml_config = """
    level: ERROR
    log_dir: yaml_logs
    colored_console: false
    exit_on_critical: false
    log_format: '%(asctime)s [YAML] %(message)s'
    external_loggers:
      requests: CRITICAL
    """

    config_path = create_test_config(yaml_config)
    print(f"Created test config at {config_path}")

    # Test 1: YAML config only
    print("\n=== Test 1: YAML Configuration Only ===")
    LoggingConfig.reset()
    LoggingConfig.initialize(config_file=config_path)

    print(f"Log level (should be ERROR): {LoggingConfig.get('default_level')}")
    print(f"Log directory (should be yaml_logs): {LoggingConfig.get('log_dir')}")
    print(f"Colored console (should be False): {LoggingConfig.get('colored_console')}")

    # Test 2: CLI args only
    print("\n=== Test 2: CLI Arguments Only ===")
    LoggingConfig.reset()

    # Create parser and parse CLI args
    parser = get_argument_parser()
    cli_args = ["--log-level", "DEBUG", "--log-dir", "cli_logs"]
    args = parser.parse_args(cli_args)
    logging_args = extract_logging_args(args)

    LoggingConfig.initialize(use_cli_args=True, **logging_args)

    print(f"Log level (should be DEBUG): {LoggingConfig.get('default_level')}")
    print(f"Log directory (should be cli_logs): {LoggingConfig.get('log_dir')}")

    # Test 3: CLI args overriding YAML config
    print("\n=== Test 3: CLI Arguments Overriding YAML ===")
    LoggingConfig.reset()

    # Create parser with both YAML and CLI args
    parser = get_argument_parser()
    cli_args = [
        "--log-level",
        "INFO",  # Should override YAML's ERROR
        "--log-dir",
        "override_logs",  # Should override YAML's yaml_logs
        "--log-config",
        config_path,  # Load the YAML config too
    ]
    args = parser.parse_args(cli_args)
    logging_args = extract_logging_args(args)

    LoggingConfig.initialize(use_cli_args=True, **logging_args)

    print(f"Log level (should be INFO, not ERROR): {LoggingConfig.get('default_level')}")
    print(f"Log directory (should be override_logs, not yaml_logs): {LoggingConfig.get('log_dir')}")
    print(f"Colored console (should still be False from YAML): {LoggingConfig.get('colored_console')}")

    # Test 4: Environment variables
    print("\n=== Test 4: Environment Variables ===")
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["LOG_DIR"] = "env_logs"

    LoggingConfig.reset()

    # CLI should override env vars
    parser = get_argument_parser()
    cli_args = ["--log-level", "DEBUG"]
    args = parser.parse_args(cli_args)
    logging_args = extract_logging_args(args)

    LoggingConfig.initialize(use_cli_args=True, **logging_args)

    print(f"Log level (should be DEBUG, not WARNING): {LoggingConfig.get('default_level')}")
    print(f"Log directory (should be env_logs from env var): {LoggingConfig.get('log_dir')}")

    # Clean up
    os.unlink(config_path)

    # Clear environment variables
    del os.environ["LOG_LEVEL"]
    del os.environ["LOG_DIR"]


if __name__ == "__main__":
    run_priority_test()
