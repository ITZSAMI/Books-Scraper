"""Command line entry point.

python -m books_etl run [--db books.db] [--csv books.csv] [--max-pages N]
python -m books_etl report <name> [--db books.db]
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

from books_etl import pipeline, reports


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
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if args.command == "run":
        try:
            summary = pipeline.run(args.db, args.csv or None, args.max_pages)
        except Exception:
            return 1
        print(summary)
        return 0

    with sqlite3.connect(args.db) as conn:
        print(reports.run_report(conn, args.name).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
