# Business Lead Scraper

Find local businesses on Google Maps and collect their **name, address, phone, website, social media links and email** in a simple web interface. Filter the results live and export them to CSV.

No coding needed to use it: you open a page in your browser, type what you are looking for, and click **Start**.

## Features

- Search by **category + areas** (e.g. "cafe" in Centrs, Teika, Imanta...) to go beyond Google's ~120 results per search
- Collects name, address, phone, website and Google Maps link
- Finds **Facebook, Instagram, TikTok, LinkedIn, YouTube and X/Twitter** links and a contact **email** from each business website
- Live progress bar and log, with a Stop button
- Many filters: name, excluded names, address, area, phone (any / none / mobile), website (none / own / social-only), chains vs unique, social platform, email
- **Export the filtered list to CSV**, or copy all phones, websites or emails
- Results are autosaved to `leads_latest.csv`
- Runs in the background (headless) or with a visible browser

## What you need

- **Windows, macOS or Linux**
- **Python 3.9 or newer**: https://www.python.org/downloads/
  (On Windows, tick **"Add Python to PATH"** during installation.)
- **Google Chrome** installed

## Installation (one time)

1. **Download the project.**
   On this page click the green **Code** button, then **Download ZIP**, and unzip it.
   (Or with git: `git clone https://github.com/AnmolGupta2282/Lead_Scraper.git`)

2. **Open a terminal in the project folder.**
   - Windows: open the folder, click the address bar, type `cmd` and press Enter.
   - macOS/Linux: open Terminal and `cd` into the folder.

3. **Install the required packages:**
   ```
   pip install -r requirements.txt
   ```
   If you see "pip is not recognized", use:
   ```
   python -m pip install -r requirements.txt
   ```

## Run the app

```
python app.py
```

Your browser opens at **http://127.0.0.1:5000**. If it does not, open that address yourself. Keep the terminal window open while you use the app. Press `Ctrl + C` in the terminal to close it.

Open the app again

The page is not a file you can open directly. It only works while the app is running in the terminal.

If the terminal is still open and running the app, go to this address in your browser:
**  http://127.0.0.1:5000
**If you closed the terminal, start the app again:
Open Command Prompt in the project folder (for example cd Desktop\scraper).
Run:
**  python app.py
The browser opens automatically. If it does not, type http://127.0.0.1:5000 into the address bar.

Restarting the app clears the results shown on the page. Your last run is still saved in leads_latest.csv in the project folder, and anything you exported stays safe.

Windows shortcut: create a file called start.bat in the project folder with these two lines, then double-click it any time to launch the app:
**
@echo off
python app.py**  

## How to use it

1. **Category**: what you want to find, e.g. `cafe`, `dentist`, `hair salon`.
2. **Areas**: one per line, e.g.
   ```
   Centrs Riga
   Agenskalns Riga
   Teika Riga
   ```
   Each line becomes a search like "cafe in Centrs Riga".
3. Choose the options:
   - **Max results**: `0` means no limit.
   - **Hide browser (headless)**: run Chrome in the background.
   - **Find social media & email**: slower, but adds social links and emails.
4. Click **Start scraping**. Results appear in the table as they are found.
5. Use the **filters** to narrow the list, then click **Export filtered CSV**.

### Getting 200-300+ results

Google Maps returns about 100-120 businesses for a single search, however long it scrolls. To get more, **add more areas** (neighborhoods, districts, streets). Results from all searches are merged and duplicates are removed.

### Filter ideas

| You want | Use |
|---|---|
| Businesses that need a website | Complete leads: *Has phone, NO website* |
| Businesses with an Instagram page | Social media: *Has Instagram* |
| Only independent shops | Chains: *Unique names only* |
| People you can text | Phone: *Mobile only* (Latvian numbers starting with 2) |
| Skip big brands | Name does NOT contain: `starbucks, narvesen, rimi` |

## Command line version (optional)

Prefer the terminal? Use the original script:

```
python business_scraper.py -q "cafe in Centrs Riga" "cafe in Teika Riga" -o leads.csv --headless
```

| Option | Meaning |
|---|---|
| `-q` | One or more search queries |
| `-o` | Output CSV file (default `data.csv`) |
| `-l` | Max total results (0 = no limit) |
| `--headless` | Hide the browser window |

## Files

| File | Purpose |
|---|---|
| `app.py` | The web interface (run this) |
| `business_scraper.py` | The Google Maps scraper |
| `social.py` | Finds social media links and emails on websites |
| `requirements.txt` | Packages to install |

## Troubleshooting

- **"python is not recognized"**: Python is not installed or was not added to PATH. Reinstall it and tick "Add Python to PATH".
- **"pip is not recognized"**: use `python -m pip install -r requirements.txt`.
- **Chrome error / driver error**: make sure Google Chrome is installed and up to date. The driver downloads automatically the first time, so you need an internet connection.
- **Very few or zero results**: try running with **Hide browser** switched off to see what Google shows (cookie page, CAPTCHA). Check that the query makes sense on Google Maps itself.
- **A field is empty (phone, address...)**: not every business lists every field. If a field is empty for *all* businesses, Google may have changed its page layout. Please open an issue.
- **Port already in use**: close other copies of the app, or change `5000` at the bottom of `app.py` to another number.
- **Fewer social links than expected**: social links are only found for businesses that have a website, and some sites load their links with JavaScript, which this tool cannot read.

## Responsible use

This tool collects publicly visible business information. Automated scraping of Google Maps may be against Google's Terms of Service, and heavy use can lead to CAPTCHAs or temporary blocks. You are responsible for how you use it. Follow local laws on data protection and marketing (such as GDPR and rules on unsolicited emails and calls), and for large or commercial use consider the official [Google Places API](https://developers.google.com/maps/documentation/places/web-service).

