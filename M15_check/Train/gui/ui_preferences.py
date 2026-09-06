"""Durable Streamlit UI preferences shared by all active views."""
from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import streamlit as st

from run_backtest import REPORT_DIR

PREFERENCES_PATH = REPORT_DIR / "ui_preferences.json"
_lock = threading.RLock()


@contextmanager
def _process_file_lock(target: Path):
  """Serialize writers across Streamlit/service processes."""
  lock_path = target.with_suffix(target.suffix + ".lock")
  lock_path.parent.mkdir(parents=True, exist_ok=True)
  with open(lock_path, "a+b") as handle:
    handle.seek(0, 2)
    if handle.tell() == 0:
      handle.write(b"0")
      handle.flush()
    handle.seek(0)
    if os.name == "nt":
      import msvcrt
      msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
      import fcntl
      fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    try:
      yield
    finally:
      handle.seek(0)
      if os.name == "nt":
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
      else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _json_safe(value: Any) -> Any:
  if isinstance(value, (date, datetime)):
    return value.isoformat()
  if isinstance(value, tuple):
    return [_json_safe(v) for v in value]
  if isinstance(value, list):
    return [_json_safe(v) for v in value]
  if isinstance(value, dict):
    return {str(k): _json_safe(v) for k, v in value.items()}
  return value


def load_preferences(path: Path | None = None) -> dict[str, Any]:
  target = path or PREFERENCES_PATH
  if not target.exists():
    return {}
  try:
    with open(target, encoding="utf-8") as handle:
      data = json.load(handle)
    return data if isinstance(data, dict) else {}
  except (OSError, json.JSONDecodeError):
    return {}


def save_preferences(data: dict[str, Any], path: Path | None = None) -> None:
  target = path or PREFERENCES_PATH
  target.parent.mkdir(parents=True, exist_ok=True)
  tmp = target.with_suffix(target.suffix + ".tmp")
  with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(_json_safe(data), handle, indent=2, ensure_ascii=False)
    handle.write("\n")
  tmp.replace(target)


def get_preference(key: str, default: Any = None) -> Any:
  with _lock:
    return load_preferences().get(key, default)


def set_preference(key: str, value: Any) -> Any:
  safe_value = _json_safe(value)
  with _lock:
    with _process_file_lock(PREFERENCES_PATH):
      data = load_preferences()
      if data.get(key) == safe_value:
        return value
      data[key] = safe_value
      save_preferences(data)
  return value


def delete_preference(key: str) -> None:
  with _lock:
    with _process_file_lock(PREFERENCES_PATH):
      data = load_preferences()
      if key not in data:
        return
      data.pop(key, None)
      save_preferences(data)


def restore_widget(
  widget_key: str,
  default: Any,
  *,
  preference_key: str | None = None,
  options: Iterable[Any] | None = None,
  multiple: bool = False,
  decode: Callable[[Any], Any] | None = None,
) -> Any:
  """Restore a widget key after Streamlit removed it on view unmount."""
  pref_key = preference_key or widget_key
  allowed = list(options) if options is not None else None
  if widget_key not in st.session_state:
    value = get_preference(pref_key, default)
    if decode is not None:
      try:
        value = decode(value)
      except (TypeError, ValueError):
        value = default
    valid = (
      isinstance(value, list) and all(item in allowed for item in value)
      if multiple and allowed is not None else
      allowed is None or value in allowed
    )
    if not valid:
      value = default if default in allowed else (allowed[0] if allowed else default)
      if multiple:
        value = list(default) if isinstance(default, (list, tuple)) else []
      set_preference(pref_key, value)
    st.session_state[widget_key] = value
  elif allowed is not None:
    current = st.session_state[widget_key]
    valid = (
      isinstance(current, list) and all(item in allowed for item in current)
      if multiple else current in allowed
    )
    if valid:
      return current
    value = (
      list(default) if multiple and isinstance(default, (list, tuple))
      else (default if default in allowed else (allowed[0] if allowed else default))
    )
    st.session_state[widget_key] = value
    set_preference(pref_key, value)
  return st.session_state[widget_key]


def persist_widget(widget_key: str, preference_key: str | None = None) -> None:
  if widget_key in st.session_state:
    set_preference(preference_key or widget_key, st.session_state[widget_key])


def set_widget_preference(
  widget_key: str,
  value: Any,
  preference_key: str | None = None,
) -> None:
  st.session_state[widget_key] = value
  set_preference(preference_key or widget_key, value)


def preference_callback(
  widget_key: str,
  preference_key: str | None = None,
) -> Callable[[], None]:
  return lambda: persist_widget(widget_key, preference_key)
