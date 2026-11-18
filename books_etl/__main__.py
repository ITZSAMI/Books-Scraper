"""Command line entry point.

python -m books_etl run [--db books.db] [--csv books.csv] [--max-pages N]
python -m books_etl report <name> [--db books.db]
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback

from books_etl import load, pipeline, reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="books_etl", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run the ETL pipeline")
    run_p.add_argument("--db", default="books.db")
    run_p.add_argument("--csv", default="books.csv", help="CSV export path ('' to skip)")
    run_p.add_argument("--max-pages", type=int, default=None)

    rep_p = sub.add_parser("report", help="run a named query from sql/reports.sql")
    rep_p.add_argument("name", choices=sorted(reports.load_queries()))
    rep_p.add_argument("--db", default="books.db")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,  # replace any handlers set up earlier, so progress always shows
    )

    if args.command == "run":
        try:
            summary = pipeline.run(args.db, args.csv or None, args.max_pages)
        except Exception:
            # Never fail silently: print the full error straight to stderr, so it
            # shows even if logging was configured elsewhere.
            print("run failed:", file=sys.stderr)
            traceback.print_exc()
            return 1
        print(summary)
        return 0

    # load.connect creates the tables if needed, so reports work on a new database.
    conn = load.connect(args.db)
    try:
        df = reports.run_report(conn, args.name)
    finally:
        conn.close()
    print(df.to_string(index=False) if not df.empty else "(no rows yet: run the pipeline first)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
