"""Shared Trade Model package format (v1)."""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_VERSION = 1
FORMAT_NAME = "edgeminer.trade_model_package"
PACKAGE_EXT = ".tmpkg"

REQUIRED_MODEL_KEYS = (
  "id",
  "label",
  "mining_search_space",
  "train_weeks",
  "feature_profile",
)

# Live schedule-parity requires frozen weekly genomes. Packages without a usable
# schedule.json are rejected on export/import and cannot be enabled on Live.
SCHEDULE_REQUIRED = True
MIN_SCHEDULE_WEEKS = 1


def utc_now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def schedule_weekly_count(schedule: dict[str, Any] | None) -> int:
  if not isinstance(schedule, dict):
    return 0
  return len(list(schedule.get("weekly") or []))


def validate_schedule_payload(schedule: dict[str, Any] | None) -> list[str]:
  """Return errors if schedule is missing/unusable for Live parity."""
  if not isinstance(schedule, dict):
    return ["missing schedule.json (export lab schedule before packaging)"]
  weekly = list(schedule.get("weekly") or [])
  if len(weekly) < MIN_SCHEDULE_WEEKS:
    return [
      f"schedule.json weekly[] empty/too short "
      f"(need ≥{MIN_SCHEDULE_WEEKS}, got {len(weekly)})"
    ]
  with_strat = sum(1 for w in weekly if isinstance((w or {}).get("strategy"), dict))
  if with_strat < MIN_SCHEDULE_WEEKS:
    return ["schedule.json weekly entries missing strategy genomes"]
  return []


def package_has_usable_schedule(pkg_dir: Path) -> bool:
  path = Path(pkg_dir) / "schedule.json"
  if not path.exists():
    return False
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return False
  return not validate_schedule_payload(data)


def _sha256_bytes(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
      h.update(chunk)
  return h.hexdigest()


def build_manifest(
  *,
  model: dict[str, Any],
  lab: dict[str, Any],
  symbol: str,
  timeframe: str,
  files: list[str],
  kb_fingerprint: str | None = None,
) -> dict[str, Any]:
  return {
    "package_version": PACKAGE_VERSION,
    "format": FORMAT_NAME,
    "created_at": utc_now_iso(),
    "lab": lab,
    "model_id": model.get("id"),
    "label": model.get("label"),
    "symbol": symbol,
    "timeframe": timeframe,
    "oos_from": model.get("oos_from"),
    "oos_to": model.get("oos_to"),
    "feature_profile": model.get("feature_profile"),
    "use_kb": bool(model.get("use_kb", True)),
    "kb_fingerprint": kb_fingerprint,
    "files": files,
  }


def validate_model_payload(model: dict[str, Any]) -> list[str]:
  errors: list[str] = []
  for k in REQUIRED_MODEL_KEYS:
    if model.get(k) in (None, "", {}):
      errors.append(f"model.json missing/empty: {k}")
  if model.get("use_kb", True) and not model.get("mining_search_space"):
    errors.append("use_kb models require mining_search_space")
  return errors


def validate_package_dir(pkg_dir: Path, *, require_schedule: bool | None = None) -> list[str]:
  errors: list[str] = []
  require_sched = SCHEDULE_REQUIRED if require_schedule is None else bool(require_schedule)
  man_path = pkg_dir / "manifest.json"
  if not man_path.exists():
    return ["missing manifest.json"]
  manifest = json.loads(man_path.read_text(encoding="utf-8"))
  if manifest.get("format") != FORMAT_NAME:
    errors.append(f"bad format: {manifest.get('format')}")
  ver = int(manifest.get("package_version") or 0)
  if ver < 1 or ver > PACKAGE_VERSION:
    errors.append(f"unsupported package_version={ver} (app supports ≤{PACKAGE_VERSION})")
  model_path = pkg_dir / "model.json"
  if not model_path.exists():
    errors.append("missing model.json")
  else:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    errors.extend(validate_model_payload(model))
  if manifest.get("use_kb") and not (pkg_dir / "kb_pin.json").exists():
    errors.append("use_kb=true but kb_pin.json missing")
  sched_path = pkg_dir / "schedule.json"
  if require_sched or sched_path.exists():
    schedule = None
    if sched_path.exists():
      try:
        schedule = json.loads(sched_path.read_text(encoding="utf-8"))
      except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"schedule.json unreadable: {exc}")
        schedule = None
    errors.extend(validate_schedule_payload(schedule))
  sums = pkg_dir / "SHA256SUMS"
  if sums.exists():
    for line in sums.read_text(encoding="utf-8").splitlines():
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      parts = line.split()
      if len(parts) < 2:
        continue
      digest, name = parts[0], parts[-1]
      fp = pkg_dir / name
      if not fp.exists():
        errors.append(f"SHA256SUMS lists missing file: {name}")
      elif _sha256_file(fp) != digest:
        errors.append(f"checksum mismatch: {name}")
  return errors


def write_package(
  out_path: Path,
  *,
  manifest: dict[str, Any],
  model: dict[str, Any],
  metrics: dict[str, Any] | None = None,
  kb_pin_src: Path | None = None,
  schedule: dict[str, Any] | None = None,
) -> Path:
  """Write a .tmpkg zip (also leaves an unpacked folder next to it for inspection)."""
  out_path = Path(out_path)
  if out_path.suffix.lower() != PACKAGE_EXT:
    out_path = out_path.with_suffix(PACKAGE_EXT)
  out_path.parent.mkdir(parents=True, exist_ok=True)
  staging = out_path.with_suffix("")
  if staging.exists():
    import shutil
    shutil.rmtree(staging)
  staging.mkdir(parents=True)

  files = ["manifest.json", "model.json"]
  (staging / "model.json").write_text(
    json.dumps(model, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  if metrics is not None:
    (staging / "metrics.json").write_text(
      json.dumps(metrics, indent=2, ensure_ascii=False, default=str) + "\n",
      encoding="utf-8",
    )
    files.append("metrics.json")
  kb_fp = None
  if kb_pin_src and Path(kb_pin_src).exists():
    dest = staging / "kb_pin.json"
    dest.write_bytes(Path(kb_pin_src).read_bytes())
    kb_fp = _sha256_file(dest)[:16]
    files.append("kb_pin.json")
  sched_errs = validate_schedule_payload(schedule)
  if SCHEDULE_REQUIRED and sched_errs:
    raise ValueError("package invalid: " + "; ".join(sched_errs))
  if schedule is not None and not sched_errs:
    (staging / "schedule.json").write_text(
      json.dumps(schedule, indent=2, ensure_ascii=False, default=str) + "\n",
      encoding="utf-8",
    )
    files.append("schedule.json")

  manifest = dict(manifest)
  manifest["files"] = files
  manifest["has_schedule"] = "schedule.json" in files
  manifest["schedule_weeks"] = schedule_weekly_count(schedule) if schedule else 0
  if kb_fp:
    manifest["kb_fingerprint"] = kb_fp
  (staging / "manifest.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )

  sum_lines = []
  for name in files:
    digest = _sha256_file(staging / name)
    sum_lines.append(f"{digest}  {name}")
  (staging / "SHA256SUMS").write_text("\n".join(sum_lines) + "\n", encoding="utf-8")

  errs = validate_package_dir(staging)
  if errs:
    raise ValueError("package invalid: " + "; ".join(errs))

  with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for p in staging.iterdir():
      if p.is_file():
        zf.write(p, arcname=p.name)
  return out_path


def extract_package(tmpkg: Path, dest_dir: Path) -> Path:
  dest_dir = Path(dest_dir)
  dest_dir.mkdir(parents=True, exist_ok=True)
  with zipfile.ZipFile(tmpkg, "r") as zf:
    zf.extractall(dest_dir)
  errs = validate_package_dir(dest_dir)
  if errs:
    raise ValueError("package invalid after extract: " + "; ".join(errs))
  return dest_dir


def read_json(path: Path) -> Any:
  return json.loads(Path(path).read_text(encoding="utf-8"))
