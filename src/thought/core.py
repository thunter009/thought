"""Main module. If include_dataclasses_scaffolding is enabled, you will see Data Class scaffolding here"""
from dataclasses import dataclass
from datetime import datetime

from thought.utils import (default_field, now)
from thought.client import get_client

@dataclass
class BaseExample:
    """
    The BaseExample object. Contains helper functions and generalized metadata
    """
    run_time: datetime = default_field(now(), init=False, repr=False)
    

