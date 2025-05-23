# Performance Benchmarks

## Comparison of Logging Performance

Comprehensive benchmarks were conducted to evaluate the performance characteristics of the `prismalog` package across different concurrency models. These benchmarks were compared to Python's standard logging library.

### Test Configuration

| Test Type        | Processes               | Threads        |
|------------------|-------------------------|----------------|
| Multiprocessing  | 3 processes             | 1 thread       |
| Multithreading   | 1 processe              | 3 threads      |
| Mixed Mode       | 2 processes             | 2 threads      |
| Standard Logging | 1 processe              | 3 threads      |

### Key Observations

1.  **Concurrency Models**:
    *   The highest throughput was observed in the multiprocessing model, with nearly 27,000 messages processed per second.
    *   A good balance of throughput and resource utilization was achieved in the mixed mode (processes with threads).
    *   The multithreading model demonstrated consistent performance at around 10,000 messages per second.
    *   The standard logging library processed approximately 6,500 messages per second.

2.  **Latency**:
    *   The lowest per-message latency (0.07-0.08ms) was provided by multiprocessing.
    *   Medium latency (0.17-0.21ms) was observed in mixed mode.
    *   Higher latency (0.26-0.42ms) was observed in thread-based approaches.
    *   Standard logging exhibited the highest latency (0.40-0.46ms) across all log levels.

3.  **Resource Usage**:
    *   Minimal memory consumption (0.20-0.49MB) was observed across prismalog approaches.
    *   Standard logging showed the lowest memory increase (0.04MB) but with slower performance.
    *   Log file sizes remained compact (0.61-1.13MB) across all approaches.

4.  **Timestamp Formatting Impact**:
    *   **Crucially, the choice of timestamp format significantly impacts performance.** Using `%(created)f` (which logs a raw numeric timestamp) can achieve substantially higher throughput (observed up to **~35,000 msgs/sec** in testing) compared to using `%(asctime)s` (which formats the timestamp into a human-readable string, observed maxing out around **~25,000 msgs/sec**).
    *   While `%(created)f` requires post-processing to convert timestamps for readability, it drastically reduces logging overhead.

### Results Summary

| Test Type       | Msgs/sec   | Exec Time (s) | DEBUG (ms) | INFO (ms) | WARNING (ms) | ERROR (ms) | Memory Δ (MB) | Log Size (MB) |
|-----------------|------------|---------------|------------|-----------|--------------|------------|---------------|---------------|
| Multiprocessing | 27,516.90  | 0.34          | 0.10       | 0.10      | 0.11         | 0.08       | 0.20          | 0.91          |
| Multithreading  | 10,141.39  | 1.22          | 0.42       | 0.39      | 0.38         | 0.30       | 0.50          | 1.11          |
| Mixed Mode      | 18,249.71  | 0.68          | 0.22       | 0.21      | 0.22         | 0.13       | 0.23          | 1.13          |
| Standard Logging| 6,572.58   | 1.41          | 0.46       | 0.45      | 0.46         | 0.38       | 0.05          | 0.79          |

### Key Observations

1. **Concurrency Models**:
   - The highest throughput was observed in the multiprocessing model, with nearly 27,000 messages processed per second.
   - A good balance of throughput and resource utilization was achieved in the mixed mode (processes with threads).
   - The multithreading model demonstrated consistent performance at around 10,000 messages per second.
   - The standard logging library processed approximately 6,500 messages per second.

2. **Latency**:
   - The lowest per-message latency (0.07-0.08ms) was provided by multiprocessing.
   - Medium latency (0.17-0.21ms) was observed in mixed mode.
   - Higher latency (0.26-0.42ms) was observed in thread-based approaches.
   - Standard logging exhibited the highest latency (0.40-0.46ms) across all log levels.

3. **Resource Usage**:
   - Minimal memory consumption (0.20-0.49MB) was observed across prismalog approaches.
   - Standard logging showed the lowest memory increase (0.04MB) but with slower performance.
   - Log file sizes remained compact (0.61-1.13MB) across all approaches.

### Performance Benchmarking

The `benchmark/performance_test.py` script allows you to measure logging performance under different concurrency models.

**Arguments:**

*   `-p N`, `--processes N`: Use N worker processes (default: 2).
*   `-t M`, `--threads M`: Use M worker threads per process (default: 2).

**Examples:**

*   **Multiprocessing Test (e.g., 3 processes, 1 thread each):**
    ```bash
    python benchmark/performance_test.py -p 3 -t 1
    ```

*   **Multithreading Test (e.g., 1 process, 3 threads):**
    ```bash
    python benchmark/performance_test.py -p 1 -t 3
    ```

*   **Mixed Concurrency Test (e.g., 2 processes, 2 threads each):**
    ```bash
    python benchmark/performance_test.py -p 2 -t 2
    # Or simply run with defaults:
    # python benchmark/performance_test.py
    ```

The script also accepts standard `prismalog` arguments like `--log-level`, `--log-format`, etc., to configure the logger during the benchmark. Rotation is automatically disabled during the benchmark run for consistent results.

### Feature Advantages Over Standard Logging

While performance benchmarks provide valuable insights, several important features are offered by `prismalog` that are not available in the standard logging library:

1.  **Process-Safe & Thread-Safe File Handling**:
    *   The included file handlers (`MultiProcessingLog`) are specifically designed to handle concurrent writes from multiple processes and threads safely, preventing log corruption or race conditions. Standard `RotatingFileHandler` is not inherently process-safe without external locking mechanisms.

2. **Color-coded Console Output**:
   - Syntax highlighting for log messages is applied automatically based on their severity level.
   - Customizable color schemes are supported for different environments.
   - Readability is improved by visually distinguishing between different message types.

3. **Special Critical Message Handling**:
   - Application termination on critical errors is optionally supported.
   - Configurable callbacks for critical message events are provided.
   - Stack trace preservation is ensured for critical failures.

4. **Advanced Configuration**:
   - Environment variable support is included, with sensible defaults and multiple fallback patterns.
   - Command-line argument integration is supported, with automatic help generation.
   - Configuration file support (YAML) is provided, with automatic detection.

5. **Developer Experience Enhancements**:
   - A simplified API is offered for common logging patterns.
   - Context managers are provided for temporary logging level changes.
   - Convenient decorators are included for function entry/exit logging.

### Choosing the Right Approach

- **Multiprocessing** should be used for maximum throughput in CPU-bound logging applications.
- **Threading** is recommended for I/O-bound applications or when shared memory is required.
- **Mixed Mode** is suitable for complex applications that benefit from both process isolation and thread efficiency.
- **Additional Features** should be considered when advanced logging capabilities, such as color coding and special critical message handling, are more important than raw performance.

These benchmarks were conducted on a modern multi-core system running Linux. Variations in performance may be observed based on system specifications, file system performance, and application characteristics.
