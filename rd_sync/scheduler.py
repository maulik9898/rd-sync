from datetime import datetime
from typing import Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import undefined
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from rd_sync.config import Settings, SyncConfig
from rd_sync.log_config import logger
from rd_sync.sync import RealDebridSync

log = logger


class SyncScheduler:
    """Manages scheduled sync jobs using APScheduler."""

    def __init__(self, settings: Settings):
        """Initialize the scheduler with settings."""
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self._active_jobs: Dict[str, RealDebridSync] = {}

    async def add_sync_job(self, name: str, config: SyncConfig) -> None:
        """Add a new sync job to the scheduler."""
        job_log = log.bind(job=name)

        if not config.enabled:
            job_log.info("job_skipped", reason="disabled")
            return

        source_account = self.settings.accounts.get(config.source)
        dest_account = self.settings.accounts.get(config.destination)

        if not source_account or not dest_account:
            job_log.error("job_config_invalid", error="Invalid account configuration")
            return

        sync = RealDebridSync(
            source_account.token, name, dest_account.token, self.settings
        )
        self._active_jobs[name] = sync

        next_run_time = undefined
        if config.schedule.type == "interval":
            trigger = IntervalTrigger(seconds=int(config.schedule.value))
            next_run_time = datetime.now()
        else:  # cron
            trigger = CronTrigger.from_crontab(config.schedule.value)

        job = self.scheduler.add_job(
            sync.sync,
            trigger=trigger,
            id=name,
            name=name,
            next_run_time=next_run_time,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        schedule_type = "interval" if config.schedule.type == "interval" else "cron"
        job_log.info(
            "job_added",
            schedule_type=schedule_type,
            schedule_value=config.schedule.value,
            next_run=job.next_run_time.isoformat(),
        )

    async def start(self) -> None:
        """Start the scheduler and add configured sync jobs."""
        log.info("scheduler_starting")

        for name, config in self.settings.syncs.items():
            await self.add_sync_job(name, config)

        self.scheduler.start()
        log.info("scheduler_started")

    async def stop(self) -> None:
        """Stop the scheduler and cleanup resources."""
        self.scheduler.shutdown()
        for sync in self._active_jobs.values():
            await sync.close()
        self._active_jobs.clear()
        log.info("scheduler_stopped")

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
