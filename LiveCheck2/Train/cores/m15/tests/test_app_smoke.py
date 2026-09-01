from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

# gui/ moved out of cores/m15 to the TrainApp root in the shared-GUI refactor;
# parents[1] kept pointing at the old location, so every case here failed with
# FileNotFoundError instead of rendering anything.
#
# Note on reach: these cases run with no TRAINAPP_DESK, so desk-scoped state
# (runtime/<desk>/…) is absent and every config read falls back to defaults. That is
# why they cannot catch bugs which only fire on a real desk's stored values — the
# DATA_START picker crash is covered by test_mt5_history_sync instead.
APP = Path(__file__).resolve().parents[3] / "gui" / "app.py"


@pytest.mark.parametrize(
  ("page", "learning_tab", "models_subtab"),
  [
    ("home", None, None),
    ("learning", "settings", None),
    ("learning", "train_kb", None),
    ("learning", "grid", None),
    ("models", None, "info"),
    ("models", None, "health"),
    ("models", None, "risk"),
    ("models", None, "journal"),
    ("models", None, "strategy"),
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
