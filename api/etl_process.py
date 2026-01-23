#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL Pipeline for SIMA Daily Quotations (Paraná Agricultural Prices)
Processes Excel files and scraped data into a consolidated dataset.
"""

import os
import re
import unicodedata
import warnings
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_EXTRACTED_DIR = DATA_DIR / "extracted"
DATA_SCRAPED_DIR = DATA_DIR / "scraped"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_FILE = DATA_PROCESSED_DIR / "consolidated.csv"

# Category mappings for products
CATEGORIAS = {
    'SOJA': 'Graos', 'MILHO': 'Graos', 'TRIGO': 'Graos', 'FEIJAO': 'Graos',
    'ARROZ': 'Graos', 'AVEIA': 'Graos', 'CEVADA': 'Graos', 'CENTEIO': 'Graos',
    'SORGO': 'Graos', 'TRITICALE': 'Graos', 'CANOLA': 'Graos', 'GIRASSOL': 'Graos',
    'AMENDOIM': 'Graos', 'CAFE': 'Graos',
    'LARANJA': 'Frutas', 'BANANA': 'Frutas', 'UVA': 'Frutas', 'MACA': 'Frutas',
    'MELANCIA': 'Frutas', 'MELAO': 'Frutas', 'MAMAO': 'Frutas', 'ABACAXI': 'Frutas',
    'MORANGO': 'Frutas', 'PESSEGO': 'Frutas', 'AMEIXA': 'Frutas', 'FIGO': 'Frutas',
    'CAQUI': 'Frutas', 'GOIABA': 'Frutas', 'MANGA': 'Frutas', 'MARACUJA': 'Frutas',
    'LIMAO': 'Frutas', 'TANGERINA': 'Frutas', 'PONCAN': 'Frutas', 'ABACATE': 'Frutas',
    'TOMATE': 'Hortalicas', 'BATATA': 'Hortalicas', 'CEBOLA': 'Hortalicas',
    'ALHO': 'Hortalicas', 'MANDIOCA': 'Hortalicas', 'CENOURA': 'Hortalicas',
    'BETERRABA': 'Hortalicas', 'REPOLHO': 'Hortalicas', 'ALFACE': 'Hortalicas',
    'COUVE': 'Hortalicas', 'PEPINO': 'Hortalicas', 'PIMENTAO': 'Hortalicas',
    'ABOBRINHA': 'Hortalicas', 'ABOBORA': 'Hortalicas', 'CHUCHU': 'Hortalicas',
    'QUIABO': 'Hortalicas', 'BERINJELA': 'Hortalicas', 'VAGEM': 'Hortalicas',
    'BROCOLIS': 'Hortalicas', 'COUVE-FLOR': 'Hortalicas', 'ESPINAFRE': 'Hortalicas',
    'RUCULA': 'Hortalicas', 'CHICORIA': 'Hortalicas', 'SALSA': 'Hortalicas',
    'CEBOLINHA': 'Hortalicas', 'RABANETE': 'Hortalicas', 'NABO': 'Hortalicas',
    'BOI': 'Pecuaria', 'VACA': 'Pecuaria', 'NOVILHO': 'Pecuaria', 'BEZERRO': 'Pecuaria',
    'SUINO': 'Pecuaria', 'PORCO': 'Pecuaria', 'FRANGO': 'Pecuaria', 'GALINHA': 'Pecuaria',
    'OVO': 'Pecuaria', 'OVINO': 'Pecuaria', 'CAPRINO': 'Pecuaria', 'LEITE': 'Pecuaria',
    'ADUBO': 'Insumos', 'FERTILIZANTE': 'Insumos', 'CALCARIO': 'Insumos',
    'UREIA': 'Insumos', 'SEMENTE': 'Insumos', 'DIESEL': 'Insumos',
    'MADEIRA': 'Florestal', 'LENHA': 'Florestal', 'PINUS': 'Florestal',
    'EUCALIPTO': 'Florestal', 'ERVA-MATE': 'Florestal', 'ERVA MATE': 'Florestal',
}


def normalize_text(text: str) -> str:
    """Normalize text by removing accents and converting to uppercase."""
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


def parse_date_from_sheet(sheet_name: str, filename: str) -> Optional[datetime]:
    """Parse date from sheet name or filename."""
    patterns = [
        r'(\d{2})-(\\d{2})-(\\d{2,4})',
        r'(\d{2})(\\d{2})(\\d{2,4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, sheet_name)
        if match:
            day, month, year = match.groups()
            year = int(year)
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            try:
                return datetime(year, int(month), int(day))
            except ValueError:
                continue

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            day, month, year = match.groups()
            year = int(year)
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            try:
                return datetime(year, int(month), int(day))
            except ValueError:
                continue

    return None


def parse_number(value) -> Optional[float]:
    """Parse a number from string, handling Brazilian format."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        if np.isnan(value) if isinstance(value, float) else False:
            return None
        return float(value)

    value = str(value).strip()
    value = re.sub(r'R\$\s*', '', value)
    value = re.sub(r'\s+', '', value)

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


def find_header_row(df: pd.DataFrame) -> int:
    """Find the row containing column headers."""
    keywords = ['produto', 'descricao', 'item', 'mercadoria', 'especificacao']

    for idx in range(min(15, len(df))):
        row = df.iloc[idx]
        row_text = ' '.join(str(v).lower() for v in row if pd.notna(v))
        if any(kw in row_text for kw in keywords):
            return idx

    return 3


def find_product_column(df: pd.DataFrame, header_row: int) -> int:
    """Find the column containing product names."""
    headers = df.iloc[header_row]
    keywords = ['produto', 'descricao', 'item', 'mercadoria', 'especificacao']

    for idx, val in enumerate(headers):
        if pd.notna(val):
            val_lower = str(val).lower()
            if any(kw in val_lower for kw in keywords):
                return idx

    return 0


def process_sheet(df: pd.DataFrame, date: datetime, filename: str) -> List[dict]:
    """Process a single sheet and extract records."""
    records = []

    if df.empty or len(df) < 5:
        return records

    header_row = find_header_row(df)
    product_col = find_product_column(df, header_row)
    headers = df.iloc[header_row].tolist()

    price_cols = []
    for idx, h in enumerate(headers):
        if pd.notna(h):
            h_str = str(h).upper()
            if any(kw in h_str for kw in ['PRODUTO', 'DESCRI', 'ITEM', 'UNID', 'ESPEC']):
                continue
            price_cols.append(idx)

    for row_idx in range(header_row + 1, len(df)):
        row = df.iloc[row_idx]

        product = row.iloc[product_col] if product_col < len(row) else None
        if pd.isna(product) or not str(product).strip():
            continue

        product = str(product).strip()
        if len(product) < 2 or product.upper() in ['NAN', 'NONE', '-', '--']:
            continue

        if any(kw in product.upper() for kw in ['PRODUTO', 'TOTAL', 'FONTE', 'OBS', 'NOTA']):
            continue

        prices = []
        for col_idx in price_cols:
            if col_idx < len(row):
                price = parse_number(row.iloc[col_idx])
                if price and price > 0:
                    prices.append(price)

        if not prices:
            continue

        preco_medio = sum(prices) / len(prices)
        preco_minimo = min(prices)
        preco_maximo = max(prices)

        record = {
            'data': date.strftime('%Y-%m-%d') if date else None,
            'ano': date.year if date else None,
            'mes': date.month if date else None,
            'dia': date.day if date else None,
            'produto': product,
            'categoria': detect_category(product),
            'preco_medio': round(preco_medio, 2),
            'preco_minimo': round(preco_minimo, 2),
            'preco_maximo': round(preco_maximo, 2),
            'num_cotacoes': len(prices),
            'arquivo': filename,
        }
        records.append(record)

    return records


def process_excel_file(filepath: Path) -> List[dict]:
    """Process a single Excel file with multiple sheets."""
    all_records = []

    try:
        xl = pd.ExcelFile(filepath, engine='xlrd' if filepath.suffix == '.xls' else 'openpyxl')

        for sheet_name in xl.sheet_names:
            date = parse_date_from_sheet(sheet_name, filepath.stem)

            if not date:
                year_match = re.search(r'(19|20)\d{2}', filepath.stem)
                if year_match:
                    year = int(year_match.group())
                    date = datetime(year, 1, 1)

            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                records = process_sheet(df, date, filepath.name)
                all_records.extend(records)
            except Exception as e:
                continue

    except Exception as e:
        pass

    return all_records


def load_scraped_data() -> pd.DataFrame:
    """Load data from web scraping."""
    scraped_csv = DATA_SCRAPED_DIR / "scraped_quotations.csv"
    if scraped_csv.exists():
        logger.info(f"Loading scraped data from {scraped_csv}")
        return pd.read_csv(scraped_csv, encoding='utf-8-sig')
    return pd.DataFrame()


def process_all_files():
    """Process all Excel files and scraped data."""
    logger.info("=" * 60)
    logger.info("SIMA Daily Quotations - ETL Pipeline")
    logger.info("=" * 60)

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Process Excel files
    excel_patterns = ['*.xlsx', '*.xls', '*.xlsm']
    excel_files = []
    if DATA_EXTRACTED_DIR.exists():
        for pattern in excel_patterns:
            excel_files.extend(DATA_EXTRACTED_DIR.glob(pattern))

    excel_files = sorted(excel_files)
    logger.info(f"Found {len(excel_files)} Excel files to process")

    all_records = []
    success_count = 0

    for i, filepath in enumerate(excel_files, 1):
        if i % 50 == 0 or i == 1:
            logger.info(f"  Processing file {i}/{len(excel_files)}...")

        records = process_excel_file(filepath)
        if records:
            all_records.extend(records)
            success_count += 1

    logger.info(f"Files with data: {success_count}")
    logger.info(f"Records from Excel: {len(all_records)}")

    # Load scraped data
    scraped_df = load_scraped_data()
    if not scraped_df.empty:
        logger.info(f"Records from scraping: {len(scraped_df)}")
        scraped_records = scraped_df.to_dict('records')
        all_records.extend(scraped_records)

    if not all_records:
        logger.error("No records extracted!")
        return

    logger.info("Consolidating data...")
    df = pd.DataFrame(all_records)

    # Remove duplicates
    df = df.drop_duplicates(subset=['data', 'produto', 'preco_medio'])
    logger.info(f"After dedup: {len(df)} records")

    # Sort
    df = df.sort_values(['ano', 'mes', 'dia', 'produto'], na_position='last')

    # Save
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    logger.info(f"Saved to: {OUTPUT_FILE}")

    # Summary
    logger.info("=" * 60)
    logger.info("ETL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total records:      {len(df):,}")
    logger.info(f"  Unique products:    {df['produto'].nunique()}")
    logger.info(f"  Categories:         {df['categoria'].nunique()}")

    if df['ano'].notna().any():
        logger.info(f"  Year range:         {int(df['ano'].min())} - {int(df['ano'].max())}")

    logger.info("=" * 60)


if __name__ == "__main__":
    process_all_files()
