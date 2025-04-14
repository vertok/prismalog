"""
Configuration Management Module for Prismalog

This module provides a centralized configuration system for the prismalog package,
enabling flexible and hierarchical configuration from multiple sources. It handles
loading, prioritizing, and accessing configuration settings throughout the application.

Key features:
- Hierarchical configuration with clear priority order
- Multi-source configuration (default values, files, environment variables, CLI)
- Support for YAML and JSON configuration files
- Automatic type conversion for numeric and boolean values
- Command-line argument integration with argparse
- Singleton pattern to ensure configuration consistency

The configuration system follows this priority order (highest to lowest):
1. Programmatic settings via direct API calls
2. Command-line arguments
3. Environment variables (with support for CI/CD environments)
4. Configuration files (YAML, JSON)
5. Default values

Usage examples:
    # Basic initialization with defaults
    LoggingConfig.initialize()

    # Initialization with configuration file
    LoggingConfig.initialize(config_file="logging_config.yaml")

    # Accessing configuration values
    log_dir = LoggingConfig.get("log_dir")

    # Setting configuration values programmatically
    LoggingConfig.set("colored_console", False)

    # Getting appropriate log level for a specific logger
    level = LoggingConfig.get_level("requests.packages.urllib3")
"""
import os
import argparse
from typing import Dict, Any, Optional

class LoggingConfig:
    """
    Configuration manager for prismalog package.

    Handles loading configuration from multiple sources with a priority order:
    1. Programmatic settings
    2. Command-line arguments
    3. Environment variables (including GitHub Actions secrets)
    4. Configuration files
    5. Default values

    This class uses a singleton pattern to ensure consistent configuration
    throughout the application lifecycle. It supports hot-reloading and can
    be accessed from any part of the application.
    """

    DEFAULT_CONFIG = {
        "log_dir": "logs",
        "default_level": "INFO",
        "rotation_size_mb": 10,
        "backup_count": 5,
        "log_format": "%(asctime)s - %(filename)s - %(name)s - [%(levelname)s] - %(message)s",
        "colored_console": True,
        "disable_rotation": False,
        "multiprocess_safe": True,
        "test_mode": False,         # Whether the logger is running in test mode
        "exit_on_critical": True,   # Whether to exit the program on critical logs
    }

    _instance = None
    _config = {}
    _initialized = False
    _debug_mode = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggingConfig, cls).__new__(cls)
            cls._config = cls.DEFAULT_CONFIG.copy()
        return cls._instance

    @classmethod
    def _debug_print(cls, message):
        """Print message only if debug mode is enabled."""
        if cls._debug_mode:
            print(message)

    @classmethod
    def initialize(cls, config_file: Optional[str] = None, parse_args: bool = True, **kwargs):
        """
        Initialize configuration from various sources.

        This method loads configuration in order of increasing priority:
        1. Default values (lowest priority)
        2. Configuration file (if provided)
        3. Environment variables
        4. Command-line arguments (if parse_args=True)
        5. Direct keyword arguments (highest priority)
        """
        # 1. Start with default values
        cls._config = cls.DEFAULT_CONFIG.copy()
        cls._debug_print(f"Starting with default config: {cls._config}")

        # 2. Update from config file if provided
        if config_file and os.path.exists(config_file):
            file_config = cls.load_from_file(config_file)
            if file_config:
                cls._config.update(file_config)
                cls._debug_print(f"Updated from config file: {config_file}")

        # 3. Update from environment variables (higher priority)
        env_config = cls.load_from_env()
        if env_config:
            cls._debug_print(f"Updating from environment variables: {env_config}")
            cls._config.update(env_config)

        # 4. Update from command-line arguments (even higher priority)
        if parse_args:
            arg_config = cls.load_from_args()
            if arg_config:
                # Handle CLI config file specially
                if 'config_file' in arg_config and arg_config['config_file'] != config_file:
                    cli_config_file = arg_config.pop('config_file')  # Remove from arg_config
                    if os.path.exists(cli_config_file):
                        # Load and apply CLI config file
                        cli_file_config = cls.load_from_file(cli_config_file)
                        if cli_file_config:
                            cls._config.update(cli_file_config)
                            cls._debug_print(f"Updated from CLI config file: {cli_config_file}")

                # Apply remaining CLI arguments
                cls._config.update(arg_config)
                cls._debug_print(f"Updated from command line arguments: {arg_config}")

        # Convert numeric and boolean values to appropriate types
        cls._convert_numeric_values()

        # 5. Update from explicit kwargs (highest priority)
        if kwargs:
            cls._debug_print(f"Updating configuration with kwargs: {kwargs}")
            cls._config.update(kwargs)

        # Set the initialized flag
        cls._initialized = True
        cls._debug_print(f"Final configuration: {cls._config}")

        return cls._config

    @classmethod
    def _convert_numeric_values(cls):
        """
        Convert string configuration values to appropriate types.

        This internal method ensures that numeric values like 'rotation_size_mb'
        are stored as integers even if they were provided as strings from
        environment variables or command-line arguments. Boolean values are
        also converted appropriately from string representations.
        """
        numeric_keys = ['rotation_size_mb', 'backup_count']
        boolean_keys = ['colored_console', 'disable_rotation', 'multiprocess_safe', 'test_mode']

        for key in numeric_keys:
            if key in cls._config and isinstance(cls._config[key], str):
                try:
                    cls._config[key] = int(cls._config[key])
                except ValueError:
                    pass

        for key in boolean_keys:
            if key in cls._config and isinstance(cls._config[key], str):
                cls._config[key] = cls._config[key].lower() in ['true', '1', 'yes', 'y']

    @classmethod
    def load_from_file(cls, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML or JSON file.

        Supports .yaml, .yml, and .json files. Values from the file will be returned
        as a dictionary. If the file doesn't exist or can't be parsed, a warning is
        printed and an empty dictionary is returned.

        Args:
            config_path: Path to the configuration file

        Returns:
            A dictionary containing the configuration loaded from the file

        Example:
            ```python
            config = LoggingConfig.load_from_file("configs/production.yaml")
            ```
        """
        file_config = {}  # Initialize with empty dict instead of returning cls._config

        if not os.path.exists(config_path):
            return file_config  # Return empty dict, not cls._config

        try:
            with open(config_path, mode='r', encoding='utf-8') as f:
                if config_path.endswith(('.yaml', '.yml')):
                    try:
                        import yaml  # pylint: disable=import-outside-toplevel
                        file_config = yaml.safe_load(f)
                    except ImportError:
                        cls._debug_print("YAML support requires PyYAML package. Install with: pip install pyyaml")
                        return file_config
                elif config_path.endswith('.json'):
                    import json  # pylint: disable=import-outside-toplevel
                    file_config = json.load(f)
                else:
                    cls._debug_print(f"Unsupported config file format: {config_path}")
                    return file_config

                # Return the loaded config rather than updating cls._config
                if not file_config or not isinstance(file_config, dict):
                    return {}

        except Exception as e:
            cls._debug_print(f"Error loading config file: {e}")

        return file_config

    @classmethod
    def load_from_env(cls) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Optimized for memory and speed by using direct lookups and avoiding
        unnecessary data structures.

        Returns:
            Dictionary with configuration values from environment variables
        """
        env_config = {}

        # Define lookup tables with ordered priorities
        env_vars = {
            'log_dir': ['GITHUB_LOGGING_DIR', 'LOGGING_DIR', 'LOG_DIR', 'LOGGING_CONFIG_DIR', 'LOG_CONFIG_DIR', 'LOGGING_PATH', 'LOG_PATH'],
            'default_level': ['GITHUB_LOGGING_VERBOSE', 'LOGGING_VERBOSE', 'LOG_LEVEL', 'LOGGING_LEVEL', 'LOG_CONFIG_LEVEL', 'LOG_VERBOSE'],
            'rotation_size_mb': ['GITHUB_LOG_ROTATION_SIZE', 'LOG_ROTATION_SIZE', 'LOG_ROTATION_SIZE_MB',
                                 'LOGGING_ROTATION_SIZE', 'LOGGING_ROTATION_SIZE_MB', 'LOG_MAX_SIZE', 'LOGGING_MAX_SIZE'],
            'backup_count': ['GITHUB_LOG_BACKUP_COUNT', 'LOG_BACKUP_COUNT', 'LOGGING_BACKUP_COUNT', 'LOG_BACKUP', 'LOGGING_BACKUP'],
            'log_format': ['GITHUB_LOG_FORMAT', 'LOG_FORMAT'],
            'colored_console': ['GITHUB_LOG_COLORED_CONSOLE', 'LOG_COLORED_CONSOLE', 'LOGGING_COLORED', 'LOG_COLOR', 'LOGGING_COLOR'],
            'disable_rotation': ['GITHUB_LOG_DISABLE_ROTATION', 'LOG_DISABLE_ROTATION'],
            'multiprocess_safe': ['GITHUB_LOG_MULTIPROCESS_SAFE', 'LOG_MULTIPROCESS_SAFE'],
            'test_mode': ['GITHUB_LOG_TEST_MODE', 'LOG_TEST_MODE'],
            'exit_on_critical': ['GITHUB_LOG_EXIT_ON_CRITICAL', 'LOG_EXIT_ON_CRITICAL', 'LOGGING_EXIT_ON_CRITICAL'],
        }

        # Efficiently check each config key using direct lookup
        for config_key, env_vars_list in env_vars.items():
            # Check each possible environment variable in priority order
            for env_var in env_vars_list:
                if env_var in os.environ:
                    env_config[config_key] = os.environ[env_var]
                    break  # Stop at first match

        return env_config

    @classmethod
    def _add_logging_args_to_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add standard logging arguments to an existing parser."""
        parser.add_argument('--log-config', '--log-conf', '--logging-conf', '--logging-config',
                        dest='config_file',
                        help='Path to logging configuration file')

        parser.add_argument('--log-level', '--logging-level',
                        dest='default_level',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the default logging level')

        parser.add_argument('--log-dir', '--logging-dir',
                        dest='log_dir',
                        help='Directory where log files will be stored')

        return parser

    @classmethod
    def load_from_args(cls) -> Dict[str, Any]:
        """
        Load configuration from command-line arguments.

        Parses command-line arguments for logging configuration options.
        Only recognizes specific logging-related arguments and ignores
        other arguments that might be intended for the application.

        Supported arguments:
            --log-config, --log-conf, --logging-config, --logging-conf:
            Path to logging configuration file

        Returns:
            Dictionary of parsed command-line arguments

        Note:
            This method uses argparse.parse_known_args() to avoid conflicts
            with application-specific command-line arguments.
        """
        parser = argparse.ArgumentParser(add_help=False)
        cls._add_logging_args_to_parser(parser)

        # Parse only known args to avoid conflicts with application args
        args, _ = parser.parse_known_args()

        # Return only non-None values
        arg_dict = {k: v for k, v in vars(args).items() if v is not None}
        return arg_dict

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        Get the complete current configuration.

        If the configuration hasn't been initialized yet, this will
        initialize it with default values before returning.

        Returns:
            Dictionary containing all configuration values

        Example:
            ```python
            config = LoggingConfig.get_config()
            print(f"Using log directory: {config['log_dir']}")
            ```
        """
        if not cls._initialized:
            cls.initialize()
        return cls._config

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.

        Args:
            key: The configuration key to retrieve
            default: Value to return if the key is not found

        Returns:
            The configuration value or the default if not found
        """
        if not cls._initialized:
            cls.initialize()

        # Special handling for nested keys
        if key == "module_levels":
            # Return the module_levels dictionary if it exists
            if "module_levels" in cls._config and isinstance(cls._config["module_levels"], dict):
                return cls._config["module_levels"]
            return {}

        # Normal key
        return cls._config.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """
        Set or update a configuration value.

        This allows runtime modification of configuration values. Changes
        will be reflected in any new loggers created after the change.

        Supports nested keys with dot notation (e.g., "module_levels.my_module").

        Args:
            key: The configuration key to set
            value: The value to assign to the key

        Example:
            ```python
            # Disable exiting on critical logs
            LoggingConfig.set("exit_on_critical", False)

            # Set module-specific log level
            LoggingConfig.set("module_levels.my_module", "DEBUG")
            ```
        """
        # Handle nested keys (with dot notation)
        if '.' in key:
            # Split the key path
            parts = key.split('.')
            main_key = parts[0]
            sub_key = parts[1]

            # Ensure parent dictionary exists
            if main_key not in cls._config:
                cls._config[main_key] = {}
            elif not isinstance(cls._config[main_key], dict):
                # If it exists but is not a dict, convert it to a dict
                cls._config[main_key] = {}

            # Set the value in the nested dict
            cls._config[main_key][sub_key] = value
        else:
            # Simple case: direct key
            cls._config[key] = value

    @classmethod
    def get_level(cls, name: Optional[str] = None, default_level: Optional[str] = None) -> int:
        """
        Get the numeric log level based on configuration priority.

        This method determines the appropriate log level based on priority order:
        1. Explicit level parameter (highest priority)
        2. Logger-specific configuration from external_loggers
        3. Default level from configuration

        Args:
            name: Optional logger name to check for specific configuration
            default_level: Optional override for the default level

        Returns:
            The numeric logging level (from logging module constants)
        """
        # 1. First priority: Use explicit level if provided
        if default_level:
            return cls.map_level(default_level)

        # 2. Second priority: Check logger-specific config
        if name:
            external_loggers = cls.get("external_loggers", {})
            if name in external_loggers:
                return cls.map_level(external_loggers[name])

        # 3. Third priority: Use configured default level
        config_level = cls.get("default_level", "INFO")
        return cls.map_level(config_level)

    @classmethod
    def map_level(cls, level_str: str) -> int:
        """
        Map string log level to numeric level.

        Args:
            level_str: String log level ('DEBUG', 'INFO', etc)

        Returns:
            The corresponding numeric logging level (from logging module constants)
        """
        import logging  # pylint: disable=import-outside-toplevel
        level = level_str.upper() if level_str else "INFO"
        return {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'WARN': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }.get(level, logging.INFO)

    @classmethod
    def reset(cls):
        """
        Reset configuration to default values.

        This method restores all configuration settings to their default values,
        which is particularly useful for testing where each test needs to start
        with a clean configuration state.

        Returns:
            The LoggingConfig class for method chaining
        """
        # Reset to default values
        cls._config = cls.DEFAULT_CONFIG.copy()

        # Reset initialization state
        cls._initialized = False

        # For debugging
        cls._debug_print("LoggingConfig reset to default values")

        return cls
