#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Preprocessing for Dashboard API
Generates optimized JSON files for the React dashboard.
Supports both aggregated and regional granularity data.
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
INPUT_FILE_REGIONAL = DATA_PROCESSED_DIR / "consolidated_regional.csv"

# Lista de regionais padrão do IDR-Paraná
REGIONAIS_PADRAO = [
    'Apucarana', 'Campo Mourão', 'Cascavel', 'Cianorte', 'Cornélio Procópio',
    'Curitiba', 'Dois Vizinhos', 'Francisco Beltrão', 'Guarapuava', 'Irati',
    'Ivaiporã', 'Laranjeiras do Sul', 'Londrina', 'Maringá', 'Paranaguá',
    'Paranavaí', 'Pato Branco', 'Pitanga', 'Ponta Grossa',
    'Santo Antônio da Platina', 'Toledo', 'Umuarama', 'União da Vitória'
]


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


def load_data(regional: bool = False) -> pd.DataFrame:
    """Load consolidated data.

    Args:
        regional: If True, load regional data; if False, load aggregated data
    """
    input_file = INPUT_FILE_REGIONAL if regional else INPUT_FILE
    logger.info(f"Loading {'regional' if regional else 'aggregated'} data from {input_file}...")

    if not input_file.exists():
        logger.warning(f"File not found: {input_file}")
        if regional:
            logger.info("Falling back to aggregated data")
            return load_data(regional=False)
        return pd.DataFrame()

    # Try multiple encodings
    df = None
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(input_file, encoding=encoding)
            break
        except Exception:
            continue

    if df is None or df.empty:
        logger.error(f"Failed to load data from {input_file}")
        return pd.DataFrame()

    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')

    # Handle different column names for price
    price_col = 'preco' if 'preco' in df.columns else 'preco_medio'
    df[price_col] = pd.to_numeric(df[price_col], errors='coerce')

    df = df[df[price_col].notna() & (df[price_col] > 0)]

    # Log and drop records with missing year (indicates ETL date parsing failure)
    missing_year = df['ano'].isna().sum()
    if missing_year > 0:
        logger.warning(f"Dropping {missing_year} records with missing year (ETL date parse failure)")
    df = df[df['ano'].notna()]

    # Normalize price column name
    if price_col == 'preco' and 'preco_medio' not in df.columns:
        df['preco_medio'] = df['preco']

    # Fix encoding in product names
    df['produto'] = df['produto'].apply(fix_encoding)

    # Fix encoding in regional names if present
    if 'regional' in df.columns:
        df['regional'] = df['regional'].apply(fix_encoding)

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


# ============================================================================
# REGIONAL DATA FUNCTIONS
# ============================================================================

def generate_regional_prices(df: pd.DataFrame) -> dict:
    """Generate price data by regional, product, and period."""
    logger.info("Generating regional prices...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping regional prices")
        return {'by_regional': {}, 'generated_at': datetime.now().isoformat()}

    prices = {'by_regional': {}, 'by_product_regional': {}}

    # Group by regional
    for regional, grp in df.groupby('regional'):
        prices['by_regional'][regional] = {
            'total_records': len(grp),
            'avg_price': round(float(grp['preco_medio'].mean()), 2),
            'products': grp['produto'].nunique(),
            'year_min': int(grp['ano'].min()),
            'year_max': int(grp['ano'].max()),
        }

    # Group by product and regional (time series)
    for (produto, regional), grp in df.groupby(['produto', 'regional']):
        grp_sorted = grp.sort_values('periodo')
        series = []
        for periodo, pg in grp_sorted.groupby('periodo'):
            series.append({
                'p': periodo,
                'v': round(float(pg['preco_medio'].mean()), 2),
                'n': len(pg),
            })

        prices['by_product_regional'].setdefault(produto, {})[regional] = series

    prices['generated_at'] = datetime.now().isoformat()
    return prices


def generate_regional_comparison(df: pd.DataFrame) -> dict:
    """Generate cross-regional comparison data for products."""
    logger.info("Generating regional comparison...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping regional comparison")
        return {'comparisons': {}, 'generated_at': datetime.now().isoformat()}

    comparisons = {}

    # For each product, compare prices across regions
    for produto, prod_df in df.groupby('produto'):
        regional_stats = {}
        for regional, grp in prod_df.groupby('regional'):
            prices = grp['preco_medio'].values
            regional_stats[regional] = {
                'mean': round(float(np.mean(prices)), 2),
                'min': round(float(np.min(prices)), 2),
                'max': round(float(np.max(prices)), 2),
                'std': round(float(np.std(prices)), 2) if len(prices) > 1 else 0,
                'count': len(prices),
            }

        if len(regional_stats) >= 2:  # Only include if we have multiple regions
            all_means = [s['mean'] for s in regional_stats.values()]
            comparisons[produto] = {
                'regions': regional_stats,
                'spread': round(max(all_means) - min(all_means), 2),
                'spread_pct': round((max(all_means) - min(all_means)) / np.mean(all_means) * 100, 1) if np.mean(all_means) > 0 else 0,
                'cheapest': min(regional_stats.items(), key=lambda x: x[1]['mean'])[0],
                'most_expensive': max(regional_stats.items(), key=lambda x: x[1]['mean'])[0],
            }

    return {'comparisons': comparisons, 'generated_at': datetime.now().isoformat()}


def generate_regional_filters(df: pd.DataFrame) -> dict:
    """Generate regional filter data."""
    logger.info("Generating regional filters...")

    filters = {
        'regionais': REGIONAIS_PADRAO,
        'regionais_com_dados': [],
        'regional_products': {},
        'regional_categories': {},
        'regional_anos': {},
    }

    if 'regional' not in df.columns:
        logger.warning("No regional column found - returning empty regional filters")
        return filters

    filters['regionais_com_dados'] = sorted(df['regional'].dropna().unique().tolist())

    # Products available in each regional
    for regional, grp in df.groupby('regional'):
        filters['regional_products'][regional] = sorted(grp['produto'].unique().tolist())
        filters['regional_categories'][regional] = sorted(grp['categoria'].unique().tolist())
        filters['regional_anos'][regional] = sorted([int(x) for x in grp['ano'].unique()])

    return filters


def generate_regional_timeseries(df: pd.DataFrame) -> dict:
    """Generate time series data with regional breakdown."""
    logger.info("Generating regional timeseries...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping regional timeseries")
        return {'series': {}, 'generated_at': datetime.now().isoformat()}

    series = {'by_regional': {}, 'by_period': {}}

    # Time series for each regional
    for regional, grp in df.groupby('regional'):
        regional_series = {}
        for periodo, pg in grp.groupby('periodo'):
            regional_series[periodo] = {
                'mean': round(float(pg['preco_medio'].mean()), 2),
                'count': len(pg),
            }
        series['by_regional'][regional] = regional_series

    # Aggregated by period with regional breakdown
    for periodo, grp in df.groupby('periodo'):
        period_data = {'total': round(float(grp['preco_medio'].mean()), 2)}
        for regional, rg in grp.groupby('regional'):
            period_data[regional] = round(float(rg['preco_medio'].mean()), 2)
        series['by_period'][periodo] = period_data

    series['generated_at'] = datetime.now().isoformat()
    return series


def generate_detailed_regional_data(df: pd.DataFrame) -> dict:
    """Generate detailed records with regional information."""
    logger.info("Generating detailed regional data...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping detailed regional data")
        return {'records': [], 'generated_at': datetime.now().isoformat()}

    # Use stratified sampling to guarantee representation of all (regional, ano) combos
    MAX_RECORDS = 200000  # Increased from 100k — ~20MB JSON is acceptable for static asset
    if len(df) > MAX_RECORDS:
        # Stratified sample by (regional, ano) to preserve all combinations
        strata = df.groupby(['regional', 'ano'], group_keys=False)
        # Calculate proportional sample size per stratum, minimum 1
        strata_sizes = strata.size()
        total = strata_sizes.sum()
        target_sizes = (strata_sizes / total * MAX_RECORDS).clip(lower=1).astype(int)

        sampled_parts = []
        for (reg, ano), size in target_sizes.items():
            stratum_df = df[(df['regional'] == reg) & (df['ano'] == ano)]
            n = min(size, len(stratum_df))
            sampled_parts.append(stratum_df.sample(n=n, random_state=42))

        sample_df = pd.concat(sampled_parts, ignore_index=True)
        logger.info(f"Stratified sample: {len(sample_df)} records from {len(df)} (preserving all regional-year combos)")
    else:
        sample_df = df

    records = []
    for _, row in sample_df.iterrows():
        records.append({
            'd': row.get('data', ''),
            'a': int(row['ano']) if pd.notna(row['ano']) else None,
            'p': row.get('produto', ''),
            'c': row.get('categoria', ''),
            'r': row.get('regional', ''),
            'u': row.get('unidade', ''),
            'v': round(float(row['preco_medio']), 2),
        })

    return {
        'records': records,
        'filters': {
            'anos': sorted([int(x) for x in df['ano'].dropna().unique()]),
            'categorias': sorted(df['categoria'].dropna().unique().tolist()),
            'produtos': sorted(df['produto'].dropna().unique().tolist())[:500],
            'regionais': sorted(df['regional'].dropna().unique().tolist()),
        },
        'generated_at': datetime.now().isoformat(),
    }


def generate_regional_statistics(df: pd.DataFrame) -> dict:
    """Generate aggregate statistics by regional."""
    logger.info("Generating regional statistics...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping regional statistics")
        return {'stats': {}, 'generated_at': datetime.now().isoformat()}

    stats = {}

    for regional, grp in df.groupby('regional'):
        prices = grp['preco_medio'].values
        stats[regional] = {
            'total_records': len(grp),
            'total_products': grp['produto'].nunique(),
            'total_categories': grp['categoria'].nunique(),
            'year_range': [int(grp['ano'].min()), int(grp['ano'].max())],
            'price_stats': {
                'mean': round(float(np.mean(prices)), 2),
                'median': round(float(np.median(prices)), 2),
                'std': round(float(np.std(prices)), 2),
                'min': round(float(np.min(prices)), 2),
                'max': round(float(np.max(prices)), 2),
            },
            'top_products': grp['produto'].value_counts().head(10).to_dict(),
            'categories': grp['categoria'].value_counts().to_dict(),
        }

    return {'stats': stats, 'generated_at': datetime.now().isoformat()}


def save_json(data: dict, filename: str):
    """Save JSON file."""
    filepath = JSON_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    logger.info(f"Saved {filename} ({filepath.stat().st_size / 1024:.1f} KB)")


def main():
    """Main preprocessing pipeline."""
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    # Check for at least one input file
    if not INPUT_FILE.exists() and not INPUT_FILE_REGIONAL.exists():
        logger.error(f"No input files found: {INPUT_FILE} or {INPUT_FILE_REGIONAL}")
        return

    # Load aggregated data
    df_agg = load_data(regional=False)

    if not df_agg.empty:
        # Original JSON files (from aggregated data)
        save_json(generate_aggregated_data(df_agg), 'aggregated.json')
        save_json(generate_detailed_data(df_agg), 'detailed.json')
        save_json(generate_time_series(df_agg), 'timeseries.json')
        save_json(generate_filter_maps(df_agg), 'filters.json')

        # Analytics JSON files
        save_json(generate_daily_series(df_agg), 'daily_series.json')
        save_json(generate_volatility(df_agg), 'volatility.json')
        save_json(generate_regional_spread(df_agg), 'regional_spread.json')

    # Load regional data if available
    if INPUT_FILE_REGIONAL.exists():
        df_regional = load_data(regional=True)

        if not df_regional.empty:
            # Regional JSON files
            save_json(generate_regional_prices(df_regional), 'regional_prices.json')
            save_json(generate_regional_comparison(df_regional), 'regional_comparison.json')
            save_json(generate_regional_filters(df_regional), 'regional_filters.json')
            save_json(generate_regional_timeseries(df_regional), 'regional_timeseries.json')
            save_json(generate_detailed_regional_data(df_regional), 'detailed_regional.json')
            save_json(generate_regional_statistics(df_regional), 'regional_statistics.json')

            logger.info(f"Generated regional JSONs with {len(df_regional)} records from {df_regional['regional'].nunique()} regions")
    else:
        logger.info("No regional data file found - skipping regional JSONs")

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
