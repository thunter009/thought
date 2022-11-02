from dataclasses import dataclass
from typing import Dict

from notion_client import Client as NotionClient

from thought.settings import NOTION_ACCESS_TOKEN
from thought.utils import default_field


def get_client(token=NOTION_ACCESS_TOKEN):
    return NotionClient(auth=token)


@dataclass
class NotionAPIClient:
    """
    Notion API Client wrapper object
    """

    client: NotionClient = default_field(get_client())

    def query(client, query: dict[str, any]):
        """
        Sends a query to the Notion API
        """
        return self.client.databases.query(**query)
