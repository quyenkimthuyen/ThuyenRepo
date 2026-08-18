# IndependentEval — locked protocol (written BEFORE results)

Mục tiêu: so sánh **hai chính sách chọn hyperparams** (AIEdge vs TrainApp-quality)
trên **cùng engine, cùng search space, cùng cost, cùng lịch**, không dùng self-report của AI_app.

## Engine (bắt buộc giống nhau)

- TrainApp core walk-forward: `optimize_on_window` → `generate_signals_mined` → `backtest_mined`
- `remine_each_week=True`, `use_learning=True`
- Slippage: **0.3** pip mọi desk

## Lịch (khóa)

| Split | From | To | Dùng để |
|-------|------|-----|---------|
| VALIDATE | 2025-07-01 | 2025-12-31 | Chọn hyperparams **chỉ ở đây** |
| TEST | 2026-01-01 | 2026-08-07 | Đánh giá **một lần** sau khi đã chọn |

TEST không được dùng để chọn preset / train_weeks / cost_gate.

## Search space (dùng chung hai phía)

Mỗi ô: `(preset, train_weeks, cost_gate_mult|None)`

1. `elite_or_quality`, 6, None
2. `anti_chase_fixed_70`, 6, None
3. `elite_or_quality`, 6, 3.5  (ATR cost-gate)
4. `elite_or_quality`, 3, None  (YAML default train_weeks)

## Cost regimes (chạy riêng từng regime; hai phía cùng cost)

| Regime | EUR | GBP |
|--------|-----|-----|
| `yaml` | 1.0 | 1.5 |
| `realistic` | 1.6 | 2.0 |

## Policy A — `aiedge`

- Score VALIDATE: `robust = total_r / max(dd, 1) - 0.05 * max(0, 55 - wr)`
- Gate: `n_trades >= 20`, `wr >= 42`, `dd <= 14`, `total_r > 0`
- Nếu không ai qua gate: soft_fallback = max robust trong grid (đánh dấu `soft_fallback=true`)

## Policy B — `trainapp_quality`

- Score VALIDATE: `quality = (R/max(DD,0.5))*2 + PF*25 + WR*0.8 + R*0.04`
  (cùng công thức BestQuality / grid `quality` của TrainApp)
- Gate: `total_r > 0` và `profit_factor >= 1.2`
- Soft fallback: max quality nếu không ai qua gate

## Luật thắng trên TEST (đăng ký trước — không dùng decide_winner của AI_app)

Cho mỗi desk × cost regime:

1. **Win** nếu `total_r` cao hơn **và** `max_drawdown_r <= đối phương + 5`
2. Else **Win** nếu `total_r` cao hơn ≥ 10R **và** DD không tệ hơn đối phương quá 10R
3. Else **tie** nếu `|ΔR| < 5` và `|ΔDD| < 5`
4. Else **inconclusive** (ghi rõ metrics; không tự gán thắng)

Tổng hợp:

- Đếm số desk win theo policy
- Đếm số desk **profit** (`total_r > 0`) theo policy
- Không crowning “ít lỗ hơn” là chiến thắng tuyệt đối nếu cả hai `total_r <= 0` — báo riêng `less_negative`

## Không dùng trong quyết định chính

- `AI_app/results/PROOF.md` / `RERANK_PROOF.md` (self-report)
- TrainApp grid rows đã mine/score trên cửa sổ TEST 2026 (OOS leakage)
- Haircut `stress_metrics` — chỉ re-sim thật với spread đã khóa

## Artifacts

- `results/indep_report.json`
- `results/INDEP_REPORT.md`
- Checkpoint theo desk để resume
