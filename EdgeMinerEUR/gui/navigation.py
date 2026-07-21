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
    NavItem("home", "Tổng quan", "command_center", "Data · KB → Grid → Model → Paper"),
    NavItem("paper", "Giám sát paper", "paper_monitor", "Tín hiệu tuần · sau khi có Trade Model"),
  )),
  NavGroup("Thiết lập & học", (
    NavItem("settings", "① Cài đặt", "settings_page", "Train · giai đoạn học · kiểm chứng OOS"),
    NavItem("learning", "② Học & tối ưu", "learning_hub", "Huấn luyện KB → Grid Search → Trade Model"),
  )),
  NavGroup("Phân tích", (
    NavItem("analysis", "Phân tích", "analysis_hub", "Dashboard báo cáo · rủi ro · nhật ký · chiến lược"),
  )),
  NavGroup("Khác", (
    NavItem("guide", "Hướng dẫn", "usage_guide", "Quy trình · khái niệm · FAQ"),
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
