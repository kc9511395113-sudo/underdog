import json
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import DATA_FILE, REFRESH_DAY, REFRESH_HOUR, REFRESH_MINUTE, REFRESH_TIMEZONE
from app.config_hk import HK_DATA_FILE
from app.screener import enrich_results, run_screen
from app.screener.hk_engine import run_hk_screen
from app.screener.hk_tiers import enrich_hk_results

_lock_us = threading.Lock()
_lock_hk = threading.Lock()
_refreshing_us = False
_refreshing_hk = False


def _load(path) -> dict | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def next_friday_refresh() -> datetime:
    tz = ZoneInfo(REFRESH_TIMEZONE)
    now = datetime.now(tz)
    days_ahead = (4 - now.weekday()) % 7
    candidate = now.replace(
        hour=REFRESH_HOUR, minute=REFRESH_MINUTE, second=0, microsecond=0
    ) + timedelta(days=days_ahead)
    if days_ahead == 0 and candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def refresh_screen(force: bool = False) -> dict:
    global _refreshing_us
    with _lock_us:
        if _refreshing_us and not force:
            existing = _load(DATA_FILE)
            if existing:
                return existing
        _refreshing_us = True
    try:
        raw = run_screen()
        data = enrich_results(raw)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save(DATA_FILE, data)
        return data
    finally:
        with _lock_us:
            _refreshing_us = False


def refresh_hk_screen(force: bool = False) -> dict:
    global _refreshing_hk
    with _lock_hk:
        if _refreshing_hk and not force:
            existing = _load(HK_DATA_FILE)
            if existing:
                return existing
        _refreshing_hk = True
    try:
        raw = run_hk_screen()
        data = enrich_hk_results(raw)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save(HK_DATA_FILE, data)
        return data
    finally:
        with _lock_hk:
            _refreshing_hk = False


def refresh_all_screens(force: bool = True) -> None:
    refresh_screen(force=force)
    refresh_hk_screen(force=force)


def get_screen_data() -> dict:
    data = _load(DATA_FILE)
    if data is None:
        try:
            data = refresh_screen(force=True)
        except Exception as exc:
            raise RuntimeError(
                "No US screener data. Run: python seed_data.py"
            ) from exc
    if "shortlist" not in data:
        data = enrich_results(data)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save(DATA_FILE, data)
    data.setdefault("meta", {})
    data["meta"].setdefault("next_refresh", next_friday_refresh().isoformat())
    return data


def get_hk_screen_data() -> dict:
    data = _load(HK_DATA_FILE)
    if data is None:
        try:
            data = refresh_hk_screen(force=True)
        except Exception as exc:
            raise RuntimeError(
                "No HK screener data. Run: python seed_hk_data.py"
            ) from exc
    if "shortlist" not in data:
        data = enrich_hk_results(data)
        data["meta"]["next_refresh"] = next_friday_refresh().isoformat()
        _save(HK_DATA_FILE, data)
    data.setdefault("meta", {})
    data["meta"].setdefault("next_refresh", next_friday_refresh().isoformat())
    return data


def is_refreshing(market: str = "us") -> bool:
    if market == "hk":
        return _refreshing_hk
    return _refreshing_us