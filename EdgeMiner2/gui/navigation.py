"""Trader-centric navigation — flat sidebar (no section groups)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
  key: str
  label: str
  module: str
  hint: str = ""
  icon: str = ""  # Streamlit Material icon, e.g. ":material/home:"


# Flat list — Cài đặt is a tab inside Học & tối ưu (not a sidebar page).
NAV_ITEMS: tuple[NavItem, ...] = (
  NavItem(
    "home", "Tổng quan", "command_center",
    "Data · KB → Grid → Model → Paper",
    ":material/dashboard:",
  ),
  NavItem(
    "learning", "Học & tối ưu", "learning_hub",
    "Cài đặt → KB → Grid → Trade Model",
    ":material/school:",
  ),
  NavItem(
    "paper", "Giám sát paper", "paper_monitor",
    "Tín hiệu tuần · sau khi có Trade Model",
    ":material/monitoring:",
  ),
  NavItem(
    "mt5_bridge", "MT5 Bridge", "mt5_bridge",
    "App quyết định · EA execute · log giao tiếp",
    ":material/hub:",
  ),
  NavItem(
    "analysis", "Phân tích", "analysis_hub",
    "Risk · nhật ký · chiến lược (theo Trade Model)",
    ":material/analytics:",
  ),
  NavItem(
    "guide", "Hướng dẫn", "usage_guide",
    "Quy trình · khái niệm · FAQ",
    ":material/menu_book:",
  ),
)

# Backward compat for code that still imports NAV_GROUPS
@dataclass(frozen=True)
class NavGroup:
  title: str
  items: tuple[NavItem, ...]


NAV_GROUPS: tuple[NavGroup, ...] = (
  NavGroup("", NAV_ITEMS),
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
  "Cài đặt": "learning",
  "Settings": "learning",
  "settings": "learning",
  "MT5 Bridge": "mt5_bridge",
  "Bridge": "mt5_bridge",
}

LEARNING_TAB_BY_ALIAS: dict[str, str] = {
  "Cài đặt": "settings",
  "Settings": "settings",
  "settings": "settings",
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

ALL_ITEMS: dict[str, NavItem] = {item.key: item for item in NAV_ITEMS}


def default_page_key() -> str:
  return "home"
