# Clone identity `B4`

| Field | Value |
|-------|-------|
| Spec | `B4` (version `B`, offset `4`) |
| Repo | `EdgeMinerM15B4` |
| INSTANCE_ID | `M15B4` |
| Bridge live / sim | `bridge_m15b4` / `bridge_sim_m15b4` |
| EA live / sim | `ForgeBridgeM15B4` / `ForgeBridgeM15B4Sim` |
| App port | `8541` (= 8501 + 4*10) |
| Bridge monitor | `8805` (= 8765 + 4*10) |
| Paper monitor | `8806` (= 8766 + 4*10) |
| Sim monitor | `8916` (= 8876 + 4*10) |
| Compare monitor | `9026` (= 8986 + 4*10) |
| Magic live / sim | `20261004` / `20262004` |

## Run

```bash
cd EdgeMinerM15B4
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/run_app_linux.sh Start
```

Offset must stay unique vs other clones (ports derive only from offset).
