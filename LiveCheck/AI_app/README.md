# AIEdge (`AI_app`) — protocol-first alternative to TrainApp

## Goal

Build a **new** train→select→test system that can be **proven better** than TrainApp under a locked evaluation protocol.

## Design (non-negotiable)

1. **Train / Validate / Test** calendar locked in `config/protocol.yaml`.
2. Hyperparams chosen **only on Validate** (never Test).
3. **Realistic spreads** (EUR 1.6 / GBP 2.0 pips) + slippage 0.3.
4. Causal weekly walk-forward miner (TrainApp-compatible genomes) + optional ATR cost-gate.
5. Fair baseline = same WF engine, fixed TrainApp recipe (`elite_or_quality`, 6w), same costs.

## Run

```powershell
cd C:\Work\ThuyenRepo\LiveCheck\AI_app
# Fair walk-forward proof (slow; merges existing desks)
python scripts\run_proof.py --desks g23,e31,g33

# Instant selection-methodology proof on published grids
python scripts\run_rerank_proof.py
```

Outputs:
- `results/model_<desk>.json`
- `results/proof_report.json` / `results/PROOF.md`
- `results/rerank_proof.json` / `results/RERANK_PROOF.md`
