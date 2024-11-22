"""Enhanced logging configuration for RD-Sync."""

from datetime import datetime
from typing import Any, Dict

import colorama
import structlog
from rich.console import Console
from rich.traceback import install as install_rich_traceback

# Initialize colorama for Windows support
colorama.init()

# Install rich traceback handler
install_rich_traceback(show_locals=False, width=150, suppress=[])


class RDSyncRenderer:
    """Custom renderer for RD-Sync logging with color support."""

    LEVEL_COLORS = {
        "debug": "bright_black",
        "info": "green",
        "warning": "yellow",
        "error": "red",
        "critical": "red bold",
    }

    EVENT_STYLES = {
        # Scheduler events
        "scheduler.starting": ("blue", "⟳"),  # Changed from 🔄 to ⟳
        "scheduler.started": ("green", "✓"),  # Changed from ✅ to ✓
        "scheduler.stopping": ("yellow", "■"),  # Changed from ⏹️ to ■
        "scheduler.stopped": ("green", "✓"),  # Changed from ✅ to ✓
        # Job events
        "job.added": ("blue", "+"),  # Changed from ➕ to +
        "job.skipped": ("yellow", "→"),  # Changed from ⏭️ to →
        "job.closed": ("green", "✓"),  # Changed from ✅ to ✓
        "job.failed": ("red", "×"),  # Changed from ❌ to ×
        # Sync events
        "sync.started": ("blue", "⟳"),  # Changed from 🔄 to ⟳
        "sync.complete": ("green", "✓"),  # Changed from ✅ to ✓
        "sync.failed": ("red", "×"),  # Changed from ❌ to ×
        "sync.analysis": ("blue", "≡"),  # Changed from 📊 to ≡
        # Torrent events
        "torrent.added": ("green", "↓"),  # Changed from 📥 to ↓
        "torrent.failed": ("red", "!"),  # Changed from ⚠️ to !
        "torrent.fetching": ("blue", "○"),  # Changed from 🔍 to ○
        # Transfer events
        "transfer.started": ("blue", "↓"),  # Changed from ⬇️ to ↓
        "transfer.complete": ("green", "✓"),  # Changed from ✅ to ✓
        # App events
        "app.starting": ("blue", "►"),  # Changed from 🚀 to ►
        "shutdown.initiated": ("yellow", "■"),  # Changed from ⏳ to ■
        "shutdown.complete": ("green", "✓"),  # Changed from ✅ to ✓
    }

    def __init__(self):
        """Initialize the renderer."""
        self.console = Console(force_terminal=True, color_system="truecolor")

    def __call__(self, _: Any, __: str, event_dict: Dict[str, Any]) -> str:
        """Format the log message with colors and structure."""
        # Extract basic fields
        timestamp = event_dict.pop("timestamp", datetime.now().isoformat())
        level = event_dict.pop("level", "info").lower()
        event_name = event_dict.pop("event", "")
        job = event_dict.pop("job", "main")

        # Construct the message
        parts = []

        # Timestamp with reduced visibility
        parts.append(f"\033[2m{timestamp}\033[0m")

        # Log level with color (increase padding from 8 to 10)
        level_color = self.LEVEL_COLORS.get(level, "white")
        parts.append(f"\033[1;{self._get_ansi_color(level_color)}m{level:10}\033[0m")

        # Job name in cyan (increase padding from 15 to 20)
        parts.append(f"\033[36m{job:20}\033[0m")

        # Event with emoji and color
        style, icon = self.EVENT_STYLES.get(event_name, ("white", "·"))
        color_code = self._get_ansi_color(style)

        # Using monospace ASCII characters for consistent width
        event_display = f" {icon} {event_name:<25}"  # Added space before icon
        parts.append(f"\033[{color_code}m{event_display}\033[0m")

        # Format remaining fields with improved readability
        extras = []
        for key, value in event_dict.items():
            if key.startswith("_") or key in ("logger", "level"):
                continue

            # Special formatting for specific fields
            if key == "success_rate":
                formatted_value = (
                    f"\033[1;32m{value}\033[0m"  # Bold green for success rate
                )
            elif key == "error_count":
                formatted_value = (
                    f"\033[1;31m{value}\033[0m"  # Bold red for error count
                )
            elif isinstance(value, (int, float)):
                formatted_value = f"\033[36m{value}\033[0m"
            else:
                formatted_value = f"\033[37m{value}\033[0m"

            extras.append(f"\033[33m{key}\033[0m={formatted_value}")

        if extras:
            parts.append(" ".join(extras))

        return " ".join(parts)

    def _get_ansi_color(self, color: str) -> str:
        """Convert color name to ANSI color code."""
        color_map = {
            "black": "30",
            "red": "31",
            "green": "32",
            "yellow": "33",
            "blue": "34",
            "magenta": "35",
            "cyan": "36",
            "white": "37",
            "bright_black": "90",
            "bright_red": "91",
            "bright_green": "92",
            "bright_yellow": "93",
            "bright_blue": "94",
            "bright_magenta": "95",
            "bright_cyan": "96",
            "bright_white": "97",
        }

        # Handle bold variant
        if "bold" in color:
            base_color = color.replace(" bold", "")
            return f"1;{color_map.get(base_color, '37')}"

        return color_map.get(color, "37")


def setup_logging() -> None:
    """Configure structured logging with ConsoleRenderer."""
    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        RDSyncRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "main") -> structlog.BoundLogger:
    """Get a logger instance bound to a specific context."""
    return structlog.get_logger().bind(job=name)


# Create base logger
logger = get_logger()

__all__ = ["setup_logging", "logger", "get_logger"]
