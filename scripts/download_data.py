#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download Script for SIMA Daily Quotations (Paraná Agricultural Prices)
Downloads historical ZIP/RAR archives from the state agriculture department.
"""

import os
import re
import sys
import time
import zipfile
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import shutil
import subprocess

# Try importing rarfile (optional - for RAR archives)
try:
    import rarfile
    HAS_RARFILE = True
except ImportError:
    HAS_RARFILE = False
    print("Warning: rarfile not installed. RAR archives won't be extracted automatically.")
    print("Install with: pip install rarfile")

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_EXTRACTED_DIR = BASE_DIR / "data" / "extracted"
LINKS_FILE = BASE_DIR / "links.txt"
DAILY_RAW_DIR = DATA_RAW_DIR / "daily"
DAILY_EXTRACTED_DIR = DATA_EXTRACTED_DIR / "daily"

# Download settings
MAX_WORKERS = 4
REQUEST_TIMEOUT = 120
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_REQUESTS = 1

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def parse_links_file():
    """Parse the links.txt file and extract archive and daily page URLs."""
    archive_links = []
    page_links = []

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Check for archive files (ZIP or RAR)
            if '.zip' in line.lower() or '.rar' in line.lower():
                # Extract just the URL (remove any leading numbers or special chars)
                if 'http' in line:
                    url_start = line.find('http')
                    url = line[url_start:].strip()
                    # Clean up any invisible characters
                    url = ''.join(c for c in url if c.isprintable())
                    if url:
                        archive_links.append(url)
                continue

            if 'http' in line:
                url_start = line.find('http')
                url = line[url_start:].strip()
                url = ''.join(c for c in url if c.isprintable())
                if 'Cotacao-Diaria-SIMA' in url or 'COTACAO-DIARIA' in url.upper():
                    page_links.append(url)

    return archive_links, page_links


def get_filename_from_url(url):
    """Extract filename from URL."""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    return filename


def download_file(url, output_dir, session=None, filename_override=None):
    """Download a single file with retry logic."""
    filename = filename_override or get_filename_from_url(url)
    output_path = output_dir / filename

    # Skip if already downloaded
    if output_path.exists():
        print(f"  [SKIP] {filename} already exists")
        return output_path, True

    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    for attempt in range(RETRY_ATTEMPTS):
        try:
            print(f"  [DOWN] Downloading {filename}...")
            response = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()

            # Write to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = output_path.stat().st_size / (1024 * 1024)
            print(f"  [OK] {filename} ({file_size:.2f} MB)")
            return output_path, True

        except requests.exceptions.RequestException as e:
            print(f"  [ERR] Attempt {attempt + 1}/{RETRY_ATTEMPTS} failed for {filename}: {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

    return None, False


def fetch_page(url, session=None):
    """Fetch a page with retry logic."""
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"  [ERR] Attempt {attempt + 1}/{RETRY_ATTEMPTS} failed for page {url}: {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(2 ** attempt)

    return None


def find_seven_zip():
    """Find 7-Zip executable."""
    candidates = [
        shutil.which("7z"),
        "C:\\\\Program Files\\\\7-Zip\\\\7z.exe",
        "C:\\\\Program Files (x86)\\\\7-Zip\\\\7z.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate

    return None


def extract_archive(archive_path, output_dir, filename_prefix=None):
    """Extract ZIP or RAR archive."""
    filename = archive_path.name

    try:
        if archive_path.suffix.lower() == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                # Get list of files, avoiding directory entries
                members = [m for m in zf.namelist() if not m.endswith('/')]
                print(f"  [EXT] Extracting {filename} ({len(members)} files)...")

                for member in members:
                    # Extract to flat structure
                    member_filename = os.path.basename(member)
                    if member_filename:
                        if filename_prefix:
                            member_filename = f"{filename_prefix}_{member_filename}"
                        source = zf.open(member)
                        target_path = output_dir / member_filename
                        with open(target_path, 'wb') as target:
                            target.write(source.read())
                        source.close()

            print(f"  [OK] Extracted {filename}")
            return True

        elif archive_path.suffix.lower() == '.rar':
            if HAS_RARFILE:
                try:
                    with rarfile.RarFile(archive_path, 'r') as rf:
                        members = [m for m in rf.namelist() if not m.endswith('/')]
                        print(f"  [EXT] Extracting {filename} ({len(members)} files)...")

                        for member in members:
                            member_filename = os.path.basename(member)
                            if member_filename:
                                if filename_prefix:
                                    member_filename = f"{filename_prefix}_{member_filename}"
                                source = rf.open(member)
                                target_path = output_dir / member_filename
                                with open(target_path, 'wb') as target:
                                    target.write(source.read())
                                source.close()

                    print(f"  [OK] Extracted {filename}")
                    return True
                except Exception as e:
                    print(f"  [WARN] rarfile failed for {filename}: {e}")

            seven_zip = find_seven_zip()
            if seven_zip:
                print(f"  [EXT] Extracting {filename} with 7-Zip...")
                output_dir.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    [seven_zip, 'x', '-aoa', f'-o{output_dir}', str(archive_path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"  [OK] Extracted {filename}")
                return True

            print(f"  [WARN] Cannot extract {filename} - no RAR tool available")
            return False

    except Exception as e:
        print(f"  [ERR] Failed to extract {filename}: {e}")
        return False

    return False


def download_all():
    """Download all archive files."""
    print("=" * 60)
    print("SIMA Daily Quotations - Data Downloader")
    print("=" * 60)

    # Create directories
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    # Parse links
    print("\n[1/3] Parsing links file...")
    archive_links, page_links = parse_links_file()
    print(f"      Found {len(archive_links)} archive files to download")
    print(f"      Found {len(page_links)} daily page links")

    if not archive_links:
        print("      No archive links found. Check links.txt")
        return

    # Download files
    print("\n[2/3] Downloading archives...")
    session = requests.Session()
    session.headers.update(HEADERS)

    downloaded_files = []
    failed_files = []

    for i, url in enumerate(archive_links, 1):
        print(f"\n  [{i}/{len(archive_links)}]")
        path, success = download_file(url, DATA_RAW_DIR, session)

        if success and path:
            downloaded_files.append(path)
        else:
            failed_files.append(url)

        if i < len(archive_links):
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Extract archives
    print("\n[3/3] Extracting archives...")
    extracted_count = 0

    for archive_path in sorted(DATA_RAW_DIR.glob("*")):
        if archive_path.suffix.lower() in ['.zip', '.rar']:
            if extract_archive(archive_path, DATA_EXTRACTED_DIR):
                extracted_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"  Archives downloaded: {len(downloaded_files)}")
    print(f"  Archives extracted:  {extracted_count}")
    print(f"  Failed downloads:    {len(failed_files)}")

    if failed_files:
        print("\n  Failed URLs:")
        for url in failed_files:
            print(f"    - {url}")

    print(f"\n  Raw files:       {DATA_RAW_DIR}")
    print(f"  Extracted files: {DATA_EXTRACTED_DIR}")
    print("=" * 60)

    if page_links:
        print("\n[4/4] Downloading daily files (2025+)...")
        download_daily_files(page_links, min_year=2025)


def parse_date_from_page(html: str) -> Optional[datetime]:
    """Extract date from daily quotation page."""
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.find('h1') or soup.find('title')
    if title:
        text = title.get_text()
        match = re.search(r'(\d{2})[/\-](\d{2})[/\-](\d{4})', text)
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass

    content = soup.get_text()
    match = re.search(r'(\d{2})[/\-](\d{2})[/\-](\d{4})', content)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def extract_file_links(html: str, page_url: str) -> List[str]:
    """Find downloadable file links in the daily page."""
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        if not href:
            continue
        if any(ext in href.lower() for ext in ['.xls', '.xlsx', '.zip', '.rar']):
            if href.startswith('http'):
                links.append(href)
            else:
                links.append(requests.compat.urljoin(page_url, href))
    return links


def download_daily_files(page_links: List[str], min_year: int = 2025):
    """Download daily files for the given year range."""
    session = requests.Session()
    session.headers.update(HEADERS)

    downloaded = 0
    for index, page_url in enumerate(page_links, 1):
        print(f"  [PAGE {index}/{len(page_links)}] {page_url}")
        html = fetch_page(page_url, session)
        if not html:
            continue

        page_date = parse_date_from_page(html)
        if not page_date or page_date.year < min_year:
            continue

        file_links = extract_file_links(html, page_url)
        if not file_links:
            continue

        for file_url in file_links:
            filename = get_filename_from_url(file_url)
            prefix = page_date.strftime('%Y-%m-%d')
            target_name = f"{prefix}_{filename}"

            path, success = download_file(file_url, DAILY_RAW_DIR, session, filename_override=target_name)
            if not success or not path:
                continue

            downloaded += 1
            if path.suffix.lower() in ['.xls', '.xlsx', '.xlsm']:
                target = DAILY_EXTRACTED_DIR / target_name
                if not target.exists():
                    target.write_bytes(path.read_bytes())
            elif path.suffix.lower() in ['.zip', '.rar']:
                extract_archive(path, DAILY_EXTRACTED_DIR, filename_prefix=prefix)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"  Downloaded {downloaded} daily files for {min_year}+")


if __name__ == "__main__":
    download_all()
