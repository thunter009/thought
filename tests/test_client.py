from unittest.mock import MagicMock, patch

import pytest
from notion_client import Client as NotionClient

from thought.client import NotionAPIClient


class TestNotionAPIClient:
    """
    Unit tests for the NotionAPIClient class

    Note: these are not integration tests using this API client
    """

    @patch("thought.client.NotionClient")
    def test_get_client(self, mock_notion_client):
        """
        Test creating a client with valid token
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance

        # Create client with test token
        test_token = "test_token"
        client = NotionAPIClient()
        actual_client = client.get_client(test_token)

        # Verify the client was created with correct token
        mock_notion_client.assert_called_once_with(auth=test_token)
        assert isinstance(actual_client, NotionClient)

    def test_get_client_no_token(self):
        """
        Test client creation with no token raises ValueError
        """
        client = NotionAPIClient()
        with pytest.raises(ValueError, match="Notion access token is required"):
            client.get_client(None)

    @patch("thought.client.NotionClient")
    def test_client_initialization(self, mock_notion_client):
        """
        Test client initialization behavior
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance

        # Test first initialization
        client1 = NotionAPIClient()
        assert client1.client is not None

        # Test second initialization (should reuse existing client)
        client2 = NotionAPIClient()
        assert client2.client is client1.client
        mock_notion_client.assert_called_once()

    @patch("thought.client.NotionClient")
    def test_query(self, mock_notion_client):
        """
        Test successful query to the Notion API
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance
        mock_client_instance.databases.query.return_value = {"results": []}

        # Create client and test query
        client = NotionAPIClient()
        test_query = {"database_id": "test_id"}
        result = client.query(test_query)

        # Verify query was called with correct parameters
        mock_client_instance.databases.query.assert_called_once_with(**test_query)
        assert isinstance(result, dict)

    @patch("thought.client.NotionClient")
    def test_query_with_complex_parameters(self, mock_notion_client):
        """
        Test query with complex parameters (filters, sorts, etc.)
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance
        mock_client_instance.databases.query.return_value = {
            "results": [],
            "has_more": False,
            "next_cursor": None,
        }

        # Create client and test complex query
        client = NotionAPIClient()
        test_query = {
            "database_id": "test_id",
            "filter": {"property": "Status", "status": {"equals": "Done"}},
            "sorts": [{"property": "Last edited time", "direction": "descending"}],
            "page_size": 100,
        }
        result = client.query(test_query)

        # Verify query was called with correct parameters
        mock_client_instance.databases.query.assert_called_once_with(**test_query)
        assert isinstance(result, dict)
        assert "results" in result
        assert "has_more" in result
        assert "next_cursor" in result

    @patch("thought.client.NotionClient")
    def test_query_error_handling(self, mock_notion_client):
        """
        Test error handling in query method
        """
        # Setup mock to raise an exception
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance
        mock_client_instance.databases.query.side_effect = Exception("API Error")

        # Create client and test error handling
        client = NotionAPIClient()
        test_query = {"database_id": "test_id"}

        with pytest.raises(Exception, match="API Error"):
            client.query(test_query)

    @patch("thought.client.NotionClient")
    def test_query_with_invalid_response(self, mock_notion_client):
        """
        Test handling of invalid response from API
        """
        # Setup mock to return invalid response
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance
        mock_client_instance.databases.query.return_value = "invalid_response"

        # Create client and test invalid response handling
        client = NotionAPIClient()
        test_query = {"database_id": "test_id"}

        with pytest.raises(AssertionError):
            client.query(test_query)
