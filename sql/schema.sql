-- Schema for the books ETL. Safe to run on every start (IF NOT EXISTS).

-- One row per pipeline run: when it ran, what it did, and whether it worked.
CREATE TABLE IF NOT EXISTS etl_runs (
    run_id          TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    rows_extracted  INTEGER,
    rows_loaded     INTEGER,
    rows_rejected   INTEGER,
    error           TEXT
);

-- Current state of every book. The URL is the natural key, so re-running
-- the pipeline updates rows instead of duplicating them.
CREATE TABLE IF NOT EXISTS books (
    url             TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    price_pence     INTEGER NOT NULL CHECK (price_pence > 0),
    currency        TEXT NOT NULL,
    rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    in_stock        INTEGER NOT NULL CHECK (in_stock IN (0, 1)),
    first_seen_run  TEXT NOT NULL REFERENCES etl_runs (run_id),
    last_seen_run   TEXT NOT NULL REFERENCES etl_runs (run_id),
    updated_at      TEXT NOT NULL
);

-- Every price change, so history is never lost when a row is updated.
CREATE TABLE IF NOT EXISTS price_history (
    url             TEXT NOT NULL REFERENCES books (url),
    run_id          TEXT NOT NULL REFERENCES etl_runs (run_id),
    price_pence     INTEGER NOT NULL,
    recorded_at     TEXT NOT NULL,
    PRIMARY KEY (url, run_id)
);

-- Rows the transform step could not convert, with the reason.
CREATE TABLE IF NOT EXISTS rejected_rows (
    run_id          TEXT NOT NULL REFERENCES etl_runs (run_id),
    url             TEXT,
    reason          TEXT NOT NULL,
    raw_json        TEXT NOT NULL
);
