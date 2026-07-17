"""
Quản lý nhiều Knowledge Base theo giai đoạn.

Mỗi profile = một file KB riêng, gắn khoảng thời gian train/learning.
Backtest chọn profile + mốc OOS → KB chỉ áp dụng kinh nghiệm trước as_of (causal).
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from knowledge_base import KnowledgeBase, KNOWLEDGE_PATH, LEARNING_DIR

PROFILES_DIR = LEARNING_DIR / "kb_profiles"
SNAPSHOTS_DIR = PROFILES_DIR / "snapshots"
INDEX_PATH = PROFILES_DIR / "index.json"
DEFAULT_PROFILE_ID = "default"
LATEST_SNAPSHOT = "latest"


def _slug(name: str) -> str:
  s = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())
  return s[:48] or "profile"


def _load_index() -> dict:
  if not INDEX_PATH.exists():
    return {"profiles": [], "default": DEFAULT_PROFILE_ID}
  with open(INDEX_PATH, encoding="utf-8") as f:
    return json.load(f)


def _save_index(data: dict):
  PROFILES_DIR.mkdir(parents=True, exist_ok=True)
  with open(INDEX_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)


def profile_path(profile_id: str) -> Path:
  if profile_id == DEFAULT_PROFILE_ID:
    return KNOWLEDGE_PATH
  return PROFILES_DIR / f"{profile_id}.json"


def snapshot_path(profile_id: str, cumulative_epoch: int) -> Path:
  return SNAPSHOTS_DIR / profile_id / f"ep{cumulative_epoch:03d}.json"


def profile_id_from_kb(kb: KnowledgeBase) -> str:
  if kb.path.resolve() == KNOWLEDGE_PATH.resolve():
    return DEFAULT_PROFILE_ID
  return kb.path.stem


def _snapshot_label(cumulative: int, meta: dict) -> str:
  wr = meta.get("win_rate_pct")
  tr = meta.get("total_r")
  se = meta.get("session_epoch")
  wr_s = f"{wr}%" if wr is not None else "?"
  tr_s = f"{tr:+.1f}R" if tr is not None else "?"
  return f"Epoch {cumulative} (run ep {se}) · WR {wr_s} · {tr_s}"


def _read_snapshots_meta(profile_id: str) -> list[dict]:
  p = get_profile(profile_id)
  if not p:
    return []
  return list(p.get("snapshots", []))


def _merge_snapshot_meta(profile_id: str, entry: dict):
  idx = _load_index()
  for i, p in enumerate(idx.get("profiles", [])):
    if p["id"] == profile_id:
      snaps = [s for s in p.get("snapshots", []) if s.get("cumulative") != entry["cumulative"]]
      snaps.append(entry)
      snaps.sort(key=lambda x: x.get("cumulative", 0))
      profiles = list(idx["profiles"])
      profiles[i] = {**p, "snapshots": snaps}
      idx["profiles"] = profiles
      _save_index(idx)
      return
  register_profile(profile_id, profile_id, None, None, 0, note="snapshots")
  _merge_snapshot_meta(profile_id, entry)


def save_epoch_snapshot(kb: KnowledgeBase, profile_id: str, metrics: dict) -> dict | None:
  """Lưu snapshot KB sau mỗi epoch học."""
  if profile_id == DEFAULT_PROFILE_ID:
    snap_root = SNAPSHOTS_DIR / DEFAULT_PROFILE_ID
  else:
    snap_root = SNAPSHOTS_DIR / profile_id
  snap_root.mkdir(parents=True, exist_ok=True)
  cumulative = len(kb.epoch_history)
  if cumulative <= 0:
    return None
  dest = snapshot_path(profile_id, cumulative)
  shutil.copy2(kb.path, dest)
  entry = {
    "cumulative": cumulative,
    "session_epoch": metrics.get("epoch"),
    "win_rate_pct": metrics.get("win_rate_pct"),
    "total_r": metrics.get("total_r"),
    "avg_rr": metrics.get("avg_rr"),
    "path": str(dest.relative_to(PROFILES_DIR)),
    "saved_at": datetime.now(timezone.utc).isoformat(),
    "label": _snapshot_label(cumulative, metrics),
  }
  _merge_snapshot_meta(profile_id, entry)
  return entry


def bootstrap_snapshots_if_missing(profile_id: str) -> int:
  """Profile cũ chưa có snapshot → lưu bản latest vào ep cuối epoch_history."""
  if profile_id == DEFAULT_PROFILE_ID:
    return 0
  snap_root = SNAPSHOTS_DIR / profile_id
  if snap_root.exists() and any(snap_root.glob("ep*.json")):
    return 0
  main = profile_path(profile_id)
  if not main.exists():
    return 0
  kb = KnowledgeBase(main)
  n = len(kb.epoch_history) or 1
  snap_root.mkdir(parents=True, exist_ok=True)
  dest = snapshot_path(profile_id, n)
  shutil.copy2(main, dest)
  last = kb.epoch_history[-1] if kb.epoch_history else {}
  entry = {
    "cumulative": n,
    "session_epoch": last.get("epoch", n),
    "win_rate_pct": last.get("win_rate_pct"),
    "total_r": last.get("total_r"),
    "avg_rr": last.get("avg_rr"),
    "path": str(dest.relative_to(PROFILES_DIR)),
    "saved_at": datetime.now(timezone.utc).isoformat(),
    "label": _snapshot_label(n, last) + " (bootstrap)",
    "bootstrap": True,
  }
  _merge_snapshot_meta(profile_id, entry)
  return n


def list_snapshots(profile_id: str, include_latest: bool = True) -> list[dict]:
  """Danh sách snapshot có thể chọn. cumulative=None → latest (file chính)."""
  bootstrap_snapshots_if_missing(profile_id)
  out: list[dict] = []
  if include_latest:
    main = profile_path(profile_id)
    if main.exists():
      kb = KnowledgeBase(main)
      last = kb.epoch_history[-1] if kb.epoch_history else {}
      out.append({
        "cumulative": None,
        "key": LATEST_SNAPSHOT,
        "label": "Latest (mới nhất — file chính)",
        "win_rate_pct": last.get("win_rate_pct"),
        "total_r": last.get("total_r"),
        "exists": True,
      })
  meta = {s["cumulative"]: s for s in _read_snapshots_meta(profile_id)}
  snap_root = SNAPSHOTS_DIR / profile_id
  if snap_root.exists():
    for path in sorted(snap_root.glob("ep*.json")):
      try:
        cumulative = int(path.stem.replace("ep", ""))
      except ValueError:
        continue
      m = meta.get(cumulative, {})
      out.append({
        "cumulative": cumulative,
        "key": str(cumulative),
        "label": m.get("label") or f"Epoch {cumulative}",
        "win_rate_pct": m.get("win_rate_pct"),
        "total_r": m.get("total_r"),
        "exists": path.exists(),
      })
  # dedupe latest if same as last cumulative file
  seen = set()
  deduped = []
  for s in out:
    k = s.get("key")
    if k in seen:
      continue
    seen.add(k)
    deduped.append(s)
  return deduped


def resolve_kb_path(profile_id: str, snapshot_epoch: int | str | None = None) -> Path:
  """Đường dẫn file KB: None/'latest' → main; int → snapshot epNNN."""
  if snapshot_epoch is None or snapshot_epoch == LATEST_SNAPSHOT or snapshot_epoch == "latest":
    return profile_path(profile_id)
  cumulative = int(snapshot_epoch)
  snap = snapshot_path(profile_id, cumulative)
  if snap.exists():
    return snap
  return profile_path(profile_id)


def list_profiles() -> list[dict]:
  idx = _load_index()
  profiles = idx.get("profiles", [])
  # đảm bảo default luôn có trong danh sách
  if not any(p["id"] == DEFAULT_PROFILE_ID for p in profiles):
    profiles.insert(0, {
      "id": DEFAULT_PROFILE_ID,
      "name": "Default (knowledge.json)",
      "path": str(KNOWLEDGE_PATH.name),
      "trained_from": None,
      "trained_to": None,
      "epochs": 0,
      "exists": KNOWLEDGE_PATH.exists(),
    })
  for p in profiles:
    p["exists"] = profile_path(p["id"]).exists()
  return profiles


def get_profile(profile_id: str) -> dict | None:
  for p in list_profiles():
    if p["id"] == profile_id:
      return p
  return None


def load_kb(profile_id: str | None = None, snapshot_epoch: int | str | None = None) -> KnowledgeBase:
  pid = profile_id or DEFAULT_PROFILE_ID
  path = resolve_kb_path(pid, snapshot_epoch)
  return KnowledgeBase(path)


def register_profile(
  profile_id: str,
  name: str,
  trained_from: str | None,
  trained_to: str | None,
  epochs: int = 0,
  note: str = "",
) -> dict:
  """Đăng ký / cập nhật metadata profile sau learning."""
  PROFILES_DIR.mkdir(parents=True, exist_ok=True)
  idx = _load_index()
  profiles = idx.get("profiles", [])
  entry = {
    "id": profile_id,
    "name": name,
    "path": profile_path(profile_id).name,
    "trained_from": trained_from,
    "trained_to": trained_to,
    "epochs": epochs,
    "note": note,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "exists": profile_path(profile_id).exists(),
  }
  replaced = False
  for i, p in enumerate(profiles):
    if p["id"] == profile_id:
      profiles[i] = {**p, **entry}
      replaced = True
      break
  if not replaced:
    profiles.append(entry)
  idx["profiles"] = profiles
  if idx.get("default") is None:
    idx["default"] = DEFAULT_PROFILE_ID
  _save_index(idx)
  return entry


def create_profile(profile_id: str, name: str, copy_from: str | None = None) -> KnowledgeBase:
  """Tạo KB profile mới (trống hoặc copy từ profile khác)."""
  path = profile_path(profile_id)
  if path.exists():
    return load_kb(profile_id)
  if copy_from:
    src = load_kb(copy_from)
    kb = KnowledgeBase(path)
    kb.rule_stats = dict(src.rule_stats)
    kb.genomes = list(src.genomes)
    kb.ml_experience = list(src.ml_experience)
    kb.rule_events = list(src.rule_events)
    kb.epoch_history = list(src.epoch_history)
    kb.epoch_count = src.epoch_count
    kb.best_fitness_ever = src.best_fitness_ever
    kb.save()
  else:
    kb = KnowledgeBase(path)
    kb.save()
  register_profile(profile_id, name, None, None, 0, note="created")
  return kb


def delete_profile(profile_id: str) -> bool:
  if profile_id == DEFAULT_PROFILE_ID:
    return False
  path = profile_path(profile_id)
  if path.exists():
    path.unlink()
  snap_root = SNAPSHOTS_DIR / profile_id
  if snap_root.exists():
    shutil.rmtree(snap_root)
  idx = _load_index()
  idx["profiles"] = [p for p in idx.get("profiles", []) if p["id"] != profile_id]
  _save_index(idx)
  return True


def kb_valid_for_backtest(profile_id: str, oos_start, oos_end=None) -> tuple[bool, str]:
  """
  Kiểm tra profile có phù hợp backtest OOS không.
  Khuyến nghị: trained_to <= oos_start (KB học trước giai đoạn test).
  """
  p = get_profile(profile_id)
  if not p or not p.get("exists"):
    return False, "Profile không tồn tại hoặc file KB trống."
  trained_to = p.get("trained_to")
  if not trained_to:
    return True, "Profile chưa ghi trained_to — vẫn dùng được với lọc causal as_of mỗi tuần."
  t_end = pd.Timestamp(trained_to)
  t_oos = pd.Timestamp(oos_start)
  if t_end > t_oos:
    return False, (
      f"KB học đến {trained_to[:10]} — sau mốc OOS bắt đầu {str(oos_start)[:10]}. "
      "Nên tạo KB chỉ trên giai đoạn TRƯỚC khi backtest."
    )
  return True, f"OK — KB giai đoạn đến {trained_to[:10]}, OOS từ {str(oos_start)[:10]}."


def suggest_profiles_for_oos(oos_start) -> list[dict]:
  """Gợi ý profile mà trained_to <= oos_start."""
  t = pd.Timestamp(oos_start)
  out = []
  for p in list_profiles():
    if not p.get("exists"):
      continue
    tt = p.get("trained_to")
    if tt is None or pd.Timestamp(tt) <= t:
      out.append(p)
  return out


def slice_df_for_period(df: pd.DataFrame, date_from: str | None, date_to: str | None) -> pd.DataFrame:
  out = df
  if date_from:
    out = out[out.index >= pd.Timestamp(date_from)]
  if date_to:
    out = out[out.index <= pd.Timestamp(date_to)]
  return out.copy()
