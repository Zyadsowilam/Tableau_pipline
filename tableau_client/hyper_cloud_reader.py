"""
Module: hyper_cloud_reader.py
Author: Zyad Sowilam
Description: Read Tableau Cloud .hyper datasource bytes into Pandas.
"""

from tableauhyperapi import HyperProcess, Connection, Telemetry, TableName, HyperException
import pandas as pd
import os
import tempfile

def read_hyper_bytes(hyper_bytes: bytes, table_name: TableName = TableName("Extract", "Extract")) -> pd.DataFrame:
    """
    Read a .hyper file from bytes into Pandas.

    :param hyper_bytes: Bytes of a .hyper file
    :param table_name: Table name inside the Hyper file
    :return: Pandas DataFrame
    """
    fd, temp_path = tempfile.mkstemp(suffix=".hyper")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(hyper_bytes)

        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            with Connection(endpoint=hyper.endpoint, database=temp_path) as connection:
                try:
                    rows = connection.execute_list_query(f"SELECT * FROM {table_name}")
                    columns = [col.name for col in connection.catalog.get_table_definition(table_name).columns]
                    df = pd.DataFrame(rows, columns=columns)
                except HyperException as e:
                    raise RuntimeError(f"Error reading Hyper table: {e}")
    finally:
        os.remove(temp_path)
    return df