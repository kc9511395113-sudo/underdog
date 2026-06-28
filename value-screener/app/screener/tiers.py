"""Quality tier classification matching the research shortlist."""
from __future__ import annotations

from app.config import BDC_KEYWORDS, MREIT_KEYWORDS, OPERATING_TICKERS, TIER_1, TIER_2
from app.screener.flow import FLOW_NOTE, attach_weekly_flows

TIER_META = {
    1: {
        "label": "Tier 1",
        "title": "Best Risk/Reward",
        "description": (
            "Larger, more established names among passers — operating businesses "
            "or institutional-quality yield vehicles."
        ),
    },
    2: {
        "label": "Tier 2",
        "title": "Solid Sector Names",
        "description": "Recognizable mid-cap BDCs, mREITs, and lenders with reasonable liquidity.",
    },
    3: {
        "label": "Tier 3",
        "title": "Higher Value-Trap Risk",
        "description": (
            "Micro-caps, ultra-high yields (15%+), or distressed niches. "
            "Proceed with extra caution."
        ),
    },
}

TIER_NOTES: dict[str, str] = {
    "CNXC": "Only large operating business at top of screen; turnaround story with heavy debt.",
    "RITM": "Largest mREIT in list; diversified mortgage platform; Strong Buy consensus.",
    "OTF": "Large BDC ($4.9B); Blue Owl sponsor; institutional-quality credit platform.",
    "FSK": "Deepest discount to book among large BDCs; negative TTM earnings — dividend risk.",
    "MFA": "Established mREIT; high yield; leveraged mortgage book.",
    "NMFC": "Well-known mid-cap BDC; middle-market private credit.",
    "CGBD": "Carlyle-sponsored BDC; secured lending focus.",
    "MFIC": "MidCap Financial; established BDC franchise.",
    "PFLT": "Floating-rate BDC; benefits from higher rate environment.",
    "PMT": "PennyMac mortgage REIT; agency/non-agency mix.",
    "CIM": "Chimera Investment; long-running mREIT.",
    "FBRT": "Commercial real estate finance; Franklin BSP platform.",
    "TRTX": "TPG commercial mortgage REIT.",
    "BRSP": "BrightSpire commercial real estate debt.",
    "GBLI": "Insurance operating company; lowest yield among passers.",
    "RWAY": "Ultra-high yield signals distress risk.",
    "MFIN": "Taxi medallion lender — highly specialized, risky niche.",
}


def classify_type(row: dict) -> str:
    ticker = row["ticker"]
    if ticker in OPERATING_TICKERS:
        return "Operating Co."
    text = f"{row.get('company', '')} {row.get('industry', '')}".lower()
    if any(k in text for k in MREIT_KEYWORDS):
        return "Mortgage REIT"
    if any(k in text for k in BDC_KEYWORDS):
        return "BDC"
    if "insurance" in text:
        return "Insurance"
    if "reit" in text or "real estate" in text:
        return "REIT"
    return "Financial"


def assign_tier(row: dict) -> int:
    ticker = row["ticker"]
    if ticker in TIER_1:
        return 1
    if ticker in TIER_2:
        return 2
    if row.get("div_n", 0) >= 18 or row.get("mcap_m", 0) < 150:
        return 3
    if row.get("mcap_m", 0) < 300:
        return 3
    return 2 if row.get("mcap_m", 0) >= 500 else 3


def _merge_flow_fields(data: dict, *, market: str) -> dict:
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
    flowed = attach_weekly_flows(unique, market=market)
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


def enrich_results(data: dict) -> dict:
    data = _merge_flow_fields(data, market="us")
    tiers: dict[int, list] = {1: [], 2: [], 3: []}
    enriched = []
    for row in data.get("results", []):
        tier = assign_tier(row)
        stock_type = classify_type(row)
        entry = {
            **row,
            "tier": tier,
            "type": stock_type,
            "note": TIER_NOTES.get(row["ticker"], ""),
            "finviz_url": f"https://finviz.com/quote.ashx?t={row['ticker']}",
            "stats_url": f"https://stockanalysis.com/stocks/{row['ticker'].lower()}/statistics/",
        }
        enriched.append(entry)
        tiers[tier].append(entry)

    shortlist = {
        str(k): {
            **TIER_META[k],
            "stocks": tiers[k],
        }
        for k in (1, 2, 3)
    }

    return {
        **data,
        "results": enriched,
        "shortlist": shortlist,
    }