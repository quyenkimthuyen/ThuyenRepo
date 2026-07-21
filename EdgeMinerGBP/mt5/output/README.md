# ForexForge → MetaTrader 5 Expert Advisor

Chuyển **Trade Model** trong ForexForge thành EA tự động trên MT5.

## Export từ CLI

```bash
cd /thuyen_check/logging/bk/EdgeMiner2
python scripts/export_mt5_ea.py
```

Tùy chọn:

```bash
python scripts/export_mt5_ea.py --model-id tm_xxx
python scripts/export_mt5_ea.py --out /path/to/output
python scripts/export_mt5_ea.py --no-remine   # dùng last_strategy đã lưu
```

Hoặc từ GUI: **Trade Models → Export MT5 EA**.

## Cài đặt trên MT5

1. Mở thư mục `mt5/output/` sau khi export.
2. Copy toàn bộ vào:
   ```
   <MT5 Data>/MQL5/Experts/ForexForgeEA/
   ```
3. Mở **MetaEditor** → compile `ForexForgeEA.mq5`.
4. Kéo EA lên chart **GBPUSD H1**.
5. Bật **Algo Trading** trên toolbar.

## Cập nhật hàng tuần

Strategy được mine lại mỗi tuần (walk-forward). **Đầu mỗi tuần**, chạy lại export và copy `Include/ForgeConfig.mqh` mới vào MT5 (hoặc copy lại cả thư mục).

## EA làm gì

- Đọc rules + ML weights từ `ForgeConfig.mqh` (sinh từ trade model).
- Tính features giống `feature_engine.py`.
- Vào lệnh khi rule score + ML filter khớp (tối đa 2 lệnh/tuần).
- SL/TP theo ATR × `atr_mult`, RR từ config.
- Exit: `full` / `partial` / `trail` / `hybrid` theo strategy.

## Input EA

| Input | Mặc định | Ý nghĩa |
|-------|----------|---------|
| InpRiskPct | 1.0 | % balance risk mỗi lệnh |
| InpMagic | 20260721 | Magic number |
| InpMaxSpreadPts | 25 | Lọc spread (0 = tắt) |
| InpAllowLong/Short | true | Cho phép hướng lệnh |

## Lưu ý

- Symbol khuyến nghị: **GBPUSD**, timeframe **H1**.
- Export **mine lại** strategy tuần hiện tại (cùng logic paper monitor).
- So khớp paper ForexForge vs MT5 demo trước khi live.
- ML là LogisticRegression — export trọng số trực tiếp, không cần ONNX.

## Cấu trúc file

```
mt5/output/
  ForexForgeEA.mq5      # EA chính
  Include/
    ForgeConfig.mqh     # Generated — strategy + ML
    ForgeFeatures.mqh   # Feature engine
    ForgeSignals.mqh    # Rule + ML signals
    ForgeTrade.mqh      # Risk & exit
  forge_export.json     # JSON tham khảo
```
