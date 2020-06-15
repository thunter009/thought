import copy
from dataclasses import field
from datetime import (
    datetime,
    timezone
)
from pathlib import Path
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
