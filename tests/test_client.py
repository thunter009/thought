from unittest.mock import MagicMock, patch

import pytest

from thought.client import NotionAPIClient


class TestNotionAPIClient:
    """
    Unit tests for the NotionAPIClient class

    Note: these are not integration tests using this API client
    """

    EXPECTED_USER_COUNT = 2

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_get_client(mock_notion_client):
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
        # The mock should be called twice: once during init, once with test_token
        calls = mock_notion_client.call_args_list
        expected_call_count = 2
        assert len(calls) == expected_call_count
        assert calls[0] == ((), {"auth": "mocked_token"})  # from __init__
        assert calls[1] == ((), {"auth": "test_token"})  # from get_client call
        # The actual_client should be our mock instance
        assert actual_client is mock_client_instance

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_get_client_no_token(mock_notion_client):
        """
        Test client creation with no token raises ValueError
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance

        client = NotionAPIClient()
        with pytest.raises(ValueError, match="Notion access token is required"):
            client.get_client(None)

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_client_initialization(mock_notion_client):
        """
        Test client initialization behavior
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance

        # Test first initialization
        client1 = NotionAPIClient()
        assert client1.client is not None

        # Test second initialization (each instance gets its own client)
        client2 = NotionAPIClient()
        assert client2.client is not None

        # Since we changed from class variable to instance variable,
        # each instance should have its own client
        # Both clients should be the same mock instance but they're separate instances
        expected_call_count = 2
        assert mock_notion_client.call_count == expected_call_count
        # Both calls should be with the mocked token
        calls = mock_notion_client.call_args_list
        assert calls[0] == ((), {"auth": "mocked_token"})
        assert calls[1] == ((), {"auth": "mocked_token"})

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_query(mock_notion_client):
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

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_query_with_complex_parameters(mock_notion_client):
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

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_query_error_handling(mock_notion_client):
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

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_query_with_invalid_response(mock_notion_client):
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

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_search_users(mock_notion_client):
        """
        Test searching for users in the workspace
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance
        mock_client_instance.users.list.return_value = {
            "results": [
                {
                    "id": "user1",
                    "name": "John Doe",
                    "type": "person",
                    "person": {"email": "john@example.com"},
                },
                {
                    "id": "user2",
                    "name": "Jane Smith",
                    "type": "person",
                    "person": {"email": "jane@example.com"},
                },
            ]
        }

        # Create client and test search
        client = NotionAPIClient()

        # Test search with no filter
        all_users = client.search_users()
        assert len(all_users) == TestNotionAPIClient.EXPECTED_USER_COUNT

        # Test search with name filter
        john_users = client.search_users("john")
        assert len(john_users) == 1
        assert john_users[0]["name"] == "John Doe"

        # Test search with email filter
        jane_users = client.search_users("jane@example.com")
        assert len(jane_users) == 1
        assert jane_users[0]["name"] == "Jane Smith"

    @staticmethod
    @patch("thought.client.NOTION_ACCESS_TOKEN", "mocked_token")
    @patch("thought.client.NotionClient")
    def test_get_user_by_name_or_email(mock_notion_client):
        """
        Test getting a specific user by name or email
        """
        # Setup mock
        mock_client_instance = MagicMock()
        mock_notion_client.return_value = mock_client_instance
        mock_client_instance.users.list.return_value = {
            "results": [
                {
                    "id": "user1",
                    "name": "John Doe",
                    "type": "person",
                    "person": {"email": "john@example.com"},
                },
                {
                    "id": "user2",
                    "name": "Jane Smith",
                    "type": "person",
                    "person": {"email": "jane@example.com"},
                },
            ]
        }

        # Create client and test user lookup
        client = NotionAPIClient()

        # Test lookup by exact name
        user = client.get_user_by_name_or_email("John Doe")
        assert user is not None
        assert user["id"] == "user1"

        # Test lookup by exact email
        user = client.get_user_by_name_or_email("jane@example.com")
        assert user is not None
        assert user["id"] == "user2"

        # Test lookup with case-insensitive match
        user = client.get_user_by_name_or_email("JOHN DOE")
        assert user is not None
        assert user["id"] == "user1"

        # Test lookup with non-existent user
        user = client.get_user_by_name_or_email("Unknown User")
        assert user is None
