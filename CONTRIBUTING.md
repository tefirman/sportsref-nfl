# Contributing to sportsref-nfl

Thank you for your interest in contributing to sportsref-nfl! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/tefirman/sportsref-nfl.git
   cd sportsref-nfl
   ```

2. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks (recommended):**
   ```bash
   pre-commit install
   ```

## Code Quality

We use several tools to maintain code quality:

- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pytest** for testing

### Running Quality Checks

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy sportsref_nfl --ignore-missing-imports

# Tests
pytest tests/ -v
```

### Pre-commit Hooks

Pre-commit hooks will automatically run these checks before each commit. If you have pre-commit installed (`pre-commit install`), these checks will run automatically.

## Testing

- Add tests for new functionality in the `tests/` directory
- Ensure all tests pass before submitting a PR
- Aim for good test coverage of new code

## Submitting Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit:**
   ```bash
   git add .
   git commit -m "Add your descriptive commit message"
   ```

3. **Push and create a Pull Request:**
   ```bash
   git push origin feature/your-feature-name
   ```

## Pull Request Guidelines

- Provide a clear description of the changes
- Include tests for new functionality
- Update documentation if needed
- Ensure all CI checks pass
- Keep PRs focused and atomic

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages (if any)

## Code Style

We follow these conventions:

- **Line length:** 88 characters
- **Quotes:** Double quotes for strings
- **Imports:** Organized with isort (handled by Ruff)
- **Type hints:** Required for public functions
- **Docstrings:** Google-style docstrings

## Questions?

Feel free to open an issue for questions or reach out via email at tefirman@gmail.com.

Thanks for contributing! 🎉