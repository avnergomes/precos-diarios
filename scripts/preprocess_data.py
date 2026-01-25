#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Preprocessing for Dashboard
Generates optimized JSON files for the React dashboard.
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DASHBOARD_DATA_DIR = BASE_DIR / "dashboard" / "public" / "data"
INPUT_FILE = DATA_PROCESSED_DIR / "consolidated.csv"


def load_data() -> pd.DataFrame:
    """Load consolidated data."""
    print("  Loading data...")
    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')

    # Clean data
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')
    df['dia'] = pd.to_numeric(df['dia'], errors='coerce')
    df['preco_medio'] = pd.to_numeric(df['preco_medio'], errors='coerce')
    df['preco_minimo'] = pd.to_numeric(df['preco_minimo'], errors='coerce')
    df['preco_maximo'] = pd.to_numeric(df['preco_maximo'], errors='coerce')

    # Filter valid records
    df = df[df['preco_medio'].notna() & (df['preco_medio'] > 0)]
    df = df[df['ano'].notna()]

    # Create period column (YYYY-MM)
    df['periodo'] = df.apply(
        lambda x: f"{int(x['ano'])}-{int(x['mes']):02d}" if pd.notna(x['mes']) else f"{int(x['ano'])}",
        axis=1
    )

    print(f"    Loaded {len(df)} records")
    return df


def generate_aggregated_data(df: pd.DataFrame) -> dict:
    """Generate pre-aggregated statistics for fast loading."""
    print("  Generating aggregated data...")

    agg = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_records': len(df),
            'year_min': int(df['ano'].min()),
            'year_max': int(df['ano'].max()),
            'unique_products': int(df['produto'].nunique()),
            'unique_categories': int(df['categoria'].nunique()),
        },
        'by_year': {},
        'by_period': {},
        'by_category': {},
        'by_product': {},
        'by_year_category': {},
        'top_products': {},
        'category_hierarchy': {},
    }

    # By Year
    year_agg = df.groupby('ano').agg({
        'preco_medio': ['mean', 'min', 'max', 'std', 'count'],
    }).round(2)
    year_agg.columns = ['media', 'minimo', 'maximo', 'desvio', 'registros']

    for year, row in year_agg.iterrows():
        agg['by_year'][int(year)] = {
            'media': float(row['media']) if pd.notna(row['media']) else 0,
            'minimo': float(row['minimo']) if pd.notna(row['minimo']) else 0,
            'maximo': float(row['maximo']) if pd.notna(row['maximo']) else 0,
            'desvio': float(row['desvio']) if pd.notna(row['desvio']) else 0,
            'registros': int(row['registros']),
        }

    # By Period (YYYY-MM)
    period_agg = df.groupby('periodo').agg({
        'preco_medio': ['mean', 'min', 'max', 'count'],
    }).round(2)
    period_agg.columns = ['media', 'minimo', 'maximo', 'registros']

    for period, row in period_agg.iterrows():
        agg['by_period'][period] = {
            'media': float(row['media']) if pd.notna(row['media']) else 0,
            'minimo': float(row['minimo']) if pd.notna(row['minimo']) else 0,
            'maximo': float(row['maximo']) if pd.notna(row['maximo']) else 0,
            'registros': int(row['registros']),
        }

    # By Category
    cat_agg = df.groupby('categoria').agg({
        'preco_medio': ['mean', 'min', 'max', 'count'],
        'produto': 'nunique',
    }).round(2)
    cat_agg.columns = ['media', 'minimo', 'maximo', 'registros', 'produtos']

    for cat, row in cat_agg.iterrows():
        agg['by_category'][cat] = {
            'media': float(row['media']) if pd.notna(row['media']) else 0,
            'minimo': float(row['minimo']) if pd.notna(row['minimo']) else 0,
            'maximo': float(row['maximo']) if pd.notna(row['maximo']) else 0,
            'registros': int(row['registros']),
            'produtos': int(row['produtos']),
        }

    # By Product (top 100)
    prod_agg = df.groupby('produto').agg({
        'preco_medio': ['mean', 'min', 'max', 'count'],
        'categoria': 'first',
        'unidade': lambda x: x.dropna().mode().iloc[0] if not x.dropna().empty else None,
    }).round(2)
    prod_agg.columns = ['media', 'minimo', 'maximo', 'registros', 'categoria', 'unidade']
    prod_agg = prod_agg.sort_values('registros', ascending=False).head(100)

    for prod, row in prod_agg.iterrows():
        agg['by_product'][prod] = {
            'media': float(row['media']) if pd.notna(row['media']) else 0,
            'minimo': float(row['minimo']) if pd.notna(row['minimo']) else 0,
            'maximo': float(row['maximo']) if pd.notna(row['maximo']) else 0,
            'registros': int(row['registros']),
            'categoria': row['categoria'],
            'unidade': row['unidade'] if pd.notna(row['unidade']) else None,
        }

    # By Year x Category
    year_cat_agg = df.groupby(['ano', 'categoria']).agg({
        'preco_medio': ['mean', 'count'],
    }).round(2)
    year_cat_agg.columns = ['media', 'registros']
    year_cat_agg = year_cat_agg.reset_index()

    for _, row in year_cat_agg.iterrows():
        key = f"{int(row['ano'])}_{row['categoria']}"
        agg['by_year_category'][key] = {
            'ano': int(row['ano']),
            'categoria': row['categoria'],
            'media': float(row['media']) if pd.notna(row['media']) else 0,
            'registros': int(row['registros']),
        }

    # Top Products per Year
    for year in df['ano'].unique():
        year_df = df[df['ano'] == year]
        top = year_df.groupby('produto').agg({
            'preco_medio': ['mean', 'count'],
        }).round(2)
        top.columns = ['media', 'registros']
        top = top.sort_values('registros', ascending=False).head(10)

        agg['top_products'][int(year)] = [
            {'produto': prod, 'media': float(row['media']), 'registros': int(row['registros'])}
            for prod, row in top.iterrows()
        ]

    # Category Hierarchy
    for cat in df['categoria'].unique():
        cat_df = df[df['categoria'] == cat]
        products = cat_df['produto'].value_counts().head(50).index.tolist()
        agg['category_hierarchy'][cat] = products

    return agg


def generate_detailed_data(df: pd.DataFrame) -> dict:
    """Generate detailed fact tables for dynamic filtering."""
    print("  Generating detailed data...")

    detailed = {
        'records': [],
        'filters': {
            'anos': sorted([int(x) for x in df['ano'].dropna().unique()]),
            'categorias': sorted(df['categoria'].dropna().unique().tolist()),
            'produtos': sorted(df['produto'].dropna().unique().tolist())[:500],
        },
    }

    # Sample for detailed records if too large
    if len(df) > 50000:
        sample_df = df.sample(n=50000, random_state=42)
    else:
        sample_df = df

    for _, row in sample_df.iterrows():
        record = {
            'd': row.get('data', ''),
            'a': int(row['ano']) if pd.notna(row['ano']) else None,
            'm': int(row['mes']) if pd.notna(row['mes']) else None,
            'p': row.get('produto', ''),
            'c': row.get('categoria', ''),
            'u': row.get('unidade', ''),
            'pm': round(float(row['preco_medio']), 2) if pd.notna(row['preco_medio']) else None,
            'pn': round(float(row['preco_minimo']), 2) if pd.notna(row['preco_minimo']) else None,
            'px': round(float(row['preco_maximo']), 2) if pd.notna(row['preco_maximo']) else None,
        }
        # Remove None values to reduce file size
        record = {k: v for k, v in record.items() if v is not None and v != ''}
        detailed['records'].append(record)

    return detailed


def generate_time_series(df: pd.DataFrame) -> dict:
    """Generate time series data for charts."""
    print("  Generating time series...")

    series = {
        'by_period': {},
        'by_category': {},
        'by_product': {},
    }

    # Overall by period
    for periodo, grp in df.groupby('periodo'):
        series['by_period'][periodo] = {
            'media': round(float(grp['preco_medio'].mean()), 2),
            'min': round(float(grp['preco_medio'].min()), 2),
            'max': round(float(grp['preco_medio'].max()), 2),
            'count': len(grp),
        }

    # By category over time
    for cat in df['categoria'].unique():
        cat_df = df[df['categoria'] == cat]
        series['by_category'][cat] = {}

        for periodo, grp in cat_df.groupby('periodo'):
            series['by_category'][cat][periodo] = {
                'media': round(float(grp['preco_medio'].mean()), 2),
                'count': len(grp),
            }

    # Top products over time
    top_products = df['produto'].value_counts().head(20).index.tolist()
    for prod in top_products:
        prod_df = df[df['produto'] == prod]
        series['by_product'][prod] = {}

        for periodo, grp in prod_df.groupby('periodo'):
            series['by_product'][prod][periodo] = {
                'media': round(float(grp['preco_medio'].mean()), 2),
                'count': len(grp),
            }

    return series


def generate_filter_maps(df: pd.DataFrame) -> dict:
    """Generate filter hierarchy maps."""
    print("  Generating filter maps...")

    maps = {
        'category_products': {},
    }

    # Category -> Products
    for cat in df['categoria'].unique():
        cat_df = df[df['categoria'] == cat]
        products = cat_df['produto'].value_counts().head(100).index.tolist()
        maps['category_products'][cat] = products

    return maps


def save_json(data: dict, filename: str):
    """Save data as optimized JSON."""
    filepath = DASHBOARD_DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = filepath.stat().st_size / 1024
    print(f"    Saved {filename} ({size_kb:.1f} KB)")


def main():
    """Main preprocessing pipeline."""
    print("=" * 60)
    print("SIMA Daily Quotations - Data Preprocessing")
    print("=" * 60)

    # Create output directory
    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check input file
    if not INPUT_FILE.exists():
        print(f"\n[ERROR] Input file not found: {INPUT_FILE}")
        print("        Please run etl_process.py first.")
        return

    # Load data
    print("\n[1/5] Loading consolidated data...")
    df = load_data()

    # Generate aggregated data
    print("\n[2/5] Generating aggregated data...")
    aggregated = generate_aggregated_data(df)
    save_json(aggregated, 'aggregated.json')

    # Generate detailed data
    print("\n[3/5] Generating detailed data...")
    detailed = generate_detailed_data(df)
    save_json(detailed, 'detailed.json')

    # Generate time series
    print("\n[4/5] Generating time series...")
    timeseries = generate_time_series(df)
    save_json(timeseries, 'timeseries.json')

    # Generate filter maps
    print("\n[5/5] Generating filter maps...")
    filter_maps = generate_filter_maps(df)
    save_json(filter_maps, 'filters.json')

    # Summary
    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"  Output directory: {DASHBOARD_DATA_DIR}")
    print(f"  Files generated:")
    for f in DASHBOARD_DATA_DIR.glob('*.json'):
        size_kb = f.stat().st_size / 1024
        print(f"    - {f.name}: {size_kb:.1f} KB")
    print("=" * 60)


if __name__ == "__main__":
    main()
