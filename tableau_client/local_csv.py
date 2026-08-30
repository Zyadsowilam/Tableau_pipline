"""
Module: local_csv.py
Author: Zyad Sowilam
Description: Simple utility to read CSV or Parquet files.
"""

import pandas as pd
from pathlib import Path

def read_csv(path: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    return pd.read_csv(path)

def read_parquet(path: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    return pd.read_parquet(path)