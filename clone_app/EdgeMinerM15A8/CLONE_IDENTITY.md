# Clone identity `A8`

| Field | Value |
|-------|-------|
| Spec | `A8` (version `A`, offset `8`) |
| Repo | `EdgeMinerM15A8` |
| INSTANCE_ID | `M15A8` |
| Bridge live / sim | `bridge_m15a8` / `bridge_sim_m15a8` |
| EA live / sim | `ForgeBridgeM15A8` / `ForgeBridgeM15A8Sim` |
| App port | `8581` (= 8501 + 8*10) |
| Bridge monitor | `8845` (= 8765 + 8*10) |
| Paper monitor | `8846` (= 8766 + 8*10) |
| Sim monitor | `8956` (= 8876 + 8*10) |
| Compare monitor | `9066` (= 8986 + 8*10) |
| Magic live / sim | `20261008` / `20262008` |

## Run

```bash
cd EdgeMinerM15A8
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/run_app_linux.sh Start
```

Offset must stay unique vs other clones (ports derive only from offset).
