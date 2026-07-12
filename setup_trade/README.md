# Setup Trade

App trading **research → validate → paper → live** — xây trên kinh nghiệm `AI_Trade`, hướng tới backtest đáng tin và vận hành thực chiến.

## Bắt đầu

Đọc kế hoạch chi tiết: **[PLAN.md](./PLAN.md)**

## Trạng thái

| Phase | Mô tả | Trạng thái |
|-------|--------|------------|
| 0 | Nền móng, data H4, CI | Hoàn thành |
| 1 | Strategy engine (RSI+EMA v1) | Hoàn thành |
| 2 | Label app + gate | Hoàn thành |
| 3 | Research & optimize | **Hoàn thành** |
| 4 | Walk-forward validation | **Đã chạy fold_a** — OOS FAIL |
| 5 | Paper trade | Chưa bắt đầu |
| 6 | Live | Chưa bắt đầu |

## Chạy app

```bash
cd setup_trade
pip install -r requirements.txt
./run.sh
# → http://127.0.0.1:8767
```

## CLI backtest

```bash
python scripts/run_backtest_cli.py --period bt_2023
```

## Walk-forward (Phase 3–4)

```bash
# Auto-label 50 setup trên train_2022
python scripts/auto_label.py --period train_2022 --max 50

# Chạy từng bước fold_a
python scripts/run_fold.py --fold fold_a --step auto_label
python scripts/run_fold.py --fold fold_a --step analyze
python scripts/run_fold.py --fold fold_a --step optimize
python scripts/run_fold.py --fold fold_a --step final_backtest

# Hoặc validation đầy đủ (optimize + OOS + báo cáo)
python scripts/run_validation.py --fold fold_a
python scripts/run_validation.py --fold fold_a --show-last
```

## Test

```bash
pytest
```

## Repo liên quan

- `/home/toc/thuyen/repo/AI_Trade` — prototype / lab label
- Spec chiến lược: `AI_Trade/Note.txt`
