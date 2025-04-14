# prismalog Examples

This directory contains examples demonstrating how to use the prismalog package in different scenarios.

## Available Examples

- `example.py`: Basic example showing how to initialize logging with a config file and use different log levels
- `nltk_example.py`: Demonstrates how to control verbose third-party libraries like NLTK using prismalog
- `config.yaml`: Example configuration file showing available options
- `config_no_exit.yaml`: Configuration that disables program termination on critical logs

## How to Run

To run the basic example:

```bash
python example.py
```bash

To run with different logging levels

```bash
python example.py --log-level DEBUG
```bash

To use a specific file:

```bash
python example.py --log-config config_no_exit.yaml
```bash

For the filterring third-party dirty logging:

```bash
python nltk_example.py --log-config config_nltk_quiet.yaml
```bash


## Example Use Cases

### Basic Logging

The `example.py` demonstrates how to:
- Initialize logging with configuration
- Use different logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Control whether critical logs cause program termination

### Multi-process Logging

Examples show how logging works across multiple processes without file corruption or interleaved log lines.

### Managing External Libraries

# prismalog Examples

This directory contains examples demonstrating various usage scenarios for the prismalog package.

## Available Examples

- `example.py`: Basic implementation showcasing logging initialization with configuration files and different log levels
- `nltk_example.py`: Demonstration of controlling verbose third-party libraries (NLTK) using prismalog
- `config.yaml`: Sample configuration file illustrating available options
- `config_no_exit.yaml`: Alternative configuration that disables program termination on critical logs

## Execution Instructions

Execute the basic example:

```bash
python example.py
```

Run with specific logging levels:

```bash
python example.py --log-level DEBUG
```

Specify a custom configuration file:

```bash
python example.py --log-config config_no_exit.yaml
```

Filter verbose third-party logging:

```bash
python nltk_example.py --log-config config_nltk_quiet.yaml
```

## Example Use Cases

### Basic Logging

The `example.py` file demonstrates:
- Logging initialization with configuration
- Implementation of different logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Configuration of critical log behavior regarding program termination

### Multi-process Logging

Examples demonstrate concurrent logging across multiple processes while maintaining file integrity and log coherence.

### External Library Management

The `nltk_example.py` illustrates configuration-based control of external library verbosity, enabling clean logs while preserving necessary information.
```
