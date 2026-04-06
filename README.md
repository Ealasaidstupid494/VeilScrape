# VeilScrape

A Python desktop tool for scraping text, links, images, videos, audio, and files
from Tor .onion websites. Built with a clean GUI and routes all traffic through
the Tor network via SOCKS5 proxy.

Made by suadatbiniqbal for educational and research purposes only.

---

## What it does

- Scrapes text, hyperlinks, images, videos, audio, and downloadable files
- Detects and lists email addresses found on the page
- Saves all data into a named folder per site with a timestamp
- Routes all requests through Tor (socks5h://127.0.0.1:9050)
- Checks if Tor is running before every scrape
- Supports stopping a scrape mid-way
- Remembers your last used URL, folder, and settings
- Light and dark mode

---

## Requirements

- Python 3.10 or higher
- Tor installed and running on port 9050

---

## Installation

```bash
git clone https://github.com/suadatbiniqbal/VeilScrape.git
cd VeilScrape
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start Tor:

```bash
sudo service tor start
```

Run the app:

```bash
python main.py
```

---

## Output structure

Each scrape creates a folder named after the site with a timestamp:
