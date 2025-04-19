"""
Performance benchmark for standard Python logging package using threads.

This script measures various performance aspects of the standard Python logging
package when used in a multithreaded environment, allowing direct comparison
with the prismalog package performance:
- Throughput (messages per second)
- Per-message timing for different log levels
- Memory consumption
- Multithreading behavior
- Memory cleanup after logging operations
"""

import gc
import json
import logging
import os
import statistics
import threading
import time
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple

# Configuration
NUM_THREADS = 4
MESSAGES_PER_THREAD = 1200
BATCH_SIZE = 100

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Set up logging configuration
log_filename = os.path.join(LOG_DIR, f"benchmark_standart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_filename), logging.StreamHandler()],  # Also print to console
)


# Example benchmark logging
def log_benchmark_results() -> None:
    logging.info("Starting benchmark test")

    # Log your benchmark results here
    logging.info("Test results: ...")
    logging.info("Performance metrics: ...")

    logging.info("Benchmark test completed")


def get_memory_usage() -> float:
    """
    Get current memory usage of the process using standard Python.

    Returns:
        float: Current memory usage in megabytes.
    """
    import resource

    # Get maximum resident set size (in bytes on Linux)
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    # Convert to megabytes
    return rusage.ru_maxrss / 1024  # ru_maxrss is in KB on Linux


def setup_logging() -> Tuple[str, logging.Logger]:
    """
    Configure the standard Python logging system with both file and console output.

    Returns:
        tuple: (log_file_path, root_logger)
    """
    # Create benchmark directory
    benchmark_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", ".benchmarks")
    os.makedirs(benchmark_dir, exist_ok=True)

    # Create timestamped log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(benchmark_dir, f"standard_logging_benchmark_{timestamp}.log")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Create handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - [%(levelname)s] - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return log_file, root_logger


def worker_thread(thread_id: int, num_messages: int, result_queue: Queue, batch_size: int = 100) -> None:
    """
    Worker thread that generates log messages and reports detailed metrics.

    Args:
        thread_id: Unique identifier for this thread
        num_messages: Number of messages to log per level
        result_queue: Queue to send results back to main thread
        batch_size: Number of messages per timing batch
    """
    # Create logger for this thread
    logger = logging.getLogger(f"std_perf_thread_{thread_id}")
    logger.setLevel(logging.DEBUG)

    # Warm up the logger
    for _ in range(5):
        logger.debug("Warm-up message")

    # Track timing metrics
    timings: Dict[str, List[float]] = {"debug": [], "info": [], "warning": [], "error": []}

    # Track memory usage
    start_memory = get_memory_usage()

    # Track total duration
    worker_start_time = time.time()

    # Log debug messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.debug("Debug message %s from thread %d", i, thread_id)
        end = time.time()

        batch_time = end - start
        timings["debug"].append(batch_time / batch_size_actual)

    # Log info messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.info("Info message %d from thread %d", i, thread_id)
        end = time.time()

        batch_time = end - start
        timings["info"].append(batch_time / batch_size_actual)

    # Log warning messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.warning("Warning message %d from thread %d", i, thread_id)
        end = time.time()

        batch_time = end - start
        timings["warning"].append(batch_time / batch_size_actual)

    # Log error messages (fewer to avoid cluttering logs)
    error_count = max(10, num_messages // 10)
    for batch_start in range(0, error_count, batch_size):
        batch_end = min(batch_start + batch_size, error_count)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.error("Error message %d from thread %d", i, thread_id)
        end = time.time()

        batch_time = end - start
        timings["error"].append(batch_time / batch_size_actual)

    # Calculate overall metrics
    worker_duration = time.time() - worker_start_time
    end_memory = get_memory_usage()

    # Send results back to main thread
    result_queue.put(
        {
            "thread_id": thread_id,
            "duration": worker_duration,
            "message_count": num_messages * 3 + error_count,  # debug + info + warning + error
            "timings": timings,
            "memory_delta": end_memory - start_memory,
        }
    )


def format_statistics(values: List[float]) -> str:
    """
    Format statistical values for display.

    Args:
        values: List of numeric values to analyze

    Returns:
        str: Formatted string with statistics
    """
    if not values:
        return "N/A"

    mean = statistics.mean(values)
    median = statistics.median(values)

    try:
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        return f"mean={mean*1000:.2f}ms, median={median*1000:.2f}ms, stdev={stdev*1000:.2f}ms"
    except:
        return f"mean={mean*1000:.2f}ms, median={median*1000:.2f}ms"


def reset_logging() -> None:
    """
    Reset the logging system by removing all handlers.
    """
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Close all handlers to release file locks
    for handler in logging.getLogger().handlers[:]:
        if hasattr(handler, "close"):
            handler.close()


def main() -> None:
    """
    Main function to run the multithreaded performance test.
    """
    # Prepare benchmark directory and results file
    benchmark_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", ".benchmarks")
    os.makedirs(benchmark_dir, exist_ok=True)

    # Create timestamped results file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(benchmark_dir, f"std_logging_benchmark_{timestamp}.json")

    print(f"\n{'='*60}")
    print(f"STANDARD PYTHON LOGGING PERFORMANCE TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"• Threads: {NUM_THREADS}")
    print(f"• Messages per level per thread: {MESSAGES_PER_THREAD}")
    print(f"• Batch size for timing: {BATCH_SIZE}")
    print(f"{'='*60}\n")

    # Clean up before starting
    gc.collect()
    initial_memory = get_memory_usage()
    print(f"Initial memory usage: {initial_memory:.2f} MB")

    # Setup logging with timestamped file
    test_start = time.time()
    log_file, root_logger = setup_logging()
    print(f"Log file: {log_file}")

    print("\nStarting worker threads...")
    threads = []
    result_queue: Queue = Queue()

    # Start worker threads
    for i in range(NUM_THREADS):
        t = threading.Thread(target=worker_thread, args=(i, MESSAGES_PER_THREAD, result_queue, BATCH_SIZE))
        threads.append(t)
        t.start()
        print(f"• Started worker {i+1}/{NUM_THREADS} (Thread ID: {t.ident})")

    # Wait for all threads to finish
    print("\nWaiting for threads to complete...")
    for t in threads:
        t.join()

    # Collect and analyze results
    results = [result_queue.get() for _ in range(NUM_THREADS)]

    # Calculate aggregate statistics
    total_duration = time.time() - test_start
    total_messages = sum(r["message_count"] for r in results)

    # Aggregate timing data
    all_timings: Dict[str, List[float]] = {"debug": [], "info": [], "warning": [], "error": []}

    for r in results:
        for level, timings in r["timings"].items():
            all_timings[level].extend(timings)

    # Measure log file size
    try:
        log_size = os.path.getsize(log_file) / (1024 * 1024)  # MB
    except:
        log_size = 0

    # Final memory usage
    gc.collect()
    final_memory = get_memory_usage()

    # Print results
    print(f"\n{'='*60}")
    print("PERFORMANCE RESULTS")
    print("{'='*60}")

    print("\nThroughput:")
    print(f"• Total log messages: {total_messages}")
    print(f"• Total execution time: {total_duration:.2f} seconds")
    print(f"• Messages per second: {total_messages/total_duration:.2f}")

    print("\nTiming by log level (per message):")
    print(f"• DEBUG:   {format_statistics(all_timings['debug'])}")
    print(f"• INFO:    {format_statistics(all_timings['info'])}")
    print(f"• WARNING: {format_statistics(all_timings['warning'])}")
    print(f"• ERROR:   {format_statistics(all_timings['error'])}")

    print("\nMemory usage:")
    print(f"• Initial: {initial_memory:.2f} MB")
    print(f"• Final: {final_memory:.2f} MB")
    print(f"• Delta: {final_memory - initial_memory:.2f} MB")

    print("\nLog file:")
    print(f"• Path: {log_file}")
    print(f"• Size: {log_size:.2f} MB")

    # Memory cleanup test
    print(f"\n{'='*60}")
    print("MEMORY CLEANUP TEST")
    print(f"{'='*60}")

    before_reset = get_memory_usage()
    print(f"• Memory before reset: {before_reset:.2f} MB")

    reset_logging()
    gc.collect()

    after_reset = get_memory_usage()
    print(f"• Memory after reset: {after_reset:.2f} MB")
    print(f"• Change: {after_reset - before_reset:.2f} MB")
    print(f"• Memory compared to start: {after_reset - initial_memory:.2f} MB")

    print(f"\n{'='*60}")
    print("TEST COMPLETED SUCCESSFULLY")
    print(f"{'='*60}\n")

    # Save structured results to the benchmark directory
    benchmark_results = {
        "date": datetime.now().isoformat(),
        "config": {"threads": NUM_THREADS, "messages_per_thread": MESSAGES_PER_THREAD, "batch_size": BATCH_SIZE},
        "throughput": {
            "total_messages": total_messages,
            "total_duration": total_duration,
            "messages_per_second": total_messages / total_duration,
        },
        "timing": {
            "debug": {
                "mean": statistics.mean(all_timings["debug"]) * 1000,
                "median": statistics.median(all_timings["debug"]) * 1000,
                "stdev": statistics.stdev(all_timings["debug"]) * 1000 if len(all_timings["debug"]) > 1 else 0,
            },
            "info": {
                "mean": statistics.mean(all_timings["info"]) * 1000,
                "median": statistics.median(all_timings["info"]) * 1000,
                "stdev": statistics.stdev(all_timings["info"]) * 1000 if len(all_timings["info"]) > 1 else 0,
            },
            "warning": {
                "mean": statistics.mean(all_timings["warning"]) * 1000,
                "median": statistics.median(all_timings["warning"]) * 1000,
                "stdev": statistics.stdev(all_timings["warning"]) * 1000 if len(all_timings["warning"]) > 1 else 0,
            },
            "error": {
                "mean": statistics.mean(all_timings["error"]) * 1000,
                "median": statistics.median(all_timings["error"]) * 1000,
                "stdev": statistics.stdev(all_timings["error"]) * 1000 if len(all_timings["error"]) > 1 else 0,
            },
        },
        "memory": {"initial": initial_memory, "final": final_memory, "delta": final_memory - initial_memory},
        "log_file": {"size_mb": log_size},
    }

    with open(results_file, mode="w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    print(f"Benchmark results saved to: {results_file}")


if __name__ == "__main__":
    main()
    log_benchmark_results()
