# prismalog Examples

This directory contains examples demonstrating how to use the prismalog package in different scenarios.

## Core Features (Zero Dependencies)

prismalog's core logging functionality requires **no external dependencies**. You can use all of the following features without installing anything beyond the Python standard library:

- Colored console logging
- Multi-process safe logging
- Log file rotation
- Custom log levels
- Logger hierarchies
- Command-line argument parsing
- Environment variable configuration

## Extended Features (Optional Dependencies)

Some advanced features require minimal optional dependencies:

- **YAML Configuration**: Requires PyYAML (`pip install PyYAML`)
- **Integration Examples**: Require specific libraries as documented in their folders

## Available Examples

This repository is organized to separate examples by their dependency requirements:

- **Main examples**: Located directly in this folder, these examples require only prismalog itself
  - `example.py`: Basic example showing how to initialize logging with a config file and use different log levels
  - `config.yaml`: Example configuration file showing available options
  - `config_no_exit.yaml`: Configuration that disables program termination on critical logs

- **Integration examples**: Located in the `integrations/` subfolder, these examples require additional dependencies
  - `integrations/nltk_example/nltk_example.py`: Demonstrates how to control verbose third-party libraries like NLTK

## Dependencies

- **Basic examples** (in this directory): No additional dependencies beyond prismalog
  ```bash
  pip install prismalog
  ```

- **Integration examples**: Require specific additional libraries as documented in their respective folders
  ```bash
  # For nltk_example:
  cd integrations/nltk_example
  pip install -r requirements.txt
  ```

## How to Run

### Basic Examples (No Additional Dependencies)

To run the basic example:

```bash
python example.py
```

To run with different logging levels:

```bash
python example.py --log-level DEBUG
```

To use a specific configuration file:

```bash
python example.py --log-config config_no_exit.yaml
```

### Integration Examples (Additional Dependencies Required)

NLTK example (requires nltk package):

```bash
# First install dependencies
cd integrations/nltk_example
pip install -r requirements.txt

# Then run the example
python nltk_example.py --log-config config_nltk_quiet.yaml
```

## Example Use Cases

### Basic Logging

The `example.py` demonstrates how to:
- Initialize logging with configuration
- Use different logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Control whether critical logs cause program termination

### Multi-process Logging

Examples show how logging works across multiple processes without file corruption or interleaved log lines.

### Managing External Libraries

The `integrations/nltk_example/nltk_example.py` illustrates configuration-based control of external library verbosity, enabling clean logs while preserving necessary information.
