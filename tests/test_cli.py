import os
from unittest.mock import Mock, patch

from click.testing import CliRunner

from thought.cli import _extract_notion_properties, _extract_property_value, cli

# Test constants
TEST_NUMBER = 42
EXPECTED_RESULT_COUNT = 2


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
