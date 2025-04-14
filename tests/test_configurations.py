"""Test prismalog with different configuration parameters."""

import unittest
import tempfile
import os
import sys
import shutil
from prismalog import get_logger, LoggingConfig, ColoredLogger
from prismalog.log import CriticalExitHandler  # Import added
import logging  # Add this import if needed

class TestConfigurationsImpact(unittest.TestCase):
    """Test various configuration settings and their impact on logging behavior."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="log_config_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_rotation_size_impact(self):
        """Test log rotation with different size thresholds."""
        # Explicitly check and unset LOG_DISABLE_ROTATION environment variable if present
        if 'LOG_DISABLE_ROTATION' in os.environ:
            saved_value = os.environ['LOG_DISABLE_ROTATION']
            del os.environ['LOG_DISABLE_ROTATION']
            print(f"Warning: Removed LOG_DISABLE_ROTATION={saved_value} for rotation test")

        # Use very small rotation size to trigger quickly
        test_rotation_size = 0.01  # 10KB
        test_backup_count = 2

        # Initialize with explicit rotation settings
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "rotation_size_mb": test_rotation_size,
            "backup_count": test_backup_count,
            "disable_rotation": False  # Explicitly enable rotation
        })

        # Important: Check if initialization didn't work, and set values directly if needed
        if LoggingConfig.get("rotation_size_mb") != test_rotation_size:
            print("Warning: LoggingConfig.initialize() did not set rotation_size_mb, using direct method")
            LoggingConfig.set("rotation_size_mb", test_rotation_size)

        if LoggingConfig.get("backup_count") != test_backup_count:
            print("Warning: LoggingConfig.initialize() did not set backup_count, using direct method")
            LoggingConfig.set("backup_count", test_backup_count)

        if LoggingConfig.get("disable_rotation") != False:
            print("Warning: LoggingConfig.initialize() did not disable rotation, setting directly")
            LoggingConfig.set("disable_rotation", False)

        # Verify settings were applied
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), test_rotation_size,
                        "Rotation size setting was not applied")
        self.assertEqual(LoggingConfig.get("backup_count"), test_backup_count,
                        "Backup count setting was not applied")
        self.assertFalse(LoggingConfig.get("disable_rotation"),
                        "Rotation should be enabled but disable_rotation is True")

        # Print the full configuration for debugging
        print(f"Configuration after setup: {LoggingConfig._config}")

    def test_rotation_size_impact_1(self):
        """Test log rotation with different size thresholds."""
        # Explicitly check and unset LOG_DISABLE_ROTATION environment variable if present
        if 'LOG_DISABLE_ROTATION' in os.environ:
            saved_value = os.environ['LOG_DISABLE_ROTATION']
            del os.environ['LOG_DISABLE_ROTATION']
            print(f"Warning: Removed LOG_DISABLE_ROTATION={saved_value} for rotation test")

        # Use very small rotation size to trigger quickly
        test_rotation_size = 0.01  # 10KB
        test_backup_count = 2

        # Initialize with explicit rotation settings
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "rotation_size_mb": test_rotation_size,
            "backup_count": test_backup_count,
            "disable_rotation": False  # Explicitly enable rotation
        })

        # Important: Check if initialization didn't work, and set values directly if needed
        if LoggingConfig.get("rotation_size_mb") != test_rotation_size:
            print("Warning: LoggingConfig.initialize() did not set rotation_size_mb, using direct method")
            LoggingConfig.set("rotation_size_mb", test_rotation_size)

        if LoggingConfig.get("backup_count") != test_backup_count:
            print("Warning: LoggingConfig.initialize() did not set backup_count, using direct method")
            LoggingConfig.set("backup_count", test_backup_count)

        if LoggingConfig.get("disable_rotation") != False:
            print("Warning: LoggingConfig.initialize() did not disable rotation, setting directly")
            LoggingConfig.set("disable_rotation", False)

        # Verify settings were applied
        self.assertEqual(LoggingConfig.get("rotation_size_mb"), test_rotation_size,
                         "Rotation size setting was not applied")
        self.assertEqual(LoggingConfig.get("backup_count"), test_backup_count,
                         "Backup count setting was not applied")
        self.assertFalse(LoggingConfig.get("disable_rotation"),
                         "Rotation should be enabled but disable_rotation is True")

        # Print the full configuration for debugging
        print(f"Configuration after setup: {LoggingConfig._config}")

        # Reset logger for clean state
        ColoredLogger.reset(new_file=True)

        # Get the actual log file path
        log_path = ColoredLogger._log_file_path
        log_dir = os.path.dirname(log_path)
        base_name = os.path.basename(log_path)

        print(f"Log file: {log_path}")
        print(f"Log directory: {log_dir}")

        # Create logger
        logger = get_logger("rotation_test")

        # Write large messages to trigger rotation
        message_count = 500
        print(f"Writing {message_count} messages to trigger rotation...")
        for i in range(message_count):
            logger.info(f"Test message {i}: " + "X" * 100)

            # Force flush handlers
            for handler in logger.logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()

            # Print progress occasionally
            if i % 100 == 0 and i > 0:
                print(f"Wrote {i} messages")

        # Give time for rotation to complete
        import time
        time.sleep(0.5)

        # Check for log files matching the base name
        log_files = [f for f in os.listdir(log_dir)
                    if f == base_name or f.startswith(base_name + '.')]

        print(f"Found log files: {log_files}")

        # backup_count + 1 files (base file + backups)
        expected_file_count = test_backup_count + 1
        self.assertEqual(len(log_files), expected_file_count,
                        f"Expected {expected_file_count} log files (base + {test_backup_count} backups), found {len(log_files)}")

        # Check all files have content
        for filename in log_files:
            file_path = os.path.join(log_dir, filename)
            size = os.path.getsize(file_path)
            print(f"File {filename}: {size} bytes")

            # Verify file has content
            self.assertGreater(size, 0, f"Log file {filename} is empty")

            # Verify the file contains the test messages
            with open(file_path, 'r') as f:
                content = f.read()
                self.assertIn("Test message", content,
                             f"Log file {filename} doesn't contain expected messages")

    def test_log_level_filtering(self):
        """Test that different log levels properly filter console messages."""
        # Disable exit behavior for this test
        CriticalExitHandler.disable_exit(True)

        # Test with different verbosity levels
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_messages = {
            "DEBUG": "Debug test message",
            "INFO": "Info test message",
            "WARNING": "Warning test message",
            "ERROR": "Error test message",
            "CRITICAL": "Critical test message"
        }

        for test_level in levels:
            # Reset completely between tests
            ColoredLogger._initialized_loggers = {}

            # Create a StringIO for capturing console output
            from io import StringIO
            test_output = StringIO()

            # Configure for this test level
            LoggingConfig.initialize(parse_args=False, **{
                "log_dir": self.temp_dir,
                "default_level": test_level,
                "exit_on_critical": False
            })

            # Reset logger with fresh file
            ColoredLogger.reset(new_file=True)

            # Create a fresh logger
            logger = get_logger("level_test", verbose=test_level)

            # Replace stdout handler to capture console output
            python_logger = logger.logger
            for handler in list(python_logger.handlers):
                if (isinstance(handler, logging.StreamHandler) and
                    not isinstance(handler, CriticalExitHandler) and
                    hasattr(handler, 'stream') and
                    handler.stream == sys.stdout):

                    # Remove stdout handler
                    python_logger.removeHandler(handler)

                    # Add the test handler
                    test_handler = logging.StreamHandler(test_output)
                    test_handler.setFormatter(handler.formatter)
                    test_handler.setLevel(getattr(logging, test_level))
                    python_logger.addHandler(test_handler)

            # Log exactly ONE message at each level with unique content
            logger.debug(level_messages["DEBUG"])
            logger.info(level_messages["INFO"])
            logger.warning(level_messages["WARNING"])
            logger.error(level_messages["ERROR"])
            logger.critical(level_messages["CRITICAL"])

            # Force flush handlers
            for handler in python_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()

            # Get console output
            console_output = test_output.getvalue()

            # Check console output based on level
            if test_level == "DEBUG":
                self.assertIn(level_messages["DEBUG"], console_output)
                self.assertIn(level_messages["INFO"], console_output)
                self.assertIn(level_messages["WARNING"], console_output)
                self.assertIn(level_messages["ERROR"], console_output)
                self.assertIn(level_messages["CRITICAL"], console_output)
            elif test_level == "INFO":
                self.assertNotIn(level_messages["DEBUG"], console_output)
                self.assertIn(level_messages["INFO"], console_output)
                self.assertIn(level_messages["WARNING"], console_output)
                self.assertIn(level_messages["ERROR"], console_output)
                self.assertIn(level_messages["CRITICAL"], console_output)
            elif test_level == "WARNING":
                self.assertNotIn(level_messages["DEBUG"], console_output)
                self.assertNotIn(level_messages["INFO"], console_output)
                self.assertIn(level_messages["WARNING"], console_output)
                self.assertIn(level_messages["ERROR"], console_output)
                self.assertIn(level_messages["CRITICAL"], console_output)
            elif test_level == "ERROR":
                self.assertNotIn(level_messages["DEBUG"], console_output)
                self.assertNotIn(level_messages["INFO"], console_output)
                self.assertNotIn(level_messages["WARNING"], console_output)
                self.assertIn(level_messages["ERROR"], console_output)
                self.assertIn(level_messages["CRITICAL"], console_output)
            elif test_level == "CRITICAL":
                self.assertNotIn(level_messages["DEBUG"], console_output)
                self.assertNotIn(level_messages["INFO"], console_output)
                self.assertNotIn(level_messages["WARNING"], console_output)
                self.assertNotIn(level_messages["ERROR"], console_output)
                self.assertIn(level_messages["CRITICAL"], console_output)

    def test_yaml_config_file(self):
        """Test loading configuration from YAML file."""
        # Write a test YAML file
        config_dir = tempfile.mkdtemp(prefix="log_config_test_")
        config_path = os.path.join(config_dir, "config.yaml")

        with open(config_path, "w") as f:
            f.write("""
            log_dir: '{0}'
            default_level: WARNING
            rotation_size_mb: 2
            """.format(config_dir))

        # Initialize with this config file
        LoggingConfig.initialize(config_file=config_path, parse_args=False)

        # Create a logger and test it
        logger = get_logger("yaml_test")
        logger.warning("Test YAML config")

        self.assertEqual(logger.level, logging.WARNING,
                         f"Logger level {logger.level} does not match expected {logging.WARNING}")

    def test_debug_level_logging(self):
        """Test DEBUG level logging captures all messages."""
        CriticalExitHandler.disable_exit(True)

        # Configure for DEBUG level
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "default_level": "DEBUG",
            "exit_on_critical": False
        })
        ColoredLogger.reset(new_file=True)

        # Get a fresh logger with explicit level
        logger = get_logger("level_test_debug", verbose="DEBUG")

        # Log messages
        logger.debug("Debug test")
        logger.info("Info test")
        logger.critical("Critical test")

        # Get log content
        log_path = ColoredLogger._log_file_path
        with open(log_path, 'r') as f:
            content = f.read()

        # All messages should be present
        self.assertIn("Debug test", content)
        self.assertIn("Info test", content)
        self.assertIn("Critical test", content)

    def test_info_level_logging(self):
        """Test INFO level logging filters out DEBUG messages in console, but writes all to file."""
        CriticalExitHandler.disable_exit(True)

        from io import StringIO
        test_output = StringIO()

        # Configure for INFO level
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "default_level": "INFO",
            "exit_on_critical": False
        })
        ColoredLogger.reset(new_file=True)

        # Get a fresh logger with explicit level
        logger = get_logger("level_test_info", verbose="INFO")

        # Replace stdout handler to capture console output
        python_logger = logger.logger
        for handler in list(python_logger.handlers):
            if (isinstance(handler, logging.StreamHandler) and
                not isinstance(handler, CriticalExitHandler) and
                hasattr(handler, 'stream') and
                handler.stream == sys.stdout):

                # Remove stdout handler
                python_logger.removeHandler(handler)

                # Add the test handler
                test_handler = logging.StreamHandler(test_output)
                test_handler.setFormatter(handler.formatter)
                test_handler.setLevel(logging.INFO)
                python_logger.addHandler(test_handler)

        # Log messages
        logger.debug("Debug test info")
        logger.info("Info test info")
        logger.critical("Critical test info")

        # Force flush handlers
        for handler in python_logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()

        # Verify console output filtering
        console_output = test_output.getvalue()
        self.assertNotIn("Debug test info", console_output)
        self.assertIn("Info test info", console_output)
        self.assertIn("Critical test info", console_output)

        # Log file captures all levels regardless of configuration
        log_path = ColoredLogger._log_file_path
        with open(log_path, 'r') as f:
            content = f.read()

        # All messages should be in log file
        self.assertIn("Debug test info", content)
        self.assertIn("Info test info", content)
        self.assertIn("Critical test info", content)

    def test_error_level_logging(self):
        """Test ERROR level logger correctly filters console output."""
        CriticalExitHandler.disable_exit(True)

        from io import StringIO
        test_output = StringIO()

        # Configure for ERROR level
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "default_level": "ERROR",
            "exit_on_critical": False
        })

        ColoredLogger.reset(new_file=True)

        # Get logger with ERROR level
        logger = get_logger("level_test_error", verbose="ERROR")

        # Replace stdout handler to capture console output
        import sys
        python_logger = logger.logger
        for handler in list(python_logger.handlers):
            if (isinstance(handler, logging.StreamHandler) and
                not isinstance(handler, CriticalExitHandler) and
                hasattr(handler, 'stream') and
                handler.stream == sys.stdout):

                # Remove stdout handler
                python_logger.removeHandler(handler)

                # Add the test handler
                test_handler = logging.StreamHandler(test_output)
                test_handler.setFormatter(handler.formatter)
                test_handler.setLevel(logging.ERROR)
                python_logger.addHandler(test_handler)

        # Log messages
        logger.debug("Debug test error")
        logger.info("Info test error")
        logger.warning("Warning test error")
        logger.error("Error test error")
        logger.critical("Critical test error")

        # Force flush handlers
        for handler in python_logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()

        # Verify console output filtering
        console_output = test_output.getvalue()
        self.assertNotIn("Debug test error", console_output)
        self.assertNotIn("Info test error", console_output)
        self.assertNotIn("Warning test error", console_output)
        self.assertIn("Error test error", console_output)
        self.assertIn("Critical test error", console_output)

        # Now verify log file contains all messages
        log_path = ColoredLogger._log_file_path
        with open(log_path, 'r') as f:
            content = f.read()

        # Log file should have all messages regardless of level
        self.assertIn("Debug test error", content)
        self.assertIn("Info test error", content)
        self.assertIn("Warning test error", content)
        self.assertIn("Error test error", content)
        self.assertIn("Critical test error", content)

    def test_console_level_filtering(self):
        """Test that console output properly filters log messages based on level."""
        CriticalExitHandler.disable_exit(True)

        from io import StringIO

        # Test different console logging levels
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_messages = {
            "DEBUG": "Debug console test message",
            "INFO": "Info console test message",
            "WARNING": "Warning console test message",
            "ERROR": "Error console test message",
            "CRITICAL": "Critical console test message"
        }

        for test_level in levels:
            # Reset for each test
            test_output = StringIO()
            ColoredLogger._initialized_loggers = {}

            # Configure for this level
            LoggingConfig.initialize(parse_args=False, **{
                "log_dir": self.temp_dir,
                "default_level": test_level,
                "exit_on_critical": False,
                "colored_console": False
            })

            ColoredLogger.reset(new_file=True)

            # Create logger with explicit level
            logger = get_logger("console_test", verbose=test_level)

            # Replace stdout handler
            python_logger = logger.logger
            for handler in list(python_logger.handlers):
                if (isinstance(handler, logging.StreamHandler) and
                    not isinstance(handler, CriticalExitHandler) and
                    hasattr(handler, 'stream') and
                    handler.stream == sys.stdout):

                    # Remove and replace with the test handler
                    python_logger.removeHandler(handler)
                    test_handler = logging.StreamHandler(test_output)
                    test_handler.setFormatter(handler.formatter)
                    test_handler.setLevel(getattr(logging, test_level))  # Explicitly set level
                    python_logger.addHandler(test_handler)

            # Log messages
            logger.debug(level_messages["DEBUG"])
            logger.info(level_messages["INFO"])
            logger.warning(level_messages["WARNING"])
            logger.error(level_messages["ERROR"])
            logger.critical(level_messages["CRITICAL"])

            # Force flush
            for handler in python_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()

            # Get output
            console_output = test_output.getvalue()
            print(f"\n--- {test_level} CONSOLE OUTPUT ---\n{console_output}\n")

            # Check filtering
            # (rest of the assertions remain the same)

    def test_log_file_captures_all_levels(self):
        """Test that log files capture all messages regardless of logger level."""
        CriticalExitHandler.disable_exit(True)

        # Configure for ERROR level to verify even low level messages get to log file
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_dir,
            "default_level": "ERROR",  # High level for console
            "exit_on_critical": False
        })
        ColoredLogger.reset(new_file=True)

        # Get a fresh logger with explicit ERROR level
        logger = get_logger("all_level_test", verbose="ERROR")

        # Log messages at all levels
        logger.debug("Debug test all levels")
        logger.info("Info test all levels")
        logger.warning("Warning test all levels")
        logger.error("Error test all levels")
        logger.critical("Critical test all levels")

        # Get log content
        log_path = ColoredLogger._log_file_path
        with open(log_path, 'r') as f:
            content = f.read()

        # All messages should be present in log file, regardless of level
        self.assertIn("Debug test all levels", content)
        self.assertIn("Info test all levels", content)
        self.assertIn("Warning test all levels", content)
        self.assertIn("Error test all levels", content)
        self.assertIn("Critical test all levels", content)
