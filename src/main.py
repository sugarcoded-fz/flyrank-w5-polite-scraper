import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from datetime import datetime, timezone


REQUEST_DELAY = 0.5 

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/sugarcoded-fz/flyrank-w5-polite-scraper)"
TIMEOUT = 10
CACHE_DIR = "cache"

os.makedirs(CACHE_DIR, exist_ok=True)

def fetch(url, cache_key):
    cache_path = os.path.join(CACHE_DIR, cache_key)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT  {url}  ({len(html)} bytes)")
        return html

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)

    if response.status_code != 200:
        raise Exception(f"Fetch failed: {url} returned {response.status_code}")

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
    for i, (url, source_page) in enumerate(book_url_pairs, start=1):
        cache_key = f"book-{i:03d}.html"
        was_cached = os.path.exists(os.path.join(CACHE_DIR, cache_key))

        html = fetch(url, cache_key)
        if not was_cached:
            time.sleep(REQUEST_DELAY)

        record = parse_book_page(html, url, source_page)
        records.append(record)

    print(f"detail_pages={len(records)}")
    return records



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



if __name__ == "__main__":
    book_urls = discover_book_urls()
    records = extract_all_books(book_urls)
    print(records[0])