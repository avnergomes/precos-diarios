#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Scraper for SIMA Daily Quotations
Discovers SIMA pages and downloads Excel files for ETL processing.

The SIMA website publishes daily quotation pages, each containing a link to
download an Excel (.xlsx) file with price data. This scraper:
1. Scans page IDs forward from the last known ID
2. Downloads the Excel files to data/extracted/daily/
3. The ETL pipeline then processes those Excel files
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EXTRACTED_DAILY_DIR = DATA_DIR / "extracted" / "daily"
LINKS_FILE = BASE_DIR / "links.txt"

BASE_URL = "https://www.agricultura.pr.gov.br"
COTACAO_URL = f"{BASE_URL}/Pagina/Cotacao-Diaria-SIMA-"

# Scraper scan settings
MAX_FORWARD_SCAN = 500
MAX_CONSECUTIVE_FAILURES = 15
STATE_FILE = DATA_DIR / "scraper_state.json"

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}


def get_latest_cotacao_id() -> int:
    """Find the latest quotation ID by checking the links file."""
    if LINKS_FILE.exists():
        with open(LINKS_FILE, 'r') as f:
            for line in f:
                match = re.search(r'SIMA-(\d+)', line, re.IGNORECASE)
                if match:
                    return int(match.group(1))
    return 2520  # Default starting point


def load_scraper_state() -> dict:
    """Load persisted scraper state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"last_found_id": 2520}


def save_scraper_state(state: dict):
    """Persist scraper state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def fetch_page(url: str) -> Optional[str]:
    """Fetch a webpage (single attempt, no retry on 404)."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError:
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None


def parse_date_from_filename(filename: str) -> Optional[datetime]:
    """Extract date from Excel filename like '05-01-2026-impressao.xlsx'."""
    match = re.search(r'(\d{2})-(\d{2})-(\d{4})', filename)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass

    # Try DD-MM-YY format
    match = re.search(r'(\d{2})-(\d{2})-(\d{2})', filename)
    if match:
        day, month, year = match.groups()
        year = int(year)
        if year < 100:
            year = 2000 + year
        try:
            return datetime(year, int(month), int(day))
        except ValueError:
            pass

    return None


def parse_date_from_page(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract date from the quotation page content."""
    # Try to find date in title or content
    title = soup.find('h1') or soup.find('title')
    if title:
        text = title.get_text()
        patterns = [
            r'(\d{2})[/\-](\d{2})[/\-](\d{4})',
            r'(\d{2})[/\-](\d{2})[/\-](\d{2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                day, month, year = match.groups()
                year = int(year)
                if year < 100:
                    year = 2000 + year
                try:
                    return datetime(year, int(month), int(day))
                except ValueError:
                    continue

    # Try finding in page content (limited search)
    content = soup.get_text()[:2000]
    match = re.search(r'(\d{2})[/\-](\d{2})[/\-](\d{4})', content)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass

    return None


def extract_excel_links(soup: BeautifulSoup, page_url: str) -> List[str]:
    """Find Excel file download links in the page."""
    links = []
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        if not href:
            continue
        if any(ext in href.lower() for ext in ['.xls', '.xlsx', '.xlsm']):
            if href.startswith('http'):
                links.append(href)
            else:
                links.append(requests.compat.urljoin(page_url, href))
    return links


def download_excel(url: str, output_dir: Path, date_prefix: str) -> Optional[Path]:
    """Download an Excel file with a date prefix."""
    filename = os.path.basename(url.split('?')[0])
    target_name = f"{date_prefix}_{filename}"
    target_path = output_dir / target_name

    # Skip if already downloaded
    if target_path.exists():
        logger.info(f"  [SKIP] {target_name} already exists")
        return target_path

    try:
        response = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        response.raise_for_status()

        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        size_kb = target_path.stat().st_size / 1024
        logger.info(f"  [OK] Downloaded {target_name} ({size_kb:.1f} KB)")
        return target_path

    except Exception as e:
        logger.warning(f"  [ERR] Failed to download {url}: {e}")
        if target_path.exists():
            target_path.unlink()
        return None


def scrape_cotacao(cotacao_id: int) -> Tuple[Optional[datetime], int]:
    """Scrape a single quotation page and download its Excel file.

    Returns:
        Tuple of (date, number_of_files_downloaded)
    """
    url = f"{COTACAO_URL}{cotacao_id}"
    logger.info(f"Checking {url}")

    html = fetch_page(url)
    if not html:
        return None, 0

    soup = BeautifulSoup(html, 'html.parser')

    # Find Excel download links
    excel_links = extract_excel_links(soup, url)
    if not excel_links:
        # Page exists but no Excel links - try to get date anyway
        date = parse_date_from_page(soup)
        logger.info(f"  Page {cotacao_id} exists but no Excel links found (date: {date})")
        return date, 0

    # Try to get date from filename first, then from page
    date = None
    for link in excel_links:
        filename = os.path.basename(link.split('?')[0])
        date = parse_date_from_filename(filename)
        if date:
            break
    if not date:
        date = parse_date_from_page(soup)

    if not date:
        logger.warning(f"  Could not determine date for page {cotacao_id}")
        return None, 0

    # Download Excel files
    date_prefix = date.strftime('%Y-%m-%d')
    EXTRACTED_DAILY_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    for link in excel_links:
        path = download_excel(link, EXTRACTED_DAILY_DIR, date_prefix)
        if path:
            downloaded += 1

    return date, downloaded


def scrape_latest_quotations(days_back: int = 7, backfill: bool = False):
    """Discover new SIMA pages and download their Excel files.

    Args:
        days_back: Not used, kept for backward compatibility.
        backfill: If True, scan a much wider range (for historical recovery).
    """
    logger.info("Starting SIMA page discovery and Excel download...")

    # Determine start ID from links.txt and state file
    links_id = get_latest_cotacao_id()
    state = load_scraper_state()
    state_id = state.get("last_found_id", 2520)
    start_id = max(links_id, state_id)

    max_scan = MAX_FORWARD_SCAN if not backfill else 1500
    max_failures = MAX_CONSECUTIVE_FAILURES if not backfill else 30

    logger.info(f"Scanning from ID {start_id} (links={links_id}, state={state_id}), max_scan={max_scan}")

    new_links = []
    consecutive_failures = 0
    highest_found = start_id
    total_downloaded = 0

    for offset in range(0, max_scan):
        cotacao_id = start_id + offset
        date, files_downloaded = scrape_cotacao(cotacao_id)

        if files_downloaded > 0:
            new_links.append(f"{COTACAO_URL}{cotacao_id}")
            highest_found = max(highest_found, cotacao_id)
            consecutive_failures = 0
            total_downloaded += files_downloaded
            logger.info(f"  Found {files_downloaded} files for ID {cotacao_id} (date: {date})")
        elif date is not None:
            # Page exists but no files - still counts as "found"
            new_links.append(f"{COTACAO_URL}{cotacao_id}")
            highest_found = max(highest_found, cotacao_id)
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                logger.info(f"  Stopping after {max_failures} consecutive misses at ID {cotacao_id}")
                break

        time.sleep(1)  # Be polite to the server

    # Update state
    state["last_found_id"] = highest_found
    state["last_run"] = datetime.now().isoformat()
    save_scraper_state(state)

    # Update links file
    if new_links:
        update_links_file(new_links)

    logger.info(f"Done. Downloaded {total_downloaded} Excel files. Highest ID: {highest_found}")
    return total_downloaded


def update_links_file(new_links: List[str]):
    """Add new links to the links file."""
    existing_links = set()
    if LINKS_FILE.exists():
        with open(LINKS_FILE, 'r') as f:
            existing_links = set(line.strip() for line in f if line.strip())

    # Add new links at the top
    new_unique = [link for link in new_links if link not in existing_links]
    if new_unique:
        all_links = new_unique + list(existing_links)
        with open(LINKS_FILE, 'w') as f:
            for link in all_links:
                f.write(link + '\n')
        logger.info(f"Added {len(new_unique)} new links to {LINKS_FILE}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SIMA Daily Quotations Scraper")
    parser.add_argument("--backfill", action="store_true",
                        help="Run in backfill mode (scan wider range)")
    args = parser.parse_args()

    scrape_latest_quotations(backfill=args.backfill)
