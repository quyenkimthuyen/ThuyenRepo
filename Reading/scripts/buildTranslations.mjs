import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { SUPPLEMENT_LESSONS } from '../js/supplementLessons.js';
import { LESSON_BANK } from './lessonBankData.mjs';
import { A2_BANK } from './banks/a2.mjs';
import { B1_BANK } from './banks/b1.mjs';
import { B2_BANK } from './banks/b2.mjs';
import { C1_BANK } from './banks/c1.mjs';
import { A1_VI } from './translationBanks/a1.mjs';
import { A2_VI } from './translationBanks/a2.mjs';
import { B1_VI } from './translationBanks/b1.mjs';
import { B2_VI } from './translationBanks/b2.mjs';
import { C1_VI } from './translationBanks/c1.mjs';
import { IELTS_VI } from './translationBanks/ielts.mjs';

const BANKS = {
  a1: LESSON_BANK.a1,
  a2: A2_BANK,
  b1: B1_BANK,
  b2: B2_BANK,
  c1: C1_BANK,
};

const VI_BANKS = {
  a1: A1_VI,
  a2: A2_VI,
  b1: B1_VI,
  b2: B2_VI,
  c1: C1_VI,
};

/** @param {unknown} entry */
function viSentences(entry) {
  if (Array.isArray(entry)) return entry;
  if (entry && typeof entry === 'object' && Array.isArray(entry.sentences)) {
    return entry.sentences;
  }
  throw new Error('Invalid translation entry');
}

/**
 * @param {string} level
 * @param {string} topic
 * @param {string} title
 */
function lookupVi(level, topic, title) {
  const enBank = BANKS[level]?.[topic] ?? [];
  const viBank = VI_BANKS[level]?.[topic] ?? [];
  const idx = enBank.findIndex((l) => l.title === title);
  if (idx === -1) {
    throw new Error(`No bank match: ${level}/${topic}/${title}`);
  }
  const vi = viSentences(viBank[idx]);
  const en = enBank[idx].sentences;
  if (vi.length !== en.length) {
    throw new Error(
      `Sentence count mismatch ${level}/${topic}/${title}: en=${en.length} vi=${vi.length}`,
    );
  }
  return vi;
}

/** @type {Record<string, string[]>} */
const translations = { ...IELTS_VI };

for (const lesson of SUPPLEMENT_LESSONS) {
  translations[lesson.id] = lookupVi(lesson.level, lesson.topic, lesson.title);
}

const out = `/** Auto-generated supplement translations — do not edit by hand */\nexport const SUPPLEMENT_TRANSLATIONS = ${JSON.stringify(translations, null, 2)};\n`;

const root = dirname(fileURLToPath(import.meta.url));
writeFileSync(join(root, '../js/supplementTranslations.js'), out);

console.log(`Generated ${Object.keys(translations).length} translation entries`);
console.log(`  supplement: ${SUPPLEMENT_LESSONS.length}`);
console.log(`  ielts: ${Object.keys(IELTS_VI).length}`);
