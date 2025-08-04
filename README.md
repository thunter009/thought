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

* **Data Import**
  * Import Markdown files with YAML frontmatter to Notion databases
  * Support for single file or batch directory imports
  * Smart record matching by ID or title
  * Multiple merge strategies (merge, replace, skip)
  * Dry-run mode for previewing changes
  * Full Markdown syntax support with rich text formatting
  * Project linking via relation properties
  * Automatic user assignment resolution

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

Export databases to JSON or CSV using the unified export command:

```bash
# Export to CSV (default)
thought export "https://notion.so/your-database-url" --output="./exports/"

# Export to JSON
thought export "https://notion.so/your-database-url" --type json --output="./exports/"

# Export specific columns
thought export "https://notion.so/your-database-url" --columns "title" --columns "url"

# Export to CSV with specific columns
thought export "https://notion.so/your-database-url" --type csv --columns "title" --columns "url"

# Convert column names to snake_case
thought export "https://notion.so/your-database-url" --lower-snake-case "Created Time"
```

### Data Import

Import Markdown files into Notion databases:

```bash
# Import a single file
thought import document.md --database "https://notion.so/your-database-url"

# Import all Markdown files from a directory
thought import ./docs/ --database "https://notion.so/your-database-url"

# Import recursively from subdirectories
thought import ./docs/ --database "https://notion.so/your-database-url" --recursive

# Preview import without making changes (dry-run)
thought import ./docs/ --database "https://notion.so/your-database-url" --dry-run

# Update existing pages by title matching
thought import file.md --database "https://notion.so/your-database-url" --identifier title

# Replace content instead of merging
thought import file.md --database "https://notion.so/your-database-url" --mode replace
```

#### Markdown Format

The import feature supports Markdown files with optional YAML frontmatter:

```markdown
---
title: My Document
tags:
  - documentation
  - guide
priority: 5
completed: false
due_date: 2024-12-31
assignee: john@example.com
project: Website Redesign
notion_id: optional-page-id-for-updates
---

# My Document

Content with **bold**, *italic*, `code`, and [links](https://example.com).

## Features

- Bullet lists
- Code blocks with syntax highlighting
- Tables and quotes
- [ ] Checkboxes that convert to Notion to-do blocks
```

#### Import Options

* **--database**: Target Notion database URL (required)
* **--recursive**: Include files from subdirectories
* **--mode**: How to handle existing pages
  * `merge` (default): Merge new content with existing
  * `replace`: Replace all existing content
  * `skip`: Skip updates to existing pages
* **--identifier**: How to match existing pages
  * `auto` (default): Try ID first, then title
  * `id`: Match by notion_id in frontmatter
  * `title`: Match by title
* **--dry-run**: Preview changes without applying them

#### Special Property Handling

The import feature automatically handles certain property types with special processing:

##### User Assignment (People Properties)
When your database has a "people" property type and your frontmatter includes `assignee` or `assigned_to`:
- The tool automatically looks up users by name or email
- Supports single assignee: `assignee: john@example.com`
- Supports multiple assignees: `assignee: ["john@example.com", "jane@example.com"]`
- Users not found in the workspace are skipped with a warning

##### Project Linking (Relation Properties)
When your database has a "relation" property type and your frontmatter includes `project` or `projects`:
- The tool automatically searches for matching pages/databases by name
- Supports single project: `project: Website Redesign`
- Supports multiple projects: `projects: ["Project Alpha", "Project Beta"]`
- Uses case-insensitive matching with exact match preference
- Projects not found are skipped with a warning

##### Property Type Conversions
The tool automatically converts frontmatter values to appropriate Notion property types:
- **Text/Title**: String values → Rich text
- **Number**: Numeric values → Number property
- **Checkbox**: Boolean values → Checkbox property
- **Select/Status**: String values → Select/Status options
- **Multi-select**: Arrays → Multi-select options
- **Date**: Date strings → Date property
- **Tags**: Arrays → Multi-select (if property name is "Tags")

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
├── markdown_parser.py  # Markdown parsing with frontmatter
├── notion_converter.py # Markdown to Notion block conversion
├── service.py          # Service registry and base classes
├── settings.py         # Configuration and environment variables
├── utils.py            # Utility functions
└── services/
    ├── instapaper.py   # Instapaper service integration
    └── markdown_import.py  # Markdown import service
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
* `python-frontmatter` - YAML frontmatter parsing
* `mistune` - Markdown parsing and AST generation

## Troubleshooting

### Import Issues

#### Missing properties warning

* The import tool will warn if your Markdown frontmatter contains properties not in the target database
* These properties will be skipped during import
* To fix: Add the missing properties to your Notion database first

#### Failed to parse Markdown

* Ensure your Markdown syntax is valid
* Check for unclosed code blocks or malformed tables
* The parser validates syntax before import

#### Pages not updating

* Check the identifier strategy matches your use case
* Use `--identifier id` if using `notion_id` in frontmatter
* Use `--identifier title` for title-based matching
* Use `--dry-run` to preview what will be matched

#### Import fails with API errors

* Verify your `NOTION_ACCESS_TOKEN` is set correctly
* Ensure the integration has access to the target database
* Check that the database URL is correct (not a page URL)

#### Content not merging correctly

* Use section markers `<!-- notion-section: section-name -->` for precise merging
* Try `--mode replace` to completely replace content
* Use `--mode skip` to only update properties

### Common Patterns

#### Bulk import from documentation

```bash
# Import all docs with metadata preservation
thought import ./docs --database "..." --recursive --dry-run

# After preview, run actual import
thought import ./docs --database "..." --recursive
```

#### Update existing tickets

```bash
# Update by ID with content replacement
thought import ticket.md --database "..." --identifier id --mode replace
```

#### Import tickets with project assignments

```bash
# Import tickets that link to projects via relation properties
thought import tickets/ --database "..." --recursive

# Example ticket frontmatter:
# ---
# title: Fix authentication bug
# status: In Progress
# assignee: developer@company.com
# project: Website Redesign
# tags: [bug, high-priority]
# ---
```

#### Import with specific properties only

* Remove unwanted properties from frontmatter before import
* The tool maps frontmatter 1:1 to Notion properties

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
