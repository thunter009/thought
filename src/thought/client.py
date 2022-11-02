from notion_client import Client as NotionClient

from thought.settings import NOTION_ACCESS_TOKEN


class NotionAPIClient:
    """
    Notion API Client wrapper
    """

    client: NotionClient | None = None

    def __init__(self):
        """
        Used for initializing a Notion API client
        """
        if self.client is None:
            self.client = self.get_client(NOTION_ACCESS_TOKEN)

    def query(self, query: dict[str, any]):
        """
        Sends a query to the Notion API
        """
        return self.client.databases.query(**query)

    def get_client(self, token: str) -> NotionClient:
        """
        Returns an official Notion API Client
        """
        return NotionClient(auth=token)
