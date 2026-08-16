# AIEdge Cost-Aware Re-Rank Proof

Generated: `2026-08-16T19:27:14+07:00`

Same TrainApp grid rows. AIEdge ranks by spread-stressed robust_score; TrainApp baseline uses user filter WR>50 RR>2.5 R>100 DD<10 else best Total R. Both evaluated after identical cost stress.

**Claim:** **AIEdge wins cost-aware re-rank** (AIEdge 4 · TrainApp 0)

### E21

- Winner: AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge stressed: R=104.745 score=29.813 DD=3.513
- TrainApp stressed: R=114.692 score=26.797 DD=4.28

### G23

- Winner: AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge stressed: R=64.289 score=11.981 DD=5.291
- TrainApp stressed: R=96.049 score=6.031 DD=14.332

### E31

- Winner: AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge stressed: R=122.704 score=10.736 DD=11.003
- TrainApp stressed: R=247.41 score=4.486 DD=48.457

### G33

- Winner: AIEdge — higher robust_score with DD not materially worse (+2R tolerance)
- AIEdge stressed: R=27.879 score=7.121 DD=3.782
- TrainApp stressed: R=212.373 score=6.604 DD=29.223
