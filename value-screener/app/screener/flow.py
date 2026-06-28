"""Weekly net cash inflow from market trading (past 5 sessions via Yahoo Finance)."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

FLOW_NOTE = (
    "Sum of estimated daily net buy turnover over the past 5 trading sessions "
    "(money-flow method: turnover × (2×Close − High − Low) / (High − Low)). "
    "Proxy for net cash inflow, not official exchange fund-flow data."
)


def yahoo_symbol(ticker: str, market: str = "us") -> str:
    if market == "hk":
        return f"{ticker.zfill(4)}.HK"
    return ticker.upper()


def _daily_net_inflow(
    high: float | None,
    low: float | None,
    close: float | None,
    volume: float | None,
    prev_close: float | None = None,
) -> float:
    if None in (high, low, close, volume) or volume <= 0:
        return 0.0
    turnover = close * volume
    span = high - low
    if span > 0:
        return turnover * (2 * close - high - low) / span
    if prev_close is not None:
        return turnover if close >= prev_close else -turnover
    return 0.0


def _fetch_chart(symbol: str, retries: int = 3) -> dict | None:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?range=5d&interval=1d"
    )
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            results = payload.get("chart", {}).get("result") or []
            return results[0] if results else None
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(1.5 + attempt * 2)
                continue
            return None
        except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError):
            return None
    return None


def weekly_net_inflow(symbol: str) -> tuple[float | None, str]:
    """Return (numeric inflow in quote currency, display label)."""
    chart = _fetch_chart(symbol)
    if not chart:
        return None, "—"

    q = chart["indicators"]["quote"][0]
    highs = q.get("high") or []
    lows = q.get("low") or []
    closes = q.get("close") or []
    volumes = q.get("volume") or []

    total = 0.0
    prev_close: float | None = None
    for high, low, close, volume in zip(highs, lows, closes, volumes):
        if close is None:
            continue
        total += _daily_net_inflow(high, low, close, volume, prev_close)
        prev_close = close

    currency = (chart.get("meta") or {}).get("currency") or "USD"
    return round(total, 2), format_flow(total, currency)


def format_flow(value: float | None, currency: str = "USD") -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else "−"
    av = abs(value)
    prefix = "HK$" if currency == "HKD" else "$"
    if av >= 1e9:
        return f"{sign}{prefix}{av / 1e9:.2f}B"
    if av >= 1e6:
        return f"{sign}{prefix}{av / 1e6:.1f}M"
    if av >= 1e3:
        return f"{sign}{prefix}{av / 1e3:.0f}K"
    return f"{sign}{prefix}{av:.0f}"


def _attach_one(row: dict, market: str) -> dict:
    sym = yahoo_symbol(row["ticker"], market)
    flow_n, flow_label = weekly_net_inflow(sym)
    currency = "HKD" if market == "hk" else "USD"
    return {
        **row,
        "week_flow_n": flow_n,
        "week_flow": flow_label,
        "week_flow_ccy": currency,
    }


def attach_weekly_flows(
    rows: list[dict],
    *,
    market: str = "us",
    progress=None,
    max_workers: int = 6,
) -> list[dict]:
    if not rows:
        return rows

    def log(msg: str) -> None:
        if progress:
            progress(msg)

    out: list[dict | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_attach_one, row, market): i
            for i, row in enumerate(rows)
        }
        done = 0
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                out[idx] = fut.result()
            except Exception:
                out[idx] = {
                    **rows[idx],
                    "week_flow_n": None,
                    "week_flow": "—",
                    "week_flow_ccy": "HKD" if market == "hk" else "USD",
                }
            done += 1
            if done % 10 == 0 or done == len(rows):
                log(f"Weekly flow: {done}/{len(rows)}")
            time.sleep(0.08)
    return [r for r in out if r is not None]