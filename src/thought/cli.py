import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import pandas as pd

from thought.client import NotionAPIClient
from thought.core import CollectionExtension, CollectionViewExtension
from thought.exceptions import (
    CollectionMustAlreadyExistError,
    LoadDestinationNotUniqueError,
)
from thought.logging_utils import configure_logging, get_logger
from thought.service import Registry
from thought.services.markdown_import import MarkdownImportService
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


@dataclass
class ImportOptions:
    """Options for import command."""

    path: str
    database: str
    recursive: bool = False
    mode: str = "merge"
    dry_run: bool = False
    identifier: str = "auto"


def _extract_property_value(prop_data: dict) -> Any:
    """Extract value from a Notion property."""
    prop_type = prop_data["type"]

    # Define mapping of property types to their extraction logic
    extractors = {
        "title": lambda: (
            prop_data["title"][0]["text"]["content"] if prop_data["title"] else ""
        ),
        "rich_text": lambda: (
            prop_data["rich_text"][0]["text"]["content"]
            if prop_data["rich_text"]
            else ""
        ),
        "number": lambda: prop_data["number"],
        "select": lambda: prop_data["select"]["name"] if prop_data["select"] else "",
        "multi_select": lambda: [opt["name"] for opt in prop_data["multi_select"]],
        "date": lambda: prop_data["date"]["start"] if prop_data["date"] else "",
        "checkbox": lambda: prop_data["checkbox"],
        "url": lambda: prop_data["url"],
        "email": lambda: prop_data["email"],
        "phone_number": lambda: prop_data["phone_number"],
    }

    return extractors.get(prop_type, lambda: str(prop_data))()


def _extract_notion_properties(api_results: list[dict]) -> list[dict]:
    """Extract and flatten Notion properties from API results."""
    rows = []
    for item in api_results:
        row = {
            "id": item["id"],
            "created_time": item["created_time"],
            "last_edited_time": item["last_edited_time"],
            "url": item["url"],
        }

        # Extract properties and flatten them
        for prop_name, prop_data in item["properties"].items():
            row[prop_name] = _extract_property_value(prop_data)

        rows.append(row)

    return rows


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
    _client: Any = None
    verbose: bool = False
    quiet: bool = False

    @property
    def client(self) -> Any:
        """Lazy initialization of Notion API client"""
        if self._client is None:
            self._client = NotionAPIClient()
        return self._client

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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Enable quiet mode (WARNING level only)",
)
@CONTEXT
def cli(ctx: Config, service_config_directory: str, verbose: bool, quiet: bool) -> None:
    """
    Thought - Notion CLI
    """
    ctx.service_config_directory = service_config_directory
    ctx.registry = Registry()
    ctx.verbose = verbose
    ctx.quiet = quiet

    # Configure logging based on verbosity flags
    configure_logging(verbose=verbose, quiet=quiet)

    # Initialize client lazily - only when actually needed
    ctx._client = None


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


@cli.command("export")
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
    help="The columns to export from the target database",
    multiple=True,
    default=None,
)
@click.option(
    "-f",
    "--filter",
    type=dict,
    help="The filter to apply to the target database",
    default=None,
)
@click.option(
    "-lsc",
    "--lower-snake-case",
    type=str,
    help="Changes the output for a provided column to lower_snake_case",
    default=None,
)
@click.option(
    "-t",
    "--type",
    "file_type",
    type=click.Choice(["csv", "json"]),
    help="The file type to export to",
    default="csv",
)
@CONTEXT
def export(
    ctx: Config,
    database_url: str,
    _output: str,
    columns: list[str] | None,
    **options,
) -> None:
    """
    Exports a Notion database to CSV or JSON file

    Arguments
    ---------
    database_url: A URL to a Notion database
    """
    client = ctx.client
    filter_param = options.get("filter")
    lower_snake_case = options.get("lower_snake_case")
    file_type = options.get("file_type", "csv")

    # convert raw URL --> UUID
    uuid = notion_url_to_uuid(database_url)
    query = {
        "database_id": uuid,
    }

    # Only add filter if it's not empty
    if filter_param:
        query["filter"] = filter_param

    # send query and get back response JSON
    try:
        result = client.query(query)
    except Exception as e:
        print(f"Error querying database with ID: {uuid}")
        print(f"Original URL: {database_url}")
        print(f"Extracted database ID: {uuid}")
        print("Make sure:")
        print("1. The URL is a direct link to a Notion database (not a page or view)")
        print("2. Your integration has access to this database")
        print("3. The database is shared with your integration")
        print(f"Original error: {e}")
        raise

    # convert response to pandas dataframe
    rows = _extract_notion_properties(result["results"])
    df = pd.DataFrame(rows)

    # if columns are specified, filter to just those columns
    if columns:
        df = df[list(columns)]

    # if lower_snake_case is specified, convert the specified column to lower_snake_case
    if lower_snake_case:
        df = pascal_to_lower_snake(df, lower_snake_case)

    # save to specified file type
    if file_type == "csv":
        df.to_csv(f"{_output}/{uuid}.csv", index=False)
    elif file_type == "json":
        df.to_json(f"{_output}/{uuid}.json", orient="records")


def _import_single_file(
    service: MarkdownImportService,
    file_path: Path,
    database_id: str,
    options: ImportOptions,
    verbose: bool = False,
) -> None:
    """Import a single Markdown file."""
    logger = get_logger(__name__)

    if verbose:
        logger.info(f"Processing file: {file_path}")
    else:
        click.echo(f"Importing {file_path}...")

    result = service.import_file(
        file_path, database_id, options.mode, options.identifier, options.dry_run
    )

    if result.success:
        message = f"✅ {result.action}: {result.file_path}"
        click.echo(message)
        logger.info(
            f"File import successful | action={result.action} | file={result.file_path}"
        )

        if result.page_id:
            click.echo(f"   Page ID: {result.page_id}")
            logger.debug(
                f"Created/updated page | page_id={result.page_id} | "
                f"file={result.file_path}"
            )
    else:
        message = f"❌ Failed: {result.file_path}"
        click.echo(message)
        click.echo(f"   Error: {result.error}")
        logger.error(
            f"File import failed | file={result.file_path} | error={result.error}"
        )


def _import_directory(
    service: MarkdownImportService,
    directory_path: Path,
    database_id: str,
    options: ImportOptions,
    verbose: bool = False,
) -> None:
    """Import all Markdown files from a directory."""
    logger = get_logger(__name__)

    logger.info(
        f"Starting directory import | path={directory_path} | "
        f"recursive={options.recursive}"
    )
    click.echo(f"Importing from {directory_path}...")
    if options.recursive:
        click.echo("   (including subdirectories)")

    # Validate database schema with sample files
    sample_files = list(directory_path.glob("*.md"))[:5]
    if sample_files:
        logger.debug(
            f"Validating database schema with {len(sample_files)} sample files"
        )
        _, warnings = service.validate_database_schema(database_id, sample_files)
        if warnings:
            click.echo("⚠️  Schema warnings:")
            for warning in warnings:
                click.echo(f"   - {warning}")
                logger.warning(f"Schema validation warning: {warning}")
            if not click.confirm("Continue anyway?"):
                logger.info("Import cancelled by user due to schema warnings")
                return

    # Import all files
    logger.info(
        f"Beginning batch import | mode={options.mode} | dry_run={options.dry_run}"
    )
    result = service.import_directory(
        directory_path,
        database_id,
        options.recursive,
        options.mode,
        options.identifier,
        options.dry_run,
    )

    # Log summary
    logger.info(
        f"Directory import completed | total={result.total_files} | "
        f"successful={result.successful} | failed={result.failed}"
    )

    # Display summary
    click.echo("\n📊 Import Summary:")
    click.echo(f"   Total files: {result.total_files}")
    click.echo(f"   ✅ Successful: {result.successful}")
    click.echo(f"   ❌ Failed: {result.failed}")

    # Show details for failed imports
    if result.failed > 0:
        click.echo("\n❌ Failed imports:")
        for r in result.results:
            if not r.success:
                click.echo(f"   - {r.file_path}: {r.error}")
                logger.error(
                    f"Failed import details | file={r.file_path} | error={r.error}"
                )

    # Show created/updated pages
    if not options.dry_run and result.successful > 0:
        click.echo("\n✅ Imported pages:")
        for r in result.results:
            if r.success:
                click.echo(f"   - {r.action}: {r.file_path.name}")
                if r.page_id:
                    page_id_clean = r.page_id.replace("-", "")
                    notion_url = f"https://notion.so/{page_id_clean}"
                    click.echo(f"     {notion_url}")
                    logger.debug(
                        f"Successfully imported | action={r.action} | "
                        f"file={r.file_path.name} | page_id={r.page_id}"
                    )


@cli.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "-d", "--database", required=True, help="URL of the Notion database to import into"
)
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recursively import Markdown files from subdirectories",
)
@click.option(
    "--mode",
    type=click.Choice(["merge", "replace", "skip"]),
    default="merge",
    help="How to handle existing pages: merge (default), replace, or skip",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be imported without making changes",
)
@click.option(
    "--identifier",
    type=click.Choice(["auto", "id", "title"]),
    default="auto",
    help="How to identify existing pages: auto (default), id, or title",
)
@CONTEXT
def import_command(  # noqa: PLR0913
    ctx: Config,
    path: str,
    database: str,
    recursive: bool,
    mode: str,
    dry_run: bool,
    identifier: str,
) -> None:
    """Import Markdown files into a Notion database.

    Arguments:
        PATH: File or directory path containing Markdown files to import

    Examples:
        # Import a single file
        thought import file.md --database "https://notion.so/..."

        # Import all files from a directory
        thought import ./docs/ --database "..." --recursive

        # Preview import without making changes
        thought import ./docs/ --database "..." --dry-run
    """
    # Create options object
    options = ImportOptions(
        path=path,
        database=database,
        recursive=recursive,
        mode=mode,
        dry_run=dry_run,
        identifier=identifier,
    )

    # Initialize the import service
    service = MarkdownImportService()

    # Extract database ID from URL
    database_id = notion_url_to_uuid(database)

    # Convert path to Path object
    import_path = Path(path)

    if dry_run:
        click.echo("🔍 DRY RUN MODE - No changes will be made")

    try:
        if import_path.is_file():
            _import_single_file(service, import_path, database_id, options, ctx.verbose)
        else:
            _import_directory(service, import_path, database_id, options, ctx.verbose)

    except Exception as e:
        click.echo(f"❌ Import failed: {e!s}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
