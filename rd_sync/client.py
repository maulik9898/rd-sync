import asyncio
import logging
import math
import time
from typing import List, Optional

import httpx

from rd_sync.config import Settings
from rd_sync.models.torrents import TorrentInfo, TorrentList
from rd_sync.utils import RateLimiter


# Custom exceptions
class RealDebridAPIError(Exception):
    """Exception raised for Real-Debrid API errors with error codes."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        self.error_code = error_code
        # Map common error codes to human readable messages
        self.error_map = {
            35: "Infringing file",
            1: "Missing parameter",
            2: "Bad parameter value",
            3: "Unknown method",
            4: "Method not allowed",
            5: "Slow down",
            6: "Resource unreachable",
            7: "Resource not found",
            8: "Bad token",
            9: "Permission denied",
            10: "Two-Factor authentication needed",
            11: "Two-Factor authentication pending",
            12: "Invalid login",
            13: "Invalid password",
            14: "Account locked",
            15: "Account not activated",
            16: "Unsupported hoster",
            17: "Hoster in maintenance",
            18: "Hoster limit reached",
            19: "Hoster temporarily unavailable",
            20: "Hoster not available for free users",
            21: "Too many active downloads",
            22: "IP Address not allowed",
            23: "Traffic exhausted",
            24: "File unavailable",
            25: "Service unavailable",
            26: "Upload too big",
            27: "Upload error",
            28: "File not allowed",
            29: "Torrent too big",
            30: "Torrent file invalid",
            31: "Action already done",
            32: "Image resolution error",
            33: "Torrent already active",
            34: "Too many requests",
            36: "Fair Usage Limit",
        }

        if error_code and error_code in self.error_map:
            message = f"{message} ({self.error_map[error_code]})"
        super().__init__(message)


class RealDebridError(RealDebridAPIError):
    """Base exception for Real-Debrid API errors."""


class TorrentError(RealDebridError):
    """Exception raised for errors in torrent operations."""

    pass


class RealDebridClient:
    """Real-Debrid API client."""

    def __init__(self, api_key: str, settings: Optional[Settings] = None):
        """Initialize the Real-Debrid client.

        Args:
            api_key: Real-Debrid API key
            settings: Optional settings object
        """
        self.api_key = api_key
        self.settings = settings or Settings()

        # Disable httpx logging if configured
        if self.settings.disable_httpx_logging:
            logging.getLogger("httpx").setLevel(logging.WARNING)

        self.client = httpx.AsyncClient(
            base_url=self.settings.api_base_url, timeout=self.settings.api_timeout_secs
        )
        # Initialize rate limiters
        self.api_limiter = RateLimiter(
            calls=self.settings.api_rate_limit_per_minute, period=60.0
        )
        self.torrents_limiter = RateLimiter(
            calls=self.settings.torrents_rate_limit_per_minute, period=60.0
        )

    async def get_total_torrents(self) -> int:
        """Get total number of torrents in the account.

        Returns:
            Total number of torrents

        Raises:
            HTTPError: If API request fails
        """
        response = await self.client.get(
            "/torrents", params={"auth_token": self.api_key, "page": 1, "limit": 1}
        )
        response.raise_for_status()
        return int(response.headers.get("X-Total-Count", 0))

    async def get_torrents_page(
        self, page: int, limit: Optional[int] = None
    ) -> TorrentList:
        """Get a single page of torrents.

        Args:
            page: Page number (1-based)
            limit: Number of items per page, defaults to settings.page_size

        Returns:
            List of torrents for the requested page

        Raises:
            HTTPError: If API request fails
        """
        limit = limit or self.settings.fetch_torrents_page_size
        response = await self.client.get(
            "/torrents",
            params={"auth_token": self.api_key, "page": page, "limit": limit},
        )
        response.raise_for_status()
        return TorrentList.from_api_response(response.json())

    async def get_all_torrents(self) -> TorrentList:
        """Get all torrents using pagination.

        Returns:
            Complete list of torrents

        Raises:
            HTTPError: If API request fails
        """
        total_torrents = await self.get_total_torrents()
        total_pages = math.ceil(total_torrents / self.settings.fetch_torrents_page_size)

        all_torrents = []
        for page in range(1, total_pages + 1):
            page_torrents = await self.get_torrents_page(page)
            all_torrents.extend(page_torrents.torrents)

        return TorrentList(torrents=all_torrents)

    async def get_torrent_info(self, torrent_id: str) -> TorrentInfo:
        """Get detailed information about a specific torrent.

        Args:
            torrent_id: Torrent ID from Real-Debrid

        Returns:
            TorrentInfo object with detailed information including files

        Raises:
            HTTPError: If API request fails
            TorrentError: If torrent info cannot be retrieved
        """
        response = await self.client.get(
            f"/torrents/info/{torrent_id}", params={"auth_token": self.api_key}
        )
        response.raise_for_status()
        return TorrentInfo.parse_obj(response.json())

    async def select_files(
        self, torrent_id: str, file_ids: list[int] | str = "all"
    ) -> None:
        """Select which files to download from a torrent.

        Args:
            torrent_id: Torrent ID from Real-Debrid
            file_ids: List of file IDs to select or "all" for all files

        Raises:
            HTTPError: If API request fails
            TorrentError: If file selection fails
        """
        files = (
            ",".join(str(id) for id in file_ids)
            if isinstance(file_ids, list)
            else file_ids
        )
        response = await self.client.post(
            f"/torrents/selectFiles/{torrent_id}",
            params={"auth_token": self.api_key},
            data={"files": files},
        )
        response.raise_for_status()

    async def add_magnet(
        self, hash: str, file_ids: Optional[List[int]] = None
    ) -> TorrentInfo:
        """Add a hash and optionally select specific files for download.

        Args:
            hash: hash to add
            file_ids: List of specific file IDs to select. If None, no files are auto-selected.

        Returns:
            Torrent object representing the added torrent

        Raises:
            RealDebridAPIError: If API returns an error response
            TorrentError: If magnet cannot be added
        """
        # Acquire rate limit token before making API call
        await self.api_limiter.acquire()

        magnet = f"magnet:?xt=urn:btih:{hash}"
        try:
            # Add the magnet
            response = await self.client.post(
                "/torrents/addMagnet",
                params={"auth_token": self.api_key},
                data={"magnet": magnet},
            )
            response.raise_for_status()
            data = response.json()

            # Check for API error response
            if "error" in data:
                error_msg = data.get("error", "Unknown API error")
                error_code = data.get("error_code")
                raise RealDebridAPIError(error_msg, error_code)

            torrent_id = data["id"]

            # Get torrent info
            torrent = await self.get_torrent_info(torrent_id)

            # Select specific files if provided
            if file_ids:
                try:
                    await self.select_files(torrent_id, file_ids)
                except Exception as e:
                    raise TorrentError(
                        f"Failed to select files for torrent {torrent_id}: {str(e)}"
                    )

            return torrent

        except httpx.HTTPError as e:
            if isinstance(e, httpx.HTTPStatusError):
                # Handle HTTP status errors with response
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", str(e))
                    error_code = error_data.get("error_code")
                    raise RealDebridAPIError(error_msg, error_code)
                except (ValueError, AttributeError):
                    raise TorrentError(f"Failed to add magnet: {str(e)}")
            else:
                # Handle other HTTP errors (connection, timeout, etc)
                raise TorrentError(f"HTTP error occurred: {str(e)}")

    async def add_magnet_and_wait(
        self,
        magnet: str,
        file_ids: Optional[List[int]] = None,
        check_interval: int = 10,
        timeout: int = 3600,
    ) -> TorrentInfo:
        """Add a magnet and wait for it to be processed and ready.

        Args:
            magnet: Magnet link to add
            file_ids: List of specific file IDs to select. If None, no files are auto-selected.
            check_interval: How often to check torrent status in seconds
            timeout: Maximum time to wait in seconds

        Returns:
            Torrent object when it's ready for download

        Raises:
            HTTPError: If API request fails
            TorrentError: If torrent fails to process
            TimeoutError: If torrent takes too long to process
        """
        torrent = await self.add_magnet(magnet, file_ids)
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Torrent {torrent.id} took too long to process")

            torrent = await self.get_torrent_info(torrent.id)

            if torrent.status == "downloaded":
                return torrent
            elif torrent.status in ["magnet_error", "error", "virus", "dead"]:
                raise TorrentError(f"Torrent failed with status: {torrent.status}")

            await asyncio.sleep(check_interval)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager enter."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
