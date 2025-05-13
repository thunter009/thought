# Thought

[![PyPI version](https://img.shields.io/pypi/v/thought.svg)](https://pypi.python.org/pypi/thought)
[![Documentation Status](https://readthedocs.org/projects/thought/badge/?version=latest)](https://thought.readthedocs.io/en/latest/?badge=latest)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Notion CLI using Notion's API via [notion-sdk-py](https://github.com/ramnes/notion-sdk-py) and Click.

## Installation

```bash
# Install with uv
uv pip install thought

# Install in development mode
git clone https://github.com/thunter009/thought.git
cd thought
uv pip install -e ".[dev]"
```

## Features

* TODO

## Development

The project uses modern Python tooling:

* [uv](https://github.com/astral-sh/uv) for dependency management
* [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
* [MyPy](https://mypy.readthedocs.io/) for type checking
* [pytest](https://docs.pytest.org/) for testing

### Development Commands

```bash
# Run tests
thought dev test

# Run linter
thought dev lint

# Run type checker
thought dev typecheck

# Format code
thought dev format

# Clean build artifacts
thought dev clean
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

For full documentation, visit [thought.readthedocs.io](https://thought.readthedocs.io/).
