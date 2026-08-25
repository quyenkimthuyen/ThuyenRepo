import json
from pathlib import Path
for desk in ("e21", "g23"):
  p = Path(rf"C:\Work\ThuyenRepo\LiveCheck\TrainApp\runtime\{desk}\results\trade_models.json")
  print("====", desk, "====")
  if not p.exists():
    print("no file"); continue
  models = json.loads(p.read_text(encoding="utf-8")).get("models") or []
  print("n=", len(models))
  for m in models:
    lab = str(m.get("label") or "")
    if "Filt" not in lab:
      continue
    print(m.get("id"), "WR", m.get("win_rate_pct"), "R", m.get("total_r"), "DD", m.get("max_drawdown_r"))
