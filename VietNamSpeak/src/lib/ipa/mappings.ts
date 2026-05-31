import type { IpaRule } from "./types";

export const IPA_RULES: IpaRule[] = [
  { ipa: "iː", vietnamese: "ii", priority: 100, category: "vowel", description: "Âm i dài" },
  { ipa: "uː", vietnamese: "uu", priority: 100, category: "vowel", description: "Âm u dài" },
  { ipa: "ɑː", vietnamese: "aa", priority: 100, category: "vowel", description: "Âm a dài" },
  { ipa: "ɔː", vietnamese: "oo", priority: 100, category: "vowel", description: "Âm o dài" },
  { ipa: "ɜː", vietnamese: "ơ", priority: 100, category: "vowel", description: "Âm ơ dài" },
  { ipa: "eɪ", vietnamese: "ây", priority: 95, category: "diphthong" },
  { ipa: "aɪ", vietnamese: "ai", priority: 95, category: "diphthong" },
  { ipa: "ɔɪ", vietnamese: "oi", priority: 95, category: "diphthong" },
  { ipa: "aʊ", vietnamese: "ao", priority: 95, category: "diphthong" },
  { ipa: "əʊ", vietnamese: "âu", priority: 95, category: "diphthong" },
  { ipa: "tʃ", vietnamese: "ch", priority: 90, category: "consonant" },
  { ipa: "dʒ", vietnamese: "j", priority: 90, category: "consonant" },
  { ipa: "ʃ", vietnamese: "sh", priority: 80, category: "consonant" },
  { ipa: "ʒ", vietnamese: "gi", priority: 80, category: "consonant" },
  { ipa: "θ", vietnamese: "th", priority: 80, category: "consonant" },
  { ipa: "ð", vietnamese: "dh", priority: 80, category: "consonant" },
  { ipa: "ŋ", vietnamese: "ng", priority: 80, category: "consonant" },
  { ipa: "æ", vietnamese: "ea", priority: 70, category: "vowel" },
  { ipa: "ɪ", vietnamese: "i", priority: 70, category: "vowel" },
  { ipa: "ʌ", vietnamese: "â", priority: 70, category: "vowel" },
  { ipa: "ə", vietnamese: "ơ", priority: 70, category: "vowel" },
  { ipa: "ɒ", vietnamese: "o", priority: 70, category: "vowel" },
  { ipa: "ʊ", vietnamese: "u", priority: 70, category: "vowel" },
  { ipa: "e", vietnamese: "e", priority: 60, category: "vowel" },
  { ipa: "b", vietnamese: "b", priority: 50, category: "consonant" },
  { ipa: "d", vietnamese: "đ", priority: 50, category: "consonant" },
  { ipa: "f", vietnamese: "f", priority: 50, category: "consonant" },
  { ipa: "ɡ", vietnamese: "g", priority: 50, category: "consonant" },
  { ipa: "g", vietnamese: "g", priority: 50, category: "consonant" },
  { ipa: "h", vietnamese: "h", priority: 50, category: "consonant" },
  { ipa: "j", vietnamese: "i", priority: 50, category: "consonant" },
  { ipa: "k", vietnamese: "k", priority: 50, category: "consonant" },
  { ipa: "l", vietnamese: "l", priority: 50, category: "consonant" },
  { ipa: "m", vietnamese: "m", priority: 50, category: "consonant" },
  { ipa: "n", vietnamese: "n", priority: 50, category: "consonant" },
  { ipa: "p", vietnamese: "p", priority: 50, category: "consonant" },
  { ipa: "r", vietnamese: "r", priority: 50, category: "consonant" },
  { ipa: "s", vietnamese: "s", priority: 50, category: "consonant" },
  { ipa: "t", vietnamese: "t", priority: 50, category: "consonant" },
  { ipa: "v", vietnamese: "v", priority: 50, category: "consonant" },
  { ipa: "w", vietnamese: "qu", priority: 50, category: "consonant" },
  { ipa: "z", vietnamese: "z", priority: 50, category: "consonant" },
  { ipa: "ˌ", vietnamese: "-", priority: 10, category: "marker" },
  { ipa: ".", vietnamese: "-", priority: 10, category: "marker" }
];

export const PRIORITIZED_IPA_RULES = [...IPA_RULES].sort((a, b) => {
  if (b.priority !== a.priority) return b.priority - a.priority;
  return b.ipa.length - a.ipa.length;
});
