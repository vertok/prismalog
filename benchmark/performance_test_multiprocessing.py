"""
Performance benchmark for the prismalog package.

This script measures various performance aspects of the prismalog package:
- Throughput (messages per second)
- Per-message timing for different log levels
- Memory consumption
- Multi-process behavior
- Memory cleanup after logging operations

It runs multiple processes that log messages concurrently and collects
detailed statistics about performance characteristics.
"""

import os
import gc
import time
import statistics
import multiprocessing
from datetime import datetime
import psutil
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


def worker_process(num_messages, result_queue, batch_size=100):
    """
    Worker process that generates log messages and reports detailed metrics.

    This function is intended to run in a separate process. It creates a logger,
    logs a specified number of messages at different levels, and measures performance
    metrics which are then sent back to the main process.

    Args:
        num_messages (int): Number of messages to log per level
        result_queue (multiprocessing.Queue): Queue to send results back to main process
        batch_size (int, optional): Measure time per this many messages. Defaults to 100.

    Returns:
        None: Results are sent via the result_queue
    """
    # Prepare worker process
    pid = os.getpid()
    logger = get_logger(f"perf_worker_{pid}", verbose="DEBUG")

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
            logger.debug(f"Debug message {i} from process {pid}")
        end = time.time()

        batch_time = end - start
        timings['debug'].append(batch_time / batch_size_actual)

    # Log info messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.info(f"Info message {i} from process {pid}")
        end = time.time()

        batch_time = end - start
        timings['info'].append(batch_time / batch_size_actual)

    # Log warning messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.warning(f"Warning message {i} from process {pid}")
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
            logger.error(f"Error message {i} from process {pid}")
        end = time.time()

        batch_time = end - start
        timings['error'].append(batch_time / batch_size_actual)

    # Calculate overall metrics
    worker_duration = time.time() - worker_start_time
    end_memory = get_memory_usage()

    # Send results back to main process
    result_queue.put({
        'pid': pid,
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
    Main function to run the performance test.

    This function:
    1. Starts multiple worker processes that log messages
    2. Collects performance metrics from all workers
    3. Calculates aggregate statistics
    4. Tests memory cleanup by resetting the logger
    5. Outputs a comprehensive performance report

    Run this function to benchmark the prismalog package's performance.
    """
    # Configuration
    NUM_PROCESSES = 2            # pylint: disable=invalid-name
    MESSAGES_PER_PROCESS = 1000  # pylint: disable=invalid-name
    BATCH_SIZE = 100             # pylint: disable=invalid-name

    print(f"\n{'='*60}")
    print(f"COLORED LOGGER PERFORMANCE TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"• Processes: {NUM_PROCESSES}")
    print(f"• Messages per level per process: {MESSAGES_PER_PROCESS}")
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

    print("\nStarting worker processes...")
    processes = []
    result_queue = multiprocessing.Queue()

    # Start worker processes
    for i in range(NUM_PROCESSES):
        p = multiprocessing.Process(
            target=worker_process,
            args=(MESSAGES_PER_PROCESS, result_queue, BATCH_SIZE)
        )
        processes.append(p)
        p.start()
        print(f"• Started worker {i+1}/{NUM_PROCESSES} (PID: {p.pid})")

    # Wait for all workers to finish
    print("\nWaiting for workers to complete...")
    for p in processes:
        p.join()

    # Collect and analyze results
    results = [result_queue.get() for _ in range(NUM_PROCESSES)]

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
    print("PERFORMANCE RESULTS")
    print(f"{'='*60}")

    print("\nThroughput:")
    print(f"• Total log messages: {total_messages}")
    print(f"• Total execution time: {total_duration:.2f} seconds")
    print(f"• Messages per second: {total_messages/total_duration:.2f}")

    print("nTiming by log level (per message):")
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

    ColoredLogger.reset(new_file=False)
    gc.collect()

    after_reset = get_memory_usage()
    print(f"• Memory after reset: {after_reset:.2f} MB")
    print(f"• Change: {after_reset - before_reset:.2f} MB")
    print(f"• Memory compared to start: {after_reset - initial_memory:.2f} MB")

    print(f"\n{'='*60}")
    print("TEST COMPLETED SUCCESSFULLY")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
