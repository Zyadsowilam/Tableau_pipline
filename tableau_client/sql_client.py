"""
Module: sql_client.py
Author: Zyad Sowilam
Description: Connect and query SQL Server or Oracle using SQLAlchemy.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine


DEFAULT_ORACLE_CLIENT_PATHS = [
    r"C:\Program Files\Tableau\Tableau 2024.3\bin",
    r"C:\app\root\product\11.2.0\client_1\BIN",
    r"C:\DevSuiteHome_1\BIN",
]


def detect_oracle_client_lib_dir() -> str | None:
    env_value = os.getenv("ORACLE_CLIENT_LIB_DIR", "").strip()
    if env_value:
        return env_value

    for candidate in DEFAULT_ORACLE_CLIENT_PATHS:
        if Path(candidate, "oci.dll").exists():
            return candidate
    return None


def init_oracle_client_if_needed(lib_dir: str | None = None) -> None:
    """
    Initialize python-oracledb in thick mode when an Oracle client is available.
    Safe to call multiple times.
    """
    try:
        import oracledb
    except ImportError:
        return

    if lib_dir is None:
        lib_dir = detect_oracle_client_lib_dir()

    if not lib_dir:
        return

    try:
        if not oracledb.is_thin_mode():
            return
    except Exception:
        pass

    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
    except Exception as exc:
        message = str(exc).lower()
        if "already been initialized" not in message:
            raise


def build_oracle_connection_string(
    username: str,
    password: str,
    host: str,
    service_name: str,
    port: int = 1521,
) -> str:
    """
    Build a SQLAlchemy Oracle connection string using the modern ``oracledb`` driver.
    """
    return (
        f"oracle+oracledb://{quote_plus(username)}:{quote_plus(password)}"
        f"@{host}:{port}/?service_name={quote_plus(service_name)}"
    )


def read_sql(query: str, connection_string: str) -> pd.DataFrame:
    """
    Execute SQL query and return Pandas DataFrame.

    :param query: SQL query string
    :param connection_string: SQLAlchemy connection string
        Example SQL Server:
        "mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17+for+SQL+Server"
        Example Oracle:
        "oracle+oracledb://user:pass@host:1521/?service_name=prod"
    """
    if connection_string.startswith("oracle+oracledb://"):
        init_oracle_client_if_needed()

    engine = create_engine(connection_string, pool_pre_ping=True)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df
