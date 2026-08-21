import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

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

def discover_book_urls():
    all_book_urls = []
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
        all_book_urls.extend(book_links)

        current_url = next_url
        page_num += 1

    unique_urls = list(dict.fromkeys(all_book_urls))

    print(f"catalogue_pages={min(page_num - 1, MAX_PAGES)}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls

if __name__ == "__main__":
    urls = discover_book_urls()