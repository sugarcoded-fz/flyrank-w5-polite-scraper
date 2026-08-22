import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from datetime import datetime, timezone
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
import re
import json
import time as time_module


REQUEST_DELAY = 0.5 

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/sugarcoded-fz/flyrank-w5-polite-scraper)"
TIMEOUT = 10
CACHE_DIR = "cache"

os.makedirs(CACHE_DIR, exist_ok=True)



class BookRecord(BaseModel):
    title: str
    product_url: str
    price_gbp: float
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str

    @field_validator("product_url")
    @classmethod
    def must_be_https(cls, v):
        if not v.startswith("https://"):
            raise ValueError("product_url must start with https://")
        return v

    @field_validator("price_gbp")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("price_gbp must be positive")
        return v




def clean_price(price_text: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", price_text)
    return float(cleaned)

def clean_record(raw_record: dict) -> dict:
    cleaned = dict(raw_record)
    cleaned["price_gbp"] = clean_price(raw_record["price_text"])
    return cleaned   


def validate_records(raw_records: list[dict]):
    valid = []
    invalid = []
    seen_urls = set()

    for raw in raw_records:
        cleaned = clean_record(raw)

        if cleaned["product_url"] in seen_urls:
            invalid.append({"record": raw, "reason": "duplicate product_url"})
            continue

        try:
            validated = BookRecord(**cleaned)
            valid.append(validated.model_dump())
            seen_urls.add(cleaned["product_url"])
        except Exception as e:
            invalid.append({"record": raw, "reason": str(e)})

    return valid, invalid


def save_output(valid_records, invalid_records):
    os.makedirs("output", exist_ok=True)

    with open("output/books.json", "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open("output/errors.json", "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, indent=2, ensure_ascii=False)

    print(f"valid={len(valid_records)}  invalid={len(invalid_records)}")



def fetch(url, cache_key):
    cache_path = os.path.join(CACHE_DIR, cache_key)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT  {url}  ({len(html)} bytes)")
        return html

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {url}")

    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"FETCH      {url}  ({len(html)} bytes)")
    return html




def parse_catalogue_page(html, page_url):
    soup = BeautifulSoup(html, "lxml")

    book_links = []
    for article in soup.find_all("article", class_="product_pod"):
        href = article.h3.a["href"]
        absolute_url = urljoin(page_url, href)
        book_links.append(absolute_url)

    next_link = soup.find("li", class_="next")
    next_url = None
    if next_link:
        next_href = next_link.a["href"]
        next_url = urljoin(page_url, next_href)

    return book_links, next_url   



def parse_book_page(html, url, source_page):
    soup = BeautifulSoup(html, "lxml")

    product_main = soup.find("div", class_="product_main")
    title = product_main.h1.text.strip()

    price_text = product_main.find("p", class_="price_color").text.strip()

    availability_text = product_main.find("p", class_="instock.availability")
    if availability_text is None:
        availability_text = product_main.find("p", class_="instock availability")
    availability_text = availability_text.text.strip()

    rating_tag = product_main.find("p", class_="star-rating")
    rating_classes = rating_tag["class"]
    rating_text = [c for c in rating_classes if c != "star-rating"][0]

    description_tag = soup.find("div", id="product_description")
    if description_tag:
        description = description_tag.find_next_sibling("p").text.strip()
    else:
        description = None

    return {
        "title": title,
        "product_url": url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }



def extract_all_books(book_url_pairs):
    records = []
    failed_pages = []

    for i, (url, source_page) in enumerate(book_url_pairs, start=1):
        cache_key = f"book-{i:03d}.html"
        html, error = fetch_with_retry(url, cache_key)

        if error:
            print(f"FAILED     {url}  ({error})")
            failed_pages.append({"url": url, "reason": error})
            continue

        try:
            record = parse_book_page(html, url, source_page)
            records.append(record)
        except Exception as e:
            print(f"PARSE FAIL {url}  ({e})")
            failed_pages.append({"url": url, "reason": f"parse error: {e}"})

    print(f"detail_pages={len(records)}  failed={len(failed_pages)}")
    return records, failed_pages



def discover_book_urls():
    all_books = []  # list of (url, source_page) tuples now, not just urls
    page_num = 1
    current_url = "https://books.toscrape.com/catalogue/page-1.html"
    MAX_PAGES = 3

    while current_url and page_num <= MAX_PAGES:
        cache_key = f"catalogue-page-{page_num}.html"
        was_cached = os.path.exists(os.path.join(CACHE_DIR, cache_key))
        html = fetch(current_url, cache_key)
        if not was_cached:
            time.sleep(REQUEST_DELAY)

        book_links, next_url = parse_catalogue_page(html, current_url)
        for link in book_links:
            all_books.append((link, current_url))

        current_url = next_url
        page_num += 1

    seen = set()
    unique_books = []
    for url, source in all_books:
        if url not in seen:
            seen.add(url)
            unique_books.append((url, source))

    print(f"catalogue_pages={min(page_num - 1, MAX_PAGES)}")
    print(f"discovered={len(all_books)}")
    print(f"unique_urls={len(unique_books)}")

    return unique_books  # now returns (url, source_page) pairs




def fetch_with_retry(url, cache_key):
    was_cached = os.path.exists(os.path.join(CACHE_DIR, cache_key))

    try:
        html = fetch(url, cache_key)
        if not was_cached:
            time.sleep(REQUEST_DELAY)
        return html, None
    except Exception as e:
        error_str = str(e)
        # Retry once on timeout or 5xx — never on 404 or 403
        if "timeout" in error_str.lower() or "50" in error_str[-3:]:
            time.sleep(1)
            try:
                html = fetch(url, cache_key)
                if not was_cached:
                    time.sleep(REQUEST_DELAY)
                return html, None
            except Exception as e2:
                return None, str(e2)
        return None, error_str


   

def run_scraper():
    start_time = time_module.time()
    start_iso = datetime.now(timezone.utc).isoformat()

    book_url_pairs = discover_book_urls()

    # Prove resilience: inject one fake URL on purpose
    # book_url_pairs.append(("https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html",
    #                         "https://books.toscrape.com/catalogue/page-1.html"))

    raw_records, failed_pages = extract_all_books(book_url_pairs)
    valid_records, invalid_records = validate_records(raw_records)
    save_output(valid_records, invalid_records)

    duration = time_module.time() - start_time

    report = {
        "start_time": start_iso,
        "duration_seconds": round(duration, 2),
        "catalogue_pages_fetched": 3,
        "detail_pages_attempted": len(book_url_pairs),
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "failed_pages": len(failed_pages),
        "failed_page_details": failed_pages
    }

    os.makedirs("output", exist_ok=True)
    with open("output/run-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n--- Run report ---")
    print(f"valid={len(valid_records)}  invalid={len(invalid_records)}  failed_pages={len(failed_pages)}  duration={duration:.1f}s")


if __name__ == "__main__":
    run_scraper()

   