import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { BUNDLED_LESSONS } from '../js/lessonsBundled.js';
import { BUNDLED_TRANSLATIONS } from '../js/lessonTranslationsBundled.js';
import { TOPICS } from '../js/lessonMeta.js';

const root = dirname(fileURLToPath(import.meta.url));
const chunksDir = join(root, '../js/chunks');
const transDir = join(chunksDir, 'translations');

mkdirSync(transDir, { recursive: true });

const topicIds = TOPICS.filter((t) => t.id !== 'custom').map((t) => t.id);

/** @type {Record<string, typeof LESSONS>} */
const byTopic = {};
for (const topicId of topicIds) {
  byTopic[topicId] = BUNDLED_LESSONS.filter((l) => l.topic === topicId);
}

const index = BUNDLED_LESSONS.map(({ id, level, topic, title, custom }) => ({
  id,
  level,
  topic,
  title,
  ...(custom ? { custom: true } : {}),
}));

writeFileSync(
  join(root, '../js/lessonIndex.js'),
  `/** Auto-generated lesson index (metadata only) */\nexport const LESSON_INDEX = ${JSON.stringify(index, null, 2)};\n`,
);

for (const topicId of topicIds) {
  const lessons = byTopic[topicId];
  writeFileSync(
    join(chunksDir, `${topicId}.js`),
    `/** Auto-generated — ${topicId} lessons */\nexport const TOPIC_LESSONS = ${JSON.stringify(lessons, null, 2)};\n`,
  );

  /** @type {Record<string, string[]>} */
  const topicTranslations = {};
  for (const lesson of lessons) {
    const vi = BUNDLED_TRANSLATIONS[lesson.id];
    if (vi?.length) topicTranslations[lesson.id] = vi;
  }

  writeFileSync(
    join(transDir, `${topicId}.js`),
    `/** Auto-generated — ${topicId} translations */\nexport const TOPIC_TRANSLATIONS = ${JSON.stringify(topicTranslations, null, 2)};\n`,
  );
}

console.log(`Index: ${index.length} lessons`);
for (const topicId of topicIds) {
  console.log(`  ${topicId}: ${byTopic[topicId].length} lessons`);
}
