# TrainApp — unified Train desks (replaces cloning EdgeMiner* folders)

## Layout

```
TrainApp/
  desks/           # e21.yaml g23.yaml e31.yaml g33.yaml
  cores/
    m15/           # shared M15 code
    m5/            # shared M5 code
  runtime/
    e21|g23|e31|g33/   # per-desk data/results/learning/mt5 (junctions → old Train)
  desk_context.py
  run_desk.py
  manage.ps1
```

Old `LiveCheck/Train/M15|M5/EdgeMiner*` apps are left untouched and are no longer required for day-to-day use.

## Commands

```powershell
cd C:\Work\ThuyenRepo\LiveCheck\TrainApp
.\manage.ps1 Check
.\manage.ps1 Start
.\manage.ps1 Status
.\manage.ps1 Stop e21
.\manage.ps1 Restart g23,e31
```

Or one desk:

```powershell
python run_desk.py e21
python run_desk.py g33 --check
```

## Ports (unchanged)

| Desk | URL |
|------|-----|
| E21 EURUSD M15 | http://127.0.0.1:8711 |
| G23 GBPUSD M15 | http://127.0.0.1:8731 |
| E31 EURUSD M5  | http://127.0.0.1:8811 |
| G33 GBPUSD M5  | http://127.0.0.1:8831 |

## How it works

1. `desks/*.yaml` holds pair, TF, port, magic, bridge folder, spread, score weights.
2. `cores/m15` or `cores/m5` is the code (one copy per timeframe).
3. `runtime/<desk>/` holds state; currently junctioned to the old desk folders so models/OHLC/bridges stay available.
4. `TRAINAPP_DESK` + `TRAINAPP_RUNTIME` make `config.py` / `protocol.py` / history cache paths desk-aware.

## Next hardening (optional)

- Copy runtime data out of junctions into real folders, then archive old Train clones.
- Push more EUR/GBP hardcodes behind `desk_context` (deploy scripts, glossary).
- Single `cores/shared` for files identical across M15/M5.
