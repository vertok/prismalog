"""
prismalog Example Script

This script demonstrates the core features of the prismalog package,
showcasing its flexible configuration options and logging capabilities.

Key features demonstrated:
1. Configuration via YAML file
2. Debug, info, warning, error, and critical log levels
3. Automatic handling of critical messages with optional program termination
4. Command-line configuration override

The script outputs logs of various severity levels and demonstrates the
'exit_on_critical' feature that can automatically terminate a program
when a critical issue is detected. This behavior is configurable through
the YAML configuration file.

Two modes are demonstrated:
- With exit_on_critical=True: Program terminates on critical messages
- With exit_on_critical=False: Program continues executing after critical logs

Usage:
    # Run with default configuration:
    python example_script.py

    # Run with custom configuration:
    python example_script.py --log-config path/to/config.yaml

    # Run with configuration that disables termination on critical messages:
    python example_script.py --log-config example/config_no_exit.yaml
"""
import argparse
import os
from prismalog.log import get_logger, LoggingConfig

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="prismalog Example Script")

    # Add logging configuration flag
    parser.add_argument('--log-config', '--logging-conf',
                       dest='config_file',
                       default="example/config.yaml",
                       help='Path to logging configuration file')

    return parser.parse_args()

def main():
    """Main function demonstrating logging capabilities."""
    # Parse command-line arguments
    args = parse_args()

    # Initialize with configuration file
    if args.config_file:
        if os.path.exists(args.config_file):
            LoggingConfig.initialize(config_file=args.config_file)
            LoggingConfig._debug_print(f"Using logging configuration from: {args.config_file}")
        else:
            LoggingConfig._debug_print(f"Warning: Config file {args.config_file} not found. Using defaults.")
            LoggingConfig.initialize()
    else:
        LoggingConfig.initialize(config_file="example/config.yaml")
        LoggingConfig._debug_print("Using default configuration from example/config.yaml")

    # Get exit_on_critical setting to inform user
    exit_setting = LoggingConfig.get("exit_on_critical", True)

    # Create logger
    logger = get_logger("example")

    # Example usage
    logger.info(f"Current 'exit_on_critical' setting: {exit_setting}")
    logger.info("This is using the configuration from the specified file")
    logger.debug("Debug is enabled from the config")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Warn user about potential program termination
    if exit_setting:
        logger.warning("About to log a CRITICAL message which will terminate the program")
        logger.warning("(To prevent termination, use a config with exit_on_critical: false)")

    # This will terminate the program if exit_on_critical is true
    logger.critical("This is a critical message. Program will terminate if exit_on_critical=True.")

    # These will only be reached if exit_on_critical is false
    logger.info("Program continued after critical message (exit_on_critical=False)")
    logger.error("This message shows the program didn't terminate")

if __name__ == "__main__":
    main()
