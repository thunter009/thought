from abc import ABC
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import pandas as pd
import pytoml as toml
from requests_oauthlib import OAuth1Session
from thought.core import Metadata, CollectionExtension
from thought.exceptions import ServiceNotRegisteredException
from thought.settings import SERVICES_REGISTERED, NOTION_SERVICES_DIRECTORY
from thought.utils import default_field


@dataclass
class GenericService:
    _type: str = default_field('generic', init=False)
    metadata: Metadata = default_field(Metadata(), init=False, repr=False)

    RESERVED_WORDS: List[str] = default_field([
        'call',
        'load',
        'client',
        'data',
        'authorize',
        'metadata'
    ], init=False, repr=False)

    @staticmethod
    def _sanitize_input(input_):
        return input_.replace('-', '_')

    def __getitem__(self, key) -> Any:
        public = [x for x in self.__dir__() 
                  if not (x.startswith('_') 
                  or x.endswith('_'))
        ]

        # filter all caps variables
        temp = [x for x in public 
                if x != x.upper()
        ]

        # filter reserved words
        temp = [x for x in temp 
                if x not in self.RESERVED_WORDS
        ]

        action_map = {k: self.__getattribute__(self._sanitize_input(k))
                                               for k in temp}

        return action_map.get(self._sanitize_input(key))

    def call(self, action: str, **kwargs):
        """
        Calls service method
        """
        try:
            return self[action](**kwargs)
        except Exception as e:
            import ipdb
            ipdb.set_trace()

    def load(self, data: pd.DataFrame, target: CollectionExtension, style="append"):
        """
        Loads provided pandas dataframe to notion collection
        """
        for row in data.iterrows():          
            import ipdb; ipdb.set_trace()


@dataclass
class APIService(GenericService):

    _type: str = default_field('api', init=False)
    _auth_type: str = default_field('oauth', init=False, repr=False)
    client: OAuth1Session = default_field(None, init=False, repr=False)
    data: pd.DataFrame = default_field(None, init=False, repr=False)

    def authorize(self) -> None:
        """
        Authorizes APIService object for access. If successful the `client` property should contain an authorized requests session.

        To be implemented by sub-classes
        """
        pass


@dataclass
class Registry:
    """
    Service registry which holds all properly registered services
    """
    services: Dict[str, Any] = default_field({}, init=False)  # a dictionary of service names: service objects

    def __getitem__(self, key):
        return self.services.get(key)

    def register(self, service_name: str, return_service_obj: bool = True):
        """
        Registers a defined service object from a provided service name string
        """
        if service_name not in SERVICES_REGISTERED.keys():
            raise ServiceNotRegisteredException(
                f"{service_name} is not a properly configured service")

        # watch out! risky code ahead!
        to_import = f'thought.services.{service_name}'
        try:
            sn = import_module(to_import)
            output = eval(f'sn.{SERVICES_REGISTERED[service_name]}')
        except ModuleNotFoundError:
            raise ServiceNotRegisteredException(
                f"{service_name} is not a properly configured service")

        # register the requested service
        self.services[service_name] = output

        # return service object by default
        if return_service_obj:
            return output
