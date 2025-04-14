.. _examples:

Examples
========

Basic Logging Example
---------------------

.. code-block:: python

   from prismalog import setup_logging, get_logger

   # Initialize with defaults
   setup_logging()

   logger = get_logger(__name__)
   logger.debug("This is a debug message")
   logger.info("This is an info message")
   logger.warning("This is a warning message")
   logger.error("This is an error message")

.. figure:: _static/basic_example_output.png
   :alt: Example Output
   :align: center

   Console output from the example above

Configuration with YAML
-----------------------

.. code-block:: python

   from prismalog import setup_logging, get_logger

   # Initialize with a YAML config file
   setup_logging(config_file="config.yaml")

   logger = get_logger(__name__)
   logger.info("Logging with custom configuration")

YAML Configuration File:

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

.. _controlling-noisy-libraries:

Controlling Noisy Libraries
---------------------------

.. code-block:: python

   from prismalog import setup_logging, get_logger

   # Load config that controls noisy libraries
   setup_logging(config_file="config_nltk_quiet.yaml")

   logger = get_logger(__name__)

   # Now these imports won't flood your logs
   import requests
   import nltk

   # Make HTTP request with controlled logging
   response = requests.get("https://example.com")
   logger.info(f"Status code: {response.status_code}")

   # Download NLTK data without verbose output
   nltk.download('punkt')

.. _multi-process-logging:

Multi-process Logging
---------------------

.. code-block:: python

   import multiprocessing
   from prismalog import setup_logging, get_logger

   def worker_process(name):
       # Each process gets its own logger
       logger = get_logger(f"worker.{name}")
       logger.info(f"Worker {name} started")
       logger.debug(f"Worker {name} doing something")
       logger.info(f"Worker {name} finished")

   if __name__ == "__main__":
       # Initialize logging before creating processes
       setup_logging()
       logger = get_logger("main")

       processes = []
       for i in range(5):
           p = multiprocessing.Process(
               target=worker_process,
               args=(f"process-{i}",)
           )
           processes.append(p)
           p.start()

       for p in processes:
           p.join()

       logger.info("All workers finished")
