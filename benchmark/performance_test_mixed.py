"""
Performance benchmark for the prismalog package using mixed concurrency.

This script measures performance when using both multiprocessing and multithreading
simultaneously, which is a common pattern in real-world applications. It measures:
- Throughput (messages per second)
- Per-message timing for different log levels
- Memory consumption
- Process and thread coordination overhead
- Memory cleanup after logging operations

It runs multiple processes, each with multiple threads, that log messages concurrently.
"""

import os
import gc
import time
import threading
import statistics
import multiprocessing
from queue import Queue
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


def thread_worker(thread_id, process_id, thread_results, num_messages, batch_size=100):
    """
    Worker thread that runs within a process and logs messages.

    Args:
        thread_id (int): Unique identifier for this thread within the process
        process_id (int): Identifier for the parent process
        thread_results (Queue): Queue to collect results from this thread
        num_messages (int): Number of messages to log per level
        batch_size (int): Number of messages to batch for timing measurements
    """
    # Create a thread-specific logger
    logger = get_logger(f"process_{process_id}_thread_{thread_id}", verbose="DEBUG")

    # Warm up
    for _ in range(3):
        logger.debug(f"Warm-up message from P{process_id}-T{thread_id}")

    # Track timing metrics
    timings = {
        'debug': [],
        'info': [],
        'warning': [],
        'error': []
    }

    # Track total duration
    worker_start_time = time.time()

    # Log debug messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.debug(f"Debug message {i} from P{process_id}-T{thread_id}")
        end = time.time()

        batch_time = end - start
        timings['debug'].append(batch_time / batch_size_actual)

    # Log info messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.info(f"Info message {i} from P{process_id}-T{thread_id}")
        end = time.time()

        batch_time = end - start
        timings['info'].append(batch_time / batch_size_actual)

    # Log warning messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.warning(f"Warning message {i} from P{process_id}-T{thread_id}")
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
            logger.error(f"Error message {i} from P{process_id}-T{thread_id}")
        end = time.time()

        batch_time = end - start
        timings['error'].append(batch_time / batch_size_actual)

    # Calculate overall metrics
    worker_duration = time.time() - worker_start_time

    # Send results back to the process
    thread_results.put({
        'thread_id': thread_id,
        'process_id': process_id,
        'duration': worker_duration,
        'message_count': num_messages * 3 + error_count,  # debug + info + warning + error
        'timings': timings
    })


def process_with_threads(process_id, num_threads, num_messages, result_queue, batch_size=100):
    """
    Worker process that spawns multiple threads.

    Args:
        process_id (int): Unique identifier for this process
        num_threads (int): Number of threads to spawn
        num_messages (int): Number of messages per thread per level
        result_queue (multiprocessing.Queue): Queue to report results back to main process
        batch_size (int): Batch size for timing measurements
    """
    # Track memory usage for this process
    start_memory = get_memory_usage()
    process_start_time = time.time()

    # Create a queue for threads to report results
    thread_results = Queue()

    # Create and start threads
    threads = []
    for thread_id in range(num_threads):
        t = threading.Thread(
            target=thread_worker,
            args=(thread_id, process_id, thread_results, num_messages, batch_size)
        )
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Collect thread results
    thread_data = []
    while not thread_results.empty():
        thread_data.append(thread_results.get())

    # Calculate process-level metrics
    process_duration = time.time() - process_start_time
    end_memory = get_memory_usage()

    # Aggregate thread-level timing data
    process_timings = {
        'debug': [],
        'info': [],
        'warning': [],
        'error': []
    }

    total_messages = 0
    for t_result in thread_data:
        total_messages += t_result['message_count']
        for level, timings in t_result['timings'].items():
            process_timings[level].extend(timings)

    # Send aggregated results back to the main process
    result_queue.put({
        'process_id': process_id,
        'thread_count': num_threads,
        'thread_results': thread_data,
        'duration': process_duration,
        'message_count': total_messages,
        'timings': process_timings,
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
    Main function to run the mixed concurrency performance test.

    This function:
    1. Starts multiple processes, each running multiple threads
    2. Collects performance metrics from all processes and threads
    3. Calculates aggregate statistics
    4. Tests memory cleanup by resetting the logger
    5. Outputs a comprehensive performance report

    Run this function to benchmark the prismalog package's performance
    in a mixed multiprocessing and multithreading environment.
    """
    # Configuration - generate approximately the same number of
    # total messages as the other tests for fair comparison
    NUM_PROCESSES = 3            # pylint: disable=invalid-name
    THREADS_PER_PROCESS = 2      # pylint: disable=invalid-name
    MESSAGES_PER_THREAD = 10000  # pylint: disable=invalid-name
    BATCH_SIZE = 100             # pylint: disable=invalid-name

    print(f"\n{'='*60}")
    print(f"MIXED CONCURRENCY LOGGER PERFORMANCE TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"• Processes: {NUM_PROCESSES}")
    print(f"• Threads per process: {THREADS_PER_PROCESS}")
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

    print("\nStarting worker processes with threads...")
    processes = []
    result_queue = multiprocessing.Queue()

    # Start the processes, each with multiple threads
    for pid in range(NUM_PROCESSES):
        p = multiprocessing.Process(
            target=process_with_threads,
            args=(pid, THREADS_PER_PROCESS, MESSAGES_PER_THREAD, result_queue, BATCH_SIZE)
        )
        processes.append(p)
        p.start()
        print(f"• Started process {pid+1}/{NUM_PROCESSES} (PID: {p.pid}) with {THREADS_PER_PROCESS} threads")

    # Wait for all processes to complete
    print("\nWaiting for processes and threads to complete...")
    for p in processes:
        p.join()

    # Collect process results
    process_results = [result_queue.get() for _ in range(NUM_PROCESSES)]

    # Calculate aggregate statistics
    total_duration = time.time() - test_start
    total_messages = sum(p['message_count'] for p in process_results)

    # Aggregate timing data from all processes and threads
    all_timings = {
        'debug': [],
        'info': [],
        'warning': [],
        'error': []
    }

    for p_result in process_results:
        for level, timings in p_result['timings'].items():
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
