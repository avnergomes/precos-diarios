#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Preprocessing for Dashboard API
Generates optimized JSON files for the React dashboard.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
JSON_DIR = DATA_DIR / "json"
INPUT_FILE = DATA_PROCESSED_DIR / "consolidated.csv"


def fix_encoding(text):
    """Fix common encoding issues in text."""
    if not isinstance(text, str):
        return text

    # Common mojibake fixes (Windows-1252 -> UTF-8 misinterpretation)
    fixes = {
        'Ã£': 'ã', 'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ãº': 'ú', 'Ã³': 'ó',
        'Ã§': 'ç', 'Ãµ': 'õ', 'Ã': 'à', 'Ã¢': 'â', 'Ãª': 'ê', 'Ã´': 'ô',
        '�': '', 'ã£': 'ã', 'ã©': 'é', 'ã­': 'í', 'ãº': 'ú',
    }

    for bad, good in fixes.items():
        text = text.replace(bad, good)

    return text


def load_data() -> pd.DataFrame:
    """Load consolidated data."""
    logger.info("Loading data...")

    # Try multiple encodings
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(INPUT_FILE, encoding=encoding)
            break
        except Exception:
            continue

    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')
    df['preco_medio'] = pd.to_numeric(df['preco_medio'], errors='coerce')

    df = df[df['preco_medio'].notna() & (df['preco_medio'] > 0)]
    df = df[df['ano'].notna()]

    # Fix encoding in product names
    df['produto'] = df['produto'].apply(fix_encoding)

    # Fix category inconsistencies - use most common category for each product
    product_main_category = df.groupby('produto')['categoria'].agg(
        lambda x: x.value_counts().index[0]
    )
    df['categoria'] = df['produto'].map(product_main_category)

    df['periodo'] = df.apply(
        lambda x: f"{int(x['ano'])}-{int(x['mes']):02d}" if pd.notna(x['mes']) else f"{int(x['ano'])}",
        axis=1
    )

    logger.info(f"Loaded {len(df)} records")
    return df


def generate_aggregated_data(df: pd.DataFrame) -> dict:
    """Generate pre-aggregated statistics."""
    agg = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_records': len(df),
            'year_min': int(df['ano'].min()),
            'year_max': int(df['ano'].max()),
        },
        'by_year': {},
        'by_category': {},
        'by_product': {},
    }

    for year, grp in df.groupby('ano'):
        agg['by_year'][int(year)] = {
            'media': round(float(grp['preco_medio'].mean()), 2),
            'registros': len(grp),
        }

    for cat, grp in df.groupby('categoria'):
        agg['by_category'][cat] = {
            'media': round(float(grp['preco_medio'].mean()), 2),
            'registros': len(grp),
        }

    prod_agg = df.groupby('produto').agg({'preco_medio': 'mean', 'categoria': 'first'}).round(2)
    for prod, row in prod_agg.head(100).iterrows():
        agg['by_product'][prod] = {
            'media': float(row['preco_medio']),
            'categoria': row['categoria'],
        }

    return agg


def generate_time_series(df: pd.DataFrame) -> dict:
    """Generate time series data."""
    series = {'by_period': {}, 'by_category': {}}

    for periodo, grp in df.groupby('periodo'):
        series['by_period'][periodo] = {
            'media': round(float(grp['preco_medio'].mean()), 2),
            'count': len(grp),
        }

    for cat in df['categoria'].unique():
        cat_df = df[df['categoria'] == cat]
        series['by_category'][cat] = {}
        for periodo, grp in cat_df.groupby('periodo'):
            series['by_category'][cat][periodo] = round(float(grp['preco_medio'].mean()), 2)

    return series


def generate_detailed_data(df: pd.DataFrame) -> dict:
    """Generate detailed records."""
    sample_df = df.sample(n=min(50000, len(df)), random_state=42) if len(df) > 50000 else df

    records = []
    for _, row in sample_df.iterrows():
        records.append({
            'd': row.get('data', ''),
            'a': int(row['ano']) if pd.notna(row['ano']) else None,
            'p': row.get('produto', ''),
            'c': row.get('categoria', ''),
            'u': row.get('unidade', ''),
            'pm': round(float(row['preco_medio']), 2),
        })

    # Build product-unit mapping for reference
    product_units = {}
    for prod in df['produto'].unique():
        unit = df[df['produto'] == prod]['unidade'].mode()
        if len(unit) > 0:
            product_units[prod] = unit.iloc[0]

    return {
        'records': records,
        'filters': {
            'anos': sorted([int(x) for x in df['ano'].dropna().unique()]),
            'categorias': sorted(df['categoria'].dropna().unique().tolist()),
            'produtos': sorted(df['produto'].dropna().unique().tolist())[:500],
        },
        'product_units': product_units,
    }


def generate_filter_maps(df: pd.DataFrame) -> dict:
    """Generate filter hierarchy."""
    maps = {'category_products': {}}
    for cat in df['categoria'].unique():
        cat_df = df[df['categoria'] == cat]
        maps['category_products'][cat] = cat_df['produto'].value_counts().head(100).index.tolist()
    return maps


def generate_daily_series(df: pd.DataFrame) -> dict:
    """Generate daily price series for top products (for volatility analysis)."""
    logger.info("Generating daily series...")
    daily = {}

    # Get top 20 products by record count
    top_products = df['produto'].value_counts().head(20).index.tolist()

    for produto in top_products:
        prod_df = df[df['produto'] == produto].copy()
        prod_df = prod_df[prod_df['data'].notna()].sort_values('data')

        if len(prod_df) > 0:
            daily[produto] = [
                {'d': str(row['data']), 'p': round(float(row['preco_medio']), 2)}
                for _, row in prod_df.iterrows()
            ]

    return {'products': daily, 'generated_at': datetime.now().isoformat()}


def generate_volatility(df: pd.DataFrame) -> dict:
    """Generate volatility metrics by product and period."""
    logger.info("Generating volatility metrics...")
    vol = {}

    # Filter to products with enough data
    product_counts = df.groupby('produto').size()
    valid_products = product_counts[product_counts >= 10].index.tolist()
    df_valid = df[df['produto'].isin(valid_products)]

    for (prod, periodo), grp in df_valid.groupby(['produto', 'periodo']):
        if len(grp) >= 3:  # Minimum 3 observations for volatility
            prices = grp['preco_medio'].values
            mean_price = float(np.mean(prices))
            std_price = float(np.std(prices))

            if mean_price > 0:
                vol.setdefault(prod, {})[periodo] = {
                    'std': round(std_price, 2),
                    'cv': round(std_price / mean_price * 100, 1),  # Coefficient of variation %
                    'range_pct': round((prices.max() - prices.min()) / mean_price * 100, 1),
                    'n': len(grp),
                }

    return {'by_product': vol, 'generated_at': datetime.now().isoformat()}


def generate_regional_spread(df: pd.DataFrame) -> dict:
    """Generate regional spread using min/max prices as proxy."""
    logger.info("Generating regional spread...")
    spread = {}

    # Check if min/max columns exist
    if 'preco_minimo' not in df.columns or 'preco_maximo' not in df.columns:
        logger.warning("preco_minimo/preco_maximo columns not found, skipping spread calculation")
        return {'by_product': {}, 'generated_at': datetime.now().isoformat()}

    # Filter rows with valid min/max
    df_valid = df[df['preco_minimo'].notna() & df['preco_maximo'].notna()].copy()

    for (prod, periodo), grp in df_valid.groupby(['produto', 'periodo']):
        if len(grp) >= 1:
            pmin = float(grp['preco_minimo'].mean())
            pmax = float(grp['preco_maximo'].mean())
            pmean = float(grp['preco_medio'].mean())

            if pmean > 0 and pmax >= pmin:
                spread.setdefault(prod, {})[periodo] = {
                    'spread_pct': round((pmax - pmin) / pmean * 100, 1),
                    'min': round(pmin, 2),
                    'max': round(pmax, 2),
                    'mean': round(pmean, 2),
                }

    return {'by_product': spread, 'generated_at': datetime.now().isoformat()}


def save_json(data: dict, filename: str):
    """Save JSON file."""
    filepath = JSON_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    logger.info(f"Saved {filename} ({filepath.stat().st_size / 1024:.1f} KB)")


def main():
    """Main preprocessing pipeline."""
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        logger.error(f"Input file not found: {INPUT_FILE}")
        return

    df = load_data()

    # Original JSON files
    save_json(generate_aggregated_data(df), 'aggregated.json')
    save_json(generate_detailed_data(df), 'detailed.json')
    save_json(generate_time_series(df), 'timeseries.json')
    save_json(generate_filter_maps(df), 'filters.json')

    # New JSON files for enhanced analytics
    save_json(generate_daily_series(df), 'daily_series.json')
    save_json(generate_volatility(df), 'volatility.json')
    save_json(generate_regional_spread(df), 'regional_spread.json')

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
