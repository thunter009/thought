import os

from thought.utils import load_env

load_env()

# loggings settings
LOGGING_FORMAT = (
    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"  # noqa: E501
)
LOGGING_DATE_FORMAT = "%m/%d/%Y %I:%M:%S %p"
LOGGING_FILE = "log.txt"
LOGGING_PATH = "."

# general settings
NOTION_ACCESS_TOKEN = os.getenv("NOTION_ACCESS_TOKEN")
NOTION_SERVICES_DIRECTORY = "Services-008f866a7d564af6ad9e49cd83Lef68788b"


# data source providers / register external services here
SERVICES_REGISTERED = {"instapaper": "InstapaperAPI"}
SERVICES_CONFIGURATION_PATH = ["services"]

# instapaper settings
INSTAPAPER_BASE_URL = "https://www.instapaper.com/api"
INSTAPAPER_BOOKMARKS_DIRECTORY = "archive"
INSTAPAPER_CONSUMER_ID = os.getenv("INSTAPAPER_CONSUMER_ID")
INSTAPAPER_CONSUMER_SECRET = os.getenv("INSTAPAPER_CONSUMER_SECRET")
INSTAPAPER_USER = os.getenv("INSTAPAPER_USER")
INSTAPAPER_PASS = os.getenv("INSTAPAPER_PASS")
