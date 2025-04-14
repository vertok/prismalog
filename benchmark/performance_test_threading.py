"""
Performance benchmark for the prismalog package using threads.

This script measures various performance aspects of the prismalog package
when used in a multithreaded environment:
- Throughput (messages per second)
- Per-message timing for different log levels
- Memory consumption
- Multithreading behavior
- Memory cleanup after logging operations

It runs multiple threads that log messages concurrently and collects
detailed statistics about performance characteristics.
"""

import os
import gc
import time
import psutil
import threading
import statistics
from queue import Queue
from datetime import datetime
from prismalog.log import ColoredLogger, get_logger

# Disable rotation for performance tests to avoid timing variations
os.environ['LOG_DISABLE_ROTATION'] = '1'

def get_memory_usage():
    """
    Get current memory usage of the process.

    Returns:
        float: Current memory usage in megabytes.
    """
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def measure_time(func):
    """
    Decorator to measure function execution time.

    Args:
        func (callable): The function to measure.

    Returns:
        callable: A wrapper function that returns the original result and elapsed time.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time
        return result, elapsed
    return wrapper


def worker_thread(thread_id, num_messages, result_queue, batch_size=100):
    """
    Worker thread that generates log messages and reports detailed metrics.

    This function creates a logger, logs a specified number of messages at
    different levels, and measures performance metrics which are then sent
    back to the main thread.

    Args:
        thread_id (int): Unique identifier for this thread
        num_messages (int): Number of messages to log per level
        result_queue (Queue): Queue to send results back to main thread
        batch_size (int, optional): Measure time per this many messages. Defaults to 100.
    """
    # Prepare worker thread
    logger = get_logger(f"perf_thread_{thread_id}", verbose="DEBUG")

    # Warm up the logger
    for _ in range(5):
        logger.debug("Warm-up message")

    # Track timing metrics
    timings = {
        'debug': [],
        'info': [],
        'warning': [],
        'error': []
    }

    # Track memory usage (note: this is process-wide, not thread-specific)
    start_memory = get_memory_usage()

    # Track total duration
    worker_start_time = time.time()

    # Log debug messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.debug(f"Debug message {i} from thread {thread_id}")
        end = time.time()

        batch_time = end - start
        timings['debug'].append(batch_time / batch_size_actual)

    # Log info messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.info(f"Info message {i} from thread {thread_id}")
        end = time.time()

        batch_time = end - start
        timings['info'].append(batch_time / batch_size_actual)

    # Log warning messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.warning(f"Warning message {i} from thread {thread_id}")
        end = time.time()

        batch_time = end - start
        timings['warning'].append(batch_time / batch_size_actual)

    # Log error messages (fewer to avoid cluttering logs)
    error_count = max(10, num_messages // 10)
    for batch_start in range(0, error_count, batch_size):
        batch_end = min(batch_start + batch_size, error_count)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.error(f"Error message {i} from thread {thread_id}")
        end = time.time()

        batch_time = end - start
        timings['error'].append(batch_time / batch_size_actual)

    # Calculate overall metrics
    worker_duration = time.time() - worker_start_time
    end_memory = get_memory_usage()

    # Send results back to main thread
    result_queue.put({
        'thread_id': thread_id,
        'duration': worker_duration,
        'message_count': num_messages * 3 + error_count,  # debug + info + warning + error
        'timings': timings,
        'memory_delta': end_memory - start_memory
    })


def format_statistics(values):
    """
    Format statistical values for display.

    Calculates mean, median, and standard deviation of the provided
    values and formats them for human-readable output.

    Args:
        values (list): List of numeric values to analyze

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


def main():
    """
    Main function to run the multithreaded performance test.

    This function:
    1. Starts multiple worker threads that log messages
    2. Collects performance metrics from all threads
    3. Calculates aggregate statistics
    4. Tests memory cleanup by resetting the logger
    5. Outputs a comprehensive performance report

    Run this function to benchmark the prismalog package's performance in a threaded environment.
    """
    # Configuration - use the same parameters as the multiprocessing test
    NUM_THREADS = 4
    MESSAGES_PER_THREAD = 1000
    BATCH_SIZE = 100

    # Prepare benchmark directory and results file
    benchmark_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", ".benchmarks")
    os.makedirs(benchmark_dir, exist_ok=True)

    # Create timestamped results file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(benchmark_dir, f"threading_benchmark_{timestamp}.json")

    print(f"\n{'='*60}")
    print(f"THREADED LOGGER PERFORMANCE TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"• Threads: {NUM_THREADS}")
    print(f"• Messages per level per thread: {MESSAGES_PER_THREAD}")
    print(f"• Batch size for timing: {BATCH_SIZE}")
    print(f"{'='*60}\n")

    # Clean up before starting
    gc.collect()
    initial_memory = get_memory_usage()
    print(f"Initial memory usage: {initial_memory:.2f} MB")

    # Create a unique log file for this test
    test_start = time.time()
    ColoredLogger.reset(new_file=True)
    log_file = ColoredLogger._log_file_path
    print(f"Log file: {log_file}")

    initial_log_files = len([f for f in os.listdir(os.path.dirname(log_file))
                           if f.startswith(os.path.basename(log_file).split('.')[0])])

    print("\nStarting worker threads...")
    threads = []
    result_queue = Queue()

    # Start worker threads
    for i in range(NUM_THREADS):
        t = threading.Thread(
            target=worker_thread,
            args=(i, MESSAGES_PER_THREAD, result_queue, BATCH_SIZE)
        )
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
    total_messages = sum(r['message_count'] for r in results)

    # Aggregate timing data
    all_timings = {
        'debug': [],
        'info': [],
        'warning': [],
        'error': []
    }

    for r in results:
        for level, timings in r['timings'].items():
            all_timings[level].extend(timings)

    # Measure log file size
    try:
        log_size = os.path.getsize(log_file) / (1024 * 1024)  # MB
    except:
        log_size = 0

    # Final memory usage
    gc.collect()
    final_memory = get_memory_usage()

    final_log_files = len([f for f in os.listdir(os.path.dirname(log_file))
                         if f.startswith(os.path.basename(log_file).split('.')[0])])
    print(f"• Log files created: {final_log_files - initial_log_files}")

    # Print results
    print(f"\n{'='*60}")
    print(f"PERFORMANCE RESULTS")
    print(f"{'='*60}")

    print(f"\nThroughput:")
    print(f"• Total log messages: {total_messages}")
    print(f"• Total execution time: {total_duration:.2f} seconds")
    print(f"• Messages per second: {total_messages/total_duration:.2f}")

    print(f"\nTiming by log level (per message):")
    print(f"• DEBUG:   {format_statistics(all_timings['debug'])}")
    print(f"• INFO:    {format_statistics(all_timings['info'])}")
    print(f"• WARNING: {format_statistics(all_timings['warning'])}")
    print(f"• ERROR:   {format_statistics(all_timings['error'])}")

    print(f"\nMemory usage:")
    print(f"• Initial: {initial_memory:.2f} MB")
    print(f"• Final: {final_memory:.2f} MB")
    print(f"• Delta: {final_memory - initial_memory:.2f} MB")

    print(f"\nLog file:")
    print(f"• Path: {log_file}")
    print(f"• Size: {log_size:.2f} MB")

    # Memory cleanup test
    print(f"\n{'='*60}")
    print(f"MEMORY CLEANUP TEST")
    print(f"{'='*60}")

    before_reset = get_memory_usage()
    print(f"• Memory before reset: {before_reset:.2f} MB")

    ColoredLogger.reset(new_file=False)
    gc.collect()

    after_reset = get_memory_usage()
    print(f"• Memory after reset: {after_reset:.2f} MB")
    print(f"• Change: {after_reset - before_reset:.2f} MB")
    print(f"• Memory compared to start: {after_reset - initial_memory:.2f} MB")

    print(f"\n{'='*60}")
    print(f"TEST COMPLETED SUCCESSFULLY")
    print(f"{'='*60}\n")

    # Save structured results to the benchmark directory
    import json
    benchmark_results = {
        "date": datetime.now().isoformat(),
        "config": {
            "threads": NUM_THREADS,
            "messages_per_thread": MESSAGES_PER_THREAD,
            "batch_size": BATCH_SIZE
        },
        "throughput": {
            "total_messages": total_messages,
            "total_duration": total_duration,
            "messages_per_second": total_messages/total_duration
        },
        "timing": {
            "debug": {
                "mean": statistics.mean(all_timings['debug']) * 1000,
                "median": statistics.median(all_timings['debug']) * 1000,
                "stdev": statistics.stdev(all_timings['debug']) * 1000 if len(all_timings['debug']) > 1 else 0
            },
            # Similar entries for other log levels
        },
        "memory": {
            "initial": initial_memory,
            "final": final_memory,
            "delta": final_memory - initial_memory
        },
        "log_file": {
            "size_mb": log_size
        }
    }

    with open(results_file, 'w') as f:
        json.dump(benchmark_results, f, indent=2)

    print(f"Benchmark results saved to: {results_file}")


if __name__ == "__main__":
    main()
