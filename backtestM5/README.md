# backtestM5 — EURUSD / GBPUSD on M5

Cloned from `backtest/` M15 desks to compare pipeline effectiveness on M5.

| Desk | Folder | App | INSTANCE |
|------|--------|-----|----------|
| E31 EUR | `EdgeMinerEURUSDM5` | http://127.0.0.1:8811 | `M5E31` |
| G33 GBP | `EdgeMinerGBPUSDM5` | http://127.0.0.1:8831 | `M5G33` |

```powershell
cd C:\Work\ThuyenRepo\backtestM5
.\manage_clones.ps1 Start
# Then Deploy EA M5 (compile ForgeBridgeM5E31 / M5G33) and Sync history on each desk.
```

Trade models from M15 were **not** carried over — remine on M5 data after history sync.
