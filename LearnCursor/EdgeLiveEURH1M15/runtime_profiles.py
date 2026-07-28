"""Runtime profiles for dual-TF Live/Sim (H1 + M15) in one app."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class TfDefaults:
  """Mining / data defaults shared by live+sim for one timeframe."""

  tf: str
  start_date: str
  bar_minutes: int
  train_unit: str  # "months" | "weeks"
  train_length: int
  target_trades_per_week: float
  max_trades_per_day: int | None
  max_trades_per_week: int | None
  data_start_broker: str
  history_action: str
  history_period: str
  cache_name: str

  @property
  def bars_per_week(self) -> int:
    return 7 * 24 * (60 // self.bar_minutes)

  @property
  def report_dir(self) -> Path:
    return ROOT / "results" / self.tf.lower()

  @property
  def cache_parquet(self) -> Path:
    return ROOT / "data" / self.cache_name

  @property
  def cache_meta(self) -> Path:
    return self.cache_parquet.with_name(self.cache_parquet.stem + "_meta.json")


@dataclass(frozen=True)
class RuntimeProfile:
  """One concurrent bridge worker identity (TF × mode)."""

  tf: str
  mode: str  # "live" | "sim"
  instance_id: str
  magic: int
  bridge_subdir: str
  monitor_port: int

  @property
  def bridge_dir(self) -> Path:
    return ROOT / "mt5" / self.bridge_subdir

  @property
  def defaults(self) -> TfDefaults:
    return TF_DEFAULTS[self.tf]

  @property
  def report_dir(self) -> Path:
    return self.defaults.report_dir

  @property
  def bar_minutes(self) -> int:
    return self.defaults.bar_minutes

  @property
  def key(self) -> str:
    return f"{self.tf}_{self.mode}"


TF_DEFAULTS: dict[str, TfDefaults] = {
  "M15": TfDefaults(
    tf="M15",
    start_date="2025-01-01",
    bar_minutes=15,
    train_unit="weeks",
    train_length=3,
    target_trades_per_week=10.0,
    max_trades_per_day=2,
    max_trades_per_week=None,
    data_start_broker="2025-01-01 00:00",
    history_action="export_m15_history",
    history_period="M15",
    cache_name="mt5_eurusd_m15.parquet",
  ),
  "H1": TfDefaults(
    tf="H1",
    start_date="2023-01-01",
    bar_minutes=60,
    train_unit="months",
    train_length=3,
    target_trades_per_week=2.0,
    max_trades_per_day=None,
    max_trades_per_week=2,
    data_start_broker="2023-01-01 00:00",
    history_action="export_h1_history",
    history_period="H1",
    cache_name="mt5_eurusd_h1.parquet",
  ),
}

# Magics / ports preserved from the dual-app split for EA identity uniqueness.
PROFILES: dict[str, RuntimeProfile] = {
  "M15_live": RuntimeProfile(
    tf="M15", mode="live", instance_id="M15",
    magic=20260724, bridge_subdir="bridge_m15", monitor_port=8765,
  ),
  "M15_sim": RuntimeProfile(
    tf="M15", mode="sim", instance_id="M15",
    magic=20260726, bridge_subdir="bridge_sim_m15", monitor_port=8876,
  ),
  "H1_live": RuntimeProfile(
    tf="H1", mode="live", instance_id="H1",
    magic=20260725, bridge_subdir="bridge_h1", monitor_port=8865,
  ),
  "H1_sim": RuntimeProfile(
    tf="H1", mode="sim", instance_id="H1",
    magic=20260727, bridge_subdir="bridge_sim_h1", monitor_port=8877,
  ),
}


def get_profile(tf: str, mode: str = "live") -> RuntimeProfile:
  key = f"{str(tf).upper()}_{str(mode).lower()}"
  if key not in PROFILES:
    raise KeyError(f"Unknown runtime profile: {key}")
  return PROFILES[key]


def get_tf_defaults(tf: str) -> TfDefaults:
  t = str(tf).upper()
  if t not in TF_DEFAULTS:
    raise KeyError(f"Unknown timeframe: {t}")
  return TF_DEFAULTS[t]


def profile_for_port(port: int) -> RuntimeProfile | None:
  p = int(port)
  for profile in PROFILES.values():
    if profile.monitor_port == p:
      return profile
  return None


def profile_for_dir(path) -> RuntimeProfile | None:
  """Reverse lookup: which (tf, mode) owns this bridge dir? None if unknown.

  Lets bridge_dir-scoped code (ea_simulator, background) resolve the correct
  TF's results/ dir without depending on the calling process's active TF —
  safe even if multiple TF workers run inside one process (e.g. GUI threads).
  """
  try:
    resolved = Path(path).resolve()
  except Exception:
    return None
  for profile in PROFILES.values():
    if profile.bridge_dir.resolve() == resolved:
      return profile
  return None


def all_profiles() -> list[RuntimeProfile]:
  return list(PROFILES.values())


def live_profiles() -> list[RuntimeProfile]:
  return [p for p in PROFILES.values() if p.mode == "live"]


def sim_profiles() -> list[RuntimeProfile]:
  return [p for p in PROFILES.values() if p.mode == "sim"]
