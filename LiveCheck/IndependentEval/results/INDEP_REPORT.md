# IndependentEval Report

Generated: `2026-08-17T13:54:05+05:30`

Protocol: see `PROTOCOL.md` (locked before run).

**Primary regime:** `realistic`

## Verdict (measured)

- Desk wins: AIEdge **0** · TrainApp-quality **0** · tie **4** · inconclusive **0**
- Profitable desks (TEST R>0): AIEdge **2** · TrainApp-quality **2**
- Claim: **No decisive winner under IndependentEval-v1**

## Per desk

### E21 · EURUSD M15 @ 1.6pip (realistic)

- Winner: **tie** — |ΔR|<5 and |ΔDD|<5
- AIEdge pick `anti_chase_fixed_70|tw6|gateNone` soft=True → TEST R=3.231 WR=33.74 DD=34.499 n=163
- TrainApp-quality pick `anti_chase_fixed_70|tw6|gateNone` soft=True → TEST R=3.231 WR=33.74 DD=34.499 n=163

### G23 · GBPUSD M15 @ 2.0pip (realistic)

- Winner: **tie** — |ΔR|<5 and |ΔDD|<5
- AIEdge pick `anti_chase_fixed_70|tw6|gateNone` soft=True → TEST R=61.089 WR=41.82 DD=17.658 n=165
- TrainApp-quality pick `anti_chase_fixed_70|tw6|gateNone` soft=True → TEST R=61.089 WR=41.82 DD=17.658 n=165

### E31 · EURUSD M5 @ 1.6pip (realistic)

- Winner: **tie** — |ΔR|<5 and |ΔDD|<5
- AIEdge pick `anti_chase_fixed_70|tw6|gateNone` soft=True → TEST R=-32.497 WR=33.6 DD=58.281 n=247
- TrainApp-quality pick `anti_chase_fixed_70|tw6|gateNone` soft=True → TEST R=-32.497 WR=33.6 DD=58.281 n=247

### G33 · GBPUSD M5 @ 2.0pip (realistic)

- Winner: **tie** — |ΔR|<5 and |ΔDD|<5
- AIEdge pick `anti_chase_fixed_70|tw6|gateNone` soft=True → TEST R=-10.899 WR=34.12 DD=49.887 n=211
- TrainApp-quality pick `anti_chase_fixed_70|tw6|gateNone` soft=False → TEST R=-10.899 WR=34.12 DD=49.887 n=211

## Caveats

- Mining is stochastic; single seed/run — not a multi-seed distribution.
- Compares **selection policies** on a shared WF search space, not full TrainApp GUI promote stack.
- Does not evaluate TrainApp models that were ranked on the TEST window itself.
