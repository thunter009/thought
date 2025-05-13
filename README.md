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

* **Collection Management**
  * Deduplicate items in collections using flexible comparison fields
  * Sort collections by any field, with support for multi-select value sorting
  * Convert collections to pandas DataFrames for data manipulation

* **Data Export**
  * Export Notion databases to JSON format
  * Export Notion databases to CSV format
  * Customize exported columns and apply filters
  * Option to convert column names to lower snake case

* **Service Integration**
  * Sync data from external services (e.g., Instapaper)
  * Extensible service architecture for adding new integrations
  * OAuth support for secure API authentication

* **Data Processing**
  * Built-in support for pandas DataFrames
  * Advanced record linkage for deduplication
  * Flexible data transformation and cleaning utilities

## Example Commands

```bash
# Deduplicate items in a collection
thought dedupe "https://notion.so/your-collection-url"

# Sort a collection by a specific field
thought sort "https://notion.so/your-collection-url" --field "tags"

# Sync data from external services (e.g. Instapaper)
thought sync instapaper bookmarks --target_collection="https://notion.so/your-page-url"

# Export database to JSON
thought tojson "https://notion.so/your-database-url" --output="data.json"

# Export database to CSV
thought tocsv "https://notion.so/your-database-url" --output="data.csv"
```

## Development

The project uses modern Python tooling:

* [uv](https://github.com/astral-sh/uv) for dependency management
* [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
* [MyPy](https://mypy.readthedocs.io/) for type checking
* [pytest](https://docs.pytest.org/) for testing

### Development Commands

```bash
# Run tests
pytest

# Run linter
ruff check .

# Run type checker
mypy .

# Format code
ruff format .

# Clean build artifacts
rm -rf build/ dist/ *.egg-info/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

For full documentation, visit [thought.readthedocs.io](https://thought.readthedocs.io/).
