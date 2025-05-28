""" Example package-level initialization script for logging.
This script initializes logging for a package, ensuring that
the logging configuration is set up correctly when the package is imported."""
import logging
import os

from prismalog.config import LoggingConfig
from prismalog.log import get_logger

# Initialize logging when package is imported
if not LoggingConfig.is_initialized():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(config_path):
        LoggingConfig.initialize(config_file=config_path)

# Export commonly used items
__all__ = ["get_logger"]


def get_package_logger(name: str) -> logging.Logger:
    """Get a logger for this package."""
    return get_logger(name)


if __name__ == "__main__":
    logger = get_package_logger("example_package")
    logger.info("This is an example package-level initialization log message.")
    logger.debug("Debugging information for package initialization.")
    logger.warning("This is a warning during package initialization.")
    logger.error("An error occurred during package initialization.")
