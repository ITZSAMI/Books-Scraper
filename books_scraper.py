"""Kept so the original command still works: `python books_scraper.py`.

It now runs the full ETL pipeline (see books_etl/) and writes books.db and books.csv.
"""

import sys

from books_etl.__main__ import main

if __name__ == "__main__":
    sys.exit(main(["run"]))
