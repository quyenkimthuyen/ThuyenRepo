# AIEdge vs TrainApp — Proof Report (v2)

Generated: `2026-08-17T09:14:18+07:00`

## Verdict

**Fair WF claim:** **AIEdge wins on locked protocol** (AIEdge 2 · TrainApp 0 · tie 0)

Profitable desks (AIEdge test R>0): **2/2**

## Method

AIEdge-v2: desk-aware preset search + select_score favoring absolute R under realistic spreads; soft-fallback never prefers thin (<min_trades) samples; M5 uses biweekly remine and no aggressive cost-gate. Primary baseline is TrainApp-fair WF at the same costs.

## Per desk

### E21 · EURUSD M15

- **Winner (fair WF):** AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge profitable: True | beats fair Total R: True
- AIEdge validate: R=29.71 WR=39.25 DD=12.674 n=107
- AIEdge test: R=11.801 WR=35.9 RR=1.958 DD=31.695 n=156 @ 1.6 pip
- TrainApp-fair: R=-29.763 WR=17.57 DD=34.365
- TrainApp published (cost-stressed, reference only): R=104.745 DD=3.513 | gap AI−pub=-92.944
- AIEdge pick: `wf|anti_chase_fixed_70|tw9|gateNone|s1`

### G23 · GBPUSD M15

- **Winner (fair WF):** AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge profitable: True | beats fair Total R: True
- AIEdge validate: R=32.817 WR=37.36 DD=20.786 n=174
- AIEdge test: R=77.598 WR=42.78 RR=2.164 DD=21.302 n=187 @ 2.0 pip
- TrainApp-fair: R=-9.822 WR=23.08 DD=25.137
- TrainApp published (cost-stressed, reference only): R=64.289 DD=5.291 | gap AI−pub=13.309
- AIEdge pick: `wf|edge_gentle|tw6|gateNone|s1`

## Fairness notes

- Primary baseline = TrainApp-fair (same cost WF), not published overlapping-era grids.
- AIEdge never uses TEST for selection.
- Published stressed numbers are shown only as a reference gap to the app UI.
