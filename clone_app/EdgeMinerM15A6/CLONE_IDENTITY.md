# Clone identity `A6`

| Field | Value |
|-------|-------|
| Spec | `A6` (version `A`, offset `6`) |
| Repo | `EdgeMinerM15A6` |
| INSTANCE_ID | `M15A6` |
| Bridge live / sim | `bridge_m15a6` / `bridge_sim_m15a6` |
| EA live / sim | `ForgeBridgeM15A6` / `ForgeBridgeM15A6Sim` |
| App port | `8561` (= 8501 + 6*10) |
| Bridge monitor | `8825` (= 8765 + 6*10) |
| Paper monitor | `8826` (= 8766 + 6*10) |
| Sim monitor | `8936` (= 8876 + 6*10) |
| Compare monitor | `9046` (= 8986 + 6*10) |
| Magic live / sim | `20261006` / `20262006` |

## Run

```bash
cd EdgeMinerM15A6
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/run_app_linux.sh Start
```

Offset must stay unique vs other clones (ports derive only from offset).
