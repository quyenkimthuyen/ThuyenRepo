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


# Flat list — Trade Models is a top-level sidebar page.
NAV_ITEMS: tuple[NavItem, ...] = (
  NavItem(
    "home", "Tổng quan", "command_center",
    "Data · KB → Grid → Model → Live/Simulate",
    ":material/dashboard:",
  ),
  NavItem(
    "learning", "Học & tối ưu", "learning_hub",
    "Cài đặt → KB → Grid Search",
    ":material/school:",
  ),
  NavItem(
    "models", "Trade Models", "trade_models_view",
    "Chọn model · Sức khỏe · Rủi ro · Nhật ký · Chiến lược",
    ":material/inventory_2:",
  ),
  NavItem(
    "mt5_bridge", "MT5 Bridge", "mt5_bridge",
    "",
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
  "Paper Monitor": "models",
  "Giám sát paper": "models",
  "paper": "models",
  "Backtest Lab": "learning",
  "Grid Search": "learning",
  "Report Compare": "learning",
  "KB & Giai đoạn": "learning",
  "KB & Học": "learning",
  "Bộ nhớ & học": "learning",
  "Learning Center": "learning",
  "Nghiên cứu": "learning",
  "Risk Dashboard": "models",
  "Quản trị rủi ro": "models",
  "Trade Journal": "models",
  "Nhật ký lệnh": "models",
  "Strategy Inspector": "models",
  "Chiến lược": "models",
  "Phân tích": "models",
  "Trade Models": "models",
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
  "Report Compare": "grid",
  "KB & Học": "train_kb",
  "Learning Center": "train_kb",
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
  "Paper Monitor": "health",
  "Giám sát paper": "health",
  "paper": "health",
}

ALL_ITEMS: dict[str, NavItem] = {item.key: item for item in NAV_ITEMS}
ALL_ITEMS["analysis"] = ANALYSIS_NAV  # for page chrome of analysis subviews


def default_page_key() -> str:
  return "home"
