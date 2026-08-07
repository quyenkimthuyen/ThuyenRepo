"""Live readiness checklist — one green/red panel before Start Live."""
from __future__ import annotations

from typing import Any, Literal

CheckStatus = Literal["pass", "warn", "fail", "skip"]


def _item(
  key: str,
  label: str,
  status: CheckStatus,
  detail: str,
  *,
  hint: str | None = None,
) -> dict[str, Any]:
  return {
    "key": key,
    "label": label,
    "status": status,
    "detail": detail,
    "hint": hint,
  }


def assess_live_readiness(
  model: dict | None = None,
  *,
  decision: dict | None = None,
  file_status: dict | None = None,
  include_bridge: bool = True,
) -> dict[str, Any]:
  """
  Aggregate Health / Remine / Space / fp / Parity into a pre-Live checklist.

  ``include_bridge=False`` skips fp/parity (e.g. Trade Models tab without desk).
  """
  from gui.mining_space_health import assess_mining_space_freshness
  from gui.trade_model import (
    get_active_trade_model,
    load_model_kb_off_report,
    load_model_mining_baseline_report,
    load_model_remine_off_report,
    load_model_report,
    report_search_space_matches_model,
  )
  from mining_presets import match_preset_name
  from mt5_bridge.models import (
    conditions_fingerprint,
    get_model_run_params,
  )

  active = get_active_trade_model() if model is None else model
  decision = decision or {}
  file_status = file_status or {}
  items: list[dict[str, Any]] = []

  # 1) Trade Model
  if not active or not active.get("id"):
    items.append(_item(
      "model", "Trade Model active", "fail",
      "Chưa chọn Trade Model.",
      hint="Trade Models → chọn model rồi quay lại Bridge.",
    ))
    return {
      "verdict": "blocked",
      "ready": False,
      "summary": "Chưa sẵn sàng Live — chưa có Trade Model.",
      "items": items,
      "n_pass": 0, "n_warn": 0, "n_fail": 1, "n_skip": 0,
    }

  mid = str(active["id"])
  from gui.trade_model import format_model_label
  items.append(_item(
    "model", "Trade Model active", "pass",
    format_model_label(active),
  ))

  # 2) Health report KB ON + space match
  report_on = load_model_report(mid)
  if not report_on:
    items.append(_item(
      "health_on", "Report Health (KB ON)", "fail",
      "Chưa có report backtest của model.",
      hint="Trade Models → Sức khỏe → Chạy so sánh (bật KB ON).",
    ))
  elif not report_search_space_matches_model(report_on, active):
    items.append(_item(
      "health_on", "Report Health (KB ON)", "fail",
      "Report lệch mining search space của model.",
      hint="Sức khỏe → bật Chạy lại KB ON → Chạy so sánh.",
    ))
  else:
    on_r = (report_on.get("overall_oos") or {}).get("total_r")
    on_wr = (report_on.get("overall_oos") or {}).get("win_rate_pct")
    bits = []
    if on_r is not None:
      bits.append(f"{float(on_r):+.1f}R")
    if on_wr is not None:
      bits.append(f"WR {float(on_wr):.1f}%")
    items.append(_item(
      "health_on", "Report Health (KB ON)", "pass",
      " · ".join(bits) if bits else "Report khớp search space.",
    ))

  # 3) KB OFF (recommended)
  report_off = load_model_kb_off_report(mid)
  if not report_off:
    items.append(_item(
      "kb_off", "Baseline KB OFF", "warn",
      "Chưa có KB OFF — chưa đo lợi thế KB.",
      hint="Sức khỏe → Chạy so sánh (luôn tạo KB OFF).",
    ))
  else:
    off_r = (report_off.get("overall_oos") or {}).get("total_r")
    on_r = (report_on or {}).get("overall_oos", {}).get("total_r") if report_on else None
    if on_r is not None and off_r is not None and float(on_r) + 3 < float(off_r):
      items.append(_item(
        "kb_off", "Baseline KB OFF", "warn",
        f"KB ON ({float(on_r):+.1f}R) kém OFF ({float(off_r):+.1f}R).",
        hint="Xem chart KB ON/OFF trước khi Live lớn.",
      ))
    else:
      detail = f"OFF {float(off_r):+.1f}R" if off_r is not None else "Có report KB OFF."
      if on_r is not None and off_r is not None:
        detail = f"ON {float(on_r):+.1f}R vs OFF {float(off_r):+.1f}R"
      items.append(_item("kb_off", "Baseline KB OFF", "pass", detail))

  # 4) Remine ON vs OFF (optional until run)
  remine_off = load_model_remine_off_report(mid)
  if not remine_off or not report_on:
    items.append(_item(
      "remine", "Remine ON vs OFF", "skip",
      "Chưa chạy So Remine — mặc định Live = Remine ON.",
      hint="Sức khỏe → Remine ON/OFF → So Remine (khuyến nghị).",
    ))
  else:
    on_r = (report_on.get("overall_oos") or {}).get("total_r")
    off_r = (remine_off.get("overall_oos") or {}).get("total_r")
    on_wr = (report_on.get("overall_oos") or {}).get("win_rate_pct")
    off_wr = (remine_off.get("overall_oos") or {}).get("win_rate_pct")
    edge_r = (
      float(on_r) - float(off_r)
      if on_r is not None and off_r is not None else None
    )
    edge_wr = (
      float(on_wr) - float(off_wr)
      if on_wr is not None and off_wr is not None else None
    )
    bits = []
    if edge_r is not None:
      bits.append(f"ΔR {edge_r:+.1f}")
    if edge_wr is not None:
      bits.append(f"ΔWR {edge_wr:+.1f}pp")
    # Soft warn only if ON clearly worse on both axes
    if (
      edge_r is not None and edge_wr is not None
      and edge_r <= -5 and edge_wr <= -2
    ):
      items.append(_item(
        "remine", "Remine ON vs OFF", "warn",
        "Remine ON kém OFF rõ (" + " · ".join(bits) + ").",
        hint="Xem Remine ON/OFF trước khi Live; mặc định Bridge vẫn Remine ON.",
      ))
    elif edge_r is not None and edge_r <= -8 and (edge_wr is None or edge_wr < 1):
      items.append(_item(
        "remine", "Remine ON vs OFF", "warn",
        "Remine ON kém OFF về R (" + " · ".join(bits) + ").",
        hint="Đối chiếu WR trên Sức khỏe trước khi tăng lot.",
      ))
    else:
      items.append(_item(
        "remine", "Remine ON vs OFF", "pass",
        " · ".join(bits) if bits else "Đã có so sánh Remine.",
      ))

  # 5) Mining space vs baseline
  ss = active.get("mining_search_space") or {}
  preset = match_preset_name(ss) if ss else None
  if not ss or preset == "baseline":
    items.append(_item(
      "space", "Mining space vs baseline", "skip",
      "Model dùng baseline miner — không cần A/B space.",
    ))
  else:
    base_rep = load_model_mining_baseline_report(mid)
    if not report_on or not base_rep:
      items.append(_item(
        "space", "Mining space vs baseline", "warn",
        f"Preset `{preset}` chưa so baseline.",
        hint="Sức khỏe → Mining space → So mining space.",
      ))
    else:
      assess = assess_mining_space_freshness(
        report_on, base_rep, preset_name=preset,
      )
      v = assess.get("verdict")
      delta = assess.get("delta") or {}
      wr_d = delta.get("win_rate_pct")
      r_d = delta.get("total_r")
      q = []
      if wr_d is not None:
        q.append(f"ΔWR {wr_d:+.1f}pp")
      if r_d is not None:
        q.append(f"ΔR {r_d:+.1f}")
      if v == "stale":
        items.append(_item(
          "space", "Mining space vs baseline", "fail",
          assess.get("message") or "Preset có dấu hiệu lỗi thời.",
          hint="Audit preset / Grid lại / đổi Trade Model trước Live lớn.",
        ))
      elif v == "watch":
        items.append(_item(
          "space", "Mining space vs baseline", "warn",
          (assess.get("message") or "Theo dõi preset.")[:180],
          hint="Xem chart WR + R trên Sức khỏe.",
        ))
      elif v == "fresh":
        items.append(_item(
          "space", "Mining space vs baseline", "pass",
          " · ".join(q) if q else "Preset còn lợi thế vs baseline.",
        ))
      else:
        items.append(_item(
          "space", "Mining space vs baseline", "warn",
          assess.get("message") or "Chưa đủ dữ liệu space.",
        ))

  # 6–8) Bridge model_id + fp + Parity
  if include_bridge:
    decision_model = decision.get("model_id") or file_status.get("model_id")
    if not decision_model:
      items.append(_item(
        "bridge_model", "Model ID Bridge vs active", "skip",
        "Chưa có model_id trên decision/status.",
        hint="Start Live để Bridge ghi model đang chạy.",
      ))
    elif str(decision_model) == str(mid):
      items.append(_item(
        "bridge_model", "Model ID Bridge vs active", "pass",
        f"Khớp `{mid}`.",
      ))
    else:
      items.append(_item(
        "bridge_model", "Model ID Bridge vs active", "fail",
        f"decision=`{decision_model}` · active=`{mid}`.",
        hint="Stop rồi Start lại Bridge để nạp Trade Model đang chọn.",
      ))

    params = get_model_run_params(active, mid)
    model_fp = conditions_fingerprint(params)
    live_fp = decision.get("conditions_fp") or file_status.get("conditions_fp")
    if not live_fp:
      items.append(_item(
        "fp", "conditions_fp Bridge", "skip",
        "Chưa có decision/status — Start Bridge để xác nhận fp.",
        hint="Sau Start Live, checklist sẽ cập nhật fp.",
      ))
    elif str(live_fp) == str(model_fp):
      items.append(_item(
        "fp", "conditions_fp Bridge", "pass",
        f"Khớp model (`{str(model_fp)[:10]}…`).",
      ))
    else:
      items.append(_item(
        "fp", "conditions_fp Bridge", "fail",
        f"Bridge `{str(live_fp)[:10]}…` ≠ model `{str(model_fp)[:10]}…`.",
        hint="Stop rồi Start lại Bridge service.",
      ))

    from gui.bridge_model_monitor import compare_live_week_to_oos

    week = decision.get("week_start") or file_status.get("week_start")
    strat = decision.get("strategy_name") or file_status.get("strategy_name")
    if not week and not strat:
      items.append(_item(
        "parity", "Parity tuần Live vs Health", "skip",
        "Chưa có tuần/strategy trên decision.",
        hint="Đợi Bridge decide hoặc mở Parity trên desk.",
      ))
    else:
      parity = compare_live_week_to_oos(
        active,
        week_start=week,
        strategy_name=strat,
        conditions_fp=live_fp,
      )
      st_p = parity.get("status")
      if st_p == "match":
        items.append(_item(
          "parity", "Parity tuần Live vs Health", "pass",
          parity.get("message") or "MATCH",
        ))
      elif st_p == "mismatch":
        items.append(_item(
          "parity", "Parity tuần Live vs Health", "fail",
          parity.get("message") or "Strategy lệch Health.",
          hint="Kiểm tra fp / Restart Bridge / refresh Health.",
        ))
      elif st_p == "week_not_in_report":
        items.append(_item(
          "parity", "Parity tuần Live vs Health", "warn",
          parity.get("message") or "Tuần mới hơn tip OOS.",
          hint="Bình thường nếu đang live tuần sau OOS report.",
        ))
      else:
        items.append(_item(
          "parity", "Parity tuần Live vs Health", "skip",
          parity.get("message") or str(st_p),
        ))

  n_pass = sum(1 for i in items if i["status"] == "pass")
  n_warn = sum(1 for i in items if i["status"] == "warn")
  n_fail = sum(1 for i in items if i["status"] == "fail")
  n_skip = sum(1 for i in items if i["status"] == "skip")

  if n_fail:
    verdict, ready = "blocked", False
    summary = (
      f"Chưa sẵn sàng Live — **{n_fail}** mục đỏ "
      f"({n_pass} OK · {n_warn} cảnh báo · {n_skip} bỏ qua)."
    )
  elif n_warn:
    verdict, ready = "caution", True
    summary = (
      f"Có thể Live **micro lot** — **{n_warn}** cảnh báo "
      f"({n_pass} OK · {n_skip} bỏ qua)."
    )
  else:
    verdict, ready = "ready", True
    summary = (
      f"Sẵn sàng Live — **{n_pass}** mục đạt"
      + (f" · {n_skip} bỏ qua" if n_skip else "")
      + "."
    )

  return {
    "verdict": verdict,
    "ready": ready,
    "summary": summary,
    "items": items,
    "n_pass": n_pass,
    "n_warn": n_warn,
    "n_fail": n_fail,
    "n_skip": n_skip,
    "model_id": mid,
  }


def render_live_readiness(
  model: dict | None = None,
  *,
  decision: dict | None = None,
  file_status: dict | None = None,
  include_bridge: bool = True,
  expanded: bool = True,
  key_prefix: str = "live_ready",
) -> dict[str, Any]:
  """Streamlit panel for the checklist."""
  import streamlit as st

  result = assess_live_readiness(
    model,
    decision=decision,
    file_status=file_status,
    include_bridge=include_bridge,
  )
  verdict = result.get("verdict")
  title = "Checklist sẵn sàng Live"
  with st.expander(title, expanded=expanded):
    if verdict == "ready":
      st.success(result["summary"])
    elif verdict == "caution":
      st.warning(result["summary"])
    else:
      st.error(result["summary"])

    icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "○"}
    for it in result.get("items") or []:
      line = f"{icon.get(it['status'], '·')} **{it['label']}** — {it['detail']}"
      if it.get("hint") and it["status"] in ("fail", "warn", "skip"):
        line += f"  \n↳ _{it['hint']}_"
      st.markdown(line)

    st.caption(
      "Mặc định Bridge = **Remine ON**. Checklist đọc report Sức khỏe "
      "(KB / Remine / Space) + fp / Parity khi Bridge đã chạy."
    )
  return result
