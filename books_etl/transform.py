"""Transform step: turn raw page text into typed, analysis-ready records.

Money is stored as an integer number of minor units (pence), never as a
float, so sums and comparisons are exact. Rows that cannot be converted are
not dropped silently: they are returned as rejects with a reason, so every
input row is accounted for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from books_etl.extract import RawBook

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
CURRENCY_SYMBOLS = {"£": "GBP", "€": "EUR", "$": "USD"}
PRICE_PATTERN = re.compile(r"([£€$])\s*(\d+(?:\.\d{1,2})?)")


@dataclass(frozen=True)
class Book:
    url: str
    title: str
    price_pence: int
    currency: str
    rating: int
    in_stock: bool


@dataclass(frozen=True)
class RejectedRow:
    raw: RawBook
    reason: str


class TransformError(ValueError):
    pass


def parse_price(text: str) -> tuple[int, str]:
    """'£51.77' -> (5177, 'GBP'). Also tolerates mis-decoded text like 'Â£51.77'."""
    match = PRICE_PATTERN.search(text)
    if not match:
        raise TransformError(f"unrecognised price {text!r}")
    symbol, number = match.groups()
    try:
        amount = Decimal(number)
    except InvalidOperation as exc:
        raise TransformError(f"unrecognised price {text!r}") from exc
    pence = int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return pence, CURRENCY_SYMBOLS[symbol]


def parse_rating(text: str) -> int:
    """'Three' -> 3."""
    try:
        return RATING_WORDS[text.strip().capitalize()]
    except KeyError as exc:
        raise TransformError(f"unrecognised rating {text!r}") from exc


def parse_in_stock(text: str) -> bool:
    """'In stock' -> True, 'Out of stock' -> False."""
    normalised = " ".join(text.lower().split())
    if normalised.startswith("in stock"):
        return True
    if normalised.startswith("out of stock"):
        return False
    raise TransformError(f"unrecognised availability {text!r}")


def transform_one(raw: RawBook) -> Book:
    title = " ".join(raw.title.split())
    if not title:
        raise TransformError("empty title")
    price_pence, currency = parse_price(raw.price_text)
    return Book(
        url=raw.url,
        title=title,
        price_pence=price_pence,
        currency=currency,
        rating=parse_rating(raw.rating_text),
        in_stock=parse_in_stock(raw.availability_text),
    )


def transform(raw_books: list[RawBook]) -> tuple[list[Book], list[RejectedRow]]:
    """Convert every row. Returns (good rows, rejected rows with reasons)."""
    books: list[Book] = []
    rejected: list[RejectedRow] = []
    for raw in raw_books:
        try:
            books.append(transform_one(raw))
        except TransformError as exc:
            rejected.append(RejectedRow(raw=raw, reason=str(exc)))
    return books, rejected
