# AIEdge vs TrainApp — Proof Report

Generated: `2026-08-16T21:12:50+07:00`

## Method

Both systems use the same causal weekly walk-forward miner and the same realistic desk spreads on the locked TEST window. TrainApp-fair uses the fixed recommended recipe (elite_or_quality, 6w). AIEdge selects preset×train_weeks (+ optional cost-gate) on VALIDATE only, then runs TEST once. Published TrainApp grids that mined on overlapping 2025-2026 eras are excluded as protocol-invalid.

**Claim:** **AIEdge wins on locked protocol** (AIEdge 3 · TrainApp 0 · tie 0)

## Per desk

### E21 · EURUSD M15

- **Winner:** AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge validate (selection): R=-21.3 WR=28.17 DD=35.65 score=-1.939
- AIEdge test (once): R=-1.054 WR=31.68 RR=2.14 DD=33.099 score=-1.198 n=161 @ spread 1.6 pip
- TrainApp-fair (same cost WF): R=-29.763 WR=17.57 DD=34.365 score=-2.738
- AIEdge pick: `wf|anti_chase_fixed_70|tw6`
- TrainApp recipe: `TrainApp default elite_or_quality tw6 @ 1.6pip`

### G23 · GBPUSD M15

- **Winner:** AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge validate (selection): R=4.37 WR=32.84 DD=35.157 score=-0.984
- AIEdge test (once): R=63.307 WR=41.32 RR=2.199 DD=17.658 score=2.901 n=167 @ spread 2.0 pip
- TrainApp-fair (same cost WF): R=-9.822 WR=23.08 DD=25.137 score=-1.987
- AIEdge pick: `wf|anti_chase_fixed_70|tw6|gateNone`
- TrainApp recipe: `TrainApp default elite_or_quality tw6 @ 2.0pip (no cost-gate)`

### E31 · EURUSD M5

- **Winner:** AIEdge — higher total_r with DD <= baseline
- AIEdge validate (selection): R=4.512 WR=50.0 DD=2.354 score=1.667
- AIEdge test (once): R=-8.158 WR=0.0 RR=0.0 DD=6.979 score=-3.919 n=7 @ spread 1.6 pip
- TrainApp-fair (same cost WF): R=-64.733 WR=18.18 DD=78.893 score=-2.661
- AIEdge pick: `wf|elite_or_quality|tw6|gate3.5`
- TrainApp recipe: `TrainApp default elite_or_quality tw6 @ 1.6pip (no cost-gate)`

## Fairness notes

- Both sides: identical spreads, identical TEST calendar, causal weekly remine.
- AIEdge never uses TEST for selection (VALIDATE only).
- TrainApp-fair = fixed recommended preset (not the optimistic published grid).
- Published TrainApp rows trained on overlapping 2025-2026 eras are protocol-invalid.
