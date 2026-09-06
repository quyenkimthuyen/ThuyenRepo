# TrainApp — unified Train desks (shared GUI)

## Layout

```
TrainApp/
  gui/                 # ONE Streamlit GUI (desk-aware via config)
  desks/               # e21.yaml g23.yaml (M15 only)
  cores/
    m15/               # M15 domain: config, data_loader, mt5_bridge, learning…
  runtime/{e21,g23}/   # per-desk data/results/learning/mt5
  desk_context.py
  run_desk.py
  manage.ps1
```

Old twin GUIs under `cores/*/gui` were archived to `_archive/gui_*_pre_shared`.
Legacy clones in `LiveCheck/Train/M15|M5/EdgeMiner*` are unused for day-to-day.

## Commands

```powershell
cd <path-to>\TrainApp2
.\manage.ps1 Check
.\manage.ps1 Start
.\manage.ps1 Status
.\manage.ps1 Stop e21
.\manage.ps1 Restart
```

Or one desk:

```powershell
python run_desk.py e21
python run_desk.py g23 --check
```

## Ports

LiveCheck2 isolation vs `LiveCheck\TrainApp2` (8711/8731, magic `20261xxx`):

| Desk | URL |
|------|-----|
| E21 EURUSD M15 | http://127.0.0.1:8911 |
| G23 GBPUSD M15 | http://127.0.0.1:8931 |

## How it works

1. `desks/*.yaml` — pair, TF, port, magic, bridge, spread, score weights.
2. `gui/` — shared UI; labels/bars/day/feature profile from `config` + `gui/desk_ui.py`.
3. `cores/m15` — domain code only (no duplicate Streamlit tree).
4. `runtime/<desk>/` — per-desk state (self-contained; copy the whole TrainApp2 folder).
5. Env: `TRAINAPP_DESK`, `TRAINAPP_RUNTIME`, `TRAINAPP_CORE`, `TRAINAPP_ROOT` (always bound to this copy).

Copy/move: copy the entire `TrainApp2` directory. Do not rely on `C:\Work\...` paths. Then:

```powershell
cd <new>\TrainApp2
.\manage.ps1 Check
.\manage.ps1 Start
```

Stale `bridge_dir` values in runtime JSON are remapped on desk start.
