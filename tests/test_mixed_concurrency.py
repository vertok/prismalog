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

import multiprocessing
import os
import re
import threading
import time
from queue import Queue
from typing import List

import pytest

from prismalog.log import get_logger


@pytest.mark.concurrency
class TestMixedConcurrency:
    """Test class for mixed multiprocessing and multithreading validation."""

    def thread_worker(
        self, thread_id: int, process_id: int, thread_results: Queue, iterations: int = 20, levels: List[str] = None
    ):
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
        results = {"process_id": process_id, "thread_id": thread_id, "messages_sent": 0, "errors": 0}

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

    def process_with_threads(self, process_id: int, num_threads: int, iterations: int, result_queue):
        """
        Worker process that spawns multiple threads.

        Args:
            process_id: Unique identifier for this process
            num_threads: Number of threads to spawn within this process
            iterations: Number of log messages per thread
            result_queue: Queue to collect results from threads
        """
        # This is a per-process queue for thread results
        thread_results = Queue()

        # Create and start threads
        threads = []
        for thread_id in range(num_threads):
            t = threading.Thread(target=self.thread_worker, args=(thread_id, process_id, thread_results, iterations))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Collect results from all threads
        process_results = {"process_id": process_id, "thread_count": num_threads, "thread_results": []}

        while not thread_results.empty():
            process_results["thread_results"].append(thread_results.get())

        # Send aggregated results back to the main process
        result_queue.put(process_results)

    def test_basic_mixed_concurrency(self, mixed_concurrency_env):
        """Test logging with a simple configuration of processes and threads."""
        num_processes = 3
        threads_per_process = 4
        iterations = 10

        processes = []

        # Create and start processes
        for pid in range(num_processes):
            p = multiprocessing.Process(
                target=self.process_with_threads,
                args=(pid, threads_per_process, iterations, mixed_concurrency_env["result_queue"]),
            )
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join()

        # Collect results
        results = []
        while not mixed_concurrency_env["result_queue"].empty():
            results.append(mixed_concurrency_env["result_queue"].get())

        # Verify all processes reported
        assert len(results) == num_processes, "Not all processes reported results"

        # Check thread results
        expected_thread_count = num_processes * threads_per_process
        actual_thread_count = sum(len(p["thread_results"]) for p in results)

        assert (
            actual_thread_count == expected_thread_count
        ), f"Expected {expected_thread_count} thread results, got {actual_thread_count}"

        # Check message counts
        expected_messages = num_processes * threads_per_process * iterations
        actual_messages = sum(sum(t["messages_sent"] for t in p["thread_results"]) for p in results)

        assert actual_messages == expected_messages, f"Expected {expected_messages} messages, got {actual_messages}"

        # Check errors
        total_errors = sum(sum(t.get("errors", 0) for t in p["thread_results"]) for p in results)
        assert total_errors == 0, f"Found {total_errors} errors during logging"

        # Allow time for log writing
        time.sleep(0.5)

        # Verify log file exists
        assert os.path.exists(mixed_concurrency_env["log_file"]), "Log file was not created"

        # Analyze log file content
        pattern = r"P(\d+)-T(\d+) message (\d+)"
        message_occurrences = {}

        with open(mixed_concurrency_env["log_file"], "r") as f:
            for line in f:
                matches = re.findall(pattern, line)
                for match in matches:
                    if match:
                        key = f"{match[0]}_{match[1]}_{match[2]}"  # process_thread_message
                        message_occurrences[key] = message_occurrences.get(key, 0) + 1

        # Check for duplicates
        duplicates = [key for key, count in message_occurrences.items() if count > 1]
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate log entries"

    # Update other test methods similarly
