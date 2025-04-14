"""
Test suite for validating prismalog with multithreading.

This module verifies that the prismalog package correctly handles
concurrent logging from multiple threads without issues like:
- Thread-safety problems
- Log entry corruption
- Missing log entries
- Interleaved log lines
"""

import os
import re
import time
import threading
import tempfile
import unittest
from queue import Queue
from typing import List
from prismalog import get_logger, LoggingConfig, ColoredLogger

class TestMultithreading(unittest.TestCase):
    """Test class for multithreading validation of the prismalog package."""

    def setUp(self):
        """Set up test environment before each test."""
        # Use a temporary log directory for tests
        self.temp_log_dir = tempfile.mkdtemp(prefix="log_thread_test_")

        # Initialize with test configuration
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_log_dir,
            "default_level": "DEBUG",
            "rotation_size_mb": 1,
            "colored_console": False,  # Disable colors for easier testing
            "exit_on_critical": False  # Don't exit on critical logs in tests
        })

        # Reset logger to ensure clean state
        ColoredLogger.reset(new_file=True)

        # Store the log file path for checking later
        self.log_file = ColoredLogger._log_file_path

        # Create a queue for thread results
        self.thread_results = Queue()

    def tearDown(self):
        """Clean up after each test."""
        # Remove all temporary log files
        if os.path.exists(self.temp_log_dir):
            for file in os.listdir(self.temp_log_dir):
                try:
                    os.remove(os.path.join(self.temp_log_dir, file))
                except:
                    pass
            os.rmdir(self.temp_log_dir)

    def thread_worker(self, thread_id: int, iterations: int, levels: List[str]):
        """
        Worker function for test threads.

        Args:
            thread_id: Unique identifier for the thread
            iterations: Number of log messages to generate
            levels: List of log levels to use (rotating)
        """
        try:
            # Get a logger for this thread
            logger = get_logger(f"thread_{thread_id}")

            # Track timing and success
            results = {
                "thread_id": thread_id,
                "messages_sent": 0,
                "errors": 0
            }

            # Generate log messages
            for i in range(iterations):
                level = levels[i % len(levels)]
                message = f"Thread {thread_id} message {i} with level {level}"

                try:
                    if level == "DEBUG":
                        logger.debug(message)
                    elif level == "INFO":
                        logger.info(message)
                    elif level == "WARNING":
                        logger.warning(message)
                    elif level == "ERROR":
                        logger.error(message)
                    elif level == "CRITICAL":
                        logger.critical(message)

                    results["messages_sent"] += 1
                except Exception as e:
                    results["errors"] += 1
                    results.setdefault("error_details", []).append(str(e))

            # Report results back through the queue
            self.thread_results.put(results)

        except Exception as e:
            self.thread_results.put({
                "thread_id": thread_id,
                "error": str(e)
            })

    def test_concurrent_logging_small_scale(self):
        """Test concurrent logging with a small number of threads and messages."""
        num_threads = 5
        iterations = 20
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

        threads = []

        # Create and start threads
        for i in range(num_threads):
            t = threading.Thread(
                target=self.thread_worker,
                args=(i, iterations, levels)
            )
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Collect results
        results = []
        while not self.thread_results.empty():
            results.append(self.thread_results.get())

        # Check that all threads completed successfully
        self.assertEqual(len(results), num_threads)

        # Check that all messages were sent
        total_messages = sum(r["messages_sent"] for r in results)
        self.assertEqual(total_messages, num_threads * iterations)

        # Check that no errors occurred
        total_errors = sum(r.get("errors", 0) for r in results)
        self.assertEqual(total_errors, 0)

        # Wait for logs to be flushed
        time.sleep(0.1)

        # Read the log file and verify
        with open(self.log_file, 'r') as f:
            log_content = f.read()

        # Check that all messages are in the log
        for thread_id in range(num_threads):
            for i in range(iterations):
                # Check for at least one message from each thread/iteration
                pattern = f"thread_{thread_id}.*message {i}"
                self.assertRegex(log_content, pattern)

    def test_concurrent_logging_medium_scale(self):
        """Test concurrent logging with a moderate number of threads and messages."""
        num_threads = 10
        iterations = 50
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

        threads = []

        # Create and start threads
        for i in range(num_threads):
            t = threading.Thread(
                target=self.thread_worker,
                args=(i, iterations, levels)
            )
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Wait for logs to be flushed
        time.sleep(0.2)

        # Read the log file and count occurrences
        message_counts = {}

        with open(self.log_file, 'r') as f:
            for line in f:
                match = re.search(r'thread_(\d+).*message (\d+)', line)
                if match:
                    thread_id = int(match.group(1))
                    message_id = int(match.group(2))
                    key = f"{thread_id}_{message_id}"
                    message_counts[key] = message_counts.get(key, 0) + 1

        # Check that the log contains the right number of log entries
        # (accounting for some messages being filtered by level)
        self.assertGreaterEqual(len(message_counts), num_threads * iterations * 0.75)

        # Check that there are no duplicate entries (each message appears exactly once)
        duplicate_entries = [key for key, count in message_counts.items() if count > 1]
        self.assertEqual(len(duplicate_entries), 0,
                         f"Found {len(duplicate_entries)} duplicate log entries")

    def test_thread_logger_independence(self):
        """Test that loggers in different threads maintain independent contexts."""
        # Create an event for synchronization
        sync_event = threading.Event()

        def thread_a():
            logger = get_logger("thread_a_logger")
            logger.info("Thread A initial message")

            # Set thread local context
            logger.thread_data = {"context": "thread_a_context"}

            # Signal thread B to continue
            sync_event.set()

            # Wait a moment for thread B to do its work
            time.sleep(0.1)

            # Log again with context
            logger.info(f"Thread A with context: {getattr(logger, 'thread_data', None)}")
            self.thread_results.put({
                "thread": "A",
                "context": getattr(logger, "thread_data", None)
            })

        def thread_b():
            logger = get_logger("thread_b_logger")

            # Wait for thread A to set its context
            sync_event.wait()

            logger.info("Thread B initial message")

            # Set a different context
            logger.thread_data = {"context": "thread_b_context"}

            logger.info(f"Thread B with context: {getattr(logger, 'thread_data', None)}")
            self.thread_results.put({
                "thread": "B",
                "context": getattr(logger, "thread_data", None)
            })

        # Start the threads
        thread_a = threading.Thread(target=thread_a)
        thread_b = threading.Thread(target=thread_b)

        thread_a.start()
        thread_b.start()

        thread_a.join()
        thread_b.join()

        # Collect and verify results
        results = {}
        while not self.thread_results.empty():
            r = self.thread_results.get()
            results[r["thread"]] = r["context"]

        # Check that each thread maintained its own context
        self.assertEqual(len(results), 2)
        self.assertIn("A", results)
        self.assertIn("B", results)
        self.assertEqual(results["A"]["context"], "thread_a_context")
        self.assertEqual(results["B"]["context"], "thread_b_context")

    def test_logging_under_thread_stress(self):
        """Test logging under heavy thread contention."""
        # Create a large number of threads that log simultaneously
        num_threads = 20
        iterations = 30

        # Use a mix of short and long messages to test buffering
        def worker_varied(thread_id):
            logger = get_logger(f"stress_{thread_id}")

            for i in range(iterations):
                if i % 3 == 0:
                    # Long message
                    logger.info(f"Thread {thread_id} iteration {i}: " + "X" * 1000)
                elif i % 3 == 1:
                    # Short message
                    logger.debug(f"T{thread_id}:{i}")
                else:
                    # Medium with formatting
                    logger.warning("Thread %(tid)s warning %(i)s with data",
                                   {'tid': thread_id, 'i': i})

                # Add some randomness in timing
                if i % 5 == 0:
                    time.sleep(0.001)

        # Start all threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker_varied, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Allow time for log writing
        time.sleep(0.5)

        # Verify log file exists and contains data
        self.assertTrue(os.path.exists(self.log_file))

        # Count lines in the log file
        with open(self.log_file, 'r') as f:
            lines = f.readlines()

        # The log should contain at least a substantial portion of the expected messages
        # (accounting for log level filtering)
        min_expected = int(num_threads * iterations * 0.6)  # 60% of messages should be logged
        self.assertGreaterEqual(len(lines), min_expected,
                               f"Expected at least {min_expected} log lines, got {len(lines)}")

        # Check for corrupt lines (lines that don't match expected format)
        corrupt_lines = []
        expected_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - .* - stress_\d+ - \[.*\] - .*'

        for i, line in enumerate(lines, 1):
            if not re.match(expected_pattern, line):
                corrupt_lines.append((i, line))

        self.assertEqual(len(corrupt_lines), 0,
                        f"Found {len(corrupt_lines)} corrupted log lines")


if __name__ == '__main__':
    unittest.main()