# M15_clone1 — isolated from M15

Clone of `M15` for a clean retrain. Do **not** start this copy on 8911/8931.

| Surface | M15 (old) | M15_clone1 |
|---------|-----------|------------|
| Train E21 | http://127.0.0.1:8911 | http://127.0.0.1:9111 |
| Train G23 | http://127.0.0.1:8931 | http://127.0.0.1:9131 |
| Chart E21 / G23 | 9975 / 9976 | 10175 / 10176 |
| Sim / Compare | 10086 / 10196 | 10286 / 10396 |
| Trade Live | 8801 | 9001 |
| E21 instance / magic | LC2E21 / 20281021 | CL1E21 / 20281121 |
| G23 instance / magic | LC2G23 / 20281041 | CL1G23 / 20281141 |
| E21 bridge | bridge_lc2_e21 | bridge_cl1_e21 |
| G23 bridge | bridge_lc2_g23 | bridge_cl1_g23 |

Runtime is this folder only (`TRAINAPP_ROOT` = `M15_clone1/Train`).
Parquet kept. KB / grid / Train trade models / compare wiped, then std recipe from scratch.

```bash
cd Train
./manage.sh Start          # clone GUI 9111 / 9131
python3 scripts/run_std_recipe.py --desks e21,g23 --wipe --keep-settings --workers 6
```
