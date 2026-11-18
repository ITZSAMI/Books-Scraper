import pytest

from books_etl.transform import (
    TransformError,
    parse_in_stock,
    parse_price,
    parse_rating,
    transform,
)
from tests.conftest import raw


@pytest.mark.parametrize(
    "text, expected",
    [
        ("£51.77", (5177, "GBP")),
        ("Â£51.77", (5177, "GBP")),  # mis-decoded pound sign still parses
        ("£10", (1000, "GBP")),
        ("£0.5", (50, "GBP")),
        ("€19.99", (1999, "EUR")),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text", ["", "51.77", "£", "free"])
def test_parse_price_rejects_bad_input(text):
    with pytest.raises(TransformError):
        parse_price(text)


@pytest.mark.parametrize("word, stars", [("One", 1), ("three", 3), ("Five", 5)])
def test_parse_rating(word, stars):
    assert parse_rating(word) == stars


def test_parse_rating_rejects_unknown_word():
    with pytest.raises(TransformError):
        parse_rating("Zero")


@pytest.mark.parametrize(
    "text, expected",
    [("In stock", True), ("  In   stock (22 available) ", True), ("Out of stock", False)],
)
def test_parse_in_stock(text, expected):
    assert parse_in_stock(text) is expected


def test_transform_splits_good_and_rejected_rows():
    books, rejected = transform(
        [
            raw(),
            raw(url="b", rating_text="Zero"),
            raw(url="c", title="   "),
        ]
    )
    assert len(books) == 1
    assert books[0].price_pence == 1000
    assert books[0].in_stock is True
    assert [r.raw.url for r in rejected] == ["b", "c"]
    assert "rating" in rejected[0].reason
    assert "title" in rejected[1].reason


def test_transform_normalises_whitespace_in_titles():
    books, _ = transform([raw(title="  A   Light\n in the Attic ")])
    assert books[0].title == "A Light in the Attic"
