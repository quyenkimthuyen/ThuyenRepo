"""Metadata chiến lược — mô tả, tham số rolling, giải thích."""

from __future__ import annotations

from typing import Any

STRATEGIES: dict[str, dict[str, Any]] = {
    "Wyckoff": {
        "id": "wyckoff",
        "icon": "📊",
        "chart_color": "#2962FF",
        "title": "Wyckoff Failed Break",
        "summary": "Spring / Upthrust — giá phá vỡ range rồi quay lại (failed break).",
        "description": """
**Logic:** Tìm vùng tích lũy (consolidation), sweep liquidity qua high/low của range,
nến đóng lại trong range → tín hiệu đảo chiều.

**Entry:** 1H | **Filter:** 4H stack (chỉ long khi 4H bullish, short khi bearish).

**SL:** Dưới/trên sweep wick + buffer | **TP:** RR 2.0 mặc định.
        """,
        "base_config": "config/wyckoff.yaml",
        "rolling_params": {
            "min_htf_adx": {"label": "4H ADX tối thiểu", "type": "float", "min": 20, "max": 32, "step": 1},
            "max_adx": {"label": "1H ADX tối đa", "type": "float", "min": 30, "max": 50, "step": 1},
            "consolidation_days": {"label": "Ngày tích lũy", "type": "int", "min": 1, "max": 5, "step": 1},
            "htf_mode": {"label": "Chế độ filter 4H", "type": "select", "options": ["strict", "stack", "trend_adx"]},
        },
    },
    "RSI Divergence": {
        "id": "rsi_divergence",
        "icon": "📉",
        "chart_color": "#FF9800",
        "title": "RSI Divergence",
        "summary": "Phân kỳ RSI + phá neckline — mean reversion.",
        "description": """
**Logic:** Bullish div — giá lower low, RSI higher low. Bearish div — ngược lại.
Vào lệnh khi phá neckline của cấu trúc phân kỳ.

**Entry:** 1H | Không bắt buộc filter 4H (có thể bật).

**Lọc:** ADX 1H thấp (sideway) thường hiệu quả hơn trend mạnh.
        """,
        "base_config": "config/rsi_divergence.yaml",
        "rolling_params": {
            "max_adx_1h": {"label": "1H ADX tối đa", "type": "float", "min": 25, "max": 40, "step": 1},
            "min_rsi_diff": {"label": "Δ RSI tối thiểu", "type": "float", "min": 2.0, "max": 6.0, "step": 0.5},
            "rsi_oversold": {"label": "RSI oversold (long)", "type": "float", "min": 35, "max": 50, "step": 1},
            "rsi_overbought": {"label": "RSI overbought (short)", "type": "float", "min": 50, "max": 65, "step": 1},
            "min_swing_gap": {"label": "Khoảng cách swing (bar)", "type": "int", "min": 8, "max": 20, "step": 1},
        },
    },
    "EMA 50/200": {
        "id": "ema_trend",
        "icon": "〰️",
        "chart_color": "#AB47BC",
        "title": "EMA 50/200 Pullback",
        "summary": "Trend follow — pullback về EMA50 trong trend EMA50/200.",
        "description": """
**Logic:** EMA50 > EMA200 (bull) hoặc ngược (bear). Giá pullback chạm EMA50,
nến bounce → vào theo trend.

**Filter:** 4H strict + spread EMA không quá rộng (tránh vào muộn).

**SL:** Dưới EMA200 / swing low | **TP:** RR 2.0.
        """,
        "base_config": "config/ema_trend.yaml",
        "rolling_params": {
            "min_htf_adx": {"label": "4H ADX tối thiểu", "type": "float", "min": 24, "max": 36, "step": 1},
            "max_adx_1h": {"label": "1H ADX tối đa", "type": "float", "min": 22, "max": 32, "step": 1},
            "pullback_atr": {"label": "Pullback (× ATR)", "type": "float", "min": 0.30, "max": 0.50, "step": 0.02},
            "max_ema_spread_atr": {"label": "Spread EMA max (× ATR)", "type": "float", "min": 1.0, "max": 3.0, "step": 0.1},
        },
    },
    "Pin Bar Elite": {
        "id": "pin_bar",
        "icon": "📌",
        "chart_color": "#FFD54F",
        "title": "Pin Bar Elite",
        "summary": "Pin bar tại swing — wick dài, thân nhỏ, filter 4H + session London.",
        "description": """
**Logic:** Nến pin (wick ≥ 4× body, wick chiếm ≥58% range) tại swing high/low.
Long: pin bull ở đáy swing | Short: pin bear ở đỉnh swing.

**Entry:** 1H | **Filter:** 4H strict, ADX 1H thấp (sideway), session 9–16h UTC.

**SL:** Dưới/trên đuôi pin + buffer ATR | **TP:** RR 2.0.

**Lưu ý:** Ít lệnh hơn Wyckoff/EMA — ưu tiên chất lượng setup.
        """,
        "base_config": "config/pin_bar.yaml",
        "rolling_params": {
            "min_htf_adx": {"label": "4H ADX tối thiểu", "type": "float", "min": 20, "max": 28, "step": 1},
            "max_adx_1h": {"label": "1H ADX tối đa", "type": "float", "min": 22, "max": 35, "step": 1},
            "min_wick_body_ratio": {"label": "Wick / body tối thiểu", "type": "float", "min": 3.0, "max": 5.0, "step": 0.5},
            "min_wick_range_ratio": {"label": "Wick / range tối thiểu", "type": "float", "min": 0.50, "max": 0.65, "step": 0.02},
            "swing_lookback": {"label": "Swing lookback (bar)", "type": "int", "min": 8, "max": 20, "step": 1},
            "htf_mode": {"label": "Chế độ filter 4H", "type": "select", "options": ["strict", "stack", "soft"]},
        },
    },
}

STRATEGY_ORDER = ["Wyckoff", "RSI Divergence", "EMA 50/200", "Pin Bar Elite"]
