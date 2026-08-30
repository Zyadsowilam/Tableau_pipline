"""
Module: tableau_cloud.py
Author: Zyad Sowilam
Description: Functions to authenticate, fetch views, and pull data from Tableau Cloud.
"""

import os
import tempfile
import requests
import pandas as pd
from io import StringIO
from typing import List, Optional

class TableauCloudClient:
    def __init__(self, server: str, site_content_url: str, token_name: str, token_secret: str, api_version: str = "3.19"):
        """
        Initialize Tableau Cloud client.

        :param server: Tableau server URL
        :param site_content_url: Tableau site content URL
        :param token_name: Personal Access Token name
        :param token_secret: Personal Access Token secret
        :param api_version: REST API version
        """
        if not server.lower().startswith("https://"):
            raise ValueError(
                f"Tableau server URL must use https:// to avoid sending the PAT secret in cleartext, got: {server!r}"
            )
        self.server = server
        self.site_content_url = site_content_url
        self.token_name = token_name
        self.token_secret = token_secret
        self.api_version = api_version
        self.site_id = None
        self.token = None
        self.headers = None

    def sign_in(self):
        """Sign in to Tableau Cloud and store authentication token."""
        url = f"{self.server}/api/{self.api_version}/auth/signin"
        payload = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.token_secret,
                "site": {"contentUrl": self.site_content_url}
            }
        }
        res = requests.post(url, json=payload, headers={"Accept": "application/json"})
        res.raise_for_status()
        data = res.json()
        self.token = data["credentials"]["token"]
        self.site_id = data["credentials"]["site"]["id"]
        self.headers = {"X-Tableau-Auth": self.token, "Accept": "application/json"}

    def sign_out(self):
        """Sign out of Tableau Cloud."""
        if self.headers:
            url = f"{self.server}/api/{self.api_version}/auth/signout"
            requests.post(url, headers=self.headers)

    def fetch_views(self) -> List[dict]:
        """
        Fetch all views in the site with pagination.

        :return: List of view dictionaries
        """
        all_views = []
        page_number = 1
        page_size = 100
        while True:
            url = f"{self.server}/api/{self.api_version}/sites/{self.site_id}/views?pageNumber={page_number}&pageSize={page_size}"
            res = requests.get(url, headers=self.headers)
            res.raise_for_status()
            views_page = res.json()["views"]["view"]
            all_views.extend(views_page)
            total_available = int(res.json()["pagination"]["totalAvailable"])
            if len(all_views) >= total_available:
                break
            page_number += 1
        return all_views

    def find_view_id(self, content_url: str) -> Optional[str]:
        """
        Find the view ID by content URL.

        :param content_url: Exact content URL or endswith
        :return: View ID or None
        """
        for v in self.fetch_views():
            if v["contentUrl"].endswith(content_url):
                return v["id"]
        return None

    def pull_view_csv(self, view_id: str) -> pd.DataFrame:
        """
        Pull data from a view as CSV into a Pandas DataFrame.

        :param view_id: Tableau view ID
        :return: Pandas DataFrame
        """
        url = f"{self.server}/api/{self.api_version}/sites/{self.site_id}/views/{view_id}/data"
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        return pd.read_csv(StringIO(res.text))
    
    def pull_view_full_data(self, view_id, as_hyper=False):
        """
        Pull underlying data of a view (ignores worksheet filters)
        """
        # Use the correct token attribute
        headers = {
            "X-Tableau-Auth": self.token,  # was self.auth_token
            "Accept": "application/json"
        }

        if as_hyper:
            url = f"{self.server}/api/{self.api_version}/sites/{self.site_id}/views/{view_id}/data?format=hyper"
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            fd, local_path = tempfile.mkstemp(suffix=".hyper")
            os.close(fd)
            try:
                with open(local_path, "wb") as f:
                    f.write(r.content)
                from .hyper_reader import read_hyper_file
                return read_hyper_file(local_path)
            finally:
                os.remove(local_path)
        else:
            url = f"{self.server}/api/{self.api_version}/sites/{self.site_id}/views/{view_id}/data?format=csv"
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            from io import StringIO
            return pd.read_csv(StringIO(r.text))
    def download_datasource_hyper(self, datasource_id: str, save_path: str):
        """
        Download Tableau Cloud datasource as .hyper file.
        
        :param datasource_id: ID of the datasource
        :param save_path: Local path to save the Hyper file
        """
        url = f"{self.server}/api/{self.api_version}/sites/{self.site_id}/datasources/{datasource_id}/content"
        headers = {"X-Tableau-Auth": self.token}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(r.content)
            