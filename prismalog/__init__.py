"""
For more information, see the documentation at:
https://github.com/vertok/prismalog
"""
from .log import get_logger, ColoredLogger
from .config import LoggingConfig

# Simple function to initialize logging from command line
def setup_logging(config_file=None, parse_args=True):
    """
    Initialize logging with potential command-line arguments.

    Simple helper function that initializes LoggingConfig with both
    a config file and command-line arguments. This is the most common
    use case for applications.

    Args:
        config_file: Optional path to config file
        parse_args: Whether to parse command-line arguments (default: True)
    """
    return LoggingConfig.initialize(config_file=config_file, parse_args=parse_args)

__all__ = ['get_logger', 'ColoredLogger', 'LoggingConfig', 'setup_logging']
