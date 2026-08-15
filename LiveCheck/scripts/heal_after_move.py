"""Rewrite absolute paths after LiveCheck (or Final_app) is moved.

Configs (mt5_bridge_*.json, worker status, install_meta, …) often store
absolute Windows paths. After a folder move those paths still point at the
old tree → Start Trading / DeployEA / train bridges break.

Usage:
  python scripts/heal_after_move.py
  python scripts/heal_after_move.py --dry-run
  python Trade/live/scripts/heal_after_move.py   # same entry via live wrapper

Safe to run repeatedly. Skips files already under the current app root.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# LiveCheck/scripts/heal_after_move.py → LiveCheck
# Also allow import from Trade/live when wrapped.
_SCRIPT = Path(__file__).resolve()
if _SCRIPT.parent.name == "scripts" and _SCRIPT.parent.parent.name == "live":
  APP_ROOT = _SCRIPT.parents[3]  # .../LiveCheck
elif _SCRIPT.parent.name == "scripts":
  APP_ROOT = _SCRIPT.parent.parent  # .../LiveCheck
else:
  APP_ROOT = _SCRIPT.parents[2]

MARKER_NAME = ".install_root"
SKIP_DIR_NAMES = {
  ".git", "__pycache__", ".venv", "venv", "node_modules",
  "debug_logs", "simulate_runs", "packages_out", "packages_inbox",
}
SKIP_SUFFIXES = {".parquet", ".ex5", ".mq5", ".pyc", ".png", ".jpg", ".zip", ".tmpkg"}
MAX_FILE_BYTES = 4_000_000

_ABS_RE = re.compile(r'^(?:[A-Za-z]:[\\/]|\\\\)')


def _is_abs_path_str(value: str) -> bool:
  s = value.strip()
  if len(s) < 4 or "\n" in s:
    return False
  if not _ABS_RE.match(s):
    return False
  # Heuristic: path-like, not a sentence
  return ("\\" in s or "/" in s) and ("." in s or "EdgeMiner" in s or "bridge" in s or "Trade" in s or "Train" in s or "split_app" in s or "backtest" in s)


def remap_abs_path(raw: str, app_root: Path) -> str | None:
  """Map an old absolute path onto the current LiveCheck tree, or None."""
  try:
    path = Path(raw)
  except Exception:
    return None
  parts = list(path.parts)
  if not parts:
    return None

  # Already under current root → keep
  try:
    path.resolve().relative_to(app_root.resolve())
    return None
  except Exception:
    pass

  def join_from(i: int, *prefix: str) -> str:
    return str(app_root.joinpath(*prefix, *parts[i:]))

  for i, part in enumerate(parts):
    if part == "Train" and i + 1 < len(parts):
      return join_from(i)
    if part == "Trade" and i + 1 < len(parts):
      return join_from(i)
    if part == "split_app":
      # Final_app/split_app/... → LiveCheck/Trade/...
      return join_from(i + 1, "Trade")
    if part == "backtestM5" and i + 1 < len(parts):
      return join_from(i + 1, "Train", "M5")
    if part == "backtest" and i + 1 < len(parts) and str(parts[i + 1]).startswith("EdgeMiner"):
      return join_from(i + 1, "Train", "M15")
    if part == "Final_app" and i + 1 < len(parts):
      nxt = str(parts[i + 1])
      if nxt.startswith("EdgeMiner"):
        tf = "M15" if nxt.endswith("M15") else "M5"
        return join_from(i + 1, "Train", tf)
      if nxt == "split_app":
        return join_from(i + 2, "Trade")
  return None


def _rewrite_string(value: str, app_root: Path) -> tuple[str, bool]:
  if not _is_abs_path_str(value):
    return value, False
  mapped = remap_abs_path(value, app_root)
  if not mapped or mapped == value:
    return value, False
  return mapped, True


def _rewrite_obj(obj: Any, app_root: Path) -> tuple[Any, int]:
  if isinstance(obj, dict):
    out: dict[str, Any] = {}
    n = 0
    for k, v in obj.items():
      nv, c = _rewrite_obj(v, app_root)
      out[k] = nv
      n += c
    return out, n
  if isinstance(obj, list):
    out_l: list[Any] = []
    n = 0
    for v in obj:
      nv, c = _rewrite_obj(v, app_root)
      out_l.append(nv)
      n += c
    return out_l, n
  if isinstance(obj, str):
    nv, changed = _rewrite_string(obj, app_root)
    return nv, (1 if changed else 0)
  return obj, 0


def _should_scan(path: Path) -> bool:
  if path.suffix.lower() not in {".json", ".jsonl", ".txt", ".cfg", ".ini", ".pid"}:
    return False
  if path.suffix.lower() in SKIP_SUFFIXES:
    return False
  try:
    if path.stat().st_size > MAX_FILE_BYTES:
      return False
  except OSError:
    return False
  # Prefer config-ish files; still allow jsonl but skip huge logs via size.
  name = path.name.lower()
  if path.suffix.lower() == ".jsonl" and "debug" in name:
    return False
  return True


def iter_candidate_files(app_root: Path) -> list[Path]:
  files: list[Path] = []
  for dirpath, dirnames, filenames in os.walk(app_root):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]
    for name in filenames:
      p = Path(dirpath) / name
      if _should_scan(p):
        files.append(p)
  return files


def heal_file(path: Path, app_root: Path, *, dry_run: bool = False) -> int:
  try:
    raw = path.read_text(encoding="utf-8")
  except (OSError, UnicodeError):
    return 0

  changed = 0
  if path.suffix.lower() == ".json":
    try:
      data = json.loads(raw)
    except json.JSONDecodeError:
      # Fall through to plain-text replace of known roots only via obj walk on
      # string scan below.
      data = None
    if data is not None:
      new_data, changed = _rewrite_obj(data, app_root)
      if changed and not dry_run:
        path.write_text(
          json.dumps(new_data, indent=2, ensure_ascii=False, default=str) + "\n",
          encoding="utf-8",
        )
      return changed

  # Plain text / jsonl: line-wise path rewrite
  lines = raw.splitlines(keepends=True)
  out_lines: list[str] = []
  for line in lines:
    # Extract quoted or bare absolute paths roughly
    def repl(m: re.Match[str]) -> str:
      nonlocal changed
      old = m.group(0)
      mapped = remap_abs_path(old, app_root)
      if mapped and mapped != old:
        changed += 1
        return mapped
      return old

    new_line = re.sub(
      r'(?:[A-Za-z]:[\\/][^"\s\'<>|*?]*)',
      repl,
      line,
    )
    out_lines.append(new_line)
  if changed and not dry_run:
    path.write_text("".join(out_lines), encoding="utf-8")
  return changed


def read_marker(app_root: Path) -> str | None:
  marker = app_root / MARKER_NAME
  if not marker.exists():
    return None
  try:
    return marker.read_text(encoding="utf-8").strip() or None
  except OSError:
    return None


def write_marker(app_root: Path) -> None:
  (app_root / MARKER_NAME).write_text(str(app_root.resolve()) + "\n", encoding="utf-8")


def heal_app_root(app_root: Path | None = None, *, dry_run: bool = False, force: bool = False) -> dict[str, Any]:
  root = (app_root or APP_ROOT).resolve()
  prev = read_marker(root)
  cur = str(root)
  moved = force or (prev is not None and prev != cur) or prev is None

  summary: dict[str, Any] = {
    "app_root": cur,
    "previous_root": prev,
    "moved": bool(moved),
    "files_touched": 0,
    "replacements": 0,
    "dry_run": dry_run,
  }
  if not moved and not force:
    summary["skipped"] = "install_root_unchanged"
    return summary

  total_repl = 0
  touched = 0
  for path in iter_candidate_files(root):
    n = heal_file(path, root, dry_run=dry_run)
    if n:
      touched += 1
      total_repl += n

  summary["files_touched"] = touched
  summary["replacements"] = total_repl
  if not dry_run:
    write_marker(root)
  return summary


def maybe_heal_on_boot(app_root: Path | None = None) -> dict[str, Any] | None:
  """No-op if marker matches; otherwise rewrite stale paths. Safe for Start hooks."""
  root = (app_root or APP_ROOT).resolve()
  prev = read_marker(root)
  if prev == str(root):
    return None
  return heal_app_root(root, dry_run=False, force=True)


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description="Heal absolute paths after moving LiveCheck")
  parser.add_argument("--root", type=Path, default=None, help="LiveCheck root (default: auto)")
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument("--force", action="store_true", help="Heal even if .install_root matches")
  args = parser.parse_args(argv)
  summary = heal_app_root(args.root, dry_run=args.dry_run, force=args.force or args.dry_run)
  print(json.dumps(summary, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
