export type IpaSound = {
  id: string;
  symbol: string;
  vietnameseHint: string;
  level: "beginner" | "elementary" | "intermediate" | "advanced";
  examples: Array<{ word: string; hint: string }>;
};

export const IPA_SOUNDS: IpaSound[] = [
  {
    id: "i-long",
    symbol: "/iː/",
    vietnameseHint: "ii kéo dài",
    level: "beginner",
    examples: [
      { word: "see", hint: "sii" },
      { word: "green", hint: "griin" },
      { word: "eat", hint: "iit" }
    ]
  },
  {
    id: "i-short",
    symbol: "/ɪ/",
    vietnameseHint: "i ngắn, bật nhanh",
    level: "beginner",
    examples: [
      { word: "sit", hint: "sit" },
      { word: "fish", hint: "fish" },
      { word: "enough", hint: "i-nâf" }
    ]
  },
  {
    id: "ae",
    symbol: "/æ/",
    vietnameseHint: "ea mở miệng rộng",
    level: "beginner",
    examples: [
      { word: "cat", hint: "keat" },
      { word: "language", hint: "leang-quịch" }
    ]
  },
  {
    id: "u-long",
    symbol: "/uː/",
    vietnameseHint: "uu kéo dài",
    level: "elementary",
    examples: [
      { word: "school", hint: "skuul" },
      { word: "blue", hint: "bluu" }
    ]
  },
  {
    id: "schwa",
    symbol: "/ə/",
    vietnameseHint: "ơ nhẹ, không nhấn",
    level: "elementary",
    examples: [
      { word: "beautiful", hint: "biu-tờ-phồ" },
      { word: "station", hint: "stây-shần" }
    ]
  },
  {
    id: "sh",
    symbol: "/ʃ/",
    vietnameseHint: "sh như suỵt",
    level: "intermediate",
    examples: [
      { word: "she", hint: "shii" },
      { word: "station", hint: "stây-shần" }
    ]
  }
];
