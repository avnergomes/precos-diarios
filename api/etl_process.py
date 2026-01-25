#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL Pipeline for SIMA Daily Quotations (Parana Agricultural Prices)
Processes Excel files and scraped data into a consolidated dataset.

Handles two file formats:
1. Newer (2018+): "Product name    unit" in column 0, MIN/M_C/MAX in column 1
2. Older (2003-2017): Product spans 3 rows vertically:
   - Row 1: Product name + MIN
   - Row 2: Type/variety + M_C
   - Row 3: Unit + MAX
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
    'AMENDOIM': 'Graos', 'CAFE': 'Graos', 'ALGODAO': 'Graos',
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
    'BOI': 'Pecuaria', 'VACA': 'Pecuaria', 'NOVILHO': 'Pecuaria', 'BEZERRO': 'Pecuaria',
    'SUINO': 'Pecuaria', 'PORCO': 'Pecuaria', 'FRANGO': 'Pecuaria', 'GALINHA': 'Pecuaria',
    'OVO': 'Pecuaria', 'OVINO': 'Pecuaria', 'CAPRINO': 'Pecuaria', 'LEITE': 'Pecuaria',
    'MADEIRA': 'Florestal', 'LENHA': 'Florestal', 'PINUS': 'Florestal',
    'EUCALIPTO': 'Florestal', 'ERVA-MATE': 'Florestal', 'ERVA MATE': 'Florestal',
}

# Known units (to exclude from product names)
UNITS = {
    'sc 60 kg', 'sc 50 kg', 'sc60kg', 'sc50kg', 'sc 60kg', 'sc 50kg',
    'arroba', 'kg', 'kg renda', 'kg embranco', 'kgrenda',
    'tonelada', 'ton', 't',
    'unidade', 'un', 'un.', 'duzia', 'dúzia', 'caixa', 'cx', 'litro', 'l',
    'cabeca', 'cabeça', 'cab', 'cab.',
}

# Type/variety descriptors (old format - row 2)
TYPES_VARIETIES = {
    'tipo 1', 'tipo 2', 'tipo 3', 'tipo 4', 'tipo 5', 'tipo 6',
    'tipo1', 'tipo2', 'tipo3', 'tipo4', 'tipo5', 'tipo6',
    'sequeiro', 'irrigado',
    'em coco', 'emcoco', 'em caroço', 'emcaroço',
    'em casca', 'emcasca', 'beneficiado',
    'em pé', 'empé', 'em pe', 'empe',
    'tipo carne', 'tipocarne', 'padrão corte', 'padrao corte',
    'bebida dura', 'bebidadura',
    'folha em barranco', 'folhaembarranco',
    'gr.longo', 'gr.longo fino', 'grlongo', 'grlongofino',
    'de cor', 'decor', 'preto', 'carioca',
    'não integrado', 'naointegrado',
}

# Invalid entries (metadata, headers, etc.)
INVALID_ENTRIES = {
    'min', 'max', 'máx', 'm_c', 'media', 'média',
    'nan', 'none', '-', '--', '\\\\\\', 'sinf', 'aus',
    'produto', 'produtos', 'total', 'fonte', 'obs', 'nota',
    '(vivo)', 'vivo', 'sc 60', 'sc 50',
}

# Canonical unit mapping for each product (from SIMA/DERAL documentation)
PRODUCT_UNITS = {
    # Grãos - sc 60 Kg (saca de 60 quilos)
    'Soja industrial tipo 1': 'sc 60 Kg',
    'Milho amarelo tipo 1': 'sc 60 Kg',
    'Milho comum': 'sc 60 Kg',
    'Milho': 'sc 60 Kg',
    'Trigo pão': 'sc 60 Kg',
    'Trigo': 'sc 60 Kg',
    'Feijão preto tipo 1': 'sc 60 Kg',
    'Feijão carioca tipo 1': 'sc 60 Kg',
    'Feijão de cor tipo 1': 'sc 60 Kg',
    'Arroz em casca tipo 1': 'sc 60 Kg',
    'Arroz irrigado': 'sc 60 Kg',
    'Arroz sequeiro': 'sc 60 Kg',
    'Café beneficiado bebida dura tipo 6': 'sc 60 Kg',
    'Algodão em caroço': 'arroba',
    # Café em coco - kg renda (rendimento)
    'Café em coco': 'kg renda',
    # Pecuária - arroba ou kg
    'Boi em pé': 'arroba',
    'Boi gordo': 'arroba',
    'Vaca em pé': 'arroba',
    'Vaca gorda': 'arroba',
    'Suíno em pé tipo carne': 'kg',
    'Suíno em pé tipo carne não integrado': 'kg',
    'Frango de corte': 'kg',
    # Florestal - arroba
    'Erva-mate': 'arroba',
    'Erva-mate folha em barranco': 'arroba',
    # Hortaliças - tonelada
    'Mandioca industrial': 'tonelada',
}


def get_canonical_unit(product_name: str) -> Optional[str]:
    """Get the canonical unit for a product."""
    if not product_name:
        return None

    # Direct lookup
    if product_name in PRODUCT_UNITS:
        return PRODUCT_UNITS[product_name]

    # Try case-insensitive lookup
    product_lower = product_name.lower()
    for prod, unit in PRODUCT_UNITS.items():
        if prod.lower() == product_lower:
            return unit

    # Try partial matching for common products
    if 'soja' in product_lower:
        return 'sc 60 Kg'
    if 'milho' in product_lower:
        return 'sc 60 Kg'
    if 'trigo' in product_lower:
        return 'sc 60 Kg'
    if 'feij' in product_lower:
        return 'sc 60 Kg'
    if 'arroz' in product_lower:
        return 'sc 60 Kg'
    if 'cafe' in product_lower or 'café' in product_lower:
        if 'coco' in product_lower:
            return 'kg renda'
        return 'sc 60 Kg'
    if 'boi' in product_lower or 'vaca' in product_lower:
        return 'arroba'
    if 'suino' in product_lower or 'suíno' in product_lower:
        return 'kg'
    if 'frango' in product_lower:
        return 'kg'
    if 'erva' in product_lower:
        return 'arroba'
    if 'mandioca' in product_lower:
        return 'tonelada'
    if 'algod' in product_lower:
        return 'arroba'

    return None


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


def is_unit(text: str) -> bool:
    """Check if text is a unit of measurement."""
    if not text:
        return False
    text_lower = text.lower().strip()
    return text_lower in UNITS or re.match(r'^sc\s*\d+\s*kg?$', text_lower, re.IGNORECASE)


def is_type_variety(text: str) -> bool:
    """Check if text is a type/variety descriptor."""
    if not text:
        return False
    text_lower = text.lower().strip()
    for t in TYPES_VARIETIES:
        if t in text_lower:
            return True
    return False


def is_invalid_entry(text: str) -> bool:
    """Check if text is an invalid entry."""
    if not text:
        return True
    text_lower = text.lower().strip()
    if text_lower in INVALID_ENTRIES:
        return True
    if len(text_lower) < 3:
        return True
    if re.match(r'^\d+$', text_lower):
        return True
    if re.match(r'^\\', text_lower):
        return True
    # Filter entries that start with unit patterns
    if re.match(r'^sc\s*\d+', text_lower):
        return True
    if re.match(r'^em\s*barranco', text_lower):
        return True
    if re.match(r'^embarranco', text_lower):
        return True
    if text_lower.startswith('('):
        return True
    return False


def extract_unit_from_text(text: str) -> Tuple[str, Optional[str]]:
    """Extract unit from the end of product text."""
    if not text:
        return '', None

    # Patterns for units at the end
    unit_patterns = [
        r'\s+(sc\s*\d+\s*[Kk]g)\s*$',
        r'\s+(arroba)\s*$',
        r'\s+(kg\s*renda)\s*$',
        r'\s+(kg\s*embranco)\s*$',
        r'\s+(kg)\s*$',
        r'\s+(tonelada)\s*$',
        r'\s+(duzia)\s*$',
        r'\s+(caixa)\s*$',
        r'\s+(litro)\s*$',
        r'\s+(un\.?)\s*$',
    ]

    for pattern in unit_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            unit = match.group(1).strip()
            product = text[:match.start()].strip()
            return product, unit

    return text, None


def parse_date_from_sheet(sheet_name: str, filename: str) -> Optional[datetime]:
    """Parse date from sheet name."""
    patterns = [
        r'(\d{2})-(\d{2})-(\d{2,4})',
        r'(\d{2})_(\d{2})_(\d{2,4})',
        r'^(\d{2})$',  # Just day number
    ]

    for pattern in patterns:
        match = re.search(pattern, sheet_name)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                day, month, year = groups
                year = int(year)
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year
                try:
                    return datetime(year, int(month), int(day))
                except ValueError:
                    continue
            elif len(groups) == 1:
                # Just day - need to get month/year from filename
                day = int(groups[0])
                year_match = re.search(r'(19|20)\d{2}', filename)
                month_map = {
                    'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4,
                    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
                }
                month = None
                for m_name, m_num in month_map.items():
                    if m_name in filename.lower():
                        month = m_num
                        break
                if year_match and month:
                    try:
                        return datetime(int(year_match.group()), month, day)
                    except ValueError:
                        pass

    return None


def parse_number(value) -> Optional[float]:
    """Parse a number from string, handling Brazilian format."""
    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        if isinstance(value, float) and np.isnan(value):
            return None
        return float(value)

    value = str(value).strip()

    if value.upper() in ['\\\\\\', 'SINF', 'AUS', '-', '--', '', 'NaN']:
        return None

    value = re.sub(r'R\$\s*', '', value)
    value = re.sub(r'\s+', '', value)

    if ',' in value:
        if '.' in value and value.rindex('.') < value.rindex(','):
            value = value.replace('.', '')
        value = value.replace(',', '.')

    try:
        result = float(value)
        if result <= 0 or result > 100000:
            return None
        return result
    except ValueError:
        return None


def find_data_start_row(df: pd.DataFrame) -> int:
    """Find the row where data starts."""
    for idx in range(min(10, len(df))):
        row = df.iloc[idx]
        if pd.notna(row.iloc[0]):
            cell_text = str(row.iloc[0]).upper()
            if 'PRODUTO' in cell_text:
                return idx + 2  # Skip header and one more row
    return 5


def process_sheet(df: pd.DataFrame, date: datetime, filename: str) -> List[dict]:
    """Process a single sheet and extract records."""
    records = []

    if df.empty or len(df) < 6:
        return records

    data_start = find_data_start_row(df)

    # Track current product for multi-row format
    current_base_product = None
    current_type = None
    current_unit = None
    pending_prices = []

    for row_idx in range(data_start, len(df)):
        row = df.iloc[row_idx]

        # Get column 0 and 1 values
        cell0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        cell1 = str(row.iloc[1]).upper().strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''

        # Determine if this is MIN, M_C, or MAX row
        is_min = cell1 == 'MIN'
        is_mc = cell1 == 'M_C'
        is_max = cell1 in ['MAX', 'MÁX', 'M�X']

        if not (is_min or is_mc or is_max):
            continue

        # Extract prices from columns 2+
        prices = []
        for col_idx in range(2, min(len(row), 22)):  # Limit to regional columns
            price = parse_number(row.iloc[col_idx])
            if price:
                prices.append(price)

        # Check what's in cell0
        if cell0:
            cell0_clean = cell0.replace('\n', ' ').strip()

            # Check if it's the new format (product + unit in same cell)
            product_text, unit = extract_unit_from_text(cell0_clean)

            if unit:
                # New format: "Product name    unit"
                if product_text and not is_invalid_entry(product_text):
                    current_base_product = product_text
                    current_type = None
                    current_unit = unit
            elif is_unit(cell0_clean):
                # Old format: unit row (MAX row)
                current_unit = cell0_clean
            elif is_type_variety(cell0_clean):
                # Old format: type/variety row (M_C row)
                current_type = cell0_clean
            elif not is_invalid_entry(cell0_clean):
                # New product name (MIN row or new format)
                current_base_product = cell0_clean
                current_type = None
                current_unit = None

        # Only record on M_C rows
        if is_mc and current_base_product and prices:
            # Build full product name
            if current_type:
                full_product = f"{current_base_product} {current_type}"
            else:
                full_product = current_base_product

            # Clean up product name
            full_product = re.sub(r'\s+', ' ', full_product).strip()

            record = {
                'data': date.strftime('%Y-%m-%d') if date else None,
                'ano': date.year if date else None,
                'mes': date.month if date else None,
                'dia': date.day if date else None,
                'produto': full_product,
                'unidade': current_unit,
                'categoria': detect_category(full_product),
                'preco_medio': round(sum(prices) / len(prices), 2),
                'preco_minimo': round(min(prices), 2),
                'preco_maximo': round(max(prices), 2),
                'num_cotacoes': len(prices),
                'arquivo': filename,
            }
            records.append(record)

    return records


def process_excel_file(filepath: Path) -> List[dict]:
    """Process a single Excel file with multiple sheets."""
    all_records = []

    try:
        engine = 'xlrd' if filepath.suffix == '.xls' else 'openpyxl'
        xl = pd.ExcelFile(filepath, engine=engine)

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
            except Exception:
                continue

    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")

    return all_records


def load_scraped_data() -> pd.DataFrame:
    """Load data from web scraping."""
    scraped_csv = DATA_SCRAPED_DIR / "scraped_quotations.csv"
    if scraped_csv.exists():
        logger.info(f"Loading scraped data from {scraped_csv}")
        return pd.read_csv(scraped_csv, encoding='utf-8-sig')
    return pd.DataFrame()


def normalize_products(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize product names to reduce variations."""

    # Standard product name mappings (order matters - more specific first)
    product_map = {
        # Grains - Arroz
        r'(?i)arroz.*(agulhinha|casca).*tipo\s*1': 'Arroz em casca tipo 1',
        r'(?i)arroz.*sequeiro': 'Arroz sequeiro',
        r'(?i)arroz.*irrigado': 'Arroz irrigado',
        # Grains - Soja
        r'(?i)soja\s*industrial\s*tipo\s*1': 'Soja industrial tipo 1',
        r'(?i)soja\s*industrial': 'Soja industrial tipo 1',
        r'(?i)sojaindustrial': 'Soja industrial tipo 1',
        r'(?i)^soja\s*$': 'Soja industrial tipo 1',
        # Grains - Milho
        r'(?i)milho\s*amarelo': 'Milho amarelo tipo 1',
        r'(?i)milho.*tipo\s*1': 'Milho amarelo tipo 1',
        r'(?i)milho.*comum': 'Milho comum',
        r'(?i)^milho\s*$': 'Milho',
        # Grains - Trigo
        r'(?i)trigo.*(pao|ph|78)': 'Trigo pão',
        r'(?i)^trigo\s*$': 'Trigo',
        # Grains - Feijão (using . for ã to handle encoding issues)
        r'(?i)feij.o\s*preto\s*tipo': 'Feijão preto tipo 1',
        r'(?i)feij.o\s*preto': 'Feijão preto tipo 1',
        r'(?i)feij.o\s*carioca\s*tipo': 'Feijão carioca tipo 1',
        r'(?i)feij.o\s*carioca': 'Feijão carioca tipo 1',
        r'(?i)feij.o.*(cor|de\s*cor)': 'Feijão de cor tipo 1',
        # Grains - Café (using . for é, handles typo "beneficado" vs "beneficiado")
        r'(?i)caf.\s*benefici?ado\s*bebida\s*dura': 'Café beneficiado bebida dura tipo 6',
        r'(?i)caf.\s*benefici?ado': 'Café beneficiado bebida dura tipo 6',
        r'(?i)caf.\s*(em\s*)?coco': 'Café em coco',
        r'(?i)algod.o': 'Algodão em caroço',
        # Livestock - Boi/Vaca
        r'(?i)boi\s*gordo': 'Boi gordo',
        r'(?i)boi.*(em\s*)?p[eé]': 'Boi em pé',
        r'(?i)^boi\s*$': 'Boi em pé',
        r'(?i)vaca\s*gorda': 'Vaca gorda',
        r'(?i)vaca.*(em\s*)?p[eé]': 'Vaca em pé',
        r'(?i)^vaca\s*$': 'Vaca em pé',
        # Livestock - Suíno (using . for í/é/ã to handle encoding issues)
        r'(?i)su.no\s*(em\s*)?p.\s*tipo\s*carne\s*n.o\s*integrado': 'Suíno em pé tipo carne não integrado',
        r'(?i)su.no\s*(em\s*)?p.\s*tipo\s*carne': 'Suíno em pé tipo carne',
        r'(?i)su.noemp.\s*tipocarne': 'Suíno em pé tipo carne',
        r'(?i)su.no\s*(em\s*)?p.': 'Suíno em pé tipo carne',
        r'(?i)^su.no\s*$': 'Suíno em pé tipo carne',
        r'(?i)frango.*corte': 'Frango de corte',
        # Forestry
        r'(?i)erva[\s\-]?mate\s*folha\s*(em\s*)?barranco': 'Erva-mate folha em barranco',
        r'(?i)erva[\s\-]?mate': 'Erva-mate',
        # Vegetables
        r'(?i)mandioca\s*industrial': 'Mandioca industrial',
        r'(?i)mandioca.*amido': 'Mandioca industrial',
        r'(?i)^mandioca\s*$': 'Mandioca industrial',
    }

    # Patterns to remove entirely
    invalid_patterns = [
        r'(?i)^sc\s*\d+',          # Starts with unit
        r'(?i)^em\s*barranco',     # Starts with location
        r'(?i)^embarranco',        # Concatenated location
        r'(?i)^\(vivo\)',          # Fragment
        r'(?i)^vaca\s+bebida',     # Wrong combination
        r'(?i)^gr\.?longo',        # Rice variety fragment
        r'(?i)^irrigado\s*$',      # Just type
        r'(?i)^sequeiro\s*$',      # Just type
        r'(?i)^tipo\s*\d+\s*$',    # Just type number
        r'(?i)^tipo\s*carne',      # Just type
        r'(?i)^n[aã]o\s*integrado',# Just modifier
        r'(?i)^arroba\s*$',        # Just unit
        r'(?i)^kg\s*$',            # Just unit
        r'(?i)vaca.*caf[eé]',      # Wrong combination
        r'(?i)caf[eé].*vaca',      # Wrong combination
    ]

    def clean_product_name(name):
        """Clean up product name - remove trailing punctuation and normalize whitespace."""
        if not name:
            return None

        # Convert to string and strip
        name = str(name).strip()

        # Remove trailing punctuation
        name = re.sub(r'[.,;:!?\s]+$', '', name)

        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name).strip()

        return name if name else None

    def normalize_product(name):
        if not name:
            return None

        # Clean the name first
        name = clean_product_name(name)
        if not name:
            return None

        # Check if it matches invalid patterns
        for pattern in invalid_patterns:
            if re.search(pattern, name):
                return None

        # Check for normalization
        for pattern, replacement in product_map.items():
            if re.search(pattern, name):
                return replacement

        # If no mapping found, apply basic cleanup:
        # - Title case
        # - Fix common word casing
        name = name.title()

        # Fix common title case issues
        name = re.sub(r'\bEm\b', 'em', name)
        name = re.sub(r'\bDe\b', 'de', name)
        name = re.sub(r'\bDa\b', 'da', name)
        name = re.sub(r'\bDo\b', 'do', name)
        name = re.sub(r'\bTipo\b', 'tipo', name)
        name = re.sub(r'\bN[aã]o\b', 'não', name)

        # Fix product-specific accents
        name = re.sub(r'\bCafe\b', 'Café', name)
        name = re.sub(r'\bFeijao\b', 'Feijão', name)
        name = re.sub(r'\bSuino\b', 'Suíno', name)
        name = re.sub(r'\bPe\b', 'pé', name)
        name = re.sub(r'Erva-Mate', 'Erva-mate', name)

        return name.strip()

    # Apply normalization
    df['produto'] = df['produto'].apply(normalize_product)

    # Remove rows with None products
    df = df[df['produto'].notna()]

    # Set canonical units for each product
    df['unidade'] = df['produto'].apply(get_canonical_unit)

    return df


def process_all_files():
    """Process all Excel files and scraped data."""
    logger.info("=" * 60)
    logger.info("SIMA Daily Quotations - ETL Pipeline")
    logger.info("=" * 60)

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

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

    # Normalize product names
    logger.info("Normalizing product names...")
    df = normalize_products(df)

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

    logger.info("\n  Top 10 products by records:")
    top_products = df['produto'].value_counts().head(10)
    for prod, count in top_products.items():
        logger.info(f"    - {prod}: {count:,}")

    logger.info("=" * 60)


if __name__ == "__main__":
    process_all_files()
