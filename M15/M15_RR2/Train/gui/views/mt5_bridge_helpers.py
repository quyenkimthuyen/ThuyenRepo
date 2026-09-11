"""Pure helpers for MT5 Bridge view (keeps mt5_bridge.py focused on UI)."""
from __future__ import annotations

from datetime import date, timedelta

from gui.desk_ui import bars_per_day, chart_bars_presets, symbol_label
from mt5_bridge.protocol import INSTANCE_ID, ROOT


def desk_symbol() -> str:
  """Fallback chart symbol when connection.json is empty (EUR vs GBP desks)."""
  try:
    from config import DEFAULT_PAIR
    pair = str(DEFAULT_PAIR or "").upper().replace("/", "")
    if pair:
      return pair
  except Exception:
    pass
  name = ROOT.name.upper()
  if "GBP" in name or INSTANCE_ID.upper().startswith(("M15G", "M5G", "G")):
    return "GBPUSD"
  return symbol_label()


def fmt_px(value) -> str:
  try:
    return f"{float(value):.5f}"
  except Exception:
    return "—"


def parse_ui_date(val) -> date | None:
  if val is None:
    return None
  if isinstance(val, date) and not isinstance(val, type(None)):
    # datetime is subclass of date
    try:
      return val if type(val) is date else val.date()  # type: ignore[attr-defined]
    except Exception:
      return val  # type: ignore[return-value]
  try:
    return date.fromisoformat(str(val)[:10])
  except Exception:
    return None


def months_spanning(d0: date, d1: date) -> list[str]:
  if d1 < d0:
    d0, d1 = d1, d0
  out: list[str] = []
  y, m = d0.year, d0.month
  while (y, m) <= (d1.year, d1.month):
    out.append(f"{y:04d}-{m:02d}")
    m += 1
    if m > 12:
      m = 1
      y += 1
  return out


def month_bounds(ym: str) -> tuple[date, date]:
  y, m = [int(x) for x in ym.split("-")[:2]]
  start = date(y, m, 1)
  if m == 12:
    end = date(y + 1, 1, 1) - timedelta(days=1)
  else:
    end = date(y, m + 1, 1) - timedelta(days=1)
  return start, end


def open_trade(trades: list[dict]) -> dict | None:
  for t in trades or []:
    if str(t.get("status") or "").lower() in ("open", "opened"):
      return t
  return None


def chart_bars_full() -> dict[str, int]:
  bpd = bars_per_day()
  return {
    **chart_bars_presets(),
    "6 tháng": bpd * 180,
    "1 năm": bpd * 365,
    "Tất cả": 200_000,
  }


CHART_RANGE_OPTIONS = ["1 ngày", "1 tuần", "1 tháng", "6 tháng", "1 năm", "Tất cả"]
