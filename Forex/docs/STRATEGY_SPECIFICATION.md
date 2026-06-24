# Strategy Specification

**Price Action Research Lab (PARL)**  
**Version:** 1.0.0  
**Status:** Source of Truth — Phase 5 implementation MUST follow this document  
**Last updated:** 2026-06-22

---

## 1. Mục đích

Tài liệu này định nghĩa **chính xác** ba setup Price Action đầu tiên của PARL. Mọi thuật toán trong Phase 5 phải implement đúng spec này — không được "đoán" quy tắc.

Mục tiêu:

- Backtest **nhất quán** và **có thể kiểm chứng**
- Không lookahead bias
- Mỗi tín hiệu có lý do (reason) mô tả được
- Tham số trong code khớp với schema plugin hiện tại

---

## 2. Quy ước toàn cục

### 2.1 Cặp tiền & Pip

| Symbol  | Pip size | Price decimals |
|---------|----------|----------------|
| EURUSD  | 0.0001   | 5              |
| GBPUSD  | 0.0001   | 5              |
| USDJPY* | 0.01     | 3              |
| XAUUSD* | 0.01     | 2              |

\* Dự phòng cho phase sau. Hiện tại chỉ EURUSD, GBPUSD.

```text
pipsToPrice(pips, symbol) = pips × pipSize(symbol)
```

### 2.2 Candle & thời gian

- Mỗi nến: `{ timestamp, open, high, low, close, volume }`
- `timestamp` = thời điểm **mở** nến (epoch ms, UTC)
- Engine duyệt bar-by-bar: tại index `i` chỉ được dùng `candles[0..i]` (không lookahead)

### 2.3 Định nghĩa Swing Level (dùng chung)

Tại bar `i` (với `i >= swingLookback`):

```text
swingHigh(i)  = max(high[j])  với j ∈ [i - swingLookback, i - 1]
swingLow(i)   = min(low[j])   với j ∈ [i - swingLookback, i - 1]
```

- **Không** tính nến hiện tại `i` vào swing window
- Swing level là **ngang** (horizontal level), không phải trendline

### 2.4 Vùng level (Level Zone)

Mỗi level có vùng chấp nhận để retest/touch:

```text
zoneUpper(level) = level + retestTolerancePips × pipSize
zoneLower(level) = level - retestTolerancePips × pipSize
```

**Mặc định:** `retestTolerancePips = 2` (cố định trong engine, không expose UI trừ khi thêm param sau)

Giá **chạm vùng** khi: `low <= zoneUpper AND high >= zoneLower`

### 2.5 Nến xác nhận (Confirmation Candle)

| Loại | Điều kiện |
|------|-----------|
| **Bullish** | `close > open` AND `close` nằm trong 40% **trên** của range nến |
| **Bearish** | `close < open` AND `close` nằm trong 40% **dưới** của range nến |

```text
range = high - low
bullishCloseZone = low + 0.6 × range   → close >= bullishCloseZone
bearishCloseZone = low + 0.4 × range   → close <= bearishCloseZone
```

Nến doji (`range < 0.5 × pipSize`): **không** được coi là confirmation.

### 2.6 Entry, SL, TP

| Field | Quy tắc |
|-------|---------|
| **Entry** | `close` của nến tín hiệu (market tại close — mô phỏng lệnh market khi nến đóng) |
| **SL** | Theo từng setup (bên dưới) + buffer `slBufferPips` (mặc định 1 pip) |
| **TP** | `entry ± rr × |entry - sl|` theo hướng lệnh |
| **RR** | Lấy từ param `rr` của strategy |

### 2.7 Tín hiệu hết hiệu lực (Setup Expiry)

Mỗi setup đang chờ (pending state) **bị hủy** khi:

1. Quá `retestMaxBars` (hoặc tương đương) kể từ breakout/grab mà chưa có entry
2. Giá **đóng cửa** phá vỡ SL ảo (invalidation level) trước khi entry
3. Một setup **mới cùng hướng** được tạo từ level khác — setup cũ bị thay thế

**Không** sinh tín hiệu trùng: tại cùng `timestamp` + `strategyId` + `direction` chỉ 1 signal.

### 2.8 Confidence Score (0–100)

Công thức chung (cộng điểm, cap 100):

| Factor | Điều kiện | Điểm |
|--------|-----------|------|
| Trend alignment | EMA20 cùng hướng / structure đúng hướng | +15 |
| Session | London (07–16 UTC) hoặc New York (12–21 UTC) | +10 |
| Momentum | Nến xác nhận body > 50% range | +10 |
| RR | rr >= 2 | +10 |
| Location | Retest/grab trong vùng level chính xác (≤ 1 pip) | +15 |
| Quality | Wick rejection rõ (Liquidity Grab / retest wick) | +15 |
| Base | Mặc định mọi signal hợp lệ | +25 |

Setup-specific adjustments được nêu trong từng strategy.

### 2.9 Output Signal (bắt buộc)

Mọi signal phải khớp `src/strategy/Signal.js`:

```json
{
  "id": "sig_...",
  "time": 1717203600000,
  "pair": "EURUSD",
  "timeframe": "H1",
  "direction": "long",
  "entry": 1.08510,
  "sl": 1.08420,
  "tp": 1.08690,
  "rr": 2,
  "confidence": 72,
  "reason": "Bullish break & retest of 1.08450 resistance",
  "screenshotPosition": { "candleIndex": 142, "timestamp": 1717203600000 },
  "strategyId": "break-retest"
}
```

---

## 3. Strategy 1 — Break & Retest

**Plugin ID:** `break-retest`  
**Ý tưởng:** Giá phá vỡ một swing level, sau đó retest level cũ (giờ đổi vai support/resistance) và tiếp tục theo hướng breakout.

### 3.1 Parameters

| Key | Default | Mô tả |
|-----|---------|-------|
| `breakoutPips` | 5 | Số pip tối thiểu vượt level để xác nhận breakout |
| `retestMaxBars` | 10 | Số nến tối đa chờ retest sau breakout |
| `rr` | 2 | Risk-reward |
| `swingLookback` | 5 | Số nến lookback xác định swing level |

### 3.2 State machine

```text
[IDLE]
  → phát hiện breakout → [BREAKOUT_PENDING]
[BREAKOUT_PENDING]
  → retest vùng level + nến xác nhận → [SIGNAL] → [IDLE]
  → quá retestMaxBars → [IDLE]
  → close phá invalidation → [IDLE]
```

### 3.3 Bullish Break & Retest (Long)

**Bước 1 — Xác định resistance**

Tại bar `i`: `level = swingHigh(i)`

**Bước 2 — Breakout**

Tại bar `b` (`b > i`):

```text
breakoutThreshold = level + breakoutPips × pipSize
bullishBreakout = close[b] >= breakoutThreshold
```

Khi đúng → lưu state:

```text
{
  direction: 'long',
  level,
  breakoutBar: b,
  breakoutHigh: high[b],
  invalidation: low[b] - slBufferPips × pipSize,
  expiresAtBar: b + retestMaxBars
}
```

**Bước 3 — Retest**

Tại bar `r` (`b < r <= expiresAtBar`):

```text
retestTouch = chạm vùng level (zoneLower..zoneUpper)
bullishConfirm = retestTouch AND bullishConfirmation(candles[r])
notInvalidated = close[r] >= invalidation
```

**Bước 4 — Signal Long**

Khi bước 3 đúng tại bar `r`:

```text
entry = close[r]
sl    = min(low[r], zoneLower) - slBufferPips × pipSize
tp    = entry + rr × (entry - sl)
reason = "Bullish B&R: broke {level}, retest bar {r - b}, entry on confirmation"
```

### 3.4 Bearish Break & Retest (Short)

Đối xứng:

```text
level = swingLow(i)
breakoutThreshold = level - breakoutPips × pipSize
bearishBreakout = close[b] <= breakoutThreshold
invalidation = high[b] + slBufferPips × pipSize
entry = close[r]
sl    = max(high[r], zoneUpper) + slBufferPips × pipSize
tp    = entry - rr × (sl - entry)
```

### 3.5 Invalidation chi tiết

| Hướng | Hủy setup khi |
|-------|---------------|
| Long | `close < invalidation` trước entry |
| Short | `close > invalidation` trước entry |

### 3.6 Ví dụ EURUSD H1

```text
swingHigh = 1.08450 (bars i-5..i-1)
breakoutPips = 5 → threshold = 1.08500
Bar 100: close = 1.08512 → BREAKOUT_PENDING
Bar 103: low = 1.08440, close = 1.08500, bullish → LONG signal
  entry = 1.08500
  sl    = 1.08430 (dưới retest low)
  tp    = 1.08640 (RR=2)
```

### 3.7 Confidence adjustments

| Điều kiện | Điểm thêm |
|-----------|-----------|
| Breakout body > 60% range | +10 |
| Retest trong ≤ 3 bars sau breakout | +10 |
| Retest wick chạm level, close trên level | +10 |

---

## 4. Strategy 2 — EMA Pullback

**Plugin ID:** `ema-pullback`  
**Ý tưởng:** Xu hướng được xác nhận bởi EMA fast/slow, chờ pullback về vùng EMA fast, entry khi nến xác nhận hướng trend.

### 4.1 Parameters

| Key | Default | Mô tả |
|-----|---------|-------|
| `emaFast` | 20 | Chu kỳ EMA nhanh |
| `emaSlow` | 50 | Chu kỳ EMA chậm |
| `rr` | 2 | Risk-reward |
| `pullbackTolerancePips` | 3 | Vùng chấp nhận quanh EMA fast |
| `trendBars` | 5 | Số nến xác nhận xu hướng |

### 4.2 EMA calculation

EMA chuẩn, tính **chỉ trên `candles[0..i]`**:

```text
k = 2 / (period + 1)
EMA[0] = close[0]
EMA[t] = close[t] × k + EMA[t-1] × (1 - k)
```

### 4.3 Trend confirmation

Tại bar `i`, sau khi có đủ `emaSlow` bars:

**Uptrend** — tất cả điều kiện:

```text
1. EMA_fast[i] > EMA_slow[i]
2. EMA_fast[i] > EMA_fast[i - trendBars]        // EMA fast dốc lên
3. close[i] > EMA_slow[i]                        // giá trên slow EMA
4. Đếm higher closes: ít nhất ceil(trendBars × 0.6) nến
   trong [i - trendBars + 1 .. i] có close > close trước đó
```

**Downtrend** — đối xứng:

```text
1. EMA_fast[i] < EMA_slow[i]
2. EMA_fast[i] < EMA_fast[i - trendBars]
3. close[i] < EMA_slow[i]
4. lower closes: ceil(trendBars × 0.6) nến giảm liên tiếp trong window
```

Không có trend → **không** tìm entry.

### 4.4 Khoảng cách EMA (filter chất lượng)

Trend phải **rõ**:

```text
emaSpread = |EMA_fast[i] - EMA_slow[i]|
minSpread = 3 × pipSize     // tối thiểu 3 pips
maxSpread = 50 × pipSize    // tối đa 50 pips (tránh overextended)
```

`emaSpread` phải nằm trong `[minSpread, maxSpread]`.

### 4.5 Pullback zone

```text
zoneUpper = EMA_fast[i] + pullbackTolerancePips × pipSize
zoneLower = EMA_fast[i] - pullbackTolerancePips × pipSize
```

**Pullback touch** tại bar `i`:

```text
long:  low[i] <= zoneUpper AND close[i] >= zoneLower
short: high[i] >= zoneLower AND close[i] <= zoneUpper
```

### 4.6 Entry rules

**Long** (trong uptrend):

```text
1. Uptrend confirmed tại i
2. Pullback touch tại i
3. bullishConfirmation(candles[i])
4. close[i] > EMA_fast[i]     // đóng cửa phục hồi trên EMA
5. low[i] > EMA_slow[i]       // không phá slow EMA
```

```text
entry = close[i]
sl    = min(low[i], zoneLower) - slBufferPips × pipSize
tp    = entry + rr × (entry - sl)
```

**Short** (downtrend): đối xứng.

### 4.7 Cooldown

Sau mỗi signal, **không** sinh signal mới cùng hướng trong `trendBars` nến tiếp theo (tránh duplicate trên cùng pullback).

### 4.8 Invalidation

Setup pullback bị hủy nếu trước khi có confirmation:

- Long: `close < EMA_slow` 
- Short: `close > EMA_slow`

### 4.9 Ví dụ

```text
EMA20 = 1.08520, EMA50 = 1.08480, uptrend OK
Bar i: low = 1.08515 (chạm EMA20), close = 1.08540, bullish
→ LONG entry 1.08540, sl 1.08490, tp 1.08640 (RR=2)
reason = "EMA pullback long: trend up, touch EMA20, bullish confirm"
```

### 4.10 Confidence adjustments

| Điều kiện | Điểm thêm |
|-----------|-----------|
| emaSpread trong [5, 20] pips | +10 |
| Pullback chỉ wick chạm EMA, body trên | +15 |
| Session London/NY | +10 (cộng thêm global) |

---

## 5. Strategy 3 — Liquidity Grab

**Plugin ID:** `liquidity-grab`  
**Ý tưởng:** Giá quét qua swing high/low (lấy liquidity / stop hunt), đóng cửa quay lại trong range cũ — false breakout.

### 5.1 Parameters

| Key | Default | Mô tả |
|-----|---------|-------|
| `swingLookback` | 7 | Lookback xác định swing level |
| `grabPips` | 3 | Pip tối thiểu vượt swing để coi là grab |
| `wickRatio` | 0.6 | Tỷ lệ wick tối thiểu / range nến |
| `rr` | 2 | Risk-reward |

### 5.2 Swing level

Giống mục 2.3, tại bar `i` **trước** nến grab:

```text
level_high = swingHigh(i)   // dùng cho bearish grab (quét đỉnh)
level_low  = swingLow(i)    // dùng cho bullish grab (quét đáy)
```

### 5.3 Bearish Liquidity Grab (Short)

**Điều kiện tại bar `g`:**

```text
1. high[g] >= level_high + grabPips × pipSize    // quét trên swing high
2. close[g] < level_high                          // đóng cửa quay lại dưới level
3. upperWick[g] / range[g] >= wickRatio           // wick trên đủ lớn
4. bearishConfirmation(candles[g])               // nến bearish xác nhận
```

```text
upperWick = high - max(open, close)
range     = high - low
```

**Signal Short:**

```text
entry = close[g]
sl    = high[g] + slBufferPips × pipSize
tp    = entry - rr × (sl - entry)
reason = "Liquidity grab short: swept {level_high}, rejected bar {g}"
```

### 5.4 Bullish Liquidity Grab (Long)

Đối xứng:

```text
1. low[g] <= level_low - grabPips × pipSize
2. close[g] > level_low
3. lowerWick[g] / range[g] >= wickRatio
4. bullishConfirmation(candles[g])
```

```text
lowerWick = min(open, close) - low
entry = close[g]
sl    = low[g] - slBufferPips × pipSize
tp    = entry + rr × (entry - sl)
```

### 5.5 Volume filter (tùy chọn, mặc định BẬT)

```text
avgVolume = mean(volume[j]) với j ∈ [g - swingLookback, g - 1]
volumeOK  = volume[g] >= 0.8 × avgVolume
```

Nếu `volume[g] === 0` (data thiếu volume) → **bỏ qua** filter volume.

### 5.6 Một grab mỗi level

Sau signal tại level `L`, không sinh signal mới cùng hướng từ cùng `L` trong `swingLookback × 2` bars.

### 5.7 Invalidation

Liquidity grab **không** dùng pending state — signal sinh **ngay** tại bar `g` nếu đủ điều kiện (single-bar pattern).

### 5.8 Ví dụ

```text
swingHigh = 1.08600
Bar g: high = 1.08635 (+3.5 pips), close = 1.08580, upperWick/range = 0.65
→ SHORT entry 1.08580, sl 1.08645, tp 1.08450 (RR≈2)
```

### 5.9 Confidence adjustments

| Điều kiện | Điểm thêm |
|-----------|-----------|
| wickRatio >= 0.7 | +15 |
| grabPips >= 5 | +10 |
| volume >= 1.2 × avgVolume | +10 |
| close quay lại trong 2 pips dưới/trên level | +10 |

---

## 6. Inside Bar Breakout

**Plugin ID:** `inside-bar-breakout`  
**Category:** Price Action — continuation after consolidation

### 6.1 Parameters

| Param | Default | Range | Description |
|-------|---------|-------|-------------|
| `trendEma` | 50 | 20 / 50 / 200 | Long when close > EMA; short when close < EMA |
| `motherMinRangePips` | 10 | 3–80 | Mother bar minimum range (pips) |
| `breakoutBufferPips` | 1 | 0–10 | Close must exceed mother extreme by buffer |
| `maxWaitBars` | 3 | 1–10 | Bars after inside bar to allow breakout |
| `rr` | 2 | 1–10 | Risk-reward |

### 6.2 Pattern detection

At bar `i` (with `i >= 2`):

```text
mother = candles[i - 2]
inside = candles[i - 1]

insideBar = inside.high < mother.high AND inside.low > mother.low
motherRangePips >= motherMinRangePips
```

When detected in `calculate()`, store pending setup until `expiresAtBar = (i - 1) + maxWaitBars`.

### 6.3 Long signal

At bar `b` while pending is active:

```text
1. close[b] > mother.high + breakoutBufferPips × pipSize
2. close[b] > EMA(trendEma)
3. entry = close[b]
4. sl = mother.low - slBufferPips × pipSize
5. tp = entry + rr × (entry - sl)
```

### 6.4 Short signal

```text
1. close[b] < mother.low - breakoutBufferPips × pipSize
2. close[b] < EMA(trendEma)
3. entry = close[b]
4. sl = mother.high + slBufferPips × pipSize
5. tp = entry - rr × (sl - entry)
```

### 6.5 State

Pending setup cleared after signal or expiry. New inside-bar pattern replaces pending.

---

## 7. Pin Bar Rejection

**Plugin ID:** `pin-bar-rejection`  
**Category:** Price Action — rejection at swing S/R (no sweep required)

### 7.1 Parameters

| Param | Default | Range | Description |
|-------|---------|-------|-------------|
| `swingLookback` | 7 | 3–30 | Swing high/low lookback |
| `retestTolerancePips` | 2 | 1–10 | Level touch zone |
| `minWickRatio` | 0.55 | 0.4–0.85 | Rejection wick / range |
| `maxBodyRatio` | 0.35 | 0.15–0.5 | Max body / range |
| `rr` | 2 | 1–10 | Risk-reward |

### 7.2 Swing levels

Same as §2.3 at bar `i` before signal candle.

### 7.3 Short at swing high

```text
1. touchesZone(candle, swingHigh, retestTolerancePips)
2. upperWick / range >= minWickRatio
3. body / range <= maxBodyRatio
4. bearishConfirmation(candle)
5. entry = close; sl = high + slBuffer; tp per RR
```

### 7.4 Long at swing low

```text
1. touchesZone(candle, swingLow, retestTolerancePips)
2. lowerWick / range >= minWickRatio
3. body / range <= maxBodyRatio
4. bullishConfirmation(candle)
5. entry = close; sl = low - slBuffer; tp per RR
```

### 7.5 Duplicate prevention

No repeat signal same direction from level within `retestTolerancePips` for `swingLookback × 2` bars.

### 7.6 Difference from Liquidity Grab

Pin Bar requires **touch** of swing zone only — **no** `grabPips` sweep beyond level.

---

## 8. Wyckoff Spring / UTAD (`wyckoff-spring-utad`)

**Category:** Wyckoff — false break of consolidation range

### 8.1 Parameters

| Param | Default | Range | Description |
|-------|---------|-------|-------------|
| `rangeLookback` | 20 | 10–60 | Bars defining horizontal range |
| `minRangePips` | 15 | 5–80 | Minimum range height |
| `minInsideRatio` | 0.65 | 0.4–0.95 | Share of closes inside range |
| `sweepPips` | 2 | 1–20 | Breach beyond boundary |
| `wickRatio` | 0.55 | 0.35–0.85 | Rejection wick / range |
| `rr` | 2 | 1–10 | Risk-reward |

### 8.2 Trading range

At bar `i` (excluding current candle):

```text
rangeHigh = max(high[j])  j ∈ [i - rangeLookback, i - 1]
rangeLow  = min(low[j])   j ∈ [i - rangeLookback, i - 1]
rangeWidthPips >= minRangePips
closeInsideRatio >= minInsideRatio
```

### 8.3 Spring (LONG)

```text
1. low <= rangeLow - sweepPips
2. close > rangeLow
3. lowerWick / range >= wickRatio
4. bullishConfirmation(candle)
5. entry = close; sl below spring low; tp per RR
```

### 8.4 UTAD (SHORT)

```text
1. high >= rangeHigh + sweepPips
2. close < rangeHigh
3. upperWick / range >= wickRatio
4. bearishConfirmation(candle)
5. entry = close; sl above UTAD high; tp per RR
```

### 8.5 Difference from Liquidity Grab

| | Wyckoff Spring/UTAD | Liquidity Grab |
|--|---------------------|----------------|
| Level | Range boundary (longer lookback) | Swing point |
| Context | Consolidation required | None |
| Entry | Spring/UTAD bar | Grab bar |

---

## 9. Wyckoff Range Test (`wyckoff-range-test`)

**Category:** Wyckoff — secondary test after spring/UTAD

### 9.1 Parameters

| Param | Default | Range | Description |
|-------|---------|-------|-------------|
| `rangeLookback` | 20 | 10–60 | Range definition |
| `minRangePips` | 15 | 5–80 | Min range height |
| `minInsideRatio` | 0.65 | 0.4–0.95 | Consolidation quality |
| `sweepPips` | 2 | 1–20 | Spring/UTAD sweep |
| `testMaxBars` | 8 | 2–25 | Bars to wait for test |
| `testTolerancePips` | 3 | 1–10 | Test touch zone |
| `rallyMinPips` | 5 | 2–40 | Min rally away from boundary |
| `eventWickRatio` | 0.5 | 0.35–0.85 | Wick on spring/UTAD arm bar |
| `testWickRatio` | 0.45 | 0.3–0.8 | Wick on test entry bar |
| `rr` | 2 | 1–10 | Risk-reward |

### 9.2 State machine

```text
1. Valid spring/UTAD → store pending event (no signal on event bar)
2. Track rallyHigh / rallyLow until expiry or invalidation
3. LONG test: touches rangeLow zone, low > springLow, rally >= rallyMinPips, bullish confirm
4. SHORT test: touches rangeHigh zone, high < utadHigh, rally >= rallyMinPips, bearish confirm
```

### 9.3 Invalidation

- Spring pending cancelled if a later bar breaks below `springLow - sweepPips`
- UTAD pending cancelled if a later bar breaks above `utadHigh + sweepPips`

---

## 10. Thứ tự thực thi trong Engine

Tại mỗi bar `i` (warmup đủ):

```text
1. strategy.calculate(candles, i)     // cập nhật state, indicators
2. signal = strategy.generateSignal(ctx)
3. if signal AND strategy.validate(signal) → lưu signal
```

`validate()` mặc định gọi `isValidSignal()` + kiểm tra setup-specific trong từng strategy.

---

## 11. Test cases bắt buộc (Phase 5)

Mỗi strategy cần pass các case sau trước khi merge:

### 11.1 Break & Retest

| # | Input | Kỳ vọng |
|---|-------|---------|
| BR-01 | Breakout không đủ pips | Không signal |
| BR-02 | Breakout đúng, retest bar 5, bullish | 1 LONG |
| BR-03 | Breakout đúng, quá retestMaxBars | Không signal |
| BR-04 | Breakout long, close phá invalidation | Không signal |
| BR-05 | 2 breakout cùng level | Chỉ 1 signal (cái đầu hoặc expiry) |

### 11.2 EMA Pullback

| # | Input | Kỳ vọng |
|---|-------|---------|
| EP-01 | EMA20 < EMA50 | Không long |
| EP-02 | Uptrend, pullback EMA20, bullish | 1 LONG |
| EP-03 | Touch EMA nhưng close dưới EMA slow | Không signal |
| EP-04 | emaSpread < 3 pips | Không signal |
| EP-05 | 2 signal liên tiếp trong cooldown | Chỉ 1 |

### 11.3 Liquidity Grab

| # | Input | Kỳ vọng |
|---|-------|---------|
| LG-01 | High sweep nhưng close trên level | Không short |
| LG-02 | Sweep + close dưới + wick 0.65 | 1 SHORT |
| LG-03 | Sweep đủ nhưng wickRatio < min | Không signal |
| LG-04 | Bullish grab đáy đối xứng | 1 LONG |
| LG-05 | Duplicate level trong window | Chỉ 1 |

### 11.4 Inside Bar Breakout

| # | Input | Kỳ vọng |
|---|-------|---------|
| IB-01 | Mother range quá nhỏ | Không signal |
| IB-02 | Inside + break up + trên EMA | 1 LONG |
| IB-03 | Inside + break down + dưới EMA | 1 SHORT |
| IB-04 | Quá maxWaitBars không break | Không signal |

### 11.5 Pin Bar Rejection

| # | Input | Kỳ vọng |
|---|-------|---------|
| PB-01 | Chạm swing nhưng body lớn | Không short |
| PB-02 | Pin bear tại swing high | 1 SHORT |
| PB-03 | Pin bull tại swing low | 1 LONG |
| PB-04 | Wick quá nhỏ | Không signal |
| PB-05 | Duplicate level | Chỉ 1 |

### 11.6 Wyckoff Spring / UTAD

| # | Input | Kỳ vọng |
|---|-------|---------|
| WS-01 | Spring sweep nhưng close dưới rangeLow | Không long |
| WS-02 | Spring hợp lệ trong range | 1 LONG |
| WS-03 | UTAD hợp lệ trong range | 1 SHORT |
| WS-04 | Thị trường trend (không consolidation) | Không signal |

### 11.7 Wyckoff Range Test

| # | Input | Kỳ vọng |
|---|-------|---------|
| WT-01 | Test phá đáy spring | Không long |
| WT-02 | Spring + rally + higher-low test | 1 LONG |
| WT-03 | Chưa rally đủ trước test | Không signal |

---

## 12. Ghi chú triển khai

1. **Pip helper:** tạo `src/utils/pip.js` — `getPipSize(symbol)`, `pipsToPrice(pips, symbol)`
2. **Shared helpers:** `CandlePatterns.js`, `WyckoffRange.js` (trading range, spring, UTAD, test)
3. **State persistence:** Break & Retest + Wyckoff Range Test dùng pending state; Liquidity Grab / Wyckoff Spring-UTAD single-bar entry
4. **Reason string:** luôn có level giá (5 decimals), bar index, hướng
5. **Không** dùng dữ liệu `candles[i+1]` trong bất kỳ điều kiện nào

---

## 13. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-06-22 | Added Wyckoff Spring/UTAD + Wyckoff Range Test |
| 1.1.0 | 2026-06-23 | Added Inside Bar Breakout + Pin Bar Rejection |
| 1.0.0 | 2026-06-22 | Initial specification for 3 PA setups |

---

*Tài liệu này là contract giữa research spec và implementation. Mọi thay đổi quy tắc phải cập nhật version và changelog trước khi sửa code.*
