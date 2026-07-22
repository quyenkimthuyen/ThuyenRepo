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


# Flat list — Cài đặt & Phân tích nằm trong Học & tối ưu (Trade Models).
NAV_ITEMS: tuple[NavItem, ...] = (
  NavItem(
    "home", "Tổng quan", "command_center",
    "Data · KB → Grid → Model → Paper",
    ":material/dashboard:",
  ),
  NavItem(
    "learning", "Học & tối ưu", "learning_hub",
    "Cài đặt → KB → Grid → Trade Model (Quản lý · Rủi ro · Nhật ký · Chiến lược)",
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
    "guide", "Hướng dẫn", "usage_guide",
    "Quy trình · khái niệm · FAQ",
    ":material/menu_book:",
  ),
)

# Kept for headers / legacy redirects (not in sidebar)
ANALYSIS_NAV = NavItem(
  "analysis", "Phân tích", "analysis_hub",
  "Risk · nhật ký · chiến lược (theo Trade Model)",
  ":material/analytics:",
)


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
  "Risk Dashboard": "learning",
  "Quản trị rủi ro": "learning",
  "Trade Journal": "learning",
  "Nhật ký lệnh": "learning",
  "Strategy Inspector": "learning",
  "Chiến lược": "learning",
  "Phân tích": "learning",
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
  "Risk Dashboard": "models",
  "Quản trị rủi ro": "models",
  "Trade Journal": "models",
  "Nhật ký lệnh": "models",
  "Strategy Inspector": "models",
  "Chiến lược": "models",
  "Phân tích": "models",
}

# Sets models_subtab (and analysis_tab) when opening from legacy names
ANALYSIS_TAB_BY_ALIAS: dict[str, str] = {
  "Risk Dashboard": "risk",
  "Quản trị rủi ro": "risk",
  "Trade Journal": "journal",
  "Nhật ký lệnh": "journal",
  "Strategy Inspector": "strategy",
  "Chiến lược": "strategy",
  "Phân tích": "risk",
}

ALL_ITEMS: dict[str, NavItem] = {item.key: item for item in NAV_ITEMS}
ALL_ITEMS["analysis"] = ANALYSIS_NAV  # for page chrome of analysis subviews


def default_page_key() -> str:
  return "home"
