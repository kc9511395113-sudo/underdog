"""Seed HK screener data by scanning stockanalysis.com."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config_hk import HK_DATA_FILE, HK_SCAN_LIMIT
from app.screener.hk_engine import run_hk_screen
from app.screener.hk_tiers import enrich_hk_results
import json

from app.storage import next_friday_refresh


def main():
    print(f"Scanning top {HK_SCAN_LIMIT} HKEX stocks (this takes a few minutes)...")

    def progress(msg):
        print(f"  {msg}")

    raw = run_hk_screen(progress=progress)
    data = enrich_hk_results(raw)
    data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
    data["meta"]["seeded_at"] = datetime.now(timezone.utc).isoformat()
    HK_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HK_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {HK_DATA_FILE}")
    print(f"Passing: {len(data['results'])} stocks")
    for r in data["results"][:15]:
        print(f"  {r['ticker']}  fwd={r['fpe_n']}  pb={r['pb_n']}  div={r['div_n']}%  {r['company'][:30]}")


if __name__ == "__main__":
    main()