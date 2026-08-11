"""Installed package store + live roster."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import INSTALLED_DIR, RESULTS_DIR, ROSTER_PATH


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def list_installed() -> list[dict]:
  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
  rows = []
  for d in sorted(INSTALLED_DIR.iterdir()):
    if not d.is_dir():
      continue
    man = _read(d / "manifest.json") or {}
    model = _read(d / "model.json") or {}
    rows.append({
      "install_id": d.name,
      "path": str(d),
      "model_id": man.get("model_id") or model.get("id"),
      "label": man.get("label") or model.get("label"),
      "symbol": man.get("symbol"),
      "timeframe": man.get("timeframe"),
      "oos_from": man.get("oos_from"),
      "oos_to": man.get("oos_to"),
      "lab": man.get("lab"),
      "kb_fingerprint": man.get("kb_fingerprint"),
      "installed_at": (_read(d / "install_meta.json") or {}).get("installed_at"),
    })
  return rows


def load_roster() -> dict:
  data = _read(ROSTER_PATH)
  if not data:
    return {"updated_at": None, "models": []}
  return data


def save_roster(models: list[dict]) -> dict:
  payload = {"updated_at": _now(), "models": models}
  _write(ROSTER_PATH, payload)
  return payload


def default_roster_from_installed() -> list[dict]:
  """Enable all installed; magics assigned separately."""
  rows = []
  for inst in list_installed():
    rows.append({
      "install_id": inst["install_id"],
      "model_id": inst["model_id"],
      "label": inst["label"],
      "symbol": inst["symbol"],
      "timeframe": inst["timeframe"],
      "enabled": True,
      "risk_pct": 1.0,
      "magic": None,
    })
  return rows
