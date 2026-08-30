# Tableau Data Pipeline

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/pandas-2.0%2B-150458)
![License](https://img.shields.io/badge/license-MIT-green)

A single, unified `get_data()` function that returns a **Pandas DataFrame** no matter where the data actually lives — Tableau Cloud, a `.hyper` extract, a CSV/Parquet file, or a SQL Server / Oracle database.

```python
df = get_data(source="tableau_cloud", view_id="...", server=..., site_content_url=..., token_name=..., token_secret=...)
df = get_data(source="hyper", path="extract.hyper")
df = get_data(source="csv", path="data.csv")
df = get_data(source="sql", query="SELECT * FROM sales", conn_str="...")
```

## Why

Every data source has its own client, its own auth flow, its own quirks. This project hides that behind one function so downstream code (notebooks, reports, dashboards) doesn't need to care where the data came from.

## Supported sources

| `source`         | What it does                                              | Required kwargs                                                          |
|-------------------|-------------------------------------------------------------|----------------------------------------------------------------------------|
| `tableau_cloud`   | Pulls a view's underlying data (or a datasource as Hyper)   | `server`, `site_content_url`, `token_name`, `token_secret`, `view_id` **or** `datasource_id` |
| `hyper`           | Reads a local `.hyper` extract                               | `path`                                                                      |
| `csv`             | Reads a local CSV file                                       | `path`                                                                      |
| `parquet`         | Reads a local Parquet file                                   | `path`                                                                      |
| `sql`             | Runs a query against SQL Server or Oracle via SQLAlchemy      | `query`, `conn_str`                                                        |

## Project layout

```
tableau_data_pipeline/
├── data_pipeline.py          # get_data() — the single entry point
├── mainExample.py            # usage example
├── oracle_schema_dump.py     # dumps an Oracle schema to module-grouped text files (for LLM context)
├── tableau_client/
│   ├── tableau_cloud.py      # Tableau Cloud REST API client
│   ├── hyper_reader.py       # local .hyper -> DataFrame
│   ├── hyper_cloud_reader.py # in-memory .hyper bytes -> DataFrame
│   ├── local_csv.py          # CSV / Parquet -> DataFrame
│   └── sql_client.py         # SQL Server / Oracle -> DataFrame
├── .env.example
└── requirements.txt
```

## Setup

```bash
git clone <this-repo-url>
cd tableau_data_pipeline

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env          # then fill in your own values
```

`.env` is git-ignored — never commit it. See [`.env.example`](.env.example) for every variable the project reads.

## Usage

**Tableau Cloud**

```python
import os
from dotenv import load_dotenv
from data_pipeline import get_data

load_dotenv()

df = get_data(
    source="tableau_cloud",
    view_id="<view-id>",
    server=os.getenv("TABLEAU_SERVER"),
    site_content_url=os.getenv("TABLEAU_SITE"),
    token_name=os.getenv("TABLEAU_TOKEN_NAME"),
    token_secret=os.getenv("TABLEAU_TOKEN_SECRET"),
)
```

> `TABLEAU_SERVER` must be `https://` — the client refuses to sign in over plain HTTP so the access token is never sent in cleartext.

**Local files**

```python
df_hyper   = get_data(source="hyper", path=os.getenv("HYPER_FILE_PATH"))
df_csv     = get_data(source="csv", path=os.getenv("LOCAL_CSV_PATH"))
df_parquet = get_data(source="parquet", path=os.getenv("LOCAL_PARQUET_PATH"))
```

**SQL Server / Oracle**

```python
df = get_data(
    source="sql",
    query="SELECT TOP 10 * FROM sales",
    conn_str=os.getenv("SQL_SERVER_CONN"),
)
```

## Security notes

- Credentials live only in `.env`, which is `.gitignore`d — never hardcode a token, password, or connection string in source.
- Tableau sign-in enforces `https://`.
- `oracle_schema_dump.py` uses bound parameters for schema names, not string interpolation.
- Downloaded `.hyper` files are written to a private temp path and deleted immediately after being read into a DataFrame — nothing lingers on disk.

## Requirements

- Python 3.10+
- Pandas 2.0+
- Tableau Hyper API ≥ 0.0.20000
- SQLAlchemy 2.0+ (with `pyodbc` for SQL Server, `oracledb` for Oracle)

See [`requirements.txt`](requirements.txt) for the full list.

## Extending

Add a new source by adding a branch to `get_data()` in [`data_pipeline.py`](data_pipeline.py) and a matching reader module under `tableau_client/`.
