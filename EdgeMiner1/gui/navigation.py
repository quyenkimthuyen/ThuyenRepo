"""Trader-centric navigation — nhóm trang theo quy trình làm việc."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
  key: str
  label: str
  module: str
  hint: str = ""


@dataclass(frozen=True)
class NavGroup:
  title: str
  items: tuple[NavItem, ...]


# module = attribute name trong gui.views
NAV_GROUPS: tuple[NavGroup, ...] = (
  NavGroup("Hàng ngày", (
  NavItem("home", "Tổng quan", "command_center", "Quy trình live · trạng thái · bước tiếp"),
    NavItem("paper", "Giám sát paper", "paper_monitor", "Tín hiệu tuần · biểu đồ · lệnh giả lập"),
  )),
  NavGroup("Kiểm chứng", (
    NavItem("research", "Nghiên cứu", "research_lab", "Chạy backtest · tìm tham số · so sánh"),
  )),
  NavGroup("Bộ nhớ & học", (
    NavItem("kb", "Bộ nhớ & học", "kb_era_hub", "Tạo profile · huấn luyện vòng học"),
  )),
  NavGroup("Phân tích", (
    NavItem("risk", "Quản trị rủi ro", "risk_dashboard", "Sụt giảm · chuỗi thắng/thua · phá sản"),
    NavItem("journal", "Nhật ký lệnh", "trade_journal", "Xem từng lệnh trong giai đoạn kiểm chứng"),
    NavItem("strategy", "Chiến lược", "strategy_inspector", "Quy tắc · DNA · mô hình ML"),
  )),
  NavGroup("Khác", (
    NavItem("guide", "Hướng dẫn", "usage_guide", "Quy trình · khái niệm · câu hỏi thường gặp"),
  )),
)

# Alias cũ — giữ deep-link / bookmark
LEGACY_ALIASES: dict[str, str] = {
  "Command Center": "home",
  "Paper Monitor": "paper",
  "Giám sát paper": "paper",
  "Backtest Lab": "research",
  "Grid Search": "research",
  "Report Compare": "research",
  "KB & Giai đoạn": "kb",
  "KB & Học": "kb",
  "Bộ nhớ & học": "kb",
  "Learning Center": "kb",
  "Risk Dashboard": "risk",
  "Quản trị rủi ro": "risk",
  "Trade Journal": "journal",
  "Nhật ký lệnh": "journal",
  "Strategy Inspector": "strategy",
  "Chiến lược": "strategy",
  "Usage Guide": "guide",
}

# Tab mặc định khi mở Nghiên cứu từ alias
RESEARCH_TAB_BY_ALIAS: dict[str, str] = {
  "Backtest Lab": "backtest",
  "Grid Search": "grid",
  "Report Compare": "reports",
}

ALL_ITEMS: dict[str, NavItem] = {
  item.key: item for group in NAV_GROUPS for item in group.items
}


def default_page_key() -> str:
  return "home"
