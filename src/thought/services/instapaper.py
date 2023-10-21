from dataclasses import dataclass
from typing import Dict

import pandas as pd
from requests_oauthlib import OAuth1Session

from thought.exceptions import CredentialsNotAuthorizedException
from thought.service import APIService
from thought.settings import (
    INSTAPAPER_BASE_URL,
    INSTAPAPER_CONSUMER_ID,
    INSTAPAPER_CONSUMER_SECRET,
    INSTAPAPER_PASS,
    INSTAPAPER_USER,
)
from thought.utils import default_field

# CONSTANTS SPECIFIC TO THIS SERVICE
AUTH_MODE = "client_auth"
ENDPOINT_ALL_BOOKMARKS = "bookmarks/list"
ENDPOINT_AUTH = "oauth/access_token"


@dataclass
class InstapaperAPI(APIService):
    """
    Instapaper API Client object
    """

    _base_url: str = default_field(INSTAPAPER_BASE_URL, init=False, repr=False)
    _api_version: float = default_field(1, init=False, repr=False)

    def __post_init__(self):
        self.authorize()

    def _concate_url_from_parts(self, suffix: str):
        return "/".join([self._base_url, str(self._api_version), suffix])

    @staticmethod
    def _build_auth_params():
        return {
            "x_auth_username": INSTAPAPER_USER,
            "x_auth_password": INSTAPAPER_PASS,
            "x_auth_mode": AUTH_MODE,
        }

    def bookmarks(self, folder: str) -> pd.DataFrame:
        suffix = ENDPOINT_ALL_BOOKMARKS
        url = self._concate_url_from_parts(suffix)
        response = self.client.get(url, params={"folder_id": folder})

        # filter out account info & metadata
        metadata_keys = {"type"}
        account_keys = {"username", "user_id", "type", "subscription_is_active"}
        holder = []
        for line in response.json():
            line_keys = set(line.keys())
            if line_keys == metadata_keys or line_keys == account_keys:
                continue
            holder.append(line)
        return pd.DataFrame(holder)

    def authorize(self) -> None:
        """
        Authorizes with instapaper oauth1 api

        Since this is just my personal account this is a simple oauth implmentation
        """
        auth_suffix = ENDPOINT_AUTH
        auth_token_url = self._concate_url_from_parts(auth_suffix)
        session = OAuth1Session(
            INSTAPAPER_CONSUMER_ID, client_secret=INSTAPAPER_CONSUMER_SECRET
        )
        params = self._build_auth_params()
        credentials = session.fetch_request_token(auth_token_url, params=params)

        if not session.authorized:
            raise CredentialsNotAuthorizedException(
                "Not properly authorized, try again"
            )

        self.client = session
