"""Sync module for Real-Debrid synchronization."""

from typing import Optional

from rd_sync.client import RealDebridClient, RealDebridError
from rd_sync.config import Settings
from rd_sync.log_config import logger

log = logger


class RealDebridSync:
    """Real-Debrid synchronization manager."""

    def __init__(
        self,
        source_api_key: str,
        job_name: str,
        destination_api_key: str,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or Settings()
        self.source = RealDebridClient(source_api_key, self.settings)
        self.destination = RealDebridClient(destination_api_key, self.settings)
        self.log = log.bind(job=job_name)

    async def sync(self):
        """Synchronize torrents from source to destination."""

        self.log.info("sync.started")

        try:
            # Fetch all torrents
            self.log.info(
                "torrents.fetching",
                msg="📥 Fetching torrents from source and destination...",
            )
            source_torrents = await self.source.get_all_torrents()
            destination_torrents = await self.destination.get_all_torrents()

            # Create hash sets for comparison
            source_hashes = {t.hash: t for t in source_torrents.torrents}
            dest_hashes = {t.hash: t for t in destination_torrents.torrents}
            torrents_to_sync = set(source_hashes.keys()) - set(dest_hashes.keys())

            # Analysis summary
            self.log.info(
                "sync.analysis",
                source_count=len(source_torrents),
                dest_count=len(destination_torrents),
                sync_count=len(torrents_to_sync),
            )

            if not torrents_to_sync:
                self.log.info("sync.complete", message="All torrents are in sync")
                return

            success_count = error_count = 0

            self.log.info("transfer.started", count=len(torrents_to_sync))

            for hash in torrents_to_sync:
                torrent = source_hashes[hash]
                try:
                    source_info = await self.source.get_torrent_info(torrent.id)
                    selected_files = [
                        f.id for f in source_info.files if f.selected == 1
                    ]

                    total_files = len(source_info.files)
                    selected_count = len(selected_files)
                    progress = (
                        (success_count + error_count + 1) / len(torrents_to_sync) * 100
                    )

                    await self.destination.add_magnet(hash, selected_files)
                    success_count += 1
                    self.log.info(
                        "torrent.added",
                        progress=f"{progress:.0f}%",
                        msg="✅ Torrent added successfully",
                        name=torrent.filename,
                        current=success_count + error_count,
                        total=len(torrents_to_sync),
                        files=f"{selected_count}/{total_files}",
                        hash=hash,
                    )

                except Exception as e:
                    error_count += 1
                    self.log.error(
                        "torrent.failed", hash=hash, name=torrent.filename, error=str(e)
                    )

            self.log.info(
                "sync.complete",
                success_count=success_count,
                error_count=error_count,
                total=len(torrents_to_sync),
            )

        except Exception as e:
            self.log.error("sync.failed", error=str(e))
            raise RealDebridError("Synchronization failed") from e

    async def close(self):
        """Close both source and destination clients."""
        await self.source.close()
        await self.destination.close()

    async def __aenter__(self):
        """Async context manager enter."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
