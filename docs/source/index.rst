.. _prismalog-documentation:

prismalog Documentation
=======================

.. image:: https://img.shields.io/badge/Python-3.8%2B-blue
   :target: https://www.python.org/downloads/
.. image:: https://img.shields.io/badge/License-MIT-green.svg
   :target: https://opensource.org/licenses/MIT
.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg
   :target: https://prismalog.readthedocs.io/

A high-performance, colored, multi-process logging system for Python applications.

.. image:: https://img.shields.io/badge/Python-3.8%2B-blue
   :target: https://www.python.org/downloads/

**prismalog** enhances Python's logging capabilities with powerful features while maintaining
compatibility with the standard library.

Key Features
------------

.. grid:: 2

    .. grid-item-card:: Colored Output
        :link: colored-console-output
        :link-type: ref
        :img-top: _static/color.png

        Colorized log levels and messages for improved readability

    .. grid-item-card:: Multi-process Safe
        :link: multi-process-logging
        :link-type: ref
        :img-top: _static/multiprocess.png

        Thread and process-safe logging without message interleaving

    .. grid-item-card:: Easy Configuration
        :link: configuration
        :link-type: ref
        :img-top: _static/config.png

        Configure via YAML, environment variables or command line

    .. grid-item-card:: Quiet Libraries
        :link: controlling-noisy-libraries
        :link-type: ref
        :img-top: _static/quiet.png

        Silence noisy third-party libraries with simple configuration

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   examples
   api/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
