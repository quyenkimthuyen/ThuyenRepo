# Clone identity `A7`

| Field | Value |
|-------|-------|
| Spec | `A7` (version `A`, offset `7`) |
| Repo | `EdgeMinerM15A7` |
| INSTANCE_ID | `M15A7` |
| Bridge live / sim | `bridge_m15a7` / `bridge_sim_m15a7` |
| EA live / sim | `ForgeBridgeM15A7` / `ForgeBridgeM15A7Sim` |
| App port | `8571` (= 8501 + 7*10) |
| Bridge monitor | `8835` (= 8765 + 7*10) |
| Paper monitor | `8836` (= 8766 + 7*10) |
| Sim monitor | `8946` (= 8876 + 7*10) |
| Compare monitor | `9056` (= 8986 + 7*10) |
| Magic live / sim | `20261007` / `20262007` |

## Run

```bash
cd EdgeMinerM15A7
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/run_app_linux.sh Start
```

Offset must stay unique vs other clones (ports derive only from offset).
