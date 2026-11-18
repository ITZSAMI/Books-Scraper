"""Apache Airflow DAG that schedules the pipeline daily and checks the result.

Not needed to run the project locally. It shows how the same code would be
orchestrated in production: the ETL runs as one task, then a data-quality
task queries etl_runs and fails the DAG if the run did not succeed or
loaded too few rows.

Requires Airflow 2.4+ with this repository on the PYTHONPATH.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from airflow.decorators import dag, task

DB_PATH = "/opt/airflow/data/books.db"
MIN_ROWS = 900  # the catalogue has 1,000 books


@dag(
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["etl", "books"],
)
def books_etl():
    @task
    def run_pipeline() -> str:
        from books_etl import pipeline

        summary = pipeline.run(db_path=DB_PATH, csv_path=None)
        return summary.run_id

    @task
    def check_run(run_id: str) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            status, rows_loaded = conn.execute(
                "SELECT status, rows_loaded FROM etl_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if status != "succeeded":
            raise ValueError(f"run {run_id} ended with status {status}")
        if rows_loaded < MIN_ROWS:
            raise ValueError(f"run {run_id} loaded {rows_loaded} rows, expected >= {MIN_ROWS}")

    check_run(run_pipeline())


books_etl()
