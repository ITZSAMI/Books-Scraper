"""Shared test helpers.

Tests never touch the network. The pages in tests/fixtures/ are small
catalogue pages written to match the markup of books.toscrape.com, served
by a fake HTTP session.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from books_etl.extract import RawBook

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://books.toscrape.com/catalogue/"


class FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text
        self.encoding = None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


class FakeSession:
    """Serves fixture pages by URL. `script` can queue responses for a URL
    (e.g. two 500s then a 200) to test retries."""

    def __init__(self, script: dict[str, list[FakeResponse]] | None = None):
        self.script = script or {}
        self.calls: list[str] = []

    def get(self, url: str, timeout: float) -> FakeResponse:
        self.calls.append(url)
        if self.script.get(url):
            return self.script[url].pop(0)
        name = url.rsplit("/", 1)[-1]
        path = FIXTURES / name
        if url.startswith(BASE) and path.exists():
            return FakeResponse(200, path.read_text(encoding="utf-8"))
        return FakeResponse(404)


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


def raw(**overrides) -> RawBook:
    fields = dict(
        url=BASE + "book_1/index.html",
        title="A Book",
        price_text="£10.00",
        rating_text="Three",
        availability_text="In stock",
    )
    fields.update(overrides)
    return RawBook(**fields)
