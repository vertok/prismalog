"""
Standard command-line argument parser for prismalog logging system.

This module provides a standardized way to add prismalog-related
command line arguments to any application using the package. It enables
consistent handling of logging configuration options across different
applications and scripts.

Features:
---------
* Standardized logging arguments for all prismalog applications
* Support for configuration via command line or config file
* Automatic mapping between CLI args and LoggingConfig settings
* Integration with Python's argparse module
* Consistent argument naming conventions

Available Arguments:
--------------------
--log-config           Path to a YAML configuration file
--log-level            Set the default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
--log-dir              Directory where log files will be stored
--log-format           Format string for log messages
--log-datefmt          Format string for log timestamps
--log-filename         Base filename prefix for log files
--no-color             Disable colored console output
--disable-rotation     Disable log file rotation
--exit-on-critical     Exit program on critical errors
--rotation-size        Log file rotation size in MB
--backup-count         Number of backup log files to keep

Usage Examples:
---------------
1. Basic usage::

    from prismalog.argparser import get_argument_parser, extract_logging_args
    from prismalog.log import LoggingConfig

    # Create parser with standard logging arguments
    parser = get_argument_parser(description="My Application")

    # Add own application-specific arguments
    parser.add_argument("--my-option", help="Application-specific option")

    # Parse arguments
    args = parser.parse_args()

    # Extract and apply logging configuration
    logging_args = extract_logging_args(args)
    LoggingConfig.from_dict(logging_args)

2. Adding to an existing parser::

    import argparse
    from prismalog.argparser import add_logging_arguments, extract_logging_args

    # Create your own parser
    parser = argparse.ArgumentParser(description="My Application")
    parser.add_argument("--my-option", help="Application-specific option")

    # Add standard logging arguments
    add_logging_arguments(parser)

    # Parse and extract
    args = parser.parse_args()
    logging_args = extract_logging_args(args)
"""

import argparse
from typing import Any, Dict, Optional


class LoggingArgumentParser:
    """Helper class for adding standard logging arguments to argparse."""

    @staticmethod
    def add_arguments(parser: Optional[argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        """
        Add standard prismalog arguments to an existing parser using LoggingConfig.

        Args:
            parser: An existing ArgumentParser instance. If None, a new one is created.

        Returns:
            The ArgumentParser with prismalog arguments added
        """
        if parser is None:
            parser = argparse.ArgumentParser()

        # Config file option
        parser.add_argument("--log-config", help="Path to a YAML configuration file")

        # Standard logging arguments with case-insensitive level
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            type=str.upper,  # Simply convert to uppercase
            help="Set the default logging level (case-insensitive)",
        )

        parser.add_argument("--log-dir", help="Directory where log files will be stored")

        parser.add_argument("--log-format", help="Format string for log messages")

        parser.add_argument(
            "--log-filename",
            "--logging-filename",
            type=str,
            help="Base filename for generated log files",
        )

        # Boolean flags
        parser.add_argument(
            "--no-color",
            "--no-colors",
            dest="colored_console",
            action="store_false",
            help="Disable colored console output",
        )

        parser.add_argument(
            "--disable-rotation", dest="disable_rotation", action="store_true", help="Disable log file rotation"
        )

        parser.add_argument(
            "--exit-on-critical",
            dest="exit_on_critical",
            action="store_true",
            help="Exit the program on critical errors",
        )

        # Numeric options
        parser.add_argument("--rotation-size", type=int, dest="rotation_size_mb", help="Log file rotation size in MB")

        parser.add_argument("--backup-count", type=int, help="Number of backup log files to keep")

        return parser

    @staticmethod
    def create_parser(description: Optional[str] = None) -> argparse.ArgumentParser:
        """
        Create a new ArgumentParser with prismalog arguments.

        Args:
            description: Description for the ArgumentParser

        Returns:
            A new ArgumentParser with prismalog arguments
        """
        parser = argparse.ArgumentParser(description=description)
        return LoggingArgumentParser.add_arguments(parser)

    @staticmethod
    def extract_logging_args(args: argparse.Namespace) -> Dict[str, Any]:
        """
        Extract logging-related arguments from parsed args based on LoggingConfig defaults.

        Args:
            args: The parsed args from ArgumentParser.parse_args()

        Returns:
            Dictionary with only the logging-related arguments mapped to LoggingConfig keys.
        """
        # Define mappings from CLI arg names to config keys
        key_mappings = {
            "log_level": "default_level",
            "log_config": "config_file",
            "log_dir": "log_dir",
            "log_format": "log_format",
            "colored_console": "colored_console",
            "disable_rotation": "disable_rotation",
            "exit_on_critical": "exit_on_critical",
            "rotation_size_mb": "rotation_size_mb",
            "backup_count": "backup_count",
            "log_filename": "log_filename",
            "logging_filename": "log_filename",
            "log_datefmt": "datefmt",
            "test_mode": "test_mode",
        }

        # Convert args to dictionary
        args_dict = vars(args)

        # Extract and map arguments
        result = {}
        for arg_name, value in args_dict.items():
            if value is not None and arg_name in key_mappings:
                config_key = key_mappings[arg_name]
                result[config_key] = value

        return result


def get_argument_parser(description: Optional[str] = None) -> argparse.ArgumentParser:
    """
    Create a new ArgumentParser with prismalog arguments.

    Args:
        description: Description for the ArgumentParser

    Returns:
        A new ArgumentParser with prismalog arguments
    """
    return LoggingArgumentParser.create_parser(description)


def add_logging_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add standard prismalog arguments to an existing parser.

    Args:
        parser: An existing ArgumentParser instance

    Returns:
        The ArgumentParser with prismalog arguments added
    """
    return LoggingArgumentParser.add_arguments(parser)


def extract_logging_args(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Extract logging-related arguments from parsed args.

    Args:
        args: The parsed args from ArgumentParser.parse_args()

    Returns:
        Dictionary with only the logging-related arguments
    """
    return LoggingArgumentParser.extract_logging_args(args)
