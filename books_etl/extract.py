"""Extract step: download catalogue pages and pull out the raw fields.

Nothing is converted here. Prices, ratings and availability stay as the
text the website shows, so the transform step owns every data rule.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

START_URL = "https://books.toscrape.com/catalogue/page-1.html"


@dataclass(frozen=True)
class RawBook:
    """One book exactly as it appears on the page."""

    url: str
    title: str
    price_text: str
    rating_text: str
    availability_text: str


class ExtractError(RuntimeError):
    """A page could not be downloaded after all retries."""


def fetch_page(
    session: requests.Session,
    url: str,
    retries: int = 3,
    backoff_seconds: float = 1.0,
    timeout: float = 10.0,
) -> str | None:
    """Download one page.

    Returns None for 404 (no such page). Retries server errors and network
    failures with exponential backoff, then raises ExtractError.
    """
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code == 404:
                return None
            if response.status_code >= 500:
                raise requests.HTTPError(f"server error {response.status_code}")
            response.raise_for_status()
            # The site serves UTF-8; setting it explicitly avoids "Â£" in prices.
            response.encoding = "utf-8"
            return response.text
        except requests.RequestException as exc:
            if attempt == retries:
                raise ExtractError(f"giving up on {url} after {retries} attempts: {exc}") from exc
            wait = backoff_seconds * 2 ** (attempt - 1)
            log.warning(
                "attempt %d/%d for %s failed (%s), retrying in %.1fs",
                attempt,
                retries,
                url,
                exc,
                wait,
            )
            time.sleep(wait)
    return None  # unreachable, keeps type checkers happy


def parse_page(html: str, page_url: str) -> tuple[list[RawBook], str | None]:
    """Parse one catalogue page. Returns its books and the next page URL (if any)."""
    soup = BeautifulSoup(html, "html.parser")
    books = []
    for pod in soup.select("article.product_pod"):
        link = pod.h3.a
        rating_tag = pod.select_one("p.star-rating")
        # class="star-rating Three" -> "Three"
        rating_words = [c for c in rating_tag.get("class", []) if c != "star-rating"]
        books.append(
            RawBook(
                url=urljoin(page_url, link["href"]),
                title=link.get("title", link.get_text()).strip(),
                price_text=pod.select_one("p.price_color").get_text(strip=True),
                rating_text=rating_words[0] if rating_words else "",
                availability_text=pod.select_one("p.availability").get_text(strip=True),
            )
        )
    next_link = soup.select_one("li.next > a")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return books, next_url


def extract(
    start_url: str = START_URL,
    max_pages: int | None = None,
    session: requests.Session | None = None,
    delay_seconds: float = 0.2,
) -> list[RawBook]:
    """Follow the "next" links from start_url and return every book found."""
    session = session or requests.Session()
    url: str | None = start_url
    pages = 0
    books: list[RawBook] = []
    while url and (max_pages is None or pages < max_pages):
        html = fetch_page(session, url)
        if html is None:
            log.info("page not found, stopping: %s", url)
            break
        page_books, url = parse_page(html, url)
        books.extend(page_books)
        pages += 1
        log.info("page %d: %d books", pages, len(page_books))
        if url and delay_seconds:
            time.sleep(delay_seconds)  # be polite to the site
    log.info("extracted %d books from %d pages", len(books), pages)
    return books
