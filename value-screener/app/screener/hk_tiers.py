"""Hong Kong quality tier classification."""
from __future__ import annotations

from app.config_hk import HK_TIER_1, HK_TIER_2, HK_TIER_NOTES
from app.screener.flow import FLOW_NOTE, attach_weekly_flows

TIER_META = {
    1: {
        "label": "Tier 1",
        "title": "Best Risk/Reward",
        "description": (
            "Large-cap SOE banks, oil, telcos, and insurers — "
            "the core of HK deep-value investing."
        ),
    },
    2: {
        "label": "Tier 2",
        "title": "Solid HK Names",
        "description": "Established H-shares with liquidity and recognizable franchises.",
    },
    3: {
        "label": "Tier 3",
        "title": "Higher Risk",
        "description": "Smaller passers or cyclical names — verify balance sheet quality.",
    },
}


def classify_type(row: dict) -> str:
    text = f"{row.get('company', '')} {row.get('industry', '')}".lower()
    if "bank" in text:
        return "Bank"
    if "insurance" in text or "life" in text:
        return "Insurance"
    if "oil" in text or "petro" in text or "energy" in text or "coal" in text:
        return "Energy"
    if "telecom" in text or "mobile" in text or "unicom" in text:
        return "Telco"
    if "reit" in text or "property" in text or "land" in text:
        return "Property/REIT"
    if "port" in text:
        return "Infrastructure"
    return "Conglomerate/Other"


def assign_tier(row: dict) -> int:
    t = row["ticker"]
    if t in HK_TIER_1:
        return 1
    if t in HK_TIER_2:
        return 2
    mcap = row.get("mcap", "")
    if "M" in mcap.upper() and "B" not in mcap.upper():
        return 3
    return 2


def _merge_hk_flow_fields(data: dict) -> dict:
    need = [
        r for r in data.get("results", []) + data.get("near_misses", [])
        if not r.get("week_flow") or r.get("week_flow") == "—"
    ]
    if not need:
        return data
    seen: set[str] = set()
    unique = []
    for row in need:
        if row["ticker"] not in seen:
            seen.add(row["ticker"])
            unique.append(row)
    flowed = attach_weekly_flows(unique, market="hk")
    by_ticker = {r["ticker"]: r for r in flowed}
    out = dict(data)
    out.setdefault("screener", {})["week_flow_note"] = FLOW_NOTE
    for key in ("results", "near_misses"):
        out[key] = [
            {**row, **{k: by_ticker[row["ticker"]][k] for k in ("week_flow_n", "week_flow", "week_flow_ccy")
                       if row["ticker"] in by_ticker}}
            for row in data.get(key, [])
        ]
    return out


def enrich_hk_results(data: dict) -> dict:
    data = _merge_hk_flow_fields(data)
    tiers: dict[int, list] = {1: [], 2: [], 3: []}
    enriched = []
    for row in data.get("results", []):
        tier = assign_tier(row)
        entry = {
            **row,
            "tier": tier,
            "type": classify_type(row),
            "note": HK_TIER_NOTES.get(row["ticker"], ""),
            "finviz_url": row.get("quote_url", ""),
            "stats_url": row.get("stats_url", ""),
        }
        enriched.append(entry)
        tiers[tier].append(entry)

    shortlist = {
        str(k): {**TIER_META[k], "stocks": tiers[k]}
        for k in (1, 2, 3)
    }
    return {**data, "results": enriched, "shortlist": shortlist}