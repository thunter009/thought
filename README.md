# Thought

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A Notion CLI tool for database management, deduplication, and external service integration. Built with Click and the Notion API.

## Installation

```bash
# Install in development mode
git clone https://github.com/thunter009/thought.git
cd thought
uv sync
```

## Configuration

The tool requires environment variables for API access:

```bash
# Notion API
export NOTION_ACCESS_TOKEN="your_notion_integration_token"

# Instapaper API (optional, for sync feature)
export INSTAPAPER_CONSUMER_ID="your_consumer_id"
export INSTAPAPER_CONSUMER_SECRET="your_consumer_secret"
export INSTAPAPER_USER="your_username"
export INSTAPAPER_PASS="your_password"
```

## Features

* **Collection Management**
  * Deduplicate items in collections using advanced record linkage
  * Sort collections by any field, with support for multi-select value sorting
  * Convert collections to pandas DataFrames for data manipulation

* **Data Export**
  * Export Notion databases to JSON format
  * Export Notion databases to CSV format
  * Customize exported columns and apply filters
  * Option to convert column names to lower snake case

* **Service Integration**
  * Sync data from Instapaper to Notion collections
  * Extensible service architecture for adding new integrations
  * OAuth1 support for secure API authentication

* **Data Processing**
  * Built-in support for pandas DataFrames
  * Advanced record linkage using the `recordlinkage` library
  * Flexible data transformation and cleaning utilities

## Commands

### Deduplication

Remove duplicate items from collections using record linkage:

```bash
# Deduplicate using all fields
thought dedupe "https://notion.so/your-collection-url"

# Deduplicate using specific fields
thought dedupe "https://notion.so/your-collection-url" --field "title" --field "url"
```

### Collection Sorting

Sort collections by any field:

```bash
# Sort by tags (default)
thought sort "https://notion.so/your-collection-url"

# Sort by specific field
thought sort "https://notion.so/your-collection-url" --field "created_time"

# Sort multi-select field values before sorting collection
thought sort "https://notion.so/your-collection-url" --field "tags" --sort_multiselect_values
```

### Data Export

Export databases to JSON or CSV:

```bash
# Export to JSON
thought tojson "https://notion.so/your-database-url" --output="./exports/"

# Export to CSV
thought tocsv "https://notion.so/your-database-url" --output="./exports/"

# Export specific columns
thought tocsv "https://notion.so/your-database-url" --columns "title" --columns "url"

# Convert column names to snake_case
thought tocsv "https://notion.so/your-database-url" --lower-snake-case "Created Time"
```

### Service Integration

Sync data from external services:

```bash
# Sync Instapaper bookmarks (requires target collection to exist)
thought sync instapaper bookmarks --target_collection="https://notion.so/your-page-url"
```

**Note**: The target collection must already exist in Notion with the name pattern `{service}_{action}` (e.g., `instapaper_bookmarks`).

## Development

### Project Structure

```plaintext
src/thought/
├── __init__.py          # Package initialization
├── cli.py              # Click CLI commands
├── client.py           # Notion API client wrapper
├── core.py             # Collection and deduplication logic
├── exceptions.py       # Custom exceptions
├── service.py          # Service registry and base classes
├── settings.py         # Configuration and environment variables
├── utils.py            # Utility functions
└── services/
    └── instapaper.py   # Instapaper service integration
```

### Development Tools

The project uses modern Python tooling:

* [uv](https://github.com/astral-sh/uv) for dependency management
* [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
* [pytest](https://docs.pytest.org/) for testing
* [pre-commit](https://pre-commit.com/) for code quality hooks

### Development Setup

```bash
uv sync --extra dev
```

### Development Commands

```bash
# Run tests
pytest

# Run linter
ruff check .

# Format code
ruff format .

# Clean build artifacts
rm -rf build/ dist/ *.egg-info/
```

### Adding New Services

To add a new service integration:

1. Create a new service class in `src/thought/services/`
2. Inherit from `GenericService` or `APIService`
3. Register the service in `settings.py` under `SERVICES_REGISTERED`
4. Implement required methods and authentication

## Dependencies

Key dependencies include:

* `click` - Command-line interface framework
* `notion-client` - Notion API client
* `pandas` - Data manipulation and analysis
* `recordlinkage` - Advanced deduplication algorithms
* `requests-oauthlib` - OAuth authentication for external services

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
