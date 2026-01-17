# Contributing to pbir-utils

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to `pbir-utils`. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [I Have a Question](#i-have-a-question)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project and everyone participating in it is governed by the [pbir-utils Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## I Have a Question

If you have questions, please search the existing [Issues](https://github.com/akhilannan/pbir-utils/issues) to see if someone else has already asked the same question. If not, feel free to open a new issue.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report.
- **Use a clear and descriptive title** for the issue to identify the problem.
- **Describe the exact steps to reproduce the problem** in as much detail as possible.
- **Include screenshots and animated GIFs** which show you following the reproduction steps.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.
- **Use a clear and descriptive title** for the issue to identify the suggestion.
- **Provide a step-by-step description of the suggested enhancement** in as much detail as possible.
- **Explain why this enhancement would be useful** to most users.

## Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/akhilannan/pbir-utils.git
    cd pbir-utils
    ```

2.  **Install `uv`:**
    Follow the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/) to install `uv`.

3.  **Sync environment:**
    ```bash
    uv sync --all-extras
    ```
    This command will create a virtual environment and install all dependencies (including dev and docs) defined in `pyproject.toml`.

### Quick Reference

Common commands for daily development:

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/pbir_utils

# Check linting
uv run ruff check .

# Format code
uv run ruff format .

# Serve documentation locally
uv run mkdocs serve
```

## Code Style

This project uses `black` for code formatting and `ruff` for linting.

-   **Format code:**
    ```bash
    uv run ruff format .
    ```
-   **Check linting:**
    ```bash
    uv run ruff check .
    ```

## Testing

This project uses `pytest` for testing.

-   **Run tests:**
    ```bash
    uv run pytest
    ```
-   **Run with coverage:**
    ```bash
    uv run pytest --cov=pbir_utils
    ```

## Documentation

Documentation is built with MkDocs.

-   **Serve documentation locally:**
    ```bash
    uv run mkdocs serve
    ```
-   **Build documentation:**
    ```bash
    uv run mkdocs build
    ```

## Pull Request Process

1.  Fork the repo and create your branch from `main`.
2.  If you've added code that should be tested, add tests.
3.  If you've changed APIs, update the documentation.
4.  Ensure the test suite passes.
5.  Make sure your code follows the existing style (run `black` and `ruff`).
6.  Issue that pull request!
