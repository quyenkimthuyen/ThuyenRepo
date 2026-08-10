"""Thuật ngữ & nhãn UI — giúp app dễ hiểu hơn cho người dùng."""
from __future__ import annotations

import streamlit as st

# --- Giải thích ngắn (dùng trong help= / caption) ---

HELP = {
  "oos": "Giai đoạn **kiểm chứng** — chỉ mô phỏng lệnh, không dùng để tối ưu chiến lược (OOS).",
  "train_weeks": "Số tuần dữ liệu gần nhất để **tìm chiến lược mới mỗi tuần** (walk-forward).",
  "train_months": "Đã thay bằng cửa sổ học 3/6/9 tuần.",
  "kb": "**Bộ nhớ kinh nghiệm (KB)** — lưu rule/chiến lược đã học từ các tuần trước.",
  "kb_on": "Dùng bộ nhớ kinh nghiệm khi tìm chiến lược (thường tốt hơn, cần kiểm chứng thêm).",
  "kb_off": "Không dùng bộ nhớ — đánh giá **khách quan nhất**, nên chạy trước khi tin vào kết quả.",
  "epoch": "**Vòng học (epoch)** — chạy cả giai đoạn một lần để cập nhật bộ nhớ (ep001, ep002, …).",
  "spread": "Chênh lệch mua/bán (pip) — trừ vào mỗi lệnh khi mô phỏng.",
  "slippage": "Trượt giá (pip) — mô phỏng khớp lệnh kém hơn giá lý tưởng.",
  "r_unit": "**Đơn vị R** — lợi nhuận theo rủi ro mỗi lệnh (1R = ±1 lần risk).",
  "drawdown": "**Max DD** — mức sụt giảm lớn nhất từ đỉnh equity (đơn vị R).",
  "win_rate": "**WR** — tỷ lệ lệnh thắng trong giai đoạn kiểm chứng.",
  "rr": "**RR** — lãi trung bình ÷ lỗ trung bình mỗi lệnh.",
  "profit_factor": "**PF** — tổng lãi ÷ tổng lỗ; >1 nghĩa là có lời.",
  "risk_of_ruin": "**RoR** — ước lượng xác suất phá sản (không phải Monte Carlo đầy đủ).",
  "holdout": "Giữ **vài tháng cuối** chỉ để test — không dùng khi tối ưu walk-forward chính.",
  "trade_profile": "**Trade Model** — cấu hình giao dịch: cửa sổ học, bộ nhớ, giai đoạn test, phí.",
  "walk_forward": "**WF** — mỗi tuần học trên data gần → trade tuần sau → lặp (tránh nhìn trước).",
  "paper": (
    "**Sim fills** (tên code cũ: *paper fills*) — khớp lệnh mô phỏng OHLC trong "
    "**Compare Trade** / HistoryFeed (`mt5_bridge.paper_fill.PaperBook`). "
    "**Không** phải desk Paper Monitor (đã gỡ khỏi nav)."
  ),
  "active_model": (
    "**Active** — Trade Model đang xem/phân tích (dropdown Trade Models). "
    "Không điều khiển lệnh Live/Sim."
  ),
  "bridge_roster": (
    "**Bridge roster** — 1–5 model chọn trên MT5 Bridge cho Live/Simulate. "
    "Archive/xóa sẽ gỡ id khỏi roster; id còn sót = *id ma* (nút Dọn roster)."
  ),
  "archive_model": (
    "**Archive** — cất model nghiên cứu (giữ report), ẩn khỏi Active/Bridge. "
    "Ưu tiên hơn Xóa cứng. Restore không tự add lại Bridge."
  ),
  "mt5_bridge": (
    "**MT5 Bridge** — App quyết định → EA `ForgeBridge` mở/đóng lệnh trên MT5. "
    "Live = thật/demo; Simulate = replay History Feed."
  ),
  "grid_search": "**Grid Search** — thử nhiều combo tham số để tìm setting tốt hơn.",
  "mining_preset": (
    "**Mining preset** — không gian tìm chiến lược (RR, exit, anti-chase…). "
    "Mặc định app: **elite_or_quality** (void RSI/VWAP OR, RR 3.2–4, exit full). "
    "Xem bảng Chi tiết preset trong Cài đặt."
  ),
  "remine": "**Remine** — mỗi tuần mine lại strategy trên cửa sổ học gần nhất (không đổi Trade Model).",
  "parity": "**Parity** — đối chiếu strategy tuần Live với weekly_log Health OOS.",
  "fp": "**fp / conditions_fp** — fingerprint điều kiện remine; Live/Sim phải khớp Trade Model.",
  "history_feed": "**History Feed** — EA phát lại nến lịch sử theo Từ/Đến để Simulate.",
}

# --- Nhãn metric (hiển thị) ---

METRIC_LABELS = {
  "win_rate_pct": "Tỷ lệ thắng",
  "avg_rr": "Lãi/lỗ (RR)",
  "total_r": "Tổng lợi nhuận (R)",
  "max_drawdown_r": "Sụt giảm tối đa",
  "profit_factor": "Hệ số lợi nhuận",
  "trades_per_week": "Lệnh/tuần",
  "n_trades": "Số lệnh",
  "max_win_streak": "Chuỗi thắng dài nhất",
  "max_loss_streak": "Chuỗi thua dài nhất",
  "risk_of_ruin_pct": "Xác suất phá sản",
}

CONSTRAINT_LABELS = {
  "profitable": "Có lời (1 năm gần nhất)",
  "win_rate_above_60": "Tỷ lệ thắng > 60% (1 năm)",
  "rr_above_2": "Lãi/lỗ > 2 (1 năm)",
  # trades_per_week_target retired — tần suất không còn gate live/checklist
}

# --- Tên hiển thị profile bộ nhớ (ID kỹ thuật → tên dễ hiểu) ---

MEMORY_PROFILE_NAMES: dict[str, str] = {
  "default": "Bộ nhớ chung",
  "era_2025_full": "Học đủ năm 2025",
  "era_2025_h2": "Học 6 tháng cuối 2025",
  "era_2022_2025": "Học 2022–2025",
  "era_2023_2025": "Học 2023–2025",
  "era_2024_2025": "Học 2024–2025",
  # legacy (hiển thị nếu còn file cũ)
  "era_2024": "Học 2024–2025",
  "era_2023_2024": "Học 2023–2025",
  "era_2022_2024": "Học 2022–2025",
  "era_2022_2023": "Học 2022–2023",
}


def format_memory_profile(profile_id: str | None) -> str:
  """ID profile bộ nhớ → tên hiển thị (ưu tiên Settings)."""
  if not profile_id:
    return "—"
  try:
    from gui.app_settings import kb_profile_label
    label = kb_profile_label(profile_id)
    if label and not label.startswith("era_"):
      return f"Học {label}" if not label.startswith("Học ") else label
  except Exception:
    pass
  pid = str(profile_id)
  if pid in MEMORY_PROFILE_NAMES:
    return MEMORY_PROFILE_NAMES[pid]
  if pid.startswith("era_"):
    # era_2024_2025 → Giai đoạn 2024–2025
    rest = pid[4:].replace("_", "–")
    return f"Giai đoạn {rest}"
  return pid


def _short_year_range(date_from: str | None, date_to: str | None) -> str:
  if not date_from or not date_to:
    return "?"
  try:
    y1 = str(date_from)[:4]
    y2 = str(date_to)[:4]
    return y1 if y1 == y2 else f"{y1}–{y2}"
  except Exception:
    return f"{date_from} → {date_to}"


def build_trade_profile_label(tp: dict) -> str:
  """
  Tên cấu hình giao dịch — thống nhất toàn app.
  VD: Học 3 tháng · Giai đoạn 2024 · vòng 3 · Kiểm chứng 2025–2026
  """
  train = tp.get("train_weeks", "?")
  oos = _short_year_range(tp.get("oos_from"), tp.get("oos_to"))
  if not tp.get("use_kb", True):
    return f"Học {train} tuần · Không bộ nhớ · Kiểm chứng {oos}"
  mem = format_memory_profile(tp.get("kb_profile"))
  ep = format_epoch(
    None if tp.get("kb_snapshot") in (None, "", "latest", "Latest") else tp.get("kb_snapshot")
  )
  if ep != "mới nhất":
    return f"Học {train} tuần · {mem} · {ep} · Kiểm chứng {oos}"
  return f"Học {train} tuần · {mem} · Kiểm chứng {oos}"


def format_kb_mode(use_kb: bool) -> str:
  return "Có bộ nhớ" if use_kb else "Không bộ nhớ"


def format_epoch(ep) -> str:
  """ep int → 'vòng 3'; None → 'mới nhất'."""
  if ep is None:
    return "mới nhất"
  try:
    return f"vòng {int(ep)}"
  except (TypeError, ValueError):
    return str(ep)


def format_kb_line(use_kb: bool, kb_profile: str | None, kb_snapshot) -> str:
  if not use_kb:
    return "Không dùng bộ nhớ"
  mem = format_memory_profile(kb_profile)
  ep = format_epoch(
    None if kb_snapshot in (None, "", "latest", "Latest") else kb_snapshot
  )
  if ep != "mới nhất":
    return f"{mem} ({ep})"
  return mem


def format_profile_oneline(tp: dict) -> str:
  """Một dòng cấu hình — tiếng Việt, ít viết tắt."""
  train = tp.get("train_weeks", "?")
  kb = format_kb_line(bool(tp.get("use_kb", True)), tp.get("kb_profile"), tp.get("kb_snapshot"))
  oos_f = tp.get("oos_from", "?")
  oos_t = tp.get("oos_to", "?")
  spread = tp.get("spread_pips", 1)
  slip = tp.get("slippage_pips", 0.3)
  return (
    f"Học **{train} tuần** · {kb} · "
    f"Kiểm chứng {oos_f} → {oos_t} · "
    f"phí {spread}/{slip} pip"
  )


def format_r(value, *, signed: bool = False) -> str:
  if value is None:
    return "—"
  try:
    v = float(value)
    return f"{v:+.2f}R" if signed else f"{v:.2f}R"
  except (TypeError, ValueError):
    return str(value)


def backtest_kpi_items(overall: dict, last_year: dict | None = None) -> list[tuple[str, str, str | None]]:
  """Danh sách KPI cho kpi_row — nhãn tiếng Việt."""
  y = last_year or {}
  return [
    (METRIC_LABELS["win_rate_pct"], f"{overall.get('win_rate_pct', '—')}%",
     f"1 năm: {y.get('win_rate_pct', '—')}%" if y else None),
    (METRIC_LABELS["avg_rr"], str(overall.get("avg_rr", "—")),
     f"1 năm: {y.get('avg_rr', '—')}" if y else None),
    (METRIC_LABELS["total_r"], format_r(overall.get("total_r"), signed=True), None),
    (METRIC_LABELS["max_drawdown_r"], format_r(overall.get("max_drawdown_r")), None),
    (METRIC_LABELS["profit_factor"], str(overall.get("profit_factor", "—")), None),
  ]


def render_glossary_expander(*, location: str = "sidebar"):
  """Deprecated — thuật ngữ đã chuyển vào trang Hướng dẫn."""
  if location == "sidebar":
    return
  render_glossary_guide()


def glossary_sections() -> list[tuple[str, list[tuple[str, str]]]]:
  """Thuật ngữ & viết tắt dùng trong app (M15)."""
  return [
    ("Học & kiểm chứng", [
      ("OOS / Kiểm chứng", "Giai đoạn chỉ test lệnh, không tối ưu lại chiến lược."),
      ("Học N tuần", "Mỗi tuần lấy N tuần data gần nhất để tìm chiến lược (3/6/9)."),
      ("WF / Walk-forward", "Học trên cửa sổ gần → trade tuần sau → trượt cửa sổ (không nhìn trước)."),
      ("KB / Bộ nhớ", "Knowledge Base — kinh nghiệm tích lũy (rules, genomes, ML)."),
      ("KB ON / OFF", "ON = dùng bộ nhớ khi mine; OFF = đánh giá khách quan nhất."),
      ("Epoch / Vòng học", "Một lần chạy cả giai đoạn để cập nhật KB (ep001, ep002, …)."),
      ("Giai đoạn (era)", "Profile KB gắn khoảng thời gian, vd. era_2025_full."),
      ("Hold-out", "Giữ vài tháng cuối chỉ để test — không dùng khi tối ưu WF chính."),
      ("Remine", "Mỗi tuần mine lại strategy trên cửa sổ học gần nhất (không đổi Trade Model)."),
    ]),
    ("Tối ưu & model", [
      ("Grid Search", "Thử nhiều combo tham số, xếp hạng để chọn Trade Model."),
      ("Trade Model", "Snapshot cấu hình đã chọn (cửa sổ học, KB/epoch, OOS, phí) — dùng chung Live/Simulate."),
      ("Active", "Model đang phân tích trong Trade Models — không điều khiển lệnh."),
      ("Archive", "Cất kệ nghiên cứu (giữ report); gỡ khỏi Bridge. Restore không tự add Bridge."),
      ("Health / Health OOS", "Báo cáo backtest OOS của model (chuẩn so sánh Live/Sim)."),
      ("fp / conditions_fp", "Fingerprint điều kiện remine; Live/Sim phải khớp Trade Model đang chọn."),
      ("Edge", "Chênh lệch R (Live/Sim − Backtest, hoặc KB ON − OFF); gần 0 ≈ khớp kỳ vọng."),
    ]),
    ("Vận hành MT5", [
      ("MT5 Bridge", "App quyết định + EA mở/đóng lệnh trên MetaTrader 5."),
      ("Bridge roster", "1–5 model runtime Live/Sim (multiselect). Khác Active."),
      ("Live", "Lệnh thật/demo trên tài khoản MT5 đang gắn EA."),
      ("Simulate", "Replay quá khứ qua App↔EA (History Feed), cùng roster với Live."),
      ("History Feed", "EA phát lại nến lịch sử theo Từ/Đến để Simulate."),
      ("Parity", "Đối chiếu strategy tuần Live với weekly_log Health OOS."),
      ("EA", "Expert Advisor trên MT5 (`ForgeBridgeM15G23` / `ForgeBridgeM15G23Sim`)."),
      ("InpMode", "Input EA: Live / History Feed (Simulate)."),
      ("Magic", "Magic Number — tách lệnh Bridge khỏi EA khác trên cùng tài khoản."),
      ("Sim fills / PaperBook", "Khớp lệnh mô phỏng OHLC trong Compare / HistoryFeed (module `paper_fill`). Không phải desk Paper Monitor."),
      ("Id ma", "Id còn trong Bridge config nhưng model đã Archive/xóa — dùng Dọn roster."),
    ]),
    ("Chỉ số & lệnh", [
      ("R", "Đơn vị lợi nhuận theo rủi ro mỗi lệnh (1R = ±1 lần risk)."),
      ("WR", "Win Rate — tỷ lệ lệnh thắng (%)."),
      ("RR", "Reward/Risk — lãi trung bình ÷ lỗ trung bình mỗi lệnh."),
      ("PF", "Profit Factor — tổng lãi ÷ tổng lỗ (>1 = có lời)."),
      ("Max DD", "Max Drawdown — sụt giảm tối đa từ đỉnh equity (R)."),
      ("RoR", "Risk of Ruin — ước lượng xác suất phá sản (không phải Monte Carlo đầy đủ)."),
      ("PnL", "Profit and Loss — lãi/lỗ (desk thường tính lệnh Auto theo Trade Model)."),
      ("Spread / Slippage", "Chênh mua-bán / trượt giá (pip) trừ vào mô phỏng."),
      ("SL / TP", "Stop Loss / Take Profit."),
      ("SIGNAL", "Có tín hiệu chưa khớp; Bridge phải gửi BUY/SELL lúc bar đóng."),
      ("OPEN / CLOSED / FILLED", "Trạng thái lệnh: đang mở / đã đóng / đã khớp (sim FILLED ≠ lệnh MT5 Live)."),
      ("Auto / Lệnh sửa", "Auto = chiến lược Trade Model; Lệnh sửa = test market / sửa tay SL·TP."),
    ]),
  ]


def render_glossary_guide() -> None:
  """Thuật ngữ đầy đủ — trang Hướng dẫn."""
  st.subheader("Thuật ngữ & viết tắt")
  st.caption("Các từ / viết tắt xuất hiện trong app. Hover help trên từng ô nhập cũng dùng cùng định nghĩa.")
  for section, items in glossary_sections():
    with st.expander(section, expanded=(section == "Học & kiểm chứng")):
      for term, desc in items:
        st.markdown(f"**{term}** — {desc}")
