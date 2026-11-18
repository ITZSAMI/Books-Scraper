"""Validate step: batch-level data-quality checks that run before anything
is written. If a check fails, the load is skipped and the run is marked
failed, so bad data never reaches the database."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from books_etl.transform import Book, RejectedRow


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(
    books: list[Book],
    rejected: list[RejectedRow],
    min_rows: int = 1,
    max_reject_ratio: float = 0.05,
) -> ValidationReport:
    report = ValidationReport()
    total = len(books) + len(rejected)

    if len(books) < min_rows:
        report.errors.append(f"expected at least {min_rows} valid rows, got {len(books)}")

    if total and len(rejected) / total > max_reject_ratio:
        report.errors.append(
            f"{len(rejected)} of {total} rows rejected, above the {max_reject_ratio:.0%} limit"
        )

    duplicates = [url for url, n in Counter(b.url for b in books).items() if n > 1]
    if duplicates:
        report.errors.append(f"{len(duplicates)} duplicate URLs, e.g. {duplicates[0]}")

    bad_prices = [b.url for b in books if b.price_pence <= 0]
    if bad_prices:
        report.errors.append(f"{len(bad_prices)} rows with non-positive price")

    bad_ratings = [b.url for b in books if not 1 <= b.rating <= 5]
    if bad_ratings:
        report.errors.append(f"{len(bad_ratings)} rows with rating outside 1-5")

    currencies = {b.currency for b in books}
    if len(currencies) > 1:
        report.errors.append(f"mixed currencies in one batch: {sorted(currencies)}")

    return report
