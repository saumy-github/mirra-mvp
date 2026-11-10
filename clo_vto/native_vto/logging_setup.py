"""Per-run logging for the VTO pipeline.

Every step module reports through `print()`. Rather than rewrite all twelve
of them, stdout and stderr are teed into `<run_dir>/run.log` for the duration
of the run: the console output is unchanged and the file gets the same lines
with a timestamp in front. Tracebacks land in the log too, which is the case
that mattered most — before this, a failed try-on left nothing on disk.
"""

from __future__ import annotations

import io
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _stamp() -> str:
    return datetime.now().strftime(_STAMP_FORMAT)


class _Tee(io.TextIOBase):
    """Writes to the original stream and to the run log."""

    def __init__(self, stream: TextIO, handle: TextIO) -> None:
        self._stream = stream
        self._handle = handle
        self._at_line_start = True

    def write(self, text: str) -> int:
        self._stream.write(text)
        self._stream.flush()
        for line in text.splitlines(keepends=True):
            if self._at_line_start and line.strip():
                self._handle.write(f"{_stamp()} ")
            self._handle.write(line)
            self._at_line_start = line.endswith("\n")
        self._handle.flush()
        return len(text)

    def flush(self) -> None:
        self._stream.flush()
        self._handle.flush()


class RunLog:
    """Context manager teeing console output into <run_dir>/run.log."""

    def __init__(self, run_dir: Path) -> None:
        self.path = Path(run_dir) / "run.log"
        self._handle: TextIO | None = None
        self._stdout: TextIO | None = None
        self._stderr: TextIO | None = None

    def __enter__(self) -> "RunLog":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")
        self._handle.write(f"\n{_stamp()} ==== run start ====\n")
        self._stdout, self._stderr = sys.stdout, sys.stderr
        sys.stdout = _Tee(self._stdout, self._handle)
        sys.stderr = _Tee(self._stderr, self._handle)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._stdout is not None:
            sys.stdout = self._stdout
        if self._stderr is not None:
            sys.stderr = self._stderr
        if self._handle is not None:
            self._handle.write(f"{_stamp()} ==== run end ====\n")
            self._handle.close()
            self._handle = None
        return False


def ensure_utf8_stdout() -> bool:
    """Make stdout and stderr able to carry the characters this pipeline prints.

    The pipeline's own output uses arrows and box-drawing characters. On Windows a piped
    or redirected stdout defaults to cp1252, which cannot encode them, and the *print*
    raises `UnicodeEncodeError` - so a cosmetic banner aborts the run before step 1.
    Encountered 2026-11-10 running the pipeline with its output captured; it would do the
    same under the RQ worker, where stdout is never a console.

    Reconfiguring is preferred over stripping the characters because it fixes every print
    at once, including ones in steps that have not been written yet. `errors='replace'`
    so that an encoding this does not anticipate degrades to a question mark instead of
    killing a try-on.
    """
    changed = False
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            if (getattr(stream, 'encoding', '') or '').lower().replace('-', '') != 'utf8':
                reconfigure(encoding='utf-8', errors='replace')
                changed = True
        except Exception:  # noqa: BLE001 - a closed or exotic stream is not fatal here
            continue
    return changed
