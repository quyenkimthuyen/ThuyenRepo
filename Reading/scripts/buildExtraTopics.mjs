import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { FOOD_LESSONS } from './banks/extraTopics/food.mjs';
import { SPORTS_LESSONS } from './banks/extraTopics/sports.mjs';
import { COMMUNICATION_LESSONS } from './banks/extraTopics/communication.mjs';

const LEVELS = ['a1', 'a2', 'b1', 'b2', 'c1'];

const TOPIC_BANKS = {
  food: FOOD_LESSONS,
  sports: SPORTS_LESSONS,
  communication: COMMUNICATION_LESSONS,
};

function slugify(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/** @type {import('../js/lessons.js').Lesson[]} */
const lessons = [];
/** @type {Record<string, string[]>} */
const translations = {};
const ids = new Set();

for (const [topic, levelBank] of Object.entries(TOPIC_BANKS)) {
  for (const level of LEVELS) {
    const items = levelBank[level] ?? [];
    if (items.length !== 10) {
      throw new Error(`${topic}/${level}: expected 10 lessons, got ${items.length}`);
    }
    for (const item of items) {
      if (item.sentences.length !== item.vi.length) {
        throw new Error(`${topic}/${level}/${item.title}: sentence count mismatch`);
      }
      let id = `${level}-${topic}-${slugify(item.title)}`;
      let n = 2;
      while (ids.has(id)) {
        id = `${level}-${topic}-${slugify(item.title)}-${n}`;
        n += 1;
      }
      ids.add(id);
      lessons.push({
        id,
        level,
        topic,
        title: item.title,
        sentences: item.sentences,
      });
      translations[id] = item.vi;
    }
  }
}

const root = dirname(fileURLToPath(import.meta.url));

writeFileSync(
  join(root, '../js/extraTopicLessons.js'),
  `/** Auto-generated extra topic lessons — do not edit by hand */\nexport const EXTRA_TOPIC_LESSONS = ${JSON.stringify(lessons, null, 2)};\n`,
);

writeFileSync(
  join(root, '../js/extraTopicTranslations.js'),
  `/** Auto-generated extra topic translations — do not edit by hand */\nexport const EXTRA_TOPIC_TRANSLATIONS = ${JSON.stringify(translations, null, 2)};\n`,
);

console.log(`Generated ${lessons.length} extra topic lessons`);
console.log(`Generated ${Object.keys(translations).length} translations`);

for (const topic of Object.keys(TOPIC_BANKS)) {
  for (const level of LEVELS) {
    const count = lessons.filter((l) => l.topic === topic && l.level === level).length;
    if (count !== 10) {
      console.error(`MISMATCH ${topic}/${level}: ${count}`);
    }
  }
}
