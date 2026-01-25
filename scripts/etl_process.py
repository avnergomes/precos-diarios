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

METRIC_LABELS = {
    'MIN', 'MINIMO', 'MÍNIMO',
    'M_C', 'MC', 'MEDIA', 'MÉDIA',
    'MAX', 'MÁX', 'MAXIMO', 'MÁXIMO',
}

MONTHS_PT = {
    'JAN': 1, 'JANEIRO': 1,
    'FEV': 2, 'FEVEREIRO': 2,
    'MAR': 3, 'MARCO': 3, 'MARÇO': 3,
    'ABR': 4, 'ABRIL': 4,
    'MAI': 5, 'MAIO': 5,
    'JUN': 6, 'JUNHO': 6,
    'JUL': 7, 'JULHO': 7,
    'AGO': 8, 'AGOSTO': 8,
    'SET': 9, 'SETEMBRO': 9,
    'OUT': 10, 'OUTUBRO': 10,
    'NOV': 11, 'NOVEMBRO': 11,
    'DEZ': 12, 'DEZEMBRO': 12,
}

UNIT_PATTERNS = [
    r'sc\\s*60\\s*kg', r'sc\\s*50\\s*kg', r'sc\\s*30\\s*kg',
    r'saca\\s*60\\s*kg', r'saca\\s*50\\s*kg',
    r'kg\\s*renda', r'kg', r'litro', r'l\\b', r'ml',
    r'arroba', r'@', r'tonelada', r't\\b',
    r'caixa', r'cx', r'unidade', r'unid\\.?', r'd\\.?z', r'duzia',
    r'cabeça', r'cabeca',
]


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
    # Prefer explicit YYYY-MM-DD or DD-MM-YYYY in filename (daily files).
    filename_patterns = [
        r'(\d{4})[-_](\d{2})[-_](\d{2})',  # YYYY-MM-DD
        r'(\d{2})[-_](\d{2})[-_](\d{4})',  # DD-MM-YYYY
    ]

    for pattern in filename_patterns:
        match = re.search(pattern, filename)
        if match:
            parts = [int(p) for p in match.groups()]
            if len(parts) == 3:
                if pattern.startswith(r'(\d{4})'):
                    year, month, day = parts
                else:
                    day, month, year = parts
                try:
                    return datetime(year, month, day)
                except ValueError:
                    continue

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

    # Try using sheet day + filename month/year
    day_match = re.fullmatch(r'\d{1,2}', sheet_name.strip())
    if day_match:
        day = int(day_match.group(0))
        month, year = extract_month_year(filename)
        if month and year:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

    # Try month/year only (fallback to first day)
    month, year = extract_month_year(sheet_name)
    if not month or not year:
        month, year = extract_month_year(filename)
    if month and year:
        try:
            return datetime(year, month, 1)
        except ValueError:
            return None

    return None


def extract_month_year(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Extract month/year from filename or sheet name."""
    if not text:
        return None, None

    text_norm = normalize_text(text)

    month = None
    for key, value in MONTHS_PT.items():
        if key in text_norm:
            month = value
            break

    year = None
    year_match = re.search(r'(19|20)\d{2}', text_norm)
    if year_match:
        year = int(year_match.group(0))

    if month and not year:
        year_two = re.search(r'(\d{2})$', text_norm)
        if year_two:
            year_val = int(year_two.group(1))
            year = 2000 + year_val if year_val < 50 else 1900 + year_val

    if not month or not year:
        numeric_match = re.search(r'(\d{2})[\-_ ]?(\d{2})(?!\d)', text_norm)
        if numeric_match:
            month_val = int(numeric_match.group(1))
            year_val = int(numeric_match.group(2))
            if 1 <= month_val <= 12:
                month = month or month_val
                year = year or (2000 + year_val if year_val < 50 else 1900 + year_val)

    return month, year


def normalize_unit(unit: str) -> str:
    """Normalize unit strings to consistent labels."""
    if not unit:
        return ''
    unit_norm = normalize_text(unit).lower()
    unit_norm = re.sub(r'\\s+', ' ', unit_norm).strip()

    replacements = {
        'sc60kg': 'sc 60 Kg',
        'sc 60 kg': 'sc 60 Kg',
        'saca 60 kg': 'sc 60 Kg',
        'sc 50 kg': 'sc 50 Kg',
        'saca 50 kg': 'sc 50 Kg',
        'kg renda': 'kg renda',
        'arroba': 'arroba',
        '@': 'arroba',
        'tonelada': 'tonelada',
        'kg': 'kg',
        'litro': 'litro',
        'l': 'litro',
        'ml': 'ml',
        'unidade': 'unid.',
        'unid.': 'unid.',
        'unid': 'unid.',
        'cx': 'caixa',
        'caixa': 'caixa',
        'cabeça': 'cabeça',
        'cabeca': 'cabeça',
        'dz': 'dúzia',
        'duzia': 'dúzia',
    }

    return replacements.get(unit_norm, unit.strip())


def split_product_unit(text: str) -> Tuple[str, Optional[str]]:
    """Split product name and unit from a combined string."""
    if not text:
        return '', None

    raw = re.sub(r'\\s+', ' ', str(text)).strip()
    unit_found = None

    for pattern in UNIT_PATTERNS:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            unit_found = match.group(0)
            raw = (raw[:match.start()] + raw[match.end():]).strip()
            break

    product = raw.strip()
    unit_norm = normalize_unit(unit_found) if unit_found else None

    if unit_norm == 'kg':
        lower = product.lower()
        if lower.endswith('sc 50') or lower.endswith('sc50'):
            product = product[:-5].strip()
            unit_norm = 'sc 50 Kg'
        elif lower.endswith('sc 60') or lower.endswith('sc60'):
            product = product[:-5].strip()
            unit_norm = 'sc 60 Kg'
        elif lower.endswith('renda'):
            product = product[:-5].strip()
            unit_norm = 'kg renda'

    return product.strip(), unit_norm


def detect_metric_label(value) -> Optional[str]:
    """Detect metric label in a cell."""
    if pd.isna(value):
        return None
    text = normalize_text(str(value))
    text = text.replace('.', '').replace('-', '').strip()
    if text in METRIC_LABELS:
        return text
    return None


def find_unit_column(headers: List) -> Optional[int]:
    """Find the column containing unit information."""
    for idx, val in enumerate(headers):
        if pd.notna(val):
            val_lower = str(val).lower()
            if 'unid' in val_lower or 'unidade' in val_lower:
                return idx
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
    unit_col = find_unit_column(headers)

    # Detect metric-based layout (MIN/M_C/MÁX)
    metric_hits = 0
    for row_idx in range(header_row + 1, min(header_row + 30, len(df))):
        metric = detect_metric_label(df.iloc[row_idx].iloc[product_col + 1] if product_col + 1 < len(df.columns) else None)
        if metric:
            metric_hits += 1
    is_metric_layout = metric_hits >= 3

    if is_metric_layout:
        current_parts = []
        current_unit = None
        current_min = None
        current_mean = None
        current_max = None
        current_prices = 0

        def flush_record():
            nonlocal current_parts, current_unit, current_min, current_mean, current_max, current_prices
            if not current_parts:
                return
            product_text = ' '.join(p for p in current_parts if p).strip()
            product_text = re.sub(r'\\s+', ' ', product_text).strip()
            product, unit = split_product_unit(product_text)
            unit = unit or current_unit

            if not product:
                return

            preco_medio = current_mean if current_mean is not None else current_min or current_max
            if preco_medio is None:
                return

            record = {
                'data': date.strftime('%Y-%m-%d') if date else None,
                'ano': date.year if date else None,
                'mes': date.month if date else None,
                'dia': date.day if date else None,
                'produto': product,
                'unidade': unit,
                'categoria': detect_category(product),
                'preco_medio': round(float(preco_medio), 2),
                'preco_minimo': round(float(current_min if current_min is not None else preco_medio), 2),
                'preco_maximo': round(float(current_max if current_max is not None else preco_medio), 2),
                'num_cotacoes': current_prices,
                'arquivo': filename,
            }
            records.append(record)

            current_parts = []
            current_unit = None
            current_min = None
            current_mean = None
            current_max = None
            current_prices = 0

        for row_idx in range(header_row + 1, len(df)):
            row = df.iloc[row_idx]
            metric_col_idx = product_col + 1
            metric_label = detect_metric_label(row.iloc[metric_col_idx] if metric_col_idx < len(row) else None)

            if not metric_label:
                continue

            product_cell = row.iloc[product_col] if product_col < len(row) else None
            if pd.notna(product_cell) and str(product_cell).strip():
                text = str(product_cell).strip()
                if current_parts and metric_label in ['MIN', 'MINIMO', 'MÍNIMO']:
                    flush_record()
                current_parts.append(text)

            if unit_col is not None and unit_col < len(row):
                unit_cell = row.iloc[unit_col]
                if pd.notna(unit_cell) and str(unit_cell).strip():
                    current_unit = normalize_unit(str(unit_cell))

            prices = []
            for col_idx in range(metric_col_idx + 1, len(row)):
                price = parse_number(row.iloc[col_idx])
                if price and price > 0:
                    prices.append(price)

            if prices:
                current_prices = max(current_prices, len(prices))
                avg_price = sum(prices) / len(prices)
                if metric_label in ['MIN', 'MINIMO', 'MÍNIMO']:
                    current_min = avg_price
                elif metric_label in ['M_C', 'MC', 'MEDIA', 'MÉDIA']:
                    current_mean = avg_price
                elif metric_label in ['MAX', 'MÁX', 'MAXIMO', 'MÁXIMO']:
                    current_max = avg_price

        flush_record()
    else:
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

            unit = None
            if unit_col is not None and unit_col < len(row):
                unit_cell = row.iloc[unit_col]
                if pd.notna(unit_cell) and str(unit_cell).strip():
                    unit = normalize_unit(str(unit_cell))

            product, unit_from_text = split_product_unit(product)
            unit = unit or unit_from_text

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
                'unidade': unit,
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
        excel_files.extend(DATA_EXTRACTED_DIR.rglob(pattern))

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
