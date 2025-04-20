.. _installation:

Installation
============

From Source
-----------

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/vertok/prismalog.git
       cd prismalog

2. Create a virtual environment:

   .. code-block:: bash

       # For standard usage
       python -m venv .venv

       # For development
       python -m venv .venv-dev

       # For testing
       python -m venv .venv-test

       # For documentation
       python -m venv .venv-doc

3. Activate the virtual environment:

   .. code-block:: bash

       # Choose one based on your needs:
       source .venv/bin/activate      # Standard usage
       source .venv-dev/bin/activate  # Development
       source .venv-test/bin/activate # Testing
       source .venv-doc/bin/activate  # Documentation

4. Install the package:

   .. code-block:: bash

       # Standard installation (zero dependencies)
       pip install -e .

       # Development installation (includes development tools)
       pip install -e .[dev]

       # Testing installation (includes testing frameworks)
       pip install -e .[test]

       # Documentation installation (includes doc generation tools)
       pip install -e .[doc]

       # Full installation (all dependencies)
       pip install -e .[all]

Usage
-----

Basic Configuration
~~~~~~~~~~~~~~~~~~~

Configure logging using command-line arguments:

.. code-block:: bash

    # Set log level
    python your_script.py --log-level DEBUG

    # Specify log directory
    python your_script.py --log-dir /path/to/logs

    # Use configuration file
    python your_script.py --log-config config.yaml

    # Activate exit on critical errors
    python your_script.py --exit-on-critical

    # Disable colored output
    python your_script.py --no-color

Available Arguments
~~~~~~~~~~~~~~~~~~~

--log-level LEVEL
    Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    Default: INFO

--log-dir DIR
    Specify directory for log files
    Default: ./logs

--log-config FILE
    Use YAML configuration file

--exit-on-critical
    Terminate program on critical errors

--no-color
    Disable colored console output
