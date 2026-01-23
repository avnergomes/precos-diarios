#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Scraper for SIMA Daily Quotations
Fetches latest quotations from the Parana Agriculture website.
"""

import os
import re
import time
import logging
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
SCRAPED_DIR = DATA_DIR / "scraped"
LINKS_FILE = BASE_DIR / "links.txt"

BASE_URL = "https://www.agricultura.pr.gov.br"
COTACAO_URL = f"{BASE_URL}/Pagina/Cotacao-Diaria-SIMA-"

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}

# Category mappings
CATEGORIAS = {
    'SOJA': 'Graos', 'MILHO': 'Graos', 'TRIGO': 'Graos', 'FEIJAO': 'Graos',
    'ARROZ': 'Graos', 'CAFE': 'Graos',
    'BOI': 'Pecuaria', 'VACA': 'Pecuaria', 'SUINO': 'Pecuaria', 'FRANGO': 'Pecuaria',
    'MANDIOCA': 'Hortalicas',
    'ERVA-MATE': 'Florestal', 'ERVA MATE': 'Florestal',
}


def normalize_text(text: str) -> str:
    """Normalize text by removing accents."""
    if not isinstance(text, str):
        return ''
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return text.upper().strip()


def detect_category(product: str) -> str:
    """Detect product category."""
    product_norm = normalize_text(product)
    for key, category in CATEGORIAS.items():
        if key in product_norm:
            return category
    return 'Outros'


def get_latest_cotacao_id() -> int:
    """Find the latest quotation ID by checking the links file."""
    if LINKS_FILE.exists():
        with open(LINKS_FILE, 'r') as f:
            first_line = f.readline().strip()
            match = re.search(r'SIMA-(\d+)', first_line)
            if match:
                return int(match.group(1))
    return 2520  # Default starting point


def fetch_page(url: str, retries: int = 3) -> Optional[str]:
    """Fetch a webpage with retries."""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    return None


def parse_date_from_page(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract date from the quotation page."""
    # Try to find date in title or content
    title = soup.find('h1') or soup.find('title')
    if title:
        text = title.get_text()
        # Look for patterns like "22/01/2025" or "22-01-2025"
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

    # Try finding in page content
    content = soup.get_text()
    for pattern in [r'(\d{2})[/\-](\d{2})[/\-](\d{4})']:
        match = re.search(pattern, content)
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                continue

    return None


def parse_number(value: str) -> Optional[float]:
    """Parse a number from Brazilian format."""
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    value = re.sub(r'R\$\s*', '', value)
    value = re.sub(r'\s+', '', value)

    if not value or value in ['-', '--', '']:
        return None

    # Handle Brazilian number format (1.234,56)
    if ',' in value:
        if '.' in value and value.rindex('.') < value.rindex(','):
            value = value.replace('.', '')
            value = value.replace(',', '.')
        else:
            value = value.replace(',', '.')

    try:
        result = float(value)
        if result < 0 or result > 100000:
            return None
        return result
    except ValueError:
        return None


def parse_quotation_table(soup: BeautifulSoup, date: datetime) -> List[dict]:
    """Parse quotation data from HTML tables."""
    records = []

    # Find all tables
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue

        # Try to identify header row
        header_row = None
        for idx, row in enumerate(rows[:5]):
            cells = row.find_all(['th', 'td'])
            text = ' '.join(c.get_text().lower() for c in cells)
            if any(kw in text for kw in ['produto', 'descri', 'especifica']):
                header_row = idx
                break

        if header_row is None:
            header_row = 0

        # Get headers
        header_cells = rows[header_row].find_all(['th', 'td'])
        headers = [c.get_text().strip() for c in header_cells]

        # Find product column
        product_col = 0
        for idx, h in enumerate(headers):
            h_lower = h.lower()
            if any(kw in h_lower for kw in ['produto', 'descri', 'especifica', 'item']):
                product_col = idx
                break

        # Find price columns (columns that are not product/unit related)
        price_cols = []
        for idx, h in enumerate(headers):
            h_upper = h.upper()
            if idx == product_col:
                continue
            if any(kw in h_upper for kw in ['UNID', 'UN.', 'MEDIDA']):
                continue
            # Likely a regional or price column
            price_cols.append(idx)

        # Process data rows
        for row in rows[header_row + 1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= product_col:
                continue

            product = cells[product_col].get_text().strip()
            if not product or len(product) < 2:
                continue
            if any(kw in product.upper() for kw in ['PRODUTO', 'TOTAL', 'FONTE', 'OBS']):
                continue

            # Extract prices
            prices = []
            for col_idx in price_cols:
                if col_idx < len(cells):
                    price = parse_number(cells[col_idx].get_text())
                    if price and price > 0:
                        prices.append(price)

            if not prices:
                continue

            record = {
                'data': date.strftime('%Y-%m-%d') if date else None,
                'ano': date.year if date else None,
                'mes': date.month if date else None,
                'dia': date.day if date else None,
                'produto': product,
                'categoria': detect_category(product),
                'preco_medio': round(sum(prices) / len(prices), 2),
                'preco_minimo': round(min(prices), 2),
                'preco_maximo': round(max(prices), 2),
                'num_cotacoes': len(prices),
                'arquivo': 'web_scrape',
            }
            records.append(record)

    return records


def scrape_cotacao(cotacao_id: int) -> Tuple[Optional[datetime], List[dict]]:
    """Scrape a single quotation page."""
    url = f"{COTACAO_URL}{cotacao_id}"
    logger.info(f"Scraping {url}")

    html = fetch_page(url)
    if not html:
        return None, []

    soup = BeautifulSoup(html, 'html.parser')
    date = parse_date_from_page(soup)
    records = parse_quotation_table(soup, date)

    return date, records


def get_last_scraped_date() -> Optional[datetime]:
    """Get the date of the last scraped quotation."""
    scraped_csv = SCRAPED_DIR / "scraped_quotations.csv"
    if scraped_csv.exists():
        df = pd.read_csv(scraped_csv)
        if 'data' in df.columns and len(df) > 0:
            try:
                return pd.to_datetime(df['data']).max().to_pydatetime()
            except:
                pass
    return None


def scrape_latest_quotations(days_back: int = 7):
    """Scrape the latest quotations that haven't been scraped yet."""
    logger.info("Starting quotation scraping...")

    # Create directories
    SCRAPED_DIR.mkdir(parents=True, exist_ok=True)

    # Get the latest known ID
    latest_id = get_latest_cotacao_id()
    logger.info(f"Latest known quotation ID: {latest_id}")

    # Get last scraped date
    last_scraped = get_last_scraped_date()
    logger.info(f"Last scraped date: {last_scraped}")

    all_records = []
    new_links = []

    # Try scraping newer IDs first
    for offset in range(0, 20):
        cotacao_id = latest_id + offset
        date, records = scrape_cotacao(cotacao_id)

        if records:
            all_records.extend(records)
            new_links.append(f"{COTACAO_URL}{cotacao_id}")
            logger.info(f"  Found {len(records)} records for ID {cotacao_id} (date: {date})")
        elif offset > 5:
            # Stop if we've tried several IDs without finding data
            break

        time.sleep(1)  # Be polite to the server

    # Also scrape recent known IDs if we haven't scraped them recently
    if last_scraped is None or (datetime.now() - last_scraped).days > 1:
        for offset in range(1, min(days_back * 2, 30)):
            cotacao_id = latest_id - offset
            if cotacao_id < 1:
                break

            date, records = scrape_cotacao(cotacao_id)

            if records:
                # Check if this date is newer than our last scrape
                if last_scraped is None or (date and date > last_scraped):
                    all_records.extend(records)
                    logger.info(f"  Found {len(records)} records for ID {cotacao_id} (date: {date})")

            time.sleep(1)

    if all_records:
        logger.info(f"Total new records scraped: {len(all_records)}")

        # Load existing scraped data
        scraped_csv = SCRAPED_DIR / "scraped_quotations.csv"
        if scraped_csv.exists():
            existing_df = pd.read_csv(scraped_csv)
            new_df = pd.DataFrame(all_records)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            # Remove duplicates
            combined_df = combined_df.drop_duplicates(subset=['data', 'produto', 'preco_medio'])
        else:
            combined_df = pd.DataFrame(all_records)

        # Sort and save
        combined_df = combined_df.sort_values(['ano', 'mes', 'dia', 'produto'], na_position='last')
        combined_df.to_csv(scraped_csv, index=False, encoding='utf-8-sig')
        logger.info(f"Saved {len(combined_df)} total records to {scraped_csv}")

        # Update links file with any new links
        if new_links:
            update_links_file(new_links)

    return all_records


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
    scrape_latest_quotations()
