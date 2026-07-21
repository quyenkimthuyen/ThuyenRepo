"""Build MT5 EA package from active Trade Model."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from mt5_export.live_strategy import mine_strategy_for_model
from mt5_export.mqh_writer import write_json, write_mqh
from mt5_export.serialize import build_export_payload

ROOT = Path(__file__).resolve().parent.parent
MT5_SRC = ROOT / "mt5"
DEFAULT_OUT = ROOT / "mt5" / "output"


def _load_model(model_id: str | None) -> dict:
  from gui.trade_model import get_model_by_id, load_active_model_id

  mid = model_id or load_active_model_id()
  if not mid:
    raise RuntimeError("Chưa có trade model active. Tạo/chọn model trong GUI trước.")
  model = get_model_by_id(mid)
  if not model:
    raise RuntimeError(f"Trade model `{mid}` không tồn tại.")
  return model


def export_mt5_package(
  *,
  model_id: str | None = None,
  out_dir: str | Path | None = None,
  remine: bool = True,
) -> Path:
  """
  Export gói MT5 Expert Advisor:
  - Copy ForexForgeEA.mq5 + Include/*.mqh
  - Generate ForgeConfig.mqh từ strategy tuần hiện tại
  - forge_export.json (tham khảo)
  """
  model = _load_model(model_id)
  out = Path(out_dir) if out_dir else DEFAULT_OUT
  if out.exists():
    shutil.rmtree(out)
  out.mkdir(parents=True, exist_ok=True)

  if remine:
    strat, meta = mine_strategy_for_model(model)
    payload = build_export_payload(strat, meta)
  else:
    from gui.trade_model import load_model_report

    report = load_model_report(model["id"])
    if not report or not report.get("last_strategy"):
      raise RuntimeError("Không có last_strategy — chạy export với remine=True.")
    meta = {
      "trade_model_id": model["id"],
      "label": model.get("label"),
      "week_start": "cached",
      "spread_pips": model.get("spread_pips", 1.0),
      "slippage_pips": model.get("slippage_pips", 0.3),
      "pair": "EURUSD",
      "tf": "H1",
    }
    strat_dict = dict(report["last_strategy"])
    strat_dict.setdefault("score_threshold", 1.0)
    strat_dict.setdefault("min_rules_match", 2)
    strat_dict.setdefault("min_bars_between", 4)
    strat_dict.setdefault("max_trades_per_week", 2)
    from config import DEFAULT_MAX_HOLD_BARS, DEFAULT_TRAIL_ACTIVATE_R, DEFAULT_TRAIL_DISTANCE_R
    strat_dict.setdefault("max_hold_bars", DEFAULT_MAX_HOLD_BARS)
    strat_dict.setdefault("session_filter", True)
    strat_dict.setdefault("partial_pct", 0.4)
    strat_dict.setdefault("partial_at_r", 1.2)
    strat_dict.setdefault("trail_activate_r", DEFAULT_TRAIL_ACTIVATE_R)
    strat_dict.setdefault("trail_distance_r", DEFAULT_TRAIL_DISTANCE_R)
    payload = {
      "format": "forexforge_mt5_v1",
      "meta": meta,
      "strategy": strat_dict,
      "ml": {"enabled": False, "features": []},
    }

  stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  write_mqh(payload, out / "Include" / "ForgeConfig.mqh")
  write_json(payload, out / "forge_export.json")

  # Static EA sources
  ea_src = MT5_SRC / "ForexForgeEA.mq5"
  inc_src = MT5_SRC / "Include"
  if not ea_src.exists():
    raise RuntimeError(f"Thiếu template EA: {ea_src}")

  shutil.copy2(ea_src, out / "ForexForgeEA.mq5")
  if inc_src.exists():
    for mqh in inc_src.glob("*.mqh"):
      if mqh.name == "ForgeConfig.mqh":
        continue
      shutil.copy2(mqh, out / "Include" / mqh.name)

  readme = MT5_SRC / "README.md"
  if readme.exists():
    shutil.copy2(readme, out / "README.md")

  (out / "EXPORT_INFO.txt").write_text(
    f"ForexForge MT5 export\n"
    f"model={model['id']}\n"
    f"label={model.get('label', '')}\n"
    f"stamp={stamp}\n"
    f"strategy={payload['strategy'].get('name', '')}\n",
    encoding="utf-8",
  )
  return out
