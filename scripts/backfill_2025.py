#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill script for SIMA Daily Quotations (2025+).
Discovers all SIMA pages from ID 2520 onward and downloads Excel files.

Usage:
    python scripts/backfill_2025.py
    python scripts/backfill_2025.py --start-id 2600 --end-id 3000
"""

import sys
import json
import re
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from api.scraper import (
    scrape_cotacao, update_links_file, COTACAO_URL, LINKS_FILE,
    load_scraper_state, save_scraper_state,
)

BACKFILL_STATE = ROOT_DIR / "data" / "backfill_state.json"
DEFAULT_START_ID = 2286
DEFAULT_END_ID = 3200


def load_known_ids() -> set:
    """Load IDs already present in links.txt."""
    known = set()
    if LINKS_FILE.exists():
        with open(LINKS_FILE, 'r') as f:
            for line in f:
                m = re.search(r'SIMA-(\d+)', line, re.IGNORECASE)
                if m:
                    known.add(int(m.group(1)))
    return known


def load_backfill_state() -> dict:
    """Load backfill state (which IDs were already tried)."""
    if BACKFILL_STATE.exists():
        try:
            return json.loads(BACKFILL_STATE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"empty_ids": [], "found_ids": []}


def save_backfill_state(state: dict):
    """Persist backfill state."""
    BACKFILL_STATE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    BACKFILL_STATE.write_text(json.dumps(state, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Backfill SIMA quotations from 2025 onward")
    parser.add_argument("--start-id", type=int, default=DEFAULT_START_ID,
                        help=f"Starting SIMA page ID (default: {DEFAULT_START_ID})")
    parser.add_argument("--end-id", type=int, default=DEFAULT_END_ID,
                        help=f"Ending SIMA page ID (default: {DEFAULT_END_ID})")
    args = parser.parse_args()

    print("=" * 60)
    print("SIMA Backfill - Discovering pages from ID %d to %d" % (args.start_id, args.end_id))
    print("=" * 60)

    known_ids = load_known_ids()
    state = load_backfill_state()
    tried_empty = set(state.get("empty_ids", []))
    found_ids = list(state.get("found_ids", []))

    new_links = []
    new_found = 0
    highest_found = args.start_id
    total_files = 0

    for cid in range(args.start_id, args.end_id + 1):
        if cid in known_ids or cid in tried_empty:
            continue

        date, files_downloaded = scrape_cotacao(cid)

        if files_downloaded > 0:
            new_links.append(f"{COTACAO_URL}{cid}")
            found_ids.append(cid)
            highest_found = max(highest_found, cid)
            new_found += 1
            total_files += files_downloaded
            print(f"[FOUND] ID {cid}: {files_downloaded} files, date={date}")
        elif date is not None:
            # Page exists but no downloadable files
            new_links.append(f"{COTACAO_URL}{cid}")
            found_ids.append(cid)
            highest_found = max(highest_found, cid)
            new_found += 1
            print(f"[PAGE]  ID {cid}: no files, date={date}")
        else:
            tried_empty.add(cid)

        time.sleep(1)

        # Save incrementally every 50 found pages
        if new_found > 0 and new_found % 50 == 0:
            print(f"\n  Saving progress ({new_found} pages found, {total_files} files)...")
            if new_links:
                update_links_file(new_links)
                new_links = []
            state["empty_ids"] = sorted(tried_empty)
            state["found_ids"] = sorted(set(found_ids))
            save_backfill_state(state)

    # Final save
    if new_links:
        update_links_file(new_links)

    state["empty_ids"] = sorted(tried_empty)
    state["found_ids"] = sorted(set(found_ids))
    save_backfill_state(state)

    # Update scraper state with highest found
    scraper_state = load_scraper_state()
    if highest_found > scraper_state.get("last_found_id", 0):
        scraper_state["last_found_id"] = highest_found
        save_scraper_state(scraper_state)

    print("\n" + "=" * 60)
    print(f"Backfill complete.")
    print(f"  New pages found: {new_found}")
    print(f"  Excel files downloaded: {total_files}")
    print(f"  Highest ID: {highest_found}")
    print(f"  Total known pages: {len(set(found_ids))}")
    print("=" * 60)
    print("\nNext step: run ETL to process downloaded files:")
    print("  py api/etl_process.py")
    print("  py api/preprocess_data.py")


if __name__ == "__main__":
    main()
