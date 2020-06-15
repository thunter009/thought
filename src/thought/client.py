import os
from notion.client import NotionClient
from thought.utils import default_field
from thought.settings import NOTION_ACCESS_TOKEN

def get_client(token):
    return NotionClient(token_v2=token)