from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.persistence.db import SessionLocal
from app.persistence.models import ScheduleJob

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
PRESET_CRON = {
    "hourly": "0 * * * *",
    "daily": "0 2 * * *",
    "weekly": "0 3 * * 1",
}


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(_tick_all, "interval", minutes=1, id="schedule-tick", replace_existing=True)
    _scheduler.start()
    logger.info("APScheduler started")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None


def resolve_cron(expr: str) -> str:
    e = (expr or "daily").strip().lower()
    return PRESET_CRON.get(e, expr.strip())


def due_now(job: ScheduleJob, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    cron = resolve_cron(job.cron)
    try:
        trigger = CronTrigger.from_crontab(cron, timezone="UTC")
    except Exception:  # noqa: BLE001
        logger.warning("invalid cron for job %s: %s", job.id, cron)
        return False
    aware_now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now
    prev = trigger.get_prev_fire_time(None, aware_now)
    if prev is None:
        return False
    prev_naive = prev.replace(tzinfo=None)
    delta = (now - prev_naive).total_seconds()
    if delta < 0 or delta >= 60:
        return False
    last = job.last_run_at
    if last is not None:
        last_naive = last.replace(tzinfo=None) if getattr(last, "tzinfo", None) else last
        if (now - last_naive).total_seconds() < 90:
            return False
    return True


def _tick_all() -> None:
    db = SessionLocal()
    try:
        jobs = db.query(ScheduleJob).filter(ScheduleJob.enabled.is_(True)).all()
        for job in jobs:
            if not due_now(job):
                continue
            asyncio.run(_run_job(db, job))
    except Exception:  # noqa: BLE001
        logger.exception("schedule tick failed")
    finally:
        db.close()


async def _run_job(db: Session, job: ScheduleJob) -> None:
    from app.services.runner import run_regression

    logger.info("scheduled regression job=%s pipeline=%s", job.id, job.pipeline_id)
    try:
        result = await run_regression(
            db,
            project_id=job.project_id,
            pipeline_id=job.pipeline_id,
            trigger=f"schedule:{job.id}",
        )
        job.last_run_at = datetime.utcnow()
        job.last_status = result.get("status") or "DONE"
        job.last_summary_json = result.get("summary") or {}
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("scheduled run failed job=%s", job.id)
        job.last_run_at = datetime.utcnow()
        job.last_status = "FAILED"
        job.last_summary_json = {"error": str(exc)}
        db.commit()
