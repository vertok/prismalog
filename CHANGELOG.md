# Changelog

All notable changes to `prismalog` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.1.3] - 2025-05-28

### Added
- Introduced example_package_level_initialisation.py for logging setup on package level.
- Updated LoggingConfig to include initialization check and finalization phase.

## [v0.1.2] - 2025-05-15

### Added
- 'stacklevel=2' in log messages to better track where
log message was produced from

## [v0.1.1] - 2025-04-23

### Added
- `log_filename` configuration option via env var (`LOG_FILENAME`, `GITHUB_LOG_FILENAME`) and CLI (`--log-filename`) to set the base name for log files.
- `colored_file` configuration option via env var (`LOG_COLORED_FILE`, `GITHUB_LOG_COLORED_FILE`) and CLI (`--colored-file`) to enable ANSI color codes in file logs.
- Dependency caching (`actions/cache`) to the GitHub Actions CI workflow to speed up builds.

### Changed
- **Performance:** Default `log_format` now consistently uses `%(created)f` instead of `%(asctime)s` for significantly improved logging throughput. Benchmarks updated to reflect this and discuss the trade-offs.
- **Configuration:** Refined environment variable handling in `LoggingConfig`, including support for `NO_COLOR`/`NO_COLORS`. Improved type conversion logic.
- **CI:** Updated performance test reporting in CI summary.
- **Documentation:** Updated docstrings in `config.py`, `log.py`, `argparser.py` to reflect new options and configuration details. Updated benchmark `README.md` with performance details regarding `%(created)f` vs `%(asctime)s` and microsecond precision caveats.


## [v0.1.0] - 2025-04-20
- Initial release

### Added
- Initial release of `prismalog`
- Core logging functionality with multi-process support
- Configuration system with environment variable support
- High-performance message queue implementation
- Zero-dependency design for Python 3.8+
- Comprehensive test suite with 90%+ code coverage
- Full documentation and examples

[v0.1.0]: https://github.com/vertok/prismalog/releases/tag/v0.1.0
