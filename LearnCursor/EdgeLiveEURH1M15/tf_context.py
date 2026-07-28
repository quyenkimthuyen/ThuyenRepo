"""TF-scoped report / artifact paths with dynamic Path-compatible REPORT_DIR."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

from config import get_active_tf, set_active_tf
from runtime_profiles import ROOT, get_tf_defaults

RESULTS_ROOT = ROOT / "results"


def resolve_tf(tf: str | None = None) -> str:
  if tf:
    return set_active_tf(tf)
  env = os.environ.get("FORGE_TF", "").strip().upper()
  if env in ("H1", "M15"):
    return set_active_tf(env)
  return get_active_tf()


def report_dir(tf: str | None = None) -> Path:
  t = resolve_tf(tf) if tf else get_active_tf()
  d = get_tf_defaults(t).report_dir
  d.mkdir(parents=True, exist_ok=True)
  return d


def get_report_dir(tf: str | None = None) -> Path:
  return report_dir(tf)


class DynamicReportDir:
  """Path-like object that always resolves under the active TF's results/."""

  __slots__ = ("_parts",)

  def __init__(self, *parts: Any):
    self._parts = tuple(str(p) for p in parts)

  def _resolve(self) -> Path:
    base = report_dir()
    return base.joinpath(*self._parts) if self._parts else base

  def __truediv__(self, other: Any) -> DynamicReportDir:
    return DynamicReportDir(*self._parts, other)

  def __str__(self) -> str:
    return str(self._resolve())

  def __repr__(self) -> str:
    return f"DynamicReportDir({self._resolve()!r})"

  def __fspath__(self) -> str:
    return str(self._resolve())

  def __eq__(self, other: object) -> bool:
    if isinstance(other, (DynamicReportDir, Path, str)):
      return str(self) == str(other)
    return NotImplemented

  def __hash__(self) -> int:
    return hash(str(self))

  def __getattr__(self, name: str) -> Any:
    return getattr(self._resolve(), name)

  def mkdir(self, *args: Any, **kwargs: Any) -> None:
    self._resolve().mkdir(*args, **kwargs)

  def exists(self) -> bool:
    return self._resolve().exists()

  def open(self, *args: Any, **kwargs: Any):
    return self._resolve().open(*args, **kwargs)

  def read_text(self, *args: Any, **kwargs: Any) -> str:
    return self._resolve().read_text(*args, **kwargs)

  def write_text(self, *args: Any, **kwargs: Any) -> int:
    return self._resolve().write_text(*args, **kwargs)

  def iterdir(self) -> Iterator[Path]:
    return self._resolve().iterdir()

  def glob(self, pattern: str):
    return self._resolve().glob(pattern)

  def with_suffix(self, suffix: str) -> Path:
    return self._resolve().with_suffix(suffix)

  def with_name(self, name: str) -> Path:
    return self._resolve().with_name(name)

  @property
  def parent(self) -> Path:
    return self._resolve().parent

  @property
  def name(self) -> str:
    return self._resolve().name

  @property
  def stem(self) -> str:
    return self._resolve().stem


# Singleton used as drop-in for former Path(__file__).parent / "results"
REPORT_DIR = DynamicReportDir()
