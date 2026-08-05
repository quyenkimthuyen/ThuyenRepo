# Clone identity `B5`

| Field | Value |
|-------|-------|
| Spec | `B5` (version `B`, offset `5`) |
| Repo | `EdgeMinerM15B5` |
| INSTANCE_ID | `M15B5` |
| Bridge live / sim | `bridge_m15b5` / `bridge_sim_m15b5` |
| EA live / sim | `ForgeBridgeM15B5` / `ForgeBridgeM15B5Sim` |
| App port | `8551` (= 8501 + 5*10) |
| Bridge monitor | `8815` (= 8765 + 5*10) |
| Paper monitor | `8816` (= 8766 + 5*10) |
| Sim monitor | `8926` (= 8876 + 5*10) |
| Compare monitor | `9036` (= 8986 + 5*10) |
| Magic live / sim | `20261005` / `20262005` |

## Run

```bash
cd EdgeMinerM15B5
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/run_app_linux.sh Start
```

Offset must stay unique vs other clones (ports derive only from offset).
