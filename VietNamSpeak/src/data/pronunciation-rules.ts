export type PronunciationRule = {
  id: string;
  pattern: string;
  ipa: string;
  vietnameseHint: string;
  explanation: string;
  examples: string[];
};

export type SpellingToIpaRule = {
  id: string;
  spelling: string;
  usuallyIpa: string;
  vietnameseHint: string;
  when: string;
  examples: string[];
  watchOut: string;
};

export type IpaToSpellingRule = {
  id: string;
  ipa: string;
  commonSpellings: string[];
  vietnameseHint: string;
  examples: string[];
  listeningTip: string;
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

export const SPELLING_TO_IPA_RULES: SpellingToIpaRule[] = [
  {
    id: "magic-e-a",
    spelling: "a_e",
    usuallyIpa: "/eɪ/",
    vietnameseHint: "ây",
    when: "Một phụ âm nằm giữa a và e câm cuối từ.",
    examples: ["name", "make", "cake", "late"],
    watchOut: "have, are, palace không theo quy tắc này."
  },
  {
    id: "magic-e-i",
    spelling: "i_e",
    usuallyIpa: "/aɪ/",
    vietnameseHint: "ai",
    when: "Một phụ âm nằm giữa i và e câm cuối từ.",
    examples: ["bike", "time", "life", "five"],
    watchOut: "give, live nghĩa là sống thường đọc /ɪ/."
  },
  {
    id: "magic-e-o",
    spelling: "o_e",
    usuallyIpa: "/oʊ/",
    vietnameseHint: "âu",
    when: "Một phụ âm nằm giữa o và e câm cuối từ, kiểu Anh Mỹ.",
    examples: ["home", "phone", "note", "hope"],
    watchOut: "come, some, love đọc /ʌ/."
  },
  {
    id: "ee-ea",
    spelling: "ee, ea",
    usuallyIpa: "/iː/",
    vietnameseHint: "ii",
    when: "Thường gặp ở giữa từ hoặc cuối từ.",
    examples: ["see", "feet", "green", "eat", "teacher"],
    watchOut: "bread, head, great là ngoại lệ phổ biến."
  },
  {
    id: "short-i",
    spelling: "i",
    usuallyIpa: "/ɪ/",
    vietnameseHint: "i ngắn",
    when: "Trong từ ngắn hoặc âm tiết đóng: i + phụ âm.",
    examples: ["sit", "fish", "milk", "win"],
    watchOut: "i trước e câm thường thành /aɪ/: bike, time."
  },
  {
    id: "short-a",
    spelling: "a",
    usuallyIpa: "/æ/",
    vietnameseHint: "ea",
    when: "Trong âm tiết đóng: a + phụ âm.",
    examples: ["cat", "bag", "map", "apple"],
    watchOut: "a trong father, water, name đọc khác."
  },
  {
    id: "short-u",
    spelling: "u, o, ou",
    usuallyIpa: "/ʌ/",
    vietnameseHint: "â",
    when: "Nhiều từ ngắn có u; một số từ có o/ou cũng đọc /ʌ/.",
    examples: ["run", "cup", "sun", "love", "enough"],
    watchOut: "put, push đọc /ʊ/; rule này không tuyệt đối."
  },
  {
    id: "oo-long-short",
    spelling: "oo",
    usuallyIpa: "/uː/ hoặc /ʊ/",
    vietnameseHint: "uu hoặc u",
    when: "oo dài trong food, school; oo ngắn trong book, good.",
    examples: ["food", "school", "room", "book", "good", "look"],
    watchOut: "Cần học theo nhóm từ vì oo có hai âm chính."
  },
  {
    id: "igh",
    spelling: "igh",
    usuallyIpa: "/aɪ/",
    vietnameseHint: "ai",
    when: "gh thường câm trong cụm igh.",
    examples: ["night", "light", "right", "high"],
    watchOut: "Không đọc g/h."
  },
  {
    id: "ay-ai",
    spelling: "ay, ai",
    usuallyIpa: "/eɪ/",
    vietnameseHint: "ây",
    when: "ay thường ở cuối từ; ai thường ở giữa từ.",
    examples: ["day", "play", "rain", "train"],
    watchOut: "said, again có thể đọc khác."
  },
  {
    id: "ow-ou",
    spelling: "ow, ou",
    usuallyIpa: "/aʊ/",
    vietnameseHint: "ao",
    when: "Nhiều từ có ow/ou đọc như ao.",
    examples: ["cow", "now", "brown", "house", "mouth"],
    watchOut: "know, low, show đọc /oʊ/."
  },
  {
    id: "ow-oa-o-e",
    spelling: "ow, oa, o_e",
    usuallyIpa: "/oʊ/",
    vietnameseHint: "âu",
    when: "Phổ biến trong Anh Mỹ.",
    examples: ["know", "show", "boat", "road", "home"],
    watchOut: "cow, now, brown đọc /aʊ/."
  },
  {
    id: "oi-oy",
    spelling: "oi, oy",
    usuallyIpa: "/ɔɪ/",
    vietnameseHint: "oi",
    when: "oi thường giữa từ; oy thường cuối từ.",
    examples: ["boy", "toy", "coin", "voice"],
    watchOut: "Không tách thành hai âm rời quá lâu."
  },
  {
    id: "ar",
    spelling: "ar",
    usuallyIpa: "/ɑr/",
    vietnameseHint: "aar",
    when: "Trong Anh Mỹ, r thường được phát âm rõ.",
    examples: ["car", "far", "start", "cart"],
    watchOut: "war, warm thường là /wɔr/."
  },
  {
    id: "er-ir-ur",
    spelling: "er, ir, ur",
    usuallyIpa: "/ɝ/ hoặc /ɚ/",
    vietnameseHint: "ơr",
    when: "Âm r-colored vowel trong Anh Mỹ.",
    examples: ["her", "bird", "girl", "turn", "teacher"],
    watchOut: "Không đọc thành ơ thuần kiểu Anh Anh."
  },
  {
    id: "tion-sion",
    spelling: "tion, sion",
    usuallyIpa: "/ʃən/ hoặc /ʒən/",
    vietnameseHint: "shần hoặc giần",
    when: "Đuôi danh từ rất phổ biến.",
    examples: ["nation", "station", "question", "vision"],
    watchOut: "question có /tʃən/; vision có /ʒən/."
  },
  {
    id: "th",
    spelling: "th",
    usuallyIpa: "/θ/ hoặc /ð/",
    vietnameseHint: "th hoặc dh",
    when: "th vô thanh trong think; hữu thanh trong this.",
    examples: ["think", "thank", "three", "this", "mother", "they"],
    watchOut: "Phải học theo từ để biết /θ/ hay /ð/."
  },
  {
    id: "ch-sh-ph-ng",
    spelling: "ch, sh, ph, ng",
    usuallyIpa: "/tʃ/, /ʃ/, /f/, /ŋ/",
    vietnameseHint: "ch, sh, f, ng",
    when: "Các cụm phụ âm phổ biến và khá ổn định.",
    examples: ["chair", "ship", "phone", "sing"],
    watchOut: "ch đôi khi đọc /k/: school, chaos, chemistry."
  },
  {
    id: "c-g-soft-hard",
    spelling: "c, g",
    usuallyIpa: "c: /k/ hoặc /s/; g: /ɡ/ hoặc /dʒ/",
    vietnameseHint: "k/s, g/j",
    when: "c/g trước e, i, y thường mềm; trước a, o, u thường cứng.",
    examples: ["cat", "city", "go", "giant", "gym"],
    watchOut: "English có nhiều ngoại lệ: get, girl đọc /ɡ/."
  },
  {
    id: "silent-letters",
    spelling: "k, gh, b, t, l câm",
    usuallyIpa: "không có âm",
    vietnameseHint: "bỏ qua chữ câm",
    when: "Một số cụm chính tả có chữ không phát âm.",
    examples: ["know", "night", "comb", "listen", "walk"],
    watchOut: "Đừng cố đọc mọi chữ cái nhìn thấy."
  }
];

export const IPA_TO_SPELLING_RULES: IpaToSpellingRule[] = [
  {
    id: "ipa-i-long",
    ipa: "/iː/",
    commonSpellings: ["ee", "ea", "e", "ie", "ei"],
    vietnameseHint: "ii",
    examples: ["see", "green", "eat", "teacher", "field", "receive"],
    listeningTip: "Nếu nghe ii dài, thử nghĩ đến ee/ea trước."
  },
  {
    id: "ipa-i-short",
    ipa: "/ɪ/",
    commonSpellings: ["i", "y", "ui"],
    vietnameseHint: "i ngắn",
    examples: ["sit", "fish", "milk", "gym", "build"],
    listeningTip: "Âm ngắn thường nằm trong âm tiết đóng."
  },
  {
    id: "ipa-ae",
    ipa: "/æ/",
    commonSpellings: ["a"],
    vietnameseHint: "ea",
    examples: ["cat", "bag", "map", "apple", "family"],
    listeningTip: "Nghe âm a-e mở rộng thì thường viết bằng a."
  },
  {
    id: "ipa-uh",
    ipa: "/ʌ/",
    commonSpellings: ["u", "o", "ou", "oo"],
    vietnameseHint: "â",
    examples: ["run", "cup", "love", "enough", "blood"],
    listeningTip: "Nghe â trong từ phổ biến có thể là u hoặc o."
  },
  {
    id: "ipa-u-long",
    ipa: "/uː/",
    commonSpellings: ["oo", "u", "ue", "ew", "ui"],
    vietnameseHint: "uu",
    examples: ["food", "school", "blue", "true", "new", "fruit"],
    listeningTip: "Nếu nghe uu dài, oo/ue/u là ứng viên mạnh."
  },
  {
    id: "ipa-u-short",
    ipa: "/ʊ/",
    commonSpellings: ["oo", "u", "ou"],
    vietnameseHint: "u ngắn",
    examples: ["book", "good", "look", "put", "could"],
    listeningTip: "Âm u ngắn hay gặp trong nhóm book/good/look."
  },
  {
    id: "ipa-ei",
    ipa: "/eɪ/",
    commonSpellings: ["a_e", "ay", "ai", "eigh", "ea"],
    vietnameseHint: "ây",
    examples: ["name", "day", "rain", "eight", "great"],
    listeningTip: "Nghe ây thì thử a_e, ay, ai."
  },
  {
    id: "ipa-ai",
    ipa: "/aɪ/",
    commonSpellings: ["i_e", "igh", "y", "ie"],
    vietnameseHint: "ai",
    examples: ["bike", "night", "my", "try", "pie"],
    listeningTip: "Nghe ai trong từ ngắn thường là i_e, igh hoặc y cuối."
  },
  {
    id: "ipa-ou",
    ipa: "/oʊ/",
    commonSpellings: ["o_e", "oa", "ow", "o"],
    vietnameseHint: "âu",
    examples: ["home", "boat", "show", "go", "know"],
    listeningTip: "Trong Anh Mỹ, /oʊ/ thường không phải âm o Việt."
  },
  {
    id: "ipa-au",
    ipa: "/aʊ/",
    commonSpellings: ["ow", "ou"],
    vietnameseHint: "ao",
    examples: ["now", "cow", "brown", "house", "mouth"],
    listeningTip: "Nghe ao thì nghĩ ow/ou."
  },
  {
    id: "ipa-oi",
    ipa: "/ɔɪ/",
    commonSpellings: ["oi", "oy"],
    vietnameseHint: "oi",
    examples: ["coin", "voice", "boy", "toy"],
    listeningTip: "oi giữa từ thường viết oi, cuối từ thường viết oy."
  },
  {
    id: "ipa-ar",
    ipa: "/ɑr/",
    commonSpellings: ["ar"],
    vietnameseHint: "aar",
    examples: ["car", "far", "start", "cart"],
    listeningTip: "Anh Mỹ phát âm r rõ, nên nghe aar thường có ar."
  },
  {
    id: "ipa-er",
    ipa: "/ɝ/, /ɚ/",
    commonSpellings: ["er", "ir", "ur", "or", "ear"],
    vietnameseHint: "ơr",
    examples: ["her", "bird", "turn", "word", "learn", "teacher"],
    listeningTip: "Nghe ơr cần nhớ nhiều cách viết: er/ir/ur/or/ear."
  },
  {
    id: "ipa-sh",
    ipa: "/ʃ/",
    commonSpellings: ["sh", "ti", "ci", "ssi", "ch"],
    vietnameseHint: "sh",
    examples: ["ship", "fish", "station", "special", "mission", "chef"],
    listeningTip: "Nghe sh ở cuối đuôi -tion thường viết tion."
  },
  {
    id: "ipa-ch",
    ipa: "/tʃ/",
    commonSpellings: ["ch", "tch", "tu", "tion"],
    vietnameseHint: "ch",
    examples: ["chair", "watch", "future", "question"],
    listeningTip: "Nghe ch cuối từ sau nguyên âm ngắn thường có tch."
  },
  {
    id: "ipa-j",
    ipa: "/dʒ/",
    commonSpellings: ["j", "g", "dge", "ge", "di"],
    vietnameseHint: "j",
    examples: ["job", "giant", "bridge", "orange", "soldier"],
    listeningTip: "Nghe j trước e/i/y có thể viết g."
  },
  {
    id: "ipa-th",
    ipa: "/θ/",
    commonSpellings: ["th"],
    vietnameseHint: "th",
    examples: ["think", "thank", "three", "mouth"],
    listeningTip: "Nghe th không rung gần như luôn viết th."
  },
  {
    id: "ipa-dh",
    ipa: "/ð/",
    commonSpellings: ["th"],
    vietnameseHint: "dh",
    examples: ["this", "they", "mother", "weather"],
    listeningTip: "Nghe dh có rung cũng thường viết th."
  },
  {
    id: "ipa-ng",
    ipa: "/ŋ/",
    commonSpellings: ["ng", "n trước k/g"],
    vietnameseHint: "ng",
    examples: ["sing", "song", "English", "think", "bank"],
    listeningTip: "Nghe ng cuối thường viết ng; trước k thường viết n."
  },
  {
    id: "ipa-f",
    ipa: "/f/",
    commonSpellings: ["f", "ff", "ph", "gh"],
    vietnameseHint: "f",
    examples: ["fish", "coffee", "phone", "laugh"],
    listeningTip: "Nghe f có thể là f/ph/gh; ph phổ biến trong từ gốc Hy Lạp."
  },
  {
    id: "ipa-s",
    ipa: "/s/",
    commonSpellings: ["s", "ss", "c", "ce", "ci"],
    vietnameseHint: "s",
    examples: ["see", "class", "city", "face", "rice"],
    listeningTip: "Nghe s trước âm e/i có thể viết c."
  },
  {
    id: "ipa-z",
    ipa: "/z/",
    commonSpellings: ["z", "s", "se"],
    vietnameseHint: "z",
    examples: ["zoo", "music", "because", "please"],
    listeningTip: "Nghe z không chắc là chữ z; s giữa nguyên âm hay đọc /z/."
  }
];
