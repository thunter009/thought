"""Test configuration and fixtures."""

import os
from unittest.mock import MagicMock, patch

import pytest

from thought.client import NotionAPIClient

# Set a fake token for testing if not already set
if "NOTION_ACCESS_TOKEN" not in os.environ:
    os.environ["NOTION_ACCESS_TOKEN"] = "fake-test-token"


@pytest.fixture(name="notion_api_client")
def notion_api_client() -> NotionAPIClient:
    """
    Mocked instance of NotionAPIClient for testing
    """
    with patch("thought.client.NotionClient") as mock_notion_client:
        # Create a mock Notion client instance
        mock_notion_client_instance = MagicMock()
        mock_notion_client.return_value = mock_notion_client_instance

        # Create the NotionAPIClient which will use the mocked NotionClient
        client = NotionAPIClient()

        return client


@pytest.fixture()
def notion_api_client_client(
    notion_api_client: NotionAPIClient,
):
    """
    Fixture: NotionAPIClient.client
    """
    return notion_api_client.client
