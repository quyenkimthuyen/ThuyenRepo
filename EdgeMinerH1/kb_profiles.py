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


def is_legacy_kb_profile(profile_id: str | None) -> bool:
  """Profile default / knowledge.json cũ — không hiện trong picker giai đoạn."""
  return (profile_id or "").strip() == DEFAULT_PROFILE_ID


def list_era_profiles(*, include_legacy: bool = False) -> list[dict]:
  """Profile bộ nhớ theo giai đoạn — mặc định ẩn «Bộ nhớ chung» (default)."""
  profiles = [p for p in list_profiles() if p.get("exists")]
  if include_legacy:
    return profiles
  return [p for p in profiles if not is_legacy_kb_profile(p.get("id"))]


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


def _merge_rule_stat(target: dict, source: dict):
  for field in ("wins", "losses", "uses"):
    target[field] = target.get(field, 0) + source.get(field, 0)
  target["total_r"] = target.get("total_r", 0.0) + source.get("total_r", 0.0)


def merge_kb_profiles(
  source_ids: list[str],
  target_id: str,
  target_name: str,
  *,
  overwrite: bool = False,
) -> dict:
  """
  Ghép nhiều KB giai đoạn thành một profile mới (rule stats, genomes, ML samples).
  """
  from knowledge_base import MAX_GENOMES, MAX_ML_SAMPLES, MAX_RULE_EVENTS

  source_ids = [s.strip() for s in source_ids if s and s.strip()]
  source_ids = list(dict.fromkeys(source_ids))
  target_id = _slug(target_id)
  if len(source_ids) < 2:
    raise ValueError("Chọn ít nhất 2 giai đoạn để ghép.")
  if target_id == DEFAULT_PROFILE_ID:
    raise ValueError("Không thể ghi đè profile mặc định.")
  if target_id in source_ids:
    raise ValueError("Profile đích không được trùng với nguồn.")

  dest_path = profile_path(target_id)
  if dest_path.exists() and not overwrite:
    raise ValueError(f"Profile `{target_id}` đã tồn tại — đổi ID hoặc bật ghi đè.")

  merged = KnowledgeBase(dest_path)
  merged.rule_stats = {}
  merged.genomes = []
  merged.ml_experience = []
  merged.rule_events = []
  merged.epoch_history = []
  merged.epoch_count = 0
  merged.best_fitness_ever = -1e9

  trained_from: str | None = None
  trained_to: str | None = None
  total_epochs = 0
  sources_ok: list[str] = []

  for sid in source_ids:
    p = get_profile(sid)
    if not p or not p.get("exists"):
      raise ValueError(f"Giai đoạn `{sid}` không tồn tại hoặc chưa có file KB.")
    src = load_kb(sid)
    for key, st in src.rule_stats.items():
      if key not in merged.rule_stats:
        merged.rule_stats[key] = dict(st)
      else:
        _merge_rule_stat(merged.rule_stats[key], st)
    merged.genomes.extend(src.genomes)
    merged.ml_experience.extend(src.ml_experience)
    merged.rule_events.extend(src.rule_events)
    merged.epoch_history.extend(src.epoch_history)
    merged.epoch_count += int(src.epoch_count or 0)
    merged.best_fitness_ever = max(merged.best_fitness_ever, float(src.best_fitness_ever or -1e9))
    total_epochs += int(p.get("epochs") or 0)
    tf, tt = p.get("trained_from"), p.get("trained_to")
    if tf and (trained_from is None or str(tf) < trained_from):
      trained_from = str(tf)
    if tt and (trained_to is None or str(tt) > trained_to):
      trained_to = str(tt)
    sources_ok.append(sid)

  seen_genome: set[str] = set()
  unique_genomes: list[dict] = []
  for g in sorted(merged.genomes, key=lambda x: x.get("fitness", 0), reverse=True):
    sig = g.get("name") or json.dumps(g.get("dna") or g, sort_keys=True, default=str)[:200]
    if sig in seen_genome:
      continue
    seen_genome.add(sig)
    unique_genomes.append(g)
  merged.genomes = unique_genomes[:MAX_GENOMES]
  merged.ml_experience = merged.ml_experience[-MAX_ML_SAMPLES:]
  merged.rule_events = merged.rule_events[-MAX_RULE_EVENTS:]
  merged.save()

  note = f"merged:{','.join(sources_ok)}"
  return register_profile(
    target_id,
    target_name.strip() or target_id,
    trained_from,
    trained_to,
    total_epochs,
    note=note,
  )


def kb_valid_for_backtest(profile_id: str, oos_start, oos_end=None) -> tuple[bool, str]:
  """
  Kiểm tra profile có phù hợp backtest OOS không.
  Walk-forward dùng as_of mỗi tuần — KB có thể học đến cuối giai đoạn
  dù OOS bắt đầu sớm hơn (kinh nghiệm sau mốc tuần không được dùng).
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
    return True, (
      f"OK — KB học đến {trained_to[:10]}; OOS từ {str(oos_start)[:10]}. "
      "Walk-forward lọc kinh nghiệm theo as_of mỗi tuần."
    )
  return True, f"OK — KB giai đoạn đến {trained_to[:10]}, OOS từ {str(oos_start)[:10]}."


def suggest_profiles_for_oos(oos_start) -> list[dict]:
  """Gợi ý profile mà trained_to <= oos_start."""
  t = pd.Timestamp(oos_start)
  out = []
  for p in list_profiles():
    if not p.get("exists") or is_legacy_kb_profile(p.get("id")):
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
