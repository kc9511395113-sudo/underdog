"""Data layer for Streamlit — reuses existing screener engines."""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import DATA_FILE, REFRESH_HOUR, REFRESH_MINUTE, REFRESH_TIMEZONE
from app.config_hk import HK_DATA_FILE
from app.screener import enrich_results, run_screen
from app.screener.hk_engine import run_hk_screen
from app.screener.hk_tiers import enrich_hk_results
from app.storage import next_friday_refresh


def _load_json(path) -> dict | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def last_friday_refresh_cutoff() -> datetime:
    """Most recent scheduled refresh moment (Friday 7:00 AM US Eastern)."""
    from datetime import timedelta

    tz = ZoneInfo(REFRESH_TIMEZONE)
    now = datetime.now(tz)
    candidate = now.replace(
        hour=REFRESH_HOUR, minute=REFRESH_MINUTE, second=0, microsecond=0
    )
    candidate -= timedelta(days=(candidate.weekday() - 4) % 7)
    if candidate > now:
        candidate -= timedelta(days=7)
    return candidate


def needs_scheduled_refresh(data: dict | None) -> bool:
    if not data or "meta" not in data:
        return True
    last = data["meta"].get("last_updated")
    if not last:
        return True
    try:
        updated = datetime.fromisoformat(last)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=ZoneInfo("UTC"))
        cutoff = last_friday_refresh_cutoff()
        return updated.astimezone(cutoff.tzinfo) < cutoff
    except ValueError:
        return True


def get_us_data(*, force_refresh: bool = False) -> dict:
    data = _load_json(DATA_FILE)
    if force_refresh or needs_scheduled_refresh(data):
        raw = run_screen()
        data = enrich_results(raw)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save_json(DATA_FILE, data)
    elif data and "shortlist" not in data:
        data = enrich_results(data)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save_json(DATA_FILE, data)
    if data:
        data.setdefault("meta", {})
        data["meta"].setdefault("next_refresh", next_friday_refresh().isoformat())
    return data or {}


def get_hk_data(*, force_refresh: bool = False) -> dict:
    data = _load_json(HK_DATA_FILE)
    if force_refresh or needs_scheduled_refresh(data):
        raw = run_hk_screen()
        data = enrich_hk_results(raw)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save_json(HK_DATA_FILE, data)
    elif data and "shortlist" not in data:
        data = enrich_hk_results(data)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save_json(HK_DATA_FILE, data)
    if data:
        data.setdefault("meta", {})
        data["meta"].setdefault("next_refresh", next_friday_refresh().isoformat())
    return data or {}