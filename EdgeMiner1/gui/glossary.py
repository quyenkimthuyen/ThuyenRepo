"""Thuật ngữ & nhãn UI — giúp app dễ hiểu hơn cho người dùng."""
from __future__ import annotations

import streamlit as st

# --- Giải thích ngắn (dùng trong help= / caption) ---

HELP = {
  "oos": "Giai đoạn **kiểm chứng** — chỉ mô phỏng lệnh, không dùng để tối ưu chiến lược.",
  "train_months": "Số tháng dữ liệu gần nhất để **tìm chiến lược mới mỗi tuần** (walk-forward).",
  "kb": "**Bộ nhớ kinh nghiệm** — lưu rule/chiến lược đã học từ các tuần trước.",
  "kb_on": "Dùng bộ nhớ kinh nghiệm khi tìm chiến lược (thường cho kết quả tốt hơn, cần kiểm chứng thêm).",
  "kb_off": "Không dùng bộ nhớ — đánh giá **khách quan nhất**, nên chạy trước khi tin vào kết quả.",
  "epoch": "**Vòng học** — chạy cả giai đoạn một lần để cập nhật bộ nhớ (ep001, ep002, …).",
  "spread": "Chênh lệch mua/bán (pip) — trừ vào mỗi lệnh khi mô phỏng.",
  "slippage": "Trượt giá (pip) — mô phỏng khớp lệnh kém hơn giá lý tưởng.",
  "r_unit": "**Đơn vị R** — lợi nhuận tính theo rủi ro mỗi lệnh (1R = thắng/thua bằng 1 lần risk).",
  "drawdown": "Mức **sụt giảm** lớn nhất từ đỉnh equity (đơn vị R).",
  "win_rate": "Tỷ lệ lệnh **thắng** trong giai đoạn kiểm chứng.",
  "rr": "Tỷ lệ **lãi trung bình / lỗ trung bình** mỗi lệnh.",
  "profit_factor": "Tổng lãi ÷ tổng lỗ — >1 nghĩa là có lời.",
  "risk_of_ruin": "Ước lượng **xác suất phá sản** theo expectancy & % rủi ro/lệnh — không phải xác suất thực tế 100%.",
  "holdout": "Giữ **vài tháng cuối** chỉ để test — không dùng khi tối ưu walk-forward chính.",
  "trade_profile": "Một **cấu hình giao dịch** gồm: cửa sổ học, bộ nhớ, giai đoạn test, phí.",
  "walk_forward": "Mỗi tuần: học trên data gần → trade tuần tiếp theo → lặp lại (tránh nhìn trước tương lai).",
  "paper": "Theo dõi tín hiệu **không dùng tiền thật** — so với backtest trước khi live.",
  "grid_search": "Thử nhiều combo tham số tự động để tìm setting tốt hơn.",
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
  "trades_per_week_near_2": "~2 lệnh/tuần",
}

# --- Tên hiển thị profile bộ nhớ (ID kỹ thuật → tên dễ hiểu) ---

MEMORY_PROFILE_NAMES: dict[str, str] = {
  "default": "Bộ nhớ chung",
  "era_2024": "Giai đoạn 2024",
  "era_2023_2024": "Giai đoạn 2023–2024",
  "era_2022_2024": "Giai đoạn 2022–2024",
  "era_2022_2023": "Giai đoạn 2022–2023",
}


def format_memory_profile(profile_id: str | None) -> str:
  """ID profile bộ nhớ → tên hiển thị."""
  if not profile_id:
    return "—"
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
  train = tp.get("train_months", "?")
  oos = _short_year_range(tp.get("oos_from"), tp.get("oos_to"))
  if not tp.get("use_kb", True):
    return f"Học {train} tháng · Không bộ nhớ · Kiểm chứng {oos}"
  mem = format_memory_profile(tp.get("kb_profile"))
  ep = format_epoch(
    None if tp.get("kb_snapshot") in (None, "", "latest", "Latest") else tp.get("kb_snapshot")
  )
  if ep != "mới nhất":
    return f"Học {train} tháng · {mem} · {ep} · Kiểm chứng {oos}"
  return f"Học {train} tháng · {mem} · Kiểm chứng {oos}"


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
  train = tp.get("train_months", "?")
  kb = format_kb_line(bool(tp.get("use_kb", True)), tp.get("kb_profile"), tp.get("kb_snapshot"))
  oos_f = tp.get("oos_from", "?")
  oos_t = tp.get("oos_to", "?")
  spread = tp.get("spread_pips", 1)
  slip = tp.get("slippage_pips", 0.3)
  return (
    f"Học **{train} tháng** · {kb} · "
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
  """Bảng thuật ngữ nhanh — sidebar hoặc main."""
  items = [
    ("Kiểm chứng", "Giai đoạn chỉ test lệnh, không tối ưu lại chiến lược (trước: OOS)."),
    ("Học N tháng", "Mỗi tuần lấy N tháng data gần nhất để tìm chiến lược."),
    ("Bộ nhớ", "Kinh nghiệm tích lũy từ các tuần/tháng trước (trước: KB)."),
    ("Giai đoạn", "Profile bộ nhớ gắn một khoảng thời gian, vd. Giai đoạn 2024 (trước: era_2024)."),
    ("Vòng học", "Một lần chạy cả giai đoạn để cập nhật bộ nhớ (trước: epoch)."),
    ("Bộ nhớ chung", "Profile mặc định, không gắn giai đoạn cụ thể (trước: default)."),
    ("Đơn vị R", "Lợi nhuận theo rủi ro mỗi lệnh (1R = ±1 lần risk)."),
    ("Walk-forward", "Học từng tuần → trade tuần sau → lặp (tránh nhìn trước)."),
  ]
  container = st.sidebar if location == "sidebar" else st
  with container.expander("📖 Thuật ngữ nhanh", expanded=False):
    for term, desc in items:
      st.markdown(f"**{term}** — {desc}")
    st.caption("Chi tiết: trang **Hướng dẫn**.")
