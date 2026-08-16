# AIEdge vs TrainApp — Proof Report

Generated: `2026-08-16T23:03:28+07:00`

## Verdict

**AIEdge wins 3–1** on the locked fair protocol (same spreads, same TEST calendar, causal weekly remine).

| Desk | Pair/TF | AIEdge test R | TrainApp-fair R | Winner |
|------|---------|---------------|-----------------|--------|
| E21 | EURUSD M15 | -1.1 | -29.8 | AIEdge |
| G23 | GBPUSD M15 | **+63.3** | -9.8 | AIEdge |
| E31 | EURUSD M5 | -8.2 | -64.7 | AIEdge |
| G33 | GBPUSD M5 | -64.0 | -22.9 | TrainApp |

Strongest absolute win: **G23** (+63R vs −10R). Re-rank methodology proof (same published grids, cost-stressed robust ranking): **AIEdge 4–0** — see `RERANK_PROOF.md`.

## Method

Both systems use the same causal weekly walk-forward miner and the same realistic desk spreads on the locked TEST window. TrainApp-fair uses the fixed recommended recipe (elite_or_quality, 6w). AIEdge selects preset×train_weeks (+ optional cost-gate) on VALIDATE only, then runs TEST once. Published TrainApp grids that mined on overlapping 2025-2026 eras are excluded as protocol-invalid.

**Claim:** **AIEdge wins on locked protocol** (AIEdge 3 · TrainApp 1 · tie 0)

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

### G33 · GBPUSD M5

- **Winner:** TrainApp — TrainApp higher total_r with DD <= candidate
- AIEdge validate (selection): R=32.792 WR=37.2 DD=41.443 score=-0.099
- AIEdge test (once): R=-63.954 WR=30.29 RR=1.843 DD=91.043 score=-1.938 n=340 @ spread 2.0 pip
- TrainApp-fair (same cost WF): R=-22.903 WR=21.33 DD=27.771 score=-2.508
- AIEdge pick: `wf|anti_chase_fixed_70|tw6|gateNone`
- TrainApp recipe: `TrainApp default elite_or_quality tw6 @ 2.0pip (no cost-gate)`

## Fairness notes

- Both sides: identical spreads, identical TEST calendar, causal weekly remine.
- AIEdge never uses TEST for selection (VALIDATE only).
- TrainApp-fair = fixed recommended preset (not the optimistic published grid).
- Published TrainApp rows trained on overlapping 2025-2026 eras are protocol-invalid.
- Caveat: under realistic spreads many M5 runs are still negative; G23 is the clearest profitable outperformance.
