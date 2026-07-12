# Architecture Decision Records (ADR)

## ADR-001: Một engine backtest duy nhất

**Trạng thái:** Chấp nhận  
**Bối cảnh:** AI_Trade có similarity, tag_driven, global, rule_mode song song → kết quả khó giải thích.  
**Quyết định:** Setup Trade v1 chỉ có `simulator/` + `strategy/rsi_ema_v1/`. Label outcome dùng cùng simulator.  
**Hệ quả:** Bỏ port `bar_importance` làm entry backtest.

## ADR-002: Walk-forward không trùng năm

**Trạng thái:** Chấp nhận  
**Quyết định:** `label_year`, `optimize_year`, `final_test_year` phải khác nhau; UI + API enforce.  
**Hệ quả:** Không map train_2024 → bt_2024 cho optimize.

## ADR-003: Label gate bắt buộc

**Trạng thái:** Chấp nhận  
**Quyết định:** Không lưu setup nếu state machine không khớp tại `entry_time`.  
**Hệ quả:** Label cũ AI_Trade (alignment ~12%) không migrate — label lại.

## ADR-004: RSI H4 native

**Trạng thái:** Đề xuất — chốt trong Phase 0  
**Quyết định:** Resample OHLC H1 → H4, tính RSI trên H4; map về H1 chỉ để hiển thị.  
**Hệ quả:** Không forward-fill RSI H1 giả làm tín hiệu.

## ADR-005: v1 một chiến lược

**Trạng thái:** Chấp nhận  
**Quyết định:** Ship `rsi_ema_v1` (Note.txt) trước; EMA-only cross là v2.  
**Hệ quả:** Giảm scope, tăng xác suất chứng minh edge.
