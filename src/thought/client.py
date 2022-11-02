from dataclasses import dataclass

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
