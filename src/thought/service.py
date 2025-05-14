from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, TypeVar

import pandas as pd
from requests_oauthlib import OAuth1Session

from thought.core import CollectionExtension, Metadata
from thought.exceptions import ServiceNotRegisteredError
from thought.settings import SERVICES_REGISTERED

T = TypeVar("T", bound="GenericService")


@dataclass
class GenericService:
    _type: str = field(default="generic", init=False)
    metadata: Metadata = field(default_factory=Metadata, init=False, repr=False)

    RESERVED_WORDS: list[str] = field(
        default_factory=lambda: [
            "call",
            "load",
            "client",
            "data",
            "authorize",
            "metadata",
        ],
        init=False,
        repr=False,
    )

    @staticmethod
    def _sanitize_input(input_: str) -> str:
        return input_.replace("-", "_")

    def __getitem__(self, key: str) -> Any:
        public = [
            x for x in self.__dir__() if not (x.startswith("_") or x.endswith("_"))
        ]

        # filter all caps variables
        temp = [x for x in public if x != x.upper()]

        # filter reserved words
        temp = [x for x in temp if x not in self.RESERVED_WORDS]

        action_map = {k: self.__getattribute__(self._sanitize_input(k)) for k in temp}

        return action_map.get(self._sanitize_input(key))

    def call(self, action: str, **kwargs: Any) -> Any:
        """
        Calls service method
        """
        try:
            return self[action](**kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to call action {action}") from e

    def load(
        self, data: pd.DataFrame, target: CollectionExtension, style: str = "append"
    ) -> None:
        """
        Loads provided pandas dataframe to notion collection
        """
        for _ in data.iterrows():
            pass


@dataclass
class APIService(GenericService):
    _type: str = field(default="api", init=False)
    _auth_type: str = field(default="oauth", init=False, repr=False)
    client: OAuth1Session | None = field(default=None, init=False, repr=False)
    data: pd.DataFrame | None = field(default=None, init=False, repr=False)

    def authorize(self) -> None:
        """
        Authorizes APIService object for access. If successful the `client` property
        should contain an authorized requests session.

        To be implemented by sub-classes
        """
        pass


@dataclass
class Registry:
    """
    Service registry which holds all properly registered services
    """

    services: dict[str, Any] = field(default_factory=dict, init=False)

    def __getitem__(self, key: str) -> Any:
        return self.services.get(key)

    def register(
        self, service_name: str, return_service_obj: bool = True
    ) -> Any | None:
        """
        Registers a defined service object from a provided service name string
        """
        if service_name not in SERVICES_REGISTERED.keys():
            raise ServiceNotRegisteredError(
                f"{service_name} is not a properly configured service"
            )

        # watch out! risky code ahead!
        to_import = f"thought.services.{service_name}"
        try:
            output = eval(
                f"{import_module(to_import)}.{SERVICES_REGISTERED[service_name]}"
            )
        except ModuleNotFoundError as err:
            raise ServiceNotRegisteredError(
                f"{service_name} is not a properly configured service"
            ) from err

        # register the requested service
        self.services[service_name] = output

        # return service object by default
        if return_service_obj:
            return output
        return None
