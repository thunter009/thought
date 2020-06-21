"""Console script for thought."""
import logging
import sys

import click
from thought.client import NotionAPI
from thought.settings import (
    LOGGING_DATE_FORMAT,
    LOGGING_FORMAT,
    LOGGING_PATH
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
CONTEXT = click.make_pass_decorator(Config, ensure=True)


@click.group()
@CONTEXT
def cli(ctx):
    '''
        Thought - A Notion CLI
    '''

@cli.command('dedupe')
@click.argument('collection')
@CONTEXT
def dedupe(ctx,
           collection):
    '''
        Removes dupelicate items in a specified collection view

        Arguments
        ------

        collection: A URL to a collection view
    '''
    client = NotionAPI().client
    col_view = client.get_collection_view(collection)
    import ipdb; ipdb.set_trace()
    passs


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
