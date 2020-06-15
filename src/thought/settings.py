import os
from thought.utils import load_env

load_env()

# loggings settings
LOGGING_FORMAT = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"  # noqa: E501
LOGGING_DATE_FORMAT = '%m/%d/%Y %I:%M:%S %p'
LOGGING_FILE = 'log.txt'
LOGGING_PATH = '.'

# general settings
NOTION_ACCESS_TOKEN = os.getenv("NOTION_ACCESS_TOKEN")