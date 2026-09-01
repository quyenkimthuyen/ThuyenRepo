"""Execution cost model — spread & slippage (EUR/USD).

Quy ước giá của toàn bộ engine: **OHLC là giá Bid**. Kiểm chứng được trên tick
sống của EA — `bar.close` trùng khít `bid`, không phải mid (connection.json,
2026-08-31: bid=1.15995 ask=1.16015 close=1.15995).

MT5 khớp lệnh theo Bid/Ask, không theo mid:

  BUY   vào ở Ask = Bid + spread   ·  SL/TP đối chiếu Bid
  SELL  vào ở Bid                  ·  SL/TP đối chiếu Ask = Bid + spread

Trước 2026-08-31 hai hàm entry/exit dùng quy ước mid (lệch nửa spread về mỗi
phía) trên dữ liệu Bid, và giá ra còn bị trừ thêm nửa spread lên chính mức SL/TP
đã bao gồm spread — tức tính phí hai lần. Đo lại bằng
`scripts/audit_fill_realism.py`: phí hai lần làm tổng R thấp hơn thực tế ~41 R
trên sổ 350 lệnh, còn neo giá mid làm nó cao hơn ~15 R, và cái sau lệch theo
chiều lệnh nên bẻ luôn việc miner chọn chiều.
"""
from __future__ import annotations

PIP = 0.0001


def round_trip_cost_pips(spread_pips: float, slippage_pips: float) -> float:
  return spread_pips + 2.0 * slippage_pips


def spread_price(spread_pips: float) -> float:
  """One spread in price units (5-digit FX)."""
  return max(0.0, float(spread_pips)) * PIP


def slippage_price(slippage_pips: float) -> float:
  """One slippage allowance in price units."""
  return max(0.0, float(slippage_pips)) * PIP


def atr_stop_distance(atr: float, atr_mult: float, spread_pips: float = 0.0) -> float:
  """Stop distance that still leaves ATR room after the broker hits the opposite quote.

  Live SELL SL fills on Ask, BUY SL on Bid. OHLC is Bid. Adding one spread to the
  ATR stop keeps the intended ATR adverse room instead of dying inside the spread.
  """
  return float(atr_mult) * float(atr) + spread_price(spread_pips)


def cost_r_from_pips(cost_pips: float, risk_price: float) -> float:
  if risk_price <= 0:
    return 0.0
  return (cost_pips * PIP) / risk_price


def entry_fill_price(
  raw_open: float, direction: int, spread_pips: float, slippage_pips: float,
) -> float:
  """Giá khớp lệnh vào, theo đúng phía quote mà MT5 dùng.

  BUY khớp ở Ask nên cộng nguyên một spread; SELL khớp ở Bid nên không cộng
  spread. Cả hai chịu thêm trượt giá bất lợi vì EA gửi lệnh thị trường.
  """
  slip = slippage_price(slippage_pips)
  if direction == 1:
    return raw_open + spread_price(spread_pips) + slip
  return raw_open - slip


def market_exit_price(
  raw_price: float, direction: int, spread_pips: float, slippage_pips: float,
) -> float:
  """Giá khớp khi đóng bằng lệnh thị trường (hết hạn giữ, đóng tay).

  Đóng một lệnh BUY là bán ở Bid; đóng một lệnh SELL là mua ở Ask.
  """
  slip = slippage_price(slippage_pips)
  if direction == 1:
    return raw_price - slip
  return raw_price + spread_price(spread_pips) + slip


def stop_exit_price(level: float, direction: int, slippage_pips: float) -> float:
  """Giá khớp khi SL bị chạm — lệnh stop, khớp ở mức SL cộng trượt bất lợi.

  Không cộng spread: mức SL tuyệt đối đã bao gồm một spread qua
  `atr_stop_distance`, và phía quote đã được xử lý ở chỗ so sánh điều kiện chạm.
  """
  slip = slippage_price(slippage_pips)
  return level - slip if direction == 1 else level + slip


def limit_exit_price(level: float) -> float:
  """Giá khớp khi TP bị chạm — lệnh limit, khớp đúng mức TP hoặc tốt hơn."""
  return level


def plan_levels(
  raw_entry: float,
  direction: int,
  atr: float,
  atr_mult: float,
  rr: float,
  spread_pips: float,
  slippage_pips: float,
) -> tuple[float, float, float, float]:
  """Entry / SL / TP / risk từ Bid open (hoặc close ước lượng) + ATR.

  Cùng hình học mà miner, nhãn, paper và live projection dùng.
  """
  entry = entry_fill_price(raw_entry, int(direction), spread_pips, slippage_pips)
  sl_d = atr_stop_distance(atr, atr_mult, spread_pips)
  if int(direction) == 1:
    sl, tp = entry - sl_d, entry + sl_d * float(rr)
  else:
    sl, tp = entry + sl_d, entry - sl_d * float(rr)
  return entry, sl, tp, sl_d


def manage_quote_high(bid_high: float, direction: int, spread_pips: float) -> float:
  """High phía quote dùng để quản lý vị thế: BUY = Bid, SELL = Ask."""
  if int(direction) == 1:
    return float(bid_high)
  return float(bid_high) + spread_price(spread_pips)


def manage_quote_low(bid_low: float, direction: int, spread_pips: float) -> float:
  """Low phía quote dùng để quản lý vị thế: BUY = Bid, SELL = Ask."""
  if int(direction) == 1:
    return float(bid_low)
  return float(bid_low) + spread_price(spread_pips)


def hit_sl_tp(
  direction: int,
  bid_high: float,
  bid_low: float,
  sl: float,
  tp: float,
  spread_pips: float,
  slippage_pips: float,
) -> tuple[str | None, float | None]:
  """SL trước TP. Trả ``('sl'|'tp', giá khớp)`` hoặc ``(None, None)``."""
  direction = int(direction)
  if direction == 1:
    if bid_low <= sl:
      return "sl", stop_exit_price(sl, 1, slippage_pips)
    if bid_high >= tp:
      return "tp", limit_exit_price(tp)
    return None, None
  qh = manage_quote_high(bid_high, -1, spread_pips)
  ql = manage_quote_low(bid_low, -1, spread_pips)
  if qh >= sl:
    return "sl", stop_exit_price(sl, -1, slippage_pips)
  if ql <= tp:
    return "tp", limit_exit_price(tp)
  return None, None


def rebase_levels(
  direction: int,
  fill_entry: float,
  planned_entry: float,
  planned_sl: float,
  planned_tp: float,
  rr: float | None = None,
) -> tuple[float, float, float]:
  """Neo SL/TP quanh giá khớp thật, giữ nguyên risk/RR đã lên kế hoạch.

  Live EA và HistoryFeed paper làm đúng việc này khi Bid/Ask lúc gửi lệnh
  khác entry ước lượng từ nến đóng.
  """
  direction = int(direction)
  planned_risk = abs(planned_entry - planned_sl) if planned_entry > 0 else 0.0
  if planned_risk <= 0.0:
    if planned_entry > 0.0:
      delta = fill_entry - planned_entry
      sl = planned_sl + delta
      tp = planned_tp + delta
      return sl, tp, abs(fill_entry - sl)
    return planned_sl, planned_tp, abs(fill_entry - planned_sl)
  if rr is None or rr <= 0.0:
    rr = abs(planned_tp - planned_entry) / planned_risk
  if direction == 1:
    sl = fill_entry - planned_risk
    tp = fill_entry + planned_risk * rr
  else:
    sl = fill_entry + planned_risk
    tp = fill_entry - planned_risk * rr
  return sl, tp, planned_risk


def apply_cost_to_r(pnl_r: float, risk_price: float, spread_pips: float, slippage_pips: float) -> float:
  cost_r = cost_r_from_pips(round_trip_cost_pips(spread_pips, slippage_pips), risk_price)
  return pnl_r - cost_r
