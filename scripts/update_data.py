#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Incremental data update for GitHub Actions pipeline.

Downloads new Excel files via the scraper, processes only those new files,
and appends the results to the existing consolidated.csv. This avoids needing
the full historical Excel archive (which is gitignored).

Pipeline:
  1. Scrape new SIMA pages → download Excel files
  2. Process only new Excel files into records
  3. Append to existing consolidated.csv (deduplicate)
  4. Regenerate dashboard JSON files
  5. Copy JSONs to dashboard/public/data/
  6. Regenerate forecasts
"""

import sys
import subprocess
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Project paths
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CONSOLIDATED_CSV = PROCESSED_DIR / "consolidated.csv"
CONSOLIDATED_REGIONAL_CSV = PROCESSED_DIR / "consolidated_regional.csv"
JSON_DIR = DATA_DIR / "json"
DASHBOARD_DATA_DIR = ROOT_DIR / "dashboard" / "public" / "data"
DAILY_DIR = DATA_DIR / "extracted" / "daily"


def step_scrape():
    """Step 1: Run the scraper to discover and download new Excel files."""
    logger.info("=" * 60)
    logger.info("STEP 1: Scraping new SIMA pages")
    logger.info("=" * 60)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    files_before = set(DAILY_DIR.glob("*.xls*"))

    from api.scraper import scrape_latest_quotations
    total = scrape_latest_quotations()
    logger.info(f"Scraper downloaded {total} files")

    files_after = set(DAILY_DIR.glob("*.xls*"))
    new_files = files_after - files_before
    logger.info(f"New files detected: {len(new_files)}")
    return list(new_files)


def step_process_new_files(new_files):
    """Step 2: Process only new Excel files and append to consolidated.csv."""
    logger.info("=" * 60)
    logger.info("STEP 2: Processing new Excel files")
    logger.info("=" * 60)

    import pandas as pd
    from api.etl_process import process_excel_file, normalize_products

    if not new_files:
        logger.info("No new files to process")
        return False

    # Process new files
    all_records = []
    for filepath in new_files:
        logger.info(f"  Processing: {filepath.name}")
        records = process_excel_file(filepath)
        all_records.extend(records)

    if not all_records:
        logger.info("No records extracted from new files")
        return False

    logger.info(f"Extracted {len(all_records)} records from {len(new_files)} files")

    # Create DataFrame and normalize
    new_df = pd.DataFrame(all_records)
    new_df = normalize_products(new_df)
    logger.info(f"After normalization: {len(new_df)} records")

    if new_df.empty:
        logger.info("No valid records after normalization")
        return False

    # Load existing consolidated data
    if CONSOLIDATED_CSV.exists():
        existing_df = pd.read_csv(CONSOLIDATED_CSV, encoding='utf-8-sig')
        logger.info(f"Existing consolidated: {len(existing_df)} records")

        # Append new records
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    # Deduplicate
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['data', 'produto', 'preco_medio'])
    logger.info(f"After dedup: {len(combined_df)} records (removed {before_dedup - len(combined_df)} dupes)")

    # Sort
    combined_df = combined_df.sort_values(['ano', 'mes', 'dia', 'produto'], na_position='last')

    # Save
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(CONSOLIDATED_CSV, index=False, encoding='utf-8-sig')
    logger.info(f"Saved consolidated CSV: {len(combined_df)} records")

    return True


def step_process_regional_files(new_files):
    """Step 2b: Process new Excel files for REGIONAL data and append to consolidated_regional.csv."""
    logger.info("=" * 60)
    logger.info("STEP 2b: Processing regional data from new files")
    logger.info("=" * 60)

    import pandas as pd
    from api.etl_process import process_excel_file_regional

    if not new_files:
        logger.info("No new files to process for regional data")
        return False

    # Process new files for regional data
    all_records = []
    for filepath in new_files:
        logger.info(f"  Processing regional: {filepath.name}")
        records = process_excel_file_regional(filepath)
        all_records.extend(records)

    if not all_records:
        logger.info("No regional records extracted from new files")
        return False

    logger.info(f"Extracted {len(all_records)} regional records from {len(new_files)} files")

    # Create DataFrame
    new_df = pd.DataFrame(all_records)
    logger.info(f"Regional records: {len(new_df)}")

    if new_df.empty:
        logger.info("No valid regional records")
        return False

    # Normalize product names (reuse from etl_process)
    from api.etl_process import normalize_products
    # Add dummy columns required by normalize_products
    if 'preco_medio' not in new_df.columns:
        new_df['preco_medio'] = new_df['preco']
    new_df = normalize_products(new_df)
    # Remove dummy column if added
    if 'preco_medio' in new_df.columns and 'preco' in new_df.columns:
        new_df = new_df.drop(columns=['preco_medio'])

    # Load existing regional data
    if CONSOLIDATED_REGIONAL_CSV.exists():
        existing_df = pd.read_csv(CONSOLIDATED_REGIONAL_CSV, encoding='utf-8-sig')
        logger.info(f"Existing regional: {len(existing_df)} records")

        # Append new records
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    # Deduplicate
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['data', 'produto', 'regional', 'preco'])
    logger.info(f"After dedup: {len(combined_df)} records (removed {before_dedup - len(combined_df)} dupes)")

    # Sort
    combined_df = combined_df.sort_values(['ano', 'mes', 'dia', 'regional', 'produto'], na_position='last')

    # Save
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(CONSOLIDATED_REGIONAL_CSV, index=False, encoding='utf-8-sig')
    logger.info(f"Saved regional CSV: {len(combined_df)} records")

    return True


def step_preprocess():
    """Step 3: Regenerate dashboard JSON files from consolidated.csv."""
    logger.info("=" * 60)
    logger.info("STEP 3: Preprocessing data for dashboard")
    logger.info("=" * 60)

    from api.preprocess_data import main as preprocess_main
    preprocess_main()


def step_copy_json():
    """Step 4: Copy JSON files to dashboard/public/data/."""
    logger.info("=" * 60)
    logger.info("STEP 4: Copying JSON files to dashboard")
    logger.info("=" * 60)

    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not JSON_DIR.exists():
        logger.warning(f"JSON directory not found: {JSON_DIR}")
        return

    for json_file in JSON_DIR.glob("*.json"):
        dest = DASHBOARD_DATA_DIR / json_file.name
        shutil.copy2(json_file, dest)
        logger.info(f"  Copied {json_file.name}")


def step_forecasts():
    """Step 5: Regenerate forecasts."""
    logger.info("=" * 60)
    logger.info("STEP 5: Generating forecasts")
    logger.info("=" * 60)

    result = subprocess.run(
        [sys.executable, str(ROOT_DIR / "scripts" / "generate_forecasts.py")],
        cwd=str(ROOT_DIR),
        capture_output=True, text=True,
    )
    if result.stdout:
        logger.info(result.stdout[-2000:])
    if result.returncode != 0:
        logger.error(f"Forecast generation failed (exit {result.returncode})")
        if result.stderr:
            logger.error(result.stderr[-1000:])
        raise RuntimeError("Forecast generation failed")


# Exit codes consumed by .github/workflows/data-pipeline.yml.
# These must stay distinct: an upstream failure must never be indistinguishable
# from "SIMA published nothing today", otherwise a broken scraper reports as a
# green run that simply had nothing to commit.
EXIT_CHANGED = 0      # new data committed
EXIT_ERROR = 1        # a step failed; needs investigation
EXIT_NO_CHANGES = 2   # ran cleanly, upstream had nothing new


def main():
    logger.info("=" * 60)
    logger.info("SIMA Daily Quotations - Incremental Update")
    logger.info("=" * 60)

    errors = []

    # Step 1: Scrape
    try:
        new_files = step_scrape()
    except Exception as e:
        logger.exception("Scraper failed")
        errors.append(f"scrape: {e}")
        new_files = []

    # Step 2: Process new files (aggregated)
    try:
        has_new_data = step_process_new_files(new_files)
    except Exception as e:
        logger.exception("Processing failed")
        errors.append(f"process: {e}")
        has_new_data = False

    # Step 2b: Process new files (regional)
    try:
        has_regional_data = step_process_regional_files(new_files)
        if has_regional_data:
            has_new_data = True
    except Exception as e:
        logger.exception("Regional processing failed")
        errors.append(f"process_regional: {e}")

    if not has_new_data:
        # An upstream step blew up: do not report this as "nothing new".
        if errors:
            logger.error(
                "No new data, but %d step(s) failed: %s", len(errors), "; ".join(errors)
            )
            return EXIT_ERROR

        logger.info("No new data found. Checking if JSON files need regeneration...")
        # Still regenerate if dashboard JSONs don't exist
        if not (DASHBOARD_DATA_DIR / "aggregated.json").exists():
            logger.info("Dashboard JSONs missing, regenerating...")
            has_new_data = True
        else:
            logger.info("Everything up to date. Nothing to do.")
            return EXIT_NO_CHANGES

    # Step 3: Preprocess
    try:
        step_preprocess()
    except Exception as e:
        logger.exception("Preprocessing failed")
        errors.append(f"preprocess: {e}")
        return EXIT_ERROR

    # Step 4: Copy JSONs
    copy_success = False
    try:
        step_copy_json()
        copy_success = True
    except Exception as e:
        logger.exception("Copy failed")
        errors.append(f"copy_json: {e}")

    # Step 5: Forecasts
    try:
        step_forecasts()
    except Exception as e:
        logger.exception("Forecast generation failed")
        errors.append(f"forecasts: {e}")
        # Non-fatal: dashboard still works without new forecasts

    # Only delete Excel files AFTER confirmed successful processing
    if copy_success and DAILY_DIR.exists():
        for f in new_files:
            if f.exists():
                f.unlink()
        logger.info(f"Cleaned up {len(new_files)} temporary Excel files")

    if errors:
        logger.error(
            "Update produced data but %d step(s) failed: %s",
            len(errors),
            "; ".join(errors),
        )
        return EXIT_ERROR

    logger.info("=" * 60)
    logger.info("Incremental update complete!")
    logger.info("=" * 60)
    return EXIT_CHANGED


if __name__ == "__main__":
    sys.exit(main())
