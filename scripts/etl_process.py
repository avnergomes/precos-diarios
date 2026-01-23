#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL Pipeline for SIMA Daily Quotations (Paraná Agricultural Prices)
Processes Excel files from the extracted archives and consolidates into a clean dataset.
"""

import os
import re
import unicodedata
import warnings
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_EXTRACTED_DIR = BASE_DIR / "data" / "extracted"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
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
    'EUCALIPTO': 'Florestal', 'ERVA-MATE': 'Florestal',
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
    # Try sheet name first (format: DD-MM-YY or DD-MM-YYYY)
    patterns = [
        r'(\d{2})-(\d{2})-(\d{2,4})',  # DD-MM-YY or DD-MM-YYYY
        r'(\d{2})(\d{2})(\d{2,4})',     # DDMMYY
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

    # Try filename
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
        if result < 0 or result > 100000:  # Sanity check
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

    return 3  # Default


def find_product_column(df: pd.DataFrame, header_row: int) -> int:
    """Find the column containing product names."""
    headers = df.iloc[header_row]
    keywords = ['produto', 'descricao', 'item', 'mercadoria', 'especificacao']

    for idx, val in enumerate(headers):
        if pd.notna(val):
            val_lower = str(val).lower()
            if any(kw in val_lower for kw in keywords):
                return idx

    return 0  # Default to first column


def process_sheet(df: pd.DataFrame, date: datetime, filename: str) -> List[dict]:
    """Process a single sheet and extract records."""
    records = []

    if df.empty or len(df) < 5:
        return records

    # Find header row and product column
    header_row = find_header_row(df)
    product_col = find_product_column(df, header_row)

    # Get column headers
    headers = df.iloc[header_row].tolist()

    # Find price columns (look for patterns like regional names or "preco", "min", "max")
    price_cols = []
    for idx, h in enumerate(headers):
        if pd.notna(h):
            h_str = str(h).upper()
            # Skip product-related columns
            if any(kw in h_str for kw in ['PRODUTO', 'DESCRI', 'ITEM', 'UNID', 'ESPEC']):
                continue
            # This might be a regional or price column
            price_cols.append(idx)

    # Process data rows
    for row_idx in range(header_row + 1, len(df)):
        row = df.iloc[row_idx]

        # Get product name
        product = row.iloc[product_col] if product_col < len(row) else None
        if pd.isna(product) or not str(product).strip():
            continue

        product = str(product).strip()
        if len(product) < 2 or product.upper() in ['NAN', 'NONE', '-', '--']:
            continue

        # Skip header-like rows
        if any(kw in product.upper() for kw in ['PRODUTO', 'TOTAL', 'FONTE', 'OBS', 'NOTA']):
            continue

        # Extract prices from all price columns
        prices = []
        for col_idx in price_cols:
            if col_idx < len(row):
                price = parse_number(row.iloc[col_idx])
                if price and price > 0:
                    prices.append(price)

        if not prices:
            continue

        # Calculate stats
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
            # Parse date from sheet name
            date = parse_date_from_sheet(sheet_name, filepath.stem)

            if not date:
                # Try to extract year from filename
                year_match = re.search(r'(19|20)\d{2}', filepath.stem)
                if year_match:
                    year = int(year_match.group())
                    date = datetime(year, 1, 1)  # Default to Jan 1

            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                records = process_sheet(df, date, filepath.name)
                all_records.extend(records)
            except Exception as e:
                continue

    except Exception as e:
        pass

    return all_records


def process_all_files():
    """Process all Excel files in the extracted directory."""
    print("=" * 60)
    print("SIMA Daily Quotations - ETL Pipeline")
    print("=" * 60)

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    excel_patterns = ['*.xlsx', '*.xls', '*.xlsm']
    excel_files = []
    for pattern in excel_patterns:
        excel_files.extend(DATA_EXTRACTED_DIR.glob(pattern))

    excel_files = sorted(excel_files)
    print(f"\n[1/3] Found {len(excel_files)} Excel files to process")

    if not excel_files:
        print("      No Excel files found.")
        return

    print("\n[2/3] Processing files...")
    all_records = []
    success_count = 0

    for i, filepath in enumerate(excel_files, 1):
        if i % 50 == 0 or i == 1:
            print(f"  Processing file {i}/{len(excel_files)}...")

        records = process_excel_file(filepath)
        if records:
            all_records.extend(records)
            success_count += 1

    print(f"\n  Files with data: {success_count}")
    print(f"  Total records extracted: {len(all_records)}")

    if not all_records:
        print("\n[ERROR] No records extracted!")
        return

    print("\n[3/3] Consolidating data...")
    df = pd.DataFrame(all_records)

    # Remove duplicates
    df = df.drop_duplicates(subset=['data', 'produto', 'preco_medio'])
    print(f"  After dedup: {len(df)} records")

    # Sort
    df = df.sort_values(['ano', 'mes', 'dia', 'produto'], na_position='last')

    # Save
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"\n  Saved to: {OUTPUT_FILE}")

    # Summary
    print("\n" + "=" * 60)
    print("ETL SUMMARY")
    print("=" * 60)
    print(f"  Total records:      {len(df):,}")
    print(f"  Unique products:    {df['produto'].nunique()}")
    print(f"  Categories:         {df['categoria'].nunique()}")

    if df['ano'].notna().any():
        print(f"  Year range:         {int(df['ano'].min())} - {int(df['ano'].max())}")

    print("\n  Records by category:")
    for cat, count in df['categoria'].value_counts().items():
        print(f"    - {cat}: {count:,}")

    print("\n  Records by year:")
    for year, count in df.groupby('ano').size().sort_index().tail(10).items():
        print(f"    - {int(year)}: {count:,}")

    print("=" * 60)


if __name__ == "__main__":
    process_all_files()
