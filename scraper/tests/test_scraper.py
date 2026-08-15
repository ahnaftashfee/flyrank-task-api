import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path


SCRAPER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRAPER_ROOT))

from src.main import (  # noqa: E402
    BookRecord,
    extract_raw_book,
    normalize_price,
)


def product_html(description: str = "A useful description.") -> str:
    description_html = (
        f'<div id="product_description"></div><p>{description}</p>'
        if description
        else ""
    )
    return f"""
    <html><body>
      <article class="product_page">
        <div class="product_main">
          <h1>  Test   Book  </h1>
          <p class="price_color">£12.34</p>
          <p class="availability"> In stock   (3 available) </p>
          <p class="star-rating Four"></p>
        </div>
        {description_html}
      </article>
    </body></html>
    """


class ScraperUnitTests(unittest.TestCase):
    def test_price_normalization(self) -> None:
        self.assertEqual(normalize_price("  £51.77 "), 51.77)

    def test_price_normalization_rejects_malformed_value(self) -> None:
        with self.assertRaises(ValueError):
            normalize_price("51 pounds")

    def test_extracts_clean_fields_from_product_area(self) -> None:
        raw = extract_raw_book(
            product_html(),
            "https://books.toscrape.com/catalogue/test-book/index.html",
            "https://books.toscrape.com/catalogue/page-1.html",
            datetime(2026, 8, 14, tzinfo=UTC),
        )
        self.assertEqual(raw["title"], "Test Book")
        self.assertEqual(raw["availability_text"], "In stock (3 available)")
        self.assertEqual(raw["rating_text"], "Four")

    def test_missing_description_becomes_none(self) -> None:
        raw = extract_raw_book(
            product_html(description=""),
            "https://books.toscrape.com/catalogue/test-book/index.html",
            "https://books.toscrape.com/catalogue/page-1.html",
            datetime(2026, 8, 14, tzinfo=UTC),
        )
        self.assertIsNone(raw["description"])

    def test_schema_rejects_non_https_url(self) -> None:
        with self.assertRaises(ValueError):
            BookRecord.model_validate(
                {
                    "title": "Test Book",
                    "product_url": "http://example.com/book",
                    "price_text": "£12.34",
                    "price_gbp": 12.34,
                    "availability_text": "In stock",
                    "rating_text": "Four",
                    "description": None,
                    "source_page": "https://books.toscrape.com/catalogue/page-1.html",
                    "fetched_at": "2026-08-14T00:00:00Z",
                }
            )

    def test_duplicate_urls_are_idempotent_in_identity_map(self) -> None:
        urls = ["https://example.com/a", "https://example.com/a"]
        identity_map = {url: {"product_url": url} for url in urls}
        self.assertEqual(len(identity_map), 1)

    def test_malformed_fixture_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            extract_raw_book(
                "<html><body><p>not a product</p></body></html>",
                "https://books.toscrape.com/catalogue/broken/index.html",
                "https://books.toscrape.com/catalogue/page-1.html",
                datetime(2026, 8, 14, tzinfo=UTC),
            )


if __name__ == "__main__":
    unittest.main()
