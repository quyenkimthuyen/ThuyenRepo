# TrainApp — unified Train desks (shared GUI)

## Layout

```
TrainApp/
  gui/                 # ONE Streamlit GUI (desk-aware via config)
  desks/               # e21.yaml g23.yaml e31.yaml g33.yaml
  cores/
    m15/               # M15 domain: config, data_loader, mt5_bridge, learning…
    m5/                # M5 domain (same surface, TF defaults differ)
  runtime/{e21,g23,e31,g33}/   # per-desk data/results/learning/mt5
  desk_context.py
  run_desk.py
  manage.ps1
```

Old twin GUIs under `cores/*/gui` were archived to `_archive/gui_*_pre_shared`.
Legacy clones in `LiveCheck/Train/M15|M5/EdgeMiner*` are unused for day-to-day.

## Commands

```powershell
cd C:\Work\ThuyenRepo\LiveCheck\TrainApp
.\manage.ps1 Check
.\manage.ps1 Start
.\manage.ps1 Status
.\manage.ps1 Stop e21
.\manage.ps1 Restart
```

Or one desk:

```powershell
python run_desk.py e21
python run_desk.py g33 --check
```

## Ports

| Desk | URL |
|------|-----|
| E21 EURUSD M15 | http://127.0.0.1:8711 |
| G23 GBPUSD M15 | http://127.0.0.1:8731 |
| E31 EURUSD M5  | http://127.0.0.1:8811 |
| G33 GBPUSD M5  | http://127.0.0.1:8831 |

## How it works

1. `desks/*.yaml` — pair, TF, port, magic, bridge, spread, score weights.
2. `gui/` — shared UI; labels/bars/day/feature profile from `config` + `gui/desk_ui.py`.
3. `cores/m15|m5` — domain code only (no duplicate Streamlit tree).
4. `runtime/<desk>/` — state (currently junctioned to old Train folders).
5. Env: `TRAINAPP_DESK`, `TRAINAPP_RUNTIME`, `TRAINAPP_CORE`, `TRAINAPP_ROOT`.
