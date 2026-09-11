"""BUG-07: Live EA HistoryFeed must never OrderSend (force paper fills like Sim)."""
from __future__ import annotations

from pathlib import Path

TRADE = Path(__file__).resolve().parents[2]
LIVE_EA = TRADE / "mt5" / "Experts" / "ForgeBridgeLive.mq5"
SIM_EA = TRADE / "mt5" / "Experts" / "ForgeBridgeLiveSim.mq5"


def test_live_ea_has_usepaperfills_forcing_history_feed():
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  assert "bool UsePaperFills()" in src, "Live EA missing UsePaperFills()"
  # HistoryFeed branch must force paper (never live OrderSend on historical bars)
  assert "BRIDGE_HISTORY_FEED" in src
  idx = src.find("bool UsePaperFills()")
  body = src[idx : idx + 250]
  assert "BRIDGE_HISTORY_FEED" in body
  assert "return true" in body


def test_live_history_paths_call_usepaperfills_not_raw_input():
  """Execution paths must gate on UsePaperFills(), not raw InpHistoryPaperFills."""
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  lines = src.splitlines()
  raw_uses = []
  in_usepaper = False
  for i, line in enumerate(lines, 1):
    if "bool UsePaperFills()" in line:
      in_usepaper = True
    if in_usepaper and line.strip() == "}":
      in_usepaper = False
      continue
    if in_usepaper:
      continue
    if "InpHistoryPaperFills" not in line:
      continue
    if "input bool" in line:
      continue
    if "UsePaperFills" in line:
      continue
    if "paper=" in line or "Comment" in line:
      continue
    raw_uses.append((i, line.strip()))
  assert raw_uses == [], f"HistoryFeed paths still use raw InpHistoryPaperFills: {raw_uses}"


def test_sim_ea_still_forces_history_paper():
  src = SIM_EA.read_text(encoding="utf-8", errors="replace")
  assert "bool UsePaperFills()" in src
  idx = src.find("bool UsePaperFills()")
  body = src[idx : idx + 250]
  assert "return true" in body


def test_history_paper_fills_use_bid_ask_spread():
  """Replay paper must fill BUY at Ask / SELL at Bid like live OrderSend."""
  for path in (LIVE_EA, SIM_EA):
    src = path.read_text(encoding="utf-8", errors="replace")
    assert "double HistSpreadPrice(const MqlRates &r)" in src
    assert '(action == "BUY") ? (r.open + spr) : r.open' in src
    assert "ask_h >= g_open_sl" in src
    fn = src[src.find("double HistSpreadPrice") : src.find("void ManagePaperHistory")]
    assert "SymbolInfoInteger" not in fn  # no weekend live tick spread


def test_history_feed_still_answers_history_export():
  """Workers need parquet; HistoryFeed used to skip ProcessHistoryRequest → no hits."""
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  idx = src.find("void OnTimer()")
  assert idx > 0
  body = src[idx : idx + 900]
  assert "ProcessHistoryRequest()" in body
  assert "ProcessHistoryFeed()" in body
  feed = body.find("BRIDGE_HISTORY_FEED")
  assert feed > 0
  assert body.find("ProcessHistoryRequest()", feed) < body.find("ProcessHistoryFeed()", feed)


def test_history_feed_waits_in_parallel_like_live():
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  start = src.rfind("void WaitHistoryDecisionsForBar(const string want)")
  assert start > 0
  body_start = src.find("{", start)
  end = src.find("void ProcessHistoryFeed()", start + 1)
  wait_fn = src[body_start:end]
  assert "TryReadDecisionForBar" in wait_fn
  assert "n_pending" in wait_fn
  assert "delay_ms + 6000" not in wait_fn
  assert "120000" in wait_fn
  feed = src[end:]
  assert "WaitHistoryDecisionsForBar(want)" in feed
  done = feed[: feed.find("MqlRates r = g_hist_rates")]
  assert "ReportPaperClose" not in done
  assert "left open like Live" in done


def test_paper_checks_sl_on_fill_bar():
  """Match broker: do not skip the entry bar when checking SL/TP."""
  for path in (LIVE_EA, SIM_EA):
    src = path.read_text(encoding="utf-8", errors="replace")
    assert "g_paper_held <= 1" not in src
    assert "g_paper_held++;" in src


def test_replay_open_sl_includes_one_spread():
  for path in (LIVE_EA, SIM_EA):
    src = path.read_text(encoding="utf-8", errors="replace")
    assert "g_rep_atr[idx] * atr + spr_pts * _Point" in src


def test_paper_max_hold_zero_not_immediate_close():
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  assert "g_max_hold > 0 && g_paper_held - 1 >= g_max_hold" in src
  sim = SIM_EA.read_text(encoding="utf-8", errors="replace")
  assert "void WaitHistoryDecisionsForBar" in sim
  assert "g_max_hold > 0 && g_paper_held - 1 >= g_max_hold" in sim
