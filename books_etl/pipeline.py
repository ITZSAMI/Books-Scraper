"""Runs the four steps in order and records the outcome in etl_runs."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from books_etl import load
from books_etl.extract import RawBook, extract
from books_etl.transform import transform
from books_etl.validate import validate

log = logging.getLogger(__name__)


class ValidationFailed(RuntimeError):
    pass


@dataclass
class RunSummary:
    run_id: str
    status: str
    rows_extracted: int
    rows_loaded: int
    rows_rejected: int


def run(
    db_path: str | Path = "books.db",
    csv_path: str | Path | None = "books.csv",
    max_pages: int | None = None,
    extractor: Callable[..., list[RawBook]] = extract,
) -> RunSummary:
    run_id = uuid.uuid4().hex[:12]
    conn = load.connect(db_path)
    load.start_run(conn, run_id)
    log.info("run %s started", run_id)

    raw: list[RawBook] = []
    try:
        raw = extractor(max_pages=max_pages)
        books, rejected = transform(raw)
        for r in rejected:
            log.warning("rejected %s: %s", r.raw.url, r.reason)

        report = validate(books, rejected)
        if not report.ok:
            raise ValidationFailed("; ".join(report.errors))

        loaded = load.load_books(conn, run_id, books, rejected)
        load.finish_run(conn, run_id, "succeeded", len(raw), loaded, len(rejected))
        if csv_path:
            load.export_csv(conn, csv_path)
        log.info("run %s succeeded: %d loaded, %d rejected", run_id, loaded, len(rejected))
        return RunSummary(run_id, "succeeded", len(raw), loaded, len(rejected))
    except Exception as exc:
        load.finish_run(conn, run_id, "failed", rows_extracted=len(raw), error=str(exc))
        log.error("run %s failed: %s", run_id, exc)
        raise
    finally:
        conn.close()
