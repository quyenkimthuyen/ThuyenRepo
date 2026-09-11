"""Cross-process file lock that works on Windows and Linux."""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def interprocess_lock(
  lock_path: Path,
  *,
  timeout_sec: float = 30.0,
  poll_sec: float = 0.05,
) -> Iterator[None]:
  """Exclusive lock via ``msvcrt`` (Windows) or ``fcntl`` (POSIX).

  Best-effort: if locking APIs are unavailable, still serialize within this
  process only (callers should keep writes short and use unique temps).
  """
  lock_path = Path(lock_path)
  lock_path.parent.mkdir(parents=True, exist_ok=True)
  lockf = open(lock_path, "a+b")
  locked = False
  deadline = time.monotonic() + max(0.5, float(timeout_sec))
  try:
    while True:
      try:
        if os.name == "nt":
          import msvcrt

          lockf.seek(0)
          if lockf.read(1) == b"":
            lockf.write(b"\0")
            lockf.flush()
          lockf.seek(0)
          msvcrt.locking(lockf.fileno(), msvcrt.LK_NBLCK, 1)
        else:
          import fcntl

          fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        break
      except OSError:
        if time.monotonic() >= deadline:
          # BUG-06: fail closed for risk_cap — never proceed unlocked.
          raise TimeoutError(f"interprocess_lock timeout: {lock_path}")
        time.sleep(poll_sec)
    yield
  finally:
    if locked:
      try:
        if os.name == "nt":
          import msvcrt

          lockf.seek(0)
          msvcrt.locking(lockf.fileno(), msvcrt.LK_UNLCK, 1)
        else:
          import fcntl

          fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
      except OSError:
        pass
    try:
      lockf.close()
    except OSError:
      pass
