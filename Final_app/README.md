# Final_app — 4 desk clean train (GUIDE validation)

Clone sạch từ `backtest/` + `backtestM5/`, **không** mang Trade Model / KB / Grid cũ.
Huấn luyện lại từ đầu theo `GUIDE_TRAIN_TRADE_MODELS.md` để kiểm chứng EUR vs GBP, M5 vs M15 trên **cùng OOS** `2026-01-01`→`2026-08-07`.

## Desks

| Folder | INSTANCE | TF | Sym | App | Magic Live/Sim |
|--------|----------|----|-----|-----|----------------|
| EdgeMinerEURUSDM15 | M15F1 | M15 | EUR | 8511 | 20261501 / 20262501 |
| EdgeMinerGBPUSDM15 | M15F2 | M15 | GBP | 8521 | 20261521 / 20262521 |
| EdgeMinerEURUSDM5 | M5F3 | M5 | EUR | 8531 | 20261541 / 20262541 |
| EdgeMinerGBPUSDM5 | M5F4 | M5 | GBP | 8541 | 20261561 / 20262561 |

`data/` được **symlink** về source (tiết kiệm disk). Kết quả train chỉ nằm trong `Final_app/*/results/`.

## Split Lab ↔ Live

```text
Final_app/split_app/
  lab/     export .tmpkg từ 4 desk EdgeMiner*
  live/    import package + roster + UI :8601
  mt5/     ForgeBridgeLive (EA chung)
```

Chi tiết: `split_app/README.md`.

## Manage apps (start / stop / status)

**Linux:**

```bash
cd /home/thuyenng/work/ThuyenRepo/Final_app
./manage_clones.sh status
./manage_clones.sh start              # all 4
./manage_clones.sh restart F3
./manage_clones.sh stop M15           # F1+F2
./manage_clones.sh start EUR          # F1+F3
```

**Windows:**

```powershell
cd C:\Work\ThuyenRepo\Final_app
.\manage_clones.cmd Status
.\manage_clones.cmd Start
.\manage_clones.ps1 Restart -Apps F3
.\manage_clones.ps1 DeployEA                    # all 4 (compile + attach)
.\manage_clones.ps1 DeployEA -Apps F1,F3 -Mode Both
.\manage_clones.ps1 DeployEA -NoAttach          # compile/link only
.\manage_clones.ps1 DeployEA -NoEnableTrading
```

`DeployEA` chỉ có trên Windows (gọi `scripts/deploy_xm_forgebridge.ps1` từng desk).

## Setup + train

```bash
cd /home/thuyenng/work/ThuyenRepo
# 1) Clone + clean
EdgeMinerM15B5/.venv/bin/python Final_app/bootstrap_clone_clean.py

# 2) Full KB → Grid(quality) → Promote → Unify → Pareto
chmod +x Final_app/run_final_train.sh
nohup Final_app/run_final_train.sh > Final_app/final_train.nohup.log 2>&1 &

# Theo dõi
tail -f Final_app/final_train.log
```

Settings mỗi desk (GUIDE):

- OOS `2026-01-01`→`2026-08-07`
- `grid_objective: quality`
- Eras: `2025-h2`, `5-thang-cuoi-2025` (4 loops)
- train_weeks: 3 & 6
- M5 presets: `elite_or_quality`, `elite_m5_balanced`, `anti_chase_fixed_70`
- M15 presets: `elite_or_quality`, `anti_chase_fixed_70`, `elite_55_4`

## Output

- `Final_app/final_train.log`
- `*/results/research/` + `trade_models.json`
- `results_final_guide_validation.md` — Pareto 4 cell

## Lưu ý thời gian

Full 4 desk (2 eras × 4 epochs KB + grid ~24–48 combo) thường **nhiều giờ**. Chạy background; không mở Streamlit song song trên cùng desk khi đang grid nặng.
