import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { LESSONS } from '../js/lessons.js';
import { LESSON_BANK } from './lessonBankData.mjs';
import { A2_BANK } from './banks/a2.mjs';
import { B1_BANK } from './banks/b1.mjs';
import { B2_BANK } from './banks/b2.mjs';
import { C1_BANK } from './banks/c1.mjs';

const BANKS = {
  a1: LESSON_BANK.a1,
  a2: A2_BANK,
  b1: B1_BANK,
  b2: B2_BANK,
  c1: C1_BANK,
};

const TOPICS = ['daily', 'travel', 'work', 'study', 'health', 'tech', 'society'];
const TARGET = 10;

function slugify(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function existingCount(level, topic) {
  return LESSONS.filter((l) => l.level === level && l.topic === topic).length;
}

function existingIds() {
  return new Set(LESSONS.map((l) => l.id));
}

const supplement = [];
const ids = existingIds();

for (const [level, topics] of Object.entries(BANKS)) {
  for (const topic of TOPICS) {
    const bank = topics[topic] ?? [];
    const need = TARGET - existingCount(level, topic);
    if (need <= 0) continue;
    if (bank.length < need) {
      throw new Error(`${level}/${topic}: bank has ${bank.length}, need ${need}`);
    }
    for (let i = 0; i < need; i++) {
      const item = bank[i];
      let id = `${level}-${topic}-${slugify(item.title)}`;
      let n = 2;
      while (ids.has(id)) {
        id = `${level}-${topic}-${slugify(item.title)}-${n}`;
        n += 1;
      }
      ids.add(id);
      supplement.push({
        id,
        level,
        topic,
        title: item.title,
        sentences: item.sentences,
      });
    }
  }
}

const out = `/** Auto-generated supplement lessons — do not edit by hand */\nexport const SUPPLEMENT_LESSONS = ${JSON.stringify(supplement, null, 2)};\n`;

const root = dirname(fileURLToPath(import.meta.url));
writeFileSync(join(root, '../js/supplementLessons.js'), out);

console.log(`Generated ${supplement.length} supplement lessons`);

for (const level of Object.keys(BANKS)) {
  for (const topic of TOPICS) {
    const total =
      existingCount(level, topic) +
      supplement.filter((l) => l.level === level && l.topic === topic).length;
    if (total !== TARGET) {
      console.error(`MISMATCH ${level}/${topic}: ${total}`);
    }
  }
}
