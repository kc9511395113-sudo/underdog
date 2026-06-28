"""Seed data/screen_results.json from prior screener run (no Finviz scrape)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import DATA_FILE
from app.screener.tiers import enrich_results
from app.storage import next_friday_refresh, save_data

SOURCE = Path(__file__).resolve().parent.parent / "us_screener_results.json"


def main():
    if not SOURCE.exists():
        print(f"Source not found: {SOURCE}")
        print("Run us_screener.py first, or use POST /api/refresh after starting the site.")
        sys.exit(1)

    with open(SOURCE, encoding="utf-8") as f:
        old = json.load(f)

    for row in old.get("results", []):
        mcap = row.get("mcap", "")
        s = mcap.upper().replace(",", "")
        try:
            if s.endswith("B"):
                row["mcap_m"] = float(s[:-1]) * 1000
            elif s.endswith("M"):
                row["mcap_m"] = float(s[:-1])
            else:
                row["mcap_m"] = 0
        except ValueError:
            row["mcap_m"] = 0

    data = {
        "meta": {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": "seed",
            "refresh_schedule": "Every Friday 7:00 AM US Eastern",
            "next_refresh": next_friday_refresh().isoformat(),
        },
        "screener": {
            **old.get("screener", {}),
            "sp500_forward_pe": 22.06,
            "sp500_forward_pe_source": "MacroMicro (Jun 2026)",
        },
        "results": old.get("results", []),
        "near_misses": [],
        "counts": {
            "universe": int(old.get("screener", {}).get("finviz_total", 290)),
            "passing": len(old.get("results", [])),
            "near_misses": 0,
        },
    }

    data = enrich_results(data)
    save_data(data)
    print(f"Seeded {DATA_FILE} with {len(data['results'])} stocks")


if __name__ == "__main__":
    main()