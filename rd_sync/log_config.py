import colorama
import structlog
from structlog.dev import ConsoleRenderer


def setup_logging() -> None:
    """Setup structured logging with ConsoleRenderer."""

    # Initialize colorama for Windows support
    colorama.init()

    # Create console renderer with custom formatting
    renderer = ConsoleRenderer(
        sort_keys=False,
        pad_event=50,  # Good padding for events
        pad_level=True,  # Ensure level field is padded
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        cache_logger_on_first_use=True,
    )


# Create base logger
logger = structlog.get_logger()

__all__ = ["setup_logging", "logger"]
