"""
Comparative performance benchmark for prismalog.

This script runs all performance tests (multiprocessing, threading,
mixed concurrency, and standard logging if available) and provides a side-by-side
comparison of the results.
"""

import os
import subprocess
import re
import json
from datetime import datetime
from prismalog import LoggingConfig, get_logger

# Force console output for the script itself
print("Setting up console logging...")
LoggingConfig.initialize(parse_args=False, **{
    "colored_console": True,
    "test_mode": False,  # Make sure test mode is off
})

# Create a logger for this script
logger = get_logger("performance_compare")
logger.info("Starting performance comparison...")

def extract_metrics(output):
    """Extract key metrics from test output."""
    metrics = {}

    # Extract messages per second
    mps_match = re.search(r'Messages per second: ([\d.]+)', output)
    if mps_match:
        metrics['messages_per_second'] = float(mps_match.group(1))

    # Extract timing data
    timing_pattern = r'• ([A-Z]+):\s+mean=([\d.]+)ms, median=([\d.]+)ms'
    for level, mean, median in re.findall(timing_pattern, output):
        metrics[f'{level.lower()}_mean_ms'] = float(mean)
        metrics[f'{level.lower()}_median_ms'] = float(median)

    # Extract memory usage
    mem_pattern = r'• Delta: ([\d.]+) MB'
    mem_match = re.search(mem_pattern, output)
    if mem_match:
        metrics['memory_delta_mb'] = float(mem_match.group(1))

    # Extract execution time
    exec_time_match = re.search(r'• Total execution time: ([\d.]+) seconds', output)
    if exec_time_match:
        metrics['execution_time'] = float(exec_time_match.group(1))

    # Extract log file size
    log_size_match = re.search(r'• Size: ([\d.]+) MB', output)
    if log_size_match:
        metrics['log_size_mb'] = float(log_size_match.group(1))

    return metrics

def run_test(script_name):
    """Run a performance test script and capture output while showing logs in real-time."""
    print(f"\n{'-'*60}")
    print(f"Running {script_name}...")
    print(f"{'-'*60}")

    # Check if the script exists
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        logger.warning(f"Script not found: {script_path}")
        return None

    try:
        # Run the script and stream output to console while also capturing it
        output = []
        with subprocess.Popen(
            ['python', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        ) as process:
            # Read and display output in real-time
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                print(line.rstrip())
                output.append(line)

            return_code = process.wait()

        if return_code != 0:
            logger.error(f"{script_name} exited with code {return_code}")
            return None

        print(f"{'-'*60}")
        print(f"Completed {script_name}")
        print(f"{'-'*60}\n")

        return ''.join(output)

    except Exception as e:
        logger.error(f"Error running {script_name}: {e}")
        return None

def format_table_row(data, headers):
    """Format a row in the comparison table."""
    row = []
    for header in headers:
        if header in data:
            if isinstance(data[header], float):
                row.append(f"{data[header]:.2f}")
            else:
                row.append(str(data[header]))
        else:
            row.append("N/A")
    return row

def save_benchmark_results(results, test_type):
    """Save benchmark results to .benchmarks directory."""
    # Create benchmark directory
    benchmark_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", ".benchmarks")
    os.makedirs(benchmark_dir, exist_ok=True)

    # Create timestamped results file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(benchmark_dir, f"{test_type}_{timestamp}.json")

    # Save results
    with open(results_file, mode='w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"Saved {test_type} results to: {results_file}")
    return results_file

def main():
    """Run all performance tests and compare results."""
    print(f"\n{'='*80}")
    print(f"LOGGING PERFORMANCE COMPARISON - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    # Track available test results
    test_metrics = {}

    # Run performance tests
    try:
        # Run all tests and collect metrics
        test_files = [
            ("performance_test_multiprocessing.py", "multiproc", "Multiprocessing"),
            ("performance_test_threading.py", "threading", "Multithreading"),
            ("performance_test_mixed.py", "mixed", "Mixed Mode"),
            ("standard_logging_benchmark.py", "std", "Standard Logging")
        ]

        for script_name, key, display_name in test_files:
            output = run_test(script_name)
            if output:
                metrics = extract_metrics(output)
                metrics['test'] = display_name
                test_metrics[key] = metrics
                save_benchmark_results(metrics, f"test_{key}")

        if not test_metrics:
            logger.error("No test metrics collected. Please ensure at least one test script is available.")
            return

        # Define table structure
        headers = [
            'test', 'messages_per_second', 'execution_time',
            'debug_mean_ms', 'info_mean_ms', 'warning_mean_ms', 'error_mean_ms',
            'memory_delta_mb', 'log_size_mb'
        ]

        header_display = {
            'test': 'Test Type',
            'messages_per_second': 'Msgs/sec',
            'execution_time': 'Exec Time (s)',
            'debug_mean_ms': 'DEBUG (ms)',
            'info_mean_ms': 'INFO (ms)',
            'warning_mean_ms': 'WARNING (ms)',
            'error_mean_ms': 'ERROR (ms)',
            'memory_delta_mb': 'Memory Δ (MB)',
            'log_size_mb': 'Log Size (MB)'
        }

        # Format data for table
        rows = []
        for key, metrics in test_metrics.items():
            rows.append(format_table_row(metrics, headers))

        # Display results
        print(f"\n{'='*100}")
        print("PERFORMANCE COMPARISON RESULTS")
        print(f"{'='*100}")

        # Print header
        header_row = " | ".join([header_display[h].ljust(15) for h in headers])
        print(f"\n{header_row}")
        print("-" * len(header_row))

        # Print data rows
        for row in rows:
            formatted_row = " | ".join([str(cell).ljust(15) for cell in row])
            print(formatted_row)

        # Display relative performance if standard logging is available
        if 'std' in test_metrics:
            print(f"\n{'='*100}")
            print("RELATIVE PERFORMANCE (normalized to standard logging = 1.0)")
            print(f"{'='*100}")

            # Calculate relative performance for key metrics
            base_mps = test_metrics['std'].get('messages_per_second', 1.0)  # Avoid division by zero

            print("\nMessages per second (higher is better):")
            print("• Standard Logging: 1.00")

            for key, name in [('multiproc', 'Multiprocessing'),
                             ('threading', 'Multithreading'),
                             ('mixed', 'Mixed Mode')]:
                if key in test_metrics:
                    relative = test_metrics[key].get('messages_per_second', 0.0) / base_mps
                    print(f"• {name}:  {relative:.2f}")

            # Average log time across all levels (lower is better)
            std_avg_time = sum(test_metrics['std'].get(f'{level}_mean_ms', 0.0)
                               for level in ['debug', 'info', 'warning', 'error']) / 4

            print("\nAverage log time in milliseconds (lower is better):")
            print(f"• Standard Logging: {std_avg_time:.2f} ms (1.00)")

            for key, name in [('multiproc', 'Multiprocessing'),
                             ('threading', 'Multithreading'),
                             ('mixed', 'Mixed Mode')]:
                if key in test_metrics:
                    avg_time = sum(test_metrics[key].get(f'{level}_mean_ms', 0.0)
                                   for level in ['debug', 'info', 'warning', 'error']) / 4
                    relative = avg_time / std_avg_time if std_avg_time > 0 else 0
                    print(f"• {name}:  {avg_time:.2f} ms ({relative:.2f})")

        # Find the fastest approach
        fastest_metrics = None
        fastest_name = None
        for key, metrics in test_metrics.items():
            if fastest_metrics is None or metrics.get(
                    'messages_per_second', 0) > fastest_metrics.get('messages_per_second', 0):
                fastest_metrics = metrics
                fastest_name = metrics['test']

        print(f"\n{'='*100}")
        print("CONCLUSION")
        print(f"{'='*100}")
        print(f"\nFastest approach: {fastest_name}")
        print(f"Messages per second: {fastest_metrics.get('messages_per_second', 0):.2f}")

        print("\nRecommendation: Choose the approach that best matches your application's")
        print("concurrency model rather than optimizing solely for logging performance.")

        if 'std' in test_metrics and fastest_name == "Standard Logging":
            print("\nNOTE: Standard Python logging outperformed prismalog in raw throughput.")
            print("However, prismalog provides additional features like enhanced color support,")
            print("better configuration management, and a more ergonomic API that may outweigh")
            print("the raw performance advantage for many use cases.")

        print(f"\n{'='*100}")

        # Create comparison data for JSON output
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "tests": dict(test_metrics),
            "fastest_approach": fastest_name,
            "fastest_messages_per_second": fastest_metrics.get('messages_per_second', 0)
        }

        # Add relative performance if standard logging is available
        if 'std' in test_metrics:
            base_mps = test_metrics['std'].get('messages_per_second', 1.0)
            comparison["relative_performance"] = {
                "messages_per_second": {
                    "standard": 1.0
                }
            }

            for key in ["multiproc", "threading", "mixed"]:
                if key in test_metrics:
                    comparison["relative_performance"]["messages_per_second"][key] = \
                        test_metrics[key].get('messages_per_second', 0.0) / base_mps

        # Save comparison results
        save_benchmark_results(comparison, "comparison")

    except Exception as e:
        logger.exception(f"Error during comparison: {e}")


if __name__ == "__main__":
    main()
