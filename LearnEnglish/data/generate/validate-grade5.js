#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const DATASET_KEY = 'grade5-basic-english-premium';
const FILE = path.join(__dirname, 'grade5-basic-english-premium.json');
const REQUIRED_TOPICS = [
  'school',
  'family',
  'animals',
  'food',
  'colors',
  'activities',
  'weather',
  'transportation',
  'body',
  'clothes',
  'sports',
  'house',
  'nature',
  'jobs',
  'daily-routines',
  'friends',
  'hobbies',
  'places',
  'time',
];
const REQUIRED_FIELDS = [
  'id',
  'word',
  'ipa_us',
  'meaning_vi',
  'example',
  'status',
  'reviewLevel',
  'reviewCount',
  'createdAt',
  'audio_us',
  'topic',
  'cefr_level',
  'difficulty',
  'image_keyword',
];
const BANNED_EXAMPLE_STARTS = [/^I like\b/i, /^I can see\b/i, /^This is my\b/i];
const IPA_SYMBOL_RE = /[ˈˌːəɚɝæɑɔɛɪʊʌθðʃʒŋɡ]/;
const URL_RE = /^https:\/\/api\.dictionaryapi\.dev\/media\/pronunciations\/en\/[a-z0-9-]+-us\.mp3$/;

const errors = [];
const warnings = [];
const stats = { total: 0, topics: {}, cefr: {}, difficulty: {} };

function normalize(value) {
  return String(value || '').trim().toLowerCase();
}

function templateKey(example) {
  return normalize(example)
    .replace(/[.,!?;:'’]/g, '')
    .replace(/\b(my|your|his|her|our|their|a|an|the|this|that|these|those)\b/g, '_')
    .split(/\s+/)
    .slice(0, 5)
    .join(' ');
}

function tokenSet(example) {
  return new Set(
    normalize(example)
      .replace(/[^a-z\s]/g, '')
      .split(/\s+/)
      .filter(Boolean),
  );
}

function jaccard(a, b) {
  const intersection = [...a].filter((x) => b.has(x)).length;
  const union = new Set([...a, ...b]).size;
  return union ? intersection / union : 0;
}

function addError(id, message) {
  errors.push(`${id || 'dataset'}: ${message}`);
}

function addWarning(id, message) {
  warnings.push(`${id || 'dataset'}: ${message}`);
}

let parsed;
try {
  parsed = JSON.parse(fs.readFileSync(FILE, 'utf8'));
} catch (error) {
  console.error(`Cannot read or parse ${FILE}: ${error.message}`);
  process.exit(1);
}

const entries = parsed[DATASET_KEY];
if (!Array.isArray(entries)) {
  addError(DATASET_KEY, 'Top-level dataset key must contain an array.');
} else {
  stats.total = entries.length;
}

const ids = new Map();
const words = new Map();
const examples = new Map();
const templates = new Map();
const exampleTokens = [];

(entries || []).forEach((entry, index) => {
  const id = entry && entry.id ? entry.id : `entry-${index + 1}`;

  REQUIRED_FIELDS.forEach((field) => {
    if (!(field in entry) || entry[field] === '' || entry[field] === null || entry[field] === undefined) {
      addError(id, `Missing required field: ${field}`);
    }
  });

  if (!/^g5-\d{4}$/.test(entry.id || '')) addError(id, 'ID must match g5-0001 format.');
  if (ids.has(entry.id)) addError(id, `Duplicate id also used by ${ids.get(entry.id)}`);
  ids.set(entry.id, id);

  const wordKey = normalize(entry.word);
  if (words.has(wordKey)) addError(id, `Duplicate word also used by ${words.get(wordKey)}`);
  words.set(wordKey, id);

  const exampleKey = normalize(entry.example);
  if (examples.has(exampleKey)) addError(id, `Duplicate example also used by ${examples.get(exampleKey)}`);
  examples.set(exampleKey, id);

  if (!/^\/.+\/$/.test(entry.ipa_us || '') || !IPA_SYMBOL_RE.test(entry.ipa_us || '')) {
    addError(id, `IPA looks invalid: ${entry.ipa_us}`);
  }
  if (/^\/[a-z -]+\/$/i.test(entry.ipa_us || '')) {
    addWarning(id, `IPA contains only plain letters; verify manually: ${entry.ipa_us}`);
  }

  if (!URL_RE.test(entry.audio_us || '')) addError(id, `Malformed audio_us URL: ${entry.audio_us}`);
  if (!REQUIRED_TOPICS.includes(entry.topic)) addError(id, `Unknown topic: ${entry.topic}`);
  if (!['A1', 'A2'].includes(entry.cefr_level)) addError(id, `Unsupported CEFR level: ${entry.cefr_level}`);
  if (!Number.isInteger(entry.difficulty) || entry.difficulty < 1 || entry.difficulty > 3) {
    addError(id, 'Difficulty must be an integer from 1 to 3.');
  }

  const example = entry.example || '';
  if (!/^[A-Z]/.test(example)) addError(id, 'Example must start with a capital letter.');
  if (!/[.!?]$/.test(example)) addError(id, 'Example must end with punctuation.');
  if (example.split(/\s+/).length < 6) addWarning(id, 'Example may be too short.');
  if (BANNED_EXAMPLE_STARTS.some((re) => re.test(example))) {
    addError(id, `Forbidden repetitive example pattern: ${example}`);
  }
  if (/\ba [aeiou]/i.test(example)) addError(id, 'Possible article error: use "an" before vowel sounds.');
  if (/\ban [bcdfghjklmnpqrstvwxyz]/i.test(example)) {
    addError(id, 'Possible article error: use "a" before consonant sounds.');
  }
  if (/\ba homework\b/i.test(example)) addError(id, 'Homework is uncountable; do not use "a homework".');
  if (/\b(She|He|It) (read|write|play|eat|go|walk|ride|help|make|take|want|need)\b/.test(example)) {
    addError(id, 'Possible subject-verb agreement issue.');
  }

  const tKey = templateKey(example);
  templates.set(tKey, (templates.get(tKey) || []).concat(id));
  exampleTokens.push({ id, set: tokenSet(example) });

  stats.topics[entry.topic] = (stats.topics[entry.topic] || 0) + 1;
  stats.cefr[entry.cefr_level] = (stats.cefr[entry.cefr_level] || 0) + 1;
  stats.difficulty[entry.difficulty] = (stats.difficulty[entry.difficulty] || 0) + 1;
});

REQUIRED_TOPICS.forEach((topic) => {
  if (!stats.topics[topic]) addError('topics', `Missing required topic: ${topic}`);
});

for (const [key, idsForTemplate] of templates.entries()) {
  if (idsForTemplate.length > 2) {
    addWarning('templates', `Repeated example opening (${idsForTemplate.length}): "${key}" in ${idsForTemplate.join(', ')}`);
  }
}

for (let i = 0; i < exampleTokens.length; i += 1) {
  for (let j = i + 1; j < exampleTokens.length; j += 1) {
    const score = jaccard(exampleTokens[i].set, exampleTokens[j].set);
    if (score >= 0.82) {
      addWarning(
        'examples',
        `Near-identical examples: ${exampleTokens[i].id} and ${exampleTokens[j].id} (${score.toFixed(2)})`,
      );
    }
  }
}

console.log('Grade 5 vocabulary validation summary');
console.log('-------------------------------------');
console.log(`Entries: ${stats.total}`);
console.log(`Topics: ${Object.keys(stats.topics).length}/${REQUIRED_TOPICS.length}`);
console.log('By topic:', stats.topics);
console.log('By CEFR:', stats.cefr);
console.log('By difficulty:', stats.difficulty);
console.log(`Warnings: ${warnings.length}`);
warnings.forEach((warning) => console.warn(`WARN  ${warning}`));
console.log(`Errors: ${errors.length}`);
errors.forEach((error) => console.error(`ERROR ${error}`));

if (errors.length > 0) process.exit(1);
