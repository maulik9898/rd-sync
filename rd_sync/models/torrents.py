from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TorrentFile(BaseModel):
    """Model representing a file in a torrent."""

    id: int
    path: str = Field(..., description="Path to the file inside the torrent")
    bytes_: int = Field(..., alias="bytes")
    selected: int = Field(..., description="0 or 1")


class TorrentInfo(BaseModel):
    """Model representing detailed torrent information from Real-Debrid."""

    id: str
    filename: str
    original_filename: str = Field(..., description="Original name of the torrent")
    hash: str = Field(..., description="SHA1 Hash of the torrent")
    bytes_: int = Field(..., alias="bytes", description="Size of selected files only")
    original_bytes: int = Field(..., description="Total size of the torrent")
    host: str = Field(..., description="Host main domain")
    split: int = Field(..., description="Split size of links")
    progress: float = Field(..., description="Progress value from 0 to 100")
    status: Literal[
        "magnet_error",
        "magnet_conversion",
        "waiting_files_selection",
        "queued",
        "downloading",
        "downloaded",
        "error",
        "virus",
        "compressing",
        "uploading",
        "dead",
    ]
    added: datetime
    files: List[TorrentFile] = Field(..., description="Files in the torrent")
    links: Optional[List[str]] = Field(None, description="Host URLs")
    ended: Optional[datetime] = Field(None, description="Only present when finished")
    speed: Optional[int] = Field(
        None, description="Only present in downloading, compressing, uploading status"
    )
    seeders: Optional[int] = Field(
        None, description="Only present in downloading, magnet_conversion status"
    )


class Torrent(BaseModel):
    """Model representing a torrent in Real-Debrid."""

    id: str
    filename: str
    hash: str = Field(..., description="SHA1 Hash of the torrent")
    bytes_: int = Field(..., alias="bytes", description="Size of selected files only")
    host: str = Field(..., description="Host main domain")
    split: int = Field(..., description="Split size of links")
    progress: float = Field(..., description="Progress value from 0 to 100")
    status: Literal[
        "magnet_error",
        "magnet_conversion",
        "waiting_files_selection",
        "queued",
        "downloading",
        "downloaded",
        "error",
        "virus",
        "compressing",
        "uploading",
        "dead",
    ]
    added: datetime
    links: Optional[List[str]] = Field(None, description="Host URLs")
    ended: Optional[datetime] = Field(None, description="Only present when finished")
    speed: Optional[int] = Field(
        None, description="Only present in downloading, compressing, uploading status"
    )
    seeders: Optional[int] = Field(
        None, description="Only present in downloading, magnet_conversion status"
    )

    def is_ready_for_sync(self) -> bool:
        """Check if torrent is fully downloaded and has available links.

        Returns:
            bool: True if torrent is ready for sync, False otherwise
        """
        return self.progress != 100 or self.links is None or len(self.links) == 0


class TorrentList(BaseModel):
    """Model representing a list of torrents."""

    torrents: List[Torrent]

    @classmethod
    def from_api_response(cls, data: List[dict]) -> "TorrentList":
        """Create TorrentList from API response data."""
        return cls(torrents=[Torrent.parse_obj(item) for item in data])

    def __len__(self):
        return len(self.torrents)

    @staticmethod
    def format_size(bytes_: int) -> str:
        """Format bytes into human readable format."""
        size = float(bytes_)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
