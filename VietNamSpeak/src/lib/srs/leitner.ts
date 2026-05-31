import type { ReviewCard } from "./types";

const BOX_INTERVALS = [0, 1, 2, 4, 7, 14, 30];
const DAY_MS = 24 * 60 * 60 * 1000;

export function scheduleLeitnerReview(card: ReviewCard, correct: boolean, now = new Date()): ReviewCard {
  const leitnerBox = correct ? Math.min(card.leitnerBox + 1, 6) : 1;
  const intervalDays = BOX_INTERVALS[leitnerBox] ?? 1;
  const state = leitnerBox >= 6 ? "mastered" : leitnerBox >= 3 ? "review" : "learning";

  return {
    ...card,
    state,
    leitnerBox,
    intervalDays,
    dueAt: new Date(now.getTime() + intervalDays * DAY_MS)
  };
}
