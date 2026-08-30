"""
Module: data_pipeline.py
Author: Zyad Sowilam
Description: Unified function to fetch data from multiple sources into a Pandas DataFrame.
Sources supported: Tableau Cloud (view/datasource), Hyper, CSV/Parquet, SQL Server/Oracle.
"""

import os
import tempfile
from typing import Optional
from .tableau_client.tableau_cloud import TableauCloudClient
from .tableau_client.hyper_reader import read_hyper_file
from .tableau_client.local_csv import read_csv, read_parquet
from .tableau_client.sql_client import read_sql

def get_data(source: str, **kwargs):
    """
    Unified function to get data from multiple sources.

    Parameters:
        source: str, one of ["tableau_cloud", "hyper", "csv", "parquet", "sql"]
        kwargs: source-specific arguments
            Tableau Cloud:
                server, site_content_url, token_name, token_secret
                view_id (preferred) OR datasource_id
                as_hyper (bool, optional)
            Hyper:
                path
            CSV/Parquet:
                path
            SQL:
                query, conn_str
    Returns:
        pd.DataFrame
    """
    if source == "tableau_cloud":
        client = TableauCloudClient(
            server=kwargs.get("server"),
            site_content_url=kwargs.get("site_content_url"),
            token_name=kwargs.get("token_name"),
            token_secret=kwargs.get("token_secret")
        )
        client.sign_in()

        df = None

        # 1️⃣ Pull from view
        view_id = kwargs.get("view_id")
        if view_id:
            df = client.pull_view_full_data(view_id, as_hyper=kwargs.get("as_hyper", False))

        # 2️⃣ Pull from datasource (Hyper download)
        elif kwargs.get("datasource_id"):
            datasource_id = kwargs.get("datasource_id")
            # Download Hyper from Tableau Cloud into a private temp file, then remove it
            fd, hyper_path = tempfile.mkstemp(suffix=".hyper")
            os.close(fd)
            try:
                client.download_datasource_hyper(datasource_id, hyper_path)
                df = read_hyper_file(hyper_path)
            finally:
                os.remove(hyper_path)

        else:
            client.sign_out()
            raise ValueError("You must provide either view_id or datasource_id for Tableau Cloud")

        client.sign_out()
        return df

    elif source == "hyper":
        path = kwargs.get("path")
        return read_hyper_file(path)

    elif source == "csv":
        path = kwargs.get("path")
        return read_csv(path)

    elif source == "parquet":
        path = kwargs.get("path")
        return read_parquet(path)

    elif source == "sql":
        query = kwargs.get("query")
        conn_str = kwargs.get("conn_str")
        return read_sql(query, conn_str)

    else:
        raise ValueError(f"Unknown source: {source}")