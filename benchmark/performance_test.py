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

import gc
import multiprocessing
import os
import statistics
import threading
import time
from datetime import datetime
from multiprocessing.synchronize import Barrier as BarrierType
from pathlib import Path
from queue import Queue
from typing import Dict, List

from prismalog.argparser import get_argument_parser
from prismalog.config import LoggingConfig
from prismalog.log import ColoredLogger, get_logger

# Configuration
TARGET_LOG_MESSAGES = 12000  # Define the target total messages
BATCH_SIZE = 100  # pylint: disable=invalid-name


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


def thread_worker(
    thread_id: int,
    process_id: int,
    thread_results: Queue,
    num_messages: int,
    sync_barrier: BarrierType,
    batch_size: int = 100,
) -> None:
    """
    Worker thread that runs within a process and logs messages.

    Args:
        thread_id: Unique identifier for this thread within the process
        process_id: Identifier for the parent process
        thread_results: Queue to collect results from this thread
        num_messages: Number of messages to log per level
        sync_barrier: Synchronization barrier for thread coordination
        batch_size: Number of messages to batch for timing measurements
    """
    # Create a thread-specific logger
    logger = get_logger(f"process_{process_id}_thread_{thread_id}", verbose="DEBUG")

    # All threads will block here until total_workers threads have called wait()
    sync_barrier.wait()

    # Track timing metrics
    timings: Dict[str, List[float]] = {"debug": [], "info": [], "warning": [], "error": []}

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
        timings["debug"].append(batch_time / batch_size_actual)

    # Log info messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.info(f"Info message {i} from P{process_id}-T{thread_id}")
        end = time.time()

        batch_time = end - start
        timings["info"].append(batch_time / batch_size_actual)

    # Log warning messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.warning(f"Warning message {i} from P{process_id}-T{thread_id}")
        end = time.time()

        batch_time = end - start
        timings["warning"].append(batch_time / batch_size_actual)

    # Log error messages
    for batch_start in range(0, num_messages, batch_size):
        batch_end = min(batch_start + batch_size, num_messages)
        batch_size_actual = batch_end - batch_start

        start = time.time()
        for i in range(batch_start, batch_end):
            logger.error(f"Error message {i} from P{process_id}-T{thread_id}")
        end = time.time()

        batch_time = end - start
        timings["error"].append(batch_time / batch_size_actual)

    # Calculate overall metrics
    worker_duration = time.time() - worker_start_time

    # Send results back to the process
    thread_results.put(
        {
            "thread_id": thread_id,
            "process_id": process_id,
            "duration": worker_duration,
            "message_count": num_messages * 4,  # debug + info + warning + error
            "timings": timings,
        }
    )


def process_with_threads(
    process_id: int,
    num_threads: int,
    num_messages: int,
    result_queue: multiprocessing.Queue,
    sync_barrier: BarrierType,
    batch_size: int = 100,
) -> None:
    """
    Worker process that spawns multiple threads.

    Args:
        process_id: Unique identifier for this process
        num_threads: Number of threads to spawn
        num_messages: Number of messages per thread per level
        result_queue: Queue to report results back to main process
        sync_barrier: Synchronization barrier for thread coordination
        batch_size: Batch size for timing measurements
    """
    # Track memory usage for this process
    start_memory = get_memory_usage()
    process_start_time = time.time()

    # Create a queue for threads to report results
    thread_results: Queue = Queue()

    # Create and start threads
    threads = []
    for thread_id in range(num_threads):
        t = threading.Thread(
            target=thread_worker, args=(thread_id, process_id, thread_results, num_messages, sync_barrier, batch_size)
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
    process_timings: Dict[str, List[float]] = {"debug": [], "info": [], "warning": [], "error": []}

    total_messages = 0
    for t_result in thread_data:
        total_messages += t_result["message_count"]
        for level, timings in t_result["timings"].items():
            process_timings[level].extend(timings)

    # Send aggregated results back to the main process
    result_queue.put(
        {
            "process_id": process_id,
            "thread_count": num_threads,
            "thread_results": thread_data,
            "duration": process_duration,
            "message_count": total_messages,
            "timings": process_timings,
            "memory_delta": end_memory - start_memory,
        }
    )


def format_statistics(values: List[float]) -> str:
    """
    Format statistical values for display.

    Calculates mean, median, and standard deviation of the provided
    values and formats them for human-readable output.

    Args:
        values: List of numeric values to analyze

    Returns:
        Formatted string with statistics
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


def main() -> None:
    """
    Main function to run the mixed concurrency performance test.
    Uses prismalog.argparser for standard logging arguments.
    """
    # Get parser pre-populated with standard logging arguments
    parser = get_argument_parser(description="prismalog Concurrency Benchmark")

    # Add benchmark-specific arguments
    parser.add_argument(
        "-p",
        "--processes",
        type=int,
        default=2,
        dest="num_processes",
        help="Number of worker processes to spawn.",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=2,
        dest="threads_per_process",
        help="Number of worker threads per process.",
    )

    # Parse all arguments (logging + benchmark-specific)
    args = parser.parse_args()

    num_processes = args.num_processes
    threads_per_process = args.threads_per_process

    # Define benchmark-specific overrides that MUST apply
    config_overrides = {
        "disable_rotation": True,  # Ensure rotation is off for benchmark
    }

    # Determine config_file path from args if applicable, otherwise None
    config_file_path = getattr(args, "config_file", None)

    # Initialize using parsed args (use_cli_args=True handles extraction)
    # and apply benchmark overrides with highest priority
    LoggingConfig.initialize(config_file=config_file_path, use_cli_args=True, **config_overrides)

    # Calculations
    total_workers = num_processes * threads_per_process
    if total_workers == 0:
        raise ValueError("Number of processes and threads per process must be > 0")

    messages_per_level_float = TARGET_LOG_MESSAGES / (total_workers * 4)
    messages_per_thread = max(1, round(messages_per_level_float))

    synchronizer = multiprocessing.Barrier(total_workers)

    actual_total_messages = total_workers * messages_per_thread * 4

    # Determine Test Type
    if threads_per_process == 1 and num_processes > 1:
        test_type = "Multiprocessing"
    elif num_processes == 1 and threads_per_process > 1:
        test_type = "Multithreading"
    elif num_processes == 1 and threads_per_process == 1:
        test_type = "Single Process/Thread"  # Handle the 1x1 case
    else:
        test_type = "Mixed"

    print(f"\n{'='*60}")
    print(f"CONCURRENCY LOGGER PERFORMANCE TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"• Test Type: {test_type}")
    print(f"• Processes: {num_processes}")
    print(f"• Threads per process: {threads_per_process}")
    print(f"• Total Workers: {total_workers}")
    print(f"• Target Total Messages: ~{TARGET_LOG_MESSAGES}")
    print(f"• Calculated Messages per Thread (per level): {messages_per_thread}")
    print(f"• Calculated Actual Total Messages: {actual_total_messages}")
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

    if log_file is not None:
        try:
            initial_log_files = len(
                [f for f in os.listdir(Path(log_file).parent) if f.startswith(Path(log_file).name.split(".")[0])]
            )
        except:
            initial_log_files = 0
    else:
        initial_log_files = 0

    print("\nStarting worker processes with threads...")
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for pid in range(num_processes):
        p = multiprocessing.Process(
            target=process_with_threads,
            args=(
                pid,
                threads_per_process,
                messages_per_thread,
                result_queue,
                synchronizer,
                BATCH_SIZE,
            ),
        )
        processes.append(p)
        p.start()
        print(f"• Started process {pid+1}/{num_processes} (PID: {p.pid}) with {threads_per_process} threads")

    print("\nWaiting for processes and threads to complete...")
    for p in processes:
        p.join()

    process_results = [result_queue.get() for _ in range(num_processes)]

    total_duration = time.time() - test_start
    total_messages = sum(p["message_count"] for p in process_results)

    all_timings: Dict[str, List[float]] = {"debug": [], "info": [], "warning": [], "error": []}

    for p_result in process_results:
        for level, timings in p_result["timings"].items():
            all_timings[level].extend(timings)

    if log_file is not None:
        try:
            log_size = os.path.getsize(log_file) / (1024 * 1024)  # MB
        except:
            log_size = 0
    else:
        log_size = 0

    gc.collect()
    final_memory = get_memory_usage()

    if log_file is not None:
        try:
            final_log_files = len(
                [f for f in os.listdir(Path(log_file).parent) if f.startswith(Path(log_file).name.split(".")[0])]
            )
        except:
            final_log_files = 0
    else:
        final_log_files = 0
    print(f"• Log files created: {final_log_files - initial_log_files}")

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
