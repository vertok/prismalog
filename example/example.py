"""
prismalog Basic Example

This script demonstrates the fundamental usage of the prismalog package,
including command-line integration, configuration handling, and logging
at different levels.

Features demonstrated:
1. Command-line argument handling for logging configuration
2. Loading configuration from YAML files
3. Creating and using loggers with different verbosity levels
4. Messages at Debug, Info, Warning, Error, and Critical levels
5. Configurable critical message handling (program termination)

Available Configuration Options:
    --log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL] - Set the default logging level
    --log-config PATH - Path to logging configuration YAML file
    --log-dir PATH - Directory where log files will be stored
    --log-format FORMAT - Custom format for log messages (e.g. "%(asctime)s - %(message)s")

    The following can be set in a config file or using environment variables:
    - colored_console: Whether to use colored output (default: True)
    - disable_rotation: Whether to disable log rotation (default: False)
    - rotation_size_mb: Size in MB before rotating log files (default: 10)
    - backup_count: Number of backup files to keep (default: 5)
    - exit_on_critical: Whether to exit on CRITICAL errors (default: True)

Usage Examples:
    # Run with default settings (INFO level):
    python example.py

    # Run with increased verbosity:
    python example.py --log-level DEBUG

    # Run with custom configuration:
    python example.py --log-config config.yaml

    # Run with custom log format:
    python example.py --log-format "%(asctime)s [%(levelname)s] %(message)s"

    # Run with custom log directory:
    python example.py --log-dir ./my_logs
"""

from prismalog.argparser import extract_logging_args, get_argument_parser
from prismalog.log import LoggingConfig, get_logger


def main() -> None:
    # Create parser with standard logging arguments
    parser = get_argument_parser(description="prismalog Example")

    # Add own arguments if needed
    parser.add_argument("--demo-mode", action="store_true", help="Run in demo mode")

    # Parse arguments
    args = parser.parse_args()

    # Extract logging arguments
    logging_args = extract_logging_args(args)

    # Initialize with extracted arguments
    LoggingConfig.initialize(use_cli_args=True, **logging_args)

    # Get logger
    log = get_logger("example")

    # Log some messages
    log.info("prismalog Example")
    log.debug("This is a debug message")
    log.info("This is an info message")
    log.warning("This is a warning message")
    log.error("This is an error message")

    # Will exit if exit_on_critical is True (default)
    if not logging_args.get("exit_on_critical", True):
        log.info("About to log a critical message (won't exit)")
    else:
        log.info("About to log a critical message (will exit)")

    log.critical("This is a critical message")
    log.info("If you see this, exit_on_critical was disabled")


if __name__ == "__main__":
    main()
