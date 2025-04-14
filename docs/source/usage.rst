.. _usage:

Usage Guide
===========

Basic Usage
-----------

.. code-block:: python

   from prismalog import setup_logging, get_logger

   # Initialize logging
   setup_logging()

   # Create a logger
   logger = get_logger(__name__)

   # Log messages at different levels
   logger.debug("Debug message")
   logger.info("Info message")
   logger.warning("Warning message")
   logger.error("Error message")
   logger.critical("Critical message")

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
   exit_on_critical: true

   # Control third-party libraries
   external_loggers:
     requests: WARNING
     urllib3: ERROR
