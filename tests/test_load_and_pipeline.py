import csv
import sqlite3
from functools import partial

import pytest

from books_etl import load, pipeline, reports
from books_etl.extract import extract
from books_etl.transform import Book, RejectedRow
from tests.conftest import BASE, raw


def book(url, price_pence=1000):
    return Book(
        url=url,
        title=f"Title {url}",
        price_pence=price_pence,
        currency="GBP",
        rating=4,
        in_stock=True,
    )


@pytest.fixture
def conn(tmp_path):
    c = load.connect(tmp_path / "test.db")
    yield c
    c.close()


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_load_is_idempotent(conn):
    for run_id in ("r1", "r2"):
        load.start_run(conn, run_id)
        load.load_books(conn, run_id, [book("a"), book("b")], [])

    assert count(conn, "books") == 2
    first, last = conn.execute(
        "SELECT first_seen_run, last_seen_run FROM books WHERE url = 'a'"
    ).fetchone()
    assert (first, last) == ("r1", "r2")
    assert count(conn, "price_history") == 2  # unchanged prices are not re-recorded


def test_price_change_is_recorded(conn):
    load.start_run(conn, "r1")
    load.load_books(conn, "r1", [book("a", 1000)], [])
    load.start_run(conn, "r2")
    load.load_books(conn, "r2", [book("a", 1250)], [])

    assert conn.execute("SELECT price_pence FROM books WHERE url='a'").fetchone()[0] == 1250
    history = conn.execute(
        "SELECT run_id, price_pence FROM price_history ORDER BY run_id"
    ).fetchall()
    assert history == [("r1", 1000), ("r2", 1250)]

    df = reports.run_report(conn, "price_changes")
    assert list(df["old_price"].dropna()) == [10.0]
    assert list(df["new_price"]) == [10.0, 12.5]


def test_rejected_rows_are_stored(conn):
    load.start_run(conn, "r1")
    load.load_books(conn, "r1", [book("a")], [RejectedRow(raw(url="x"), "unrecognised rating")])
    assert conn.execute("SELECT url, reason FROM rejected_rows").fetchone() == (
        "x",
        "unrecognised rating",
    )


def test_load_is_atomic(conn):
    load.start_run(conn, "r1")
    bad = Book(url="b", title="T", price_pence=-5, currency="GBP", rating=3, in_stock=True)
    with pytest.raises(sqlite3.IntegrityError):  # CHECK (price_pence > 0)
        load.load_books(conn, "r1", [book("a"), bad], [])
    assert count(conn, "books") == 0  # "a" was rolled back too


def test_pipeline_end_to_end(tmp_path, fake_session):
    db, out = tmp_path / "books.db", tmp_path / "books.csv"
    extractor = partial(extract, BASE + "page-1.html", session=fake_session, delay_seconds=0)

    summary = pipeline.run(db, out, extractor=extractor)

    assert (summary.status, summary.rows_loaded, summary.rows_rejected) == ("succeeded", 5, 0)
    with sqlite3.connect(db) as c:
        assert count(c, "books") == 5
        assert c.execute("SELECT status FROM etl_runs").fetchone()[0] == "succeeded"
        for name in reports.load_queries():
            reports.run_report(c, name)  # every report query runs on real data
    rows = list(csv.DictReader(out.open()))
    assert len(rows) == 5
    attic = next(r for r in rows if r["title"] == "A Light in the Attic")
    assert attic["price"] == "51.77"


def test_failed_validation_marks_run_failed_and_loads_nothing(tmp_path):
    db = tmp_path / "books.db"
    with pytest.raises(pipeline.ValidationFailed):
        pipeline.run(db, None, extractor=lambda max_pages=None: [])

    with sqlite3.connect(db) as c:
        status, error = c.execute("SELECT status, error FROM etl_runs").fetchone()
        assert status == "failed"
        assert "at least 1" in error
        assert count(c, "books") == 0
