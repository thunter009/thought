import logging
import re
import sys
from pathlib import Path

import click
import pandas as pd

from thought.client import NotionAPIClient
from thought.core import CollectionExtension, CollectionViewExtension
from thought.exceptions import (
    CollectionMustAlreadyExistException,
    LoadDestinationNotUniqueException,
)
from thought.service import Registry
from thought.settings import (
    LOGGING_DATE_FORMAT,
    LOGGING_FORMAT,
    LOGGING_PATH,
    NOTION_SERVICES_DIRECTORY,
)
from thought.utils import (
    notion_clean_column_name,
    notion_query,
    notion_rich_text_to_plain_text,
    notion_select_to_plain_text,
    notion_url_to_uuid,
    now,
    pascal_to_lower_snake,
)

FILE_NAME = __name__
logging.basicConfig(
    level=logging.INFO,
    datefmt=LOGGING_DATE_FORMAT,
    format=LOGGING_FORMAT,
    handlers=[
        logging.FileHandler(
            f"{LOGGING_PATH}/{FILE_NAME}.log", encoding=None, delay=False
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger()


class Config:
    """Configuration Object"""

    def add_url_prefix(self, url):
        """Adds a notion.so prefex to notion URLS"""
        prefix = "https://www.notion.so/"
        return prefix + url


CONTEXT = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option(
    "--service_config_directory",
    default="../services/",
    help="Directory where {service}.toml configuration file is loaded from. Defaults to '/services/'",
)
@CONTEXT
def cli(ctx, service_config_directory):
    """
    Thought - Notion CLI
    """
    ctx.service_config_directory = service_config_directory
    ctx.registry = Registry()
    ctx.client = NotionAPIClient().client


@cli.command("dedupe")
@click.argument("collection_url")
@click.option(
    "-f",
    "--field",
    multiple=True,
    help="Deduplication field. Can be one or many. Defaults to all collection object properties",
)
@CONTEXT
def dedupe(ctx, collection_url: str, field):
    """
    Removes dupelicate items in a specified collection view

    Arguments
    ---------

    collection: A URL to a collection view
    """
    client = ctx.client
    col_view = client.get_collection_view(collection_url)
    collection = CollectionExtension(col_view.collection)
    deduped_df = (
        collection.dedupe(comparison_fields=list(field))
        if field
        else collection.dedupe()
    )
    collection.sync(
        deduped_df, id_col="id"
    )  # call to sync collection objects property data with dataframe records using object id as key
    # above does nothing...


@cli.command("sort")
@click.argument("url")
@click.option(
    "-f", "--field", default="tags", help='The field to sort on. Defaults to "tags"'
)
@click.option(
    "--sort_multiselect_schema_values",
    is_flag=True,
    default=False,
    help="If the provided field is a multi-select and the --sort_multiselect_schema_values flag \
          is passed, sorts the possible values of the multi-select field before sorting the entire \
          collection view by the multi-select field",
)
@click.option(
    "--sort_multiselect_record_values",
    is_flag=True,
    default=False,
    help="If the provided field is a multi-select and the --sort_multiselect_record_values flag is passed, \
                                                                                     sorts each record's multi-select field value before sorting the entire collection view by \
                                                                                     the multi-select field",
)
@CONTEXT
def sort(ctx, url, field, sort_field_values, sort_multiselect_values) -> None:
    """
    Sorts a provided field's attributes in alpha-numeric order

    Arguments
    ---------

    url: A URL to a collection or collection view to sort
    field: The collection's field to sort on. Defaults to "tags"

    Options
    ---------
    sort_field_values: Sorts a multi-select field's possible values instead of sorting the collection view's actual records
    sort_multiselect_values: If the provided field is a multi-select, sorts of the multi-select values before sorting the collection view by the multi-select field
    ascending: Sorts in ascending order by default

    """
    client = ctx.client
    col_view = client.get_collection_view(url)
    collection_view = CollectionViewExtension(col_view)
    collection_view.sort(
        field=field,
        sort_multiselect_values=sort_multiselect_values,
    )


@cli.command("sync")
@click.argument("service")  # , help='The service you want to sync data from')
@click.argument(
    "action"
)  # , help='The sync action you want to perform with the specified service')
@click.option(
    "--target_collection",
    default=NOTION_SERVICES_DIRECTORY,
    help="The target page you want the output of the sync action to persist in. Will create a Collection in this object with the service name as the title.",
)
# @click.option('--service_definition', default=SERVICES_CONFIGURATION_PATH, help='The target collection you want the output of the sync action to persist in')
@CONTEXT
def sync(ctx, service: str, action: str, target_collection: str) -> None:
    """
    Syncs data from an external data provider to a Collection in your Notion environment.

    Arguments
    ---------

    service: The service you want to sync data from
    action: The sync action you want to perform with the specified service.

    Options
    ---------
    target: The target page you want the output of the sync action to persist in. Will create a Collection in this object with the service name as the title.

    Example
    ---------

    `thought sync instapaper bookmarks`
    """
    client = ctx.client
    registry = ctx.registry
    registered_service = registry.register(service)
    service_instance = registered_service()

    if not service_instance:
        logging.info(
            "%s service not defined and configured properly. Please refer to docs.",
            service,
        )

    if not service_instance[action]:
        logging.info(
            "%s action not defined for specified service. Please refer to docs.", action
        )

    data = service_instance.call(
        action, folder="archive"
    )  # TODO: onboard arbitrary key: values from click options here

    page = client.get_block(target_collection)
    collection_name = f"{service}_{action}"

    # filter through possible collections in the service pages children, collection
    collection = [x for x in page.children if collection_name == x.title]

    if not collection:
        # TODO: create new collection if nothing matches our {service}_{action} nameing pattern -- blocked by API support as of 8/11/20
        raise CollectionMustAlreadyExistException(
            f"{collection_name} must already exist"
        )

    if len(collection) > 1:
        raise LoadDestinationNotUniqueException(
            f"Target collection must be unique: remove existing collection {collection_name} or pick a new function name"
        )

    # drop to base object since we're confident this list should only contain 1 object
    collection = collection[0].collection
    service_instance.load(data, collection)


@cli.command("tojson")
@click.argument("database_url")
@click.option(
    "-o",
    "--output",
    "_output",
    type=str,
    help="The output path to save the exported data to",
    default=".",
)
@click.option(
    "-c",
    "--columns",
    type=str,
    help="The columns to export from the target database",
    multiple=True,
    default=None,
)
@click.option(
    "-f",
    "--filter",
    type=list,
    help="The filter to apply to the target database",
    default={},
)
@click.option(
    "-lsc",
    "--lower-snake-case",
    type=str,
    help="Changes the output for a provided column to lower_snake_case",
    default={},
)
@CONTEXT
def tojson(
    ctx,
    database_url: str,
    _output: str,
    columns: list,
    lower_snake_case: str,
) -> None:
    """
    Exports a database view to JSON records format.

    Arguments
    ---------

    database_url: The URL to a specific database (or view) you want to export as a JSON records array
    filter: A JSON object specifying the filter to apply to the database

    Example
    ---------

    `thought tojson "https://www.notion.so/<YOUR ORG>/<DATABASE_ID>?v=<VIEW_ID>"`
    """
    client = ctx.client

    # convert raw URL --> UUID
    uuid = notion_url_to_uuid(database_url)

    # construct query from CLI parameters
    # TODO: pass filters via CLI params

    query = {
        "database_id": uuid,
        "filter": {"property": "status", "select": {"equals": "PROD"}},
    }

    # send query and get back response JSON
    # result = client.databases.query(**query)
    result = notion_query(client, query)

    # handle pagination
    # TODO: make this a recursive async function
    results = []
    has_more = result["has_more"]
    results.append(result["results"])
    while has_more:
        cursor = {"start_cursor": result["next_cursor"]}
        new_query = query | cursor
        result = notion_query(client, new_query)
        results.append(result["results"])
        has_more = result["has_more"]

    # filter down JSON response to export ready object
    holder = []
    for r in results:

        # convert dict to df
        df = pd.json_normalize(r)

        # handle all columns case
        if len(columns) == 0:
            input_columns = list(df.columns)

        # select only provided columns
        else:
            input_columns = [
                x for x in df.columns for y in columns if f"properties.{y}" in x
            ]

        # TODO: add click option to include title column object + flatten it
        reduced_columns = [
            x
            for x in input_columns
            if all(
                [
                    not re.search(r"\.id$", x),
                    not re.search(r"\.type$", x),
                    not re.search(r"\.color$", x),
                    not re.search(r"\.title$", x),
                    not re.search(r"\.rollup\.", x),
                    not re.search(r"\.last_edited_by$", x),
                    not re.search(r"\.created_by$", x),
                    "properties." in x,
                ]
            )
        ]
        df = df[reduced_columns]
        df = df.loc[:, ~df.columns.duplicated()].copy()

        # handle rich_text fields
        # TODO: make this a function
        rich_text_columns = [x for x in df.columns if "rich_text" in x]

        if rich_text_columns:

            for rt_col in rich_text_columns:
                df[rt_col] = df[rt_col].apply(notion_rich_text_to_plain_text)

        # handle tag fields
        # TODO: make this a function

        tag_columns = [
            x
            for x in df.columns
            if any(
                [
                    "multi_select" in x,
                    "select" in x,
                ]
            )
        ]

        if tag_columns:

            for col in tag_columns:
                df[col] = df[col].apply(notion_select_to_plain_text)

        # change column names to "pure" column names without notion data structure cruft
        new_column_names = {x: notion_clean_column_name(x) for x in df.columns}
        df.rename(columns=new_column_names, inplace=True)

        # drops subtly duplicate columns from entering the dataframe
        df.dropna(axis=1, how="all", inplace=True)

        holder.append(df)

    # write object to file
    path = Path(_output) / Path(f"{uuid}-{now()}.json")
    df = pd.concat(holder)

    if lower_snake_case:
        df = pascal_to_lower_snake(df, "metric")
        df = pascal_to_lower_snake(df, "metric_v2")
    try:
        df.to_json(path, orient="records")
    except:
        logger.debug("Something went wrong writing out %s", str(path))


@cli.command("tocsv")
@click.argument("database_url")
@click.option(
    "-o",
    "--output",
    "_output",
    type=str,
    help="The output path to save the exported data to",
    default=".",
)
@click.option(
    "-c",
    "--columns",
    type=str,
    help="The columns to export from the target database",
    multiple=True,
    default=None,
)
@click.option(
    "-f",
    "--filter",
    type=list,
    help="The filter to apply to the target database",
    default={},
)
@click.option(
    "-lsc",
    "--lower-snake-case",
    type=str,
    help="Changes the output for a provided column to lower_snake_case",
    default={},
)
@CONTEXT
def tocsv(
    ctx,
    database_url: str,
    _output: str,
    columns: list,
    filter: dict,
    lower_snake_case: str,
) -> None:
    """
    Exports a database view to CSV format.

    Arguments
    ---------

    database_url: The URL to a specific database (or view) you want to export as a JSON records array
    filter: A JSON object specifying the filter to apply to the database

    Example
    ---------

    `thought tojson "https://www.notion.so/<YOUR ORG>/<DATABASE_ID>?v=<VIEW_ID>"`
    """
    # TODO: refactor tojson and tocsv for common code/overlap in functionality
    client = ctx.client

    # convert raw URL --> UUID
    uuid = notion_url_to_uuid(database_url)

    # construct query from CLI parameters
    # TODO: pass filters via CLI params

    query = {"database_id": uuid}

    result = notion_query(client, query)

    # handle pagination
    # TODO: make this a recursive async function
    results = []
    has_more = result["has_more"]
    results.append(result["results"])
    while has_more:
        cursor = {"start_cursor": result["next_cursor"]}
        new_query = query | cursor
        result = notion_query(client, new_query)
        results.append(result["results"])
        has_more = result["has_more"]

    # filter down JSON response to export ready object
    holder = []
    for r in results:

        # convert dict to df
        df = pd.json_normalize(r)

        # handle all columns case
        if len(columns) == 0:
            input_columns = list(df.columns)

        # select only provided columns
        else:
            input_columns = [
                x for x in df.columns for y in columns if f"properties.{y}" in x
            ]

        # TODO: add click option to include title column object + flatten it
        reduced_columns = [
            x
            for x in input_columns
            if all(
                [
                    not re.search(r"\.id$", x),
                    not re.search(r"\.type$", x),
                    not re.search(r"\.color$", x),
                    not re.search(r"\.title$", x),
                    not re.search(r"\.rollup\.", x),
                    not re.search(r"\.last_edited_by$", x),
                    not re.search(r"\.created_by$", x),
                    "properties." in x,
                ]
            )
        ]
        df = df[reduced_columns]
        df = df.loc[:, ~df.columns.duplicated()].copy()

        # handle rich_text fields
        # TODO: make this a function
        rich_text_columns = [x for x in df.columns if "rich_text" in x]

        if rich_text_columns:

            for rt_col in rich_text_columns:
                df[rt_col] = df[rt_col].apply(notion_rich_text_to_plain_text)

        # handle tag fields
        # TODO: make this a function

        tag_columns = [
            x
            for x in df.columns
            if any(
                [
                    "multi_select" in x,
                    "select" in x,
                ]
            )
        ]

        if tag_columns:

            for col in tag_columns:
                df[col] = df[col].apply(notion_select_to_plain_text)

        # handle name/id field
        # TODO: make this a function
        # formula_columns = [
        #     x for x in df.columns
        #     if any([
        #         '.formula.' in x,
        #     ])
        # ]

        # if formula_columns:

        #     for col in tag_columns:
        #         df[col] = df[col].apply(notion_select_to_plain_text)

        # change column names to "pure" column names without notion data structure cruft

        new_column_names = {x: notion_clean_column_name(x) for x in df.columns}
        df.rename(columns=new_column_names, inplace=True)
        holder.append(df)

    # write object to file
    path = Path(_output) / Path(f"{uuid}-{now()}.csv")

    df = pd.concat(holder)
    try:
        df.to_csv(path, index=False)
    except:
        logger.debug("Something went wrong writing out %s", str(path))


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
