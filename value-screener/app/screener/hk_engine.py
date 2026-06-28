"""Hong Kong stock screener via stockanalysis.com (Finviz does not cover HKEX)."""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from app.config_hk import (
    DIVIDEND_MIN,
    FORWARD_PE_MAX,
    HK_LIST_URL,
    HK_SCAN_LIMIT,
    HK_STATS_URL,
    HANG_SENG_FORWARD_PE,
    HANG_SENG_SOURCE,
    PB_MAX,
    RELAXED_FORWARD_PE_MAX,
    RELAXED_PB_MAX,
)
from app.screener.flow import FLOW_NOTE, attach_weekly_flows

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(2 + attempt * 3)
                continue
            raise
    return ""


def fetch_hk_symbols(limit: int = HK_SCAN_LIMIT) -> list[dict]:
    html = fetch(HK_LIST_URL)
    rows = []
    seen: set[str] = set()
    pattern = (
        r'/quote/hkg/(\d{4})/">?\d{0,4}</a>.*?'
        r'<td class="slw[^"]*">([^<]+)</td>.*?'
        r'<td[^>]*>([\d.,]+[TBMK]?)</td>'
    )
    for m in re.finditer(pattern, html, re.S):
        sym, company, mcap = m.group(1), m.group(2).strip(), m.group(3).strip()
        if sym in seen:
            continue
        seen.add(sym)
        rows.append({"ticker": sym, "company": company, "mcap": mcap})
        if len(rows) >= limit:
            break

    if len(rows) < 50:
        for sym in re.findall(r"/quote/hkg/(\d{4})/", html):
            if sym not in seen:
                seen.add(sym)
                rows.append({"ticker": sym, "company": "", "mcap": ""})
            if len(rows) >= limit:
                break
    return rows


def _parse_metric(label: str, html: str) -> str | None:
    m = re.search(
        rf"{re.escape(label)}.*?<td[^>]*title=\"([^\"]+)\"[^>]*>([^<]*)</td>",
        html,
        re.S,
    )
    if m:
        return (m.group(1) or m.group(2)).strip()
    m = re.search(
        rf"{re.escape(label)}.*?<td[^>]*class=\"[^\"]*text-right[^\"]*\"[^>]*>([^<]+)</td>",
        html,
        re.S,
    )
    return m.group(1).strip() if m else None


def _parse_company(html: str, symbol: str) -> str:
    t = re.search(r"<title>([^<]+)</title>", html)
    if t:
        title = t.group(1).replace("&amp;", "&")
        title = re.sub(r"\s*Statistics.*$", "", title, flags=re.I)
        title = re.sub(rf"\s*\(HKG:{symbol}\)\s*", "", title, flags=re.I)
        return title.strip()
    return symbol


def _to_float(val, default: float = 999.0) -> float:
    if not val or val in ("-", "n/a", "Upgrade"):
        return default
    try:
        return float(str(val).replace("%", "").replace(",", "").replace("HKD", "").strip())
    except ValueError:
        return default


def fetch_hk_stats(symbol: str) -> dict | None:
    html = fetch(HK_STATS_URL.format(symbol=symbol))
    if "Statistics" not in html and "Valuation" not in html:
        return None

    fpe = _to_float(_parse_metric("Forward PE", html))
    pb = _to_float(_parse_metric("PB Ratio", html))
    div = _to_float(_parse_metric("Dividend Yield", html), 0.0)
    pe = _parse_metric("PE Ratio", html) or "-"
    mcap_raw = _parse_metric("Market Cap", html) or ""
    mcap = _format_mcap(mcap_raw)

    return {
        "ticker": symbol,
        "company": _parse_company(html, symbol),
        "industry": "",
        "mcap": mcap,
        "pe": pe,
        "fpe": str(fpe) if fpe < 900 else "-",
        "pb": str(pb) if pb < 900 else "-",
        "dividend": f"{div}%" if div else "0%",
        "fpe_n": round(fpe, 2) if fpe < 900 else 999.0,
        "pb_n": round(pb, 2) if pb < 900 else 999.0,
        "div_n": round(div, 2),
        "stats_url": HK_STATS_URL.format(symbol=symbol),
        "quote_url": f"https://stockanalysis.com/quote/hkg/{symbol}/",
    }


def _screen_batch(symbols: list[dict], progress=None) -> list[dict]:
    results: list[dict] = []
    total = len(symbols)

    def _merge(base: dict, stats: dict | None) -> dict | None:
        if not stats:
            return None
        return {**base, **stats, "company": stats.get("company") or base.get("company", "")}

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(fetch_hk_stats, row["ticker"]): row for row in symbols
        }
        for i, fut in enumerate(as_completed(futures), 1):
            base = futures[fut]
            try:
                stats = fut.result()
                merged = _merge(base, stats)
                if merged:
                    results.append(merged)
            except Exception:
                pass
            if progress and i % 25 == 0:
                progress(f"HK stats: {i}/{total}")
            time.sleep(0.05)
    return results


def apply_hk_filters(rows: list[dict], fpe_max: float, pb_max: float, div_min: float) -> list[dict]:
    out = [
        r for r in rows
        if r["fpe_n"] < fpe_max and r["pb_n"] < pb_max and r["div_n"] > div_min
    ]
    out.sort(key=lambda x: x["fpe_n"])
    return out


def run_hk_screen(progress=None) -> dict:
    if progress:
        progress("Fetching HKEX stock list...")
    symbols = fetch_hk_symbols()
    if progress:
        progress(f"Scanning {len(symbols)} HK stocks for valuation data...")

    all_stats = _screen_batch(symbols, progress=progress)
    strict = apply_hk_filters(all_stats, FORWARD_PE_MAX, PB_MAX, DIVIDEND_MIN)

    strict_tickers = {r["ticker"] for r in strict}
    near_misses = []
    for row in all_stats:
        if row["ticker"] in strict_tickers:
            continue
        if (
            row["fpe_n"] < RELAXED_FORWARD_PE_MAX
            and row["pb_n"] < RELAXED_PB_MAX
            and row["div_n"] > DIVIDEND_MIN
            and _mcap_billions(row.get("mcap", "")) >= 50
        ):
            near_misses.append(row)
    near_misses.sort(key=lambda x: x["fpe_n"])

    if progress:
        progress("Fetching weekly net cash inflow (HK)...")
    flow_rows = attach_weekly_flows(
        strict + near_misses[:12], market="hk", progress=progress
    )
    flow_by_ticker = {r["ticker"]: r for r in flow_rows}
    strict = [flow_by_ticker.get(r["ticker"], r) for r in strict]
    near_misses = [flow_by_ticker.get(r["ticker"], r) for r in near_misses]

    now = datetime.now(timezone.utc).isoformat()
    return {
        "meta": {
            "last_updated": now,
            "source": "stockanalysis.com",
            "market": "Hong Kong (HKEX)",
            "refresh_schedule": "Every Friday 7:00 AM US Eastern",
            "scan_universe": len(symbols),
        },
        "screener": {
            "forward_pe_max": FORWARD_PE_MAX,
            "pb_max": PB_MAX,
            "dividend_min_pct": DIVIDEND_MIN,
            "list_url": HK_LIST_URL,
            "hang_seng_forward_pe": HANG_SENG_FORWARD_PE,
            "hang_seng_source": HANG_SENG_SOURCE,
            "week_flow_note": FLOW_NOTE,
        },
        "results": strict,
        "near_misses": near_misses[:12],
        "counts": {
            "universe": len(symbols),
            "scanned": len(all_stats),
            "passing": len(strict),
            "near_misses": len(near_misses),
        },
    }


def _format_mcap(raw: str) -> str:
    raw = raw.replace(",", "").strip()
    try:
        val = float(raw)
        if val >= 1e12:
            return f"{val / 1e12:.2f}T"
        if val >= 1e9:
            return f"{val / 1e9:.2f}B"
        if val >= 1e6:
            return f"{val / 1e6:.2f}M"
    except ValueError:
        pass
    return raw


def _mcap_billions(mcap: str) -> float:
    s = mcap.upper().replace(",", "").strip()
    try:
        if s.endswith("T"):
            return float(s[:-1]) * 1000
        if s.endswith("B"):
            return float(s[:-1])
        if s.endswith("M"):
            return float(s[:-1]) / 1000
    except ValueError:
        pass
    return 0.0