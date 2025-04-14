"""
Test suite for validating prismalog with mixed concurrency models.

This module tests the prismalog package under concurrent use with both
multiprocessing and multithreading combined - a common pattern in real-world
applications. It verifies:

- Correct handling of logs from multiple processes, each with multiple threads
- No corruption or data races between processes and threads
- Proper log sequencing and file integrity
- Log uniqueness (no duplicated log entries)
- Resilience under high concurrency pressure
"""

import os
import re
import time
import random
import multiprocessing
import threading
import tempfile
import unittest
from queue import Queue
from typing import List
from prismalog import get_logger, LoggingConfig, ColoredLogger


class TestMixedConcurrency(unittest.TestCase):
    """Test class for mixed multiprocessing and multithreading validation."""

    def setUp(self):
        """Set up test environment before each test."""
        # Use a temporary log directory for tests
        self.temp_log_dir = tempfile.mkdtemp(prefix="log_mixed_test_")

        # Initialize with test configuration
        LoggingConfig.initialize(parse_args=False, **{
            "log_dir": self.temp_log_dir,
            "default_level": "DEBUG",
            "rotation_size_mb": 5,
            "colored_console": False,  # Disable colors for easier testing
            "exit_on_critical": False,  # Don't exit on critical logs in tests
            "multiprocess_safe": True   # Ensure multiprocess safety is enabled
        })

        # Reset logger to ensure clean state
        ColoredLogger.reset(new_file=True)

        # Store the log file path for checking later
        self.log_file = ColoredLogger._log_file_path

        # Create a multiprocessing queue for process results
        self.result_queue = multiprocessing.Queue()

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

    def thread_worker(self, thread_id: int, process_id: int, thread_results: Queue,
                     iterations: int = 20, levels: List[str] = None):
        """
        Worker function for test threads within a process.

        Args:
            thread_id: Unique identifier for the thread within its process
            process_id: Identifier for the parent process
            thread_results: Queue to collect results (thread-local)
            iterations: Number of log messages to generate
            levels: List of log levels to use (rotating)
        """
        if levels is None:
            levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

        logger_name = f"process_{process_id}_thread_{thread_id}"
        logger = get_logger(logger_name)

        # Track results
        results = {
            "process_id": process_id,
            "thread_id": thread_id,
            "messages_sent": 0,
            "errors": 0
        }

        # Generate log messages
        for i in range(iterations):
            level = levels[i % len(levels)]
            message = f"P{process_id}-T{thread_id} message {i} (level:{level})"

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

        # Report results back to the parent process
        thread_results.put(results)

    def process_with_threads(self, process_id: int, num_threads: int, iterations: int):
        """
        Worker process that spawns multiple threads.

        Args:
            process_id: Unique identifier for this process
            num_threads: Number of threads to spawn within this process
            iterations: Number of log messages per thread
        """
        # This is a per-process queue for thread results
        thread_results = Queue()

        # Create and start threads
        threads = []
        for thread_id in range(num_threads):
            t = threading.Thread(
                target=self.thread_worker,
                args=(thread_id, process_id, thread_results, iterations)
            )
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Collect results from all threads
        process_results = {
            "process_id": process_id,
            "thread_count": num_threads,
            "thread_results": []
        }

        while not thread_results.empty():
            process_results["thread_results"].append(thread_results.get())

        # Send aggregated results back to the main process
        self.result_queue.put(process_results)

    def test_basic_mixed_concurrency(self):
        """Test logging with a simple configuration of processes and threads."""
        num_processes = 3
        threads_per_process = 4
        iterations = 10

        processes = []

        # Create and start processes
        for pid in range(num_processes):
            p = multiprocessing.Process(
                target=self.process_with_threads,
                args=(pid, threads_per_process, iterations)
            )
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join()

        # Collect results
        results = []
        while not self.result_queue.empty():
            results.append(self.result_queue.get())

        # Verify all processes reported
        self.assertEqual(len(results), num_processes,
                         "Not all processes reported results")

        # Check thread results
        thread_success = True
        expected_thread_count = num_processes * threads_per_process
        actual_thread_count = sum(len(p["thread_results"]) for p in results)

        self.assertEqual(actual_thread_count, expected_thread_count,
                         f"Expected {expected_thread_count} thread results, got {actual_thread_count}")

        # Check message counts
        expected_messages = num_processes * threads_per_process * iterations
        actual_messages = sum(sum(t["messages_sent"] for t in p["thread_results"])
                             for p in results)

        self.assertEqual(actual_messages, expected_messages,
                         f"Expected {expected_messages} messages, got {actual_messages}")

        # Check errors
        total_errors = sum(sum(t.get("errors", 0) for t in p["thread_results"])
                          for p in results)
        self.assertEqual(total_errors, 0, f"Found {total_errors} errors during logging")

        # Allow time for log writing
        time.sleep(0.5)

        # Verify log file exists
        self.assertTrue(os.path.exists(self.log_file), "Log file was not created")

        # Analyze log file content
        pattern = r'P(\d+)-T(\d+) message (\d+)'
        message_occurrences = {}

        with open(self.log_file, 'r') as f:
            for line in f:
                matches = re.findall(pattern, line)
                for match in matches:
                    if match:
                        key = f"{match[0]}_{match[1]}_{match[2]}"  # process_thread_message
                        message_occurrences[key] = message_occurrences.get(key, 0) + 1

        # Check for duplicates
        duplicates = [key for key, count in message_occurrences.items() if count > 1]
        self.assertEqual(len(duplicates), 0,
                         f"Found {len(duplicates)} duplicate log entries")

    def test_high_concurrency_pressure(self):
        """Test logging under high concurrency pressure with many processes and threads."""
        num_processes = 5  # Increase this for more stress testing
        min_threads = 3
        max_threads = 8   # Random number of threads per process
        iterations = 15

        processes = []

        # Create processes with varying thread counts
        for pid in range(num_processes):
            threads_count = random.randint(min_threads, max_threads)
            p = multiprocessing.Process(
                target=self.process_with_threads,
                args=(pid, threads_count, iterations)
            )
            processes.append(p)
            p.start()

        # Wait for processes to complete
        for p in processes:
            p.join()

        # Allow more time for log flushing under pressure
        time.sleep(1.0)

        # Verify log file exists and is non-empty
        self.assertTrue(os.path.exists(self.log_file), "Log file was not created")

        file_size = os.path.getsize(self.log_file)
        self.assertGreater(file_size, 0, "Log file is empty")

        # Analyze the log file for formatting consistency
        malformed_lines = []
        expected_format = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - .* - process_\d+_thread_\d+ - \[.*\] - P\d+-T\d+ message \d+'

        line_count = 0
        with open(self.log_file, 'r') as f:
            for i, line in enumerate(f, 1):
                line_count += 1
                if not re.match(expected_format, line.strip()):
                    malformed_lines.append((i, line.strip()))
                    if len(malformed_lines) > 10:  # Limit to first 10 errors
                        break

        # Check for log corruption under pressure
        self.assertEqual(len(malformed_lines), 0,
                        f"Found {len(malformed_lines)} malformed lines in log file")

    def test_process_thread_isolation(self):
        """Test that processes and threads maintain proper isolation."""
        def thread_isolation_worker(thread_id, isolation_data, thread_queue):
            logger = get_logger(f"isolation_thread_{thread_id}")

            # Set thread-specific data
            logger.thread_data = {
                "thread_value": f"thread_{thread_id}_data"
            }

            # Log with thread data
            logger.info(f"Thread {thread_id} with data: {logger.thread_data}")

            # Read the isolation data which might have been set by other threads
            thread_queue.put({
                "thread_id": thread_id,
                "my_data": logger.thread_data,
                "isolation_data": isolation_data.copy() if hasattr(isolation_data, 'copy') else isolation_data
            })

        def process_with_isolation_threads(process_id):
            # Data to be shared between threads in this process only
            isolation_data = {}
            # Queue for thread results within this process
            thread_queue = Queue()

            # Create a specific logger for this process
            logger = get_logger(f"isolation_process_{process_id}")
            logger.process_data = {
                "process_value": f"process_{process_id}_data"
            }

            # Log with process-specific data
            logger.info(f"Process {process_id} with data: {logger.process_data}")

            threads = []
            for t_id in range(3):  # 3 threads per process
                t = threading.Thread(
                    target=thread_isolation_worker,
                    args=(t_id, isolation_data, thread_queue)
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Collect thread results and send to main process
            thread_results = []
            while not thread_queue.empty():
                thread_results.append(thread_queue.get())

            # Send process and thread data back to main
            self.result_queue.put({
                "process_id": process_id,
                "process_data": getattr(logger, "process_data", None),
                "thread_results": thread_results
            })

        # Run 3 processes
        processes = []
        for p_id in range(3):
            p = multiprocessing.Process(
                target=process_with_isolation_threads,
                args=(p_id,)
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        # Collect and analyze results
        results = []
        while not self.result_queue.empty():
            results.append(self.result_queue.get())

        # Check for proper isolation between processes and threads
        for proc_result in results:
            pid = proc_result["process_id"]
            proc_data = proc_result["process_data"]

            # Verify process data is correct
            self.assertEqual(
                proc_data["process_value"],
                f"process_{pid}_data",
                f"Process {pid} has incorrect data"
            )

            # Check thread isolation within this process
            thread_results = proc_result["thread_results"]
            for thread_result in thread_results:
                tid = thread_result["thread_id"]
                thread_data = thread_result["my_data"]

                # Verify thread data is correct
                self.assertEqual(
                    thread_data["thread_value"],
                    f"thread_{tid}_data",
                    f"Thread {tid} in process {pid} has incorrect data"
                )

    def test_process_staggered_start_stop(self):
        """Test logging with processes that start and stop at different times."""
        def staggered_process(process_id, delay_start, work_time, iterations):
            # Delay before starting work
            time.sleep(delay_start)

            # Create a logger
            logger = get_logger(f"staggered_{process_id}")

            # Do work for the specified amount of time
            start_time = time.time()
            message_count = 0

            while time.time() - start_time < work_time:
                for i in range(iterations):
                    iteration = message_count + i
                    level = ["DEBUG", "INFO", "WARNING", "ERROR"][iteration % 4]

                    message = f"Staggered P{process_id} message {iteration}"

                    if level == "DEBUG":
                        logger.debug(message)
                    elif level == "INFO":
                        logger.info(message)
                    elif level == "WARNING":
                        logger.warning(message)
                    elif level == "ERROR":
                        logger.error(message)

                message_count += iterations
                time.sleep(0.01)  # Small pause

            # Report results
            self.result_queue.put({
                "process_id": process_id,
                "messages_sent": message_count
            })

        # Create processes with staggered start/stop times
        # Format: (process_id, start_delay, work_time, iterations_per_batch)
        process_configs = [
            (0, 0.0, 0.2, 5),     # Starts immediately, runs briefly
            (1, 0.1, 0.3, 10),    # Slight delay start, runs longer
            (2, 0.0, 0.4, 15),    # Starts immediately, runs longest
            (3, 0.2, 0.1, 20),    # Starts late, finishes quickly
        ]

        processes = []
        for pid, delay, work_time, iters in process_configs:
            p = multiprocessing.Process(
                target=staggered_process,
                args=(pid, delay, work_time, iters)
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        # Allow time for logs to be written
        time.sleep(0.5)

        # Check the log file format integrity
        with open(self.log_file, 'r') as f:
            lines = f.readlines()

        # Instead of checking for strict timestamp order, which can fail due to millisecond-level
        # timing differences between processes, check for these more important properties:

        # 1. Verify all log entries have valid timestamps
        invalid_format = []
        for i, line in enumerate(lines):
            if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} -', line):
                invalid_format.append((i, line))

        self.assertEqual(len(invalid_format), 0,
                         f"Found {len(invalid_format)} log entries with invalid timestamp format")

        # 2. Check that timestamps are within a reasonable range
        # Extract timestamps with line contents
        timestamped_entries = []
        for line in lines:
            match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (.*)', line)
            if match:
                timestamp, content = match.groups()
                timestamped_entries.append((timestamp, content))

        # Convert to datetime objects
        from datetime import datetime
        datetime_entries = [(datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f"), content)
                            for ts, content in timestamped_entries]

        # Check time span - first to last
        if datetime_entries:
            first_dt = min(dt for dt, _ in datetime_entries)
            last_dt = max(dt for dt, _ in datetime_entries)
            time_span = (last_dt - first_dt).total_seconds()

            # Time span should be reasonable based on the test durations
            self.assertGreaterEqual(time_span, 0.1,  # At least some minimal span
                                   "Log timespan too short")
            self.assertLessEqual(time_span, 2.0,     # Not unreasonably long
                                "Log timespan too long")

        # 3. Check for severe timestamp anomalies (more than 100ms out of order)
        # Minor out-of-order timestamps (few ms) are expected and acceptable
        anomalies = []
        sorted_entries = sorted(datetime_entries, key=lambda x: x[0])

        for i, ((ts, content), (next_ts, next_content)) in enumerate(zip(sorted_entries[:-1], sorted_entries[1:])):
            # If an entry is found in the file significantly after one with a later timestamp
            original_indices = [j for j, (dts, cnt) in enumerate(datetime_entries) if dts == ts and cnt == content]
            next_original_indices = [j for j, (dts, cnt) in enumerate(datetime_entries) if dts == next_ts and cnt == next_content]

            if original_indices and next_original_indices:
                o_idx, no_idx = original_indices[0], next_original_indices[0]
                if o_idx > no_idx + 10:  # Allow small inversions (10 lines) but catch major ones
                    anomalies.append((o_idx, no_idx, ts, next_ts))
                    if len(anomalies) >= 5:  # Limit reporting to 5 anomalies
                        break

        self.assertEqual(len(anomalies), 0,
                        f"Found {len(anomalies)} severe timestamp order anomalies")


if __name__ == '__main__':
    unittest.main()