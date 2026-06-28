import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import REFRESH_DAY, REFRESH_HOUR, REFRESH_MINUTE, REFRESH_TIMEZONE
from app.storage import refresh_all_screens

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _friday_job() -> None:
    logger.info("Friday scheduled refresh starting")
    try:
        refresh_all_screens(force=True)
        logger.info("Friday scheduled refresh completed (US + HK)")
    except Exception:
        logger.exception("Friday scheduled refresh failed")


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    tz = ZoneInfo(REFRESH_TIMEZONE)
    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(
        _friday_job,
        CronTrigger(
            day_of_week=REFRESH_DAY,
            hour=REFRESH_HOUR,
            minute=REFRESH_MINUTE,
            timezone=tz,
        ),
        id="friday_refresh",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started — refreshes every %s at %02d:%02d %s",
        REFRESH_DAY,
        REFRESH_HOUR,
        REFRESH_MINUTE,
        REFRESH_TIMEZONE,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None