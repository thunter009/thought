import copy
from dataclasses import field
from datetime import datetime, timezone
from pathlib import Path

import pytoml as toml
import regex as re
from dotenv import load_dotenv


def load_env():
    """
    loads local environment variables
    """
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path, verbose=True)

def now():
    """
    returns current UTC timestamp
    """
    utc_dt = datetime.now(timezone.utc)  # UTC time
    return utc_dt


def default_field(obj, **kwargs):
    """
    returns field object that can handle default factory functions properly
    """
    return field(default_factory=lambda: copy.copy(obj), **kwargs)


def notion_url_to_uuid(url: str) -> str:
    """
    converts a valid Notion URL to a UUID

    e.g. https://www.notion.so/teehuntz/022f2194a8c040709992a2533a99cdbe\?v\=55194a17a1e64b9db5d45289d5fb412f --> 40d4e41a-255a-4140-ab7b-2da041e953db
    """
    regex = r'(?<=https:\/\/www.notion.so\/[a-zA-Z0-9]+\/)[a-zA-Z0-9]{32}'
    search = re.search(regex, url)
    if search:
        result = search.group()
        result = f'{result[:8]}-{result[8:12]}-{result[12:16]}-{result[16:20]}-{result[20:]}'
    return result


def notion_rich_text_to_plain_text(rich_text_list: list) -> str:
    """
    Converts a notion rich_text list into a plain text string
    """
    holder = []
    for part in rich_text_list:
        holder.append(part['text']['content'])
    return ''.join(holder)
        
def notion_clean_column_name(column_name: str) -> str:
    """
    Converts a notion column name to a "clean" name with no data structure components

    Example
    -------
    properties.ThisIsACheckbox.checkbox -> ThisIsACheckbox
    """
    regex = r'(?<=properties\.)([a-zA-Z_]+)(?=\.[a-zA-Z_]+)'
    search = re.search(regex, column_name)
    return search.group() if search else None
