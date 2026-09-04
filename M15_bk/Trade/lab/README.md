# Lab side — export Trade Model packages

Lab **không** clone thêm 4 desk. Dùng luôn:

- `Final_app/EdgeMinerEURUSDM15` (M15F1)
- `Final_app/EdgeMinerGBPUSDM15` (M15F2)
- `Final_app/EdgeMinerEURUSDM5` (M5F3)
- `Final_app/EdgeMinerGBPUSDM5` (M5F4)

Việc học / Grid / unify OOS vẫn chạy trên các desk đó (`../run_final_train.sh`, `../manage_clones.sh`).

## Vai trò của `lab/`

Chỉ **export** model đã promote thành `.tmpkg` để Live import.

```bash
cd /home/thuyenng/work/ThuyenRepo/Final_app/split_app

# Liệt kê model trên 1 desk
python lab/export_trade_package.py --desk EdgeMinerEURUSDM5 --list

# Export theo label
python lab/export_trade_package.py --desk EdgeMinerEURUSDM5 --label BestQuality

# Export mọi model live (không archived)
python lab/export_trade_package.py --desk EdgeMinerEURUSDM5 --all

# Export cả 4 desk, chỉ Best*
python lab/export_trade_package.py --all-desks --best-only
```

Output mặc định: `split_app/packages_out/`.
