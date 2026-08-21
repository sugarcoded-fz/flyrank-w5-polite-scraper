import os
import requests

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


if __name__ == "__main__":
    fetch("https://books.toscrape.com/catalogue/page-1.html", "catalogue-page-1.html")