"""Console script for thought."""
import logging
import sys

import click

from thought.client import NotionAPIClient
from thought.core import CollectionExtension, CollectionViewExtension, Output
from thought.exceptions import (
    CollectionMustAlreadyExistException,
    LoadDestinationNotUniqueException,
)
from thought.service import GenericService, Registry
from thought.services.instapaper import InstapaperAPI
from thought.settings import (
    LOGGING_DATE_FORMAT,
    LOGGING_FORMAT,
    LOGGING_PATH,
    NOTION_SERVICES_DIRECTORY,
    SERVICES_CONFIGURATION_PATH,
)

FILE_NAME = __name__
logging.basicConfig(level=logging.INFO,
                    datefmt=LOGGING_DATE_FORMAT,
                    format=LOGGING_FORMAT,
                    handlers=[
                        logging.FileHandler(
                            f"{LOGGING_PATH}/{FILE_NAME}.log",
                            encoding=None,
                            delay=False),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger()

class Config:
    """Configuration Object"""

    def add_url_prefix(url):
        prefix = 'https://www.notion.so/'
        return prefix + url

CONTEXT = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option('--service_config_directory', default='../services/', help='Directory where {service}.toml configuration file is loaded from. Defaults to \'/services/\'')
@CONTEXT
def cli(ctx,
        service_config_directory):
    '''
        Thought - Notion CLI
    '''
    ctx.service_config_directory = service_config_directory
    ctx.registry = Registry()
    ctx.client = NotionAPIClient().client


@cli.command('dedupe')
@click.argument('collection_url')
@click.option('-f', '--field', multiple=True, help='Deduplication field. Can be one or many. Defaults to all collection object properties')
@CONTEXT
def dedupe(ctx,
           collection_url: str,
           field):
    '''
        Removes dupelicate items in a specified collection view

        Arguments
        ---------

        collection: A URL to a collection view
    '''
    client = ctx.client
    col_view = client.get_collection_view(collection_url)
    collection = CollectionExtension(col_view.collection)
    deduped_df = collection.dedupe(comparison_fields=list(field)) if field else collection.dedupe()
    collection.sync(deduped_df, id_col='id') # call to sync collection objects property data with dataframe records using object id as key
    # above does nothing...
    breakpoint()

@cli.command('sort')
@click.argument('url')
@click.option('-f', '--field', default="tags", help='The field to sort on. Defaults to "tags"')
@click.option('--sort_multiselect_schema_values', is_flag=True, default=False, help="If the provided field is a multi-select and the --sort_multiselect_schema_values flag is passed, \
                                                                                     sorts the possible values of the multi-select field before sorting the entire collection view by \
                                                                                     the multi-select field")
@click.option('--sort_multiselect_record_values', is_flag=True, default=False, help="If the provided field is a multi-select and the --sort_multiselect_record_values flag is passed, \
                                                                                     sorts each record's multi-select field value before sorting the entire collection view by \
                                                                                     the multi-select field")
@CONTEXT
def sort(ctx,
         url,
         field,
         sort_field_values,
         sort_multiselect_values) -> None:
    '''
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
        
    '''
    client = ctx.client
    col_view = client.get_collection_view(url)
    collection_view = CollectionViewExtension(col_view)
    collection_view.sort(field=field, 
                         sort_multiselect_values=sort_multiselect_values,
                         )

@cli.command('sync')
@click.argument('service')#, help='The service you want to sync data from')
@click.argument('action')#, help='The sync action you want to perform with the specified service')
@click.option('--target_collection', default=NOTION_SERVICES_DIRECTORY, help='The target page you want the output of the sync action to persist in. Will create a Collection in this object with the service name as the title.')
# @click.option('--service_definition', default=SERVICES_CONFIGURATION_PATH, help='The target collection you want the output of the sync action to persist in')
@CONTEXT
def sync(ctx,
         service: str,
         action: str,
         target_collection: str) -> None:
    '''
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
    '''
    client = ctx.client
    registry = ctx.registry
    registered_service = registry.register(service)
    service_instance = registered_service()

    if not service_instance:
        logging.INFO("%s service not defined and configured properly. Please refer to docs.".format(service))
    
    if not service_instance[action]:
        logging.INFO("%s action not defined for specified service. Please refer to docs.".format(action))

    data = service_instance.call(action, folder='archive') #TODO: onboard arbitrary key: values from click options here
    breakpoint()
    
    page = client.get_block(target_collection)
    collection_name = f'{service}_{action}'

    # filter through possible collections in the service pages children, collection
    collection = [x for x in page.children if collection_name == x.title]

    if not collection:
        #TODO: create new collection if nothing matches our {service}_{action} nameing pattern -- blocked by API support as of 8/11/20
        raise CollectionMustAlreadyExistException(f"{collection_name} must already exist")
    
    if len(collection) > 1:
        raise LoadDestinationNotUniqueException(f"Target collection must be unique: remove existing collection {collection_name} or pick a new function name")
    
    # drop to base object since we're confident this list should only contain 1 object
    collection = collection[0].collection
    service_instance.load(data, collection)


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
