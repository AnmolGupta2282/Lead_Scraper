"""
Business Lead Scraper
---------------------
Extracts business names, addresses, phone numbers, and website URLs from Google Maps.
"""

import argparse
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver(headless: bool = False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape business details including name, address, phone, and website.")
    parser.add_argument("-q", "--query", required=True, help="Search query (e.g., 'Coffee shops in Riga', 'Plumbers in Chicago')")
    parser.add_argument("-o", "--output", default="data.csv", help="Output CSV filename")
    parser.add_argument("-l", "--limit", type=int, default=10, help="Maximum number of businesses to scrape")
    parser.add_argument("--headless", action="store_true", help="Run browser in background without GUI")
    return parser.parse_args()


def scrape_businesses(query: str, limit: int, output_file: str, headless: bool):
    driver = setup_driver(headless)
    wait = WebDriverWait(driver, 15)
    
    print(f"Opening Google Maps search for query: '{query}'...")
    driver.get("https://www.google.com/maps")
    
    # Handle cookie consent dialog if it appears
    try:
        consent_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Accept') or contains(@aria-label, 'Piekrist')]")))
        consent_btn.click()
        time.sleep(1)
    except Exception:
        pass  # Cookie dialog not displayed

    # Submit search query
    search_box = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
    search_box.clear()
    search_box.send_keys(query)
    search_box.send_keys(Keys.ENTER)
    
    time.sleep(3)

    # Locate the scrollable feed container
    try:
        feed_panel = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))
    except Exception:
        print("Error: Could not locate results panel. Please verify your search query.")
        driver.quit()
        return

    scraped_data = []
    seen_names = set()

    print("Gathering listings...")
    
    while len(scraped_data) < limit:
        # Collect visible place listing links
        cards = driver.find_elements(By.XPATH, "//a[contains(@href, '/maps/place/')]")
        
        if not cards:
            break

        previous_count = len(scraped_data)

        for card in cards:
            if len(scraped_data) >= limit:
                break
                
            try:
                # Scroll card into view and click to open details
                driver.execute_script("arguments[0].scrollIntoView(true);", card)
                time.sleep(0.5)
                card.click()
                time.sleep(2)  # Wait for detail pane to refresh

                # 1. Extract Name
                name = ""
                try:
                    name_el = driver.find_element(By.XPATH, "//h1[contains(@class, 'DUwDvf')]")
                    name = name_el.text.strip()
                except Exception:
                    pass

                if not name or name in seen_names:
                    continue

                # 2. Extract Address
                address = ""
                try:
                    addr_btn = driver.find_element(By.XPATH, "//button[@data-item-id='address']")
                    address = addr_btn.text.strip().replace("\n", ", ")
                except Exception:
                    pass

                # 3. Extract Phone Number
                phone = ""
                try:
                    phone_btn = driver.find_element(By.XPATH, "//button[contains(@data-item-id, 'phone')]")
                    phone = phone_btn.text.strip()
                except Exception:
                    pass

                # 4. Extract Website URL
                website = ""
                try:
                    web_btn = driver.find_element(By.XPATH, "//a[@data-item-id='authority']")
                    website = web_btn.get_attribute("href")
                except Exception:
                    pass

                seen_names.add(name)
                scraped_data.append({
                    "name": name,
                    "address": address,
                    "phone": phone,
                    "website": website
                })

                print(f"[{len(scraped_data)}/{limit}] Scraped: {name}")

            except Exception:
                continue

        # Scroll feed panel down to trigger loading of additional entries
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed_panel)
        time.sleep(2)

        # Exit if no new listings were loaded during this iteration
        if len(scraped_data) == previous_count:
            print("No additional listings found.")
            break

    driver.quit()

    # Save extracted dataset to CSV
    if scraped_data:
        headers = ["name", "address", "phone", "website"]
        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(scraped_data)

        print(f"\nSuccessfully saved {len(scraped_data)} listings to '{output_file}'!")
    else:
        print("\nNo data was extracted.")


if __name__ == "__main__":
    args = parse_args()
    scrape_businesses(
        query=args.query,
        limit=args.limit,
        output_file=args.output,
        headless=args.headless
    )
