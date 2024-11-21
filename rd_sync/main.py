import asyncio

from rd_sync.config import Settings
from rd_sync.log_config import logger, setup_logging
from rd_sync.scheduler import SyncScheduler

# Initialize logging
setup_logging()


async def main():
    """Main entry point for the application."""
    try:
        settings = Settings()

        async with SyncScheduler(settings) as _:
            # Keep the main task running
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("════════════════════════════════════════════")
        logger.warning("⚡ Gracefully shutting down RD-Sync service...")
        logger.info("════════════════════════════════════════════")
    except Exception as e:
        logger.exception(e)
    finally:
        logger.info("shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
