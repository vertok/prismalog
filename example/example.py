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

The example shows how prismalog integrates with Python's argparse module
to handle command-line options for verbosity and configuration files.
It also illustrates how the 'exit_on_critical' setting affects program
behavior when critical errors are encountered.

Usage:
    # Run with default settings (INFO level):
    python example.py

    # Run with increased verbosity:
    python example.py --verbose DEBUG

    # Run with custom configuration:
    python example.py --log-config config.yaml

    # Run with both options:
    python example.py --verbose DEBUG --log-config config.yaml
"""
import argparse
import os
from prismalog import get_logger, LoggingConfig

def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description='Colored Logger Example')
    parser.add_argument('--verbose', type=str.upper,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO',
                        help='Set the logging level (case-insensitive)')
    parser.add_argument('--logging-conf', '--log-config',
                        dest='config_file',
                        help='Path to logging configuration YAML file')
    return parser.parse_args()

def main() -> None:
    """
    Main function to run the logger example.

    It initializes the logger based on the verbosity flag and configuration,
    then logs several messages with different log levels.
    """
    args = parse_args()

    # Initialize logging configuration if provided
    if args.config_file:
        if os.path.exists(args.config_file):
            LoggingConfig.initialize(config_file=args.config_file)
            LoggingConfig._debug_print(f"Using logging configuration from: {args.config_file}")
        else:
            LoggingConfig._debug_print(f"Warning: Config file {args.config_file} not found. Using defaults.")

    # Create logger with the desired log level
    log = get_logger('example', args.verbose)

    # Example usage: Logging messages at different levels
    log.debug("This is a debug message")  # Will be logged if --verbose is set
    log.info("This is an info message")
    log.warning("This is a warning message")
    log.error("This is an error message")

    # Output current exit_on_critical setting
    exit_setting = LoggingConfig.get("exit_on_critical", True)
    log.info(f"Current 'exit_on_critical' setting: {exit_setting}")
    log.critical("This is a critical message. Program will terminate if exit_on_critical=True.")

    # This will only be reached if exit_on_critical=False in the config
    log.error("This message will only appear if exit_on_critical=False.")
    log.info("Program completed successfully.")

if __name__ == "__main__":
    main()
