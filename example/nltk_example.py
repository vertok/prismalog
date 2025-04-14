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

The example downloads several NLTK datasets and performs basic NLP operations,
comparing the logging output with different configurations:
- config_nltk_verbose.yaml: Shows all NLTK messages (noisy but complete)
- config_nltk_quiet.yaml: Suppresses routine NLTK messages for cleaner logs

This capability is particularly valuable in production environments where
signal-to-noise ratio in logs is critical for effective monitoring and debugging.

Usage:
    python nltk_example.py                       # Uses default config (verbose)
    python nltk_example.py --log-config config_nltk_quiet.yaml  # Suppressed logs
"""
import os
import argparse
from prismalog import get_logger, LoggingConfig

def download_nltk_data():
    """
    Download NLTK data with logging configuration from config file or CLI args.
    """
    # Get logger
    logger = get_logger("nltk_example")

    # Log configuration info
    config_file = LoggingConfig.get("config_file", None)
    if config_file:
        logger.info(f"Using configuration from: {config_file}")
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
        import nltk

        # Download a few popular NLTK datasets
        logger.info("Downloading punkt tokenizer...")
        nltk.download('punkt', quiet=use_quiet)

        logger.info("Downloading stopwords...")
        nltk.download('stopwords', quiet=use_quiet)

        logger.info("Downloading wordnet...")
        nltk.download('wordnet', quiet=use_quiet)

        # Use the downloaded resources
        logger.info("Testing the downloaded resources...")

        # Test punkt
        from nltk.tokenize import word_tokenize
        text = "NLTK is a leading platform for building Python programs to work with human language data."
        tokens = word_tokenize(text)
        logger.info(f"Tokenized text: {tokens[:5]}...")

        # Test stopwords
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
        filtered_tokens = [w for w in tokens if w.lower() not in stop_words]
        logger.info(f"After removing stopwords: {filtered_tokens[:5]}...")

        # Test wordnet
        from nltk.corpus import wordnet as wn
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

def main():
    """Main function to run the NLTK example with logging control."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="NLTK Example with logging control")

    # Add a unique flag for logging config that won't conflict with other args
    parser.add_argument('--log-config', '--log-conf', dest='config_file', help='Path to logging configuration file')

    args = parser.parse_args()

    # Initialize with the specified config file or use default
    if args.config_file:
        if os.path.exists(args.config_file):
            config_file = args.config_file
        else:
            print(f"Warning: Config file '{args.config_file}' not found. Using default config.")
            config_file = 'example/config_nltk_verbose.yaml'
            # Check if default exists too
            if not os.path.exists(config_file):
                print(f"Warning: Default config file '{config_file}' not found either. Using internal defaults.")
                config_file = None
    else:
        config_file = 'example/config_nltk_verbose.yaml'
        # Check if default exists
        if not os.path.exists(config_file):
            print(f"Warning: Default config file '{config_file}' not found. Using internal defaults.")
            config_file = None

    # Initialize with the proper config file or None for defaults
    LoggingConfig.initialize(config_file=config_file, parse_args=False)

    success = download_nltk_data()

    if success:
        print("\nCompleted! Check the logs to see the difference.")
        if config_file:
            if args.config_file and os.path.exists(args.config_file):
                print("Note: CUSTOM configuration was used.")
            else:
                print("Note: DEFAULT configuration was used.")
        else:
            print("Note: INTERNAL DEFAULTS were used (no config file found).")

if __name__ == "__main__":
    main()
