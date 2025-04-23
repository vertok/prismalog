"""
Configuration Management Module for prismalog

This module provides a centralized configuration system for the prismalog package,
enabling flexible and hierarchical configuration from multiple sources. It handles
loading, prioritizing, and accessing configuration settings throughout the application.

Key features:
- Hierarchical configuration with clear priority order
- Multi-source configuration (default values, files, environment variables, CLI)
- Support for YAML configuration files
- Automatic type conversion for numeric and boolean values
- Command-line argument integration with argparse
- Singleton pattern to ensure configuration consistency

The configuration system follows this priority order (highest to lowest):
1. Programmatic settings via direct API calls or kwargs to initialize()
2. Command-line arguments
3. Configuration files (YAML)
4. Environment variables (with support for CI/CD environments)
5. Default values

Environment Variables:
    Standard environment variables use the ``LOG_`` prefix:

    - ``LOG_DIR``: Directory for log files
    - ``LOG_LEVEL``: Default logging level (e.g., INFO, DEBUG)
    - ``LOG_ROTATION_SIZE``: Size in MB for log rotation
    - ``LOG_BACKUP_COUNT``: Number of backup log files
    - ``LOG_FORMAT``: Log message format string
    - ``LOG_DATEFMT``: Log message date format string
    - ``LOG_FILENAME``: Base filename prefix for log files (default: 'app')
    - ``LOG_COLORED_CONSOLE``: Whether to use colored console output (true/false)
    - ``LOG_DISABLE_ROTATION``: Whether to disable log rotation (true/false)
    - ``LOG_EXIT_ON_CRITICAL``: Whether to exit on critical logs (true/false)
    - ``LOG_TEST_MODE``: Whether logger is in test mode (true/false)

    For GitHub Actions, the same variables are supported with ``GITHUB_`` prefix:

    - ``GITHUB_LOG_DIR``, ``GITHUB_LOG_LEVEL``, ``GITHUB_LOG_FILENAME``, ``GITHUB_LOG_DATEFMT``, etc.

Command-Line Arguments:
    The following arguments can be parsed if `use_cli_args=True` during initialization:

    - ``--log-config`` / ``--log-conf``: Path to logging configuration file (YAML)
    - ``--log-level`` / ``--logging-level``: Default logging level (DEBUG, INFO, etc.)
    - ``--log-dir`` / ``--logging-dir``: Directory for log files
    - ``--log-format`` / ``--logging-format``: Format string for log messages
    - ``--log-datefmt`` / ``--logging-datefmt``: Format string for log timestamps
    - ``--log-filename`` / ``--logging-filename``: Prefix for log filenames
    - ``--no-color`` / ``--no-colors``: Disable colored console output
    - ``--disable-rotation``: Disable log file rotation
    - ``--exit-on-critical``: Exit the program on critical errors
    - ``--rotation-size``: Log file rotation size in MB
    - ``--backup-count``: Number of backup log files to keep

Type Conversion:
    String values from configuration files and environment variables are automatically
    converted to the appropriate types (boolean, integer) based on the default config's
    type definition. Boolean values support multiple string representations:
    - True: "true", "1", "yes", "y", "t", "on"
    - False: "false", "0", "no", "n", "f", "off", "none"

Usage examples:
    # Basic initialization with defaults
    LoggingConfig.initialize()

    # Initialization with configuration file and CLI args enabled
    LoggingConfig.initialize(config_file="logging_config.yaml", use_cli_args=True)

    # Accessing configuration values
    log_dir = LoggingConfig.get("log_dir")
    filename_prefix = LoggingConfig.get_filename_prefix()

    # Setting configuration values programmatically
    LoggingConfig.set("colored_console", False)

    # Getting appropriate log level for a specific logger
    level = LoggingConfig.get_level("requests.packages.urllib3")
"""

import argparse
import os
from typing import Any, Dict, Optional, Type, cast


class LoggingConfig:
    """
    Configuration manager for prismalog package.

    Handles loading configuration from multiple sources with a priority order:
    1. Programmatic settings
    2. Command-line arguments
    3. Configuration files (YAML)
    4. Environment variables (including GitHub Actions secrets)
    5. Default values

    This class uses a singleton pattern to ensure consistent configuration
    throughout the application lifecycle. It supports configuration from
    multiple sources and provides automatic type conversion.

    Attributes:
        DEFAULT_CONFIG (Dict[str, Any]): Default configuration values
        _instance (LoggingConfig): Singleton instance of LoggingConfig
        _config (Dict[str, Any]): Current active configuration
        _initialized (bool): Whether the configuration has been initialized
        _debug_mode (bool): Whether to print debug messages during configuration

    Examples:
        # Initialize with default settings
        LoggingConfig.initialize()

        # Initialize with a configuration file
        LoggingConfig.initialize(config_file="logging.yaml")

        # Get a configuration value
        log_dir = LoggingConfig.get("log_dir")
    """

    DEFAULT_CONFIG = {
        "log_dir": "logs",
        "default_level": "INFO",
        "rotation_size_mb": 10,
        "backup_count": 5,
        "log_format": "%(asctime)s - %(filename)s - %(name)s - [%(levelname)s] - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S.%f",
        "log_filename": "app",  # Default log filename prefix
        "colored_console": True,
        "disable_rotation": False,
        "exit_on_critical": False,  # Whether to exit the program on critical logs
        "test_mode": False,  # Whether the logger is running in test mode
    }

    _instance = None
    _config: Dict[str, Any] = {}  # Add type annotation
    _initialized = False
    _debug_mode = False

    def __new__(cls) -> "LoggingConfig":
        """Singleton pattern to ensure only one instance of LoggingConfig exists."""
        if cls._instance is None:
            cls._instance = super(LoggingConfig, cls).__new__(cls)
            cls._config = cls.DEFAULT_CONFIG.copy()
        return cls._instance

    @classmethod
    def debug_print(cls, message: str) -> None:
        """
        Print debug message only if debug mode is enabled.

        Args:
            message: The message to print when debugging is enabled
        """
        if cls._debug_mode:
            print(message)

    @classmethod
    def initialize(cls, config_file: Optional[str] = None, use_cli_args: bool = True, **kwargs: Any) -> Dict[str, Any]:
        """
        Initialize configuration from various sources using a two-phase approach.

        The configuration is loaded in two phases:
        1. Collection Phase: Gather and convert configurations from all sources
        2. Application Phase: Apply configurations in priority order

        Args:
            config_file: Path to configuration file (YAML)
            use_cli_args: Whether to parse command-line arguments
            **kwargs: Direct configuration values (highest priority)

        Returns:
            The complete configuration dictionary

        Examples:
            # Basic initialization
            LoggingConfig.initialize()

            # Initialize with a YAML config file
            LoggingConfig.initialize(config_file="logging.yaml")

            # Initialize with direct override values
            LoggingConfig.initialize(log_level="DEBUG", colored_console=False)
        """
        # Phase 1: Collect configurations from all sources
        config_sources = cls._collect_configurations(config_file, use_cli_args, kwargs)

        # Phase 2: Apply configurations in priority order
        cls._apply_configurations(config_sources)

        return cls._config

    @classmethod
    def _collect_configurations(
        cls, config_file: Optional[str], use_cli_args: bool, kwargs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Collect configurations from all possible sources and convert types immediately.

        This method gathers configuration from multiple sources:
        - Default values
        - Environment variables
        - Configuration files (if specified)
        - Command-line arguments (if use_cli_args is True)
        - Direct keyword arguments

        Each source's values are converted to appropriate types during collection.

        Args:
            config_file: Optional path to a configuration file
            use_cli_args: Whether to parse command-line arguments
            kwargs: Direct configuration values passed to initialize()

        Returns:
            Dictionary containing configuration values from each source
        """
        # Start with empty collections for each source
        sources: Dict[str, Dict[str, Any]] = {
            "defaults": cls.DEFAULT_CONFIG.copy(),
            "file": {},
            "env": {},
            "cli": {},
            "kwargs": kwargs.copy() if kwargs else {},
        }

        # Collect and convert file configuration
        if config_file and os.path.exists(config_file):
            raw_file_config = cls._load_raw_file_config(config_file)
            if raw_file_config:
                # Convert types immediately
                file_config = cls._convert_config_values(raw_file_config)
                sources["file"] = file_config
                cls.debug_print(f"Collected from file: {file_config}")

        # Collect and convert environment variables
        raw_env_config = cls._load_raw_env_config()
        if raw_env_config:
            # Convert types immediately
            env_config = cls._convert_config_values(raw_env_config)
            sources["env"] = env_config
            cls.debug_print(f"Collected from environment: {env_config}")

        # Collect and convert command line arguments
        if use_cli_args:
            raw_arg_config = cls._load_raw_cli_args()
            if raw_arg_config:
                # Convert types immediately
                arg_config = cls._convert_config_values(raw_arg_config)
                sources["cli"] = arg_config
                cls.debug_print(f"Collected from CLI: {arg_config}")

        return sources

    @classmethod
    def _apply_configurations(cls, sources: Dict[str, Dict[str, Any]]) -> None:
        """
        Apply configurations in the correct priority order.

        Priority order (lowest to highest):
        1. Default values (starting point)
        2. Environment variables (override defaults)
        3. Configuration file (overrides environment)
        4. Command-line arguments (overrides file)
        5. Direct keyword arguments (highest priority)

        Args:
            sources: Dictionary containing configurations from different sources
        """
        # 1. Start with defaults
        cls._config = sources["defaults"].copy()
        cls.debug_print(f"1. Starting with defaults: {cls._config}")

        # 2. Apply environment variables (overrides defaults)
        if sources["env"]:
            cls.debug_print("2. Applying environment variables")
            cls._config.update(sources["env"])
            cls.debug_print(f"   Config after env vars: {cls._config}")

        # 3. Apply configuration file (overrides env)
        if sources["file"]:
            cls.debug_print("3. Applying file configuration")
            cls._config.update(sources["file"])
            cls.debug_print(f"   Config after file: {cls._config}")

        # 4. Apply command-line arguments (overrides file)
        if sources["cli"]:
            cls.debug_print("4. Applying command line arguments")
            cls._config.update(sources["cli"])
            cls.debug_print(f"   Config after CLI args: {cls._config}")

        # 5. Apply direct kwargs (highest priority)
        if sources["kwargs"]:
            cls.debug_print("5. Applying kwargs")
            cls._config.update(sources["kwargs"])
            cls.debug_print(f"   Config after kwargs: {cls._config}")

        cls._initialized = True
        cls.debug_print(f"Final configuration: {cls._config}")

    @classmethod
    def _convert_config_values(cls, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert string configuration values to their appropriate types.

        This is the central type conversion method used by all config sources.
        It handles two types of conversions:
        1. Boolean values: Converts strings like "true", "yes", "1" to True and their opposites to False
        2. Numeric values: Converts digit strings to integers

        The method processes boolean conversions first, then numeric conversions.
        Invalid conversion attempts result in the key being removed from the result.

        Args:
            config_dict: Dictionary containing configuration values to convert

        Returns:
            Dictionary with values converted to appropriate types

        Examples:
            >>> LoggingConfig._convert_config_values({"colored_console": "true", "rotation_size_mb": "50"})
            {'colored_console': True, 'rotation_size_mb': 50}
        """
        if not config_dict:
            return {}

        result = config_dict.copy()

        # Get the keys and their types from DEFAULT_CONFIG
        numeric_keys = [k for k, v in cls.DEFAULT_CONFIG.items() if isinstance(v, int)]
        boolean_keys = [k for k, v in cls.DEFAULT_CONFIG.items() if isinstance(v, bool)]

        # First, convert boolean values
        for key in boolean_keys:
            if key in result and isinstance(result[key], str):
                val = result[key].strip().lower()
                if val in ["true", "1", "yes", "y", "t", "on"]:
                    result[key] = True
                    cls.debug_print(f"Converted '{key}={val}' to boolean True")
                elif val in ["false", "0", "no", "n", "f", "off", "none"]:
                    result[key] = False
                    cls.debug_print(f"Converted '{key}={val}' to boolean False")
                else:
                    cls.debug_print(f"Warning: Cannot convert '{key}={val}' to boolean")
                    result.pop(key, None)  # Remove invalid values

        # Then, convert numeric values
        for key in numeric_keys:
            if key in result and isinstance(result[key], str):
                val = result[key].strip()
                if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
                    result[key] = int(val)
                    cls.debug_print(f"Converted '{key}={val}' to integer {int(val)}")
                else:
                    cls.debug_print(f"Warning: Cannot convert '{key}={val}' to integer")
                    result.pop(key, None)  # Remove invalid values

        return result

    @classmethod
    def _load_raw_file_config(cls, config_path: str) -> Dict[str, Any]:
        """
        Load raw configuration from file without type conversion.

        Supports YAML file format. If PyYAML is not installed,
        YAML files cannot be loaded and an empty dictionary is returned.

        Args:
            config_path: Path to the configuration file

        Returns:
            Dictionary with raw configuration values from the file,
            or empty dictionary if file doesn't exist or has invalid format
        """
        file_config: Dict[str, Any] = {}  # Add type annotation here
        if not os.path.exists(config_path):
            return file_config

        try:
            with open(config_path, mode="r", encoding="utf-8") as f:
                if config_path.endswith((".yaml", ".yml")):
                    try:
                        import yaml

                        file_config = yaml.safe_load(f)
                    except ImportError:
                        print("YAML configuration requires PyYAML. Install with: pip install PyYAML")
                        print("Continuing with default configuration.")
                        return file_config
                else:
                    cls.debug_print(f"Unsupported config file format: {config_path}")
                    return file_config

        except Exception as e:
            cls.debug_print(f"Error loading config file: {e}")
            return file_config

        # Process level values to ensure they are uppercase
        if "default_level" in file_config and isinstance(file_config["default_level"], str):
            file_config["default_level"] = file_config["default_level"].upper()

        # Also handle external_loggers levels
        if "external_loggers" in file_config and isinstance(file_config["external_loggers"], dict):
            for logger, level in file_config["external_loggers"].items():
                if isinstance(level, str):
                    file_config["external_loggers"][logger] = level.upper()

        return file_config

    @classmethod
    def _load_raw_env_config(cls) -> Dict[str, Any]:
        """
        Load raw environment variables without type conversion.

        Looks for environment variables with both LOG_ and GITHUB_ prefixes.
        For each configuration key, it checks the variables in order and uses
        the first one found.

        Returns:
            Dictionary mapping configuration keys to environment variable values
        """
        env_config = {}

        # Define lookup tables with ordered priorities
        env_vars = {
            "log_dir": ["LOG_DIR", "GITHUB_LOG_DIR"],
            "default_level": ["LOG_LEVEL", "GITHUB_LOG_LEVEL"],
            "rotation_size_mb": ["LOG_ROTATION_SIZE", "GITHUB_LOG_ROTATION_SIZE"],
            "backup_count": ["LOG_BACKUP_COUNT", "GITHUB_LOG_BACKUP_COUNT"],
            "log_format": ["LOG_FORMAT", "GITHUB_LOG_FORMAT"],
            "datefmt": ["LOG_DATEFMT", "GITHUB_LOG_DATEFMT"],
            "log_filename": ["LOG_FILENAME", "GITHUB_LOG_FILENAME"],
            "colored_console": ["LOG_COLORED_CONSOLE", "GITHUB_LOG_COLORED_CONSOLE"],
            "disable_rotation": ["LOG_DISABLE_ROTATION", "GITHUB_LOG_DISABLE_ROTATION"],
            "exit_on_critical": ["LOG_EXIT_ON_CRITICAL", "GITHUB_LOG_EXIT_ON_CRITICAL"],
            "test_mode": ["LOG_TEST_MODE", "GITHUB_LOG_TEST_MODE"],
        }

        # Efficiently check each config key using direct lookup
        for config_key, env_vars_list in env_vars.items():
            for env_var in env_vars_list:
                if env_var in os.environ:
                    env_config[config_key] = os.environ[env_var]
                    break  # Stop after finding the first matching env var

        return env_config

    @classmethod
    def _load_raw_cli_args(cls) -> Dict[str, Any]:
        """
        Parse command-line arguments for logging configuration without type conversion.

        This method creates an ArgumentParser that only handles logging-specific
        arguments and uses parse_known_args() to avoid conflicts with
        application-specific arguments.

        If a config file is specified in the arguments, its content is loaded
        and merged with the CLI arguments (with CLI args taking precedence).

        Returns:
            Dictionary of raw string values from command-line arguments
        """
        parser = argparse.ArgumentParser(add_help=False)
        cls._add_logging_args_to_parser(parser)

        # Parse only known args to avoid conflicts with application args
        args, _ = parser.parse_known_args()

        # Process the parsed arguments - collect only non-None values
        arg_dict = {k: v for k, v in vars(args).items() if v is not None}

        # Handle config file if present, but don't convert types yet
        if "config_file" in arg_dict:
            config_path = arg_dict.pop("config_file")  # Remove the path from arg_dict
            raw_file_config = cls._load_raw_file_config(config_path)

            # Merge file config with arg_dict (CLI args take precedence)
            merged_config = raw_file_config.copy()
            merged_config.update(arg_dict)  # CLI args override file config
            return merged_config

        return arg_dict

    @classmethod
    def load_from_file(cls, config_path: str) -> Dict[str, Any]:
        """
        Load and convert configuration from a YAML file.

        This is a convenience method that loads raw configuration from a file
        and then converts the values to appropriate types.

        Args:
            config_path: Path to the configuration file

        Returns:
            Dictionary with configuration values converted to appropriate types
        """
        raw_config = cls._load_raw_file_config(config_path)
        return cls._convert_config_values(raw_config)

    @classmethod
    def load_from_env(cls) -> Dict[str, Any]:
        """
        Load and convert configuration from environment variables.

        This is a convenience method that loads raw configuration from
        environment variables and then converts the values to appropriate types.

        Returns:
            Dictionary with configuration values converted to appropriate types
        """
        raw_config = cls._load_raw_env_config()
        return cls._convert_config_values(raw_config)

    @classmethod
    def _add_logging_args_to_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """
        Add standard logging arguments to an existing parser.

        Adds the following arguments to the parser:
        - --log-config, --log-conf: Path to logging configuration file
        - --log-level, --logging-level: Default logging level
        - --log-dir, --logging-dir: Directory for log files
        - --log-format, --logging-format: Format string for log messages
        - --log-datefmt, --logging-datefmt: Format string for log timestamps
        - --log-filename, --logging-filename: Prefix for log filenames

        Args:
            parser: An existing ArgumentParser to add arguments to

        Returns:
            The modified ArgumentParser with logging arguments added
        """
        parser.add_argument(
            "--log-config",
            "--log-conf",
            dest="config_file",
            help="Path to logging configuration file",
        )

        parser.add_argument(
            "--log-level",
            "--logging-level",
            dest="default_level",
            type=str.upper,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set the default logging level",
        )

        parser.add_argument(
            "--log-dir", "--logging-dir", dest="log_dir", help="Directory where log files will be stored"
        )

        parser.add_argument(
            "--log-format",
            "--logging-format",
            dest="log_format",
            help="Format string for log messages (e.g. '%(asctime)s - %(message)s')",
        )

        parser.add_argument(
            "--log-datefmt",
            "--logging-datefmt",
            dest="datefmt",
            help="Format string for log timestamps (e.g. '%%Y-%%m-%%d %%H:%%M:%%S.%%f')",
        )

        parser.add_argument(
            "--log-filename",
            "--logging-filename",
            dest="log_filename",
            help="Prefix for log filenames",
        )

        return parser

    @classmethod
    def parse_cli_args(cls) -> Dict[str, Any]:
        """
        Parse command-line arguments for logging configuration.

        Parses command-line arguments for logging configuration options.
        Only recognizes specific logging-related arguments and ignores
        other arguments that might be intended for the application.

        Supported arguments:
            --log-config, --log-conf: Path to logging configuration file
            --log-level, --logging-level: Default logging level
            --log-dir, --logging-dir: Directory for log files

        Returns:
            Dictionary of parsed command-line arguments with proper type conversion

        Note:
            This method uses argparse.parse_known_args() to avoid conflicts
            with application-specific command-line arguments.
        """
        parser = argparse.ArgumentParser(add_help=False)
        cls._add_logging_args_to_parser(parser)

        # Parse only known args to avoid conflicts with application args
        args, _ = parser.parse_known_args()

        # Process the parsed arguments
        arg_dict = {k: v for k, v in vars(args).items() if v is not None}

        # If --log-config was provided, load that config file
        if "config_file" in arg_dict:
            config_path = arg_dict.pop("config_file")  # Remove the path from arg_dict
            file_config = cls.load_from_file(config_path)

            # Merge file config with arg_dict (CLI args take precedence)
            merged_config = file_config.copy()
            merged_config.update(arg_dict)  # CLI args override file config
            return merged_config

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
            print(f"Log directory: {config['log_dir']}")
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

        Example:
            ```python
            log_dir = LoggingConfig.get("log_dir")
            level = LoggingConfig.get("default_level", "INFO")
            ```
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
        # First check if it's in current config
        if key in cls._config:
            return cls._config[key]

        # If not, check if it's in DEFAULT_CONFIG
        if key in cls.DEFAULT_CONFIG:
            return cls.DEFAULT_CONFIG[key]

        # If not found in either place, return the provided default
        return default

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
            >>> # Disable exiting on critical logs
            >>> LoggingConfig.set("exit_on_critical", False)
            >>>
            >>> # Set module-specific log level
            >>> LoggingConfig.set("module_levels.my_module", "DEBUG")
        """
        # Handle nested keys (with dot notation)
        if "." in key:
            # Split the key path
            parts = key.split(".")
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

        Examples:
            Get default level for application:

            >>> default_level = LoggingConfig.get_level()

            Get level for a specific module:

            >>> requests_level = LoggingConfig.get_level("requests.packages.urllib3")

            Override with explicit level:

            >>> debug_level = LoggingConfig.get_level(default_level="DEBUG")
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
    def map_level(cls, level: str) -> int:
        """
        Map string log level to numeric level.

        Converts string log level names to their corresponding numeric values
        from the logging module. If the level string is not recognized,
        defaults to logging.INFO.

        Args:
            level: String log level ('DEBUG', 'INFO', etc.)

        Returns:
            The corresponding numeric logging level (from logging module constants)

        Example:
            ```python
            debug_level = LoggingConfig.map_level("DEBUG")  # Returns 10
            warn_level = LoggingConfig.map_level("WARNING")  # Returns 30
            ```
        """
        import logging  # pylint: disable=import-outside-toplevel

        return {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "WARN": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }.get(level, logging.INFO)

    @classmethod
    def reset(cls) -> Type["LoggingConfig"]:
        """
        Reset configuration to default values.

        This method restores all configuration settings to their default values,
        which is particularly useful for testing where each test needs to start
        with a clean configuration state.

        Returns:
            The LoggingConfig class for method chaining

        Example:
            ```python
            # Reset to defaults and then set a specific value
            LoggingConfig.reset().set("colored_console", False)
            ```
        """
        # Reset to default values
        cls._config = cls.DEFAULT_CONFIG.copy()

        # Reset initialization state
        cls._initialized = False

        # For debugging
        cls.debug_print("LoggingConfig reset to default values")

        return cls

    @classmethod
    def get_filename_prefix(cls) -> str:
        """
        Get the configured log filename prefix.

        Returns:
            The configured prefix string, defaulting to 'app'.
        """
        value = cls.get("log_filename", "app")
        return cast(str, value)
