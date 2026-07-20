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


NAV_GROUPS: tuple[NavGroup, ...] = (
  NavGroup("Hàng ngày", (
    NavItem("home", "Tổng quan", "command_center", "Quy trình live · trạng thái · bước tiếp"),
    NavItem("paper", "Giám sát paper", "paper_monitor", "Tín hiệu tuần · biểu đồ · lệnh giả lập"),
  )),
  NavGroup("Học & tối ưu", (
    NavItem("learning", "Học & tối ưu", "learning_hub", "Grid Search · Trade Models · so sánh"),
    NavItem("settings", "Cài đặt", "settings_page", "Train window · giai đoạn học · kiểm chứng"),
  )),
  NavGroup("Phân tích", (
    NavItem("analysis", "Phân tích", "analysis_hub", "Risk · nhật ký lệnh · chiến lược"),
  )),
  NavGroup("Khác", (
    NavItem("guide", "Hướng dẫn", "usage_guide", "Quy trình · khái niệm · câu hỏi thường gặp"),
  )),
)

LEGACY_ALIASES: dict[str, str] = {
  "Command Center": "home",
  "Paper Monitor": "paper",
  "Giám sát paper": "paper",
  "Backtest Lab": "learning",
  "Grid Search": "learning",
  "Report Compare": "learning",
  "KB & Giai đoạn": "learning",
  "KB & Học": "learning",
  "Bộ nhớ & học": "learning",
  "Learning Center": "learning",
  "Nghiên cứu": "learning",
  "Risk Dashboard": "analysis",
  "Quản trị rủi ro": "analysis",
  "Trade Journal": "analysis",
  "Nhật ký lệnh": "analysis",
  "Strategy Inspector": "analysis",
  "Chiến lược": "analysis",
  "Usage Guide": "guide",
  "Cài đặt": "settings",
  "Settings": "settings",
}

LEARNING_TAB_BY_ALIAS: dict[str, str] = {
  "Backtest Lab": "grid",
  "Grid Search": "grid",
  "Report Compare": "era",
  "KB & Học": "train_kb",
  "Learning Center": "train_kb",
}

ANALYSIS_TAB_BY_ALIAS: dict[str, str] = {
  "Risk Dashboard": "risk",
  "Trade Journal": "journal",
  "Strategy Inspector": "strategy",
}

ALL_ITEMS: dict[str, NavItem] = {
  item.key: item for group in NAV_GROUPS for item in group.items
}


def default_page_key() -> str:
  return "home"
