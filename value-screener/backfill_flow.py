"""Backfill weekly net inflow into cached screener JSON (no full Finviz/HK rescan)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import DATA_FILE
from app.config_hk import HK_DATA_FILE
from app.screener.flow import FLOW_NOTE, attach_weekly_flows
from app.screener.hk_tiers import enrich_hk_results
from app.screener.tiers import enrich_results


def _needs_flow(row: dict) -> bool:
    return "week_flow" not in row or row.get("week_flow") in (None, "", "—")


def backfill_file(path: Path, *, market: str, enrich_fn) -> None:
    if not path.exists():
        print(f"Skip (missing): {path}")
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    targets: list[dict] = []
    seen: set[str] = set()
    for key in ("results", "near_misses"):
        for row in data.get(key, []):
            t = row["ticker"]
            if t not in seen and _needs_flow(row):
                seen.add(t)
                targets.append(row)

    if not targets:
        print(f"{path.name}: flow data already present")
        return

    print(f"{path.name}: fetching flow for {len(targets)} tickers...")
    enriched = attach_weekly_flows(targets, market=market, progress=print)
    by_ticker = {r["ticker"]: r for r in enriched}

    for key in ("results", "near_misses"):
        data[key] = [
            {**row, **{k: by_ticker[row["ticker"]][k] for k in ("week_flow_n", "week_flow", "week_flow_ccy")
                       if k in by_ticker.get(row["ticker"], {})}}
            if row["ticker"] in by_ticker else row
            for row in data.get(key, [])
        ]

    data.setdefault("screener", {})["week_flow_note"] = FLOW_NOTE
    data.setdefault("meta", {})["flow_backfilled"] = datetime.now(timezone.utc).isoformat()
    data = enrich_fn(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Updated {path}")


def main():
    backfill_file(DATA_FILE, market="us", enrich_fn=enrich_results)
    backfill_file(HK_DATA_FILE, market="hk", enrich_fn=enrich_hk_results)


if __name__ == "__main__":
    main()