# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] - 2026-02-13

### Fixed
- International game parsing error caused by malformed Wikipedia table rows
- Replaced deprecated `isnull()`/`notnull()` with `isna()`/`notna()` across the codebase
- Replaced `os.system("wget ...")` in depth chart retrieval with `requests.get()` for portability and security

### Added
- `Makefile` with `lint`, `typecheck`, `test`, `check`, and `format` targets
- `CHANGELOG.md` covering all releases from v0.1.0 onward
- Updated README with Makefile documentation in the Development section

### Changed
- Python 3.13 added to supported versions
- Upgraded mypy version in CI/CD pipeline

## [0.1.3] - 2025-08-25

### Fixed
- FutureWarning in schedule assembly from deprecated pandas patterns

### Changed
- Added `User-Agent` header to Wikipedia requests to respect their robot policy

## [0.1.2] - 2025-08-14

### Added
- Caching logic for Team and Roster endpoints

### Changed
- Improved mypy type checking configuration and fixed type annotation issues
- Added pre-commit configuration with ruff and mypy hooks

## [0.1.1] - 2025-08-09

### Added
- File-based caching system with intelligent expiration rules
- CLI interface for all major data retrieval functions

### Fixed
- Various CLI bugs and documentation updates
- Ruff and mypy linting issues

### Changed
- Updated GitHub Actions publishing workflow

## [0.1.0] - 2025-08-06

### Added
- Initial release of sportsref-nfl
- Schedule retrieval and ELO rating calculations
- Boxscore data parsing
- Player statistics, rosters, draft data, and depth charts
- Stadium location and travel calculation functionality
- QB ELO rating system
- GitHub Actions CI/CD pipeline with multi-OS, multi-version testing
- PyPI publishing workflow
