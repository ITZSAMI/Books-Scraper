import pytest

from books_etl import extract as extract_mod
from books_etl.extract import ExtractError, extract, fetch_page, parse_page
from tests.conftest import BASE, FIXTURES, FakeResponse, FakeSession


def test_parse_page_reads_every_field():
    html = (FIXTURES / "page-1.html").read_text(encoding="utf-8")
    books, next_url = parse_page(html, BASE + "page-1.html")

    assert len(books) == 3
    first = books[0]
    # full title comes from the title attribute, not the cut-off link text
    assert first.title == "A Light in the Attic"
    assert first.url == BASE + "a-light-in-the-attic_1000/index.html"
    assert first.price_text == "£51.77"
    assert first.rating_text == "Three"
    assert first.availability_text == "In stock"
    assert books[2].availability_text == "Out of stock"
    assert next_url == BASE + "page-2.html"


def test_last_page_has_no_next_url():
    html = (FIXTURES / "page-2.html").read_text(encoding="utf-8")
    _, next_url = parse_page(html, BASE + "page-2.html")
    assert next_url is None


def test_extract_follows_pagination(fake_session):
    books = extract(BASE + "page-1.html", session=fake_session, delay_seconds=0)
    assert len(books) == 5
    assert fake_session.calls == [BASE + "page-1.html", BASE + "page-2.html"]


def test_extract_respects_max_pages(fake_session):
    books = extract(BASE + "page-1.html", max_pages=1, session=fake_session, delay_seconds=0)
    assert len(books) == 3


def test_fetch_returns_none_for_404(fake_session):
    assert fetch_page(fake_session, BASE + "page-99.html") is None


def test_fetch_retries_server_errors(monkeypatch):
    monkeypatch.setattr(extract_mod.time, "sleep", lambda s: None)
    url = BASE + "page-1.html"
    session = FakeSession({url: [FakeResponse(500), FakeResponse(503)]})
    assert "product_pod" in fetch_page(session, url, retries=3)
    assert len(session.calls) == 3


def test_fetch_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(extract_mod.time, "sleep", lambda s: None)
    url = BASE + "page-1.html"
    session = FakeSession({url: [FakeResponse(500)] * 3})
    with pytest.raises(ExtractError):
        fetch_page(session, url, retries=3)
