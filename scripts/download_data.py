#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download Script for SIMA Daily Quotations (Paraná Agricultural Prices)
Downloads historical ZIP/RAR archives from the state agriculture department.
"""

import os
import sys
import time
import zipfile
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

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
    """Parse the links.txt file and extract archive download URLs."""
    archive_links = []

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

    return archive_links


def get_filename_from_url(url):
    """Extract filename from URL."""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    return filename


def download_file(url, output_dir, session=None):
    """Download a single file with retry logic."""
    filename = get_filename_from_url(url)
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


def extract_archive(archive_path, output_dir):
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
                        source = zf.open(member)
                        target_path = output_dir / member_filename
                        with open(target_path, 'wb') as target:
                            target.write(source.read())
                        source.close()

            print(f"  [OK] Extracted {filename}")
            return True

        elif archive_path.suffix.lower() == '.rar':
            if not HAS_RARFILE:
                print(f"  [WARN] Cannot extract {filename} - rarfile not installed")
                return False

            with rarfile.RarFile(archive_path, 'r') as rf:
                members = [m for m in rf.namelist() if not m.endswith('/')]
                print(f"  [EXT] Extracting {filename} ({len(members)} files)...")

                for member in members:
                    member_filename = os.path.basename(member)
                    if member_filename:
                        source = rf.open(member)
                        target_path = output_dir / member_filename
                        with open(target_path, 'wb') as target:
                            target.write(source.read())
                        source.close()

            print(f"  [OK] Extracted {filename}")
            return True

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

    # Parse links
    print("\n[1/3] Parsing links file...")
    archive_links = parse_links_file()
    print(f"      Found {len(archive_links)} archive files to download")

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


if __name__ == "__main__":
    download_all()
