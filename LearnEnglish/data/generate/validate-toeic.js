#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const DATASET_KEY = 'toeic-basic-english-premium';
const FILE = path.join(__dirname, 'toeic-basic-english-premium.json');
const REQUIRED_TOPICS = [
  'office',
  'meetings',
  'communication',
  'scheduling',
  'travel',
  'transportation',
  'hospitality',
  'dining',
  'shopping',
  'finance',
  'banking',
  'accounting',
  'sales',
  'marketing',
  'human-resources',
  'training',
  'operations',
  'manufacturing',
  'technology',
  'shipping',
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
const IPA_SYMBOL_RE = /[ˈˌːəɚɝæɑɔɛɪʊʌθðʃʒŋɡ]/;
const URL_RE = /^https:\/\/api\.dictionaryapi\.dev\/media\/pronunciations\/en\/[a-z0-9-]+-us\.mp3$/;

const errors = [];
const warnings = [];
const stats = { total: 0, topics: {}, cefr: {}, difficulty: {} };

function normalize(value) {
  return String(value || '').trim().toLowerCase();
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

(entries || []).forEach((entry, index) => {
  const id = entry && entry.id ? entry.id : `entry-${index + 1}`;

  REQUIRED_FIELDS.forEach((field) => {
    if (!(field in entry) || entry[field] === '' || entry[field] === null || entry[field] === undefined) {
      addError(id, `Missing required field: ${field}`);
    }
  });

  if (!/^toeic-\d{4}$/.test(entry.id || '')) addError(id, 'ID must match toeic-0001 format.');
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
  if (!['A2', 'B1', 'B2'].includes(entry.cefr_level)) addError(id, `Unsupported CEFR level: ${entry.cefr_level}`);
  if (!Number.isInteger(entry.difficulty) || entry.difficulty < 1 || entry.difficulty > 4) {
    addError(id, 'Difficulty must be an integer from 1 to 4.');
  }

  const example = entry.example || '';
  if (!/^[A-Z]/.test(example)) addError(id, 'Example must start with a capital letter.');
  if (!/[.!?]$/.test(example)) addError(id, 'Example must end with punctuation.');
  if (example.split(/\s+/).length < 7) addWarning(id, 'Example may be too short for TOEIC context.');
  if (/\ba [aeiou]/i.test(example)) addError(id, 'Possible article error: use "an" before vowel sounds.');
  if (/\ban [bcdfghjklmnpqrstvwxyz]/i.test(example)) {
    addError(id, 'Possible article error: use "a" before consonant sounds.');
  }

  stats.topics[entry.topic] = (stats.topics[entry.topic] || 0) + 1;
  stats.cefr[entry.cefr_level] = (stats.cefr[entry.cefr_level] || 0) + 1;
  stats.difficulty[entry.difficulty] = (stats.difficulty[entry.difficulty] || 0) + 1;
});

if (stats.total < 750 || stats.total > 850) {
  addWarning('dataset', `Expected about 800 entries; found ${stats.total}.`);
}

REQUIRED_TOPICS.forEach((topic) => {
  if (!stats.topics[topic]) addError('topics', `Missing required topic: ${topic}`);
});

console.log('TOEIC vocabulary validation summary');
console.log('-----------------------------------');
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
