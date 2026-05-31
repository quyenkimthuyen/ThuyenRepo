export type IpaSound = {
  id: string;
  symbol: string;
  vietnameseHint: string;
  group: "short-vowel" | "long-vowel" | "diphthong" | "consonant" | "hard-for-vietnamese";
  groupLabel: string;
  level: "beginner" | "elementary" | "intermediate" | "advanced";
  mouthTip: string;
  avoid: string;
  examples: Array<{ word: string; hint: string }>;
};

export const IPA_SOUNDS: IpaSound[] = [
  {
    id: "i-long",
    symbol: "/iː/",
    vietnameseHint: "ii kéo dài",
    group: "long-vowel",
    groupLabel: "Nguyên âm dài",
    level: "beginner",
    mouthTip: "Cười nhẹ, kéo dài âm ii.",
    avoid: "Đừng đọc ngắn như /ɪ/ trong sit.",
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
    group: "short-vowel",
    groupLabel: "Nguyên âm ngắn",
    level: "beginner",
    mouthTip: "Miệng thả lỏng, âm i rất ngắn.",
    avoid: "Đừng kéo dài thành ii.",
    examples: [
      { word: "sit", hint: "sit" },
      { word: "fish", hint: "fish" },
      { word: "enough", hint: "i-nâf" }
    ]
  },
  {
    id: "e-short",
    symbol: "/e/",
    vietnameseHint: "e ngắn",
    group: "short-vowel",
    groupLabel: "Nguyên âm ngắn",
    level: "beginner",
    mouthTip: "Gần âm e tiếng Việt nhưng ngắn và gọn.",
    avoid: "Đừng đọc thành ê dài.",
    examples: [
      { word: "pen", hint: "pen" },
      { word: "red", hint: "red" },
      { word: "friend", hint: "frend" }
    ]
  },
  {
    id: "ae",
    symbol: "/æ/",
    vietnameseHint: "ea mở miệng rộng",
    group: "short-vowel",
    groupLabel: "Nguyên âm ngắn",
    level: "beginner",
    mouthTip: "Mở miệng rộng hơn âm e, giống a pha e.",
    avoid: "Đừng đọc thành a Việt Nam.",
    examples: [
      { word: "cat", hint: "keat" },
      { word: "apple", hint: "ea-pồ" },
      { word: "language", hint: "leang-quịch" }
    ]
  },
  {
    id: "a-short",
    symbol: "/ʌ/",
    vietnameseHint: "â ngắn",
    group: "short-vowel",
    groupLabel: "Nguyên âm ngắn",
    level: "beginner",
    mouthTip: "Âm â ngắn, cổ họng mở nhẹ.",
    avoid: "Đừng đọc thành a hoặc u.",
    examples: [
      { word: "run", hint: "rân" },
      { word: "sun", hint: "sân" },
      { word: "enough", hint: "i-nâf" }
    ]
  },
  {
    id: "o-short",
    symbol: "/ɒ/",
    vietnameseHint: "o ngắn",
    group: "short-vowel",
    groupLabel: "Nguyên âm ngắn",
    level: "elementary",
    mouthTip: "Môi hơi tròn, âm o ngắn.",
    avoid: "Đừng đọc thành ô dài.",
    examples: [
      { word: "dog", hint: "đog" },
      { word: "hot", hint: "hot" },
      { word: "want", hint: "quont" }
    ]
  },
  {
    id: "u-short",
    symbol: "/ʊ/",
    vietnameseHint: "u ngắn",
    group: "short-vowel",
    groupLabel: "Nguyên âm ngắn",
    level: "beginner",
    mouthTip: "Tròn môi nhẹ, không kéo dài.",
    avoid: "Đừng đọc dài như /uː/.",
    examples: [
      { word: "book", hint: "buk" },
      { word: "good", hint: "gud" },
      { word: "look", hint: "luk" }
    ]
  },
  {
    id: "u-long",
    symbol: "/uː/",
    vietnameseHint: "uu kéo dài",
    group: "long-vowel",
    groupLabel: "Nguyên âm dài",
    level: "elementary",
    mouthTip: "Tròn môi và kéo dài uu.",
    avoid: "Đừng đọc ngắn như book.",
    examples: [
      { word: "school", hint: "skuul" },
      { word: "blue", hint: "bluu" },
      { word: "movie", hint: "muu-vi" }
    ]
  },
  {
    id: "aa-long",
    symbol: "/ɑː/",
    vietnameseHint: "aa mở dài",
    group: "long-vowel",
    groupLabel: "Nguyên âm dài",
    level: "elementary",
    mouthTip: "Mở miệng rộng, kéo dài aa.",
    avoid: "Đừng đọc ngắn thành a.",
    examples: [
      { word: "father", hint: "faa-dhờ" },
      { word: "car", hint: "kaa" },
      { word: "start", hint: "staat" }
    ]
  },
  {
    id: "or-long",
    symbol: "/ɔː/",
    vietnameseHint: "oo/o dài",
    group: "long-vowel",
    groupLabel: "Nguyên âm dài",
    level: "elementary",
    mouthTip: "Môi tròn, kéo dài âm o.",
    avoid: "Đừng đọc thành o ngắn.",
    examples: [
      { word: "water", hint: "quoo-tờ" },
      { word: "morning", hint: "moo-rning" },
      { word: "walk", hint: "quook" }
    ]
  },
  {
    id: "er-long",
    symbol: "/ɜː/",
    vietnameseHint: "ơ dài",
    group: "long-vowel",
    groupLabel: "Nguyên âm dài",
    level: "intermediate",
    mouthTip: "Âm ơ kéo dài, lưỡi ở giữa miệng.",
    avoid: "Đừng đọc thành e hoặc â.",
    examples: [
      { word: "bird", hint: "bơd" },
      { word: "girl", hint: "gơl" },
      { word: "learn", hint: "lơn" }
    ]
  },
  {
    id: "schwa",
    symbol: "/ə/",
    vietnameseHint: "ơ nhẹ, không nhấn",
    group: "short-vowel",
    groupLabel: "Nguyên âm yếu",
    level: "elementary",
    mouthTip: "Âm rất nhẹ, thường ở âm tiết không nhấn.",
    avoid: "Đừng đọc quá rõ hoặc quá dài.",
    examples: [
      { word: "beautiful", hint: "biu-tờ-phồ" },
      { word: "station", hint: "stây-shần" },
      { word: "computer", hint: "kờm-piu-tờ" }
    ]
  },
  {
    id: "ei",
    symbol: "/eɪ/",
    vietnameseHint: "ây",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "beginner",
    mouthTip: "Bắt đầu như e rồi trượt sang i.",
    avoid: "Đừng đọc thành a theo mặt chữ.",
    examples: [
      { word: "day", hint: "đây" },
      { word: "name", hint: "nâym" },
      { word: "station", hint: "stây-shần" }
    ]
  },
  {
    id: "ai",
    symbol: "/aɪ/",
    vietnameseHint: "ai",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "beginner",
    mouthTip: "Bắt đầu a rồi trượt sang i.",
    avoid: "Đừng đọc chữ i thành i ngắn.",
    examples: [
      { word: "rice", hint: "rais" },
      { word: "night", hint: "nait" },
      { word: "life", hint: "laif" }
    ]
  },
  {
    id: "oi",
    symbol: "/ɔɪ/",
    vietnameseHint: "oi",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "elementary",
    mouthTip: "Từ o tròn môi trượt sang i.",
    avoid: "Đừng tách thành hai âm rời quá lâu.",
    examples: [
      { word: "boy", hint: "boi" },
      { word: "toy", hint: "toi" },
      { word: "voice", hint: "vois" }
    ]
  },
  {
    id: "au",
    symbol: "/aʊ/",
    vietnameseHint: "ao",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "elementary",
    mouthTip: "Bắt đầu a rồi khép môi sang u.",
    avoid: "Đừng đọc thành âu nếu IPA là /aʊ/.",
    examples: [
      { word: "now", hint: "nao" },
      { word: "house", hint: "haos" },
      { word: "mouth", hint: "maoth" }
    ]
  },
  {
    id: "ou",
    symbol: "/əʊ/",
    vietnameseHint: "âu",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "beginner",
    mouthTip: "Bắt đầu ơ nhẹ rồi trượt sang u.",
    avoid: "Đừng đọc thành o đơn.",
    examples: [
      { word: "hello", hint: "hờ-lâu" },
      { word: "home", hint: "hâum" },
      { word: "phone", hint: "fâun" }
    ]
  },
  {
    id: "ear",
    symbol: "/ɪə/",
    vietnameseHint: "ia/ia-ơ",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "intermediate",
    mouthTip: "Từ i ngắn trượt nhẹ sang ơ.",
    avoid: "Đừng đọc thành ia tiếng Việt quá rõ.",
    examples: [
      { word: "near", hint: "nia" },
      { word: "here", hint: "hia" },
      { word: "idea", hint: "ai-đia" }
    ]
  },
  {
    id: "air",
    symbol: "/eə/",
    vietnameseHint: "e-ờ",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "intermediate",
    mouthTip: "Bắt đầu e rồi hạ nhẹ về ơ.",
    avoid: "Đừng đọc r quá nặng nếu giọng Anh.",
    examples: [
      { word: "chair", hint: "che-ờ" },
      { word: "hair", hint: "he-ờ" },
      { word: "care", hint: "ke-ờ" }
    ]
  },
  {
    id: "ure",
    symbol: "/ʊə/",
    vietnameseHint: "u-ờ",
    group: "diphthong",
    groupLabel: "Nguyên âm đôi",
    level: "advanced",
    mouthTip: "Từ u ngắn trượt nhẹ sang ơ.",
    avoid: "Đừng kéo dài thành uu.",
    examples: [
      { word: "tour", hint: "tu-ờ" },
      { word: "sure", hint: "shu-ờ" },
      { word: "poor", hint: "pu-ờ" }
    ]
  },
  {
    id: "sh",
    symbol: "/ʃ/",
    vietnameseHint: "sh như suỵt",
    group: "hard-for-vietnamese",
    groupLabel: "Âm khó với người Việt",
    level: "intermediate",
    mouthTip: "Chu môi nhẹ, đẩy hơi như suỵt.",
    avoid: "Đừng đọc thành s thường.",
    examples: [
      { word: "she", hint: "shii" },
      { word: "fish", hint: "fish" },
      { word: "station", hint: "stây-shần" }
    ]
  },
  {
    id: "ch",
    symbol: "/tʃ/",
    vietnameseHint: "ch bật nhanh",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Bật t rồi chuyển nhanh sang sh.",
    avoid: "Đừng kéo thành chờ.",
    examples: [
      { word: "chair", hint: "che-ờ" },
      { word: "teacher", hint: "tii-chờ" },
      { word: "watch", hint: "quoch" }
    ]
  },
  {
    id: "j",
    symbol: "/dʒ/",
    vietnameseHint: "j/dj",
    group: "hard-for-vietnamese",
    groupLabel: "Âm khó với người Việt",
    level: "intermediate",
    mouthTip: "Bật d rồi chuyển sang âm giống j.",
    avoid: "Đừng đọc thành d Việt Nam đơn giản.",
    examples: [
      { word: "job", hint: "job" },
      { word: "orange", hint: "o-rinj" },
      { word: "language", hint: "leang-quịch" }
    ]
  },
  {
    id: "th-voiceless",
    symbol: "/θ/",
    vietnameseHint: "th cắn lưỡi, không rung",
    group: "hard-for-vietnamese",
    groupLabel: "Âm khó với người Việt",
    level: "intermediate",
    mouthTip: "Đặt đầu lưỡi giữa hai răng, thổi hơi.",
    avoid: "Đừng đọc thành t hoặc s.",
    examples: [
      { word: "thank", hint: "theangk" },
      { word: "three", hint: "thrii" },
      { word: "think", hint: "think" }
    ]
  },
  {
    id: "th-voiced",
    symbol: "/ð/",
    vietnameseHint: "dh cắn lưỡi, có rung",
    group: "hard-for-vietnamese",
    groupLabel: "Âm khó với người Việt",
    level: "advanced",
    mouthTip: "Đặt lưỡi như /θ/ nhưng rung dây thanh.",
    avoid: "Đừng đọc thành d hoặc đ.",
    examples: [
      { word: "mother", hint: "mâ-dhờ" },
      { word: "father", hint: "faa-dhờ" },
      { word: "this", hint: "dhis" }
    ]
  },
  {
    id: "ng",
    symbol: "/ŋ/",
    vietnameseHint: "ng cuối",
    group: "hard-for-vietnamese",
    groupLabel: "Âm khó với người Việt",
    level: "elementary",
    mouthTip: "Giống ng tiếng Việt, nhưng nếu ở cuối thì không thêm gờ.",
    avoid: "Đừng thêm âm g sau cùng.",
    examples: [
      { word: "sing", hint: "sing" },
      { word: "morning", hint: "moo-rning" },
      { word: "English", hint: "ing-glish" }
    ]
  },
  {
    id: "w",
    symbol: "/w/",
    vietnameseHint: "qu/u lướt",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Tròn môi trước rồi mở nhanh.",
    avoid: "Đừng đọc thành v.",
    examples: [
      { word: "water", hint: "quoo-tờ" },
      { word: "walk", hint: "quook" },
      { word: "want", hint: "quont" }
    ]
  },
  {
    id: "y",
    symbol: "/j/",
    vietnameseHint: "i lướt",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Giống âm i rất nhanh ở đầu âm tiết.",
    avoid: "Đừng đọc thành j tiếng Việt.",
    examples: [
      { word: "yes", hint: "ies" },
      { word: "yellow", hint: "ie-lâu" },
      { word: "music", hint: "miu-zik" }
    ]
  },
  {
    id: "r",
    symbol: "/r/",
    vietnameseHint: "r tiếng Anh",
    group: "hard-for-vietnamese",
    groupLabel: "Âm khó với người Việt",
    level: "intermediate",
    mouthTip: "Cong lưỡi nhẹ, không rung mạnh như r tiếng Việt.",
    avoid: "Đừng rung r quá nhiều.",
    examples: [
      { word: "red", hint: "red" },
      { word: "rice", hint: "rais" },
      { word: "run", hint: "rân" }
    ]
  },
  {
    id: "v",
    symbol: "/v/",
    vietnameseHint: "v răng-môi",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "elementary",
    mouthTip: "Răng trên chạm môi dưới, có rung.",
    avoid: "Đừng đọc thành d/y theo vùng miền.",
    examples: [
      { word: "very", hint: "ve-ri" },
      { word: "voice", hint: "vois" },
      { word: "live", hint: "liv" }
    ]
  },
  {
    id: "f",
    symbol: "/f/",
    vietnameseHint: "f/ph thổi hơi",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Răng trên chạm môi dưới, thổi hơi không rung.",
    avoid: "Đừng đọc thành ph có nguyên âm ờ phía sau.",
    examples: [
      { word: "fish", hint: "fish" },
      { word: "phone", hint: "fâun" },
      { word: "life", hint: "laif" }
    ]
  },
  {
    id: "z",
    symbol: "/z/",
    vietnameseHint: "z có rung",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "intermediate",
    mouthTip: "Giống s nhưng rung dây thanh.",
    avoid: "Đừng đọc thành s.",
    examples: [
      { word: "zoo", hint: "zuu" },
      { word: "music", hint: "miu-zik" },
      { word: "because", hint: "bi-koz" }
    ]
  },
  {
    id: "zh",
    symbol: "/ʒ/",
    vietnameseHint: "gi/sh có rung",
    group: "hard-for-vietnamese",
    groupLabel: "Âm khó với người Việt",
    level: "advanced",
    mouthTip: "Giống /ʃ/ nhưng rung dây thanh.",
    avoid: "Đừng đọc thành sh không rung.",
    examples: [
      { word: "vision", hint: "vi-giần" },
      { word: "measure", hint: "me-giờ" },
      { word: "usually", hint: "iu-giờ-li" }
    ]
  },
  {
    id: "p-final",
    symbol: "/p/",
    vietnameseHint: "p bật/chặn môi",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Mím môi rồi bật nhẹ, cuối từ thì chặn gọn.",
    avoid: "Đừng thêm 'pờ' ở cuối.",
    examples: [
      { word: "pen", hint: "pen" },
      { word: "ship", hint: "ship" },
      { word: "apple", hint: "ea-pồ" }
    ]
  },
  {
    id: "t-final",
    symbol: "/t/",
    vietnameseHint: "t chặn gọn",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Đầu lưỡi chạm sau răng trên, kết thúc gọn.",
    avoid: "Đừng thêm 'tờ' ở cuối.",
    examples: [
      { word: "eat", hint: "iit" },
      { word: "cat", hint: "keat" },
      { word: "night", hint: "nait" }
    ]
  },
  {
    id: "k-final",
    symbol: "/k/",
    vietnameseHint: "k chặn gọn",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Cuống lưỡi chặn phía sau, bật rất nhẹ.",
    avoid: "Đừng thêm 'cờ' ở cuối.",
    examples: [
      { word: "book", hint: "buk" },
      { word: "school", hint: "skuul" },
      { word: "walk", hint: "quook" }
    ]
  },
  {
    id: "s",
    symbol: "/s/",
    vietnameseHint: "s không rung",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Đẩy hơi qua khe răng, không rung.",
    avoid: "Đừng đọc thành z.",
    examples: [
      { word: "see", hint: "sii" },
      { word: "rice", hint: "rais" },
      { word: "school", hint: "skuul" }
    ]
  },
  {
    id: "l",
    symbol: "/l/",
    vietnameseHint: "l rõ",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Đầu lưỡi chạm lợi trên, cuối từ vẫn giữ âm.",
    avoid: "Đừng nuốt l cuối trong school.",
    examples: [
      { word: "look", hint: "luk" },
      { word: "blue", hint: "bluu" },
      { word: "school", hint: "skuul" }
    ]
  },
  {
    id: "b",
    symbol: "/b/",
    vietnameseHint: "b có rung",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Mím môi rồi bật, có rung dây thanh.",
    avoid: "Đừng đọc thành p.",
    examples: [
      { word: "book", hint: "buk" },
      { word: "blue", hint: "bluu" },
      { word: "beautiful", hint: "biu-tờ-phồ" }
    ]
  },
  {
    id: "d",
    symbol: "/d/",
    vietnameseHint: "đ/d nhẹ",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Đầu lưỡi chạm lợi trên, bật có rung.",
    avoid: "Đừng thêm 'đờ' ở cuối.",
    examples: [
      { word: "day", hint: "đây" },
      { word: "red", hint: "red" },
      { word: "good", hint: "gud" }
    ]
  },
  {
    id: "g",
    symbol: "/ɡ/",
    vietnameseHint: "g",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Bật ở phía sau miệng, có rung.",
    avoid: "Đừng đọc thành j.",
    examples: [
      { word: "green", hint: "griin" },
      { word: "dog", hint: "đog" },
      { word: "good", hint: "gud" }
    ]
  },
  {
    id: "h",
    symbol: "/h/",
    vietnameseHint: "h nhẹ",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Thở nhẹ ra, không siết cổ.",
    avoid: "Đừng bỏ mất h đầu.",
    examples: [
      { word: "hello", hint: "hờ-lâu" },
      { word: "home", hint: "hâum" },
      { word: "house", hint: "haos" }
    ]
  },
  {
    id: "m",
    symbol: "/m/",
    vietnameseHint: "m",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Mím môi, âm đi qua mũi.",
    avoid: "Đừng thêm nguyên âm sau m cuối.",
    examples: [
      { word: "milk", hint: "milk" },
      { word: "mother", hint: "mâ-dhờ" },
      { word: "name", hint: "nâym" }
    ]
  },
  {
    id: "n",
    symbol: "/n/",
    vietnameseHint: "n",
    group: "consonant",
    groupLabel: "Phụ âm",
    level: "beginner",
    mouthTip: "Đầu lưỡi chạm lợi trên, âm qua mũi.",
    avoid: "Đừng nhầm n với ng cuối.",
    examples: [
      { word: "name", hint: "nâym" },
      { word: "pen", hint: "pen" },
      { word: "run", hint: "rân" }
    ]
  }
];

export const IPA_GROUP_ORDER: IpaSound["group"][] = [
  "short-vowel",
  "long-vowel",
  "diphthong",
  "consonant",
  "hard-for-vietnamese"
];

export function groupIpaSounds() {
  return IPA_GROUP_ORDER.map((group) => ({
    group,
    label: IPA_SOUNDS.find((sound) => sound.group === group)?.groupLabel ?? group,
    sounds: IPA_SOUNDS.filter((sound) => sound.group === group)
  })).filter((item) => item.sounds.length > 0);
}
