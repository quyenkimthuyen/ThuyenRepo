export type WordLevel = "beginner" | "elementary" | "intermediate" | "advanced";

export type Word = {
  id: string;
  word: string;
  ipa: string;
  vnPronunciation: string;
  meaningVi: string;
  exampleEn: string;
  exampleVi: string;
  audioUrl?: string;
  topic: string;
  level: WordLevel;
};

export const WORDS: Word[] = [
  {
    id: "school",
    word: "school",
    ipa: "/skuːl/",
    vnPronunciation: "skuul",
    meaningVi: "trường học",
    exampleEn: "I go to school every day.",
    exampleVi: "Tôi đi học mỗi ngày.",
    topic: "school",
    level: "beginner"
  },
  {
    id: "beautiful",
    word: "beautiful",
    ipa: "/ˈbjuːtəfəl/",
    vnPronunciation: "biu-tờ-phồ",
    meaningVi: "đẹp",
    exampleEn: "The garden is beautiful.",
    exampleVi: "Khu vườn rất đẹp.",
    topic: "daily",
    level: "elementary"
  },
  {
    id: "language",
    word: "language",
    ipa: "/ˈlæŋɡwɪdʒ/",
    vnPronunciation: "leang-quịch",
    meaningVi: "ngôn ngữ",
    exampleEn: "English is a useful language.",
    exampleVi: "Tiếng Anh là một ngôn ngữ hữu ích.",
    topic: "learning",
    level: "intermediate"
  },
  {
    id: "enough",
    word: "enough",
    ipa: "/ɪˈnʌf/",
    vnPronunciation: "i-nâf",
    meaningVi: "đủ",
    exampleEn: "We have enough time.",
    exampleVi: "Chúng ta có đủ thời gian.",
    topic: "daily",
    level: "elementary"
  },
  {
    id: "green",
    word: "green",
    ipa: "/ɡriːn/",
    vnPronunciation: "griin",
    meaningVi: "màu xanh lá",
    exampleEn: "The leaf is green.",
    exampleVi: "Chiếc lá màu xanh.",
    topic: "colors",
    level: "beginner"
  },
  {
    id: "station",
    word: "station",
    ipa: "/ˈsteɪʃən/",
    vnPronunciation: "stây-shần",
    meaningVi: "nhà ga",
    exampleEn: "The train stops at the station.",
    exampleVi: "Tàu dừng ở nhà ga.",
    topic: "travel",
    level: "intermediate"
  }
];

export function getWordById(id: string) {
  return WORDS.find((word) => word.id === id);
}
