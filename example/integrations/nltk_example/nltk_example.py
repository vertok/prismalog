"""
NLTK Integration Example for prismalog

This example demonstrates how prismalog can effectively control and manage
verbose logging from third-party libraries such as NLTK (Natural Language Toolkit).

NLTK is known for generating numerous log messages during data downloads
and processing, which can easily overwhelm application logs. This example
showcases how prismalog can:

1. Selectively filter third-party library logs based on configuration
2. Control verbosity levels for external dependencies without modifying their code
3. Maintain clean application logs while still capturing important information
4. Demonstrate different configuration approaches (verbose vs. quiet)

Usage:
    # Use default configuration (verbose):
    python nltk_example.py

    # Use specific config file:
    python nltk_example.py --log-config config_nltk_quiet.yaml

    # Set specific log level:
    python nltk_example.py --log-level DEBUG
"""

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from logging import Logger
    from prismalog.log import ColoredLogger

import nltk  # type: ignore
from nltk.tokenize import word_tokenize  # type: ignore

from prismalog.argparser import extract_logging_args, get_argument_parser
from prismalog.log import LoggingConfig, get_logger


def download_nltk_data(logger: Union["Logger", "ColoredLogger"]) -> bool:
    """
    Download NLTK data with logging configuration from config file or CLI args.

    Returns:
        bool: True if download was successful, False otherwise
    """
    # Log configuration info
    config_file = LoggingConfig.get("config_file", None)
    if config_file:
        logger.info("Using configuration from: %s", config_file)
    else:
        logger.info("Using default configuration")

    # Get the configured log level for NLTK
    external_loggers = LoggingConfig.get("external_loggers", {})
    nltk_level = external_loggers.get("nltk", "INFO")
    use_quiet = nltk_level in ["WARNING", "ERROR", "CRITICAL"]

    logger.info(f"NLTK log level: {nltk_level}")
    logger.info(f"NLTK download quiet mode: {'enabled' if use_quiet else 'disabled'}")

    logger.info("Starting NLTK data download...")

    try:
        # Download a few popular NLTK datasets
        logger.info("Downloading punkt tokenizer...")
        nltk.download("punkt", quiet=use_quiet)

        logger.info("Downloading stopwords...")
        nltk.download("stopwords", quiet=use_quiet)

        logger.info("Downloading wordnet...")
        nltk.download("wordnet", quiet=use_quiet)

        # Use the downloaded resources
        logger.info("Testing the downloaded resources...")

        # Test punkt
        text = "NLTK is a leading platform for building Python programs to work with human language data."
        tokens = word_tokenize(text)
        logger.info(f"Tokenized text: {tokens[:5]}...")

        # Test stopwords
        from nltk.corpus import stopwords  # type: ignore

        stop_words = set(stopwords.words("english"))
        filtered_tokens = [w for w in tokens if w.lower() not in stop_words]
        logger.info(f"After removing stopwords: {filtered_tokens[:5]}...")

        # Test wordnet
        from nltk.corpus import wordnet as wn  # type: ignore

        synonyms = []
        for syn in wn.synsets("program"):
            for lemma in syn.lemmas():
                synonyms.append(lemma.name())
        if synonyms:
            logger.info(f"Synonyms of 'program': {synonyms[:5]}...")

        logger.info("NLTK example completed successfully!")

    except Exception as e:
        logger.exception(f"Error during NLTK operations: {e}")
        return False

    return True


def main() -> None:
    """Main function to run the NLTK example with logging control."""
    # Create parser with standard logging arguments
    parser = get_argument_parser(description="NLTK Example")

    # Parse arguments
    args = parser.parse_args()

    # Extract logging arguments
    logging_args = extract_logging_args(args)

    # Initialize logging with extracted arguments
    LoggingConfig.initialize(use_cli_args=True, **logging_args)

    # Get logger for this module
    logger = get_logger(__name__)

    success = download_nltk_data(logger)

    if success:
        print("\nCompleted! Check the logs to see the difference.")
        if logging_args.get("config_file"):
            print("Note: Configuration from --log-config was used.")
        else:
            print("Note: Default configuration was used.")


if __name__ == "__main__":
    main()
