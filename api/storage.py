#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regional CSV storage helpers: year-partitioned files under
data/processed/regional/consolidated_regional_YYYY.csv

Used by app_v2.py (imported via try/except) and update_data.py.
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent
_REGIONAL_DIR = _BASE_DIR / "data" / "processed" / "regional"
# Legacy single-file path (kept as write-fallback when no rows exist yet)
_SINGLE_FILE = _BASE_DIR / "data" / "processed" / "consolidated_regional.csv"


def load_regional() -> pd.DataFrame:
    """Load regional data from year-partitioned files.

    Falls back to the legacy single file when no partitions exist.
    Returns empty DataFrame if nothing is found.
    """
    partitions = sorted(_REGIONAL_DIR.glob("consolidated_regional_*.csv")) if _REGIONAL_DIR.exists() else []
    if partitions:
        frames = []
        for p in partitions:
            try:
                frames.append(pd.read_csv(p, encoding='utf-8-sig'))
            except Exception as e:
                logger.warning(f"Skipping unreadable partition {p.name}: {e}")
        if frames:
            df = pd.concat(frames, ignore_index=True)
            logger.info(f"Loaded {len(df):,} regional rows from {len(frames)} partitions")
            return df

    # Fall back to legacy single file
    if _SINGLE_FILE.exists():
        logger.info(f"Loading regional data from legacy single file {_SINGLE_FILE}")
        return pd.read_csv(_SINGLE_FILE, encoding='utf-8-sig')

    return pd.DataFrame()


def save_regional(df: pd.DataFrame) -> None:
    """Save regional DataFrame to year-partitioned CSV files.

    Each year gets its own file: consolidated_regional_YYYY.csv
    Existing partitions for years not in df are left untouched.
    """
    if df.empty:
        logger.warning("save_regional called with empty DataFrame — nothing written")
        return

    if 'ano' not in df.columns:
        raise ValueError("save_regional: 'ano' column missing; refusing to write")

    _REGIONAL_DIR.mkdir(parents=True, exist_ok=True)
    for year, grp in df.groupby(df['ano'].dropna().astype(int)):
        path = _REGIONAL_DIR / f"consolidated_regional_{int(year)}.csv"
        grp = grp.sort_values(['mes', 'dia', 'regional', 'produto'], na_position='last') \
                 if all(c in grp.columns for c in ['mes', 'dia', 'regional', 'produto']) \
                 else grp
        grp.to_csv(path, index=False, encoding='utf-8-sig')
    logger.info(f"Saved {len(df):,} regional rows across {df['ano'].nunique()} year partitions → {_REGIONAL_DIR}")
