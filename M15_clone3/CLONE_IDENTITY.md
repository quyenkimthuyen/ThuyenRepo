# M15_clone3 — isolated from M15, M15_clone1, M15_clone2

Clone of `M15_clone2` with unique Train / Trade ports. Do **not** start this copy
on 8911/8931, 9111/9131, 9311/9331, or Trade 8801/9001/9201.

| Surface | M15 | clone1 | clone2 | **clone3** |
|---------|-----|--------|--------|------------|
| Train E21 | :8911 | :9111 | :9311 | **:9511** |
| Train G23 | :8931 | :9131 | :9331 | **:9531** |
| Chart E21 / G23 | 9975 / 9976 | 10175 / 10176 | 10375 / 10376 | **10575 / 10576** |
| Sim / Compare | 10086 / 10196 | 10286 / 10396 | 10486 / 10596 | **10686 / 10796** |
| Trade Live | 8801 | 9001 | 9201 | **9401** |
| Trade bridge / sim | 9801 / 9901 | 10001 / 10101 | 10201 / 10301 | **10401 / 10501** |
| E21 instance / magic | LC2E21 / 20281021 | CL1E21 / 20281121 | CL2E21 / 20281221 | **CL3E21 / 20281321** |
| G23 instance / magic | LC2G23 / 20281041 | CL1G23 / 20281141 | CL2G23 / 20281241 | **CL3G23 / 20281341** |
| Trade instance / magic | LIVE2 / 20283001 | LIVECL1 / 20283101 | LIVECL2 / 20283201 | **LIVECL3 / 20283301** |
| E21 bridge | bridge_lc2_e21 | bridge_cl1_e21 | bridge_cl2_e21 | **bridge_cl3_e21** |
| G23 bridge | bridge_lc2_g23 | bridge_cl1_g23 | bridge_cl2_g23 | **bridge_cl3_g23** |

Runtime is this folder only (`TRAINAPP_ROOT` = `M15_clone3/Train`).

```bash
cd Train
./manage.sh Start          # clone3 GUI 9511 / 9531
cd ../Trade/live
./scripts/run_app_linux.sh Start   # port 9401
```
