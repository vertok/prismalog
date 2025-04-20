.. _usage:

Usage Guide
===========

Basic Usage
-----------

.. code-block:: python

   from prismalog.log import LoggingConfig, get_logger

   # Initialize logging
   LoggingConfig.initialize()

   # Create a logger
   logger = get_logger(__name__)

   # Log messages at different levels
   logger.debug("Debug message")
   logger.info("Info message")
   logger.warning("Warning message")
   logger.error("Error message")
   logger.critical("Critical message")

Usage
=====

Command Line Interface
----------------------

prismalog provides a standardized command-line interface through its argument parser.
All applications using prismalog can access these common arguments:

.. code-block:: bash

    python your_script.py [options]

Common Arguments
~~~~~~~~~~~~~~~~

--log-level LEVEL
    Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    Default: INFO

--log-dir DIR
    Specify the directory for log files
    Default: ./logs

--log-config FILE
    Use a YAML configuration file for logging settings

--exit-on-critical
    Terminate program on critical errors

--no-color
    Disable colored console output

.. _colored-console-output:

Colored Console Output
----------------------

.. _configuration:

Configuration
-------------

Command-line Arguments:
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python your_script.py --verbose DEBUG --log-config config.yaml

YAML Configuration:
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # config.yaml
   default_level: INFO
   colored_console: true
   log_dir: logs
   rotation_size_mb: 10
   backup_count: 5
   exit_on_critical: false

   # Control third-party libraries
   external_loggers:
     requests: WARNING
     urllib3: ERROR
