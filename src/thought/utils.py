import copy
from dataclasses import field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pandas as pd
import regex as re
from dotenv import load_dotenv


def load_env():
    """
    loads local environment variables
    """
    env_path = Path(".") / ".env"
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
    """
    regex = r"(?<=https:\/\/www.notion.so\/[a-zA-Z0-9]+\/)[a-zA-Z0-9]{32}"
    search = re.search(regex, url)
    if search:
        result = search.group()
        result = (
            f"{result[:8]}-{result[8:12]}-{result[12:16]}-{result[16:20]}-{result[20:]}"
        )
    return result


def notion_rich_text_to_plain_text(rich_text_list: list) -> str:
    """
    Converts a notion rich_text list into a plain text string
    """
    holder = []
    for part in rich_text_list:
        holder.append(part["text"]["content"])
    return "".join(holder)


def notion_select_to_plain_text(input_value: list) -> str:
    """
    Converts a notion rich_text list into a plain text string
    """
    if input_value and isinstance(input_value, list):
        holder = []
        for part in input_value:
            holder.append(part["name"])
        return holder

    return input_value


def notion_clean_column_name(column_name: str) -> str:
    """
    Converts a notion column name to a "clean" name with no data structure components

    Example
    -------
    properties.ThisIsACheckbox.checkbox -> ThisIsACheckbox
    """
    # handle date columns
    is_date_regex = (
        r"(?<=properties\.)([a-zA-Z0-9_\-#.() ]+\.date\.[a-zA-Z0-9_\-#.() ]+)"
    )
    is_date = re.search(is_date_regex, column_name)

    # handle formula columns
    is_formula_regex = (
        r"(?<=properties\.)([a-zA-Z0-9_\-#.() ]+\.formula\.[a-zA-Z0-9_\-#.() ]+)"
    )
    is_formula = re.search(is_formula_regex, column_name)

    # handle select columns
    is_select_regex = (
        r"(?<=properties\.)([a-zA-Z0-9_\-#.() ]+\.select\.[a-zA-Z0-9_\-#.() ]+)"
    )
    is_select = re.search(is_select_regex, column_name)

    if is_date:
        return is_date.group().replace(".date.", "_")
    elif is_formula:
        return re.sub(r"\.formula\.[a-zA-Z0-9_\-#.() ]+", "", is_formula.group())
    elif is_select:
        return re.sub(r"\.select\.[a-zA-Z0-9_\-#.() ]+", "", is_select.group())
    else:
        regex = r"(?<=properties\.)([a-zA-Z0-9_\-#.() \u263a-\U0001f645]+)(?=\.[a-zA-Z0-9_ ]+)"  # noqa E501
        search = re.search(regex, column_name)
        return search.group() if search else column_name


def notion_query(client, query: Dict[str, any]):
    return client.databases.query(**query)


def pascal_to_lower_snake(df: pd.DataFrame, column: str) -> str:
    df[column] = (
        df[column]
        .replace("QQ", "qq")
        .replace("ACS", "acs")
        .replace("YR", "yr")
        .replace("1Y", "1y")
        .replace("as_of", "date")
        .replace("PctAge", "PctAge_")
        .replace("(?<=[0-9])to", "_to_", regex=True)
        .replace("(?<!^)(?=[A-Z])", "_", regex=True)
        .replace("_2_0_1_9", "_2019")
        .str.lower()
    )
    return df
