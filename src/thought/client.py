import os

from notion.client import NotionClient
from thought.settings import NOTION_ACCESS_TOKEN


def get_client(token):
    return NotionClient(token_v2=token)


class NotionAPI:
    """
    Notion Client object
    """
    token: str = NOTION_ACCESS_TOKEN
    client: NotionClient = None

    def __init__(self):
        if self.token is None:
            self.token = NOTION_ACCESS_TOKEN

        if self.client is None:
            self.client = get_client(self.token)