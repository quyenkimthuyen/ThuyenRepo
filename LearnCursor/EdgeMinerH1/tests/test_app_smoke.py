from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "gui" / "app.py"


@pytest.mark.parametrize(
  ("page", "learning_tab", "models_subtab"),
  [
    ("home", None, None),
    ("learning", "settings", None),
    ("learning", "train_kb", None),
    ("learning", "grid", None),
    ("learning", "models", "manage"),
    ("learning", "models", "risk"),
    ("learning", "models", "journal"),
    ("learning", "models", "strategy"),
    ("paper", None, None),
    ("mt5_bridge", None, None),
    ("guide", None, None),
  ],
)
def test_main_views_render_without_exception(
  page: str,
  learning_tab: str | None,
  models_subtab: str | None,
):
  app = AppTest.from_file(str(APP))
  app.session_state["nav_page"] = page
  if learning_tab:
    app.session_state["learning_tab"] = learning_tab
  if models_subtab:
    app.session_state["models_subtab"] = models_subtab
  app.run(timeout=180)
  errors = [str(item.value) for item in app.exception]
  assert not errors, "\n".join(errors)
