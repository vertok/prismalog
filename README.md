# prismalog

A robust, multi-process safe logging system for Python applications that integrates perfectly with the psy-supabase package.

[![PyPI version](https://img.shields.io/pypi/v/prismalog.svg)](https://pypi.org/project/prismalog/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/prismalog.svg)](https://pypi.org/project/prismalog/)
[![Coverage Python 3.8](https://vertok.github.io/prismalog/badges/coverage-py3.8.svg)](https://vertok.github.io/prismalog/htmlcov/index.html)
[![Pylint Python 3.8](https://vertok.github.io/prismalog/badges/pylint-py3.8.svg)](https://vertok.github.io/prismalog/reports/html/3.8/reports/pylint/pylint-py3.8.html)
[![Coverage Python 3.10](https://vertok.github.io/prismalog/badges/coverage-py3.10.svg)](https://vertok.github.io/prismalog/htmlcov/index.html)
[![Pylint Python 3.10](https://vertok.github.io/prismalog/badges/pylint-py3.10.svg)](https://vertok.github.io/prismalog/reports/html/3.10/reports/pylint/pylint-py3.10.html)
[![Coverage Python 3.11](https://vertok.github.io/prismalog/badges/coverage-py3.11.svg)](https://vertok.github.io/prismalog/htmlcov/index.html)
[![Pylint Python 3.11](https://vertok.github.io/prismalog/badges/pylint-py3.11.svg)](https://vertok.github.io/prismalog/reports/html/3.11/reports/pylint/pylint-py3.11.html)

## Features

- ⚛️ Zero-dependency core
- 🚀 High performance
- 🎨 Colored console output
- 📁 Automatic log file rotation
- 🔄 Multi-process safe logging
- 🧵 Multithreading-safe logging
- ⚙️ YAML-based configuration
- 🔇 Control for verbose third-party libraries
- 🧪 Testing support

## Performance Characteristics

prismalog was designed for high-performance applications. My testing shows:

- **Overhead per log call**: ~0.15ms (typical)
- **Memory impact**: Minimal (~0.3MB for 10,000 messages)
- **Throughput**: Capable of handling 20,000+ messages per second
- **Multi-process/Multi-threading safety**: No measurable performance penalty compared to single-process

## Performance Notes

While prismalog achieves excellent performance characteristics, it's important to note that the primary bottleneck is filesystem I/O when writing to log files. This limitation is inherent to disk-based logging systems:

- File locking mechanisms required for multi-process safety introduce some overhead
- Synchronous writes to ensure log integrity can impact throughput during high-volume logging events
- Storage device speed directly impacts maximum sustainable throughput

For applications with extreme logging requirements, consider:
- Using an asynchronous logging configuration
- Implementing log batching for high-volume events
- Configuring separate log files for different components to distribute I/O load

The current performance metrics were achieved with standard SSD hardware. With specialized I/O optimization or enterprise-grade storage systems, significantly higher throughput is achievable.

## Quick Start

```python
from prismalog import get_logger, LoggingConfig

# Initialize with configuration file
LoggingConfig.initialize(config_file="config.yaml")

# Get a logger
logger = get_logger("my_module")
logger.info("Application started")
```

## Command-Line Integration

Any application using prismalog automatically supports these command-line arguments:

```bash
--log-config PATH          # Path to logging configuration file
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                           # Set the default logging level
--log-dir PATH             # Directory where log files will be stored
```

## Usage

```python
from prismalog.log import get_logger, LoggingConfig

# Initialize logging (with command-line support)
LoggingConfig.initialize(use_cli_args=True)

# Get logger and use it
logger = get_logger("my_app")
logger.info("Application started")
```

## Dependencies

prismalog is designed to work with **zero external dependencies** for core functionality. It relies solely on the Python standard library, making it lightweight and easy to integrate into any project.

### Optional Dependencies

- **YAML Configuration**: If YAML config files needed, install with `pip install prismalog[yaml]`
- **Development**: For running tests and examples, install with `pip install prismalog[dev]`

### Installation Options

```bash
# Prepare before installation (recommended)
python -m venv .venv
source source .venv/bin/activate

# Basic installation - no external dependencies
pip install -e .

# With documentation support
pip install prismalog[doc]

# For development and testing
pip install prismalog[dev]

# With all optional features
pip install prismalog[all]
