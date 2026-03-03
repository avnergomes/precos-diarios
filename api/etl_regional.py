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
from collections import OrderedDict

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
# IMPORTANT: NO partial/substring matching - all lookups are exact after normalization
REGIONAL_ALIASES: Dict[str, str] = {
    # === CANONICAL NAMES (lowercase, no accents) ===
    'apucarana': 'Apucarana',
    'campo mourao': 'Campo Mourão',
    'cascavel': 'Cascavel',
    'cianorte': 'Cianorte',
    'cornelio procopio': 'Cornélio Procópio',
    'curitiba': 'Curitiba',
    'dois vizinhos': 'Dois Vizinhos',
    'francisco beltrao': 'Francisco Beltrão',
    'guarapuava': 'Guarapuava',
    'irati': 'Irati',
    'ivaipora': 'Ivaiporã',
    'jacarezinho': 'Jacarezinho',
    'laranjeiras do sul': 'Laranjeiras do Sul',
    'londrina': 'Londrina',
    'maringa': 'Maringá',
    'paranagua': 'Paranaguá',
    'paranavai': 'Paranavaí',
    'pato branco': 'Pato Branco',
    'pitanga': 'Pitanga',
    'ponta grossa': 'Ponta Grossa',
    'santo antonio da platina': 'Santo Antônio da Platina',
    'toledo': 'Toledo',
    'umuarama': 'Umuarama',
    'uniao da vitoria': 'União da Vitória',

    # === ERA 3 COMMA-ABBREVIATED (exact values from 2014-Jun/2019 Excel files) ===
    'c, mourao': 'Campo Mourão',
    'c,mourao': 'Campo Mourão',
    'c mourao': 'Campo Mourão',
    'c,procopio': 'Cornélio Procópio',
    'c, procopio': 'Cornélio Procópio',
    'c procopio': 'Cornélio Procópio',
    'f,beltrao': 'Francisco Beltrão',
    'f, beltrao': 'Francisco Beltrão',
    'f beltrao': 'Francisco Beltrão',
    'p, grossa': 'Ponta Grossa',
    'p,grossa': 'Ponta Grossa',
    'p grossa': 'Ponta Grossa',
    'p, branco': 'Pato Branco',
    'p,branco': 'Pato Branco',
    'p branco': 'Pato Branco',
    'u, vitoria': 'União da Vitória',
    'u,vitoria': 'União da Vitória',
    'u vitoria': 'União da Vitória',
    'laranj, sul': 'Laranjeiras do Sul',
    'laranj,sul': 'Laranjeiras do Sul',
    'laranj sul': 'Laranjeiras do Sul',

    # === ERA 1/2 DOT-ABBREVIATED FRAGMENTS (single row only, NOT split) ===
    'corn.': 'Cornélio Procópio',
    'corn': 'Cornélio Procópio',
    'fco.': 'Francisco Beltrão',
    'fco': 'Francisco Beltrão',
    'fco. beltrao': 'Francisco Beltrão',

    # === ERA 1/2 COMBINED NAMES (after extract_regional_headers joins rows) ===
    'campomourao': 'Campo Mourão',
    'cornelioprocopio': 'Cornélio Procópio',
    'corn.proc.': 'Cornélio Procópio',
    'cornprocopio': 'Cornélio Procópio',
    'cornproc': 'Cornélio Procópio',
    'corn.procopio': 'Cornélio Procópio',
    'corn. proc.': 'Cornélio Procópio',
    'fco.beltrao': 'Francisco Beltrão',
    'fcobeltrao': 'Francisco Beltrão',
    'patobranco': 'Pato Branco',
    'pontagrossa': 'Ponta Grossa',
    'uniaovitoria': 'União da Vitória',
    'uniao vitoria': 'União da Vitória',

    # === COMMON DOT ABBREVIATIONS ===
    'p. grossa': 'Ponta Grossa',
    'p.grossa': 'Ponta Grossa',
    'pta grossa': 'Ponta Grossa',
    'pta. grossa': 'Ponta Grossa',
    'c. mourao': 'Campo Mourão',
    'c.mourao': 'Campo Mourão',
    'p. branco': 'Pato Branco',
    'p.branco': 'Pato Branco',
    'c. procopio': 'Cornélio Procópio',
    'c.procopio': 'Cornélio Procópio',
    'f. beltrao': 'Francisco Beltrão',
    'f.beltrao': 'Francisco Beltrão',
    'u. vitoria': 'União da Vitória',
    'u.vitoria': 'União da Vitória',
    'l. sul': 'Laranjeiras do Sul',
    'l.sul': 'Laranjeiras do Sul',
    'd. vizinhos': 'Dois Vizinhos',
    'd.vizinhos': 'Dois Vizinhos',
    'sa platina': 'Santo Antônio da Platina',
    's.a. platina': 'Santo Antônio da Platina',
    'sto antonio da platina': 'Santo Antônio da Platina',
    's.a.platina': 'Santo Antônio da Platina',

    # === PARTIAL SINGLE-WORD that are SAFE (unique enough to match) ===
    # Only words that unambiguously identify ONE regional
    # Note: Do NOT add dangerous fragments like 'zinho', 'do', 'ga', 'proc.'
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
    """Normalize regional name to standard format.

    IMPORTANT: This function does NOT do partial/substring matching.
    All matching is exact against REGIONAL_ALIASES after normalization.
    For split headers (ERA 0/1/2), the COMBINATION must happen in
    extract_regional_headers() before calling this function.
    """
    if not name or pd.isna(name):
        return None

    # Clean and lowercase
    name_clean = str(name).strip().lower()
    name_clean = re.sub(r'\s+', ' ', name_clean)
    # Remove accents
    name_clean = unicodedata.normalize('NFKD', name_clean)
    name_clean = ''.join(c for c in name_clean if not unicodedata.combining(c))

    # STRATEGY 1: Exact match as-is
    if name_clean in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_clean]

    # STRATEGY 2: Replace comma with dot (ERA 3 "P, GROSSA" → "p. grossa")
    name_with_dot = name_clean.replace(',', '.')
    if name_with_dot in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_with_dot]

    # STRATEGY 3: Remove all punctuation (comma, dot, hyphen) and try
    name_no_punct = re.sub(r'[,.\-]', '', name_clean).strip()
    name_no_punct = re.sub(r'\s+', ' ', name_no_punct)
    if name_no_punct in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_no_punct]

    # STRATEGY 4: Remove all punctuation AND spaces (for concatenated names)
    name_no_spaces = re.sub(r'[,.\-\s]', '', name_clean)
    if name_no_spaces in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_no_spaces]

    # STRATEGY 5: Check against REGIONAIS_PADRAO (canonical list) — exact match only
    for standard in REGIONAIS_PADRAO:
        standard_norm = unicodedata.normalize('NFKD', standard.lower())
        standard_norm = ''.join(c for c in standard_norm if not unicodedata.combining(c))
        if name_no_punct == standard_norm or name_no_spaces == standard_norm.replace(' ', ''):
            return standard

    # NO partial match — it causes BUG 4 (ZINHO→Dois Vizinhos) and BUG 5 (DO→Dois Vizinhos)
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
    """Extract regional names from Excel header rows.

    Handles 5 eras of SIMA Excel files:
    - ERA 0 (2001-2002 Resumo): 29 cols, headers rows 5+6 (split, hyphenated)
    - ERA 1 (2001-2004 Sima): 29 cols, headers rows 5+6 (split, hyphenated)
    - ERA 2 (2005-2013): 23 cols, headers rows 3+4 (split, hyphenated)
    - ERA 3 (2014-Jun/2019): 24 cols, headers row 3 (comma-abbreviated)
    - ERA 4 (Jul/2019+): 24 cols, headers row 3 (full names)

    STRATEGY:
    1. Try single-row detection (ERA 3/4) — scan rows 0-9 for known regionais
    2. If <15 found, try combining consecutive rows (ERA 0/1/2 split headers)
    3. If still <10 found, use ERA-based fallback by column count

    CRITICAL RULES:
    - Columns >= 20 are NEVER regionais (they are Média/Var statistics)
    - Deduplicate: if 2 columns map to same regional, something is wrong
    """
    regional_cols: Dict[int, str] = {}
    num_cols = len(df.columns)

    # Maximum column index for regional data (exclusive)
    # ERA 0/1/2: 18 regionais in cols 2-19, so max_col = 20
    # ERA 3/4: 20 regionais in cols 2-21, so max_col = 22
    # FIX v4: União da Vitória is in col 21, so must include it
    max_regional_col = 22  # Include col 21 (União da Vitória)

    # Non-regional strings to skip
    SKIP_STRINGS = {
        'sima', 'media', 'média', 'no estado', 'no dia', 'dia ant.',
        'dia ant', 'diaria', 'diária', 'cotacao do dia', 'cotação do dia',
        'cotacao do dia :', 'cotação do dia :', 'em r$/unidade',
        'var, (%)', 'var (%)', 'var(%)', 'variacao', 'variação',
        'produtos', 'produtos no parana', 'produtos no paraná',
        'min', 'max', 'med', 'produto', 'unidade', 'und',
    }

    # STRATEGY 1: Try single-row detection (scan rows 0-9)
    best_single_row = {}
    for row_idx in range(min(10, len(df))):
        row_matches = {}
        row = df.iloc[row_idx]
        for col_idx in range(2, min(num_cols, max_regional_col)):
            cell = row.iloc[col_idx]
            if pd.notna(cell):
                cell_str = str(cell).strip()
                if len(cell_str) < 2:
                    continue
                # Skip pure numbers
                try:
                    float(cell_str.replace(',', '.').replace(' ', ''))
                    continue
                except ValueError:
                    pass
                # Skip known non-regional strings
                cell_lower = cell_str.strip().lower()
                cell_norm = unicodedata.normalize('NFKD', cell_lower)
                cell_norm = ''.join(c for c in cell_norm if not unicodedata.combining(c))
                if cell_norm in SKIP_STRINGS:
                    continue
                regional = normalize_regional(cell_str)
                if regional and col_idx not in row_matches:
                    row_matches[col_idx] = regional

        # Keep the row with the most matches
        if len(row_matches) > len(best_single_row):
            best_single_row = row_matches

    regional_cols = best_single_row.copy()

    # STRATEGY 2: If <15 found, try combining consecutive rows (ERA 0/1/2 split headers)
    if len(regional_cols) < 15:
        best_combined = {}
        for row_idx in range(min(10, len(df) - 1)):
            row_top = df.iloc[row_idx]
            row_bot = df.iloc[row_idx + 1]
            combined_matches = {}

            for col_idx in range(2, min(num_cols, max_regional_col)):
                top_val = row_top.iloc[col_idx]
                bot_val = row_bot.iloc[col_idx]

                top = str(top_val).strip() if pd.notna(top_val) else ''
                bot = str(bot_val).strip() if pd.notna(bot_val) else ''

                # Try combination in multiple ways
                found = None

                if top and bot:
                    # Way 1: Remove trailing hyphen and concatenate directly
                    top_clean = top.rstrip('-').strip()
                    combined = f"{top_clean}{bot}"
                    found = normalize_regional(combined)

                    if not found:
                        # Way 2: Join with space
                        combined_space = f"{top_clean} {bot}"
                        found = normalize_regional(combined_space)

                    if not found:
                        # Way 3: Join with dot (CORN. + PROC. = CORN.PROC.)
                        combined_dot = f"{top}.{bot}"
                        found = normalize_regional(combined_dot)

                    if not found:
                        # Way 4: Clean both, join with space
                        top_no_punct = top.rstrip('.-').strip()
                        bot_no_punct = bot.rstrip('.-').strip()
                        combined_clean = f"{top_no_punct} {bot_no_punct}"
                        found = normalize_regional(combined_clean)

                elif top and not bot:
                    # Single-row entry (e.g., "IRATI" with empty bottom)
                    found = normalize_regional(top)

                if found and col_idx not in combined_matches:
                    combined_matches[col_idx] = found

            # Keep the row-pair with the most matches
            if len(combined_matches) > len(best_combined):
                best_combined = combined_matches

        # Use combined results if they found significantly more regionais
        if len(best_combined) > len(regional_cols):
            regional_cols = best_combined

    # STRATEGY 3: ERA-based fallback if still < 10 regionais
    if len(regional_cols) < 10:
        logger.warning(
            f"Only {len(regional_cols)} regionais detected from headers. "
            f"Using ERA-based fallback (num_cols={num_cols})."
        )
        # Detect era by column count
        if num_cols >= 28:
            # ERA 0/1: 29 columns, 18 regionais in cols 2-19
            era01_order = [
                'Apucarana', 'Campo Mourão', 'Cascavel', 'Cornélio Procópio',
                'Curitiba', 'Francisco Beltrão', 'Guarapuava', 'Irati',
                'Ivaiporã', 'Jacarezinho', 'Londrina', 'Maringá',
                'Paranavaí', 'Pato Branco', 'Ponta Grossa', 'Toledo',
                'Umuarama', 'União da Vitória'
            ]
            regional_cols = {}
            for i, reg in enumerate(era01_order):
                regional_cols[i + 2] = reg  # cols 2-19
        elif num_cols <= 23:
            # ERA 2: 23 columns, 18 regionais in cols 2-19
            era2_order = [
                'Apucarana', 'Campo Mourão', 'Cascavel', 'Cornélio Procópio',
                'Curitiba', 'Francisco Beltrão', 'Guarapuava', 'Irati',
                'Ivaiporã', 'Jacarezinho', 'Londrina', 'Maringá',
                'Paranavaí', 'Pato Branco', 'Ponta Grossa', 'Toledo',
                'Umuarama', 'União da Vitória'
            ]
            regional_cols = {}
            for i, reg in enumerate(era2_order):
                if i + 2 < num_cols - 3:  # Leave room for stats columns
                    regional_cols[i + 2] = reg
        else:
            # ERA 3/4: 24 columns, 19 regionais in cols 2-20
            era34_order = [
                'Apucarana', 'Campo Mourão', 'Cascavel', 'Cornélio Procópio',
                'Curitiba', 'Francisco Beltrão', 'Guarapuava', 'Irati',
                'Ivaiporã', 'Jacarezinho', 'Laranjeiras do Sul', 'Londrina',
                'Maringá', 'Paranavaí', 'Pato Branco', 'Ponta Grossa',
                'Toledo', 'Umuarama', 'União da Vitória'
            ]
            regional_cols = {}
            for i, reg in enumerate(era34_order):
                regional_cols[i + 2] = reg

    # SANITY CHECK 1: Remove columns >= max_regional_col that snuck in
    regional_cols = {col: reg for col, reg in regional_cols.items() if col < max_regional_col}

    # SANITY CHECK 2: Deduplicate — if 2 columns map to the same regional, keep leftmost
    seen_names: Dict[str, int] = {}
    deduped: Dict[int, str] = {}
    for col in sorted(regional_cols.keys()):
        name = regional_cols[col]
        if name not in seen_names:
            seen_names[name] = col
            deduped[col] = name
        else:
            logger.warning(
                f"Duplicate regional '{name}' in cols {seen_names[name]} and {col}. "
                f"Keeping col {seen_names[name]}, dropping col {col}."
            )
    regional_cols = deduped

    logger.debug(f"Detected {len(regional_cols)} regionais: { {c: r for c, r in sorted(regional_cols.items())} }")
    return regional_cols


def extract_date_from_filename(filename: str, sheet_name: str = '') -> Optional[datetime]:
    """Extract date from filename patterns used in SIMA archives.

    Supported patterns:
    - "Abril 2017", "Janeiro2019" — month name + 4-digit year
    - "Abril2003" — month name directly concatenated with year
    - "Resumo Sima_MMYY", "Resumo SIMA_0705" — underscore + MMYY
    - "Resumo_0302" — underscore + MMYY
    - "ResumoSIMA_Ago01" — abbreviated month + 2-digit year
    - "Sima Janeiro 2009" — "Sima" + month name + year
    """
    month_names = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    }

    fn_lower = filename.lower().strip()
    # Remove accents for matching
    fn_norm = unicodedata.normalize('NFKD', fn_lower)
    fn_norm = ''.join(c for c in fn_norm if not unicodedata.combining(c))

    # Determine day from sheet_name if it's a simple number
    day = None
    sheet_stripped = sheet_name.strip()
    if re.match(r'^\d{1,2}$', sheet_stripped):
        d = int(sheet_stripped)
        if 1 <= d <= 31:
            day = d
    elif re.match(r'^\d{4}$', sheet_stripped):
        # DDMM format — day is first 2 digits
        d = int(sheet_stripped[:2])
        if 1 <= d <= 31:
            day = d

    # Pattern 1: Month name + 4-digit year (e.g., "Abril 2017", "Janeiro2019", "Janeiro_2012", "Sima Janeiro 2009")
    for name, num in sorted(month_names.items(), key=lambda x: -len(x[0])):
        # Normalize month name
        name_norm = unicodedata.normalize('NFKD', name)
        name_norm = ''.join(c for c in name_norm if not unicodedata.combining(c))

        for variant in set([name, name_norm]):
            # FIX v4: Allow underscore between month and year (e.g., "Janeiro_2012")
            match = re.search(rf'{variant}[_\s]*((?:19|20)\d{{2}})', fn_norm)
            if match:
                year = int(match.group(1))
                d = day if day else 1
                try:
                    return datetime(year, num, d)
                except ValueError:
                    return datetime(year, num, 1)

    # Pattern 2: "Resumo Sima_MMYY" or "Resumo_MMYY" (e.g., "_0705" = Jul 2005, "_0302" = Mar 2002)
    match = re.search(r'[_\s](\d{2})\s?(\d{2})(?:\s|$|\.)', fn_lower)
    if match:
        mm, yy = int(match.group(1)), int(match.group(2))
        if 1 <= mm <= 12 and 0 <= yy <= 99:
            year = 2000 + yy if yy < 50 else 1900 + yy
            d = day if day else 1
            try:
                return datetime(year, mm, d)
            except ValueError:
                return datetime(year, mm, 1)

    # Pattern 3: "ResumoSIMA_Ago01" (abbreviated month + 2-digit year at end)
    for name, num in sorted(month_names.items(), key=lambda x: -len(x[0])):
        name_norm = unicodedata.normalize('NFKD', name)
        name_norm = ''.join(c for c in name_norm if not unicodedata.combining(c))

        for variant in set([name, name_norm]):
            match = re.search(rf'{variant}\s*(\d{{2}})(?:\s|$|\.)', fn_norm)
            if match:
                yy = int(match.group(1))
                year = 2000 + yy if yy < 50 else 1900 + yy
                d = day if day else 1
                try:
                    return datetime(year, num, d)
                except ValueError:
                    return datetime(year, num, 1)

    return None


def parse_date_from_sheet(sheet_name: str, filename: str) -> Optional[datetime]:
    """Parse date from sheet name.

    Supported formats:
    - DD-MM-YYYY (e.g., '01-03-2019') — ERA 4 Mar-Jun 2019
    - DD-MM-YY (e.g., '01-08-19') — ERA 4 Jul/2019+
    - DD (e.g., '02', '15') — ERA 0/2/3/4 (day only, month/year from filename)
    - DDMM (e.g., '0104' = Apr 1st) — ERA 1 (day + month, year from filename)
    """
    sheet_stripped = sheet_name.strip()

    # Pattern 1: DD-MM-YYYY or DD_MM_YYYY (ERA 4 Mar-Jun 2019)
    match = re.match(r'^(\d{2})[-_](\d{2})[-_](\d{4})$', sheet_stripped)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return datetime(year, month, day)
        except ValueError:
            pass

    # Pattern 2: DD-MM-YY or DD_MM_YY (ERA 4 Jul/2019+)
    match = re.match(r'^(\d{2})[-_](\d{2})[-_](\d{2})$', sheet_stripped)
    if match:
        day, month, yy = int(match.group(1)), int(match.group(2)), int(match.group(3))
        year = 2000 + yy if yy < 50 else 1900 + yy
        try:
            return datetime(year, month, day)
        except ValueError:
            pass

    # Pattern 3: DD (day only) — need month/year from filename
    if re.match(r'^\d{1,2}$', sheet_stripped):
        day = int(sheet_stripped)
        if 1 <= day <= 31:
            date = extract_date_from_filename(filename, sheet_stripped)
            if date:
                try:
                    return datetime(date.year, date.month, day)
                except ValueError:
                    return date

    # Pattern 4: DDMM (ERA 1, e.g., '0104' = Apr 1st)
    if re.match(r'^\d{4}$', sheet_stripped):
        dd = int(sheet_stripped[:2])
        mm = int(sheet_stripped[2:])
        if 1 <= dd <= 31 and 1 <= mm <= 12:
            # Get year from filename
            year_match = re.search(r'(19|20)\d{2}', filename)
            if year_match:
                year = int(year_match.group())
                try:
                    return datetime(year, mm, dd)
                except ValueError:
                    pass
            else:
                # Try extract_date_from_filename for year
                date = extract_date_from_filename(filename, sheet_stripped)
                if date:
                    try:
                        return datetime(date.year, mm, dd)
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
    """Normalize product name to canonical format."""
    if not name or pd.isna(name):
        return None

    name = str(name).strip()

    # Step 1: Clean trailing punctuation artifacts from Excel parsing
    name = re.sub(r'\s*[,\.;:]+\s*$', '', name)
    name = name.strip()
    if not name:
        return None

    # Step 2: Normalize whitespace
    name = re.sub(r'\s+', ' ', name)

    # Step 3: Try direct product_map (regex-based)
    # Using OrderedDict to ensure patterns are tested in order
    # Bare names MUST come BEFORE more specific patterns
    product_map = OrderedDict([
        # === BARE NAMES (must come BEFORE more specific patterns) ===
        (r'(?i)^boi\s*$', 'Boi em pé'),
        (r'(?i)^vaca\s*$', 'Vaca em pé'),
        (r'(?i)^caf[eé]\s*$', 'Café em coco'),
        (r'(?i)^frango\s*$', 'Frango de corte'),
        (r'(?i)^soja\s*$', 'Soja industrial tipo 1'),
        (r'(?i)^trigo\s*$', 'Trigo pão'),
        (r'(?i)^milho\s*$', 'Milho amarelo tipo 1'),
        (r'(?i)^milho\s*comum\s*$', 'Milho amarelo tipo 1'),
        (r'(?i)^erva[\s\-]*mate\s*$', 'Erva-mate folha em barranco'),
        (r'(?i)^feij[aã]o\s*de\s*cor\s*$', 'Feijão de cor tipo 1'),
        (r'(?i)^arroz\s*em\s*casca\s*$', 'Arroz em casca tipo 1'),

        # === CONCATENATED NAMES (no spaces) ===
        (r'(?i)^milhocomum$', 'Milho amarelo tipo 1'),
        (r'(?i)^feij[aã]odecor$', 'Feijão de cor tipo 1'),
        (r'(?i)^arrozemcasca$', 'Arroz em casca tipo 1'),

        # === TYPOS AND VARIANTS (FIX v4) ===
        (r'(?i)caf[eé]\s*beneficado', 'Café beneficiado'),  # typo Beneficado → Beneficiado
        (r'(?i)feij[aã]o\s*carioca\s*tipo\s*1\s*[,.]?\s*(?:sc|Sc)\s*\d+', 'Feijão carioca tipo 1'),  # unidade grudada
        (r'(?i)feij[aã]o\s*carioca\s*tipo\s*1', 'Feijão carioca tipo 1'),  # normalizar casing
        (r'(?i)^feij[aã]o\s*carioca\s*$', 'Feijão carioca tipo 1'),  # nome incompleto
        (r'(?i)arroz\s*agulhinha\s*em\s*casca.*', 'Arroz em casca tipo 1'),  # normalizar variação agulhinha

        # === FULL CANONICAL PATTERNS ===
        (r'(?i)soja\s*industrial', 'Soja industrial tipo 1'),
        (r'(?i)boi\s*em\s*p[eé]', 'Boi em pé'),
        (r'(?i)vaca\s*em\s*p[eé]', 'Vaca em pé'),
        (r'(?i)caf[eé]\s*em\s*coco', 'Café em coco'),
        (r'(?i)caf[eé]\s*beneficiado', 'Café beneficiado'),
        (r'(?i)frango\s*de\s*corte', 'Frango de corte'),
        (r'(?i)frango\s*vivo', 'Frango vivo'),
        (r'(?i)trigo\s*p[aã]o', 'Trigo pão'),
        (r'(?i)milho\s*amarelo', 'Milho amarelo tipo 1'),
        (r'(?i)erva[\s\-]*mate.*folha', 'Erva-mate folha em barranco'),
        (r'(?i)erva[\s\-]*mate.*cancheada', 'Erva-mate cancheada'),
        (r'(?i)feij[aã]o\s*de\s*cor', 'Feijão de cor tipo 1'),
        (r'(?i)feij[aã]o\s*preto', 'Feijão preto tipo 1'),
        (r'(?i)arroz\s*em\s*casca\s*irrigado', 'Arroz em casca irrigado'),
        (r'(?i)arroz\s*em\s*casca\s*sequeiro', 'Arroz em casca sequeiro'),
        (r'(?i)arroz\s*em\s*casca', 'Arroz em casca tipo 1'),
        (r'(?i)su[ií]no\s*vivo', 'Suíno vivo'),
        (r'(?i)su[ií]no', 'Suíno vivo'),
        (r'(?i)mandioca\s*ind', 'Mandioca industrial'),
        (r'(?i)mandioca\s*mesa', 'Mandioca de mesa'),
        (r'(?i)mandioca', 'Mandioca industrial'),
        (r'(?i)algod[aã]o', 'Algodão em caroço'),
        (r'(?i)leite\s*(?:cru|in\s*natura)', 'Leite cru'),
        (r'(?i)leite', 'Leite cru'),
        (r'(?i)casulo\s*(?:de\s*)?bicho[\s\-]*da[\s\-]*seda', 'Casulo de bicho-da-seda'),
        (r'(?i)casulo', 'Casulo de bicho-da-seda'),
        (r'(?i)ovo.*branco', 'Ovo branco'),
        (r'(?i)ovo.*vermelho', 'Ovo vermelho'),
        (r'(?i)^ovo\s*$', 'Ovo branco'),
    ])

    for pattern, canonical in product_map.items():
        if re.search(pattern, name):
            return canonical

    # Step 4: Return original name if no mapping found (preserve unknown products)
    # Basic cleanup for unmatched products
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

    # Find data start row - look for first MIN indicator in col 1
    data_start = None
    for idx in range(min(15, len(df))):
        if len(df.columns) > 1:
            cell1 = str(df.iloc[idx, 1]).strip().upper() if pd.notna(df.iloc[idx, 1]) else ''
            if cell1 == 'MIN':
                data_start = idx
                break

    if data_start is None:
        # Fallback: look for PRODUTO in col 0
        for idx in range(min(10, len(df))):
            cell0 = str(df.iloc[idx, 0]).upper() if pd.notna(df.iloc[idx, 0]) else ''
            if 'PRODUTO' in cell0:
                data_start = idx + 2
                break

    if data_start is None:
        data_start = 5  # Last resort default

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


def process_excel_file(filepath: Path) -> List[dict]:
    """Process a single Excel file with multiple sheets."""
    all_records = []

    # FIX v4: Ensure filepath is a Path object (accept both str and Path)
    if isinstance(filepath, str):
        filepath = Path(filepath)

    try:
        engine = 'xlrd' if filepath.suffix == '.xls' else 'openpyxl'
        xl = pd.ExcelFile(filepath, engine=engine)

        for sheet_name in xl.sheet_names:
            # CASCADE 1: Try to parse date from sheet name
            date = parse_date_from_sheet(sheet_name, filepath.stem)

            # CASCADE 2: Try to extract date from filename
            if not date:
                date = extract_date_from_filename(filepath.stem, sheet_name)

            # CASCADE 3: Try to extract date from within the Excel header cells
            if not date:
                try:
                    temp_df = pd.read_excel(xl, sheet_name=sheet_name, header=None, nrows=5)
                    # Check known header positions: r0c22 (ERA 3/4), r2c20 (ERA 0/1)
                    for row_check, col_check in [(0, 22), (2, 20), (0, 20), (1, 20), (1, 22)]:
                        if row_check < len(temp_df) and col_check < len(temp_df.columns):
                            val = temp_df.iloc[row_check, col_check]
                            if pd.notna(val):
                                if isinstance(val, datetime):
                                    date = val
                                    break
                                val_str = str(val).strip()
                                # Try DD/MM/YYYY (barras)
                                m = re.match(r'(\d{2})/(\d{2})/(\d{4})', val_str)
                                if m:
                                    try:
                                        date = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                                        break
                                    except ValueError:
                                        pass
                                # Try DD.MM.YYYY (PONTOS — ERA 0!)
                                m = re.match(r'(\d{2})\.(\d{2})\.(\d{4})', val_str)
                                if m:
                                    try:
                                        date = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                                        break
                                    except ValueError:
                                        pass
                                # Try DD-MM-YYYY (hífens)
                                m = re.match(r'(\d{2})-(\d{2})-(\d{4})', val_str)
                                if m:
                                    try:
                                        date = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                                        break
                                    except ValueError:
                                        pass
                except Exception:
                    pass

            # CASCADE 4: Last resort — extract just the year from filename
            if not date:
                year_match = re.search(r'(19|20)\d{2}', filepath.stem)
                if year_match:
                    year = int(year_match.group())
                    # Try to get month from sheet_name if it's DDMM
                    sheet_stripped = sheet_name.strip()
                    if re.match(r'^\d{4}$', sheet_stripped):
                        mm = int(sheet_stripped[2:])
                        dd = int(sheet_stripped[:2])
                        if 1 <= mm <= 12 and 1 <= dd <= 31:
                            try:
                                date = datetime(year, mm, dd)
                            except ValueError:
                                date = datetime(year, 1, 1)
                    if not date:
                        date = datetime(year, 1, 1)

            if not date:
                logger.warning(f"Could not parse date for sheet '{sheet_name}' in '{filepath.name}'")

            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                records = process_sheet_regional(df, date, filepath.name)
                all_records.extend(records)
            except Exception as e:
                logger.error(f"Error processing sheet '{sheet_name}' in '{filepath.name}': {e}")
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
