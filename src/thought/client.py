from typing import Any

from notion_client import Client as NotionClient

from thought.settings import NOTION_ACCESS_TOKEN


class NotionAPIClient:
    """
    Notion API Client wrapper
    """

    def __init__(self) -> None:
        """
        Used for initializing a Notion API client
        """
        self.client: NotionClient | None = None
        if self.client is None:
            self.client = self.get_client(NOTION_ACCESS_TOKEN)

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        """
        Sends a query to the Notion API
        """
        assert self.client is not None
        result = self.client.databases.query(**query)
        assert isinstance(result, dict)
        return result

    def get_client(self, token: str | None) -> NotionClient:
        """
        Returns an official Notion API Client
        """
        if token is None:
            raise ValueError("Notion access token is required")
        return NotionClient(auth=token)
