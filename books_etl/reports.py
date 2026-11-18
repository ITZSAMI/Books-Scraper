"""Loads the named queries in sql/reports.sql and runs them."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

REPORTS_PATH = Path(__file__).resolve().parent.parent / "sql" / "reports.sql"


def load_queries(path: Path = REPORTS_PATH) -> dict[str, str]:
    """Split the file on '-- name: <name>' lines into {name: sql}."""
    parts = re.split(r"^-- name:\s*(\w+)\s*$", path.read_text(), flags=re.MULTILINE)
    # parts = [preamble, name1, sql1, name2, sql2, ...]
    return {name: sql.strip() for name, sql in zip(parts[1::2], parts[2::2], strict=True)}


def run_report(conn: sqlite3.Connection, name: str) -> pd.DataFrame:
    queries = load_queries()
    if name not in queries:
        raise KeyError(f"unknown report {name!r}; choose from {sorted(queries)}")
    return pd.read_sql_query(queries[name], conn)
