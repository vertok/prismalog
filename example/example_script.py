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

    # Run with critical messages allowed to exit:
    python example_script.py --exit-on-critical
"""

from time import sleep

from prismalog.argparser import extract_logging_args, get_argument_parser
from prismalog.log import LoggingConfig, get_logger


def main() -> None:
    """Main function demonstrating logging capabilities."""
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

    # Create logger
    logger = get_logger("example")
    exit_on_critical = logging_args.get("exit_on_critical", True)
    log_level = logging_args.get("default_level", "INFO")

    # Example usage - show current settings
    logger.info("Current log level: %s", log_level)
    logger.info("Exit on critical: %s", exit_on_critical)

    # Demonstrate different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Warn user about potential program termination
    if exit_on_critical:
        logger.info("\nAbout to log a CRITICAL message, which will terminate the program")
        logger.info("This happens because you used: --exit-on-critical")
        sleep(1)
        logger.critical("This is a CRITICAL message - program will exit now")
    else:
        logger.info("\nCRITICAL messages won't terminate the program (default behavior)")
        logger.critical("This is a CRITICAL message - program continues")
        logger.info("Program completed successfully")
        logger.info("To change this behavior, use --exit-on-critical")

    # This will not terminate the program since exit_on_critical is false
    logger.critical("This is a critical message")

    # These will only be reached if exit_on_critical is false
    logger.info("Program continued after critical message")
    logger.info("This confirms exit_on_critical is disabled")


if __name__ == "__main__":
    main()
