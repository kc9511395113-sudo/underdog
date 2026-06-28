"""Finviz scraper: Forward P/E < 8, P/B < 0.8, Dividend > 5%."""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape

from app.config import (
    DATA_DIR,
    DIVIDEND_MIN,
    FILTERS,
    FINVIZ_BASE,
    FORWARD_PE_MAX,
    PB_MAX,
    RELAXED_FORWARD_PE_MAX,
    RELAXED_PB_MAX,
)
from app.screener.flow import FLOW_NOTE, attach_weekly_flows

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finviz.com/screener.ashx",
}


def clean(cell: str) -> str:
    cell = re.sub(r"<[^>]+>", "", cell)
    return unescape(re.sub(r"\s+", " ", cell)).strip()


def fetch(url: str, retries: int = 5) -> str:
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(3 + attempt * 4)
                continue
            raise
    return ""


def parse_valuation_page(html: str) -> list[dict]:
    rows = []
    for row_html in re.findall(
        r'<tr[^>]*class="styled-row[^"]*"[^>]*>(.*?)</tr>', html, re.S
    ):
        ticker_m = re.search(r'class="tab-link">([A-Z][A-Z0-9\.]*)</a>', row_html)
        if not ticker_m:
            continue
        cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]
        if len(cells) < 8:
            continue
        industry_m = re.search(r'data-boxover-industry="([^"]*)"', row_html)
        company_m = re.search(r'data-boxover-company="([^"]*)"', row_html)
        rows.append({
            "ticker": ticker_m.group(1),
            "company": unescape(company_m.group(1)) if company_m else "",
            "industry": unescape(industry_m.group(1)) if industry_m else "",
            "mcap": cells[2],
            "pe": cells[3],
            "fpe": cells[4],
            "peg": cells[5],
            "ps": cells[6],
            "pb": cells[7],
            "price": cells[15] if len(cells) > 15 else "",
        })
    return rows


def parse_dividend_page(html: str) -> dict[str, str]:
    """v=161 view has Dividend column at index 3."""
    out: dict[str, str] = {}
    for row_html in re.findall(
        r'<tr[^>]*class="styled-row[^"]*"[^>]*>(.*?)</tr>', html, re.S
    ):
        ticker_m = re.search(r'class="tab-link">([A-Z][A-Z0-9\.]*)</a>', row_html)
        if not ticker_m:
            continue
        cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]
        if len(cells) < 4:
            continue
        out[ticker_m.group(1)] = cells[3]
    return out


def to_float(val, default: float = 999.0) -> float:
    if val in ("", "-", "n/a", None):
        return default
    try:
        return float(str(val).replace("%", "").replace(",", ""))
    except ValueError:
        return default


def parse_mcap_millions(mcap: str) -> float:
    """Convert Finviz market cap string to millions USD."""
    if not mcap or mcap == "-":
        return 0.0
    s = mcap.upper().replace(",", "").strip()
    try:
        if s.endswith("B"):
            return float(s[:-1]) * 1000
        if s.endswith("M"):
            return float(s[:-1])
        if s.endswith("K"):
            return float(s[:-1]) / 1000
        return float(s)
    except ValueError:
        return 0.0


def scrape_finviz(progress=None) -> tuple[list[dict], dict[str, str], str]:
    def log(msg: str) -> None:
        if progress:
            progress(msg)

    all_val: list[dict] = []
    seen: set[str] = set()
    total = "?"

    for r in range(1, 601, 20):
        url = f"{FINVIZ_BASE}?v=121&f={FILTERS}&ft=4&o=forwardpe&r={r}"
        html = fetch(url)
        if r == 1:
            m = re.search(r"#1 / (\d+) Total", html)
            total = m.group(1) if m else "?"
            log(f"Finviz universe: {total} stocks")
        page = parse_valuation_page(html)
        if not page:
            break
        for row in page:
            if row["ticker"] not in seen:
                seen.add(row["ticker"])
                all_val.append(row)
        log(f"Valuation page {r}: {len(all_val)} total")
        time.sleep(2.0)

    div_info: dict[str, str] = {}
    for r in range(1, 601, 20):
        url = f"{FINVIZ_BASE}?v=161&f={FILTERS}&ft=4&o=-dividend&r={r}"
        html = fetch(url)
        page = parse_dividend_page(html)
        if not page:
            break
        div_info.update(page)
        log(f"Dividend page {r}: {len(div_info)} total")
        time.sleep(1.5)

    return all_val, div_info, total


def apply_filters(
    all_val: list[dict],
    div_info: dict[str, str],
    fpe_max: float,
    pb_max: float,
    div_min: float,
) -> list[dict]:
    results = []
    for row in all_val:
        div_raw = div_info.get(row["ticker"], "")
        fpe = to_float(row["fpe"])
        pb = to_float(row["pb"])
        div = to_float(div_raw, 0.0)
        if fpe < fpe_max and pb < pb_max and div > div_min:
            results.append({
                **row,
                "dividend": div_raw,
                "fpe_n": round(fpe, 2),
                "pb_n": round(pb, 2),
                "div_n": round(div, 2),
                "mcap_m": round(parse_mcap_millions(row["mcap"]), 2),
            })
    results.sort(key=lambda x: x["fpe_n"])
    return results


def run_screen(progress=None) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_val, div_info, total = scrape_finviz(progress=progress)

    strict = apply_filters(
        all_val, div_info, FORWARD_PE_MAX, PB_MAX, DIVIDEND_MIN
    )
    near_misses = []
    strict_tickers = {r["ticker"] for r in strict}
    relaxed = apply_filters(
        all_val, div_info, RELAXED_FORWARD_PE_MAX, RELAXED_PB_MAX, DIVIDEND_MIN
    )
    for row in relaxed:
        if row["ticker"] not in strict_tickers and row["mcap_m"] >= 2000:
            near_misses.append(row)
    near_misses.sort(key=lambda x: x["fpe_n"])

    if progress:
        progress("Fetching weekly net cash inflow (US)...")
    flow_rows = attach_weekly_flows(
        strict + near_misses[:10], market="us", progress=progress
    )
    flow_by_ticker = {r["ticker"]: r for r in flow_rows}
    strict = [flow_by_ticker.get(r["ticker"], r) for r in strict]
    near_misses = [flow_by_ticker.get(r["ticker"], r) for r in near_misses]

    now = datetime.now(timezone.utc).isoformat()
    return {
        "meta": {
            "last_updated": now,
            "source": "finviz",
            "refresh_schedule": "Every Friday 7:00 AM US Eastern",
        },
        "screener": {
            "forward_pe_max": FORWARD_PE_MAX,
            "pb_max": PB_MAX,
            "dividend_min_pct": DIVIDEND_MIN,
            "finviz_url": (
                f"https://finviz.com/screener.ashx?v=121&f={FILTERS}&ft=4&o=forwardpe"
            ),
            "finviz_total": total,
            "sp500_forward_pe": 22.06,
            "sp500_forward_pe_source": "MacroMicro (Jun 2026)",
            "week_flow_note": FLOW_NOTE,
        },
        "results": strict,
        "near_misses": near_misses[:10],
        "counts": {
            "universe": len(all_val),
            "passing": len(strict),
            "near_misses": len(near_misses),
        },
    }