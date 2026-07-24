"""Per-run logging: identical output to console and to `<output_dir>/run.log`.

Modeled directly on `clo_avatar_generation/avatar_runtime/logging_setup.py`.
`configure_console_logger()` starts console-only with a `MemoryHandler`
buffering records; `attach_run_file_handler()` flushes the buffer into a real
file handler once an output directory is known, so `run.log` still captures
every line from the start of the run, not just what happened after the file
existed.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

LOGGER_NAME = "mirra.vto"
_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_DATEFMT = "%Y-%m-%dT%H:%M:%S"


def configure_console_logger() -> logging.Logger:
    """Start a fresh run logger: console output plus a pre-file memory buffer.

    Resets any handlers left over from a previous call in the same process so
    repeated runs (e.g. in tests) don't accumulate duplicate output.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    buffer_handler = logging.handlers.MemoryHandler(capacity=10_000, flushLevel=logging.CRITICAL + 1)
    buffer_handler.setLevel(logging.INFO)
    buffer_handler.setFormatter(formatter)
    logger.addHandler(buffer_handler)

    return logger


def attach_run_file_handler(logger: logging.Logger, output_dir: Path) -> None:
    """Attach `output_dir/run.log`, flushing any buffered pre-file records into it."""
    if any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        return

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)
    file_handler = logging.FileHandler(Path(output_dir) / "run.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    for handler in list(logger.handlers):
        if isinstance(handler, logging.handlers.MemoryHandler):
            handler.setTarget(file_handler)
            handler.flush()
            logger.removeHandler(handler)
            handler.close()

    logger.addHandler(file_handler)
