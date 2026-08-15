# The polite scraper

This is the Python lane for FlyRank Week 5 assignment A9. It collects the first three catalogue pages from Books to Scrape, follows the 60 book links exposed by those pages, validates every record with Pydantic, and writes reusable JSON output.

## Target classification

- **Target:** [Books to Scrape](https://books.toscrape.com/), a fictional bookstore published by ToScrape as a safe web-scraping sandbox.
- **Why this target:** the site explicitly says it exists for beginners learning scraping and for developers testing scraping tools.
- **Scope:** only the first three catalogue pages and the 60 book-detail pages linked from them.
- **Collected fields:** title, canonical product URL, raw price, numeric GBP price, availability, rating, optional description, source catalogue page, and fetch timestamp.
- **robots.txt check:** `https://books.toscrape.com/robots.txt` returned HTTP 404 on 2026-08-14, so no robots file was found. A missing file is not treated as permission; the site's explicit sandbox description is why this limited exercise is appropriate.

I will not reuse this code on another site without checking its rules and terms first.

## Install and run

Python 3.10 or newer is required. From the repository root:

```bash
python3 -m venv scraper/.venv
source scraper/.venv/bin/activate
python -m pip install -r scraper/requirements.txt
python scraper/src/main.py
```

The last line is the one command that runs the scraper. It creates:

- `scraper/output/books.json` - 60 valid, unique records
- `scraper/output/errors.json` - rejected records or failed pages with reasons
- `scraper/output/run-report.json` - counts and timing for the latest run

The first run fills `scraper/cache/`. Later runs read the saved HTML and should finish in a few seconds without requesting those pages again.

Run the deliberate failure check with:

```bash
python scraper/src/main.py --include-broken-url
```

That option adds one made-up book URL after normal discovery. The server returns 404, the scraper does not retry it, and the 60 good records are still written.

## Pipeline

1. Start from catalogue page 1 and follow the site's own `next` links until three pages have been processed.
2. Resolve relative links with `urljoin` and remove duplicate product URLs.
3. Fetch uncached HTML with an identifying user-agent, a 10-second timeout, status checks, and at least 500 ms between real requests.
4. Retry a timeout or 5xx response once. Do not retry 403 or 404 responses.
5. Extract each book from `article.product_page`, keeping the raw text and provenance.
6. Normalize the price and validate the complete record with Pydantic.
7. Store valid records by canonical product URL, isolate errors, and write an honest run report.

The core assignment needs no browser because the required data is already present in the HTML returned by the server. Starting a browser would add time and memory without exposing additional data.

## Record schema

| Field | Type | Rule |
| --- | --- | --- |
| `title` | string | Required and non-empty |
| `product_url` | string | Required HTTPS canonical URL |
| `price_text` | string | Original value such as `£51.77` |
| `price_gbp` | number | Parsed non-negative GBP value |
| `availability_text` | string | Required raw availability text |
| `rating_text` | string | One of `One` through `Five` |
| `description` | string or null | Null when the page has no description |
| `source_page` | string | HTTPS catalogue page that exposed the book |
| `fetched_at` | ISO 8601 datetime | Time the cached HTML was originally fetched |

Pydantic rejects unknown fields and invalid values. Rejected records never enter `books.json`; they are written to `errors.json` with the reason instead.

## Real failure-test report

This report came from a cached rerun with one deliberate 404. All 63 real pages were cache hits, the bad page was skipped without retry, and all 60 valid records survived.

```json
{
  "started_at": "2026-08-15T02:09:36.091462Z",
  "duration_seconds": 0.383,
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "attempted_detail_pages": 61,
  "detail_pages": 60,
  "pages_fetched": 0,
  "cache_hits": 63,
  "network_requests": 1,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failed_page_details": [
    {
      "url": "https://books.toscrape.com/catalogue/definitely-not-a-real-book/index.html",
      "reason": "HTTP 404; not cached"
    }
  ]
}
```

The initial uncached run fetched 63 pages, discovered 60 unique books, validated all 60, and finished in 31.433 seconds with no failures.

## Tests

Run the offline parser and schema tests from the repository root:

```bash
python -m unittest discover -s scraper/tests -v
```

The seven tests cover price normalization, malformed prices, scoped extraction and whitespace cleanup, a missing description, HTTPS schema enforcement, duplicate identity URLs, and malformed HTML.

## Politeness and ethics

Every network request identifies this project, has a timeout, checks the status code, and is separated from the previous real request by at least 500 ms. Cached pages have no delay because they never contact the server. Only the data needed for this assignment is collected.

Use an official API when one exists. Never bypass authentication, paywalls, access controls, or blocks. A scraper should collect the minimum necessary data and stop when a site says no.

## Limitation

The extractor intentionally targets the current Books to Scrape product markup. If that sandbox changes its product selectors or field labels, affected records will be rejected and reported instead of being guessed.
