# M15_clone2 — isolated from M15 and M15_clone1

Clone of `M15_clone1` (winning Settings + KB-protect code) with empty KB / grid / Trade Models.
Do **not** start this copy on 8911/8931 or 9111/9131.

| Surface | M15 (old) | M15_clone1 | M15_clone2 |
|---------|-----------|------------|------------|
| Train E21 | http://127.0.0.1:8911 | http://127.0.0.1:9111 | http://127.0.0.1:9311 |
| Train G23 | http://127.0.0.1:8931 | http://127.0.0.1:9131 | http://127.0.0.1:9331 |
| Chart E21 / G23 | 9975 / 9976 | 10175 / 10176 | 10375 / 10376 |
| Sim / Compare | 10086 / 10196 | 10286 / 10396 | 10486 / 10596 |
| Trade Live | 8801 | 9001 | 9201 |
| Trade bridge / sim | 9801 / 9901 | 10001 / 10101 | 10201 / 10301 |
| E21 instance / magic | LC2E21 / 20281021 | CL1E21 / 20281121 | CL2E21 / 20281221 |
| G23 instance / magic | LC2G23 / 20281041 | CL1G23 / 20281141 | CL2G23 / 20281241 |
| Trade instance / magic | LIVE2 / 20283001 | LIVECL1 / 20283101 | LIVECL2 / 20283201 |
| E21 bridge | bridge_lc2_e21 | bridge_cl1_e21 | bridge_cl2_e21 |
| G23 bridge | bridge_lc2_g23 | bridge_cl1_g23 | bridge_cl2_g23 |

Runtime is this folder only (`TRAINAPP_ROOT` = `M15_clone2/Train`).
Parquet kept. KB / grid / Trade Models / compare / Live packages wiped.

Default Settings (winning recipe):
- EUR: era `2024-h1`, weeks `[8]`, presets `eur_fill_wk5_mid`, `eur_fill_wk5`, `eur_fill_wk5_bank`, OOS `2026-h1`
- GBP: era `2025-h2`, weeks `[6]`, presets `gbp_fill_wk5_bank`, `gbp_fill_wk5_lift`, `gbp_fill_wk5`
- Desk yaml `target_trades_per_week: 5.0` (learn KB)

```bash
cd Train
./manage.sh Start          # clone2 GUI 9311 / 9331
python3 scripts/run_std_recipe.py --desks e21,g23 --wipe --keep-settings --workers 6
```
