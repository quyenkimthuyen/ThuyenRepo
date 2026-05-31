import type { ReviewCard, ReviewGrade } from "./types";

const DAY_MS = 24 * 60 * 60 * 1000;

export function createNewReviewCard(now = new Date()): ReviewCard {
  return {
    state: "new",
    repetitions: 0,
    intervalDays: 0,
    easeFactor: 2.5,
    dueAt: now,
    leitnerBox: 1
  };
}

export function scheduleSm2Review(card: ReviewCard, grade: ReviewGrade, now = new Date()): ReviewCard {
  const failed = grade < 3;
  const repetitions = failed ? 0 : card.repetitions + 1;
  const easeFactor = Math.max(
    1.3,
    card.easeFactor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
  );

  let intervalDays = 1;
  if (failed) {
    intervalDays = 0;
  } else if (repetitions === 1) {
    intervalDays = 1;
  } else if (repetitions === 2) {
    intervalDays = 6;
  } else {
    intervalDays = Math.round(card.intervalDays * easeFactor);
  }

  const state = failed
    ? "learning"
    : repetitions >= 5 && intervalDays >= 21
      ? "mastered"
      : "review";

  return {
    ...card,
    state,
    repetitions,
    intervalDays,
    easeFactor,
    dueAt: new Date(now.getTime() + intervalDays * DAY_MS)
  };
}
