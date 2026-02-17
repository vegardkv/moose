"""Logging configuration with structured stdout and Discord alerts."""

import asyncio
import logging
import sys

from moose.notifications import send_discord


class DiscordHandler(logging.Handler):
    """Custom logging handler that forwards WARNING+ messages to Discord."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_tasks = set()

    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Discord if it's WARNING or higher."""
        try:
            msg = self.format(record)
            level = "warning" if record.levelno == logging.WARNING else "error"

            # Run async send_discord in a new event loop
            # (logging handlers are sync, so we need to handle this carefully)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an event loop, schedule it as a task
                    task = asyncio.create_task(send_discord(msg, level))
                    # Keep track of background tasks to prevent them from
                    # being garbage collected
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                else:
                    # Otherwise run it
                    loop.run_until_complete(send_discord(msg, level))
            except RuntimeError:
                # No event loop - create a new one
                asyncio.run(send_discord(msg, level))
        except Exception:
            self.handleError(record)


def setup_logging() -> None:
    """
    Configure logging with:
    - Structured stdout output for journalctl
    - Discord webhook handler for WARNING+ messages
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Structured formatter for journalctl
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Stdout handler - all messages
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # Discord handler - WARNING+ only
    discord_handler = DiscordHandler()
    discord_handler.setLevel(logging.WARNING)
    discord_handler.setFormatter(formatter)
    root_logger.addHandler(discord_handler)
