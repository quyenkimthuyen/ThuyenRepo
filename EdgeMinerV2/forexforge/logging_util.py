"""Structured logging for ForexForge v2."""
from __future__ import annotations

import logging
import sys


def get_logger(name: str = "forexforge") -> logging.Logger:
  # Avoid Windows cp1252 crashes on Unicode log/print paths
  try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
  except Exception:
    pass
  logger = logging.getLogger(name)
  if logger.handlers:
    return logger
  logger.setLevel(logging.INFO)
  handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
  )
  logger.addHandler(handler)
  logger.propagate = False
  return logger
