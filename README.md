# Books ETL

![CI](https://github.com/ITZSAMI/Books-Scraper/actions/workflows/ci.yml/badge.svg)

A small but complete ETL pipeline in Python and SQL. It collects every book
from [books.toscrape.com](https://books.toscrape.com) (a site built for
scraping practice), turns the raw page text into typed records, checks the
batch for data-quality problems, and loads it into a SQLite database where
every row can be traced back to the run that produced it.

The project started as a single scraping script that wrote a CSV. It was
rebuilt to follow the patterns used in production data pipelines:
separate extract / transform / validate / load steps, idempotent loads,
an audit trail of runs, tests that never touch the network, and an
Airflow DAG for scheduling.

## Architecture

```
books.toscrape.com
        │
        ▼
 ┌─────────────┐   RawBook (text as shown on the page)
 │  extract.py │   follows pagination, retries with backoff, polite delay
 └──────┬──────┘
        ▼
 ┌──────────────┐  Book (typed) + RejectedRow (with reason)
 │ transform.py │  "£51.77" → 5177 pence, "Three" → 3, "In stock" → True
 └──────┬───────┘
        ▼
 ┌─────────────┐   batch checks: row count, reject ratio, duplicates,
 │ validate.py │   price > 0, rating 1–5, single currency
 └──────┬──────┘   → any failure stops the run before anything is written
        ▼
 ┌─────────────┐   one transaction: upsert books, record price changes,
 │   load.py   │   store rejects, then export CSV
 └──────┬──────┘
        ▼
   SQLite (books.db) ──► sql/reports.sql ──► python -m books_etl report …
```

`pipeline.py` runs the steps in order and records each run's outcome in the
`etl_runs` table. `dags/books_etl_dag.py` schedules the same code daily in
Apache Airflow, with a follow-up data-quality task.

## Data model

| Table | Purpose |
|---|---|
| `etl_runs` | One row per run: start/end time, status (`running` / `succeeded` / `failed`), row counts, error message |
| `books` | Current state of each book, keyed by URL. `first_seen_run` and `last_seen_run` link back to `etl_runs` |
| `price_history` | A row whenever a book's price is new or has changed, so history survives updates |
| `rejected_rows` | Rows the transform step could not convert, with the reason and the raw input as JSON |

Full definitions with constraints: [`sql/schema.sql`](sql/schema.sql).

## Design decisions

- **Money as integers.** Prices are stored in pence (`price_pence INTEGER`),
  parsed with `Decimal`, never `float`, so totals and comparisons are exact.
- **Idempotent loads.** Books are upserted on their URL
  (`INSERT … ON CONFLICT DO UPDATE`), so re-running the pipeline never
  creates duplicates.
- **Atomic loads.** The whole batch is written in one transaction. If any
  row breaks a database constraint, nothing from that run is kept.
- **Nothing is dropped silently.** Every extracted row either loads or lands
  in `rejected_rows` with a reason. If more than 5% are rejected, the run fails.
- **Validate before load.** Bad batches are stopped before they reach the
  database, and the failure is recorded in `etl_runs.error`.
- **Tests without the network.** Extraction is tested against HTML fixtures
  through a fake HTTP session, including retry and pagination behaviour.

## Quick start

Requires Python 3.11+.

```bash
git clone https://github.com/ITZSAMI/Books-Scraper.git
cd Books-Scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m books_etl run                 # full catalogue → books.db + books.csv
python -m books_etl run --max-pages 2   # quick run, first two pages only
python -m books_etl report price_by_rating
```

`python books_scraper.py` still works and runs the full pipeline.

### Reports

All report queries live in [`sql/reports.sql`](sql/reports.sql):

| Name | What it shows | SQL used |
|---|---|---|
| `price_by_rating` | Count, average, min and max price per star rating | `GROUP BY`, aggregates |
| `top_per_rating` | Three most expensive books in each rating | `ROW_NUMBER() OVER (PARTITION BY …)` |
| `price_bands` | Books per price band and share of the catalogue | `CASE`, `SUM(…) OVER ()` |
| `price_changes` | Old and new price for books that changed between runs | `LAG()`, subquery, join |
| `run_history` | Last ten pipeline runs and their outcome | |

## Running the tests

```bash
pytest -v          # 37 tests, no network needed
ruff check .       # lint
```

CI runs lint and tests on Python 3.11–3.15 for every push and pull request.

## Runbook

**Checking whether the last run worked**

```bash
python -m books_etl report run_history
```

`status` is `succeeded`, `failed` or `running`. A run stuck at `running`
means the process was killed before it could record its result. The books
load itself is a single transaction, so the database is never left
half-written; re-run to get a clean `succeeded` record.

**A run failed**

1. Read the `error` column in `run_history`.
2. `giving up on … after 3 attempts`: the site was down or unreachable.
   Re-run later. Nothing was written, so re-running is safe.
3. `rows rejected, above the 5% limit`: the site's markup or data format
   probably changed. Look at the reasons:
   ```bash
   sqlite3 books.db "SELECT reason, COUNT(*) FROM rejected_rows GROUP BY reason;"
   ```
   Fix the parser in `transform.py` (or `extract.py` if fields are missing),
   add a test for the new format, then re-run.
4. `duplicate URLs` or `mixed currencies`: inspect the extracted data before
   changing any limits. These checks exist to catch real problems.

**Re-running**

Always safe. Existing books are updated in place, and only real price
changes are added to `price_history`.

## Project structure

```
books_etl/
  extract.py      download pages, parse raw fields, retries
  transform.py    raw text → typed Book, or a RejectedRow with a reason
  validate.py     batch-level data-quality checks
  load.py         SQLite schema, upserts, run tracking, CSV export
  pipeline.py     runs the steps and records the outcome
  reports.py      runs named queries from sql/reports.sql
  __main__.py     command line (run / report)
sql/
  schema.sql      tables and constraints
  reports.sql     analysis queries
dags/
  books_etl_dag.py  Airflow DAG: daily run + data-quality check
tests/            pytest suite with HTML fixtures
.github/workflows/ci.yml
```

## Possible next steps

- Load into a cloud warehouse (e.g. Snowflake or Postgres) behind the same
  `load.py` interface.
- Scrape each book's detail page for UPC, category and stock count.
- Alert on failed runs (e.g. Slack webhook from the Airflow DAG).
