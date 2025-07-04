# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Thought is a Notion CLI tool built with Python that provides database management, deduplication, and external service integration capabilities. It's designed to work with Notion's API to manipulate collections, export data, and sync from external services like Instapaper.

## Development Commands

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_client.py

# Run tests in verbose mode
pytest -v
```

### Code Quality
```bash
# Check code with ruff linter
ruff check .

# Format code with ruff
ruff format .

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Installation & Setup
```bash
# Install in development mode
uv pip install -e ".[dev]"

# Install dependencies only
uv pip install -e .
```

### CLI Usage
```bash
# Main CLI entry point
thought --help

# Example commands
thought dedupe "https://notion.so/your-collection-url"
thought sort "https://notion.so/your-collection-url" --field "tags"
thought sync instapaper bookmarks --target_collection="page_url"
thought tojson "https://notion.so/your-database-url" --output="./exports/"
```

## Architecture

### Core Components

- **CLI Layer** (`cli.py`): Click-based command-line interface with commands for dedupe, sort, sync, export
- **API Client** (`client.py`): Notion API wrapper using the official `notion-client` library
- **Core Logic** (`core.py`): Collection and CollectionView extensions with pandas integration and record linkage for deduplication
- **Service Layer** (`service.py`): Plugin architecture for external service integrations with base classes `GenericService` and `APIService`
- **Settings** (`settings.py`): Environment variable configuration and service registration

### Key Design Patterns

1. **Extension Pattern**: `CollectionExtension` and `CollectionViewExtension` wrap notion-py objects to add functionality
2. **Service Registry**: Dynamic service loading using `SERVICES_REGISTERED` dictionary in settings
3. **Dataclass Architecture**: Heavy use of dataclasses with `@dataclass` decorator for structured data
4. **Pandas Integration**: Core operations convert Notion data to pandas DataFrames for manipulation

### Data Flow

1. CLI commands parse URLs and extract UUIDs using `notion_url_to_uuid()`
2. `NotionAPIClient` handles API communication with official Notion client
3. Collections are wrapped in extension classes for enhanced functionality
4. Record linkage library performs deduplication using exact matching strategies
5. External services sync data through the service registry pattern

### Service Integration

Services are registered in `settings.SERVICES_REGISTERED` and must:
- Inherit from `GenericService` or `APIService`
- Implement required methods (e.g., `authorize()` for API services)
- Be placed in `src/thought/services/` directory
- Follow naming convention: `{service}_{action}` for target collections

### Environment Variables

Required for operation:
- `NOTION_ACCESS_TOKEN`: Notion integration token
- `INSTAPAPER_CONSUMER_ID`, `INSTAPAPER_CONSUMER_SECRET`: For Instapaper sync
- `INSTAPAPER_USER`, `INSTAPAPER_PASS`: Instapaper credentials

## Testing

Uses pytest with fixtures defined in `conftest.py`. Key test patterns:
- `notion_api_client` fixture provides NotionAPIClient instance
- Tests focus on client initialization and API interaction
- Coverage reporting enabled with `--cov=thought`

## Code Style

- Line length: 88 characters (ruff configuration)
- Python 3.11+ target
- Double quotes for strings
- Space indentation
- Pre-commit hooks enforce quality standards
