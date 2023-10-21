from notion_client import Client as NotionClient

from thought.client import NotionAPIClient
from thought.settings import NOTION_ACCESS_TOKEN


class TestNotionAPIClient:
    """
    Unit tests for the NotionAPIClient class

    Note: these are not integration tests using this API client
    """

    def test_get_client(
        self,
        notion_api_client: NotionAPIClient,
        notion_api_client_client: NotionAPIClient.client,
    ):
        """
        Test creating a client
        """
        # test that the function works
        actual_client = notion_api_client.get_client(NOTION_ACCESS_TOKEN)
        assert isinstance(actual_client, NotionClient)

        # test that the class attributes are initializing properly
        assert isinstance(notion_api_client_client, NotionClient)
