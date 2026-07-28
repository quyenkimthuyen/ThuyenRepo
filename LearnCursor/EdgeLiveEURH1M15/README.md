# ForexForge — EUR/USD H1 + M15 Live/Sim (unified)

Một app duy nhất thay cho `EdgeMinerH1` + `EdgeMinerM15`: Learning/KB/Grid/Trade Models
theo timeframe, và **bốn** bridge runtime chạy song song (H1/M15 × Live/Sim).

| Runtime | Magic | Chart port | Bridge dir | EA |
|---|---|---|---|---|
| M15 Live | 20260724 | 8765 | `mt5/bridge_m15` | ForgeBridgeM15 |
| M15 Sim | 20260726 | 8876 | `mt5/bridge_sim_m15` | ForgeBridgeM15Sim |
| H1 Live | 20260725 | 8865 | `mt5/bridge_h1` | ForgeBridgeH1 |
| H1 Sim | 20260727 | 8877 | `mt5/bridge_sim_h1` | ForgeBridgeH1Sim |

Artifacts theo TF: `results/m15/`, `results/h1/`. Paper trading đã gỡ.

App Streamlit mặc định: `http://127.0.0.1:8501`.

## Chạy app

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Start
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Restart
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Status
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Stop
```

Deploy EA (chọn TF):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Timeframe M15 -Mode Live
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Timeframe H1 -Mode Live
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Timeframe M15 -Mode HistoryFeed
```

Deploy **cả 4 EA** (M15/H1 × Live/Sim) — cũng có nút **Deploy 4 EA** trên sidebar:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_all_forgebridge.ps1 -Attach -EnableTrading
```

Cần **2 chart EURUSD M15 + 2 chart EURUSD H1** (free hoặc đã gắn đúng EA).
Linux/macOS:

```bash
pip install -r requirements.txt
python run_gui.py
```

CLI:

```bash
FORGE_TF=M15 python run_backtest.py
FORGE_TF=H1 python run_backtest.py
FORGE_TF=M15 python run_learning.py
```

## Ghi chú

- `EdgeMinerH1` / `EdgeMinerM15` giữ nguyên (tham chiếu). App mới: `EdgeLiveEURH1M15`.
- Sau khi đổi bridge subdir (`bridge_m15` …) cần **redeploy / recompile** EA trên MT5.
