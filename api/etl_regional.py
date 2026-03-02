#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL Pipeline for SIMA Daily Quotations with Regional Granularity
Processes Excel files and extracts per-regional pricing data.

Output: consolidated.csv with columns:
  data, ano, mes, dia, produto, unidade, categoria, regional, preco, arquivo
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
OUTPUT_FILE_REGIONAL = DATA_PROCESSED_DIR / "consolidated_regional.csv"
OUTPUT_FILE_AGGREGATED = DATA_PROCESSED_DIR / "consolidated.csv"  # Backwards compatible

# 23 Regional Nuclei (IDR) of Paraná - standardized names
REGIONAIS_PADRAO = [
    'Apucarana', 'Campo Mourão', 'Cascavel', 'Cianorte', 'Cornélio Procópio',
    'Curitiba', 'Dois Vizinhos', 'Francisco Beltrão', 'Guarapuava', 'Irati',
    'Ivaiporã', 'Laranjeiras do Sul', 'Londrina', 'Maringá', 'Paranaguá',
    'Paranavaí', 'Pato Branco', 'Pitanga', 'Ponta Grossa',
    'Santo Antônio da Platina', 'Toledo', 'Umuarama', 'União da Vitória'
]

# Mapping of common abbreviations/variations to standard names
REGIONAL_ALIASES = {
    'apucarana': 'Apucarana',
    'c.mourao': 'Campo Mourão', 'campo mourao': 'Campo Mourão', 'c. mourão': 'Campo Mourão',
    'c mourao': 'Campo Mourão', 'campo mourão': 'Campo Mourão', 'cm': 'Campo Mourão',
    'cascavel': 'Cascavel',
    'cianorte': 'Cianorte',
    'c.procopio': 'Cornélio Procópio', 'cornelio procopio': 'Cornélio Procópio', 'c. procópio': 'Cornélio Procópio',
    'c procopio': 'Cornélio Procópio',
    'curitiba': 'Curitiba',
    'dois vizinhos': 'Dois Vizinhos', 'd.vizinhos': 'Dois Vizinhos', 'd vizinhos': 'Dois Vizinhos',
    'f.beltrao': 'Francisco Beltrão', 'francisco beltrao': 'Francisco Beltrão', 'f. beltrão': 'Francisco Beltrão',
    'f beltrao': 'Francisco Beltrão',
    'guarapuava': 'Guarapuava',
    'irati': 'Irati',
    'ivaipora': 'Ivaiporã', 'ivaiporã': 'Ivaiporã',
    'laranjeiras': 'Laranjeiras do Sul', 'laranjeiras do sul': 'Laranjeiras do Sul', 'l. sul': 'Laranjeiras do Sul',
    'l sul': 'Laranjeiras do Sul', 'l.sul': 'Laranjeiras do Sul',
    'londrina': 'Londrina',
    'maringa': 'Maringá', 'maringá': 'Maringá',
    'paranagua': 'Paranaguá', 'paranaguá': 'Paranaguá',
    'paranavai': 'Paranavaí', 'paranavaí': 'Paranavaí',
    'p.branco': 'Pato Branco', 'pato branco': 'Pato Branco', 'p. branco': 'Pato Branco',
    'p branco': 'Pato Branco',
    'pitanga': 'Pitanga',
    'p.grossa': 'Ponta Grossa', 'ponta grossa': 'Ponta Grossa', 'p. grossa': 'Ponta Grossa',
    'pg': 'Ponta Grossa', 'pta grossa': 'Ponta Grossa', 'pont. grossa': 'Ponta Grossa',
    'ponta-grossa': 'Ponta Grossa', 'pta. grossa': 'Ponta Grossa',
    's.a.platina': 'Santo Antônio da Platina', 'sto antonio': 'Santo Antônio da Platina',
    's.a. platina': 'Santo Antônio da Platina', 'santo antonio da platina': 'Santo Antônio da Platina',
    'sa platina': 'Santo Antônio da Platina', 'sap': 'Santo Antônio da Platina',
    'toledo': 'Toledo',
    'umuarama': 'Umuarama',
    'u.vitoria': 'União da Vitória', 'uniao da vitoria': 'União da Vitória', 'u. vitória': 'União da Vitória',
    'u vitoria': 'União da Vitória',
}

# Category mappings
CATEGORIAS = {
    'SOJA': 'Grãos', 'MILHO': 'Grãos', 'TRIGO': 'Grãos', 'FEIJAO': 'Grãos',
    'ARROZ': 'Grãos', 'AVEIA': 'Grãos', 'CEVADA': 'Grãos', 'CENTEIO': 'Grãos',
    'SORGO': 'Grãos', 'TRITICALE': 'Grãos', 'CANOLA': 'Grãos', 'GIRASSOL': 'Grãos',
    'AMENDOIM': 'Grãos', 'CAFE': 'Café', 'ALGODAO': 'Grãos',
    'LARANJA': 'Frutas', 'BANANA': 'Frutas', 'UVA': 'Frutas', 'MACA': 'Frutas',
    'MELANCIA': 'Frutas', 'MELAO': 'Frutas', 'MAMAO': 'Frutas', 'ABACAXI': 'Frutas',
    'MORANGO': 'Frutas', 'PESSEGO': 'Frutas', 'AMEIXA': 'Frutas', 'FIGO': 'Frutas',
    'CAQUI': 'Frutas', 'GOIABA': 'Frutas', 'MANGA': 'Frutas', 'MARACUJA': 'Frutas',
    'LIMAO': 'Frutas', 'TANGERINA': 'Frutas', 'PONCAN': 'Frutas', 'ABACATE': 'Frutas',
    'TOMATE': 'Hortaliças', 'BATATA': 'Hortaliças', 'CEBOLA': 'Hortaliças',
    'ALHO': 'Hortaliças', 'MANDIOCA': 'Mandioca', 'CENOURA': 'Hortaliças',
    'BETERRABA': 'Hortaliças', 'REPOLHO': 'Hortaliças', 'ALFACE': 'Hortaliças',
    'COUVE': 'Hortaliças', 'PEPINO': 'Hortaliças', 'PIMENTAO': 'Hortaliças',
    'ABOBRINHA': 'Hortaliças', 'ABOBORA': 'Hortaliças', 'CHUCHU': 'Hortaliças',
    'QUIABO': 'Hortaliças', 'BERINJELA': 'Hortaliças', 'VAGEM': 'Hortaliças',
    'BOI': 'Pecuária', 'VACA': 'Pecuária', 'NOVILHO': 'Pecuária', 'BEZERRO': 'Pecuária',
    'SUINO': 'Pecuária', 'PORCO': 'Pecuária', 'FRANGO': 'Pecuária', 'GALINHA': 'Pecuária',
    'OVO': 'Pecuária', 'OVINO': 'Pecuária', 'CAPRINO': 'Pecuária', 'LEITE': 'Pecuária',
    'MADEIRA': 'Florestal', 'LENHA': 'Florestal', 'PINUS': 'Florestal',
    'EUCALIPTO': 'Florestal', 'ERVA-MATE': 'Florestal', 'ERVA MATE': 'Florestal',
}

# Product unit mapping
PRODUCT_UNITS = {
    'Soja industrial tipo 1': 'sc 60 Kg',
    'Milho amarelo tipo 1': 'sc 60 Kg',
    'Trigo pão': 'sc 60 Kg',
    'Feijão preto tipo 1': 'sc 60 Kg',
    'Feijão carioca tipo 1': 'sc 60 Kg',
    'Arroz em casca tipo 1': 'sc 60 Kg',
    'Café beneficiado bebida dura tipo 6': 'sc 60 Kg',
    'Café em coco': 'kg renda',
    'Boi em pé': 'arroba',
    'Vaca em pé': 'arroba',
    'Suíno em pé tipo carne': 'kg',
    'Frango de corte': 'kg',
    'Erva-mate folha em barranco': 'arroba',
    'Mandioca industrial': 'tonelada',
    'Algodão em caroço': 'arroba',
}


def normalize_text(text: str) -> str:
    """Normalize text by removing accents and converting to uppercase."""
    if not isinstance(text, str):
        return ''
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return text.upper().strip()


def normalize_regional(name: str) -> Optional[str]:
    """Normalize regional name to standard format."""
    if not name or pd.isna(name):
        return None

    # Clean and lowercase
    name_clean = str(name).strip().lower()
    name_clean = re.sub(r'\s+', ' ', name_clean)
    name_clean = unicodedata.normalize('NFKD', name_clean)
    name_clean = ''.join(c for c in name_clean if not unicodedata.combining(c))

    # Check aliases
    if name_clean in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_clean]

    # Try partial match - require minimum length to avoid false positives
    if len(name_clean) >= 5:
        for alias, standard in REGIONAL_ALIASES.items():
            if alias in name_clean or name_clean in alias:
                return standard

        # Try matching against standard list (fuzzy)
        for standard in REGIONAIS_PADRAO:
            standard_lower = standard.lower()
            standard_norm = unicodedata.normalize('NFKD', standard_lower)
            standard_norm = ''.join(c for c in standard_norm if not unicodedata.combining(c))
            if standard_norm in name_clean or name_clean in standard_norm:
                return standard

    return None


def detect_category(product: str) -> str:
    """Detect product category."""
    product_norm = normalize_text(product)
    for key, category in CATEGORIAS.items():
        if key in product_norm:
            return category
    return 'Outros'


def get_canonical_unit(product_name: str) -> Optional[str]:
    """Get the canonical unit for a product."""
    if not product_name:
        return None

    if product_name in PRODUCT_UNITS:
        return PRODUCT_UNITS[product_name]

    product_lower = product_name.lower()
    if 'soja' in product_lower or 'milho' in product_lower or 'trigo' in product_lower:
        return 'sc 60 Kg'
    if 'feij' in product_lower or 'arroz' in product_lower:
        return 'sc 60 Kg'
    if 'cafe' in product_lower or 'café' in product_lower:
        if 'coco' in product_lower:
            return 'kg renda'
        return 'sc 60 Kg'
    if 'boi' in product_lower or 'vaca' in product_lower:
        return 'arroba'
    if 'suino' in product_lower or 'suíno' in product_lower or 'frango' in product_lower:
        return 'kg'
    if 'erva' in product_lower:
        return 'arroba'
    if 'mandioca' in product_lower:
        return 'tonelada'

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


def extract_regional_headers(df: pd.DataFrame) -> Dict[int, str]:
    """Extract regional names from Excel header rows."""
    regional_cols = {}

    # Scan first 10 rows (was 5) and ALL columns (was max 25)
    for row_idx in range(min(10, len(df))):
        row = df.iloc[row_idx]

        for col_idx in range(2, len(row)):  # Removed the min(len(row), 25) cap
            cell = row.iloc[col_idx]
            if pd.notna(cell):
                cell_str = str(cell).strip()
                # Skip numeric cells, short strings, and known non-regional values
                if len(cell_str) < 3:
                    continue
                try:
                    float(cell_str.replace(',', '.'))
                    continue  # It's a number, skip
                except ValueError:
                    pass
                regional = normalize_regional(cell_str)
                if regional and col_idx not in regional_cols:
                    regional_cols[col_idx] = regional

    # If no headers found, use default order but ONLY for columns that exist
    if not regional_cols:
        default_order = REGIONAIS_PADRAO[:min(20, max(0, len(df.columns) - 2))]
        for i, reg in enumerate(default_order):
            col = i + 2
            if col < len(df.columns):
                regional_cols[col] = reg

    return regional_cols


def parse_date_from_sheet(sheet_name: str, filename: str) -> Optional[datetime]:
    """Parse date from sheet name."""
    patterns = [
        r'(\d{2})-(\d{2})-(\d{2,4})',
        r'(\d{2})_(\d{2})_(\d{2,4})',
        r'^(\d{2})$',
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


def is_invalid_entry(text: str) -> bool:
    """Check if text is an invalid entry."""
    if not text:
        return True

    text_lower = text.lower().strip()
    invalid = {'min', 'max', 'máx', 'm_c', 'media', 'média', 'nan', 'none', '-', '--',
               '\\\\\\', 'sinf', 'aus', 'produto', 'produtos', 'total', 'fonte'}

    if text_lower in invalid:
        return True
    if len(text_lower) < 3:
        return True
    if re.match(r'^\d+$', text_lower):
        return True
    if re.match(r'^sc\s*\d+', text_lower):
        return True

    return False


def extract_unit_from_text(text: str) -> Tuple[str, Optional[str]]:
    """Extract unit from the end of product text."""
    if not text:
        return '', None

    unit_patterns = [
        r'\s+(sc\s*\d+\s*[Kk]g)\s*$',
        r'\s+(arroba)\s*$',
        r'\s+(kg\s*renda)\s*$',
        r'\s+(kg)\s*$',
        r'\s+(tonelada)\s*$',
    ]

    for pattern in unit_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            unit = match.group(1).strip()
            product = text[:match.start()].strip()
            return product, unit

    return text, None


def normalize_product_name(name: str) -> Optional[str]:
    """Normalize product name to standard format."""
    if not name:
        return None

    # Clean trailing punctuation artifacts from Excel parsing
    name = re.sub(r'\s*[,\.]+\s*$', '', name)
    name = name.strip()

    product_map = {
        # Bare product names (must come BEFORE more specific patterns)
        r'(?i)^soja\s*$': 'Soja industrial tipo 1',
        r'(?i)^boi\s*$': 'Boi em pé',
        r'(?i)^vaca\s*$': 'Vaca em pé',
        r'(?i)^caf[eé]\s*$': 'Café em coco',
        r'(?i)^frango\s*$': 'Frango de corte',
        r'(?i)^trigo\s*$': 'Trigo pão',
        r'(?i)^milho\s*comum\s*$': 'Milho amarelo tipo 1',
        r'(?i)^milhocomum\s*$': 'Milho amarelo tipo 1',
        r'(?i)^feij.o\s*de\s*cor\s*$': 'Feijão de cor tipo 1',
        r'(?i)^feij.odecor\s*$': 'Feijão de cor tipo 1',
        r'(?i)^arroz\s*em\s*casca\s*$': 'Arroz em casca tipo 1',
        r'(?i)^arrozemcasca\s*$': 'Arroz em casca tipo 1',
        # Specific patterns
        r'(?i)soja\s*industrial': 'Soja industrial tipo 1',
        r'(?i)milho\s*amarelo': 'Milho amarelo tipo 1',
        r'(?i)milho.*tipo\s*1': 'Milho amarelo tipo 1',
        r'(?i)trigo.*(pao|ph)': 'Trigo pão',
        r'(?i)feij.o\s*preto': 'Feijão preto tipo 1',
        r'(?i)feij.o\s*carioca': 'Feijão carioca tipo 1',
        r'(?i)arroz.*(casca|agulhinha).*tipo\s*1': 'Arroz em casca tipo 1',
        r'(?i)caf.\s*benefici?ado': 'Café beneficiado bebida dura tipo 6',
        r'(?i)caf.\s*(em\s*)?coco': 'Café em coco',
        r'(?i)boi.*(em\s*)?p[eé]': 'Boi em pé',
        r'(?i)boi\s*gordo': 'Boi gordo',
        r'(?i)vaca.*(em\s*)?p[eé]': 'Vaca em pé',
        r'(?i)su.no\s*(em\s*)?p.': 'Suíno em pé tipo carne',
        r'(?i)frango.*corte': 'Frango de corte',
        r'(?i)erva[\s\-]?mate.*folha': 'Erva-mate folha em barranco',
        r'(?i)erva[\s\-]?mate': 'Erva-mate',
        r'(?i)mandioca': 'Mandioca industrial',
        r'(?i)algod.o': 'Algodão em caroço',
    }

    for pattern, replacement in product_map.items():
        if re.search(pattern, name):
            return replacement

    # Basic cleanup
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    name = name.title()

    # Fix common casing
    name = re.sub(r'\bEm\b', 'em', name)
    name = re.sub(r'\bDe\b', 'de', name)
    name = re.sub(r'\bTipo\b', 'tipo', name)

    return name


def process_sheet_regional(df: pd.DataFrame, date: datetime, filename: str) -> List[dict]:
    """Process a single sheet and extract per-regional records."""
    records = []

    if df.empty or len(df) < 6:
        return records

    # Extract regional headers from first rows
    regional_cols = extract_regional_headers(df)

    if not regional_cols:
        logger.warning(f"No regional headers found in {filename}")
        return records

    # Find data start row
    data_start = 5
    for idx in range(min(10, len(df))):
        row = df.iloc[idx]
        if pd.notna(row.iloc[0]):
            cell_text = str(row.iloc[0]).upper()
            if 'PRODUTO' in cell_text:
                data_start = idx + 2
                break

    # Track current product
    current_base_product = None
    current_type = None
    current_unit = None

    for row_idx in range(data_start, len(df)):
        row = df.iloc[row_idx]

        cell0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        cell1 = str(row.iloc[1]).upper().strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''

        is_mc = cell1 == 'M_C'

        if not is_mc:
            # Update product tracking for MIN/MAX rows
            if cell0:
                cell0_clean = cell0.replace('\n', ' ').strip()
                product_text, unit = extract_unit_from_text(cell0_clean)

                if unit:
                    if product_text and not is_invalid_entry(product_text):
                        current_base_product = product_text
                        current_type = None
                        current_unit = unit
                elif not is_invalid_entry(cell0_clean):
                    current_base_product = cell0_clean
                    current_type = None
                    current_unit = None
            continue

        # Process M_C row - extract prices per regional
        if not current_base_product:
            continue

        # Build full product name
        if current_type:
            full_product = f"{current_base_product} {current_type}"
        else:
            full_product = current_base_product

        full_product = normalize_product_name(full_product)
        if not full_product:
            continue

        # Extract prices for each regional
        for col_idx, regional in regional_cols.items():
            if col_idx >= len(row):
                continue

            price = parse_number(row.iloc[col_idx])
            if price is not None:
                record = {
                    'data': date.strftime('%Y-%m-%d') if date else None,
                    'ano': date.year if date else None,
                    'mes': date.month if date else None,
                    'dia': date.day if date else None,
                    'produto': full_product,
                    'unidade': current_unit or get_canonical_unit(full_product),
                    'categoria': detect_category(full_product),
                    'regional': regional,
                    'preco': round(price, 2),
                    'arquivo': filename,
                }
                records.append(record)

    return records


def extract_date_from_filename(filename: str, sheet_name: str = '') -> Optional[datetime]:
    """Extract date from filename patterns used in SIMA archives."""
    month_names = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    }

    fn_lower = filename.lower().strip()

    # Pattern 1: "Abril 2017", "Janeiro 2018", "Marco 2017"
    for name, num in month_names.items():
        match = re.search(rf'{name}\s*((?:19|20)\d{{2}})', fn_lower)
        if match:
            year = int(match.group(1))
            day = int(sheet_name) if re.match(r'^\d{1,2}$', sheet_name.strip()) else 1
            day = min(max(day, 1), 28)  # Safety clamp
            try:
                return datetime(year, num, day)
            except ValueError:
                return datetime(year, num, 1)

    # Pattern 2: "Resumo Sima_MMYY" or "Resumo SIMA_MMYY" or "Resumo_MMYY"
    match = re.search(r'[_\s](\d{2})[\s_]?(\d{2})(?:\s|$|\.)', fn_lower)
    if match:
        mm, yy = int(match.group(1)), int(match.group(2))
        if 1 <= mm <= 12 and 0 <= yy <= 99:
            year = 2000 + yy if yy < 50 else 1900 + yy
            day = int(sheet_name) if re.match(r'^\d{1,2}$', sheet_name.strip()) else 1
            day = min(max(day, 1), 28)
            try:
                return datetime(year, mm, day)
            except ValueError:
                return datetime(year, mm, 1)

    # Pattern 3: "ResumoSIMA_Ago01" (abbreviated month + YY)
    for name, num in month_names.items():
        match = re.search(rf'{name}\s*(\d{{2}})(?:\s|$|\.)', fn_lower)
        if match:
            yy = int(match.group(1))
            year = 2000 + yy if yy < 50 else 1900 + yy
            day = int(sheet_name) if re.match(r'^\d{1,2}$', sheet_name.strip()) else 1
            day = min(max(day, 1), 28)
            try:
                return datetime(year, num, day)
            except ValueError:
                return datetime(year, num, 1)

    return None


def process_excel_file(filepath: Path) -> List[dict]:
    """Process a single Excel file with multiple sheets."""
    all_records = []

    try:
        engine = 'xlrd' if filepath.suffix == '.xls' else 'openpyxl'
        xl = pd.ExcelFile(filepath, engine=engine)

        for sheet_name in xl.sheet_names:
            date = parse_date_from_sheet(sheet_name, filepath.stem)

            if not date:
                # Try to extract month/year from filename patterns like:
                # "Resumo Sima_0107" (MMYY), "Resumo SIMA_0105" (MMYY),
                # "Resumo_0102" (MMYY), "ResumoSIMA_Ago01" (MonYY),
                # "Abril 2017" (Month Year), "Janeiro 2018" (Month Year)
                date = extract_date_from_filename(filepath.stem, sheet_name)

            if not date:
                year_match = re.search(r'(19|20)\d{2}', filepath.stem)
                if year_match:
                    year = int(year_match.group())
                    date = datetime(year, 1, 1)

            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                records = process_sheet_regional(df, date, filepath.name)
                all_records.extend(records)
            except Exception:
                continue

    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")

    return all_records


def generate_aggregated_csv(df: pd.DataFrame):
    """Generate aggregated CSV (backwards compatible format)."""
    agg = df.groupby(['data', 'ano', 'mes', 'dia', 'produto', 'unidade', 'categoria']).agg({
        'preco': ['mean', 'min', 'max', 'count']
    }).reset_index()

    agg.columns = ['data', 'ano', 'mes', 'dia', 'produto', 'unidade', 'categoria',
                   'preco_medio', 'preco_minimo', 'preco_maximo', 'num_cotacoes']

    agg['preco_medio'] = agg['preco_medio'].round(2)
    agg['preco_minimo'] = agg['preco_minimo'].round(2)
    agg['preco_maximo'] = agg['preco_maximo'].round(2)

    agg.to_csv(OUTPUT_FILE_AGGREGATED, index=False, encoding='utf-8-sig')
    logger.info(f"Saved aggregated to: {OUTPUT_FILE_AGGREGATED}")


def process_all_files():
    """Process all Excel files and generate regional data."""
    logger.info("=" * 60)
    logger.info("SIMA Regional ETL Pipeline")
    logger.info("=" * 60)

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    excel_patterns = ['*.xlsx', '*.xls', '*.xlsm']
    excel_files = []

    if DATA_EXTRACTED_DIR.exists():
        for pattern in excel_patterns:
            excel_files.extend(DATA_EXTRACTED_DIR.rglob(pattern))  # Changed from .glob() to .rglob()

    daily_dir = DATA_EXTRACTED_DIR / "daily"
    if daily_dir.exists():
        for pattern in excel_patterns:
            excel_files.extend(daily_dir.glob(pattern))  # Keep non-recursive for daily/

    excel_files = sorted(set(excel_files))  # Deduplicate after collecting
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
    logger.info(f"Records extracted: {len(all_records)}")

    if not all_records:
        logger.error("No records extracted!")
        return

    logger.info("Consolidating data...")
    df = pd.DataFrame(all_records)

    # Remove duplicates
    df = df.drop_duplicates(subset=['data', 'produto', 'regional', 'preco'])
    logger.info(f"After dedup: {len(df)} records")

    # Sort
    df = df.sort_values(['ano', 'mes', 'dia', 'produto', 'regional'], na_position='last')

    # Save regional granular data
    df.to_csv(OUTPUT_FILE_REGIONAL, index=False, encoding='utf-8-sig')
    logger.info(f"Saved regional to: {OUTPUT_FILE_REGIONAL}")

    # Generate aggregated version for backwards compatibility
    generate_aggregated_csv(df)

    # Summary
    logger.info("=" * 60)
    logger.info("ETL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total records:      {len(df):,}")
    logger.info(f"  Unique products:    {df['produto'].nunique()}")
    logger.info(f"  Unique regionais:   {df['regional'].nunique()}")
    logger.info(f"  Categories:         {df['categoria'].nunique()}")

    if df['ano'].notna().any():
        logger.info(f"  Year range:         {int(df['ano'].min())} - {int(df['ano'].max())}")

    logger.info("\n  Regionais encontradas:")
    for reg in sorted(df['regional'].dropna().unique()):
        count = len(df[df['regional'] == reg])
        logger.info(f"    - {reg}: {count:,}")

    logger.info("=" * 60)


if __name__ == "__main__":
    process_all_files()
