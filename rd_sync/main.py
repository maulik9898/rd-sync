import asyncio
import signal
from rd_sync.config import Settings
from rd_sync.log_config import get_logger, setup_logging
from rd_sync.scheduler import SyncScheduler

# Initialize logging
settings = Settings()
setup_logging()
logger = get_logger()


async def main():
    """Main entry point."""

    # Create and start scheduler
    scheduler = None
    try:
        logger.info("app.starting", version="1.0.0")

        # Setup signal handlers
        loop = asyncio.get_running_loop()
        scheduler = SyncScheduler(settings)

        def handle_shutdown(sig):
            logger.warning(
                "shutdown.initiated", msg="Gracefully shutting down RD-Sync service"
            )
            asyncio.create_task(scheduler.stop())

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s))

        async with scheduler:
            # Wait for shutdown signal
            await scheduler.wait_for_shutdown()

    except Exception as e:
        logger.error("main.error", error=str(e))
        raise
    finally:
        logger.info("shutdown.complete")


if __name__ == "__main__":
    asyncio.run(main())
