"""Tests for the Markdown import service."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from thought.markdown_parser import ParsedMarkdown
from thought.services.markdown_import import (
    BatchImportResult,
    ImportResult,
    MarkdownImportService,
)

# Test constants
EXPECTED_FILE_COUNT = 2
EXPECTED_PRIORITY = 5
EXPECTED_PRIORITY_FLOAT = 3.0
EXPECTED_BLOCK_DELETE_COUNT = 2


@pytest.fixture
def mock_notion_client():
    """Create a mock Notion client."""
    mock = Mock()
    mock.client = MagicMock()
    return mock


@pytest.fixture
def import_service():
    """Create a MarkdownImportService with mocked dependencies."""
    # Create mock objects
    mock_client = Mock()
    mock_client.client = MagicMock()
    mock_parser = Mock()
    mock_converter = Mock()

    # Configure parser to return ParsedMarkdown by default
    mock_parser.parse_file.return_value = ParsedMarkdown(
        frontmatter={}, content="", sections=[], file_path=Path("test.md")
    )

    # Configure converter to return empty blocks by default
    mock_converter.markdown_to_blocks.return_value = []

    # Create the service and directly set the mocked dependencies
    service = MarkdownImportService.__new__(MarkdownImportService)
    service._type = "markdown_import"
    service.client = mock_client
    service.parser = mock_parser
    service.converter = mock_converter

    return service


@pytest.fixture
def sample_parsed_markdown():
    """Create a sample ParsedMarkdown object."""
    return ParsedMarkdown(
        frontmatter={
            "title": "Test Document",
            "tags": ["test", "import"],
            "priority": 5,
        },
        content="# Test Document\n\nThis is test content.",
        sections=[],
        file_path=Path("test.md"),
    )


class TestMarkdownImportService:
    """Test MarkdownImportService functionality."""

    def test_import_file_create_new(self, import_service, tmp_path):
        """Test importing a file that creates a new page."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("""---
title: New Document
tags:
  - test
---

# New Document

Content here.
""")

        # Configure parser to return parsed content
        import_service.parser.parse_file.return_value = ParsedMarkdown(
            frontmatter={"title": "New Document", "tags": ["test"]},
            content="# New Document\n\nContent here.",
            sections=[],
            file_path=test_file,
        )

        # Configure converter
        import_service.converter.markdown_to_blocks.return_value = [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"text": {"content": "New Document"}}]},
            },
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": "Content here."}}]},
            },
        ]

        # Mock API responses
        import_service.client.client.databases.query = MagicMock(
            return_value={"results": []}
        )
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Title": {"type": "title"},
                    "Tags": {"type": "multi_select"},
                }
            }
        )
        import_service.client.client.pages.create = MagicMock(
            return_value={"id": "page-123"}
        )

        # Import file
        result = import_service.import_file(
            test_file,
            database_id="db-123",
            mode="merge",
            identifier="auto",
            dry_run=False,
        )

        # Verify result
        assert result.success
        assert result.page_id == "page-123"
        assert result.action == "created"
        assert result.file_path == test_file

        # Verify API calls
        import_service.client.client.pages.create.assert_called_once()

    def test_import_file_update_existing(self, import_service, tmp_path):
        """Test importing a file that updates an existing page."""
        # Create test file with notion_id
        test_file = tmp_path / "test.md"
        test_file.write_text("""---
title: Existing Document
notion_id: existing-page-123
---

# Updated Content
""")

        # Configure parser
        import_service.parser.parse_file.return_value = ParsedMarkdown(
            frontmatter={
                "title": "Existing Document",
                "notion_id": "existing-page-123",
            },
            content="# Updated Content",
            sections=[],
            file_path=test_file,
        )

        # Configure converter
        import_service.converter.markdown_to_blocks.return_value = [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"text": {"content": "Updated Content"}}]},
            }
        ]

        # Mock finding existing page
        import_service.client.client.pages.retrieve = MagicMock(
            return_value={
                "id": "existing-page-123",
                "parent": {"database_id": "db-123"},
            }
        )
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={"properties": {"Title": {"type": "title"}}}
        )
        import_service.client.client.pages.update = MagicMock(
            return_value={"id": "existing-page-123"}
        )
        import_service.client.client.blocks.children.list = MagicMock(
            return_value={"results": [], "has_more": False}
        )
        import_service.client.client.blocks.children.append = MagicMock()

        # Import file
        result = import_service.import_file(
            test_file,
            database_id="db-123",
            mode="merge",
            identifier="auto",
            dry_run=False,
        )

        # Verify result
        assert result.success
        assert result.page_id == "existing-page-123"
        assert result.action == "updated"

    def test_import_file_dry_run(self, import_service, tmp_path):
        """Test dry-run mode."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Mock API responses
        import_service.client.client.databases.query = MagicMock(
            return_value={"results": []}
        )
        import_service.client.client.pages.create = MagicMock()

        # Import with dry-run
        result = import_service.import_file(
            test_file, database_id="db-123", dry_run=True
        )

        # Verify result
        assert result.success
        assert result.action == "would create"

        # Verify no actual changes were made
        import_service.client.client.pages.create.assert_not_called()

    def test_import_file_error_handling(self, import_service, tmp_path):
        """Test error handling during import."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Mock API error
        import_service.parser.parse_file = Mock(side_effect=Exception("Parse error"))

        # Import file
        result = import_service.import_file(test_file, database_id="db-123")

        # Verify error result
        assert not result.success
        assert "Parse error" in result.error

    def test_import_directory(self, import_service, tmp_path):
        """Test importing multiple files from a directory."""
        # Create test files
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.md").write_text("# File 2")
        (tmp_path / "other.txt").write_text("Not markdown")

        # Mock successful imports
        import_service.import_file = Mock(
            side_effect=[
                ImportResult(
                    file_path=tmp_path / "file1.md",
                    success=True,
                    page_id="page-1",
                    action="created",
                ),
                ImportResult(
                    file_path=tmp_path / "file2.md",
                    success=True,
                    page_id="page-2",
                    action="created",
                ),
            ]
        )

        # Import directory
        result = import_service.import_directory(
            tmp_path, database_id="db-123", recursive=False
        )

        # Verify result
        assert isinstance(result, BatchImportResult)
        assert result.total_files == EXPECTED_FILE_COUNT
        assert result.successful == EXPECTED_FILE_COUNT
        assert result.failed == 0
        assert result.all_successful

    def test_import_directory_recursive(self, import_service, tmp_path):
        """Test recursive directory import."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "root.md").write_text("# Root")
        (subdir / "nested.md").write_text("# Nested")

        # Mock imports
        import_service.import_file = Mock(
            return_value=ImportResult(
                file_path=Path("test.md"),
                success=True,
                page_id="page-1",
                action="created",
            )
        )

        # Import recursively
        result = import_service.import_directory(
            tmp_path, database_id="db-123", recursive=True
        )

        # Should find both files
        assert result.total_files == EXPECTED_FILE_COUNT
        assert import_service.import_file.call_count == EXPECTED_FILE_COUNT

    def test_find_existing_page_by_id(self, import_service, sample_parsed_markdown):
        """Test finding existing page by notion_id."""
        sample_parsed_markdown.frontmatter["notion_id"] = "page-123"

        import_service.client.client.pages.retrieve = MagicMock(
            return_value={"id": "page-123"}
        )

        result = import_service._find_existing_page(
            sample_parsed_markdown, database_id="db-123", identifier="id"
        )

        assert result == {"id": "page-123"}
        import_service.client.client.pages.retrieve.assert_called_once_with(
            page_id="page-123"
        )

    def test_find_existing_page_by_title(self, import_service, sample_parsed_markdown):
        """Test finding existing page by title."""
        import_service.client.client.databases.query = MagicMock(
            return_value={"results": [{"id": "found-page"}]}
        )

        result = import_service._find_existing_page(
            sample_parsed_markdown, database_id="db-123", identifier="title"
        )

        assert result == {"id": "found-page"}

    def test_create_page_with_properties(self, import_service, sample_parsed_markdown):
        """Test creating a page with frontmatter properties."""
        # Mock database schema
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Name": {"type": "title"},
                    "Tags": {"type": "multi_select"},
                    "Priority": {"type": "number"},
                    "Status": {"type": "status"},
                }
            }
        )
        import_service.client.client.pages.create = MagicMock(
            return_value={"id": "new-page-123"}
        )

        page_id = import_service._create_page("db-123", sample_parsed_markdown)

        assert page_id == "new-page-123"

        # Verify properties were set
        call_args = import_service.client.client.pages.create.call_args
        properties = call_args[1]["properties"]
        # Name should be set from title
        assert "Name" in properties
        assert properties["Name"]["title"][0]["text"]["content"] == "Test Document"
        assert "Tags" in properties
        assert properties["Tags"]["multi_select"] == [
            {"name": "test"},
            {"name": "import"},
        ]
        assert "Priority" in properties
        assert properties["Priority"]["number"] == EXPECTED_PRIORITY

    def test_validate_database_schema(self, import_service, tmp_path):
        """Test database schema validation."""
        # Create sample files
        test_file = tmp_path / "test1.md"
        test_file.write_text("""---
title: Test
custom_field: Value
---
# Test
""")

        # Configure parser to return parsed content
        import_service.parser.parse_file.return_value = ParsedMarkdown(
            frontmatter={"title": "Test", "custom_field": "Value"},
            content="# Test",
            sections=[],
            file_path=test_file,
        )

        # Configure converter to return properties (still needed for backward compatibility)
        import_service.converter.frontmatter_to_properties.return_value = {
            "Title": {"rich_text": [{"text": {"content": "Test"}}]},
            "Custom Field": {"rich_text": [{"text": {"content": "Value"}}]},
        }

        # Mock the _convert_properties_with_schema method used in validation
        import_service._convert_properties_with_schema = MagicMock(
            return_value={"Title": {"title": [{"text": {"content": "Test"}}]}}
        )

        # Mock database schema
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Title": {"type": "title"},
                    "Tags": {"type": "multi_select"},
                }
            }
        )

        valid, warnings = import_service.validate_database_schema(
            "db-123", [tmp_path / "test1.md"]
        )

        assert valid
        assert len(warnings) > 0
        assert "custom_field" in warnings[0]

    def test_mode_replace(self, import_service, sample_parsed_markdown):
        """Test replace mode for updates."""
        # Configure converter to return blocks
        import_service.converter.markdown_to_blocks.return_value = [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"text": {"content": "Test Document"}}]},
            }
        ]

        import_service.client.client.pages.retrieve = MagicMock(
            return_value={"parent": {"database_id": "db-123"}}
        )
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Title": {"type": "title"},
                    "Tags": {"type": "multi_select"},
                    "Priority": {"type": "number"},
                }
            }
        )
        import_service.client.client.pages.update = MagicMock()
        import_service.client.client.blocks.children.list = MagicMock(
            return_value={
                "results": [{"id": "block-1"}, {"id": "block-2"}],
                "has_more": False,
            }
        )
        import_service.client.client.blocks.delete = MagicMock()
        import_service.client.client.blocks.children.append = MagicMock()

        import_service._update_page("page-123", sample_parsed_markdown, mode="replace")

        # Should delete existing blocks
        assert (
            import_service.client.client.blocks.delete.call_count
            == EXPECTED_BLOCK_DELETE_COUNT
        )

        # Should add new blocks
        import_service.client.client.blocks.children.append.assert_called()

    def test_mode_skip(self, import_service, sample_parsed_markdown):
        """Test skip mode for updates."""
        # Configure converter to return blocks
        import_service.converter.markdown_to_blocks.return_value = [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"text": {"content": "Test Document"}}]},
            }
        ]

        import_service.client.client.pages.retrieve = MagicMock(
            return_value={"parent": {"database_id": "db-123"}}
        )
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Title": {"type": "title"},
                    "Tags": {"type": "multi_select"},
                    "Priority": {"type": "number"},
                }
            }
        )
        import_service.client.client.pages.update = MagicMock()
        import_service.client.client.blocks.children.append = MagicMock()

        import_service._update_page("page-123", sample_parsed_markdown, mode="skip")

        # Should not update properties or content in skip mode
        import_service.client.client.pages.update.assert_not_called()
        import_service.client.client.blocks.children.append.assert_not_called()

    def test_mode_merge(self, import_service, sample_parsed_markdown):
        """Test merge mode for updates (currently same as replace)."""
        # Configure converter to return blocks
        import_service.converter.markdown_to_blocks.return_value = [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"text": {"content": "Test Document"}}]},
            }
        ]

        import_service.client.client.pages.retrieve = MagicMock(
            return_value={"parent": {"database_id": "db-123"}}
        )
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Title": {"type": "title"},
                    "Tags": {"type": "multi_select"},
                    "Priority": {"type": "number"},
                }
            }
        )
        import_service.client.client.pages.update = MagicMock()
        import_service.client.client.blocks.children.list = MagicMock(
            return_value={
                "results": [{"id": "block-1"}, {"id": "block-2"}],
                "has_more": False,
            }
        )
        import_service.client.client.blocks.delete = MagicMock()
        import_service.client.client.blocks.children.append = MagicMock()

        import_service._update_page("page-123", sample_parsed_markdown, mode="merge")

        # Should update properties
        import_service.client.client.pages.update.assert_called_once()

        # Should delete existing blocks (merge currently works like replace)
        assert (
            import_service.client.client.blocks.delete.call_count
            == EXPECTED_BLOCK_DELETE_COUNT
        )

        # Should add new blocks
        import_service.client.client.blocks.children.append.assert_called()

    def test_property_filtering(self, import_service, sample_parsed_markdown):
        """Test that only existing database properties are used."""
        # Add some properties that don't exist in the database
        sample_parsed_markdown.frontmatter.update(
            {
                "non_existent_field": "value",
                "another_missing": 123,
                "completed": True,  # This one doesn't exist in our mock database
            }
        )

        # Mock database schema with limited properties
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Name": {"type": "title"},  # Different from "Title"
                    "Tags": {"type": "multi_select"},
                    # Note: Priority, completed, and other fields are missing
                }
            }
        )
        import_service.client.client.pages.create = MagicMock(
            return_value={"id": "new-page-123"}
        )

        import_service._create_page("db-123", sample_parsed_markdown)

        # Verify only valid properties were included
        call_args = import_service.client.client.pages.create.call_args
        properties = call_args[1]["properties"]

        # Should have Name (title) and Tags, but not the others
        assert "Name" in properties  # Title property from the DB
        assert properties["Name"]["title"][0]["text"]["content"] == "Test Document"
        assert "Tags" in properties
        assert properties["Tags"]["multi_select"] == [
            {"name": "test"},
            {"name": "import"},
        ]
        assert "Priority" not in properties  # Not in DB schema
        assert "Non Existent Field" not in properties
        assert "Another Missing" not in properties
        assert "Completed" not in properties

    def test_case_insensitive_property_matching(
        self, import_service, sample_parsed_markdown
    ):
        """Test that properties match case-insensitively."""
        sample_parsed_markdown.frontmatter = {
            "title": "Test Doc",
            "TAGS": ["tag1", "tag2"],  # Uppercase in frontmatter
            "priority": 3,
        }

        # Mock database with different casing
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {
                    "Title": {"type": "title"},
                    "tags": {"type": "multi_select"},  # Lowercase in DB
                    "Priority": {"type": "number"},
                }
            }
        )
        import_service.client.client.pages.create = MagicMock(
            return_value={"id": "new-page-123"}
        )

        import_service._create_page("db-123", sample_parsed_markdown)

        # Verify properties were matched despite case differences
        call_args = import_service.client.client.pages.create.call_args
        properties = call_args[1]["properties"]

        assert "Title" in properties
        assert properties["Title"]["title"][0]["text"]["content"] == "Test Doc"
        assert "tags" in properties  # Should use DB's casing
        assert properties["tags"]["multi_select"] == [
            {"name": "tag1"},
            {"name": "tag2"},
        ]
        assert "Priority" in properties
        assert properties["Priority"]["number"] == EXPECTED_PRIORITY_FLOAT

    def test_status_property_conversion(self, import_service, sample_parsed_markdown):
        """Test that status properties are correctly converted."""
        sample_parsed_markdown.frontmatter = {
            "title": "Test Doc",
            "status": "In Progress",
        }

        # Mock database with status property
        import_service.client.client.databases.retrieve = MagicMock(
            return_value={
                "properties": {"Title": {"type": "title"}, "Status": {"type": "status"}}
            }
        )
        import_service.client.client.pages.create = MagicMock(
            return_value={"id": "new-page-123"}
        )

        import_service._create_page("db-123", sample_parsed_markdown)

        # Verify status property was set correctly
        call_args = import_service.client.client.pages.create.call_args
        properties = call_args[1]["properties"]

        assert "Title" in properties
        assert "Status" in properties
        assert properties["Status"]["status"]["name"] == "In Progress"
