#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run the complete ETL pipeline locally.
"""

import sys
import os
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

def main():
    print("=" * 60)
    print("SIMA Daily Quotations - Complete Pipeline")
    print("=" * 60)

    # Step 1: Download data (if needed)
    print("\n[1/4] Checking for new data to download...")
    try:
        from scripts.download_data import main as download_main
        download_main()
    except Exception as e:
        print(f"Download step skipped: {e}")

    # Step 2: Run scraper (if configured)
    print("\n[2/4] Running web scraper...")
    try:
        from api.scraper import scrape_latest_quotations
        scrape_latest_quotations(days_back=7)
    except Exception as e:
        print(f"Scraper step skipped: {e}")

    # Step 3: Run ETL
    print("\n[3/4] Running ETL process...")
    try:
        from api.etl_process import process_all_files
        process_all_files()
    except Exception as e:
        print(f"ETL error: {e}")
        return

    # Step 4: Preprocess data
    print("\n[4/4] Preprocessing data for dashboard...")
    try:
        from api.preprocess_data import main as preprocess_main
        preprocess_main()
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return

    # Copy JSON files to dashboard (for local development)
    print("\n[5/5] Copying JSON files to dashboard...")
    json_dir = ROOT_DIR / "data" / "json"
    dashboard_data_dir = ROOT_DIR / "dashboard" / "public" / "data"
    dashboard_data_dir.mkdir(parents=True, exist_ok=True)

    for json_file in json_dir.glob("*.json"):
        dest = dashboard_data_dir / json_file.name
        import shutil
        shutil.copy2(json_file, dest)
        print(f"  Copied {json_file.name}")

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)
    print("\nTo start the dashboard:")
    print("  cd dashboard && npm run dev")
    print("\nTo start the API server:")
    print("  python -m api.app")


if __name__ == "__main__":
    main()
