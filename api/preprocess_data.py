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


def load_data() -> pd.DataFrame:
    """Load consolidated data."""
    logger.info("Loading data...")
    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')

    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')
    df['preco_medio'] = pd.to_numeric(df['preco_medio'], errors='coerce')

    df = df[df['preco_medio'].notna() & (df['preco_medio'] > 0)]
    df = df[df['ano'].notna()]

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
            'pm': round(float(row['preco_medio']), 2),
        })

    return {
        'records': records,
        'filters': {
            'anos': sorted([int(x) for x in df['ano'].dropna().unique()]),
            'categorias': sorted(df['categoria'].dropna().unique().tolist()),
            'produtos': sorted(df['produto'].dropna().unique().tolist())[:500],
        },
    }


def generate_filter_maps(df: pd.DataFrame) -> dict:
    """Generate filter hierarchy."""
    maps = {'category_products': {}}
    for cat in df['categoria'].unique():
        cat_df = df[df['categoria'] == cat]
        maps['category_products'][cat] = cat_df['produto'].value_counts().head(100).index.tolist()
    return maps


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
    save_json(generate_aggregated_data(df), 'aggregated.json')
    save_json(generate_detailed_data(df), 'detailed.json')
    save_json(generate_time_series(df), 'timeseries.json')
    save_json(generate_filter_maps(df), 'filters.json')

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
