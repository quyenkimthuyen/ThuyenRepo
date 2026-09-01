#!/usr/bin/env python
"""Đo phương sai của quá trình học KB bằng nhiều bản rút độc lập mỗi era.

Một KB học xong là một lần rút thăm từ một quá trình tiến hoá ngẫu nhiên, không
phải "kết quả" của era đó: gs_20260831 đo được biên độ 27,61 R giữa ba bản rút
cùng dữ liệu, cùng cửa sổ, cùng code. So sánh hai era mà mỗi era chỉ học một lần
thì không tách được hiệu ứng era khỏi hiệu ứng rút thăm.

Salt (M15_LEARNING_SEED_SALT) là thứ duy nhất thay đổi giữa các bản rút, nên mỗi
bản rút vừa độc lập vừa tái lập được: ghi lại salt là đủ để dựng lại đúng KB đó.
Học vào đúng profile production thay vì profile tạm, vì tên profile nằm trong
seed — profile tạm sẽ cho một KB khác với cái grid thực sự chạy.

  # Đo 3 bản rút cho mỗi era đang hoạt động
  python scripts/measure_kb_draws.py --draws 3

  # Chốt bản rút đã chọn (học lại đúng salt đó, để nguyên trong profile)
  python scripts/measure_kb_draws.py --apply 2025-h2=2,2025-q4=1
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports" / "kb_draws.json"


def _bind_desk(desk: str) -> None:
  from desk_context import apply_desk_env

  cfg = apply_desk_env(desk)
  core_root = str(cfg["core_root"])
  if core_root not in sys.path:
    sys.path.insert(0, core_root)


def _set_salt(salt: int) -> None:
  """Đặt salt cho cả process hiện tại và mọi process con."""
  os.environ["M15_LEARNING_SEED_SALT"] = str(salt)
  import meta_learner

  meta_learner.LEARNING_SEED_SALT = int(salt)


def _era_specs(keys: list[str] | None) -> list[dict]:
  from gui.app_settings import load_settings, resolve_learning_eras

  eras = resolve_learning_eras(load_settings())
  if keys:
    by_key = {e["key"]: e for e in eras}
    missing = [k for k in keys if k not in by_key]
    if missing:
      have = ", ".join(sorted(by_key)) or "(rỗng)"
      raise SystemExit(f"Không có era {missing} trong catalog. Đang có: {have}")
    return [by_key[k] for k in keys]
  return eras


def _learn_one(era: dict, salt: int, epochs: int) -> dict:
  """Một bản rút: reset profile rồi học lại từ đầu dưới salt đã cho."""
  from gui.services import execute_learning

  _set_salt(salt)
  t0 = time.time()
  report = execute_learning(
    epochs=epochs,
    reset_kb=True,
    kb_profile=era["kb_profile"],
    kb_name=era.get("label") or era["kb_profile"],
    from_date=era["learn_from"],
    until_date=era["learn_until"],
  )
  return {
    "era": era["key"],
    "kb_profile": era["kb_profile"],
    "salt": salt,
    "secs": round(time.time() - t0, 1),
    "epochs": [
      {
        "epoch": int(m.get("epoch") or i + 1),
        "n_trades": int(m.get("n_trades") or 0),
        "win_rate_pct": float(m.get("win_rate_pct") or 0.0),
        "avg_rr": float(m.get("avg_rr") or 0.0),
        "total_r": float(m.get("total_r") or 0.0),
      }
      for i, m in enumerate(report.get("epoch_history") or [])
    ],
  }


def _last_epoch(draw: dict) -> dict:
  eps = draw.get("epochs") or []
  return eps[-1] if eps else {}


def _spread(values: list[float]) -> dict:
  if not values:
    return {}
  return {
    "mean": round(statistics.fmean(values), 2),
    "sd": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
    "min": round(min(values), 2),
    "max": round(max(values), 2),
    "range": round(max(values) - min(values), 2),
  }


def _median_salt(draws: list[dict]) -> int | None:
  """Salt của bản rút giữa theo total_r epoch cuối.

  Chọn bản giữa chứ không chọn bản tốt nhất: R trong mẫu dự báo *ngược* R ngoài
  mẫu (era 12 tháng +84,35 trong mẫu nhưng tệ hơn 30,5 R ngoài mẫu so với era 6
  tháng +32,59), nên chọn theo đuôi thuận là chọn ngược. Bản giữa là lựa chọn
  trung tính duy nhất không bốc thăm may.
  """
  scored = [(float(_last_epoch(d).get("total_r") or 0.0), int(d["salt"])) for d in draws]
  if not scored:
    return None
  scored.sort()
  return scored[len(scored) // 2][1]


def _print_table(by_era: dict[str, list[dict]]) -> dict:
  picks: dict[str, int] = {}
  for era, draws in by_era.items():
    print(f"\n=== {era} · {draws[0]['kb_profile']} ===")
    n_ep = max((len(d["epochs"]) for d in draws), default=0)
    for d in draws:
      cells = " | ".join(
        f"ep{e['epoch']} R={e['total_r']:+7.2f} WR={e['win_rate_pct']:5.2f}% n={e['n_trades']:>3}"
        for e in d["epochs"]
      )
      print(f"  salt={d['salt']}  {cells}   ({d['secs']}s)")
    for ep in range(1, n_ep + 1):
      rs = [e["total_r"] for d in draws for e in d["epochs"] if e["epoch"] == ep]
      wrs = [e["win_rate_pct"] for d in draws for e in d["epochs"] if e["epoch"] == ep]
      sr, sw = _spread(rs), _spread(wrs)
      if sr:
        print(
          f"  ep{ep} phân tán: R mean={sr['mean']:+.2f} sd={sr['sd']:.2f} "
          f"range={sr['range']:.2f} | WR sd={sw['sd']:.2f} điểm"
        )
    pick = _median_salt(draws)
    if pick is not None:
      picks[era] = pick
      print(f"  → bản giữa: salt={pick}")
  return picks


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", default="e21")
  ap.add_argument("--eras", default="", help="Mặc định: mọi era đang hoạt động")
  ap.add_argument("--draws", type=int, default=3)
  ap.add_argument("--epochs", type=int, default=0, help="Mặc định: learning_loops")
  ap.add_argument("--apply", default="", help="Chốt salt: 2025-h2=2,2025-q4=1")
  ap.add_argument("--out", default=str(DEFAULT_OUT))
  args = ap.parse_args()

  _bind_desk(args.desk)
  from gui.app_settings import load_settings

  epochs = int(args.epochs or load_settings().get("learning_loops") or 2)
  keys = [k.strip() for k in args.eras.split(",") if k.strip()]

  if args.apply:
    chosen = {}
    for part in args.apply.split(","):
      k, _, v = part.partition("=")
      if not _:
        raise SystemExit(f"--apply cần dạng era=salt, nhận {part!r}")
      chosen[k.strip()] = int(v)
    specs = _era_specs(list(chosen))
    for era in specs:
      salt = chosen[era["key"]]
      print(f"Chốt {era['key']} · salt={salt} · {epochs} epoch", flush=True)
      d = _learn_one(era, salt, epochs)
      last = _last_epoch(d)
      print(
        f"  xong: ep{last.get('epoch')} R={last.get('total_r'):+.2f} "
        f"WR={last.get('win_rate_pct'):.2f}% n={last.get('n_trades')}",
        flush=True,
      )
    print("\nSalt đã chốt nằm trong M15_LEARNING_SEED_SALT của lần học cuối; "
          "ghi lại để dựng lại đúng KB này.")
    return 0

  specs = _era_specs(keys)
  print(
    f"Đo {args.draws} bản rút × {len(specs)} era × {epochs} epoch "
    f"= {args.draws * len(specs)} lần học",
    flush=True,
  )
  by_era: dict[str, list[dict]] = {}
  for era in specs:
    for salt in range(1, args.draws + 1):
      print(f"\n[{era['key']}] salt={salt} …", flush=True)
      d = _learn_one(era, salt, epochs)
      by_era.setdefault(era["key"], []).append(d)
      last = _last_epoch(d)
      print(
        f"  R={last.get('total_r'):+.2f} WR={last.get('win_rate_pct'):.2f}% "
        f"n={last.get('n_trades')} ({d['secs']}s)",
        flush=True,
      )

  picks = _print_table(by_era)
  out = Path(args.out)
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(
    json.dumps(
      {"epochs": epochs, "draws": args.draws, "by_era": by_era, "median_salt": picks},
      indent=2,
      ensure_ascii=False,
    ),
    encoding="utf-8",
  )
  print(f"\nĐã ghi {out}")
  if picks:
    arg = ",".join(f"{k}={v}" for k, v in picks.items())
    print(f"Chốt bằng: python scripts/measure_kb_draws.py --apply {arg}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
