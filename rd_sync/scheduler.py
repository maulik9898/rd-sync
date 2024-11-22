import asyncio
from datetime import datetime
from typing import Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import undefined
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from rd_sync.config import Settings, SyncConfig
from rd_sync.log_config import get_logger
from rd_sync.sync import RealDebridSync


class SyncScheduler:
    """Manages scheduled sync jobs using APScheduler."""

    def __init__(self, settings: Settings):
        """Initialize the scheduler with settings."""
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self._active_jobs: Dict[str, RealDebridSync] = {}
        self.log = get_logger("scheduler")
        self._shutdown_event = asyncio.Event()
        self._cleanup_timeout = 5.0  # seconds

    async def add_sync_job(self, name: str, config: SyncConfig) -> None:
        """Add a new sync job to the scheduler."""
        job_log = get_logger(name)

        if not config.enabled:
            job_log.info("job.skipped", reason="disabled")
            return

        source_account = self.settings.accounts.get(config.source)
        dest_account = self.settings.accounts.get(config.destination)

        if not source_account or not dest_account:
            job_log.error("job.config_invalid", error="Invalid account configuration")
            return

        sync = RealDebridSync(
            source_account.token,
            name,
            dest_account.token,
            self.settings,
            config.dry_run,
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

        job_log.info(
            "job.added",
            name=name,
            schedule_type=config.schedule.type,
            schedule_value=config.schedule.value,
            next_run=job.next_run_time,
            source=config.source,
            destination=config.destination,
        )

    async def start(self) -> None:
        """Start the scheduler and add configured sync jobs."""
        self.log.info("scheduler.starting")

        for name, config in self.settings.syncs.items():
            await self.add_sync_job(name, config)

        self.scheduler.start()
        active_jobs = len(self._active_jobs)
        self.log.info("scheduler.started", active_jobs=active_jobs)

    async def stop(self) -> None:
        """Stop the scheduler and cleanup resources."""
        if not self.scheduler.running:
            return

        self.log.info("scheduler.stopping")

        # Pause the scheduler first to prevent new jobs from starting
        self.scheduler.pause()

        try:
            # Remove all jobs first to prevent them from being rescheduled
            self.scheduler.remove_all_jobs()

            # Shutdown the scheduler
            self.scheduler.shutdown(wait=False)

            # Close all active jobs with timeout
            close_tasks = []
            for name, sync in self._active_jobs.items():
                task = asyncio.create_task(self._safe_close_job(name, sync))
                close_tasks.append(task)

            if close_tasks:
                # Wait for all jobs to close with timeout
                await asyncio.wait(close_tasks, timeout=self._cleanup_timeout)

            self._active_jobs.clear()

        except Exception as e:
            self.log.error("scheduler.stop_error", error=str(e))
        finally:
            self.log.info("scheduler.stopped")
            self._shutdown_event.set()

    async def _safe_close_job(self, name: str, sync: RealDebridSync) -> None:
        """Safely close a job with error handling."""
        try:
            await sync.close()
            self.log.debug("job.closed", job=name)
        except Exception as e:
            self.log.error("job.close_failed", job=name, error=str(e))

    async def wait_for_shutdown(self) -> None:
        """Wait for scheduler shutdown to complete."""
        await self._shutdown_event.wait()

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        await self.wait_for_shutdown()
