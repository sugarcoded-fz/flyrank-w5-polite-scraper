# The Polite Scraper

A scraping pipeline that collects the first 3 catalogue pages (60 books)
from books.toscrape.com, extracts raw fields, cleans and validates them
against a schema, and produces structured JSON — surviving individual
page failures without crashing, and reporting honest numbers at the end
of every run.

## Target classification

**Site:** books.toscrape.com
**Why:** Explicitly built and hosted as a public sandbox for practicing
web scraping (confirmed at toscrape.com).
**Scope:** The first 3 catalogue pages only (60 books total) — not the
entire site.
**Data collected:** Book title, price, availability, star rating,
description, and product URL — all publicly rendered on each page.
**robots.txt result:** No robots file found (404 at
books.toscrape.com/robots.txt). A missing file is not permission by
itself — permission here comes from the site's own stated purpose as a
practice sandbox, confirmed by hand before writing any request code.

I will not reuse this code on another site without checking its rules
and terms first.

## How to run it

\`\`\`bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 src/main.py
\`\`\`

Takes roughly 30–60 seconds on a cold run (60 real requests, half-second
delay between each). Subsequent runs read from cache and finish in
under a second.

## Record schema

| Field | Type | Notes |
|---|---|---|
| title | string | |
| product_url | string | Canonical identity — must start with https:// |
| price_gbp | float | Cleaned from price_text, must be positive |
| price_text | string | Original raw value, kept alongside the clean one |
| availability_text | string | Raw text, e.g. "In stock (22 available)" |
| rating_text | string | One of One/Two/Three/Four/Five |
| description | string or null | null when the page has no description |
| source_page | string | Which of the 3 catalogue pages this book was found on |
| fetched_at | string (ISO 8601) | UTC timestamp of when this record was fetched |

## Politeness rules

- **User-agent**: every real request identifies itself as
  `FlyRankInternshipA9/1.0` with a link back to this repo.
- **Timeout**: every request gives up after 10 seconds.
- **Delay**: at least 500ms between real (non-cached) requests.
- **Status check**: only a 200 response is treated as a valid page;
  anything else is a failed fetch, not HTML to parse.
- **Cache**: development and repeated runs read from `cache/` instead
  of re-requesting the site. A full run touches the live site once per
  unique page, ever.

## Idempotency

Running the scraper twice produces the same 60 records in
`output/books.json` — not 120. Each run recomputes the full valid set
from scratch and overwrites the output file, rather than appending.

## Resilience

One deliberately fake book URL was added to the crawl list to prove
the pipeline survives a broken page: it was logged with a reason in
the run report and skipped, while the other 60 real books were still
processed and stored correctly. See `output/run-report.json` below for
a real example.

## Sample run report

\`\`\`json
{
  "start_time": "2026-08-22T12:50:53.507744+00:00",
  "duration_seconds": 5.03,
  "catalogue_pages_fetched": 3,
  "detail_pages_attempted": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_page_details": []
}
\`\`\`

## Why this assignment needed no browser

Every field this scraper collects — title, price, availability, rating,
description — is already present in the raw HTML the server sends back
on a plain GET request. Nothing here is rendered client-side by
JavaScript after the page loads. A headless browser (Playwright,
Selenium, etc.) would only add startup cost, memory overhead, and
complexity for zero additional data — plain HTTP requests are the
correct, cheaper tool for this specific site.

## Ethics note

I only scraped a site explicitly built and offered for scraping
practice. In general: prefer an official API when one exists, never
bypass logins, paywalls, or explicit blocks, and collect only the data
actually needed for the task at hand — not everything reachable.

## Known limitations

- The rate limiter is a fixed delay, not adaptive — it doesn't back off
  further if the site were to respond slowly or with errors at scale.
- Retry logic covers one retry on timeout/5xx; it does not implement
  exponential backoff (that's next week's assignment, A16).