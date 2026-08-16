from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from aiapp.backtest.engine import run_backtest
from aiapp.config import RESULTS, Desk, load_protocol
from aiapp.data.ohlc import load_ohlc, slice_range
from aiapp.features.build import build_features
from aiapp.strategy.robust_pullback import Params, param_grid


@dataclass
class SelectedModel:
  desk: str
  params: Params
  train: dict
  validate: dict
  test: dict | None = None

  def to_dict(self) -> dict[str, Any]:
    return {
      "desk": self.desk,
      "params": self.params.to_dict(),
      "param_key": self.params.key(),
      "train": self.train,
      "validate": self.validate,
      "test": self.test,
    }


def _passes_validate(m: dict, protocol: dict) -> bool:
  return (
    int(m.get("n_trades") or 0) >= int(protocol.get("min_validate_trades") or 12)
    and float(m.get("win_rate_pct") or 0) >= float(protocol.get("min_validate_wr") or 40)
    and float(m.get("max_drawdown_r") or 999) <= float(protocol.get("max_validate_dd") or 15)
    and float(m.get("total_r") or 0) > 0
  )


def optimize_desk(desk: Desk, protocol: dict | None = None) -> SelectedModel:
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)

  df = load_ohlc(desk.data_parquet)
  feat = build_features(df)
  tr = proto["train"]
  va = proto["validate"]
  feat_tr = slice_range(feat, tr["from"], tr["to"])
  feat_va = slice_range(feat, va["from"], va["to"])

  candidates: list[tuple[float, Params, dict, dict]] = []
  for p in param_grid():
    bt_tr = run_backtest(feat_tr, p, spread_pips=desk.spread_pips, slippage_pips=slip)
    # Soft gate: train must not be deeply negative
    if float(bt_tr.metrics.get("total_r") or 0) < -20:
      continue
    bt_va = run_backtest(feat_va, p, spread_pips=desk.spread_pips, slippage_pips=slip)
    if not _passes_validate(bt_va.metrics, proto):
      continue
    score = float(bt_va.metrics.get("robust_score") or -1e9)
    candidates.append((score, p, bt_tr.metrics, bt_va.metrics))

  if not candidates:
    raise RuntimeError(
      f"{desk.id}: no param set passed validate gates "
      f"(min_trades/wr/dd/total_r). Refusing to deploy a losing model."
    )

  candidates.sort(key=lambda x: x[0], reverse=True)
  score, best_p, tr_m, va_m = candidates[0]
  return SelectedModel(desk=desk.id, params=best_p, train=tr_m, validate=va_m)


def evaluate_test(desk: Desk, model: SelectedModel, protocol: dict | None = None) -> SelectedModel:
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)
  te = proto["test"]
  df = load_ohlc(desk.data_parquet)
  feat = build_features(df)
  feat_te = slice_range(feat, te["from"], te["to"])
  bt = run_backtest(feat_te, model.params, spread_pips=desk.spread_pips, slippage_pips=slip)
  model.test = bt.metrics
  return model


def save_model(model: SelectedModel) -> Path:
  RESULTS.mkdir(parents=True, exist_ok=True)
  path = RESULTS / f"model_{model.desk}.json"
  path.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")
  # also store trades equity summary path placeholder
  return path
