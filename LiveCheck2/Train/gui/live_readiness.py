"""Live readiness checklist — one green/red panel before Start Live."""
from __future__ import annotations

from typing import Any, Literal

from gui.navigation import LABEL_TAB_OOS

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
  Aggregate Health / Remine / Space / fp into a pre-Live checklist.

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
      "model", "Trade Model", "fail",
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
  from gui.trade_model import format_model_label, format_model_short
  items.append(_item(
    "model", "Trade Model", "pass",
    format_model_short(active, max_len=56) or format_model_label(active),
  ))

  # 2) Health report KB ON + space match
  report_on = load_model_report(mid)
  if not report_on:
    items.append(_item(
      "health_on", "Report Health (KB ON)", "fail",
      "Chưa có report backtest của model.",
      hint=f"Trade Models → {LABEL_TAB_OOS} → Chạy so sánh (bật KB ON).",
    ))
  elif not report_search_space_matches_model(report_on, active):
    items.append(_item(
      "health_on", "Report Health (KB ON)", "fail",
      "Report lệch mining search space của model.",
      hint=f"{LABEL_TAB_OOS} → bật Chạy lại KB ON → Chạy so sánh.",
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
      hint=f"{LABEL_TAB_OOS} → Chạy so sánh (luôn tạo KB OFF).",
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
      hint=f"{LABEL_TAB_OOS} → Remine ON/OFF → So Remine (khuyến nghị).",
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
        hint=f"Đối chiếu WR trên {LABEL_TAB_OOS} trước khi tăng lot.",
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
        hint=f"{LABEL_TAB_OOS} → Mining space → So mining space.",
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
          hint=f"Xem chart WR + R trên {LABEL_TAB_OOS}.",
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

  # 6–7) Bridge model_id + fp (per-model slot when multi roster)
  # Live là giai đoạn sau OOS — không so Parity tuần vs Health.
  if include_bridge:
    per = file_status.get("per_model") if isinstance(file_status.get("per_model"), dict) else {}
    slot = per.get(mid) if isinstance(per.get(mid), dict) else {}
    roster_ids = [str(x) for x in (file_status.get("model_ids") or [])]
    decision_model = (
      slot.get("model_id")
      or decision.get("model_id")
      or file_status.get("model_id")
    )

    if mid in per or mid in roster_ids:
      items.append(_item(
        "bridge_model", "Model trong roster Bridge", "pass",
        f"Đang chạy · magic `{slot.get('magic') or '—'}`",
      ))
    elif not decision_model and not roster_ids and not per:
      items.append(_item(
        "bridge_model", "Model trong roster Bridge", "skip",
        "Chưa Start Bridge — chưa có roster/status.",
        hint="Start Live/Simulate để Bridge ghi model đang chạy.",
      ))
    elif str(decision_model) == str(mid):
      items.append(_item(
        "bridge_model", "Model trong roster Bridge", "pass",
        f"Khớp `{mid[:20]}…`.",
      ))
    else:
      items.append(_item(
        "bridge_model", "Model trong roster Bridge", "fail",
        f"decision=`{decision_model}` · checklist=`{mid}`.",
        hint="Stop rồi Start lại Bridge với đúng multiselect.",
      ))

    params = get_model_run_params(active, mid)
    model_fp = conditions_fingerprint(params)
    live_fp = (
      slot.get("conditions_fp")
      or decision.get("conditions_fp")
      or file_status.get("conditions_fp")
    )
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


def _decision_for_model(
  mid: str,
  *,
  file_status: dict | None,
  fallback: dict | None,
) -> dict:
  """Prefer decisions/<model_id>.json, then per_model slot, then shared decision."""
  from mt5_bridge.protocol import (
    BRIDGE_DIR,
    BRIDGE_SIM_DIR,
    decision_path_for,
    read_json,
  )

  for bridge_dir in (BRIDGE_DIR, BRIDGE_SIM_DIR):
    try:
      d = read_json(decision_path_for(mid, bridge_dir))
      if d:
        return d
    except Exception:
      pass
  per = (file_status or {}).get("per_model") if isinstance((file_status or {}).get("per_model"), dict) else {}
  slot = per.get(mid) if isinstance(per.get(mid), dict) else {}
  if slot:
    out = dict(slot)
    out.setdefault("model_id", mid)
    return out
  return dict(fallback or {})


def _render_checklist_items(result: dict) -> None:
  import streamlit as st

  icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "○"}
  for it in result.get("items") or []:
    line = f"{icon.get(it['status'], '·')} **{it['label']}** — {it['detail']}"
    if it.get("hint") and it["status"] in ("fail", "warn", "skip"):
      line += f"  \n↳ _{it['hint']}_"
    st.markdown(line)


def _aggregate_multi_results(per: list[dict[str, Any]]) -> dict[str, Any]:
  n_pass = sum(int(r["result"].get("n_pass") or 0) for r in per)
  n_warn = sum(int(r["result"].get("n_warn") or 0) for r in per)
  n_fail = sum(int(r["result"].get("n_fail") or 0) for r in per)
  n_skip = sum(int(r["result"].get("n_skip") or 0) for r in per)
  blocked = sum(1 for r in per if r["result"].get("verdict") == "blocked")
  caution = sum(1 for r in per if r["result"].get("verdict") == "caution")
  ready_n = sum(1 for r in per if r["result"].get("verdict") == "ready")
  if blocked:
    verdict, ready = "blocked", False
    summary = (
      f"**{blocked}/{len(per)}** model chưa sẵn sàng · "
      f"{ready_n} OK · {caution} cảnh báo · {n_fail} mục đỏ."
    )
  elif caution:
    verdict, ready = "caution", True
    summary = (
      f"Có thể Live micro — **{caution}/{len(per)}** model còn cảnh báo · "
      f"{ready_n} sẵn sàng."
    )
  else:
    verdict, ready = "ready", True
    summary = f"Sẵn sàng Live — **{len(per)}** model đạt checklist."
  return {
    "verdict": verdict,
    "ready": ready,
    "summary": summary,
    "items": [],
    "n_pass": n_pass,
    "n_warn": n_warn,
    "n_fail": n_fail,
    "n_skip": n_skip,
    "per_model": per,
    "model_ids": [r["id"] for r in per],
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
  """Streamlit panel for the checklist (single or multi Bridge roster)."""
  import streamlit as st

  from gui.trade_model import (
    format_model_short,
    get_bridge_runtime_model_ids,
    get_model_by_id,
  )

  bridge_ids = get_bridge_runtime_model_ids() if include_bridge else []

  # Multi-model Bridge: checklist từng model trong roster
  if include_bridge and len(bridge_ids) > 1:
    per: list[dict[str, Any]] = []
    for mid in bridge_ids:
      m = get_model_by_id(mid) or ({"id": mid} if model and str(model.get("id")) == mid else None)
      if m is None:
        m = {"id": mid}
      d = _decision_for_model(mid, file_status=file_status, fallback=decision)
      r = assess_live_readiness(
        m,
        decision=d,
        file_status=file_status,
        include_bridge=include_bridge,
      )
      per.append({"id": mid, "model": m, "result": r})

    result = _aggregate_multi_results(per)
    verdict = result.get("verdict")
    title = f"Checklist sẵn sàng Live · {len(per)} model"
    with st.expander(title, expanded=expanded):
      if verdict == "ready":
        st.success(result["summary"])
      elif verdict == "caution":
        st.warning(result["summary"])
      else:
        st.error(result["summary"])

      # Compact overview table
      overview = []
      for row in per:
        rr = row["result"]
        icon = {"ready": "✅", "caution": "⚠️", "blocked": "❌"}.get(
          rr.get("verdict"), "·"
        )
        overview.append({
          "Status": icon,
          "Model": format_model_short(row.get("model"), max_len=40),
          "OK": rr.get("n_pass") or 0,
          "Warn": rr.get("n_warn") or 0,
          "Fail": rr.get("n_fail") or 0,
        })
      import pandas as pd
      st.dataframe(pd.DataFrame(overview), hide_index=True, use_container_width=True)

      tabs = st.tabs([
        format_model_short(row.get("model"), max_len=28) for row in per
      ])
      for tab, row in zip(tabs, per):
        with tab:
          rr = row["result"]
          if rr.get("verdict") == "ready":
            st.success(rr["summary"])
          elif rr.get("verdict") == "caution":
            st.warning(rr["summary"])
          else:
            st.error(rr["summary"])
          _render_checklist_items(rr)

      st.caption(
        "Checklist theo **từng model trong Bridge roster**. "
        "Remine ON · Health report · conditions_fp khi Bridge đã chạy."
      )
    return result

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

    _render_checklist_items(result)

    st.caption(
      f"Mặc định Bridge = **Remine ON**. Checklist đọc báo cáo {LABEL_TAB_OOS} "
      "(KB / Remine / Space) + conditions_fp khi Bridge đã chạy."
    )
  return result
