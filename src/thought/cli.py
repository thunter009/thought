import logging
import sys
from typing import Any

import click
import pandas as pd

from thought.client import NotionAPIClient
from thought.core import CollectionExtension, CollectionViewExtension
from thought.exceptions import (
    CollectionMustAlreadyExistError,
    LoadDestinationNotUniqueError,
)
from thought.service import Registry
from thought.settings import (
    LOGGING_DATE_FORMAT,
    LOGGING_FORMAT,
    LOGGING_PATH,
    NOTION_SERVICES_DIRECTORY,
)
from thought.utils import (
    notion_url_to_uuid,
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

    service_config_directory: str
    registry: Any
    client: Any

    def add_url_prefix(self, url: str) -> str:
        """Adds a notion.so prefex to notion URLS"""
        prefix = "https://www.notion.so/"
        return prefix + url


CONTEXT = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option(
    "--service_config_directory",
    default="../services/",
    help="Directory where {service}.toml configuration file is loaded from. "
    "Defaults to '/services/'",
)
@CONTEXT
def cli(ctx: Config, service_config_directory: str) -> None:
    """
    Thought - Notion CLI
    """
    ctx.service_config_directory = service_config_directory
    ctx.registry = Registry()
    ctx.client = NotionAPIClient()


@cli.command("dedupe")
@click.argument("collection_url")
@click.option(
    "-f",
    "--field",
    multiple=True,
    help="Deduplication field. Can be one or many. "
    "Defaults to all collection object properties",
)
@CONTEXT
def dedupe(ctx: Config, collection_url: str, field: tuple[str, ...]) -> None:
    """
    Removes dupelicate items in a specified collection view

    Arguments
    ---------

    collection: A URL to a collection view
    """
    client = ctx.client
    col_view = client.get_collection_view(collection_url)
    collection = CollectionExtension(col_view.collection)
    collection.dedupe(comparison_fields=list(field)) if field else collection.dedupe()


@cli.command("sort")
@click.argument("url")
@click.option(
    "-f", "--field", default="tags", help='The field to sort on. Defaults to "tags"'
)
@click.option(
    "--sort_multiselect_values",
    is_flag=True,
    default=False,
    help="If the provided field is a multi-select and the "
    "--sort_multiselect_record_values flag is passed, sorts each record's "
    "multi-select field value before sorting the entire collection view by "
    "the multi-select field",
)
@CONTEXT
def sort(ctx: Config, url: str, field: str, sort_multiselect_values: bool) -> None:
    """
    Sorts a provided field's attributes in alpha-numeric order

    Arguments
    ---------
    url: A URL to a collection or collection view to sort
    field: The collection's field to sort on. Defaults to "tags"

    Options
    ---------
    sort_field_values: Sorts a multi-select field's possible values instead of
                      sorting the collection view's actual records
    sort_multiselect_values: If the provided field is a multi-select, sorts of
                            the multi-select values before sorting the collection
                            view by the multi-select field
    ascending: Sorts in ascending order by default
    """
    client = ctx.client
    # convert raw URL --> UUID
    uuid = notion_url_to_uuid(url)
    query = {
        "database_id": uuid,
        "sort": {"property": field, "direction": "ascending"},
    }

    # send query and get back response JSON
    # result = client.databases.query(**query)
    _ = client.query(query)

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
    help=(
        "The target page you want the output of the sync action to persist in. "
        "Will create a Collection in this object with the service name as the title."
    ),
)
@CONTEXT
def sync(ctx: Config, service: str, action: str, target_collection: str) -> None:
    """Sync data from an external service to a Notion collection.

    This function retrieves data from a specified service using a given action,
    then loads that data into a Notion collection. The target collection must
    already exist and be uniquely identifiable.

    Parameters
    ----------
    ctx : Config
        Click context object containing client and registry instances
    service : str
        Name of the service to sync data from (e.g. 'instapaper')
    action : str
        Action to perform with the specified service (e.g. 'bookmarks')
    target_collection : str
        URL or ID of the target Notion page where the collection exists

    Raises
    ------
    CollectionMustAlreadyExistError
        If the target collection does not exist
    LoadDestinationNotUniqueError
        If multiple collections match the target name

    Example
    -------
    >>> thought sync instapaper bookmarks --target_collection=page_url
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
        # TODO: create new collection if nothing matches our {service}_{action}
        # naming pattern
        # -- blocked by API support as of 8/11/20
        raise CollectionMustAlreadyExistError(f"{collection_name} must already exist")

    if len(collection) > 1:
        raise LoadDestinationNotUniqueError(
            f"Target collection must be unique: remove existing collection "
            f"{collection_name} or pick a new function name"
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
    type=dict,
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
    ctx: Config,
    database_url: str,
    _output: str,
    columns: list[str] | None,
    filter: dict[str, Any],
    lower_snake_case: str,
) -> None:
    """
    Exports a Notion database to a JSON file

    Arguments
    ---------
    database_url: A URL to a Notion database
    """
    client = ctx.client
    # convert raw URL --> UUID
    uuid = notion_url_to_uuid(database_url)
    query = {
        "database_id": uuid,
        "filter": filter,
    }

    # send query and get back response JSON
    result = client.query(query)

    # convert response to pandas dataframe
    df = pd.DataFrame(result["results"])

    # if columns are specified, filter to just those columns
    if columns:
        df = df[columns]

    # if lower_snake_case is specified, convert the specified column to lower_snake_case
    if lower_snake_case:
        df = pascal_to_lower_snake(df, lower_snake_case)

    # save to JSON
    df.to_json(f"{_output}/{uuid}.json", orient="records")


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
    type=dict,
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
    ctx: Config,
    database_url: str,
    _output: str,
    columns: list[str] | None,
    filter: dict[str, Any],
    lower_snake_case: str,
) -> None:
    """
    Exports a Notion database to a CSV file

    Arguments
    ---------
    database_url: A URL to a Notion database
    """
    client = ctx.client
    # convert raw URL --> UUID
    uuid = notion_url_to_uuid(database_url)
    query = {
        "database_id": uuid,
        "filter": filter,
    }

    # send query and get back response JSON
    result = client.query(query)

    # convert response to pandas dataframe
    df = pd.DataFrame(result["results"])

    # if columns are specified, filter to just those columns
    if columns:
        df = df[columns]

    # if lower_snake_case is specified, convert the specified column to lower_snake_case
    if lower_snake_case:
        df = pascal_to_lower_snake(df, lower_snake_case)

    # save to CSV
    df.to_csv(f"{_output}/{uuid}.csv", index=False)


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
