import fs from "node:fs/promises";

const OUT_FILE = "grade9-basic-english-premium.json";
const KEY = "grade9-basic-english-premium";
const CREATED_AT = 1779703568473;
const EXISTING_GRADE_FILES = [
  "grade3-basic-english-premium.json",
  "grade4-basic-english-premium.json",
  "grade5-basic-english-premium.json",
];

const manualIpa = {
  biodiversity: "/ˌbaɪoʊdaɪˈvɝːsəti/",
  blogging: "/ˈblɑːɡɪŋ/",
  coding: "/ˈkoʊdɪŋ/",
  coursework: "/ˈkɔːrswɝːk/",
  rainforest: "/ˈreɪnfɔːrɪst/",
  sketching: "/ˈsketʃɪŋ/",
};

const arpabetToIpa = {
  AA: "ɑ", AE: "æ", AH: "ʌ", AO: "ɔ", AW: "aʊ", AY: "aɪ",
  B: "b", CH: "tʃ", D: "d", DH: "ð", EH: "ɛ", ER: "ɝ", EY: "eɪ",
  F: "f", G: "ɡ", HH: "h", IH: "ɪ", IY: "iː", JH: "dʒ", K: "k",
  L: "l", M: "m", N: "n", NG: "ŋ", OW: "oʊ", OY: "ɔɪ", P: "p",
  R: "r", S: "s", SH: "ʃ", T: "t", TH: "θ", UH: "ʊ", UW: "uː",
  V: "v", W: "w", Y: "j", Z: "z", ZH: "ʒ",
};
const vowelPhones = new Set(["AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"]);

const topics = [
  {
    topic: "school",
    label: "school",
    cefr: "B1",
    difficulty: 3,
    image: "grade nine school classroom",
    words: [
      ["curriculum", "chương trình học"],
      ["semester", "học kỳ"],
      ["essay", "bài luận"],
      ["reference", "tài liệu tham khảo"],
      ["debate", "cuộc tranh luận"],
      ["laboratory", "phòng thí nghiệm"],
      ["scholarship", "học bổng"],
      ["attendance", "sự chuyên cần"],
      ["discipline", "kỷ luật"],
      ["elective", "môn tự chọn"],
      ["transcript", "bảng điểm"],
      ["coursework", "bài tập trong khóa học"],
    ],
  },
  {
    topic: "family",
    label: "family",
    cefr: "B1",
    difficulty: 3,
    image: "teen family home",
    words: [
      ["adolescence", "tuổi vị thành niên"],
      ["responsibility", "trách nhiệm"],
      ["tradition", "truyền thống"],
      ["guardian", "người giám hộ"],
      ["ancestor", "tổ tiên"],
      ["conflict", "mâu thuẫn"],
      ["independence", "sự độc lập"],
      ["generation", "thế hệ"],
      ["ceremony", "buổi lễ"],
      ["household", "hộ gia đình"],
      ["privacy", "sự riêng tư"],
    ],
  },
  {
    topic: "animals",
    label: "animals",
    cefr: "B1",
    difficulty: 3,
    image: "wild animals habitat",
    words: [
      ["species", "loài"],
      ["habitat", "môi trường sống"],
      ["predator", "động vật săn mồi"],
      ["prey", "con mồi"],
      ["mammal", "động vật có vú"],
      ["reptile", "bò sát"],
      ["migration", "sự di cư"],
      ["extinction", "sự tuyệt chủng"],
      ["conservation", "sự bảo tồn"],
      ["wildlife", "động vật hoang dã"],
      ["adaptation", "sự thích nghi"],
      ["population", "quần thể"],
    ],
  },
  {
    topic: "food",
    label: "food and health",
    cefr: "B1",
    difficulty: 3,
    image: "healthy food nutrition",
    words: [
      ["nutrition", "dinh dưỡng"],
      ["ingredient", "nguyên liệu"],
      ["cuisine", "ẩm thực"],
      ["appetite", "sự thèm ăn"],
      ["diet", "chế độ ăn"],
      ["protein", "chất đạm"],
      ["vitamin", "vitamin"],
      ["carbohydrate", "carbohydrate"],
      ["recipe", "công thức nấu ăn"],
      ["flavor", "hương vị"],
      ["portion", "khẩu phần"],
      ["preservative", "chất bảo quản"],
    ],
  },
  {
    topic: "colors",
    label: "art and description",
    cefr: "B1",
    difficulty: 3,
    image: "art colors design",
    words: [
      ["shade", "sắc độ"],
      ["tone", "tông màu"],
      ["pattern", "hoa văn"],
      ["contrast", "sự tương phản"],
      ["highlight", "điểm nhấn"],
      ["background", "nền"],
      ["outline", "đường viền"],
      ["texture", "kết cấu"],
      ["transparent", "trong suốt"],
      ["fluorescent", "huỳnh quang"],
    ],
  },
  {
    topic: "activities",
    label: "activities",
    cefr: "B1",
    difficulty: 3,
    image: "teen activities teamwork",
    words: [
      ["participate", "tham gia"],
      ["volunteer", "tình nguyện"],
      ["compete", "thi đấu"],
      ["perform", "biểu diễn"],
      ["explore", "khám phá"],
      ["coordinate", "điều phối"],
      ["collaborate", "hợp tác"],
      ["research", "nghiên cứu"],
      ["rehearse", "diễn tập"],
      ["accomplish", "hoàn thành"],
      ["concentrate", "tập trung"],
    ],
  },
  {
    topic: "weather",
    label: "weather and climate",
    cefr: "B1",
    difficulty: 3,
    image: "weather climate sky",
    words: [
      ["meteorology", "khí tượng học"],
      ["humidity", "độ ẩm"],
      ["pressure", "áp suất"],
      ["thunderstorm", "bão có sấm sét"],
      ["drought", "hạn hán"],
      ["climate", "khí hậu"],
      ["atmosphere", "bầu khí quyển"],
      ["lightning", "tia chớp"],
      ["rainfall", "lượng mưa"],
      ["breeze", "làn gió nhẹ"],
    ],
  },
  {
    topic: "transportation",
    label: "transportation",
    cefr: "B1",
    difficulty: 3,
    image: "city transportation traffic",
    words: [
      ["transit", "vận chuyển công cộng"],
      ["pedestrian", "người đi bộ"],
      ["intersection", "giao lộ"],
      ["highway", "đường cao tốc"],
      ["congestion", "sự tắc nghẽn"],
      ["platform", "sân ga"],
      ["route", "tuyến đường"],
      ["fare", "giá vé"],
      ["departure", "sự khởi hành"],
      ["destination", "điểm đến"],
    ],
  },
  {
    topic: "body",
    label: "body and health",
    cefr: "B1",
    difficulty: 3,
    image: "human body health",
    words: [
      ["muscle", "cơ bắp"],
      ["skeleton", "bộ xương"],
      ["organ", "cơ quan nội tạng"],
      ["nerve", "dây thần kinh"],
      ["pulse", "mạch đập"],
      ["symptom", "triệu chứng"],
      ["injury", "chấn thương"],
      ["treatment", "sự điều trị"],
      ["posture", "tư thế"],
      ["eyesight", "thị lực"],
    ],
  },
  {
    topic: "clothes",
    label: "clothes and style",
    cefr: "B1",
    difficulty: 3,
    image: "clothes fashion fabric",
    words: [
      ["fabric", "vải"],
      ["sleeve", "tay áo"],
      ["collar", "cổ áo"],
      ["garment", "quần áo"],
      ["textile", "hàng dệt"],
      ["casual", "thường ngày"],
      ["formal", "trang trọng"],
      ["waterproof", "chống thấm nước"],
      ["fashionable", "hợp thời trang"],
      ["accessory", "phụ kiện"],
    ],
  },
  {
    topic: "sports",
    label: "sports",
    cefr: "B1",
    difficulty: 3,
    image: "sports competition team",
    words: [
      ["tournament", "giải đấu"],
      ["athlete", "vận động viên"],
      ["referee", "trọng tài"],
      ["opponent", "đối thủ"],
      ["championship", "chức vô địch"],
      ["endurance", "sức bền"],
      ["training", "việc luyện tập"],
      ["strategy", "chiến thuật"],
      ["score", "tỷ số"],
      ["teamwork", "tinh thần đồng đội"],
    ],
  },
  {
    topic: "house",
    label: "house and home",
    cefr: "B1",
    difficulty: 3,
    image: "house apartment room",
    words: [
      ["basement", "tầng hầm"],
      ["attic", "gác mái"],
      ["ceiling", "trần nhà"],
      ["hallway", "hành lang"],
      ["appliance", "thiết bị gia dụng"],
      ["faucet", "vòi nước"],
      ["outlet", "ổ cắm điện"],
      ["decoration", "đồ trang trí"],
      ["storage", "sự lưu trữ"],
      ["maintenance", "bảo trì"],
    ],
  },
  {
    topic: "nature",
    label: "nature and environment",
    cefr: "B1",
    difficulty: 3,
    image: "nature environment landscape",
    words: [
      ["environment", "môi trường"],
      ["pollution", "sự ô nhiễm"],
      ["resource", "tài nguyên"],
      ["landscape", "phong cảnh"],
      ["coastline", "đường bờ biển"],
      ["rainforest", "rừng mưa nhiệt đới"],
      ["volcano", "núi lửa"],
      ["erosion", "sự xói mòn"],
      ["renewable", "có thể tái tạo"],
      ["biodiversity", "đa dạng sinh học"],
    ],
  },
  {
    topic: "jobs",
    label: "jobs and careers",
    cefr: "B1",
    difficulty: 3,
    image: "careers jobs workplace",
    words: [
      ["developer", "nhà phát triển"],
      ["journalist", "nhà báo"],
      ["architect", "kiến trúc sư"],
      ["accountant", "kế toán viên"],
      ["technician", "kỹ thuật viên"],
      ["researcher", "nhà nghiên cứu"],
      ["designer", "nhà thiết kế"],
      ["consultant", "cố vấn"],
      ["electrician", "thợ điện"],
      ["pharmacist", "dược sĩ"],
    ],
  },
  {
    topic: "daily-routines",
    label: "daily routines",
    cefr: "B1",
    difficulty: 3,
    image: "daily routine teenager",
    words: [
      ["routine", "thói quen hằng ngày"],
      ["appointment", "cuộc hẹn"],
      ["deadline", "hạn chót"],
      ["errand", "việc vặt"],
      ["chore", "việc nhà"],
      ["reminder", "lời nhắc"],
      ["journal", "nhật ký"],
      ["alarm", "chuông báo thức"],
      ["commute", "việc đi lại hằng ngày"],
      ["prepare", "chuẩn bị"],
      ["reflect", "suy ngẫm"],
      ["priority", "sự ưu tiên"],
    ],
  },
  {
    topic: "friends",
    label: "friends and relationships",
    cefr: "B1",
    difficulty: 3,
    image: "teen friends relationship",
    words: [
      ["trust", "sự tin tưởng"],
      ["respect", "sự tôn trọng"],
      ["honesty", "sự trung thực"],
      ["loyalty", "lòng trung thành"],
      ["support", "sự ủng hộ"],
      ["sympathy", "sự cảm thông"],
      ["cooperation", "sự hợp tác"],
      ["encouragement", "sự khích lệ"],
    ],
  },
  {
    topic: "hobbies",
    label: "hobbies",
    cefr: "B1",
    difficulty: 3,
    image: "teen hobbies creative",
    words: [
      ["filmmaking", "làm phim"],
      ["blogging", "viết blog"],
      ["coding", "lập trình"],
      ["calligraphy", "thư pháp"],
      ["origami", "nghệ thuật gấp giấy"],
      ["pottery", "đồ gốm"],
      ["astronomy", "thiên văn học"],
      ["hiking", "đi bộ đường dài"],
      ["drama", "kịch"],
      ["sketching", "vẽ phác thảo"],
    ],
  },
  {
    topic: "places",
    label: "places in the community",
    cefr: "B1",
    difficulty: 3,
    image: "community places city",
    words: [
      ["embassy", "đại sứ quán"],
      ["courthouse", "tòa án"],
      ["auditorium", "hội trường"],
      ["university", "trường đại học"],
      ["gallery", "phòng trưng bày"],
      ["landmark", "địa danh nổi tiếng"],
      ["harbor", "bến cảng"],
      ["factory", "nhà máy"],
      ["suburb", "vùng ngoại ô"],
      ["district", "quận, huyện"],
    ],
  },
  {
    topic: "time",
    label: "time and planning",
    cefr: "B1",
    difficulty: 3,
    image: "time planning calendar",
    words: [
      ["century", "thế kỷ"],
      ["decade", "thập kỷ"],
      ["era", "thời đại"],
      ["period", "giai đoạn"],
      ["timeline", "dòng thời gian"],
      ["duration", "khoảng thời gian"],
      ["frequency", "tần suất"],
      ["interval", "khoảng cách thời gian"],
      ["punctual", "đúng giờ"],
      ["temporary", "tạm thời"],
      ["permanent", "vĩnh viễn"],
      ["sequence", "trình tự"],
    ],
  },
];

const exampleTemplates = {
  school: [
    "The Grade 9 students discussed the {word} during English class.",
    "Our teacher explained the word {word} with a clear example.",
    "The class learned why the {word} is important for study skills.",
  ],
  family: [
    "The story shows how {word} can affect a family.",
    "Mai wrote about {word} in her personal reflection.",
    "The discussion helped students understand {word} at home.",
  ],
  animals: [
    "The science article explained how {word} changes animal life.",
    "Students found information about {word} in the wildlife report.",
    "The documentary showed an example of {word} in nature.",
  ],
  food: [
    "The health lesson explained why {word} matters in a balanced diet.",
    "Students compared labels to learn more about {word}.",
    "The article gave useful advice about {word} and healthy eating.",
  ],
  colors: [
    "The art teacher showed how {word} changes the feeling of a picture.",
    "Students used {word} to describe the design in detail.",
    "The poster looked clearer after Lan adjusted the {word}.",
  ],
  activities: [
    "The club members decided to {word} in the school event.",
    "Students learned how to {word} while working in a group.",
    "The teacher encouraged everyone to {word} with confidence.",
  ],
  weather: [
    "The weather report warned people about {word} in the afternoon.",
    "Students studied {word} when learning about climate change.",
    "The science teacher asked the class to record {word} for one week.",
  ],
  transportation: [
    "The map helped students understand {word} in the city.",
    "The traveler checked information about {word} before leaving.",
    "The lesson compared different problems related to {word}.",
  ],
  body: [
    "The health teacher explained how {word} affects the body.",
    "Students read a short article about {word} and exercise.",
    "The doctor gave advice about {word} during the school visit.",
  ],
  clothes: [
    "The fashion article described {clothesTerm} in simple English.",
    "Students used {clothesTerm} to talk about clothing choices.",
    "The designer considered {clothesTerm} while planning the costume.",
  ],
  sports: [
    "The coach explained the importance of {word} before practice.",
    "Students wrote a report about {word} after the match.",
    "The team discussed {word} before the final game.",
  ],
  house: [
    "The family discussed {word} while planning the new house.",
    "The article gave advice about {word} at home.",
    "Students labeled {word} on the picture of the apartment.",
  ],
  nature: [
    "The class presentation explained why {word} should be protected.",
    "Students discussed {word} during the environment lesson.",
    "The report described how {word} affects local communities.",
  ],
  jobs: [
    "The career day speaker explained the work of {jobTerm}.",
    "Students interviewed {jobTerm} for their school project.",
    "The article described the skills {jobTerm} needs.",
  ],
  "daily-routines": [
    "Nam added {word} to his weekly plan.",
    "Students discussed how {word} can make daily life easier.",
    "The teacher asked everyone to write one sentence about {word}.",
  ],
  friends: [
    "Good friends build {word} by listening to each other.",
    "The story teaches students the value of {word}.",
    "The group solved the problem with {word} and patience.",
  ],
  hobbies: [
    "Linh enjoys {word} after school because it helps her relax.",
    "The club introduced {word} to new Grade 9 students.",
    "Students wrote about {word} in their hobby journals.",
  ],
  places: [
    "The class learned about the {word} during the community unit.",
    "Tourists visited the {word} after reading the guidebook.",
    "Students described the {word} in their city presentation.",
  ],
  time: [
    "The timeline showed how the {word} changed history.",
    "Students used {word} to organize events in the story.",
    "The teacher explained {word} with examples from daily life.",
  ],
};

function normalizeWord(word) {
  return word.toLowerCase().trim();
}

function fallbackAudio(word) {
  return `https://api.dictionaryapi.dev/media/pronunciations/en/${encodeURIComponent(word)}-us.mp3`;
}

function normalizeIpa(text) {
  if (!text) return "";
  const trimmed = text.trim();
  if (!trimmed) return "";
  return trimmed.startsWith("/") ? trimmed : `/${trimmed.replace(/^[/\\[]|[/\\]]$/g, "")}/`;
}

async function loadCmuDictionary() {
  const response = await fetch("https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict");
  if (!response.ok) throw new Error(`Unable to load CMU dictionary: HTTP ${response.status}`);
  const text = await response.text();
  const dictionary = new Map();
  for (const line of text.split(/\r?\n/)) {
    if (!line || line.startsWith(";")) continue;
    const [word, ...phones] = line.trim().split(/\s+/);
    const normalized = word.replace(/\(\d+\)$/, "");
    if (!dictionary.has(normalized)) dictionary.set(normalized, phones);
  }
  return dictionary;
}

function phonesToIpa(phones) {
  const parts = [];
  for (const phone of phones) {
    const match = phone.match(/^([A-Z]+)([012])?$/);
    if (!match) continue;
    const [, base, stress] = match;
    const ipa = arpabetToIpa[base];
    if (!ipa) continue;
    if (stress === "1" || stress === "2") {
      let insertAt = parts.length;
      while (insertAt > 0 && !parts[insertAt - 1].isVowel) insertAt -= 1;
      parts.splice(insertAt, 0, { ipa: stress === "1" ? "ˈ" : "ˌ", isVowel: false });
    }
    const vowel = vowelPhones.has(base);
    if (base === "AH" && stress === "0") parts.push({ ipa: "ə", isVowel: vowel });
    else if (base === "ER" && stress === "0") parts.push({ ipa: "ɚ", isVowel: vowel });
    else parts.push({ ipa, isVowel: vowel });
  }
  return parts.length > 0 ? `/${parts.map((part) => part.ipa).join("")}/` : "";
}

function getCmuIpa(cmuDictionary, word) {
  const normalized = word.toLowerCase().replace(/[^a-z]/g, "");
  if (manualIpa[normalized]) return manualIpa[normalized];
  const phones = cmuDictionary.get(normalized);
  return phones ? phonesToIpa(phones) : "";
}

async function getAudioAndFallbackIpa(word) {
  const apiWord = word.replace(/[^a-z-]/gi, "");
  try {
    const response = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(apiWord)}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const entries = await response.json();
    const phonetics = entries.flatMap((entry) => entry.phonetics || []);
    const usAudio = phonetics.find((p) => p.audio && /-us\.mp3|\/us\//i.test(p.audio));
    const withAudio = phonetics.find((p) => p.audio);
    const withText = phonetics.find((p) => p.text);
    const topLevelText = entries.find((entry) => entry.phonetic)?.phonetic;
    return {
      ipa_us: normalizeIpa(withText?.text || topLevelText),
      audio_us: (usAudio || withAudio || {}).audio || fallbackAudio(apiWord),
    };
  } catch {
    return { ipa_us: "", audio_us: fallbackAudio(apiWord) };
  }
}

function makeExample(topic, word, index) {
  const templates = exampleTemplates[topic];
  if (!templates) throw new Error(`Missing example templates for ${topic}`);
  const article = /^[aeiou]/i.test(word) ? "an" : "a";
  const styleWords = new Set(["casual", "formal", "waterproof", "fashionable"]);
  const clothesTerm = styleWords.has(word) ? `a ${word} style` : `the ${word}`;
  return templates[index % templates.length]
    .replaceAll("{word}", word)
    .replaceAll("{clothesTerm}", clothesTerm)
    .replaceAll("{jobTerm}", `${article} ${word}`);
}

const expectedCounts = {
  school: 12,
  family: 11,
  animals: 12,
  food: 12,
  colors: 10,
  activities: 11,
  weather: 10,
  transportation: 10,
  body: 10,
  clothes: 10,
  sports: 10,
  house: 10,
  nature: 10,
  jobs: 10,
  "daily-routines": 12,
  friends: 8,
  hobbies: 10,
  places: 10,
  time: 12,
};

const existingWords = new Set();
for (const file of EXISTING_GRADE_FILES) {
  const data = JSON.parse(await fs.readFile(file, "utf8"));
  const entries = data[Object.keys(data)[0]];
  for (const entry of entries) existingWords.add(normalizeWord(entry.word));
}

const sourceWords = new Set();
const overlaps = [];
for (const topic of topics) {
  if (topic.words.length !== expectedCounts[topic.topic]) {
    throw new Error(`${topic.topic} has ${topic.words.length} words, expected ${expectedCounts[topic.topic]}`);
  }
  for (const [word] of topic.words) {
    const normalized = normalizeWord(word);
    if (sourceWords.has(normalized)) throw new Error(`Duplicate source word: ${word}`);
    if (existingWords.has(normalized)) overlaps.push(word);
    sourceWords.add(normalized);
  }
}
if (overlaps.length > 0) {
  throw new Error(`Words already exist in grades 3-5: ${overlaps.join(", ")}`);
}

const cmuDictionary = await loadCmuDictionary();
const entries = [];
const missingIpa = [];

for (const topic of topics) {
  topic.words.forEach(([word, meaning_vi], indexInTopic) => {
    entries.push({
      pending: { word, meaning_vi, topic, indexInTopic },
    });
  });
}

for (let i = 0; i < entries.length; i += 1) {
  const { word, meaning_vi, topic, indexInTopic } = entries[i].pending;
  const pronunciation = await getAudioAndFallbackIpa(word);
  const ipa_us = getCmuIpa(cmuDictionary, word) || pronunciation.ipa_us;
  if (!ipa_us) missingIpa.push(word);
  entries[i] = {
    id: `g9-${String(i + 1).padStart(4, "0")}`,
    word,
    ipa_us,
    meaning_vi,
    example: makeExample(topic.topic, word, indexInTopic),
    status: "new",
    reviewLevel: 0,
    reviewCount: 0,
    createdAt: CREATED_AT,
    audio_us: pronunciation.audio_us,
    topic: topic.topic,
    cefr_level: topic.cefr,
    difficulty: topic.difficulty,
    image_keyword: `${word} ${topic.image}`,
  };
}

const requiredFields = ["id", "word", "ipa_us", "meaning_vi", "example", "status", "reviewLevel", "reviewCount", "createdAt", "audio_us", "topic", "cefr_level", "difficulty", "image_keyword"];
const topicCounts = entries.reduce((counts, entry) => {
  counts[entry.topic] = (counts[entry.topic] || 0) + 1;
  return counts;
}, {});
const missingRequired = entries.filter((entry) => requiredFields.some((field) => entry[field] === undefined || entry[field] === null || entry[field] === ""));

if (entries.length !== 200) throw new Error(`Expected 200 entries, got ${entries.length}`);
if (new Set(entries.map((entry) => normalizeWord(entry.word))).size !== entries.length) throw new Error("Duplicate words in output");
if (new Set(entries.map((entry) => entry.example)).size !== entries.length) throw new Error("Duplicate examples in output");
if (missingIpa.length > 0) throw new Error(`Missing IPA: ${missingIpa.join(", ")}`);
if (missingRequired.length > 0) throw new Error(`${missingRequired.length} entries have missing required fields`);

await fs.writeFile(OUT_FILE, `${JSON.stringify({ [KEY]: entries }, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  file: OUT_FILE,
  total: entries.length,
  topics: Object.keys(topicCounts).length,
  topicCounts,
  duplicateWords: 0,
  missingIpa: missingIpa.length,
  missingRequired: missingRequired.length,
}, null, 2));
