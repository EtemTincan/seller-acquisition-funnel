"""Thin DuckDB layer: load the Parquet files, run the SQL files in /sql."""
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = "2018-08-31"  # last day with complete order data


def read_sql(name: str) -> str:
    return (ROOT / "sql" / f"{name}.sql").read_text()


def connect(window: int, skip_top: bool) -> duckdb.DuckDBPyConnection:
    """Open an in-memory database with the base views built for these settings."""
    con = duckdb.connect()
    for table in ("leads", "deals", "sales"):
        path = (ROOT / "data" / f"{table}.parquet").as_posix()
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM '{path}'")
    # Views cannot hold prepared parameters, so the settings are inlined.
    # All three are fixed values chosen in the app, never free text.
    base = (
        read_sql("00_base")
        .replace("$cutoff", f"'{CUTOFF}'")
        .replace("$window", str(int(window)))
        .replace("$skip_top", str(int(skip_top)))
    )
    con.execute(base)
    return con


def run(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    return con.execute(read_sql(name).replace("$cutoff", f"'{CUTOFF}'")).df()
