from typing import Dict
from dataclasses import dataclass
from urllib.parse import urljoin

import requests as req
import pandas as pd
from requests_oauthlib import OAuth1Session
from thought.service import APIService
from thought.settings import (
    INSTAPAPER_BASE_URL,
    INSTAPAPER_BOOKMARKS_DIRECTORY,
    INSTAPAPER_CONSUMER_ID,
    INSTAPAPER_CONSUMER_SECRET,
    INSTAPAPER_PASS,
    INSTAPAPER_USER
)
from thought.utils import default_field


@dataclass
class InstapaperAPI(APIService):
    """
    Instapaper API Client object
    """
    _base_url: str = default_field(INSTAPAPER_BASE_URL, init=False, repr=False)
    _api_version: float = default_field(1, init=False, repr=False)
    
    CLIENT_KEY: str = default_field(INSTAPAPER_CONSUMER_ID, init=False, repr=False)
    CLIENT_SECRET: str = default_field(INSTAPAPER_CONSUMER_SECRET, init=False, repr=False)

    def __post_init__(self):
        self.authorize()

    def _concate_url_from_parts(self, suffix: str):
        return '/'.join([self._base_url, str(self._api_version), suffix])

    @staticmethod
    def _build_auth_params():
        return {
            'x_auth_username': INSTAPAPER_USER, 
            'x_auth_password': INSTAPAPER_PASS, 
            'x_auth_mode': 'client_auth'
        }

    def bookmarks_all(self, folder: str) -> pd.DataFrame:
        import ipdb; ipdb.set_trace()
        pass

    def _download_all_bookmark_highlights(self, bookmarks: str) -> pd.DataFrame:
        pass
    
    def authorize(self) -> None:
        '''
            Authorizes with instapaper oauth1 api

            Since this is just my personal account this is a simple oauth implmentation
        '''
        auth_suffix = 'oauth/access_token'
        auth_token_url = self._concate_url_from_parts(auth_suffix)
        session = OAuth1Session(self.CLIENT_KEY, client_secret=self.CLIENT_SECRET)
        params = self._build_auth_params()
        credentials = session.fetch_request_token(auth_token_url, params=params)

        if not session.authorized:
            raise CredentialsNotAuthorizedException("Not properly authorized, try again")
            import ipdb; ipdb.set_trace()

        self.client = session
    
    # def download(self, folder: str, include_highlights: bool = True) -> Dict[str, pd.DataFrame]:
    #     '''
    #         Downloads all instapaper bookmarks found in the supplied 'folder' parameter.

    #         If `include_highlights` is True then bookmark highlights will also be downloaded

    #     '''        
    #     # download all bookmarks
    #     bookmarks = self.bookmarks_all(folder)

    #     if include_highlights:
    #         # download all highlights for retrieved bookmarks
    #         self._download_all_bookmark_highlights(bookmarks)