"""Mine strategy hiện tại từ Trade Model (cùng logic paper monitor)."""
from __future__ import annotations

from typing import Any

import pandas as pd

from config import MIN_TRAIN_BARS
from data_loader import get_train_window_indices, load_gbpusd_h1
from feature_engine import FeatureMatrix
from optimizer import get_knowledge_base, optimize_on_window, set_kb_profile
from paper_monitor import _current_week_bounds
from strategy_miner import MinedStrategy, ensure_label_cache_for_df


def _model_params(model: dict) -> dict[str, Any]:
  return {
    "train_months": int(model.get("train_months", 3)),
    "use_kb": bool(model.get("use_kb", True)),
    "kb_profile": model.get("kb_profile"),
    "kb_snapshot": model.get("kb_snapshot"),
    "spread_pips": float(model.get("spread_pips", 1.0)),
    "slippage_pips": float(model.get("slippage_pips", 0.3)),
    "trade_model_id": model.get("id"),
    "label": model.get("label"),
  }


def mine_strategy_for_model(model: dict) -> tuple[MinedStrategy, dict[str, Any]]:
  """Mine strategy cho tuần hiện tại theo cấu hình trade model."""
  params = _model_params(model)
  df = load_gbpusd_h1()
  ensure_label_cache_for_df(len(df))
  fm = FeatureMatrix(df)
  week_start, week_end = _current_week_bounds(df)

  kb = None
  if params["use_kb"] and params["kb_profile"]:
    set_kb_profile(params["kb_profile"], params["kb_snapshot"])
    kb = get_knowledge_base(params["kb_profile"], params["kb_snapshot"])

  train_start, train_end = get_train_window_indices(
    df, week_start, params["train_months"],
  )
  if train_start is None or (train_end - train_start) < MIN_TRAIN_BARS:
    raise RuntimeError("Không đủ dữ liệu train cho tuần hiện tại.")

  strat = optimize_on_window(
    fm,
    train_start,
    train_end,
    use_learning=params["use_kb"],
    as_of=week_start,
    kb=kb,
  )
  if strat is None:
    raise RuntimeError("Không mine được strategy từ trade model.")

  meta = {
    **params,
    "week_start": str(week_start.date()),
    "week_end": str(week_end.date()),
    "data_end": str(df.index[-1]),
    "pair": "GBPUSD",
    "tf": "H1",
  }
  return strat, meta
