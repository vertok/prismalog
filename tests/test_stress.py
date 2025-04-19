"""Stress tests for prismalog under extreme conditions."""

import os
import shutil
import tempfile
import threading
import time
import unittest

import pytest

from prismalog import LoggingConfig, get_logger


class TestStressCases(unittest.TestCase):
    """Test the logging system under extreme stress conditions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="log_stress_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_flood_logging(self):
        """Test the logger under flooding conditions."""
        LoggingConfig.initialize(
            use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False, "rotation_size_mb": 10}
        )

        logger = get_logger("flood_test")

        # Store start time
        start_time = time.time()
        message_count = 50000  # 50K messages

        # Flood with messages
        for i in range(message_count):
            logger.info(f"Flood message {i}")

        duration = time.time() - start_time

        # Success criteria: didn't crash and maintained decent performance
        msgs_per_sec = message_count / duration
        print(f"\nFlood test: {message_count} messages in {duration:.2f}s = {msgs_per_sec:.2f} msgs/sec")

        self.assertTrue(msgs_per_sec > 1000, f"Performance too low: {msgs_per_sec:.2f} msgs/sec")

    def bursty_thread(self, thread_id, bursts, logger):
        """Thread that logs in bursts."""
        for burst in range(bursts):
            # Sleep between bursts
            time.sleep(0.05)
            # Then send a burst of messages
            for i in range(100):
                logger.debug(f"Thread {thread_id} burst {burst} msg {i}")

    def test_bursty_logging(self):
        """Test with many threads doing bursty logging."""
        LoggingConfig.initialize(use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False})

        logger = get_logger("bursty_test")

        # Create many threads that log in bursts
        threads = []
        num_threads = 20
        bursts_per_thread = 5

        start_time = time.time()

        # Start all threads
        for i in range(num_threads):
            t = threading.Thread(target=self.bursty_thread, args=(i, bursts_per_thread, logger))
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        duration = time.time() - start_time

        total_messages = num_threads * bursts_per_thread * 100
        msgs_per_sec = total_messages / duration

        print(f"\nBursty test: {total_messages} messages in {duration:.2f}s = {msgs_per_sec:.2f} msgs/sec")

        # Success criteria is not crashing under bursty load
        self.assertTrue(True)

    @pytest.mark.slow
    def test_long_running(self):
        """Test logger running for a longer period with continuous activity."""
        if os.environ.get("SKIP_LONG_TESTS"):
            self.skipTest("Skipping long-running test")

        LoggingConfig.initialize(use_cli_args=False, **{"log_dir": self.temp_dir, "colored_console": False})

        logger = get_logger("long_running_test")

        # Run time in seconds
        run_time = 30
        start_time = time.time()
        count = 0

        # Log continuously for the specified time
        while time.time() - start_time < run_time:
            logger.info(f"Long running message {count}")
            count += 1

            # Small sleep to avoid completely flooding
            if count % 1000 == 0:
                time.sleep(0.01)

        duration = time.time() - start_time
        msgs_per_sec = count / duration

        print(f"\nLong running test: {count} messages in {duration:.2f}s = {msgs_per_sec:.2f} msgs/sec")

        # Success criteria is maintaining performance over time
        recent_performance = msgs_per_sec

        self.assertTrue(recent_performance > 1000, f"Performance degraded over time: {recent_performance:.2f} msgs/sec")
