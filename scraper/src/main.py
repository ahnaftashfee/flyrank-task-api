from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(+https://github.com/ahnaftashfee/flyrank-task-api)"
)
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5
RETRY_DELAY_SECONDS = 1.0
MAX_CATALOGUE_PAGES = 3
BROKEN_TEST_URL = urljoin(
    BASE_URL, "catalogue/definitely-not-a-real-book/index.html"
)

SCRAPER_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = SCRAPER_ROOT / "cache"
OUTPUT_DIR = SCRAPER_ROOT / "output"


class BookRecord(BaseModel):
    """Validated form of one scraped book record."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    product_url: str
    price_text: str = Field(pattern=r"^£\d+\.\d{2}$")
    price_gbp: float = Field(ge=0)
    availability_text: str = Field(min_length=1)
    rating_text: str = Field(pattern=r"^(One|Two|Three|Four|Five)$")
    description: str | None
    source_page: str
    fetched_at: datetime

    @field_validator("product_url", "source_page")
    @classmethod
    def require_https_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("URL must start with https://")
        return value


@dataclass(frozen=True)
class FetchResult:
    html: str
    fetched_at: datetime
    from_cache: bool


class FetchError(Exception):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(reason)
        self.url = url
        self.reason = reason


class PoliteFetcher:
    """Fetches HTML with identification, pacing, timeout, retry, and caching."""

    def __init__(self, cache_dir: Path = CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.last_request_finished_at: float | None = None
        self.pages_fetched = 0
        self.cache_hits = 0
        self.network_requests = 0

    def fetch(self, url: str, cache_name: str | None = None) -> FetchResult:
        cache_path = self.cache_dir / (cache_name or self._detail_cache_name(url))
        if cache_path.exists():
            html = cache_path.read_text(encoding="utf-8")
            self.cache_hits += 1
            fetched_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC)
            print(f"CACHE HIT bytes={len(html.encode('utf-8'))} url={url}")
            return FetchResult(html, fetched_at, True)

        for attempt in (1, 2):
            self._wait_before_request()
            self.network_requests += 1

            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            except requests.Timeout as error:
                self.last_request_finished_at = time.monotonic()
                if attempt == 1:
                    print(f"RETRY reason=timeout attempt=2 url={url}")
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                raise FetchError(url, "request timed out after one retry") from error
            except requests.RequestException as error:
                self.last_request_finished_at = time.monotonic()
                raise FetchError(url, f"request failed: {error}") from error

            self.last_request_finished_at = time.monotonic()

            if response.status_code == 200:
                response.encoding = response.apparent_encoding or response.encoding
                html = response.text
                cache_path.write_text(html, encoding="utf-8")
                self.pages_fetched += 1
                fetched_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC)
                print(f"FETCH bytes={len(html.encode('utf-8'))} url={url}")
                return FetchResult(html, fetched_at, False)

            if 500 <= response.status_code <= 599 and attempt == 1:
                print(
                    f"RETRY status={response.status_code} attempt=2 url={url}"
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            raise FetchError(url, f"HTTP {response.status_code}; not cached")

        raise FetchError(url, "fetch failed")

    def _wait_before_request(self) -> None:
        if self.last_request_finished_at is None:
            return
        elapsed = time.monotonic() - self.last_request_finished_at
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)

    @staticmethod
    def _detail_cache_name(url: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        slug = Path(url.rstrip("/")).parent.name or "book"
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug).strip("-")[:60]
        return f"book-{safe_slug}-{digest}.html"


def clean_text(value: str) -> str:
    return " ".join(value.split())


def normalize_price(price_text: str) -> float:
    match = re.fullmatch(r"£(\d+\.\d{2})", clean_text(price_text))
    if match is None:
        raise ValueError(f"invalid GBP price: {price_text!r}")
    return float(match.group(1))


def discover_books(
    fetcher: PoliteFetcher,
) -> tuple[dict[str, str], int, int]:
    """Follow the site's next links for exactly three catalogue pages."""

    page_url = START_URL
    discovered = 0
    unique_books: dict[str, str] = {}
    catalogue_pages = 0

    while page_url and catalogue_pages < MAX_CATALOGUE_PAGES:
        page_number = catalogue_pages + 1
        result = fetcher.fetch(page_url, f"catalogue-page-{page_number}.html")
        soup = BeautifulSoup(result.html, "html.parser")
        catalogue_pages += 1

        for anchor in soup.select("article.product_pod h3 a[href]"):
            discovered += 1
            product_url = urljoin(page_url, str(anchor["href"]))
            unique_books.setdefault(product_url, page_url)

        next_anchor = soup.select_one("li.next a[href]")
        page_url = (
            urljoin(page_url, str(next_anchor["href"]))
            if next_anchor is not None
            else ""
        )

    return unique_books, catalogue_pages, discovered


def extract_raw_book(
    html: str,
    product_url: str,
    source_page: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("article.product_page")
    if product is None:
        raise ValueError("product area not found")

    title_element = product.select_one(".product_main h1")
    price_element = product.select_one(".product_main .price_color")
    availability_element = product.select_one(".product_main .availability")
    rating_element = product.select_one(".product_main .star-rating")

    if not all(
        (title_element, price_element, availability_element, rating_element)
    ):
        raise ValueError("one or more required product fields are missing")

    rating_text = next(
        (
            class_name
            for class_name in rating_element.get("class", [])
            if class_name != "star-rating"
        ),
        "",
    )
    description_heading = product.select_one("#product_description")
    description_element = (
        description_heading.find_next_sibling("p")
        if description_heading is not None
        else None
    )

    return {
        "title": clean_text(title_element.get_text(" ", strip=True)),
        "product_url": product_url,
        "price_text": clean_text(price_element.get_text(" ", strip=True)),
        "availability_text": clean_text(
            availability_element.get_text(" ", strip=True)
        ),
        "rating_text": rating_text,
        "description": (
            clean_text(description_element.get_text(" ", strip=True))
            if description_element is not None
            else None
        ),
        "source_page": source_page,
        "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
    }


def validate_book(raw: dict[str, Any]) -> BookRecord:
    return BookRecord.model_validate(
        {**raw, "price_gbp": normalize_price(raw["price_text"])}
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def run(include_broken_url: bool = False) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    started_timer = time.monotonic()
    fetcher = PoliteFetcher()
    records_by_url: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    failed_page_details: list[dict[str, str]] = []

    books, catalogue_pages, discovered = discover_books(fetcher)
    unique_discovered = len(books)
    print(
        f"catalogue_pages={catalogue_pages} "
        f"discovered={discovered} unique_urls={unique_discovered}"
    )

    attempted_books = dict(books)
    if include_broken_url:
        attempted_books[BROKEN_TEST_URL] = START_URL

    first_raw_record: dict[str, Any] | None = None
    invalid_records = 0
    failed_pages = 0

    for product_url, source_page in attempted_books.items():
        try:
            result = fetcher.fetch(product_url)
            raw_record = extract_raw_book(
                result.html,
                product_url,
                source_page,
                result.fetched_at,
            )
            if first_raw_record is None:
                first_raw_record = raw_record
            record = validate_book(raw_record)
            records_by_url[record.product_url] = record.model_dump(mode="json")
        except FetchError as error:
            failed_pages += 1
            detail = {"url": error.url, "reason": error.reason}
            failed_page_details.append(detail)
            errors.append({"product_url": error.url, "reason": error.reason})
            print(f"SKIP reason={error.reason!r} url={error.url}")
        except (ValueError, ValidationError) as error:
            invalid_records += 1
            errors.append({"product_url": product_url, "reason": str(error)})
            print(f"INVALID reason={str(error)!r} url={product_url}")

    records = list(records_by_url.values())
    write_json(OUTPUT_DIR / "books.json", records)
    write_json(OUTPUT_DIR / "errors.json", errors)

    duration_seconds = round(time.monotonic() - started_timer, 3)
    report = {
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "duration_seconds": duration_seconds,
        "catalogue_pages": catalogue_pages,
        "discovered_urls": discovered,
        "unique_urls": unique_discovered,
        "attempted_detail_pages": len(attempted_books),
        "detail_pages": len(records),
        "pages_fetched": fetcher.pages_fetched,
        "cache_hits": fetcher.cache_hits,
        "network_requests": fetcher.network_requests,
        "valid_records": len(records),
        "invalid_records": invalid_records,
        "failed_pages": failed_pages,
        "failed_page_details": failed_page_details,
    }
    write_json(OUTPUT_DIR / "run-report.json", report)

    if first_raw_record is not None:
        print("raw_record=" + json.dumps(first_raw_record, ensure_ascii=False))
    print(f"detail_pages={len(records)}")
    print("run_report=" + json.dumps(report, ensure_ascii=False))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Politely scrape the first three Books to Scrape catalogue pages."
    )
    parser.add_argument(
        "--include-broken-url",
        action="store_true",
        help=(
            "Add one deliberate 404 to prove that a failed page does not stop "
            "the run."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run(include_broken_url=arguments.include_broken_url)
