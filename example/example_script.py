"""
prismalog Example Script

This script demonstrates the core features of the prismalog package,
showcasing its flexible configuration options and logging capabilities.

Key features demonstrated:
1. Command-line argument handling via prismalog.argparser
2. Debug, info, warning, error, and critical log levels
3. Automatic handling of critical messages with optional program termination
4. Command-line configuration override

Usage:
    # Run with default settings (INFO level):
    python example_script.py

    # Run with debug level:
    python example_script.py --log-level DEBUG

    # Run with custom configuration:
    python example_script.py --log-config path/to/config.yaml

    # Run with critical messages allowed (no exit):
    python example_script.py --no-exit-on-critical
"""

from prismalog.argparser import extract_logging_args, get_argument_parser
from prismalog.log import LoggingConfig, get_logger


def main() -> None:
    """Main function demonstrating logging capabilities."""
    # Create parser with standard logging arguments
    parser = get_argument_parser(description="prismalog Example")

    # Add your own arguments if needed
    parser.add_argument("--demo-mode", action="store_true", help="Run in demo mode")

    # Parse arguments
    args = parser.parse_args()

    # Extract logging arguments
    logging_args = extract_logging_args(args)

    # Initialize with extracted arguments
    LoggingConfig.initialize(use_cli_args=True, **logging_args)

    # Create logger
    logger = get_logger("example")

    # Example usage - show current settings
    logger.info(f"Current log level: {logging_args.get('default_level', 'INFO')}")
    logger.info(f"Exit on critical: {not logging_args.get('exit_on_critical', True)}")

    # Demonstrate different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Warn user about potential program termination
    if logging_args.get("exit_on_critical", True):
        logger.warning("About to log a CRITICAL message which will terminate the program")
        logger.warning("(Use --no-exit-on-critical to prevent termination)")
    else:
        logger.info("Program will continue after critical message")

    # This will terminate the program if exit_on_critical is true
    logger.critical("This is a critical message")

    # These will only be reached if exit_on_critical is false
    logger.info("Program continued after critical message")
    logger.info("This confirms exit_on_critical is disabled")


if __name__ == "__main__":
    main()
