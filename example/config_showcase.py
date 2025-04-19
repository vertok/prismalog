"""
prismalog Configuration Keys Showcase

This example demonstrates all the configuration keys available in prismalog
and how to set them using the standard argument parser.

Configuration Keys:
1. log_dir - Location where log files are stored
2. default_level - Default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
3. rotation_size_mb - Size threshold for log file rotation in megabytes
4. backup_count - Number of backup log files to keep when rotating
5. log_format - Format string for log messages
6. colored_console - Whether to use colored output in console
7. disable_rotation - Whether to disable log file rotation
8. exit_on_critical - Whether to exit the program on critical errors
9. test_mode - Special mode for testing (not used in normal operation)

Usage:
  # Show default configuration:
  python config_showcase.py

  # Set logging level:
  python config_showcase.py --log-level DEBUG

  # Custom log format:
  python config_showcase.py --log-format "%(asctime)s [%(levelname)s] %(message)s"

  # Disable exit on critical:
  python config_showcase.py --no-exit-on-critical

  # Customize log directory:
  python config_showcase.py --log-dir ./my_logs
"""

import os
from time import sleep

from prismalog import LoggingConfig, get_logger
from prismalog.argparser import get_argument_parser, extract_logging_args


def main():
    # Get the standard argument parser
    parser = get_argument_parser(description="prismalog Configuration Showcase")

    # Parse arguments and extract logging-specific ones
    args = parser.parse_args()
    logging_args = extract_logging_args(args)

    # Initialize with CLI args support and direct kwargs
    LoggingConfig.initialize(use_cli_args=True, **logging_args)

    # Create logger
    log = get_logger("config_demo")

    # Display each configuration key and its current value
    log.info("prismalog Configuration Keys Showcase")
    log.info("===================================")

    # 1. log_dir - Where logs are stored
    log_dir = LoggingConfig.get("log_dir")
    log.info(f"1. log_dir = {log_dir}")
    log.info(f"   Log files location: {os.path.abspath(log_dir)}")
    log.info(f"   Set with: --log-dir ./path/to/logs")

    # 2. default_level - Default logging level
    default_level = LoggingConfig.get("default_level")
    log.info(f"2. default_level = {default_level}")
    log.info(f"   Controls minimum log level to record")
    log.info(f"   Set with: --log-level DEBUG")

    # 3. rotation_size_mb - When logs are rotated
    rotation_size = LoggingConfig.get("rotation_size_mb")
    log.info(f"3. rotation_size_mb = {rotation_size}")
    log.info(f"   Log files rotate after reaching this size in MB")
    log.info(f"   Set with: --rotation-size 20")

    # 4. backup_count - How many backups to keep
    backup_count = LoggingConfig.get("backup_count")
    log.info(f"4. backup_count = {backup_count}")
    log.info(f"   Number of rotated log files to keep")
    log.info(f"   Set with: --backup-count 10")

    # 5. log_format - Format of log messages
    log_format = LoggingConfig.get("log_format")
    log.info(f"5. log_format = {log_format}")
    log.info(f"   Controls how log messages are formatted")
    log.info(f'   Set with: --log-format "%(asctime)s [%(levelname)s] %(message)s"')

    # 6. colored_console - Color output in terminal
    colored_console = LoggingConfig.get("colored_console")
    log.info(f"6. colored_console = {colored_console}")
    log.info(f"   Whether log messages use colors in the console")
    log.info(f"   Set with: --no-color to disable")

    # 7. disable_rotation - Turn off rotation
    disable_rotation = LoggingConfig.get("disable_rotation")
    log.info(f"7. disable_rotation = {disable_rotation}")
    log.info(f"   Whether log file rotation is disabled")
    log.info(f"   Set with: --disable-rotation")

    # 8. exit_on_critical - Program termination behavior
    exit_on_critical = LoggingConfig.get("exit_on_critical")
    log.info(f"8. exit_on_critical = {exit_on_critical}")
    log.info(f"   Whether to terminate the program on critical logs")
    log.info(f"   Set with: --no-exit-on-critical to disable")

    # 9. test_mode - For testing the logger itself
    test_mode = LoggingConfig.get("test_mode")
    log.info(f"9. test_mode = {test_mode}")
    log.info(f"   Debug mode for testing the package (rarely used in applications)")
    log.info(f"   Set with: --test-mode")

    log.info("\nThese CLI arguments are handled by prismalog.argparser!")
    log.info("They're standardized across all prismalog applications")

    # Demonstrate some types of messages
    log.info("\nExample log messages at different levels:")
    log.debug("This is a DEBUG message (only shown if level is DEBUG)")
    log.info("This is an INFO message")
    log.warning("This is a WARNING message")
    log.error("This is an ERROR message")

    # Demonstrate exit_on_critical
    if exit_on_critical:
        log.info("\nAbout to log a CRITICAL message, which will terminate the program")
        log.info("To prevent termination, run with: --no-exit-on-critical")
        sleep(1)  # Give user time to read
        log.critical("This is a CRITICAL message - program will exit now")
    else:
        log.info("\nCRITICAL messages won't terminate the program (--no-exit-on-critical was used)")
        log.critical("This is a CRITICAL message - program continues")
        log.info("Program completed successfully")


if __name__ == "__main__":
    main()