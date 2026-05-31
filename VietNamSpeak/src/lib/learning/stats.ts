import { WORDS } from "@/data/words";

export const demoStats = {
  streak: 7,
  xp: 1280,
  level: 6,
  accuracy: 87,
  reviewsDue: 12,
  wordsLearned: WORDS.length
};

export function xpForCorrectAnswer(level: number) {
  return 10 + Math.max(level - 1, 0) * 2;
}
