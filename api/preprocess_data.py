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
from datetime import datetime, timezone
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
QUARANTINE_FILE = DATA_PROCESSED_DIR / "quarantine.csv"

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


def _quarantine(rows: pd.DataFrame, motivo: str) -> None:
    """Append rows to QUARANTINE_FILE. Aggregated and regional rows have
    different columns, so merge in pandas (column union) instead of a raw
    CSV append, which would produce ragged lines."""
    rows = rows.assign(motivo_quarentena=motivo)
    if QUARANTINE_FILE.exists():
        rows = pd.concat([pd.read_csv(QUARANTINE_FILE, encoding='utf-8-sig'), rows], ignore_index=True)
    rows.to_csv(QUARANTINE_FILE, index=False, encoding='utf-8-sig')


def load_data(regional: bool = False) -> pd.DataFrame:
    """Load consolidated data.

    Args:
        regional: If True, load regional data; if False, load aggregated data
    """
    if regional:
        # Regional data lives in year partitions (api/storage.py); falls back to
        # the legacy single file inside load_regional().
        from api.storage import load_regional
        input_file = 'data/processed/regional/'
        logger.info("Loading regional data from year partitions...")
        df = load_regional()
        if df.empty:
            logger.info("No regional data; falling back to aggregated data")
            return load_data(regional=False)
    else:
        input_file = INPUT_FILE
        logger.info(f"Loading aggregated data from {input_file}...")
        if not input_file.exists():
            logger.warning(f"File not found: {input_file}")
            return pd.DataFrame()
        # All CSVs are written with utf-8-sig; fail loud on wrong encoding
        try:
            df = pd.read_csv(input_file, encoding='utf-8-sig')
        except Exception as e:
            logger.error(f"Failed to load {input_file} as utf-8-sig: {e}")
            raise

    if df.empty:
        logger.error(f"Empty data from {input_file}")
        return pd.DataFrame()

    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')

    # Handle different column names for price
    price_col = 'preco' if 'preco' in df.columns else 'preco_medio'
    df[price_col] = pd.to_numeric(df[price_col], errors='coerce')

    # Quarantine invalid prices before filtering
    invalid_mask = df[price_col].isna() | (df[price_col] <= 0)
    if invalid_mask.any():
        _quarantine(df[invalid_mask], 'preco_invalido')
        logger.warning(f"Quarantined {invalid_mask.sum()} rows with price <= 0 → {QUARANTINE_FILE}")

    df = df[df[price_col].notna() & (df[price_col] > 0)]

    # Log and drop records with missing year (indicates ETL date parsing failure)
    missing_year = df['ano'].isna().sum()
    if missing_year > 0:
        logger.warning(f"Dropping {missing_year} records with missing year (ETL date parse failure)")
        if 'arquivo' in df.columns:
            bad_files = df[df['ano'].isna()]['arquivo'].unique()[:10]
            logger.warning(f"  Sample affected files: {list(bad_files)}")
    df = df[df['ano'].notna()]

    # Normalize price column name
    if price_col == 'preco' and 'preco_medio' not in df.columns:
        df['preco_medio'] = df['preco']

    # Fix encoding in product names
    df['produto'] = df['produto'].apply(fix_encoding)

    # Fix encoding in regional names if present
    if 'regional' in df.columns:
        df['regional'] = df['regional'].apply(fix_encoding)

    # Normalize category names (fix missing accents)
    category_fixes = {
        'Graos': 'Grãos',
        'Cafe': 'Café',
        'Pecuaria': 'Pecuária',
    }
    df['categoria'] = df['categoria'].replace(category_fixes)

    # Fix category inconsistencies - use most common category for each product
    product_main_category = df.groupby('produto')['categoria'].agg(
        lambda x: x.value_counts().index[0]
    )
    df['categoria'] = df['produto'].map(product_main_category)

    # Normalize unit casing: 'Kg'→'kg', 'Kg renda'→'kg renda'
    _unit_fix = {'Kg': 'kg', 'Kg renda': 'kg renda'}
    if 'unidade' in df.columns:
        df['unidade'] = df['unidade'].map(lambda u: _unit_fix.get(u, u) if pd.notna(u) else u)

    # Outlier detection: quarantine prices >10x or <0.1x per-product+unit median
    price_col_used = 'preco' if 'preco' in df.columns and 'preco_medio' not in df.columns else 'preco_medio'
    if price_col_used in df.columns and 'unidade' in df.columns:
        medians = df.groupby(['produto', 'unidade'])[price_col_used].transform('median')
        outlier_mask = ((df[price_col_used] > medians * 10) | (df[price_col_used] < medians * 0.1)) & medians.notna()
        if outlier_mask.any():
            _quarantine(df[outlier_mask], 'outlier_preco')
            logger.warning(f"Quarantined {outlier_mask.sum()} outlier rows → {QUARANTINE_FILE}")
            df = df[~outlier_mask]

    df['periodo'] = df.apply(
        lambda x: f"{int(x['ano'])}-{int(x['mes']):02d}" if pd.notna(x['mes']) else f"{int(x['ano'])}",
        axis=1
    )

    logger.info(f"Loaded {len(df)} records")
    return df


def generate_aggregated_data(df: pd.DataFrame) -> dict:
    """Gera estatisticas pre-agregadas.

    Este arquivo passou a ser a fonte da visao padrao do dashboard (sem
    filtro). Antes o front baixava detailed.json (4,5 MB) e recalculava tudo
    no cliente; como detailed.json e uma AMOSTRA de 50 mil registros, os
    numeros de destaque saiam da amostra e nao do conjunto completo. Aqui os
    agregados vem do df inteiro, entao alem de muito menor tambem e correto.

    Por isso incluimos minimo/maximo/registros/unidade e a sparkline mensal:
    sao os campos que o dashboard antes derivava dos registros crus.
    """
    agg = {
        'metadata': {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_records': len(df),
            'year_min': int(df['ano'].min()),
            'year_max': int(df['ano'].max()),
            'latest_date': _latest_date(df),
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
        precos = grp['preco_medio'].dropna()
        agg['by_category'][cat] = {
            'media': round(float(precos.mean()), 2) if len(precos) else 0.0,
            'registros': len(grp),
            'minimo': round(float(precos.min()), 2) if len(precos) else 0.0,
            'maximo': round(float(precos.max()), 2) if len(precos) else 0.0,
            'produtos': int(grp['produto'].nunique()),
        }

    for prod, grp in df.groupby('produto'):
        precos = grp['preco_medio'].dropna()
        if not len(precos):
            continue

        unidade = grp['unidade'].mode()
        anos = sorted(grp['ano'].dropna().unique(), reverse=True)
        variacao = None
        if len(anos) >= 2:
            # YTD: compare same months in both years to avoid partial-year bias
            current_months = grp[grp['ano'] == anos[0]]['mes'].dropna().unique()
            max_month = int(max(current_months)) if len(current_months) else 12
            atual = grp[(grp['ano'] == anos[0]) & (grp['mes'] <= max_month)]['preco_medio'].mean()
            anterior = grp[(grp['ano'] == anos[1]) & (grp['mes'] <= max_month)]['preco_medio'].mean()
            if pd.notna(atual) and pd.notna(anterior) and anterior > 0:
                variacao = round(float((atual - anterior) / anterior * 100), 2)

        agg['by_product'][prod] = {
            'media': round(float(precos.mean()), 2),
            'categoria': grp['categoria'].iloc[0],
            'registros': len(grp),
            'unidade': unidade.iloc[0] if len(unidade) else None,
            'minimo': round(float(precos.min()), 2),
            'maximo': round(float(precos.max()), 2),
            'variacao': variacao,
            # Ultimos 12 meses, no mesmo formato que o front espera.
            'sparkline': _monthly_sparkline(grp),
        }

    return agg


def _latest_date(df: pd.DataFrame) -> str:
    """Data mais recente presente no conjunto, como string ISO."""
    datas = df['data'].dropna().astype(str)
    return max(datas) if len(datas) else ''


def _monthly_sparkline(grp: pd.DataFrame, months: int = 12) -> list:
    """Media mensal dos ultimos `months` periodos de um produto."""
    if 'periodo' not in grp.columns:
        return []
    serie = grp.dropna(subset=['preco_medio']).groupby('periodo')['preco_medio'].mean()
    return [
        {'period': str(period), 'value': round(float(value), 2)}
        for period, value in serie.sort_index().tail(months).items()
    ]


def generate_latest_prices(df: pd.DataFrame) -> dict:
    """Registros completos da data mais recente.

    O painel "Ultimos Precos" derivava isso varrendo detailed.json inteiro.
    Como aquele arquivo e uma amostra aleatoria, o painel podia omitir
    produtos cotados no dia. Aqui usamos o df completo, entao o resultado e
    exato e cabe em poucos KB.
    """
    latest = _latest_date(df)
    if not latest:
        return {'date': '', 'records': []}

    day = df[df['data'].astype(str) == latest]
    records = [
        {
            'd': str(row.get('data', '')),
            'a': int(row['ano']) if pd.notna(row['ano']) else None,
            'p': row.get('produto', ''),
            'c': row.get('categoria', ''),
            'u': row.get('unidade', ''),
            'pm': round(float(row['preco_medio']), 2),
        }
        for _, row in day.iterrows()
        if pd.notna(row.get('preco_medio'))
    ]

    return {'date': latest, 'records': records}


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
    """Registros detalhados, agora completos.

    Antes isto era uma amostra aleatoria de 50 mil registros, porque o arquivo
    era baixado no carregamento inicial e o tamanho pesava. O efeito colateral
    era que todo numero do dashboard saia da amostra: filtrar por "Pecuaria"
    mostrava ~13,5 mil cotacoes onde existem ~20,9 mil.

    Como o dashboard passou a baixar este arquivo apenas sob demanda (quando o
    usuario aplica um filtro), o limite deixou de fazer sentido. Sem amostra,
    as visoes filtradas passam a bater com os agregados.
    """
    records = []
    for _, row in df.iterrows():
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

    return {'products': daily, 'generated_at': datetime.now(timezone.utc).isoformat()}


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

    return {'by_product': vol, 'generated_at': datetime.now(timezone.utc).isoformat()}


def generate_regional_spread(df: pd.DataFrame) -> dict:
    """Generate regional spread using min/max prices as proxy."""
    logger.info("Generating regional spread...")
    spread = {}

    # Check if min/max columns exist
    if 'preco_minimo' not in df.columns or 'preco_maximo' not in df.columns:
        logger.warning("preco_minimo/preco_maximo columns not found, skipping spread calculation")
        return {'by_product': {}, 'generated_at': datetime.now(timezone.utc).isoformat()}

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

    return {'by_product': spread, 'generated_at': datetime.now(timezone.utc).isoformat()}


# ============================================================================
# REGIONAL DATA FUNCTIONS
# ============================================================================

def generate_regional_prices(df: pd.DataFrame) -> dict:
    """Generate price data by regional, product, and period."""
    logger.info("Generating regional prices...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping regional prices")
        return {'by_regional': {}, 'generated_at': datetime.now(timezone.utc).isoformat()}

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

    prices['generated_at'] = datetime.now(timezone.utc).isoformat()
    return prices


def generate_regional_comparison(df: pd.DataFrame) -> dict:
    """Generate cross-regional comparison data for products."""
    logger.info("Generating regional comparison...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping regional comparison")
        return {'comparisons': {}, 'generated_at': datetime.now(timezone.utc).isoformat()}

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

    return {'comparisons': comparisons, 'generated_at': datetime.now(timezone.utc).isoformat()}


def generate_regional_filters(df: pd.DataFrame) -> dict:
    """Generate regional filter data."""
    logger.info("Generating regional filters...")

    filters = {
        'regionais': [],  # populated below from actual data
        'regionais_com_dados': [],
        'regional_products': {},
        'regional_categories': {},
        'regional_anos': {},
    }

    if 'regional' not in df.columns:
        logger.warning("No regional column found - returning empty regional filters")
        return filters

    filters['regionais_com_dados'] = sorted(df['regional'].dropna().unique().tolist())
    filters['regionais'] = filters['regionais_com_dados']  # derived from actual data

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
        return {'series': {}, 'generated_at': datetime.now(timezone.utc).isoformat()}

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

    series['generated_at'] = datetime.now(timezone.utc).isoformat()
    return series


def generate_detailed_regional_data(df: pd.DataFrame) -> dict:
    """Generate detailed records with regional information."""
    logger.info("Generating detailed regional data...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping detailed regional data")
        return {'records': [], 'generated_at': datetime.now(timezone.utc).isoformat()}

    # Sampling strategy: keep ALL recent data (2025+), stratified sample for historical data
    MAX_RECORDS = 300000
    RECENT_YEAR_CUTOFF = 2025  # Include all records from this year onwards

    # Split into recent and historical
    recent_df = df[df['ano'] >= RECENT_YEAR_CUTOFF]
    historical_df = df[df['ano'] < RECENT_YEAR_CUTOFF]

    # Budget for historical data
    historical_budget = max(0, MAX_RECORDS - len(recent_df))

    if len(historical_df) > historical_budget and historical_budget > 0:
        # Stratified sample by (regional, ano, mes) for historical data
        strata = historical_df.groupby(['regional', 'ano', 'mes'], group_keys=False)
        strata_sizes = strata.size()
        total = strata_sizes.sum()
        target_sizes = (strata_sizes / total * historical_budget).clip(lower=1).astype(int)

        sampled_parts = []
        for (reg, ano, mes), size in target_sizes.items():
            stratum_df = historical_df[(historical_df['regional'] == reg) &
                                       (historical_df['ano'] == ano) &
                                       (historical_df['mes'] == mes)]
            n = min(size, len(stratum_df))
            sampled_parts.append(stratum_df.sample(n=n, random_state=42))

        historical_sample = pd.concat(sampled_parts, ignore_index=True)
        sample_df = pd.concat([recent_df, historical_sample], ignore_index=True)
        logger.info(f"Sample: {len(recent_df)} recent (>={RECENT_YEAR_CUTOFF}) + {len(historical_sample)} historical = {len(sample_df)} total")
    elif len(historical_df) <= historical_budget:
        # All data fits within budget
        sample_df = df
        logger.info(f"Using all {len(df)} records (within budget)")
    else:
        # Only recent data (no budget for historical)
        sample_df = recent_df
        logger.info(f"Using only recent data: {len(recent_df)} records")

    records = []
    for _, row in sample_df.iterrows():
        records.append({
            'd': row.get('data', ''),
            'a': int(row['ano']) if pd.notna(row['ano']) else None,
            'm': int(row['mes']) if pd.notna(row.get('mes')) else None,
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
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }


def generate_regional_statistics(df: pd.DataFrame) -> dict:
    """Generate aggregate statistics by regional."""
    logger.info("Generating regional statistics...")

    if 'regional' not in df.columns:
        logger.warning("No regional column found - skipping regional statistics")
        return {'stats': {}, 'generated_at': datetime.now(timezone.utc).isoformat()}

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

    return {'stats': stats, 'generated_at': datetime.now(timezone.utc).isoformat()}


def save_json(data: dict, filename: str):
    """Save JSON file."""
    filepath = JSON_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    logger.info(f"Saved {filename} ({filepath.stat().st_size / 1024:.1f} KB)")


_VALID_CATEGORIES = {
    'Grãos', 'Café', 'Frutas', 'Hortaliças', 'Mandioca', 'Pecuária', 'Florestal',
}

_VALID_UNITS = {
    'sc 60 Kg', 'sc 50 Kg', 'arroba', 'kg', 'kg renda', 'tonelada',
    'unidade', 'caixa', 'duzia', 'litro', 'cabeça',
}


def _write_step_summary(msg: str) -> None:
    import os
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        try:
            with open(summary, 'a', encoding='utf-8') as f:
                f.write(f"\n> :warning: {msg}\n")
        except Exception:
            pass


def _business_days_since(d) -> int:
    """Approximate business days from date d to today (ignoring holidays)."""
    from datetime import date as _date
    today = _date.today()
    if d >= today:
        return 0
    count = 0
    current = d
    while current < today:
        current = current.__class__.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:
            count += 1
    return count


def _validate_df(df: pd.DataFrame, label: str = 'aggregated') -> None:
    """Validate data quality; raises ValueError on hard failures, logs warnings on soft ones."""
    from datetime import date as _date

    # Hard check: uniqueness of business key
    key_cols = ['data', 'produto', 'unidade']
    if all(c in df.columns for c in key_cols):
        dupes = df.duplicated(subset=key_cols, keep=False)
        if dupes.any():
            n = dupes.sum()
            msg = f"[{label}] HARD ERROR: {n} duplicate rows on (data, produto, unidade)"
            logger.error(msg)
            raise ValueError(msg)

    # Soft check: category domain
    if 'categoria' in df.columns:
        unknown_cats = set(df['categoria'].dropna().unique()) - _VALID_CATEGORIES
        if unknown_cats:
            # Warning, not error: a new legitimate value must not block the daily run
            msg = f"[{label}] unknown categories (update the allowed domain if legitimate): {unknown_cats}"
            logger.warning(msg)
            _write_step_summary(msg)

    # Soft check: unit domain
    if 'unidade' in df.columns:
        unknown_units = set(df['unidade'].dropna().unique()) - _VALID_UNITS
        if unknown_units:
            # Warning, not error: a new legitimate value must not block the daily run
            msg = f"[{label}] unknown units (update the allowed domain if legitimate): {unknown_units}"
            logger.warning(msg)
            _write_step_summary(msg)

    # Warning: staleness (>3 business days without new data)
    if 'data' in df.columns:
        try:
            latest = pd.to_datetime(df['data']).max().date()
            bd = _business_days_since(latest)
            if bd > 3:
                msg = f"[{label}] STALE DATA: latest record is {latest} ({bd} business days ago)"
                logger.warning(msg)
                _write_step_summary(msg)
        except Exception:
            pass


def main():
    """Main preprocessing pipeline."""
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    # Quarantine is rebuilt from scratch on every run (load_data appends to it)
    QUARANTINE_FILE.unlink(missing_ok=True)

    # Load aggregated data
    df_agg = load_data(regional=False)
    if df_agg.empty:
        raise RuntimeError(f"No aggregated data found at {INPUT_FILE}")

    _validate_df(df_agg, 'aggregated')
    # Original JSON files (from aggregated data)
    save_json(generate_aggregated_data(df_agg), 'aggregated.json')
    save_json(generate_latest_prices(df_agg), 'latest.json')
    # detailed.json continua sendo gerado, mas o dashboard so o baixa sob
    # demanda (ao aplicar filtro), nao mais no carregamento inicial.
    save_json(generate_detailed_data(df_agg), 'detailed.json')
    save_json(generate_time_series(df_agg), 'timeseries.json')
    save_json(generate_filter_maps(df_agg), 'filters.json')

    # Analytics JSON files
    save_json(generate_daily_series(df_agg), 'daily_series.json')
    save_json(generate_volatility(df_agg), 'volatility.json')
    save_json(generate_regional_spread(df_agg), 'regional_spread.json')

    # Regional data: same cleaning/quarantine path as aggregated (load_data)
    df_regional = load_data(regional=True)

    if not df_regional.empty and 'regional' in df_regional.columns:
        # Regional JSON files
        save_json(generate_regional_prices(df_regional), 'regional_prices.json')
        save_json(generate_regional_comparison(df_regional), 'regional_comparison.json')
        save_json(generate_regional_filters(df_regional), 'regional_filters.json')
        save_json(generate_regional_timeseries(df_regional), 'regional_timeseries.json')
        save_json(generate_detailed_regional_data(df_regional), 'detailed_regional.json')
        save_json(generate_regional_statistics(df_regional), 'regional_statistics.json')

        logger.info(f"Generated regional JSONs with {len(df_regional)} records from {df_regional['regional'].nunique()} regions")
    else:
        logger.info("No regional data found - skipping regional JSONs")

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
