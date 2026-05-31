export type ReviewState = "new" | "learning" | "review" | "mastered";

export type ReviewCard = {
  state: ReviewState;
  repetitions: number;
  intervalDays: number;
  easeFactor: number;
  dueAt: Date;
  leitnerBox: number;
};

export type ReviewGrade = 0 | 1 | 2 | 3 | 4 | 5;
