from __future__ import annotations

import html
import json
from typing import Any

from backend.reports.equity import drawdown_curve, equity_curve, r_multiples


def render_backtest_html(result: dict[str, Any], *, title: str = "Backtest Report") -> str:
    m = result.get("metrics") or {}
    mc = result.get("monte_carlo") or {}
    trades = result.get("trades") or []
    eq = equity_curve(trades)
    dd = drawdown_curve(trades)
    rs = r_multiples(trades)
    passed = result.get("pass", False)
    banner = (
        '<div class="banner ok">PASS criteria met</div>'
        if passed
        else '<div class="banner warn">Chưa đạt PASS — xem metrics</div>'
    )
    if m.get("trades", 0) < 50:
        banner += '<div class="banner info">Dưới 50 lệnh — ý nghĩa thống kê hạn chế</div>'

    def esc(obj: Any) -> str:
        return html.escape(json.dumps(obj, indent=2, default=str))

    eq_points = " ".join(f"{i},{p['equity_pips']}" for i, p in enumerate(eq))
    dd_points = " ".join(f"{i},{p['drawdown_pips']}" for i, p in enumerate(dd))

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f1419; color: #e7ecf3; }}
    h1 {{ font-size: 1.4rem; }}
    .banner {{ padding: 0.6rem 1rem; border-radius: 6px; margin: 0.5rem 0; }}
    .ok {{ background: #1a3d2e; color: #3ecf8e; }}
    .warn {{ background: #3d2a1a; color: #f0b429; }}
    .info {{ background: #1a2a3d; color: #8b9bb4; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #2a3548; padding: 0.5rem; text-align: left; }}
    th {{ background: #1a2332; }}
    pre {{ background: #1a2332; padding: 1rem; border-radius: 6px; overflow: auto; }}
    svg {{ background: #121a24; border-radius: 6px; margin: 1rem 0; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p>Period: <strong>{html.escape(str(result.get('period', '')))}</strong></p>
  {banner}
  <h2>Metrics</h2>
  <table>
    <tr><th>Trades</th><td>{m.get('trades', 0)}</td></tr>
    <tr><th>Win rate</th><td>{m.get('win_rate', 0):.1%}</td></tr>
    <tr><th>Profit factor</th><td>{m.get('profit_factor', 0)}</td></tr>
    <tr><th>Expectancy</th><td>{m.get('expectancy_pips', 0)} pips</td></tr>
    <tr><th>Max DD</th><td>{m.get('max_drawdown_pips', 0)} pips</td></tr>
    <tr><th>Total</th><td>{m.get('total_pips', 0)} pips</td></tr>
  </table>
  <h2>Monte Carlo</h2>
  <table>
    <tr><th>PF p5</th><td>{mc.get('pf_p5', 0)}</td></tr>
    <tr><th>PF p50</th><td>{mc.get('pf_p50', 0)}</td></tr>
    <tr><th>PF p95</th><td>{mc.get('pf_p95', 0)}</td></tr>
    <tr><th>DD p95</th><td>{mc.get('dd_p95', 0)} pips</td></tr>
  </table>
  <h2>Equity curve (pips)</h2>
  <svg width="800" height="200" viewBox="0 0 800 200">
    <polyline fill="none" stroke="#3d8bfd" stroke-width="2"
      points="{_scale_poly(eq_points, 800, 200)}" />
  </svg>
  <h2>Drawdown (pips)</h2>
  <svg width="800" height="120" viewBox="0 0 800 120">
    <polyline fill="none" stroke="#ff6b6b" stroke-width="2"
      points="{_scale_poly(dd_points, 800, 120, invert_y=False)}" />
  </svg>
  <h2>By setup</h2>
  <pre>{esc(m.get('by_setup', {}))}</pre>
  <h2>By month</h2>
  <pre>{esc(m.get('by_month', {}))}</pre>
  <h2>R-multiples (sample)</h2>
  <pre>{esc(rs[:30])}</pre>
</body>
</html>"""


def _scale_poly(points: str, width: int, height: int, *, invert_y: bool = True) -> str:
    if not points.strip():
        return ""
    pairs = []
    for part in points.split():
        x_s, y_s = part.split(",")
        pairs.append((float(x_s), float(y_s)))
    if len(pairs) < 2:
        return points
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    xmin, xmax = min(xs), max(xs) or 1
    ymin, ymax = min(ys), max(ys)
    if ymax == ymin:
        ymax = ymin + 1
    out = []
    pad = 10
    for x, y in pairs:
        sx = pad + (x - xmin) / (xmax - xmin) * (width - 2 * pad)
        norm = (y - ymin) / (ymax - ymin)
        sy = (height - pad) - norm * (height - 2 * pad) if invert_y else pad + norm * (height - 2 * pad)
        out.append(f"{sx:.1f},{sy:.1f}")
    return " ".join(out)
