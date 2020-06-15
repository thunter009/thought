"""Console script for thought."""
import sys
import click


import logging
from thought.settings import LOGGING_DATE_FORMAT, LOGGING_FORMAT, LOGGING_PATH

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


@click.command()
def main(args=None):
    """Console script for thought."""
    click.echo("Replace this message by putting your code into "
               "thought.cli.main")
    click.echo("See click documentation at https://click.palletsprojects.com/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
