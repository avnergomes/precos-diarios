#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill script for SIMA Daily Quotations (2025+).
Discovers all SIMA pages from ID 2520 onward and scrapes price data.

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

import pandas as pd
from api.scraper import (
    scrape_cotacao, update_links_file, COTACAO_URL,
    SCRAPED_DIR, LINKS_FILE,
)

BACKFILL_STATE = ROOT_DIR / "data" / "backfill_state.json"
DEFAULT_START_ID = 2520
DEFAULT_END_ID = 3200
BATCH_SIZE = 50


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
    """Load backfill state (which IDs were already tried and empty)."""
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


def save_records(records: list):
    """Merge records into scraped_quotations.csv."""
    if not records:
        return

    SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
    scraped_csv = SCRAPED_DIR / "scraped_quotations.csv"
    new_df = pd.DataFrame(records)

    if scraped_csv.exists():
        existing = pd.read_csv(scraped_csv, encoding='utf-8-sig')
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=['data', 'produto', 'preco_medio'])
    else:
        combined = new_df

    combined = combined.sort_values(['ano', 'mes', 'dia', 'produto'], na_position='last')
    combined.to_csv(scraped_csv, index=False, encoding='utf-8-sig')
    print(f"  Saved {len(combined)} total records to {scraped_csv}")


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

    batch_records = []
    batch_links = []
    new_found = 0

    for cid in range(args.start_id, args.end_id + 1):
        if cid in known_ids or cid in tried_empty:
            continue

        date, records = scrape_cotacao(cid)

        if records:
            batch_records.extend(records)
            batch_links.append(f"{COTACAO_URL}{cid}")
            found_ids.append(cid)
            new_found += 1
            print(f"[FOUND] ID {cid}: {len(records)} records, date={date}")
        else:
            tried_empty.add(cid)

        time.sleep(1)

        # Save incrementally every BATCH_SIZE found pages
        if new_found > 0 and new_found % BATCH_SIZE == 0:
            print(f"\n  Saving batch ({new_found} found so far)...")
            save_records(batch_records)
            if batch_links:
                update_links_file(batch_links)
            state["empty_ids"] = sorted(tried_empty)
            state["found_ids"] = sorted(set(found_ids))
            save_backfill_state(state)
            batch_records = []
            batch_links = []

    # Final save
    if batch_records or batch_links:
        print(f"\n  Final save...")
        save_records(batch_records)
        if batch_links:
            update_links_file(batch_links)

    state["empty_ids"] = sorted(tried_empty)
    state["found_ids"] = sorted(set(found_ids))
    save_backfill_state(state)

    print("\n" + "=" * 60)
    print(f"Backfill complete. Found {new_found} new pages.")
    print(f"Total known pages: {len(found_ids)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
