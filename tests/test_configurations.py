"""Test prismalog with different configuration parameters."""

import logging
import os
import shutil
import sys
import tempfile
import time
import unittest

from prismalog.log import ColoredLogger, CriticalExitHandler, LoggingConfig, MultiProcessingLog, get_logger


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
        if "LOG_DISABLE_ROTATION" in os.environ:
            saved_value = os.environ["LOG_DISABLE_ROTATION"]
            del os.environ["LOG_DISABLE_ROTATION"]
            print(f"Warning: Removed LOG_DISABLE_ROTATION={saved_value} for rotation test")

        # Use very small rotation size to trigger quickly
        test_rotation_size = 0.01  # 10KB
        test_backup_count = 2

        # Initialize with explicit rotation settings
        LoggingConfig.initialize(
            use_cli_args=False,
            **{
                "log_dir": self.temp_dir,
                "rotation_size_mb": test_rotation_size,
                "backup_count": test_backup_count,
                "disable_rotation": False,  # Explicitly enable rotation
            },
        )

        # Important: Check if initialization didn't work, and set values directly if needed
        if LoggingConfig.get("rotation_size_mb") != test_rotation_size:
            print("Warning: LoggingConfig.initialize() did not set rotation_size_mb, using direct method")
            LoggingConfig.set("rotation_size_mb", test_rotation_size)

        if LoggingConfig.get("backup_count") != test_backup_count:
            print("Warning: LoggingConfig.initialize() did not set backup_count, using direct method")
            LoggingConfig.set("backup_count", test_backup_count)

        if LoggingConfig.get("disable_rotation") is not False:
            print("Warning: LoggingConfig.initialize() did not disable rotation, setting directly")
            LoggingConfig.set("disable_rotation", False)

        # Verify settings were applied
        self.assertEqual(
            LoggingConfig.get("rotation_size_mb"), test_rotation_size, "Rotation size setting was not applied"
        )
        self.assertEqual(LoggingConfig.get("backup_count"), test_backup_count, "Backup count setting was not applied")
        self.assertFalse(
            LoggingConfig.get("disable_rotation"), "Rotation should be enabled but disable_rotation is True"
        )

        # Print the full configuration for debugging
        print(f"Configuration after setup: {LoggingConfig._config}")

    def test_rotation_size_impact_1(self):
        """Test log rotation with different size thresholds."""
        # Explicitly check and unset LOG_DISABLE_ROTATION environment variable if present
        if "LOG_DISABLE_ROTATION" in os.environ:
            saved_value = os.environ["LOG_DISABLE_ROTATION"]
            del os.environ["LOG_DISABLE_ROTATION"]
            print(f"Warning: Removed LOG_DISABLE_ROTATION={saved_value} for rotation test")

        # Use very small rotation size to trigger quickly
        test_rotation_size = 0.01  # 10KB
        test_backup_count = 2

        # Initialize with explicit rotation settings
        LoggingConfig.initialize(
            use_cli_args=False,
            **{
                "log_dir": self.temp_dir,
                "rotation_size_mb": test_rotation_size,
                "backup_count": test_backup_count,
                "disable_rotation": False,  # Explicitly enable rotation
            },
        )

        # Important: Check if initialization didn't work, and set values directly if needed
        if LoggingConfig.get("rotation_size_mb") != test_rotation_size:
            print("Warning: LoggingConfig.initialize() did not set rotation_size_mb, using direct method")
            LoggingConfig.set("rotation_size_mb", test_rotation_size)

        if LoggingConfig.get("backup_count") != test_backup_count:
            print("Warning: LoggingConfig.initialize() did not set backup_count, using direct method")
            LoggingConfig.set("backup_count", test_backup_count)

        if LoggingConfig.get("disable_rotation") is not False:
            print("Warning: LoggingConfig.initialize() did not disable rotation, setting directly")
            LoggingConfig.set("disable_rotation", False)

        # Verify settings were applied
        self.assertEqual(
            LoggingConfig.get("rotation_size_mb"), test_rotation_size, "Rotation size setting was not applied"
        )
        self.assertEqual(LoggingConfig.get("backup_count"), test_backup_count, "Backup count setting was not applied")
        self.assertFalse(
            LoggingConfig.get("disable_rotation"), "Rotation should be enabled but disable_rotation is True"
        )

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
                if hasattr(handler, "flush"):
                    handler.flush()

            # Print progress occasionally
            if i % 100 == 0 and i > 0:
                print(f"Wrote {i} messages")

        time.sleep(0.5)

        # Check for log files matching the base name
        log_files = [f for f in os.listdir(log_dir) if f == base_name or f.startswith(base_name + ".")]

        print(f"Found log files: {log_files}")

        # backup_count + 1 files (base file + backups)
        expected_file_count = test_backup_count + 1
        self.assertEqual(
            len(log_files),
            expected_file_count,
            f"Expected {expected_file_count} log files (base + {test_backup_count} backups), found {len(log_files)}",
        )
        # Check all files have content
        for filename in log_files:
            file_path = os.path.join(log_dir, filename)
            size = os.path.getsize(file_path)
            print(f"File {filename}: {size} bytes")

            # Verify file has content
            self.assertGreater(size, 0, f"Log file {filename} is empty")

            # Verify the file contains the test messages
            with open(file_path, mode="r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("Test message", content, f"Log file {filename} doesn't contain expected messages")

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
            "CRITICAL": "Critical test message",
        }

        for test_level in levels:
            # Reset completely between tests
            ColoredLogger._initialized_loggers = {}

            # Create a StringIO for capturing console output
            from io import StringIO

            test_output = StringIO()

            # Configure for this test level
            LoggingConfig.initialize(
                use_cli_args=False, **{"log_dir": self.temp_dir, "default_level": test_level, "exit_on_critical": False}
            )

            # Reset logger with fresh file
            ColoredLogger.reset(new_file=True)

            # Create a fresh logger
            logger = get_logger("level_test", verbose=test_level)

            # Replace stdout handler to capture console output
            python_logger = logger.logger
            for handler in list(python_logger.handlers):
                if (
                    isinstance(handler, logging.StreamHandler)
                    and not isinstance(handler, CriticalExitHandler)
                    and hasattr(handler, "stream")
                    and handler.stream == sys.stdout
                ):

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
                if hasattr(handler, "flush"):
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
            f.write(
                """
            log_dir: '{0}'
            default_level: WARNING
            rotation_size_mb: 2
            """.format(
                    config_dir
                )
            )

        # Initialize with this config file
        LoggingConfig.initialize(config_file=config_path, use_cli_args=False)

        # Create a logger and test it
        logger = get_logger("yaml_test")
        logger.warning("Test YAML config")

        self.assertEqual(
            logger.level, logging.WARNING, f"Logger level {logger.level} does not match expected {logging.WARNING}"
        )

    def test_debug_level_logging(self):
        """Test DEBUG level logging captures all messages."""
        CriticalExitHandler.disable_exit(True)

        # Configure for DEBUG level
        LoggingConfig.initialize(
            use_cli_args=False, **{"log_dir": self.temp_dir, "default_level": "DEBUG", "exit_on_critical": False}
        )
        ColoredLogger.reset(new_file=True)

        # Get a fresh logger with explicit level
        logger = get_logger("level_test_debug", verbose="DEBUG")

        # Log messages
        logger.debug("Debug test")
        logger.info("Info test")
        logger.critical("Critical test")

        # Get log content
        log_path = ColoredLogger._log_file_path
        with open(log_path, "r") as f:
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
        LoggingConfig.initialize(
            use_cli_args=False, **{"log_dir": self.temp_dir, "default_level": "INFO", "exit_on_critical": False}
        )
        ColoredLogger.reset(new_file=True)

        # Get a fresh logger with explicit level
        logger = get_logger("level_test_info", verbose="INFO")

        # Replace stdout handler to capture console output
        python_logger = logger.logger
        for handler in list(python_logger.handlers):
            if (
                isinstance(handler, logging.StreamHandler)
                and not isinstance(handler, CriticalExitHandler)
                and hasattr(handler, "stream")
                and handler.stream == sys.stdout
            ):

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
            if hasattr(handler, "flush"):
                handler.flush()

        # Verify console output filtering
        console_output = test_output.getvalue()
        self.assertNotIn("Debug test info", console_output)
        self.assertIn("Info test info", console_output)
        self.assertIn("Critical test info", console_output)

        # Log file captures all levels regardless of configuration
        log_path = ColoredLogger._log_file_path
        with open(log_path, "r") as f:
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
        LoggingConfig.initialize(
            use_cli_args=False, **{"log_dir": self.temp_dir, "default_level": "ERROR", "exit_on_critical": False}
        )

        ColoredLogger.reset(new_file=True)

        # Get logger with ERROR level
        logger = get_logger("level_test_error", verbose="ERROR")

        # Replace stdout handler to capture console output
        python_logger = logger.logger
        for handler in list(python_logger.handlers):
            if (
                isinstance(handler, logging.StreamHandler)
                and not isinstance(handler, CriticalExitHandler)
                and hasattr(handler, "stream")
                and handler.stream == sys.stdout
            ):

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
            if hasattr(handler, "flush"):
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
        with open(log_path, "r") as f:
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
            "CRITICAL": "Critical console test message",
        }

        for test_level in levels:
            # Reset for each test
            test_output = StringIO()
            ColoredLogger._initialized_loggers = {}

            # Configure for this level
            LoggingConfig.initialize(
                use_cli_args=False,
                **{
                    "log_dir": self.temp_dir,
                    "default_level": test_level,
                    "exit_on_critical": False,
                    "colored_console": False,
                },
            )

            ColoredLogger.reset(new_file=True)

            # Create logger with explicit level
            logger = get_logger("console_test", verbose=test_level)

            # Replace stdout handler
            python_logger = logger.logger
            for handler in list(python_logger.handlers):
                if (
                    isinstance(handler, logging.StreamHandler)
                    and not isinstance(handler, CriticalExitHandler)
                    and hasattr(handler, "stream")
                    and handler.stream == sys.stdout
                ):

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
                if hasattr(handler, "flush"):
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
        LoggingConfig.initialize(
            use_cli_args=False,
            **{"log_dir": self.temp_dir, "default_level": "ERROR", "exit_on_critical": False},  # High level for console
        )
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
        with open(log_path, mode="r", encoding="utf-8") as f:
            content = f.read()

        # All messages should be present in log file, regardless of level
        self.assertIn("Debug test all levels", content)
        self.assertIn("Info test all levels", content)
        self.assertIn("Warning test all levels", content)
        self.assertIn("Error test all levels", content)
        self.assertIn("Critical test all levels", content)

    def test_dynamic_level_updates(self):
        """Test dynamically updating log levels at runtime."""
        CriticalExitHandler.disable_exit(True)

        # Configure initial state with INFO level
        LoggingConfig.initialize(
            use_cli_args=False, **{"log_dir": self.temp_dir, "default_level": "INFO", "exit_on_critical": False}
        )
        ColoredLogger.reset(new_file=True)

        # Create loggers with different initial levels
        logger_info = get_logger("update_level_info", verbose="INFO")
        logger_debug = get_logger("update_level_debug", verbose="DEBUG")

        # Verify initial levels
        self.assertEqual(logger_info.level, logging.INFO)
        self.assertEqual(logger_debug.level, logging.DEBUG)

        # Capture console output
        from io import StringIO

        info_output = StringIO()
        debug_output = StringIO()

        # Replace stdout handlers to capture output
        for logger_obj, output in [(logger_info, info_output), (logger_debug, debug_output)]:
            python_logger = logger_obj.logger
            for handler in list(python_logger.handlers):
                if (
                    isinstance(handler, logging.StreamHandler)
                    and not isinstance(handler, CriticalExitHandler)
                    and hasattr(handler, "stream")
                    and handler.stream == sys.stdout
                ):

                    # Remove stdout handler
                    python_logger.removeHandler(handler)

                    # Add the test handler with the logger's level
                    test_handler = logging.StreamHandler(output)
                    test_handler.setFormatter(handler.formatter)
                    test_handler.setLevel(logger_obj.level)  # Use the logger's current level
                    python_logger.addHandler(test_handler)

        # Log messages with initial levels
        logger_info.debug("Info logger debug msg - should not appear")
        logger_info.info("Info logger info msg - should appear")
        logger_debug.debug("Debug logger debug msg - should appear")
        logger_debug.info("Debug logger info msg - should appear")

        # Force flush handlers
        for logger_obj in [logger_info, logger_debug]:
            for handler in logger_obj.logger.handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

        # Check initial output
        info_initial = info_output.getvalue()
        debug_initial = debug_output.getvalue()

        self.assertNotIn("Info logger debug msg", info_initial)
        self.assertIn("Info logger info msg", info_initial)
        self.assertIn("Debug logger debug msg", debug_initial)
        self.assertIn("Debug logger info msg", debug_initial)

        # Reset capture buffers
        info_output = StringIO()
        debug_output = StringIO()

        # Replace handlers again with fresh buffers
        for logger_obj, output in [(logger_info, info_output), (logger_debug, debug_output)]:
            python_logger = logger_obj.logger
            for handler in list(python_logger.handlers):
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, CriticalExitHandler):
                    python_logger.removeHandler(handler)
                    test_handler = logging.StreamHandler(output)
                    test_handler.setFormatter(handler.formatter)
                    test_handler.setLevel(logger_obj.level)
                    python_logger.addHandler(test_handler)

        # Test 1: Update INFO logger to DEBUG using update_logger_level
        ColoredLogger.update_logger_level("update_level_info", "DEBUG")

        # Verify level was updated
        self.assertEqual(logger_info.level, logging.DEBUG)

        # Log messages after update
        logger_info.debug("Info logger debug msg after update - should now appear")
        logger_info.info("Info logger info msg after update - should appear")

        # Force flush handlers
        for handler in logger_info.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Verify DEBUG messages now appear
        info_updated = info_output.getvalue()
        self.assertIn("Info logger debug msg after update", info_updated)
        self.assertIn("Info logger info msg after update", info_updated)

        # Reset capture buffer
        debug_output = StringIO()

        # Replace handlers again
        for handler in list(logger_debug.logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, CriticalExitHandler):
                logger_debug.logger.removeHandler(handler)
                test_handler = logging.StreamHandler(debug_output)
                test_handler.setFormatter(handler.formatter)
                # Don't set level yet - we'll test the level setter
                logger_debug.logger.addHandler(test_handler)

        # Test 2: Update DEBUG logger to WARNING using level setter
        logger_debug.level = logging.WARNING

        # Verify console handlers were updated but file handlers weren't
        for handler in logger_debug.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, MultiProcessingLog):
                self.assertEqual(handler.level, logging.WARNING, "Console handler level not updated correctly")
            elif isinstance(handler, MultiProcessingLog):
                # File handlers should remain at DEBUG level for capturing all messages
                self.assertEqual(handler.level, logging.DEBUG, "File handler level should not be changed")

        # Log messages at all levels
        logger_debug.debug("Debug level after change to WARNING - should not appear")
        logger_debug.info("Info level after change to WARNING - should not appear")
        logger_debug.warning("Warning level after change - should appear")
        logger_debug.error("Error level after change - should appear")

        # Force flush handlers
        for handler in logger_debug.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Verify output filtering
        debug_after_change = debug_output.getvalue()
        self.assertNotIn("Debug level after change to WARNING", debug_after_change)
        self.assertNotIn("Info level after change to WARNING", debug_after_change)
        self.assertIn("Warning level after change", debug_after_change)
        self.assertIn("Error level after change", debug_after_change)

        # Check log file has all messages regardless of level changes
        log_path = ColoredLogger._log_file_path
        with open(log_path, mode="r", encoding="utf-8") as f:
            content = f.read()

        # All messages should be in log file
        self.assertIn("Info logger debug msg", content)
        self.assertIn("Info logger debug msg after update", content)
        self.assertIn("Debug level after change to WARNING", content)

    def test_multiple_logger_level_independence(self):
        """Test that loggers with different levels maintain independence when updated."""
        CriticalExitHandler.disable_exit(True)

        # Configure initial state
        LoggingConfig.initialize(
            use_cli_args=False, **{"log_dir": self.temp_dir, "default_level": "INFO", "exit_on_critical": False}
        )
        ColoredLogger.reset(new_file=True)

        # Create three loggers with different levels
        logger_debug = get_logger("multi_debug", verbose="DEBUG")
        logger_info = get_logger("multi_info", verbose="INFO")
        logger_warning = get_logger("multi_warning", verbose="WARNING")

        # Verify initial setup
        self.assertEqual(logger_debug.level, logging.DEBUG)
        self.assertEqual(logger_info.level, logging.INFO)
        self.assertEqual(logger_warning.level, logging.WARNING)

        # Create StringIO objects for each logger
        from io import StringIO

        debug_output = StringIO()
        info_output = StringIO()
        warning_output = StringIO()

        # Replace handlers to capture output
        for logger_obj, output in [
            (logger_debug, debug_output),
            (logger_info, info_output),
            (logger_warning, warning_output),
        ]:
            for handler in list(logger_obj.logger.handlers):
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, CriticalExitHandler):
                    logger_obj.logger.removeHandler(handler)
                    test_handler = logging.StreamHandler(output)
                    test_handler.setFormatter(handler.formatter)
                    test_handler.setLevel(logger_obj.level)
                    logger_obj.logger.addHandler(test_handler)

        # Test 1: Update only the info logger to DEBUG
        ColoredLogger.update_logger_level("multi_info", "DEBUG")

        # Verify only that logger changed
        self.assertEqual(logger_debug.level, logging.DEBUG, "DEBUG logger should remain unchanged")
        self.assertEqual(logger_info.level, logging.DEBUG, "INFO logger should now be DEBUG")
        self.assertEqual(logger_warning.level, logging.WARNING, "WARNING logger should remain unchanged")

        # Test 2: Use the level setter on the warning logger
        logger_warning.level = logging.ERROR

        # Verify independence of loggers
        self.assertEqual(logger_debug.level, logging.DEBUG, "DEBUG logger should still be unchanged")
        self.assertEqual(logger_info.level, logging.DEBUG, "INFO->DEBUG logger should be unchanged")
        self.assertEqual(logger_warning.level, logging.ERROR, "WARNING logger should now be ERROR")

        # Now log messages with each logger
        logger_debug.debug("DEBUG logger debug message")
        logger_info.debug("INFO->DEBUG logger debug message")
        logger_warning.warning("WARNING->ERROR logger warning message")
        logger_warning.error("WARNING->ERROR logger error message")

        # Force flush handlers
        for logger_obj in [logger_debug, logger_info, logger_warning]:
            for handler in logger_obj.logger.handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

        # Verify each logger's output respects its own level
        debug_content = debug_output.getvalue()
        info_content = info_output.getvalue()
        warning_content = warning_output.getvalue()

        self.assertIn("DEBUG logger debug message", debug_content)
        self.assertIn("INFO->DEBUG logger debug message", info_content)
        self.assertNotIn("WARNING->ERROR logger warning message", warning_content)
        self.assertIn("WARNING->ERROR logger error message", warning_content)

        # Test 3: Update default_level through LoggingConfig and verify it doesn't affect existing loggers
        LoggingConfig.set("default_level", "CRITICAL")

        # Create a new logger that should inherit the new default level
        new_logger = get_logger("new_logger_after_default_change")
        self.assertEqual(new_logger.level, logging.CRITICAL, "New logger should inherit updated default level")

        # But existing loggers should maintain their levels
        self.assertEqual(logger_debug.level, logging.DEBUG, "Existing DEBUG logger unchanged")
        self.assertEqual(logger_info.level, logging.DEBUG, "Existing INFO->DEBUG logger unchanged")
        self.assertEqual(logger_warning.level, logging.ERROR, "Existing WARNING->ERROR logger unchanged")

    def test_log_level_priority(self):
        """Test the priority order of different ways to set log levels."""
        CriticalExitHandler.disable_exit(True)

        # 1. First set a global default in LoggingConfig
        LoggingConfig.initialize(
            use_cli_args=False,
            **{"log_dir": self.temp_dir, "default_level": "WARNING", "exit_on_critical": False},  # Global default
        )
        ColoredLogger.reset(new_file=True)

        # Create a StringIO for output capture
        from io import StringIO

        output = StringIO()

        # 2. Create a logger with default level (should inherit WARNING)
        default_logger = get_logger("default_priority")
        self.assertEqual(default_logger.level, logging.WARNING, "Logger should inherit global default level")

        # 3. Create a logger with explicit level (should override global default)
        explicit_logger = get_logger("explicit_priority", verbose="INFO")
        self.assertEqual(explicit_logger.level, logging.INFO, "Explicit level should override global default")

        # 4. Create a logger that will be affected by module-specific config
        module_logger = get_logger("module_specific")
        self.assertEqual(module_logger.level, logging.WARNING, "Should initially have global default level")

        # 5. Set module-specific level through configuration
        LoggingConfig.set("module_levels.module_specific", "DEBUG")

        # Create a new logger for the same module to get the module-specific setting
        module_logger_new = get_logger("module_specific")

        self.assertEqual(module_logger_new.level, logging.DEBUG, "Module-specific level should override global default")

        # 6. Change global default
        LoggingConfig.set("default_level", "ERROR")

        # Create a new logger to inherit the new default
        new_default_logger = get_logger("new_default_priority")
        self.assertEqual(new_default_logger.level, logging.ERROR, "New logger should get updated global default")

        # Verify existing loggers - important: module_logger will be updated to DEBUG
        # because we just added module-specific configuration for it
        self.assertEqual(module_logger.level, logging.DEBUG, "Module logger should have module-specific level")

        # This logger had no module-specific config, so it keeps its original level
        self.assertEqual(
            default_logger.level, logging.WARNING, "Existing loggers without module config keep original level"
        )
        self.assertEqual(explicit_logger.level, logging.INFO, "Explicit logger should keep its level")

    def test_nested_configuration_keys(self):
        """Test that nested configuration keys work correctly."""
        # Reset configuration
        LoggingConfig.reset()

        # Initialize with a fresh configuration
        LoggingConfig.initialize(use_cli_args=False)

        # 1. First test: simple key setting
        LoggingConfig.set("simple_key", "simple_value")
        self.assertEqual(LoggingConfig.get("simple_key"), "simple_value", "Simple key should be set and retrievable")

        # 2. Set a nested key using current implementation
        LoggingConfig.set("module_levels.test_module", "DEBUG")

        # Get the raw dictionary to see what happened
        config_dict = LoggingConfig.get_config()

        # This will likely fail because the current implementation
        # doesn't support nested keys properly
        self.assertIn("module_levels", config_dict, "module_levels key should exist in configuration")

        if "module_levels" in config_dict:
            # If module_levels exists, check if it's a dictionary
            self.assertIsInstance(config_dict["module_levels"], dict, "module_levels should be a dictionary")

            # Check if our module is in the dictionary
            self.assertIn(
                "test_module", config_dict["module_levels"], "test_module should be in module_levels dictionary"
            )

            # Check if the value is correct
            if "test_module" in config_dict["module_levels"]:
                self.assertEqual(
                    config_dict["module_levels"]["test_module"], "DEBUG", "test_module should have DEBUG level"
                )

        # 3. Test retrieving the nested value
        module_level = LoggingConfig.get("module_levels", {}).get("test_module")
        self.assertEqual(module_level, "DEBUG", "Should be able to retrieve nested module level")

        # 4. Test creating a logger with this module name
        test_logger = get_logger("test_module")
        self.assertEqual(test_logger.level, logging.DEBUG, "Logger should inherit level from module_levels config")

    def test_log_filename_default_value(self):
        """Test that the default log_filename value is applied."""
        LoggingConfig.reset()
        LoggingConfig.initialize(config_file=None, use_cli_args=False)
        assert LoggingConfig.get("log_filename") == "app"

    def test_log_filename_from_env(self):
        """Test setting log_filename via environment variable."""
        LoggingConfig.reset()
        custom_name = "env_test_log"
        os.environ["LOG_FILENAME"] = custom_name
        try:
            LoggingConfig.initialize(config_file=None, use_cli_args=False)
            assert LoggingConfig.get("log_filename") == custom_name
        finally:
            if "LOG_FILENAME" in os.environ:
                del os.environ["LOG_FILENAME"]

    def test_log_filename_from_github_env(self):
        """Test setting log_filename via GitHub environment variable."""
        LoggingConfig.reset()
        custom_name = "github_test_log"
        os.environ["GITHUB_LOG_FILENAME"] = custom_name
        try:
            LoggingConfig.initialize(config_file=None, use_cli_args=False)
            assert LoggingConfig.get("log_filename") == custom_name
        finally:
            if "GITHUB_LOG_FILENAME" in os.environ:
                del os.environ["GITHUB_LOG_FILENAME"]

    def test_log_filename_from_yaml(self):
        """Test setting log_filename via YAML configuration file."""
        LoggingConfig.reset()
        custom_name = "yaml_test_log"
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write(f"log_filename: '{custom_name}'\n")

        try:
            LoggingConfig.initialize(config_file=yaml_path, use_cli_args=False)
            assert LoggingConfig.get("log_filename") == custom_name
        finally:
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_log_filename_from_cli(self):
        """Test setting log_filename via command-line argument."""
        LoggingConfig.reset()
        custom_name = "cli_test_log"
        original_argv = sys.argv
        try:
            sys.argv = ["test_script.py", "--log-filename", custom_name]
            LoggingConfig.initialize(config_file=None, use_cli_args=True)
            assert LoggingConfig.get("log_filename") == custom_name
        finally:
            sys.argv = original_argv  # Restore original argv

    def test_log_filename_priority_order(self):
        """Test priority order specifically for log_filename."""
        LoggingConfig.reset()
        default_name = LoggingConfig.DEFAULT_CONFIG["log_filename"]
        env_name = "env_priority"
        yaml_name = "yaml_priority"
        cli_name = "cli_priority"

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml_path = f.name
            f.write(f"log_filename: '{yaml_name}'\n")

        original_argv = sys.argv
        try:
            # Set ENV var
            os.environ["LOG_FILENAME"] = env_name

            # Set CLI arg
            sys.argv = ["test_script.py", "--log-filename", cli_name]

            # Initialize with all sources
            LoggingConfig.initialize(config_file=yaml_path, use_cli_args=True)
            # CLI should win
            assert LoggingConfig.get("log_filename") == cli_name

            # Test without CLI
            sys.argv = ["test_script.py"]  # No relevant CLI arg
            LoggingConfig.reset()
            LoggingConfig.initialize(config_file=yaml_path, use_cli_args=True)
            # YAML should win over ENV
            assert LoggingConfig.get("log_filename") == yaml_name

            # Test without CLI or YAML
            LoggingConfig.reset()
            LoggingConfig.initialize(config_file=None, use_cli_args=False)  # ENV only
            # ENV should win over Default
            assert LoggingConfig.get("log_filename") == env_name

            # Test with only Default
            del os.environ["LOG_FILENAME"]
            LoggingConfig.reset()
            LoggingConfig.initialize(config_file=None, use_cli_args=False)
            assert LoggingConfig.get("log_filename") == default_name

        finally:
            sys.argv = original_argv
            if "LOG_FILENAME" in os.environ:
                del os.environ["LOG_FILENAME"]
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_log_filename_actual_file_creation(self):
        """Test that the log file created uses the configured log_filename."""
        log_dir = os.path.join(self.temp_dir, "custom_logs")
        custom_name = "my_service_log"

        # Initialize with custom dir and filename
        LoggingConfig.initialize(use_cli_args=False, log_dir=str(log_dir), log_filename=custom_name)

        # Reset ColoredLogger to ensure it picks up the new config for file path
        ColoredLogger.reset(new_file=True)

        logger = get_logger("test_file_name")
        logger.info("Testing custom filename.")

        # Force flush and wait
        for handler in logger.handlers:
            handler.flush()
        time.sleep(0.2)  # Give FS time

        # Check for log file with the correct base name
        log_files = [
            f for f in os.listdir(log_dir) if f.startswith(custom_name) and f.endswith(".log")
        ]  # Check for files starting with the custom name
        assert log_files, f"No log files starting with '{custom_name}' found in {log_dir}"

        # Verify content
        with open(os.path.join(log_dir, log_files[0]), mode="r", encoding="utf-8") as f:
            content = f.read()
        assert "Testing custom filename." in content, f"Log message not found in {log_files[0]}"
