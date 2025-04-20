"""
For more information, see the documentation at:
https://github.com/vertok/prismalog
"""

from typing import Optional

from .config import LoggingConfig
from .log import ColoredFormatter, ColoredLogger, CriticalExitHandler, MultiProcessingLog, get_logger


def setup_logging(config_file: Optional[str] = None, use_cli_args: bool = True) -> dict:
    """
    Initialize logging with potential command-line arguments.

    Simple helper function that initializes LoggingConfig with both
    a config file and command-line arguments. This is the most common
    use case for applications.

    Args:
        config_file: Optional path to config file
        use_cli_args: Whether to parse command-line arguments (default: True)
    """
    return LoggingConfig.initialize(config_file=config_file, use_cli_args=use_cli_args)


__all__ = [
    "get_logger",
    "ColoredLogger",
    "ColoredFormatter",
    "MultiProcessingLog",
    "CriticalExitHandler",
    "LoggingConfig",
    "setup_logging",
]
