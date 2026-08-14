#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'all-topics-hangout1.json');
const EXPECTED_TOPICS = [
  'hangout1-welcome',
  'hangout1-unit1-school-things',
  'hangout1-unit2-my-toys',
  'hangout1-unit3-my-classroom',
  'hangout1-unit4-family-and-friends',
  'hangout1-unit5-actions-and-animals',
  'hangout1-unit6-feelings',
  'hangout1-unit7-daily-activities',
  'hangout1-unit8-my-face-and-body',
  'hangout1-unit9-peoples-jobs',
];

const errors = [];
let totalWords = 0;

try {
  const content = fs.readFileSync(FILE, 'utf8');
  const data = JSON.parse(content);

  EXPECTED_TOPICS.forEach((topic) => {
    if (!data[topic]) {
      errors.push(`Missing topic group: ${topic}`);
    } else if (!Array.isArray(data[topic]) || data[topic].length === 0) {
      errors.push(`Topic group ${topic} is empty or not an array.`);
    } else {
      totalWords += data[topic].length;
      data[topic].forEach((word, idx) => {
        if (!word.id || !word.word || !word.meaning_vi || !word.example || !word.ipa_us) {
          errors.push(`[${topic} #${idx + 1}] Missing required field in word: ${JSON.stringify(word)}`);
        }
      });
    }
  });
} catch (err) {
  errors.push(`Failed to read/parse file: ${err.message}`);
}

if (errors.length > 0) {
  console.error('Validation failed:');
  errors.forEach((e) => console.error(` - ${e}`));
  process.exit(1);
} else {
  console.log(`Validation passed successfully! Found ${totalWords} total words across ${EXPECTED_TOPICS.length} units.`);
}
