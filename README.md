# prismalog

A robust, multi-process safe logging system for Python applications that integrates perfectly with the psy-supabase package.

[![Documentation Status](https://readthedocs.org/projects/prismalog/badge/?version=latest)](https://prismalog.readthedocs.io/en/latest/?badge=latest)
[![PyLint](https://img.shields.io/badge/PyLint-10.0/10-brightgreen)](https://github.com/vertok/prismalog)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)](https://github.com/vertok/prismalog)
[![Python Versions](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![PyPI version](https://badge.fury.io/py/prismalog.svg)](https://badge.fury.io/py/prismalog)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/prismalog)](https://pypi.org/project/prismalog/)

## Features

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
from prismalog import get_logger, setup_logging

# Initialize logging (with command-line support)
setup_logging()

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

# With YAML support
pip install prismalog[yaml]

# With all optional features
pip install prismalog[all]

# For development and testing
pip install prismalog[dev]
