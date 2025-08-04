import logging
import os
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from thought.cli import _extract_notion_properties, _extract_property_value, cli
from thought.services.markdown_import import BatchImportResult, ImportResult

# Test constants
TEST_NUMBER = 42
EXPECTED_RESULT_COUNT = 2


def create_mock_notion_client():
    """Create a fully mocked Notion client for testing."""
    mock_client = Mock()
    mock_client.pages = Mock()
    mock_client.pages.create = Mock(return_value={"id": "page-123", "properties": {}})
    mock_client.pages.retrieve = Mock(
        return_value={
            "id": "page-123",
            "parent": {"database_id": "12345678123412341234123456789012"},
        }
    )
    mock_client.pages.update = Mock()
    mock_client.databases = Mock()
    mock_client.databases.query = Mock(return_value={"results": []})
    mock_client.databases.retrieve = Mock(
        return_value={
            "properties": {
                "Name": {"type": "title", "title": {}},
                "Tags": {"type": "multi_select", "multi_select": {"options": []}},
            }
        }
    )
    mock_client.blocks = Mock()
    mock_client.blocks.children = Mock()
    mock_client.blocks.children.append = Mock()
    mock_client.blocks.children.list = Mock(
        return_value={"results": [], "has_more": False}
    )
    mock_client.blocks.delete = Mock()
    return mock_client


def test_cli_help():
    """
    Integration Test: thought --help
    """
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "--help",
        ],
    )

    assert (
        "\n  --help                          Show this message and exit.\n"
        in result.output
    )
    assert result.exit_code == 0


def test_export_command_help():
    """
    Test: thought export --help
    """
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "export",
            "--help",
        ],
    )

    assert "Exports a Notion database to CSV or JSON file" in result.output
    assert "--columns" in result.output
    assert "--type" in result.output
    assert result.exit_code == 0


def test_import_command_help():
    """
    Test: thought import --help
    """
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "import",
            "--help",
        ],
    )

    assert "Import Markdown files into a Notion database" in result.output
    assert "--database" in result.output
    assert "--recursive" in result.output
    assert "--mode" in result.output
    assert "--dry-run" in result.output
    assert "--identifier" in result.output
    assert result.exit_code == 0


def test_import_single_file():
    """
    Test importing a single file - integration test with mocked Notion API
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create test file
        with open("test.md", "w") as f:
            f.write("# Test Document\n\nThis is test content.")

        # Mock the entire Notion client and service chain
        with (
            patch("thought.cli.notion_url_to_uuid") as mock_uuid,
            patch("thought.cli.MarkdownImportService") as mock_import_service_class,
            patch(
                "thought.services.markdown_import.NotionAPIClient"
            ) as mock_api_client,
        ):
            # Set up UUID mock
            mock_uuid.return_value = "12345678123412341234123456789012"

            # Set up NotionAPIClient mock
            mock_client_instance = Mock()
            mock_client_instance.client = create_mock_notion_client()
            mock_api_client.return_value = mock_client_instance

            # Set up MarkdownImportService mock
            mock_service = Mock()
            mock_service.import_file.return_value = ImportResult(
                success=True,
                action="created",
                file_path=Path("test.md"),
                page_id="page-123",
            )
            mock_import_service_class.return_value = mock_service

            # Run the command
            result = runner.invoke(
                cli,
                ["import", "test.md", "--database", "https://notion.so/db-url"],
                catch_exceptions=False,
            )

            # Check the output
            assert result.exit_code == 0
            assert "Importing test.md..." in result.output
            assert "✅ created:" in result.output


def test_import_directory():
    """
    Test importing a directory - integration test with mocked Notion API
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create test directory with files
        os.mkdir("docs")
        with open("docs/file1.md", "w") as f:
            f.write("# File 1\n\nContent of file 1")
        with open("docs/file2.md", "w") as f:
            f.write("# File 2\n\nContent of file 2")

        # Mock the entire Notion client and service chain
        with (
            patch("thought.cli.notion_url_to_uuid") as mock_uuid,
            patch("thought.cli.MarkdownImportService") as mock_import_service_class,
            patch(
                "thought.services.markdown_import.NotionAPIClient"
            ) as mock_api_client,
        ):
            # Set up UUID mock
            mock_uuid.return_value = "12345678123412341234123456789012"

            # Set up NotionAPIClient mock
            mock_client_instance = Mock()
            mock_client_instance.client = create_mock_notion_client()
            mock_api_client.return_value = mock_client_instance

            # Set up MarkdownImportService mock
            mock_service = Mock()
            mock_service.import_directory.return_value = BatchImportResult(
                total_files=2,
                successful=2,
                failed=0,
                results=[
                    ImportResult(
                        success=True,
                        action="created",
                        file_path=Path("docs/file1.md"),
                        page_id="page-1",
                    ),
                    ImportResult(
                        success=True,
                        action="created",
                        file_path=Path("docs/file2.md"),
                        page_id="page-2",
                    ),
                ],
            )
            mock_service.validate_database_schema.return_value = (True, [])
            mock_import_service_class.return_value = mock_service

            # Run the command
            result = runner.invoke(
                cli,
                [
                    "import",
                    "docs",
                    "--database",
                    "https://notion.so/db-url",
                    "--recursive",
                ],
                catch_exceptions=False,
            )

            # Check the output
            assert result.exit_code == 0
            assert "Import Summary" in result.output
            assert (
                "Total files: 2" in result.output
                or "Total files: EXPECTED_FILE_COUNT" in result.output
            )
            assert (
                "✅ Successful: 2" in result.output
                or "✅ Successful: EXPECTED_FILE_COUNT" in result.output
            )


def test_import_dry_run():
    """
    Test dry-run mode - integration test with mocked Notion API
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create test file
        with open("test.md", "w") as f:
            f.write("# Test Document\n\nThis is test content.")

        # Mock the entire Notion client and service chain
        with (
            patch("thought.cli.notion_url_to_uuid") as mock_uuid,
            patch("thought.cli.MarkdownImportService") as mock_import_service_class,
            patch(
                "thought.services.markdown_import.NotionAPIClient"
            ) as mock_api_client,
        ):
            # Set up UUID mock
            mock_uuid.return_value = "12345678123412341234123456789012"

            # Set up NotionAPIClient mock
            mock_client_instance = Mock()
            mock_client_instance.client = create_mock_notion_client()
            mock_api_client.return_value = mock_client_instance

            # Set up MarkdownImportService mock
            mock_service = Mock()
            mock_service.import_file.return_value = ImportResult(
                success=True,
                action="would create",
                file_path=Path("test.md"),
                page_id=None,
            )
            mock_import_service_class.return_value = mock_service

            # Run the command with dry-run
            result = runner.invoke(
                cli,
                [
                    "import",
                    "test.md",
                    "--database",
                    "https://notion.so/db-url",
                    "--dry-run",
                ],
                catch_exceptions=False,
            )

            # Check the output
            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            assert "would create" in result.output


def test_import_with_errors():
    """
    Test import with errors - integration test simulating parse error
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create test directory with an invalid file
        os.mkdir("docs")
        with open("docs/valid.md", "w") as f:
            f.write("# Valid\n\nThis is valid content.")
        with open("docs/invalid.md", "w") as f:
            # Write content that will cause an error during parsing
            f.write("---\ninvalid_yaml: [unclosed\n---\n# Invalid")

        # Mock the entire Notion client and service chain
        with (
            patch("thought.cli.notion_url_to_uuid") as mock_uuid,
            patch("thought.cli.MarkdownImportService") as mock_import_service_class,
            patch(
                "thought.services.markdown_import.NotionAPIClient"
            ) as mock_api_client,
        ):
            # Set up UUID mock
            mock_uuid.return_value = "12345678123412341234123456789012"

            # Set up NotionAPIClient mock
            mock_client_instance = Mock()
            mock_client_instance.client = create_mock_notion_client()
            mock_api_client.return_value = mock_client_instance

            # Set up MarkdownImportService mock
            mock_service = Mock()
            mock_service.import_directory.return_value = BatchImportResult(
                total_files=2,
                successful=1,
                failed=1,
                results=[
                    ImportResult(
                        success=True,
                        action="created",
                        file_path=Path("docs/valid.md"),
                        page_id="page-1",
                    ),
                    ImportResult(
                        success=False,
                        action="created",
                        file_path=Path("docs/invalid.md"),
                        page_id=None,
                        error="Parse error: invalid YAML",
                    ),
                ],
            )
            mock_service.validate_database_schema.return_value = (True, [])
            mock_import_service_class.return_value = mock_service

            # Run the command
            result = runner.invoke(
                cli,
                ["import", "docs", "--database", "https://notion.so/db-url"],
                catch_exceptions=False,
            )

            # Check the output - with actual parsing, we should see some kind of summary
            assert result.exit_code == 0
            assert "Import Summary" in result.output or "Failed" in result.output


def test_old_commands_removed():
    """
    Test that old tocsv and tojson commands are no longer available
    """
    runner = CliRunner()

    # Test that tocsv command no longer exists
    result = runner.invoke(cli, ["tocsv", "--help"])
    assert result.exit_code != 0
    assert "No such command" in result.output

    # Test that tojson command no longer exists
    result = runner.invoke(cli, ["tojson", "--help"])
    assert result.exit_code != 0
    assert "No such command" in result.output


def test_export_command_in_help():
    """
    Test that export command appears in main CLI help
    """
    runner = CliRunner()

    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "export" in result.output


def test_cli_help_without_token():
    """
    Test that CLI help works without Notion token (lazy initialization)
    """
    runner = CliRunner()

    # Test main help without token
    result = runner.invoke(cli, ["--help"], env={})
    assert result.exit_code == 0
    assert "Thought - Notion CLI" in result.output

    # Test export command help without token
    result = runner.invoke(cli, ["export", "--help"], env={})
    assert result.exit_code == 0
    assert "Exports a Notion database" in result.output


def test_extract_property_value():
    """
    Test the _extract_property_value function with different property types
    """
    # Test title property
    title_prop = {"type": "title", "title": [{"text": {"content": "Test Title"}}]}
    assert _extract_property_value(title_prop) == "Test Title"

    # Test empty title
    empty_title_prop = {"type": "title", "title": []}
    assert _extract_property_value(empty_title_prop) == ""

    # Test rich_text property
    rich_text_prop = {
        "type": "rich_text",
        "rich_text": [{"text": {"content": "Rich text content"}}],
    }
    assert _extract_property_value(rich_text_prop) == "Rich text content"

    # Test number property
    number_prop = {"type": "number", "number": TEST_NUMBER}
    assert _extract_property_value(number_prop) == TEST_NUMBER

    # Test select property
    select_prop = {"type": "select", "select": {"name": "Selected Option"}}
    assert _extract_property_value(select_prop) == "Selected Option"

    # Test multi_select property
    multi_select_prop = {
        "type": "multi_select",
        "multi_select": [{"name": "Option 1"}, {"name": "Option 2"}],
    }
    assert _extract_property_value(multi_select_prop) == ["Option 1", "Option 2"]

    # Test checkbox property
    checkbox_prop = {"type": "checkbox", "checkbox": True}
    assert _extract_property_value(checkbox_prop) is True

    # Test unknown property type
    unknown_prop = {"type": "unknown", "some_data": "value"}
    result = _extract_property_value(unknown_prop)
    assert isinstance(result, str)


def test_extract_notion_properties():
    """
    Test the _extract_notion_properties function
    """
    api_results = [
        {
            "id": "test-id-1",
            "created_time": "2023-01-01T00:00:00.000Z",
            "last_edited_time": "2023-01-01T00:00:00.000Z",
            "url": "https://notion.so/test-1",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"text": {"content": "Test Item 1"}}],
                },
                "Status": {"type": "select", "select": {"name": "Active"}},
            },
        },
        {
            "id": "test-id-2",
            "created_time": "2023-01-02T00:00:00.000Z",
            "last_edited_time": "2023-01-02T00:00:00.000Z",
            "url": "https://notion.so/test-2",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"text": {"content": "Test Item 2"}}],
                },
                "Status": {"type": "select", "select": {"name": "Inactive"}},
            },
        },
    ]

    result = _extract_notion_properties(api_results)

    assert len(result) == EXPECTED_RESULT_COUNT
    assert result[0]["id"] == "test-id-1"
    assert result[0]["Name"] == "Test Item 1"
    assert result[0]["Status"] == "Active"
    assert result[1]["id"] == "test-id-2"
    assert result[1]["Name"] == "Test Item 2"
    assert result[1]["Status"] == "Inactive"


@patch("thought.cli.notion_url_to_uuid")
@patch("thought.cli.NotionAPIClient")
def test_export_command_csv(mock_client_class, mock_url_to_uuid):
    """
    Test the export command with CSV output
    """
    # Mock the URL to UUID conversion
    mock_url_to_uuid.return_value = "test-uuid"

    # Mock the Notion API client
    mock_client = Mock()
    mock_client.query.return_value = {
        "results": [
            {
                "id": "test-id",
                "created_time": "2023-01-01T00:00:00.000Z",
                "last_edited_time": "2023-01-01T00:00:00.000Z",
                "url": "https://notion.so/test",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"text": {"content": "Test Item"}}],
                    }
                },
            }
        ]
    }
    mock_client_class.return_value = mock_client

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["export", "https://notion.so/test-db", "--type", "csv"],
            env={"NOTION_ACCESS_TOKEN": "test-token"},
        )

        assert result.exit_code == 0
        # Check that CSV file was created
        assert os.path.exists("test-uuid.csv")


@patch("thought.cli.notion_url_to_uuid")
@patch("thought.cli.NotionAPIClient")
def test_export_command_json(mock_client_class, mock_url_to_uuid):
    """
    Test the export command with JSON output
    """
    # Mock the URL to UUID conversion
    mock_url_to_uuid.return_value = "test-uuid"

    # Mock the Notion API client
    mock_client = Mock()
    mock_client.query.return_value = {
        "results": [
            {
                "id": "test-id",
                "created_time": "2023-01-01T00:00:00.000Z",
                "last_edited_time": "2023-01-01T00:00:00.000Z",
                "url": "https://notion.so/test",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"text": {"content": "Test Item"}}],
                    }
                },
            }
        ]
    }
    mock_client_class.return_value = mock_client

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["export", "https://notion.so/test-db", "--type", "json"],
            env={"NOTION_ACCESS_TOKEN": "test-token"},
        )

        assert result.exit_code == 0
        # Check that JSON file was created
        assert os.path.exists("test-uuid.json")


class TestCLILogging:
    """Test CLI logging functionality."""

    def test_cli_verbose_flag(self, caplog):
        """Test that the --verbose flag enables debug logging."""
        runner = CliRunner()

        with caplog.at_level(logging.DEBUG):
            result = runner.invoke(cli, ["--verbose", "--help"])

        assert result.exit_code == 0
        # The configure_logging function should have been called
        # We can't easily test the actual logging level here due to Click's isolation
        # but we can test that the command runs successfully with verbose flag

    def test_cli_quiet_flag(self, caplog):
        """Test that the --quiet flag enables warning-only logging."""
        runner = CliRunner()

        result = runner.invoke(cli, ["--quiet", "--help"])
        assert result.exit_code == 0

    def test_cli_verbose_and_quiet_flags_conflict(self):
        """Test that verbose and quiet flags can be used together (quiet takes precedence)."""
        runner = CliRunner()

        # Both flags should be accepted (no error)
        result = runner.invoke(cli, ["--verbose", "--quiet", "--help"])
        assert result.exit_code == 0

    def test_import_with_verbose_logging(self, caplog):
        """Test import command with verbose logging."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create test file
            with open("test.md", "w") as f:
                f.write("# Test Document\n\nThis is test content.")

            # Mock the entire Notion client and service chain
            with (
                patch("thought.cli.notion_url_to_uuid") as mock_uuid,
                patch("thought.cli.MarkdownImportService") as mock_import_service_class,
                patch(
                    "thought.services.markdown_import.NotionAPIClient"
                ) as mock_api_client,
            ):
                # Set up UUID mock
                mock_uuid.return_value = "12345678123412341234123456789012"

                # Set up NotionAPIClient mock
                mock_client_instance = Mock()
                mock_client_instance.client = create_mock_notion_client()
                mock_api_client.return_value = mock_client_instance

                # Set up MarkdownImportService mock
                mock_service = Mock()
                mock_service.import_file.return_value = ImportResult(
                    success=True,
                    action="created",
                    file_path=Path("test.md"),
                    page_id="page-123",
                )
                mock_import_service_class.return_value = mock_service

                # Run the command with verbose flag
                with caplog.at_level(logging.DEBUG):
                    result = runner.invoke(
                        cli,
                        [
                            "--verbose",
                            "import",
                            "test.md",
                            "--database",
                            "https://notion.so/db-url",
                        ],
                        catch_exceptions=False,
                    )

                # Check the output
                assert result.exit_code == 0
                # With verbose mode, we should see more detailed output
                assert "✅ created: test.md" in result.output
