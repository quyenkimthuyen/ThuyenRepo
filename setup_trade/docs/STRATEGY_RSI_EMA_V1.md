# RSI + EMA v1 — Spec chiến lược

Chiến lược duy nhất Phase 1–3. Nguồn gốc: `AI_Trade/Note.txt`.

## Vùng RSI H4

| Vùng | Band | Vai trò |
|------|------|---------|
| Thấp | 28–32 | TP SHORT |
| Giữa | 48–52 | S/R — mốc 50 |
| Cao | 68–72 | TP LONG |

## Quy ước implement (đã chốt)

| Quy tắc | Giá trị |
|---------|---------|
| RSI H4 | Nến H4 đóng, resample `4h` right-label |
| Chạm band | **Close H4** trong band |
| Thủng | Close ngoài band |
| Entry | Close nến H1 sau signal |
| EMA filter | Giá trong tolerance ATR quanh EMA50/200 |

## Setup IDs

### `s1_break_retest`

- **LONG:** Vượt 52 → hồi 48–52 → bật lên + EMA hỗ trợ
- **SHORT:** Thủng 48 → hồi 48–52 → bật xuống + EMA kháng cự

### `s2_extreme_bounce`

- **LONG:** Trên 50 → chạm 68–72 → hồi 48–52 (lần 1–2) → bật
- **SHORT:** Dưới 50 → chạm 28–32 → hồi 48–52 (lần 1–2) → bật

## Module map

- `backend/strategy/rsi_ema_v1/detector.py` — state detection
- `backend/strategy/rsi_ema_v1/engine.py` — scan + label gate
- `backend/simulator/trade.py` — cùng engine cho label outcome & backtest
