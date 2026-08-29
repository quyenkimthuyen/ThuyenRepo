"""BUG-04: extend host loss_guard with DD(R) / total loss(R) trips.

LiveCheck Train desks only implement consecutive-loss streaks. Live UI stores
``loss_guard_max_*_dd_r`` / ``loss_guard_max_*_loss_r`` — wire them here.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _local_now(now: datetime | None = None) -> datetime:
  if now is not None:
    if now.tzinfo is None:
      return now.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return now.astimezone()
  return datetime.now().astimezone()


def _parse_exit_ts(trade: dict) -> datetime | None:
  raw = (
    trade.get("exit_time")
    or trade.get("closed_at")
    or trade.get("updated_at")
    or trade.get("entry_time")
  )
  if raw is None or raw == "":
    return None
  try:
    import pandas as pd
    ts = pd.Timestamp(str(raw))
    if getattr(ts, "tzinfo", None) is None:
      return ts.to_pydatetime().replace(tzinfo=_local_now().tzinfo)
    return ts.to_pydatetime().astimezone()
  except Exception:
    return None


def trades_in_window(
  trades: list[dict],
  *,
  window: str,
  now: datetime | None = None,
) -> list[dict]:
  now_local = _local_now(now)
  window_l = str(window or "day").lower()
  selected: list[dict] = []
  for t in trades:
    ts = _parse_exit_ts(t)
    if ts is None:
      continue
    ts_local = ts.astimezone(now_local.tzinfo)
    if window_l == "day":
      if ts_local.date() != now_local.date():
        continue
    elif window_l in ("week", "iso_week"):
      if ts_local.isocalendar()[:2] != now_local.isocalendar()[:2]:
        continue
    else:
      if ts_local < now_local - timedelta(days=7):
        continue
    selected.append(t)
  return selected


def window_total_r(
  trades: list[dict],
  *,
  window: str,
  now: datetime | None = None,
) -> float:
  total = 0.0
  for t in trades_in_window(trades, window=window, now=now):
    try:
      if t.get("r") is not None:
        total += float(t["r"])
    except (TypeError, ValueError):
      continue
  return round(total, 4)


def window_drawdown_r(
  trades: list[dict],
  *,
  window: str,
  now: datetime | None = None,
) -> float:
  eq = peak = 0.0
  dd = 0.0
  for t in trades_in_window(trades, window=window, now=now):
    try:
      r = float(t["r"]) if t.get("r") is not None else 0.0
    except (TypeError, ValueError):
      continue
    eq += r
    peak = max(peak, eq)
    dd = max(dd, peak - eq)
  return round(dd, 4)


def _trade_model_id(trade: dict) -> str:
  return str(trade.get("model_id") or trade.get("id") or "").strip() or "_unknown"


def group_trades_by_model(trades: list[dict]) -> dict[str, list[dict]]:
  grouped: dict[str, list[dict]] = {}
  for t in trades:
    grouped.setdefault(_trade_model_id(t), []).append(t)
  return grouped


def _live_bridge_dirs() -> list[Path]:
  dirs: list[Path] = []
  seen: set[str] = set()

  def _add(path: Path) -> None:
    try:
      key = str(path.resolve())
    except OSError:
      key = str(path)
    if key in seen:
      return
    seen.add(key)
    dirs.append(Path(path))

  try:
    from books import bridge_dir, group_models_by_book
    from package_store import load_roster
    rows = [r for r in (load_roster().get("models") or []) if r.get("enabled")]
    groups = group_models_by_book(rows) if rows else {}
    for sym, tf in groups:
      _add(bridge_dir(sym, tf, sim=False))
  except Exception:
    pass
  if not dirs:
    try:
      from live_config import MT5_ROOT
      if MT5_ROOT.is_dir():
        for path in sorted(MT5_ROOT.glob("bridge_live_*")):
          if path.is_dir():
            _add(path)
    except Exception:
      pass
  return dirs


def _normalize_closed_trade(trade: dict) -> dict:
  row = dict(trade)
  try:
    from journal_view import _trade_r
    r = _trade_r(trade)
    if r is not None:
      row["r"] = r
  except Exception:
    pass
  return row


def desk_closed_trades(
  host_lg: Any,
  trades: list[dict] | None,
  *,
  bridge_dir: Path | None = None,
) -> list[dict]:
  """Closed trades for desk-total −R. Injected ``trades`` stay local (tests)."""
  if trades is not None:
    return host_lg.closed_auto_trades_chronologically(trades, bridge_dir=bridge_dir)
  rows: list[dict] = []
  try:
    from journal_view import _is_closed, load_trades
    for bdir in _live_bridge_dirs():
      for t in load_trades(bdir):
        if not _is_closed(t):
          continue
        rows.append(_normalize_closed_trade(t))
    if rows:
      return rows
  except Exception:
    pass
  return host_lg.closed_auto_trades_chronologically(None, bridge_dir=bridge_dir)


def evaluate_loss_guard_extended(
  host_lg: Any,
  cfg: dict | None,
  *,
  bridge_dir: Path | None = None,
  trades: list[dict] | None = None,
  now: datetime | None = None,
) -> dict[str, Any] | None:
  """Per-model DD day/week; Max −R/ngày is the sum of all models (desk)."""
  cfg = cfg or {}
  if not bool(cfg.get("loss_guard_enabled", False)):
    return None

  max_day_dd = float(cfg.get("loss_guard_max_day_dd_r") or 0)
  max_week_dd = float(cfg.get("loss_guard_max_week_dd_r") or 0)
  max_day_loss = float(cfg.get("loss_guard_max_day_loss_r") or 0)
  if max_day_dd <= 0 and max_week_dd <= 0 and max_day_loss <= 0:
    return None

  closed_book = host_lg.closed_auto_trades_chronologically(trades, bridge_dir=bridge_dir)
  halted = {str(x) for x in (cfg.get("loss_guard_halted_models") or []) if x}

  desk_closed = desk_closed_trades(host_lg, trades, bridge_dir=bridge_dir)
  desk_day_r = window_total_r(desk_closed, window="day", now=now)
  if max_day_loss > 0 and desk_day_r <= -max_day_loss + 1e-9:
    return {
      "enabled": True,
      "per_model": False,
      "scope": "day_loss",
      "value": desk_day_r,
      "limit": max_day_loss,
      "reason": (
        f"Risk guard: tổng −R ngày {desk_day_r:.2f}R ≤ -{max_day_loss:.2f}R "
        f"— FLAT tất cả model."
      ),
      "max_day_dd_r": max_day_dd,
      "max_week_dd_r": max_week_dd,
      "max_day_loss_r": max_day_loss,
      "day_total_r": desk_day_r,
      "desk_day_total_r": desk_day_r,
    }

  tripped = None
  worst_day_dd = worst_week_dd = 0.0
  for mid, rows in group_trades_by_model(closed_book).items():
    if mid in halted:
      continue
    day_dd = window_drawdown_r(rows, window="day", now=now)
    week_dd = window_drawdown_r(rows, window="week", now=now)
    worst_day_dd = max(worst_day_dd, day_dd)
    worst_week_dd = max(worst_week_dd, week_dd)
    hit = None
    if max_day_dd > 0 and day_dd + 1e-9 >= max_day_dd:
      hit = {
        "scope": "day_dd",
        "value": day_dd,
        "limit": max_day_dd,
        "reason": (
          f"Risk guard: {mid} DD ngày {day_dd:.2f}R ≥ {max_day_dd:.2f}R — FLAT model."
        ),
      }
    elif max_week_dd > 0 and week_dd + 1e-9 >= max_week_dd:
      hit = {
        "scope": "week_dd",
        "value": week_dd,
        "limit": max_week_dd,
        "reason": (
          f"Risk guard: {mid} DD tuần {week_dd:.2f}R ≥ {max_week_dd:.2f}R — FLAT model."
        ),
      }
    if hit is not None:
      tripped = {
        **hit,
        "per_model": True,
        "model_id": mid,
        "day_dd_r": day_dd,
        "week_dd_r": week_dd,
        "day_total_r": desk_day_r,
        "desk_day_total_r": desk_day_r,
      }
      break

  if tripped is None:
    return None
  return {
    "enabled": True,
    "max_day_dd_r": max_day_dd,
    "max_week_dd_r": max_week_dd,
    "max_day_loss_r": max_day_loss,
    "day_dd_r": tripped.get("day_dd_r", worst_day_dd),
    "week_dd_r": tripped.get("week_dd_r", worst_week_dd),
    "day_total_r": desk_day_r,
    "desk_day_total_r": desk_day_r,
    **tripped,
  }


def loss_guard_status_extended(
  host_lg: Any,
  cfg: dict | None,
  *,
  bridge_dir: Path | None = None,
  trades: list[dict] | None = None,
  now: datetime | None = None,
) -> dict[str, Any]:
  cfg = cfg or {}
  max_day_dd = float(cfg.get("loss_guard_max_day_dd_r") or 0)
  max_week_dd = float(cfg.get("loss_guard_max_week_dd_r") or 0)
  max_day_loss = float(cfg.get("loss_guard_max_day_loss_r") or 0)
  enabled = bool(cfg.get("loss_guard_enabled", False))
  closed = (
    host_lg.closed_auto_trades_chronologically(trades, bridge_dir=bridge_dir)
    if enabled else []
  )
  halted = {str(x) for x in (cfg.get("loss_guard_halted_models") or []) if x}
  day_dds: list[float] = []
  week_dds: list[float] = []
  day_rs: list[float] = []
  for mid, rows in group_trades_by_model(closed).items():
    if mid in halted:
      continue
    day_dds.append(window_drawdown_r(rows, window="day", now=now))
    week_dds.append(window_drawdown_r(rows, window="week", now=now))
    day_rs.append(window_total_r(rows, window="day", now=now))
  desk_day_r = round(sum(day_rs), 4) if day_rs else 0.0
  return {
    "enabled": enabled,
    "max_day_dd_r": max_day_dd,
    "max_week_dd_r": max_week_dd,
    "max_day_loss_r": max_day_loss,
    "day_dd_r": max(day_dds) if day_dds else 0.0,
    "week_dd_r": max(week_dds) if week_dds else 0.0,
    "day_total_r": desk_day_r,
    "desk_day_total_r": desk_day_r,
    "tripped": bool(cfg.get("loss_guard_tripped") or halted),
    "tripped_at": cfg.get("loss_guard_tripped_at"),
    "tripped_reason": cfg.get("loss_guard_tripped_reason"),
    "halted_models": sorted(halted),
  }


def patch_host_loss_guard(lg_module: Any) -> bool:
  """Replace host evaluate/status with DD-aware versions; wrap halt to close tickets.

  Idempotent. Always installs BUG-14 close-command wrap even when host already
  has DD helpers (Final_app).
  """
  changed = False

  def evaluate_loss_guard(cfg=None, *, bridge_dir=None, trades=None, now=None):  # noqa: ANN001
    return evaluate_loss_guard_extended(
      lg_module, cfg, bridge_dir=bridge_dir, trades=trades, now=now,
    )

  def loss_guard_status(cfg=None, *, bridge_dir=None, trades=None, now=None):  # noqa: ANN001
    return loss_guard_status_extended(
      lg_module, cfg, bridge_dir=bridge_dir, trades=trades, now=now,
    )

  lg_module.window_drawdown_r = window_drawdown_r
  lg_module.window_total_r = window_total_r
  lg_module.evaluate_loss_guard = evaluate_loss_guard
  lg_module.loss_guard_status = loss_guard_status
  lg_module._live_dd_ext = True
  changed = True

  # BUG-14: FLAT decision alone does not close open tickets — EA needs command.json.
  if not getattr(lg_module, "_live_halt_close", False) and hasattr(
    lg_module, "apply_loss_guard_halt",
  ):
    _orig_apply = lg_module.apply_loss_guard_halt

    def apply_loss_guard_halt(  # noqa: ANN001
      trip,
      *,
      bridge_dir=None,
      bar=None,
      model_id=None,
      model_ids=None,
    ):
      already = False
      try:
        from mt5_bridge.background import load_config
        already = bool((load_config() or {}).get("loss_guard_tripped"))
      except Exception:
        already = False
      decision = _orig_apply(
        trip,
        bridge_dir=bridge_dir,
        bar=bar,
        model_id=model_id,
        model_ids=model_ids,
      )
      # Book-wide halt: EA CloseAllByMagic. Per-model halt must not close the
      # whole book — FLAT decision for that model_id is enough.
      if not already and not (trip or {}).get("per_model"):
        try:
          from mt5_bridge.protocol import write_manual_close_command
          reason = str((trip or {}).get("reason") or "loss_guard")
          write_manual_close_command(
            bridge_dir=bridge_dir,
            reason=f"loss_guard:{reason}"[:240],
            signal_id="loss_guard_halt_close",
          )
        except Exception:
          pass
      return decision

    lg_module.apply_loss_guard_halt = apply_loss_guard_halt
    lg_module._live_halt_close = True
    changed = True

  return changed
