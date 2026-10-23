# Google Maps Business Lead 

A lightweight, two-stage Python tool designed to find local business leads. It searches Google Maps for targeted businesses, extracts contact details (Name, Address, Phone Number, Website), and automatically crawls discovered websites to harvest email addresses.

---

## Features
- **Custom Business Scraping**: Scrape Google Maps by category, business type, or city.
- **Complete Details Extraction**: Captures Business Name, Address, Phone Number, and Official Website URL.
- **Smart Parsing**: Extracts standard `mailto:` links and obfuscated email formats (`name [at] domain [dot] com`).
- **Data Enrichment**: Preserves original business data while appending discovered email addresses cleanly to CSV files.

---

## Repository Structure

- `business_scraper.py`: Extracts business listings (Name, Address, Phone, Website) from Google Maps using Selenium.
- `requirements.txt`: Project dependencies.
- `.gitignore`: Files ignored by Git (caches, virtual environments, CSV outputs).

---

## Quick Start Guide

### 1. Prerequisites
Ensure you have **Python 3.8+** and Google Chrome installed.

### 2. Installation
Clone this repository and install dependencies:
```bash
git clone [https://github.com/AnmolGupta2282/Lead_Scraper.git](https://github.com/AnmolGupta2282/Lead_Scraper.git)
cd Lead_Scraper

pip install -r requirements.txt

**How to Use**

Bash 
python business_scraper.py -q "cafe in Centrs Riga" -o riga_cafes.csv --headless

