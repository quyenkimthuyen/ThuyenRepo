import { describe, expect, it } from "vitest";

import { scheduleLeitnerReview } from "./leitner";
import { createNewReviewCard, scheduleSm2Review } from "./sm2";

describe("spaced repetition", () => {
  it("moves successful cards into review with SM-2", () => {
    const now = new Date("2026-01-01T00:00:00.000Z");
    const card = createNewReviewCard(now);
    const next = scheduleSm2Review(card, 5, now);

    expect(next.state).toBe("review");
    expect(next.repetitions).toBe(1);
    expect(next.intervalDays).toBe(1);
  });

  it("resets failed cards to learning with Leitner", () => {
    const card = { ...createNewReviewCard(), leitnerBox: 4, state: "review" as const };
    const next = scheduleLeitnerReview(card, false);

    expect(next.leitnerBox).toBe(1);
    expect(next.state).toBe("learning");
  });
});
