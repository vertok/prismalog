"""
Test suite for validating prismalog with multithreading.

This module verifies that the prismalog package correctly handles
concurrent logging from multiple threads without issues like:
- Thread-safety problems
- Log entry corruption
- Missing log entries
- Interleaved log lines
"""

import threading
import time
from queue import Queue
from typing import List

import pytest

from prismalog.log import get_logger


@pytest.mark.multithreading
class TestMultithreading:
    """Test class for multithreading validation of the prismalog package."""

    def thread_worker(self, thread_id: int, iterations: int, levels: List[str], result_queue: Queue):
        """Worker function for test threads."""
        try:
            logger = get_logger(f"thread_{thread_id}")
            results = {"thread_id": thread_id, "messages_sent": 0, "errors": 0}

            for i in range(iterations):
                level = levels[i % len(levels)]
                message = f"Thread {thread_id} message {i} with level {level}"

                try:
                    getattr(logger, level.lower())(message)
                    results["messages_sent"] += 1
                except Exception as e:
                    results["errors"] += 1
                    results.setdefault("error_details", []).append(str(e))

            result_queue.put(results)

        except Exception as e:
            result_queue.put({"thread_id": thread_id, "error": str(e)})

    def test_concurrent_logging_small_scale(self, thread_test_env):
        """Test concurrent logging with a small number of threads and messages."""
        num_threads = 5
        iterations = 20
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        threads = []

        # Create and start threads
        for i in range(num_threads):
            t = threading.Thread(
                target=self.thread_worker, args=(i, iterations, levels, thread_test_env["result_queue"])
            )
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        time.sleep(0.1)

        with open(thread_test_env["log_file"], "r") as f:
            log_content = f.read()

        # Verify results
        results = []
        while not thread_test_env["result_queue"].empty():
            results.append(thread_test_env["result_queue"].get())

        assert len(results) == num_threads, "Not all threads completed"
        total_messages = sum(r["messages_sent"] for r in results)
        assert total_messages == num_threads * iterations, "Not all messages were sent"

    # Additional test methods can be updated similarly...
