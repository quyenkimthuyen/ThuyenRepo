import fs from "node:fs/promises";

const OUT_FILE = "toeic-basic-english-premium.json";
const KEY = "toeic-basic-english-premium";
const CREATED_AT = 1779703568473;

const manualIpa = {
  bookkeeping: "/ˈbʊkkiːpɪŋ/",
  ecommerce: "/ˈiːkɑːmɝːs/",
  helpline: "/ˈhɛlplaɪn/",
  hostname: "/ˈhoʊstneɪm/",
  insurable: "/ɪnˈʃʊrəbəl/",
  onboarding: "/ˈɑːnbɔːrdɪŋ/",
  ringtone: "/ˈrɪŋtoʊn/",
  timesheet: "/ˈtaɪmʃiːt/",
  waybill: "/ˈweɪbɪl/",
};

const meaningOverrides = {
  bond: "trái phiếu",
  share: "cổ phiếu",
  return: "lợi nhuận thu về",
  yield: "lợi suất",
  principal: "tiền gốc",
  equity: "vốn chủ sở hữu",
  claim: "yêu cầu bồi thường",
  premium: "phí bảo hiểm",
  draft: "bản nháp",
  outlet: "ổ cắm",
  produce: "nông sản",
  leave: "nghỉ phép",
  line: "đường dây",
  rate: "mức giá",
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

const extraTopics = [
  {
    topic: "procurement",
    label: "procurement",
    cefr: "B2",
    difficulty: 3,
    image: "procurement purchasing contract",
    words: ["procurement", "requisition", "quotation", "bid", "tender", "bidder", "negotiation", "sourcing", "purchaser", "buyer", "order", "reorder", "backlog", "fulfillment", "shortage", "surplus", "estimate", "comparison", "selection", "acquisition", "outsourcing", "consignment", "installment", "brokerage", "dealership"],
  },
  {
    topic: "accounting",
    label: "accounting",
    cefr: "B2",
    difficulty: 4,
    image: "accounting ledger finance",
    words: ["accountant", "accounting", "ledger", "bookkeeping", "auditor", "depreciation", "asset", "equity", "credit", "debit", "payable", "receivable", "deduction", "allowance", "compensation", "deficit", "expenditure", "fiscal", "forecast", "valuation", "allocation", "amortization", "collateral", "overhead", "principal"],
  },
  {
    topic: "project-management",
    label: "project management",
    cefr: "B2",
    difficulty: 3,
    image: "project management timeline",
    words: ["milestone", "timeline", "deliverable", "stakeholder", "scope", "phase", "rollout", "implementation", "revision", "outcome", "progress", "priority", "constraint", "dependency", "feasibility", "initiative", "kickoff", "benchmark", "workflow", "roadmap", "task", "completion", "collaboration", "planning", "coordination"],
  },
  {
    topic: "leadership",
    label: "leadership and management",
    cefr: "B2",
    difficulty: 3,
    image: "leadership management team",
    words: ["executive", "board", "chairperson", "founder", "owner", "leadership", "delegation", "authority", "accountability", "decision", "directive", "performance", "productivity", "efficiency", "target", "mission", "vision", "hierarchy", "administration", "governance", "oversight", "deputy", "officer", "personnel", "subordinate"],
  },
  {
    topic: "human-resources",
    label: "human resources",
    cefr: "B2",
    difficulty: 3,
    image: "human resources employees",
    words: ["onboarding", "layoff", "turnover", "grievance", "pension", "retirement", "evaluation", "appraisal", "absenteeism", "workforce", "handbook", "probation", "relocation", "incentive", "leave", "maternity", "roster", "union", "morale", "seniority", "mentor", "mentorship", "coaching", "recruitment", "screening"],
  },
  {
    topic: "economics",
    label: "economics",
    cefr: "B2",
    difficulty: 4,
    image: "economics market graph",
    words: ["economy", "economist", "inflation", "deflation", "recession", "indicator", "sector", "trade", "tariff", "quota", "commodity", "export", "monopoly", "competition", "growth", "decline", "stability", "fluctuation", "trend", "index", "shortfall", "yield", "recovery", "consumption", "scarcity"],
  },
  {
    topic: "media",
    label: "media and public relations",
    cefr: "B1",
    difficulty: 3,
    image: "media public relations news",
    words: ["press", "journalist", "newsletter", "publication", "editor", "article", "broadcast", "channel", "announcement", "bulletin", "headline", "release", "spokesperson", "media", "subscription", "circulation", "column", "magazine", "newspaper", "reporter", "advertiser", "copywriter", "editorial", "podcast", "webpage"],
  },
  {
    topic: "communication",
    label: "communication",
    cefr: "B1",
    difficulty: 2,
    image: "communication phone message",
    words: ["telephone", "voicemail", "message", "notification", "signal", "connection", "conversation", "correspondence", "fax", "mailbox", "receiver", "transmitter", "microphone", "headset", "cable", "wireless", "broadband", "teleconference", "chat", "dialogue", "directory", "line", "ringtone", "speakerphone", "handset"],
  },
  {
    topic: "research",
    label: "research and analysis",
    cefr: "B2",
    difficulty: 4,
    image: "research analysis laboratory",
    words: ["research", "analysis", "analyst", "experiment", "hypothesis", "methodology", "observation", "respondent", "finding", "laboratory", "measurement", "variable", "accuracy", "reliability", "validity", "source", "abstract", "citation", "review", "trial", "statistics", "conclusion", "recommendation", "insight", "innovation"],
  },
  {
    topic: "data",
    label: "data and digital systems",
    cefr: "B2",
    difficulty: 4,
    image: "data digital system computer",
    words: ["data", "dataset", "algorithm", "automation", "backup", "bandwidth", "configuration", "dashboard", "encryption", "firewall", "interface", "hostname", "cloud", "upload", "download", "scanner", "router", "processor", "analytics", "metric", "template", "format", "debugging", "verification", "authentication"],
  },
  {
    topic: "banking",
    label: "banking services",
    cefr: "B2",
    difficulty: 4,
    image: "banking teller vault",
    words: ["teller", "vault", "cheque", "overdraft", "remittance", "borrower", "lender", "repayment", "liquidity", "solvency", "denomination", "coin", "cashless", "routing", "clearing", "authenticate", "passbook", "wire", "financier", "safekeeping", "escrow", "notary", "pledge", "depositary", "payee"],
  },
  {
    topic: "investment",
    label: "investment",
    cefr: "B2",
    difficulty: 4,
    image: "investment portfolio stocks",
    words: ["portfolio", "stockholder", "shareholder", "bond", "share", "securities", "broker", "diversification", "return", "mutual", "funding", "prospectus", "capitalization", "divestment", "accrual", "annuity", "treasury", "stake", "volatility", "earnings", "futures", "hedge", "speculator", "maturity", "distribution"],
  },
  {
    topic: "insurance",
    label: "insurance",
    cefr: "B2",
    difficulty: 4,
    image: "insurance policy claim",
    words: ["premium", "insurer", "deductible", "claimant", "damage", "theft", "protection", "renewal", "cancellation", "adjuster", "collision", "casualty", "underwriter", "insurable", "waiver", "exclusion", "rider", "actuary", "payout", "incident", "loss", "compensate", "assure", "insured", "uninsured"],
  },
  {
    topic: "construction",
    label: "construction",
    cefr: "B1",
    difficulty: 3,
    image: "construction building site",
    words: ["contractor", "subcontractor", "architect", "engineer", "cement", "concrete", "brick", "steel", "foundation", "roof", "wall", "beam", "scaffolding", "crane", "excavation", "site", "surveyor", "plumbing", "wiring", "carpenter", "masonry", "demolition", "insulation", "drainage", "zoning"],
  },
  {
    topic: "maintenance",
    label: "maintenance and repair",
    cefr: "B1",
    difficulty: 3,
    image: "maintenance repair tools",
    words: ["technician", "malfunction", "breakdown", "outage", "leak", "clog", "filter", "battery", "generator", "toolbox", "wrench", "ladder", "lubrication", "fixture", "ventilation", "thermostat", "cleaning", "sanitation", "disinfection", "servicing", "troubleshooting", "diagnostic", "washer", "dryer", "faucet"],
  },
  {
    topic: "energy",
    label: "energy and utilities",
    cefr: "B1",
    difficulty: 3,
    image: "energy utility power",
    words: ["electricity", "power", "voltage", "socket", "plug", "solar", "wind", "turbine", "grid", "fuel", "gasoline", "diesel", "coal", "oil", "pipeline", "renewable", "meter", "kilowatt", "hydrogen", "geothermal", "biomass", "nuclear", "petroleum", "charging", "blackout"],
  },
  {
    topic: "agriculture",
    label: "agriculture",
    cefr: "B1",
    difficulty: 3,
    image: "agriculture farm harvest",
    words: ["farm", "farmer", "crop", "harvest", "soil", "seed", "irrigation", "fertilizer", "pesticide", "livestock", "dairy", "poultry", "greenhouse", "orchard", "tractor", "barn", "acre", "grain", "wheat", "corn", "rice", "produce", "organic", "cultivation", "pasture"],
  },
  {
    topic: "food-preparation",
    label: "food preparation",
    cefr: "B1",
    difficulty: 2,
    image: "food preparation kitchen",
    words: ["nutrition", "calorie", "protein", "vegetarian", "allergy", "spice", "flavor", "texture", "serving", "grill", "oven", "stove", "freezer", "refrigerator", "pan", "knife", "leftover", "sauce", "marinade", "pastry", "bakery", "roast", "steam", "slice", "chop"],
  },
  {
    topic: "healthcare-advanced",
    label: "advanced healthcare",
    cefr: "B2",
    difficulty: 4,
    image: "healthcare hospital medical",
    words: ["referral", "specialist", "surgeon", "nurse", "ambulance", "paramedic", "ward", "symptom", "fever", "injury", "checkup", "dosage", "tablet", "capsule", "vaccine", "hospital", "medical", "dental", "rehabilitation", "prevention", "infection", "outpatient", "anesthesia", "consultation", "discharge"],
  },
  {
    topic: "public-services",
    label: "public services",
    cefr: "B1",
    difficulty: 3,
    image: "public services government city",
    words: ["municipal", "government", "council", "mayor", "citizen", "community", "library", "park", "recreation", "welfare", "infrastructure", "committee", "ordinance", "district", "province", "taxpayer", "ballot", "election", "embassy", "consulate", "census", "legislation", "bureau", "ministry", "governor"],
  },
];

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

async function translateToVietnamese(word) {
  const normalized = normalizeWord(word);
  if (meaningOverrides[normalized]) return meaningOverrides[normalized];
  const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q=${encodeURIComponent(word)}`;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return data?.[0]?.map((part) => part[0]).join("").trim() || word;
  } catch {
    return word;
  }
}

function makeExample(word, label) {
  return `The ${word} was useful in the ${label} context.`;
}

for (const topic of extraTopics) {
  if (topic.words.length !== 25) {
    throw new Error(`${topic.topic} has ${topic.words.length} words, expected 25`);
  }
}

const file = JSON.parse(await fs.readFile(OUT_FILE, "utf8"));
const baseEntries = file[KEY].slice(0, 500);
const baseWords = new Set(baseEntries.map((entry) => normalizeWord(entry.word)));
const sourceWords = new Set();
for (const topic of extraTopics) {
  for (const word of topic.words) {
    const normalized = normalizeWord(word);
    if (baseWords.has(normalized) || sourceWords.has(normalized)) {
      throw new Error(`Duplicate word before network lookup: ${word}`);
    }
    sourceWords.add(normalized);
  }
}

const cmuDictionary = await loadCmuDictionary();
const seen = new Set(baseEntries.map((entry) => normalizeWord(entry.word)));
const entries = [...baseEntries];

for (const topic of extraTopics) {
  for (const word of topic.words) {
    const normalized = normalizeWord(word);
    if (seen.has(normalized)) throw new Error(`Duplicate word: ${word}`);
    seen.add(normalized);
    const number = entries.length + 1;
    const pronunciation = await getAudioAndFallbackIpa(word);
    const cmuIpa = getCmuIpa(cmuDictionary, word);
    entries.push({
      id: `toeic-${String(number).padStart(4, "0")}`,
      word,
      ipa_us: cmuIpa || pronunciation.ipa_us,
      meaning_vi: await translateToVietnamese(word),
      example: makeExample(word, topic.label),
      status: "new",
      reviewLevel: 0,
      reviewCount: 0,
      createdAt: CREATED_AT,
      audio_us: pronunciation.audio_us,
      topic: topic.topic,
      cefr_level: topic.cefr,
      difficulty: topic.difficulty,
      image_keyword: `${word} ${topic.image}`,
    });
  }
}

const requiredFields = ["id", "word", "ipa_us", "meaning_vi", "example", "status", "reviewLevel", "reviewCount", "createdAt", "audio_us", "topic", "cefr_level", "difficulty", "image_keyword"];
const words = entries.map((entry) => normalizeWord(entry.word));
const ids = entries.map((entry) => entry.id);
const missingRequired = entries.filter((entry) => requiredFields.some((field) => entry[field] === undefined || entry[field] === null || entry[field] === ""));

if (entries.length !== 1000) throw new Error(`Expected 1000 entries, got ${entries.length}`);
if (new Set(words).size !== entries.length) throw new Error("Duplicate words found after append");
if (new Set(ids).size !== entries.length) throw new Error("Duplicate ids found after append");
if (missingRequired.length > 0) {
  console.error(JSON.stringify(missingRequired.map((entry) => ({
    id: entry.id,
    word: entry.word,
    missing: requiredFields.filter((field) => entry[field] === undefined || entry[field] === null || entry[field] === ""),
  })), null, 2));
  throw new Error(`${missingRequired.length} entries have missing required fields`);
}

await fs.writeFile(OUT_FILE, `${JSON.stringify({ [KEY]: entries }, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  file: OUT_FILE,
  total: entries.length,
  added: entries.length - baseEntries.length,
  uniqueWords: new Set(words).size,
  uniqueIds: new Set(ids).size,
  topics: new Set(entries.map((entry) => entry.topic)).size,
  missingRequired: missingRequired.length,
}, null, 2));
