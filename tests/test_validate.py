from books_etl.transform import Book, RejectedRow
from books_etl.validate import validate
from tests.conftest import raw


def book(url="u1", price_pence=1000, rating=3, currency="GBP"):
    return Book(
        url=url, title="T", price_pence=price_pence, currency=currency, rating=rating, in_stock=True
    )


def test_clean_batch_passes():
    assert validate([book("a"), book("b")], []).ok


def test_empty_batch_fails():
    report = validate([], [])
    assert not report.ok
    assert "at least 1" in report.errors[0]


def test_too_many_rejects_fails():
    rejected = [RejectedRow(raw(url=str(i)), "bad") for i in range(2)]
    report = validate([book(str(i)) for i in range(10)], rejected, max_reject_ratio=0.05)
    assert any("rejected" in e for e in report.errors)


def test_duplicates_fail():
    report = validate([book("same"), book("same")], [])
    assert any("duplicate" in e for e in report.errors)


def test_bad_values_fail():
    report = validate([book("a", price_pence=0), book("b", rating=7)], [])
    assert any("price" in e for e in report.errors)
    assert any("rating" in e for e in report.errors)


def test_mixed_currencies_fail():
    report = validate([book("a"), book("b", currency="EUR")], [])
    assert any("currencies" in e for e in report.errors)
