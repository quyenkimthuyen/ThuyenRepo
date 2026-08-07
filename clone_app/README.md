# Cloned EdgeMinerM15 instances

Created from `EdgeMinerM15` via `scripts/clone_m15_instance.sh`.

| Spec | Folder | App | Bridge / Paper / Sim / Compare | Magic live | EA / bridge folder |
|------|--------|-----|--------------------------------|------------|--------------------|
| A6 | `EdgeMinerM15A6` | 8561 | 8825 / 8826 / 8936 / 9046 | 20261006 | `ForgeBridgeM15A6` / `bridge_m15a6` |
| A7 | `EdgeMinerM15A7` | 8571 | 8835 / 8836 / 8946 / 9056 | 20261007 | `ForgeBridgeM15A7` / `bridge_m15a7` |
| A8 | `EdgeMinerM15A8` | 8581 | 8845 / 8846 / 8956 / 9066 | 20261008 | `ForgeBridgeM15A8` / `bridge_m15a8` |

Each instance has its own ports, magic, EA name, Experts folder, and bridge directories — safe to run side-by-side with each other and with M15/B4/B5.

## Manage all 3 apps

```powershell
cd C:\Work\ThuyenRepo\clone_app
.\manage_clones.ps1 Status
.\manage_clones.ps1 Start
.\manage_clones.ps1 Stop
.\manage_clones.ps1 Restart
.\manage_clones.ps1 Start -Apps A6,A8
.\manage_clones.ps1 DeployEA
.\manage_clones.ps1 DeployEA -NoEnableTrading
.\manage_clones.ps1 DeployEA -NoAttach
.\manage_clones.ps1 DeployEA -Apps A6
.\manage_clones.ps1 DeployEA -Mode Both -Apps A7,A8
```

`DeployEA` compiles, links bridge folders, **attaches EA to charts and enables trading by default**, and starts each clone's bridge service. Use `-NoAttach` for compile/link only; `-NoEnableTrading` to attach with trading off. When deploying multiple apps it uses `-NoRestartTerminal` until the last one (one MT5 restart at the end).

Or from cmd: `manage_clones.cmd Start` / `manage_clones.cmd Restart A7` / `manage_clones.cmd DeployEA`.

## Run one app (Windows)

```powershell
cd C:\Work\ThuyenRepo\clone_app\EdgeMinerM15A6
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\scripts\run_app_windows.ps1 Start
```

Then deploy with that clone's `scripts\deploy_xm_forgebridge.ps1`.
