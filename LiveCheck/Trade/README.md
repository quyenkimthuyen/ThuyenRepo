# split_app — Lab (export) + Live (import & trade)

Tách theo thảo luận GUIDE / Live package:

| Phần | Path | Vai trò |
|------|------|---------|
| **Lab** | `lab/` | Học & tối ưu vẫn ở 4 desk `Final_app/EdgeMiner*` · tool **export** Trade Model → package |
| **Live** | `live/` | App chạy lệnh: **import** package, roster, remine tuần, 1 EA chung |
| **Shared** | `shared/` | Schema package `.tmpkg` (zip) |
| **MT5** | `mt5/` | `ForgeBridgeLive` / `ForgeBridgeLiveSim` — EA dùng chung mọi model |

```text
Final_app/EdgeMiner*  ──export──►  packages_out/*.tmpkg  ──import──►  live/installed_models/
     (KB/Grid/OOS)                                                      │
                                                                        ▼
                                                              ForgeBridgeLive.mq5
                                                              (1 EA, multi-magic roster)
```

## Remine hàng tuần

**Không** cần export/import package mỗi tuần.  
Package mang recipe (search space + KB pin). Live remine trên data broker + pin local.

Chỉ export package mới khi lab promote model / đổi KB / đổi space.

## Live runtime (đã wire)

1. `materialize_models` → `live/results/trade_models.json` + kb_pin  
2. Host code = Final_app desk khớp symbol/TF  
3. `mt5_bridge_service_live.py` → BridgeEngine quyết định / remine  
4. `chart_validate` trước Start; flatten + kill-switch trong UI  
5. Windows: `deploy_live_ea.ps1` (ForgeBridgeLive, magic 20263001)

```bash
# Smoke
../../EdgeMinerM15B5/.venv/bin/python live/scripts/smoke_live.py
```

## Quick start

```bash
# 1) Export từ lab desk (sau khi có Trade Model)
cd /home/thuyenng/work/ThuyenRepo/Final_app/split_app
../../EdgeMinerM15B5/.venv/bin/python lab/export_trade_package.py \
  --desk EdgeMinerEURUSDM5 --model-id <tm_...> 

# hoặc --label BestQuality --all-best

# 2) Import vào Live
python live/import_trade_package.py packages_out/xxx.tmpkg

# 3) Chạy Live UI
./live/scripts/run_app_linux.sh Start   # port 8601
```

Windows DeployEA: `live/scripts/deploy_live_ea.ps1` (Attach + EnableTrading mặc định).

Xem thêm: `PACKAGE_SPEC.md`, `lab/README.md`, `live/README.md`.
