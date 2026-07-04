#!/usr/bin/env python3
"""Print expert diagnosis of latest run."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    run_path = Path("output/run_report.json")
    test_path = Path("output/test_report.json")
    data = json.loads(run_path.read_text()) if run_path.exists() else {}
    if test_path.exists():
        test_data = json.loads(test_path.read_text())
        data.setdefault("validated_strategies", test_data.get("strategies", []))
        data.setdefault("summary", test_data.get("summary", {}))

    strategies = data.get("validated_strategies", data.get("strategies", []))
    summary = data.get("summary", {})
    portfolio = data.get("portfolio", {})
    tf = data.get("timeframe", "1h")
    htf = data.get("htf_filter", "4h")
    spread = data.get("spread_pips", 0.5)

    print("\n" + "=" * 70)
    print("  PHÂN TÍCH CHUYÊN GIA")
    print("=" * 70)

    print("\n[1] BỐI CẢNH THỊ TRƯỜNG")
    print(f"  - EURUSD entry {tf} + filter {htf}, spread ECN {spread} pip")
    print("  - SL 2% equity, RR≥2 — risk cố định, strategy chỉ quyết entry/exit")
    print("  - Train 1 năm / OOS 2 năm blind — regime shift là bình thường")

    print("\n[2] KẾT QUẢ HIỆN TẠI")
    passed = summary.get("passed", sum(1 for s in strategies if s.get("passed")))
    print(f"  - Strategies giữ lại : {len(strategies)}")
    print(f"  - Pass (gate tắt)    : {passed}")
    if strategies:
        best = max(strategies, key=lambda s: s.get("oos_metrics", {}).get("win_rate", 0))
        t, o = best.get("train_metrics", {}), best.get("oos_metrics", {})
        print(f"  - Best OOS WR        : {o.get('win_rate', 0):.1%} ({o.get('trade_count', 0)} lệnh)")
        print(f"  - Best train WR      : {t.get('win_rate', 0):.1%} ({t.get('trade_count', 0)} lệnh)")
    if portfolio:
        po = portfolio.get("oos_metrics", {})
        print(f"  - Portfolio OOS      : WR={po.get('win_rate', 0):.1%} PF={po.get('profit_factor', 0):.2f} "
              f"trades={po.get('trade_count', 0)} return={po.get('total_return', 0):.1%}")

    print("\n[3] NGUYÊN NHÂN GỐC (ROOT CAUSE)")
    causes = []
    for s in strategies[:3]:
        t, o = s.get("train_metrics", {}), s.get("oos_metrics", {})
        if t.get("trade_count", 0) < 50:
            causes.append("Mẫu train nhỏ (<50 lệnh) → dễ overfit")
        if t.get("win_rate", 0) - o.get("win_rate", 0) > 0.15:
            causes.append("Curve-fit: WR train >> OOS → điều kiện quá khớp năm train")
        if o.get("profit_factor", 0) < 1.0:
            causes.append(f"PF OOS < 1: edge chưa đủ sau spread/slippage")
    for i, c in enumerate(dict.fromkeys(causes), 1):
        print(f"  {i}. {c}")
    if not causes:
        print("  - Edge OOS chưa đủ mạnh so với spread + RR cố định")

    print("\n[4] HỆ THỐNG ĐÃ ÁP DỤNG (sau benchmark 66 configs)")
    print(f"  ✓ Entry {tf} + filter {htf} | spread ECN {spread} pip")
    print("  ✓ WINNER: single mine, 1 strategy, fitness select (không portfolio)")
    print("  ✓ Quarterly re-mine & portfolio 2-3: loại (OOS âm trong benchmark)")
    print("  ✓ Holdout filter: loại (chọn sai setup)")
    exp_path = Path("output/experiment_report.json")
    if exp_path.exists():
        exp = json.loads(exp_path.read_text())
        w = exp.get("winner", {})
        if w:
            print(f"  ✓ Benchmark OOS: ret={w.get('oos_return', 0):+.1%} PF={w.get('oos_pf', 0):.2f}")

    print("\n[5] ĐỀ XUẤT TIẾP")
    print("  - Tách regime trend/range (ADX) trước khi mine")
    print("  - Walk-forward nhiều fold hơn khi có đủ data 1H")
    print("  - Re-mine theo quarter trên OOS rolling (paper trade)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
