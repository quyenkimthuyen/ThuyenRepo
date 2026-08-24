"""Shared JSON file protocol between ForgeBridge EA and App service."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app_paths import get_root, relocate_under_root
ROOT = get_root()

def _desk_bridge_defaults():
  import os
  cfg = {}
  if os.environ.get("TRAINAPP_DESK"):
    try:
      import sys
      from pathlib import Path as _P
      root = _P(os.environ.get("TRAINAPP_ROOT") or "").resolve()
      if root and str(root) not in sys.path:
        sys.path.insert(0, str(root))
      from desk_context import load_desk
      cfg = load_desk()
    except Exception:
      cfg = {}
  return cfg

_CFG = _desk_bridge_defaults()
_BRIDGE = str(_CFG.get("bridge_subdir") or "bridge_m5e31")
_BRIDGE_SIM = str(_CFG.get("bridge_sim_subdir") or "bridge_sim_m5e31")
BRIDGE_DIR = ROOT / "mt5" / _BRIDGE
# One Live EA: history test uses sim_control.json in the Live folder.
BRIDGE_SIM_DIR = BRIDGE_DIR
CONFIG_PATH = ROOT / "results" / "mt5_bridge_config.json"

BAR_NAME = "bar.json"
BARS_NAME = "bars.json"
CONNECTION_NAME = "connection.json"
HISTORY_REQUEST_NAME = "history_request.json"
HISTORY_CHUNK_NAME = "history_chunk.json"
HISTORY_ACK_NAME = "history_ack.json"
HISTORY_STATUS_NAME = "history_status.json"
DECISION_NAME = "decision.json"
DECISIONS_DIR_NAME = "decisions"
MODELS_NAME = "models.json"
COMMAND_NAME = "command.json"
COMMAND_ACK_NAME = "command_ack.json"
FILL_NAME = "fill.json"
STATUS_NAME = "status.json"
REPLAY_NAME = "replay_decisions.json"
REPLAY_CSV_NAME = "replay_signals.csv"
SIM_CONTROL_NAME = "sim_control.json"

DEFAULT_MODEL_ID = ""
DEFAULT_MAGIC = int(_CFG.get("magic") or 20261061)
DEFAULT_SIM_MAGIC = int(_CFG.get("sim_magic") or 20262061)
DEFAULT_TIMEFRAME = str(_CFG.get("tf") or "M5")
INSTANCE_ID = str(_CFG.get("instance_id") or "M5E31")
MAX_BRIDGE_MODELS = 5



def ensure_bridge_dir(path: Path | None = None) -> Path:
  d = path or BRIDGE_DIR
  d.mkdir(parents=True, exist_ok=True)
  return d


def _read_config_bridge_dir() -> Path | None:
  try:
    if not CONFIG_PATH.exists():
      return None
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw = str(data.get("bridge_dir") or "").strip()
    if not raw:
      return None
    return relocate_under_root(raw, root=ROOT) or Path(raw)
  except Exception:
    return None


def _discover_named_bridge(*, sim: bool) -> Path | None:
  """Clones use mt5/bridge_m15aN (+ bridge_sim_m15aN), not mt5/bridge."""
  mt5 = ROOT / "mt5"
  if not mt5.is_dir():
    return None
  dirs = [p for p in mt5.iterdir() if p.is_dir()]
  if sim:
    cands = sorted(
      p for p in dirs
      if p.name.startswith("bridge_sim") and p.name != "bridge_sim"
    )
  else:
    cands = sorted(
      p for p in dirs
      if p.name.startswith("bridge_") and "sim" not in p.name
    )
  if not cands:
    return None
  for p in cands:
    if (p / CONNECTION_NAME).exists() or (p / STATUS_NAME).exists():
      return p
  return cands[0]


def resolve_live_bridge_dir() -> Path:
  """Live EA I/O dir — config.bridge_dir (clones) or default mt5/bridge."""
  cfg_dir = _read_config_bridge_dir()
  if cfg_dir is not None:
    return ensure_bridge_dir(cfg_dir)
  discovered = _discover_named_bridge(sim=False)
  if discovered is not None:
    return ensure_bridge_dir(discovered)
  return BRIDGE_DIR


def resolve_sim_bridge_dir() -> Path:
  """History test I/O dir — same Live EA folder (sim_control.json)."""
  return resolve_live_bridge_dir()


def safe_replace(src: Path, dst: Path, attempts: int = 5, delay: float = 0.05) -> None:
  dst.parent.mkdir(parents=True, exist_ok=True)
  for attempt in range(attempts):
    try:
      src.replace(dst)
      return
    except OSError as err:
      if attempt < attempts - 1:
        time.sleep(delay)
      else:
        try:
          import shutil
          shutil.copy2(src, dst)
          if src.exists():
            src.unlink(missing_ok=True)
          return
        except Exception:
          if src.exists():
            try:
              src.unlink(missing_ok=True)
            except Exception:
              pass
          raise err


def atomic_write_json(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  with open(tmp, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
  try:
    safe_replace(tmp, path)
  except Exception:
    try:
      with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
      if tmp.exists():
        tmp.unlink(missing_ok=True)
    except Exception:
      pass



def read_json(path: Path) -> dict | list | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except (OSError, json.JSONDecodeError):
    return None


def bar_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / BAR_NAME


def bars_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / BARS_NAME


def connection_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / CONNECTION_NAME


def history_request_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_REQUEST_NAME


def history_chunk_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_CHUNK_NAME


def history_ack_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_ACK_NAME


def history_status_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_STATUS_NAME


def decision_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / DECISION_NAME


def decisions_dir(bridge_dir: Path | None = None) -> Path:
  d = ensure_bridge_dir(bridge_dir) / DECISIONS_DIR_NAME
  d.mkdir(parents=True, exist_ok=True)
  return d


def decision_path_for(model_id: str, bridge_dir: Path | None = None) -> Path:
  """Per-model decision file: decisions/<model_id>.json (safe filename)."""
  safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(model_id or "unknown"))
  if not safe:
    safe = "unknown"
  return decisions_dir(bridge_dir) / f"{safe}.json"


def models_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / MODELS_NAME


def normalize_model_ids(model_ids: list | tuple | str | None, *, fallback: str | None = None) -> list[str]:
  """Dedupe model ids, cap at MAX_BRIDGE_MODELS. Accepts legacy singular model_id.

  A comma-separated string (e.g. from CLI ``--model-ids a,b``) is split into
  multiple ids — not treated as one id containing commas.
  """
  raw: list[str] = []
  if isinstance(model_ids, str) and model_ids.strip():
    raw = [p.strip() for p in model_ids.split(",") if p.strip()]
  elif isinstance(model_ids, (list, tuple)):
    for x in model_ids:
      s = str(x).strip()
      if not s:
        continue
      if "," in s:
        raw.extend(p.strip() for p in s.split(",") if p.strip())
      else:
        raw.append(s)
  seen: set[str] = set()
  out: list[str] = []
  for mid in raw:
    if mid in seen:
      continue
    seen.add(mid)
    out.append(mid)
    if len(out) >= MAX_BRIDGE_MODELS:
      break
  if not out and fallback and str(fallback).strip():
    fb = str(fallback).strip()
    if "," in fb:
      out = normalize_model_ids(fb)
    else:
      out = [fb]
  return out


def assign_magics(
  model_ids: list[str],
  *,
  base_magic: int = DEFAULT_MAGIC,
  existing: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
  """Stable magic per model: prefer existing map, else base+index.

  Keeps previously assigned magics when the roster shrinks/grows so open
  positions are not remapped mid-trade.
  """
  ids = normalize_model_ids(model_ids)
  prev = dict(existing or {})
  used = set(int(v) for v in prev.values() if v is not None)
  rows: list[dict[str, Any]] = []
  next_i = 0
  for mid in ids:
    if mid in prev and prev[mid] is not None:
      magic = int(prev[mid])
    else:
      while True:
        magic = int(base_magic) + next_i
        next_i += 1
        if magic not in used:
          break
      used.add(magic)
    rows.append({"id": mid, "magic": magic})
  return rows


def read_models_roster(bridge_dir: Path | None = None) -> dict[str, Any]:
  data = read_json(models_path(bridge_dir))
  return data if isinstance(data, dict) else {}


def write_models_roster(
  model_ids: list[str],
  *,
  risk_pct: float = 1.0,
  bridge_dir: Path | None = None,
  base_magic: int = DEFAULT_MAGIC,
  labels: dict[str, str] | None = None,
) -> dict[str, Any]:
  """App → EA roster. Preserves magics for models still present."""
  prev = read_models_roster(bridge_dir)
  existing: dict[str, int] = {}
  for row in prev.get("models") or []:
    if isinstance(row, dict) and row.get("id") is not None and row.get("magic") is not None:
      existing[str(row["id"])] = int(row["magic"])
  rows = assign_magics(model_ids, base_magic=base_magic, existing=existing)
  label_map = labels or {}
  models = []
  for row in rows:
    mid = row["id"]
    models.append({
      "id": mid,
      "magic": int(row["magic"]),
      "label": str(label_map.get(mid) or mid),
    })
  payload: dict[str, Any] = {
    "updated_at": utc_now_iso(),
    "risk_pct": float(risk_pct),
    "base_magic": int(base_magic),
    "models": models,
  }
  atomic_write_json(models_path(bridge_dir), payload)
  return payload


def magic_to_model_id(roster: dict[str, Any] | None, magic: int | None) -> str | None:
  if not roster or magic is None:
    return None
  try:
    m = int(magic)
  except (TypeError, ValueError):
    return None
  for row in roster.get("models") or []:
    if isinstance(row, dict) and int(row.get("magic") or -1) == m:
      return str(row.get("id") or "") or None
  return None


def write_model_decision(
  decision: dict[str, Any],
  *,
  bridge_dir: Path | None = None,
  mirror_primary: bool = True,
  primary_model_id: str | None = None,
) -> Path:
  """Write decisions/<model_id>.json; optionally mirror primary to decision.json."""
  mid = str(decision.get("model_id") or primary_model_id or "unknown")
  path = decision_path_for(mid, bridge_dir)
  atomic_write_json(path, decision)
  if mirror_primary:
    primary = str(primary_model_id or "")
    if not primary or mid == primary:
      atomic_write_json(decision_path(bridge_dir), decision)
  return path


def command_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / COMMAND_NAME


def command_ack_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / COMMAND_ACK_NAME


def fill_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / FILL_NAME


def status_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / STATUS_NAME


def replay_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REPLAY_NAME


def replay_csv_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REPLAY_CSV_NAME


def sim_control_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir or BRIDGE_DIR) / SIM_CONTROL_NAME


def read_sim_control(bridge_dir: Path | None = None) -> dict[str, Any]:
  data = read_json(sim_control_path(bridge_dir))
  return data if isinstance(data, dict) else {}


def history_replay_active(bridge_dir: Path | None = None) -> bool:
  """True while the Live EA is running a from/to history test."""
  ctrl = read_sim_control(bridge_dir)
  if bool(ctrl.get("enabled")):
    return True
  return str(ctrl.get("ea_status") or "") == "running"


def write_sim_control(
  bridge_dir: Path | None = None,
  *,
  merge: bool = True,
  **fields: Any,
) -> dict[str, Any]:
  """Write App→EA history-feed control file (EA updates ea_status/bars_*)."""
  path = sim_control_path(bridge_dir)
  cur: dict[str, Any] = {}
  if merge:
    prev = read_json(path)
    if isinstance(prev, dict):
      cur.update(prev)
  cur.update(fields)
  cur["updated_at"] = utc_now_iso()
  atomic_write_json(path, cur)
  return cur


def utc_now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _manual_signal_id(prefix: str = "manual_test") -> str:
  return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def pip_size_from_quotes(*, digits: int | None = None, point: float | None = None) -> float:
  """Estimate 1 pip in price units (EURUSD 5-digit → 0.0001)."""
  if point is not None and float(point) > 0:
    d = int(digits) if digits is not None else (5 if float(point) < 0.001 else 4)
    return float(point) * (10.0 if d in (3, 5) else 1.0)
  if digits is not None:
    d = int(digits)
    if d in (3, 5):
      return 10.0 ** -(d - 1)
    return 10.0 ** -d
  return 0.0001


def prices_from_pips(
  action: str,
  *,
  bid: float,
  ask: float,
  sl_pips: float,
  tp_pips: float,
  pip_size: float | None = None,
) -> tuple[float, float, float]:
  """Return (entry_ref, sl, tp) for a market test order."""
  act = action.upper()
  pip = float(pip_size) if pip_size and pip_size > 0 else 0.0001
  if act == "BUY":
    entry = float(ask)
    return entry, entry - float(sl_pips) * pip, entry + float(tp_pips) * pip
  if act == "SELL":
    entry = float(bid)
    return entry, entry + float(sl_pips) * pip, entry - float(tp_pips) * pip
  raise ValueError(f"action must be BUY/SELL, got {action!r}")


def write_manual_market_command(
  action: str,
  *,
  sl: float,
  tp: float,
  signal_id: str | None = None,
  bridge_dir: Path | None = None,
  exit_mode: str = "full",
  reason: str = "manual_bridge_test",
  **extra: Any,
) -> dict[str, Any]:
  """App → EA immediate market order via command.json (does not wait for new bar)."""
  act = str(action).upper()
  if act not in ("BUY", "SELL"):
    raise ValueError(f"action must be BUY/SELL, got {action!r}")
  payload: dict[str, Any] = {
    "cmd": "market",
    "action": act,
    "signal_id": signal_id or _manual_signal_id(),
    "sl": float(sl),
    "tp": float(tp),
    "exit_mode": exit_mode,
    "reason": reason,
    "updated_at": utc_now_iso(),
    **extra,
  }
  atomic_write_json(command_path(bridge_dir), payload)
  return payload


def write_manual_close_command(
  *,
  signal_id: str | None = None,
  bridge_dir: Path | None = None,
  reason: str = "manual_bridge_test_close",
  **extra: Any,
) -> dict[str, Any]:
  """App → EA immediate close of positions with bridge magic."""
  payload: dict[str, Any] = {
    "cmd": "close",
    "action": "FLAT",
    "signal_id": signal_id or _manual_signal_id("manual_close"),
    "reason": reason,
    "updated_at": utc_now_iso(),
    **extra,
  }
  atomic_write_json(command_path(bridge_dir), payload)
  return payload


def write_status(bridge_dir: Path | None = None, **fields: Any) -> None:
  payload = {"updated_at": utc_now_iso(), **fields}
  atomic_write_json(status_path(bridge_dir), payload)
