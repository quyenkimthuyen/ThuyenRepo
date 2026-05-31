export type PronunciationRule = {
  id: string;
  pattern: string;
  ipa: string;
  vietnameseHint: string;
  explanation: string;
  examples: string[];
};

export const PRONUNCIATION_RULES: PronunciationRule[] = [
  {
    id: "tion",
    pattern: "tion",
    ipa: "/ʃən/",
    vietnameseHint: "shần",
    explanation: "Thường đứng cuối danh từ và phát âm là /ʃən/, không đọc từng chữ t-i-o-n.",
    examples: ["nation", "station", "education"]
  },
  {
    id: "sh",
    pattern: "sh",
    ipa: "/ʃ/",
    vietnameseHint: "sh",
    explanation: "Đẩy hơi nhẹ qua răng, giống âm suỵt.",
    examples: ["she", "fish", "shop"]
  },
  {
    id: "ch",
    pattern: "ch",
    ipa: "/tʃ/",
    vietnameseHint: "ch",
    explanation: "Âm bật nhanh, gần với ch nhưng cần rõ hơi cuối.",
    examples: ["chair", "teacher", "children"]
  },
  {
    id: "ph",
    pattern: "ph",
    ipa: "/f/",
    vietnameseHint: "ph/f",
    explanation: "Trong nhiều từ gốc Hy Lạp, ph đọc như /f/.",
    examples: ["phone", "photo", "physics"]
  },
  {
    id: "th-voiceless",
    pattern: "th",
    ipa: "/θ/",
    vietnameseHint: "th",
    explanation: "Đặt đầu lưỡi giữa răng, thổi nhẹ. Không đọc thành t hoặc s.",
    examples: ["think", "thank", "three"]
  },
  {
    id: "ng",
    pattern: "ng",
    ipa: "/ŋ/",
    vietnameseHint: "ng",
    explanation: "Âm ng ở cuối hoặc giữa từ, không thêm gờ nếu từ kết thúc bằng /ŋ/.",
    examples: ["sing", "English", "language"]
  },
  {
    id: "magic-e",
    pattern: "magic e",
    ipa: "/eɪ iː aɪ əʊ juː/",
    vietnameseHint: "nguyên âm dài",
    explanation: "Chữ e câm cuối từ thường làm nguyên âm trước đó đọc theo tên chữ cái.",
    examples: ["make", "bike", "home"]
  },
  {
    id: "silent-letters",
    pattern: "silent letters",
    ipa: "varies",
    vietnameseHint: "không đọc chữ câm",
    explanation: "Một số chữ xuất hiện trong chính tả nhưng không có âm IPA tương ứng.",
    examples: ["knife", "listen", "school"]
  }
];
