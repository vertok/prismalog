"""
Log Sequence Test for prismalog

This module provides testing functionality to validate the consistency and
integrity of sequential logging across different log levels. It demonstrates
how prismalog handles rapid sequential logging operations.

The test generates a sequence of log entries with different severity levels
(DEBUG, INFO, WARNING, ERROR) and verifies that:
1. All messages are properly written to the log file
2. The sequence of log levels is maintained
3. No messages are dropped during high-volume logging

Each process is represented by a distinct color in the console output,
making it easy to visually distinguish between different processes when
running in a multiprocessing environment.

Usage:
    python log_sequence_test.py

You can adjust the number of iterations by modifying the parameter
in the __main__ block at the bottom of this file.
"""
import os
import time
from datetime import datetime
from prismalog.log import ColoredLogger, get_logger

def log_sequence_test(iterations=100):
    """
    Test if consecutive logging with different log levels works consistently.

    Args:
        iterations: Number of iterations to run the test
    """
    print(f"\n{'='*60}")
    print(f"LOG SEQUENCE TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"• Testing {iterations} iterations of sequential log levels")

    # Disable rotation for this test
    os.environ['LOG_DISABLE_ROTATION'] = '1'

    # Create a fresh logger and log file
    ColoredLogger.reset(new_file=True)
    log_file = ColoredLogger._log_file_path
    print(f"• Using log file: {log_file}")

    logger = get_logger("sequence_test", verbose="DEBUG")

    print("\nRunning sequence test...")
    start_time = time.time()

    # Run the sequence test
    for i in range(iterations):
        # Log with all levels in sequence
        logger.debug(f"[{i}] DEBUG level message in sequence")
        logger.info(f"[{i}] INFO level message in sequence")
        logger.warning(f"[{i}] WARNING level message in sequence")
        logger.error(f"[{i}] ERROR level message in sequence")

        # Optional: add a tiny delay to make it easier to see sequences in logs
        # time.sleep(0.001)

    duration = time.time() - start_time
    print(f"• Completed in {duration:.2f} seconds")
    print(f"• Messages per second: {(iterations * 4)/duration:.2f}")

    # Verify log file contents
    print("\nVerifying log file...")
    with open(log_file, mode='r', encoding='utf-8') as f:
        log_content = f.read()
        log_lines = log_content.strip().split('\n')
        total_lines = len(log_lines)

    print(f"• Total log lines: {total_lines}")
    print(f"• Expected lines: {iterations * 4}")

    if total_lines == iterations * 4:
        print("✅ Log line count matches expected value")
    else:
        print("❌ Log line count doesn't match expected value")

    # Analyze sequence pattern
    print("\nAnalyzing log sequence integrity...")

    # Sample a few sequences for verification
    sequences_to_check = min(10, iterations)
    sequence_valid = True

    for i in range(sequences_to_check):
        check_idx = i * 4  # Each iteration has 4 log lines
        if check_idx + 3 >= total_lines:
            break

        has_debug = "[DEBUG]" in log_lines[check_idx]
        has_info = "[INFO]" in log_lines[check_idx+1]
        has_warning = "[WARNING]" in log_lines[check_idx+2]
        has_error = "[ERROR]" in log_lines[check_idx+3]

        sequence_ok = all([has_debug, has_info, has_warning, has_error])
        if not sequence_ok:
            sequence_valid = False
            print(f"❌ Sequence broken at iteration {i}:")
            print(f"  Line {check_idx}: {'DEBUG' if has_debug else 'NOT DEBUG'}")
            print(f"  Line {check_idx+1}: {'INFO' if has_info else 'NOT INFO'}")
            print(f"  Line {check_idx+2}: {'WARNING' if has_warning else 'NOT WARNING'}")
            print(f"  Line {check_idx+3}: {'ERROR' if has_error else 'NOT ERROR'}")

    if sequence_valid:
        print("✅ Log sequences appear valid")

    # Additional integrity check - search for specific message patterns
    print("\nChecking for specific message patterns...")

    # Check some random iterations
    check_iterations = [0, iterations//2, iterations-1]
    for i in check_iterations:
        debug_msg = f"[{i}] DEBUG level message"
        info_msg = f"[{i}] INFO level message"
        warning_msg = f"[{i}] WARNING level message"
        error_msg = f"[{i}] ERROR level message"

        has_debug = any(debug_msg in line for line in log_lines)
        has_info = any(info_msg in line for line in log_lines)
        has_warning = any(warning_msg in line for line in log_lines)
        has_error = any(error_msg in line for line in log_lines)

        if all([has_debug, has_info, has_warning, has_error]):
            print(f"✅ Iteration {i}: All message types found")
        else:
            print(f"❌ Iteration {i}: Missing message types")
            if not has_debug:   print("  - Missing DEBUG message")    # pylint: disable=multiple-statements
            if not has_info:    print("  - Missing INFO message")     # pylint: disable=multiple-statements
            if not has_warning: print("  - Missing WARNING message")  # pylint: disable=multiple-statements
            if not has_error:   print("  - Missing ERROR message")    # pylint: disable=multiple-statements

    print(f"\n{'='*60}")
    print("TEST COMPLETED")
    print(f"{'='*60}")
    print("Open the log file to inspect it manually:")
    print(f"{log_file}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Adjust the number of iterations here.
    log_sequence_test(iterations=10000)
