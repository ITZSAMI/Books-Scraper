"""Load step: write the batch to SQLite in a single transaction.

* Idempotent: books are upserted on their URL, so running twice does not
  create duplicates.
* Traceable: each row records the run that first and last saw it, price
  changes go to price_history, and rejected rows are stored with a reason.
* Atomic: either the whole batch is written or none of it is.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from books_etl.transform import Book, RejectedRow

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def start_run(conn: sqlite3.Connection, run_id: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO etl_runs (run_id, started_at, status) VALUES (?, ?, 'running')",
            (run_id, now_utc()),
        )


def finish_run(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    rows_extracted: int | None = None,
    rows_loaded: int | None = None,
    rows_rejected: int | None = None,
    error: str | None = None,
) -> None:
    with conn:
        conn.execute(
            """UPDATE etl_runs
               SET finished_at = ?, status = ?, rows_extracted = ?,
                   rows_loaded = ?, rows_rejected = ?, error = ?
               WHERE run_id = ?""",
            (now_utc(), status, rows_extracted, rows_loaded, rows_rejected, error, run_id),
        )


def load_books(
    conn: sqlite3.Connection,
    run_id: str,
    books: list[Book],
    rejected: list[RejectedRow],
) -> int:
    """Upsert books and record price changes and rejects. Returns rows written."""
    ts = now_utc()
    with conn:  # one transaction: commits on success, rolls back on any error
        for book in books:
            previous = conn.execute(
                "SELECT price_pence FROM books WHERE url = ?", (book.url,)
            ).fetchone()

            conn.execute(
                """INSERT INTO books (url, title, price_pence, currency, rating, in_stock,
                                      first_seen_run, last_seen_run, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (url) DO UPDATE SET
                       title = excluded.title,
                       price_pence = excluded.price_pence,
                       currency = excluded.currency,
                       rating = excluded.rating,
                       in_stock = excluded.in_stock,
                       last_seen_run = excluded.last_seen_run,
                       updated_at = excluded.updated_at""",
                (
                    book.url,
                    book.title,
                    book.price_pence,
                    book.currency,
                    book.rating,
                    int(book.in_stock),
                    run_id,
                    run_id,
                    ts,
                ),
            )

            if previous is None or previous[0] != book.price_pence:
                conn.execute(
                    "INSERT INTO price_history (url, run_id, price_pence, recorded_at) "
                    "VALUES (?, ?, ?, ?)",
                    (book.url, run_id, book.price_pence, ts),
                )

        conn.executemany(
            "INSERT INTO rejected_rows (run_id, url, reason, raw_json) VALUES (?, ?, ?, ?)",
            [(run_id, r.raw.url, r.reason, json.dumps(asdict(r.raw))) for r in rejected],
        )
    return len(books)


def export_csv(conn: sqlite3.Connection, csv_path: str | Path) -> int:
    """Write the current books table to CSV, with prices in pounds for readability."""
    df = pd.read_sql_query(
        """SELECT title, price_pence / 100.0 AS price, currency, rating,
                  in_stock, url
           FROM books ORDER BY title""",
        conn,
    )
    df["in_stock"] = df["in_stock"].astype(bool)
    df.to_csv(csv_path, index=False)
    return len(df)
