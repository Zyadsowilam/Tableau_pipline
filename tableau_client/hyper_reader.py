"""
Module: hyper_reader.py
Author: Zyad Sowilam
Description: Functions to read .hyper files using Tableau Hyper API.
"""

from tableauhyperapi import HyperProcess, Connection, Telemetry, TableName
import pandas as pd
from pathlib import Path
import os
from typing import Optional

def read_hyper_file(hyper_path: Optional[str] = None) -> pd.DataFrame:
    """
    Read a .hyper file into a Pandas DataFrame.

    :param hyper_path: Path to .hyper file. If None, reads from HYPER_PATH environment variable.
    :return: Pandas DataFrame
    """
    if not hyper_path:
        hyper_path = os.getenv("HYPER_PATH")
        if not hyper_path:
            raise ValueError("hyper_path not provided and HYPER_PATH not set in environment")
    hyper_path = Path(hyper_path)
    if not hyper_path.exists():
        raise FileNotFoundError(f"{hyper_path} does not exist")

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=hyper_path) as connection:
            # Most Tableau extracts use this:
            table_name = TableName("Extract", "Extract")
            rows = connection.execute_list_query(f"SELECT * FROM {table_name}")
            columns = [col.name for col in connection.catalog.get_table_definition(table_name).columns]
            df = pd.DataFrame(rows, columns=columns)
    return df