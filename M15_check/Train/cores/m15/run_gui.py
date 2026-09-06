#!/usr/bin/env python3
"""Launch ForexForge GUI (Streamlit)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
app = ROOT / "gui" / "app.py"

if __name__ == "__main__":
  subprocess.run([
    sys.executable, "-m", "streamlit", "run",
    str(app),
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false",
  ], cwd=str(ROOT))
