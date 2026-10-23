"""
Business Lead Scraper - fixed version
-------------------------------------
Phase 1: scroll the Google Maps results feed and collect every place URL.
Phase 2: open each place URL directly and extract name, address, phone, website.

Google Maps returns roughly 100-120 results max per search, so to reach 200-300+
leads give several queries (different areas / categories). Results are de-duplicated.

Example:
  python business_scraper.py -q "cafe in Centrs Riga" "cafe in Agenskalns Riga" \
      "cafe in Teika Riga" "cafe in Purvciems Riga" -o cafes.csv
"""

import argparse
import csv
import re
import time
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

FIELDS = ["name", "address", "phone", "website", "maps_url"]


def setup_driver(headless: bool = False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-US")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def parse_args():
    p = argparse.ArgumentParser(description="Scrape business listings from Google Maps.")
    p.add_argument("-q", "--query", required=True, nargs="+",
                   help="One or more search queries, e.g. 'cafe in Centrs Riga' 'cafe in Teika Riga'")
    p.add_argument("-o", "--output", default="data.csv", help="Output CSV filename")
    p.add_argument("-l", "--limit", type=int, default=0, help="Max total results (0 = no limit)")
    p.add_argument("--headless", action="store_true", help="Run without a visible browser window")
    return p.parse_args()


def handle_cookie_consent(driver):
    xpaths = [
        "//button[.//span[contains(., 'Accept all') or contains(., 'Piekrist visiem')]]",
        "//button[contains(@aria-label, 'Accept all') or contains(@aria-label, 'Piekrist visiem')]",
        "//form//button[contains(., 'Accept all') or contains(., 'Piekrist visiem')]",
    ]
    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            time.sleep(1.5)
            return
        except Exception:
            continue


def place_key(url: str) -> str:
    """Stable id for de-duplication (the !1s... feature id, else the path)."""
    m = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", url)
    if m:
        return m.group(1)
    return url.split("?")[0]


def collect_place_urls(driver, query: str, max_urls: int):
    """Phase 1: scroll the results feed until it ends, return list of place URLs."""
    url = f"https://www.google.com/maps/search/{quote_plus(query)}?hl=en"
    driver.get(url)
    handle_cookie_consent(driver)
    time.sleep(3)

    # Query resolved straight to a single place (no feed)
    feeds = driver.find_elements(By.XPATH, "//div[@role='feed']")
    if not feeds:
        if "/maps/place/" in driver.current_url:
            return [driver.current_url]
        return []

    feed = feeds[0]
    found = {}
    stagnant = 0

    while len(found) < max_urls:
        links = driver.find_elements(By.XPATH, "//div[@role='feed']//a[contains(@href, '/maps/place/')]")
        before = len(found)
        for a in links:
            try:
                href = a.get_attribute("href")
            except Exception:
                continue
            if href:
                found.setdefault(place_key(href), href)

        print(f"   ...{len(found)} listings found so far")

        end = driver.find_elements(
            By.XPATH, "//*[contains(text(), \"You've reached the end of the list\")]")
        if end:
            print("   Reached end of results for this query.")
            break

        # Scroll the feed (re-find it each time to avoid stale references)
        try:
            feed = driver.find_element(By.XPATH, "//div[@role='feed']")
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed)
        except Exception:
            break
        time.sleep(2)

        if len(found) == before:
            stagnant += 1
            # nudge: scroll up a bit then down to trigger lazy loading
            try:
                driver.execute_script("arguments[0].scrollTop -= 600;", feed)
                time.sleep(0.5)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed)
            except Exception:
                pass
            time.sleep(1.5)
            if stagnant >= 6:
                print("   No new listings loading. Moving on.")
                break
        else:
            stagnant = 0

    return list(found.values())[:max_urls]


def text_of(driver, xpath, attr_prefix=None):
    try:
        el = driver.find_element(By.XPATH, xpath)
    except Exception:
        return ""
    label = el.get_attribute("aria-label") or ""
    if label and ":" in label:
        return label.split(":", 1)[1].strip()
    return (el.text or "").strip().replace("\n", ", ")


def extract_place(driver, url: str):
    """Phase 2: open a place page and read its details."""
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[normalize-space(.)!='']")))
    except Exception:
        return None
    time.sleep(1)

    name = ""
    for h in driver.find_elements(By.TAG_NAME, "h1"):
        t = (h.text or "").strip()
        if t and t.lower() not in ("results", "rezultāti"):
            name = t
            break
    if not name:
        return None

    address = text_of(driver, "//button[@data-item-id='address']")
    phone = text_of(driver, "//button[starts-with(@data-item-id, 'phone')]")

    website = ""
    try:
        website = driver.find_element(
            By.XPATH, "//a[@data-item-id='authority']").get_attribute("href") or ""
    except Exception:
        pass

    return {"name": name, "address": address, "phone": phone,
            "website": website, "maps_url": url}


def save_csv(rows, output_file):
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def scrape_businesses(queries, limit, output_file, headless):
    driver = setup_driver(headless)
    max_total = limit if limit > 0 else 10**6
    results = []
    seen_urls = set()
    seen_biz = set()

    try:
        for query in queries:
            if len(results) >= max_total:
                break
            print(f"\n=== Query: '{query}' ===")
            print("Phase 1: collecting listing URLs...")
            urls = collect_place_urls(driver, query, max_total * 2)
            urls = [u for u in urls if place_key(u) not in seen_urls]
            print(f"   {len(urls)} new listings to visit.")

            print("Phase 2: extracting details...")
            for u in urls:
                if len(results) >= max_total:
                    break
                seen_urls.add(place_key(u))
                try:
                    row = extract_place(driver, u)
                except Exception as e:
                    print(f"   skip (error: {type(e).__name__})")
                    continue
                if not row:
                    continue
                biz_key = (row["name"].lower(), row["address"].lower())
                if biz_key in seen_biz:
                    continue
                seen_biz.add(biz_key)
                results.append(row)
                print(f"[{len(results)}] {row['name']}")

                if len(results) % 25 == 0:
                    save_csv(results, output_file)  # periodic safety save
    except KeyboardInterrupt:
        print("\nInterrupted - saving what we have so far.")
    finally:
        driver.quit()

    if results:
        save_csv(results, output_file)
        print(f"\nSaved {len(results)} business records to '{output_file}'.")
    else:
        print("\nNo listings were extracted.")


if __name__ == "__main__":
    args = parse_args()
    scrape_businesses(args.query, args.limit, args.output, args.headless)
