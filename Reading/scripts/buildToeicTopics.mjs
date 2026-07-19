import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const harkerDir = join(root, '../../Toeic/Harker2/public/data');
const outDir = join(root, '../js');

const LEVEL = 'c1';
const TOPIC = 'toeic';

/** @param {string} s */
function cleanText(s) {
  return s
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\bTEST\b[\s\d.]*1000\s*2[\s\d.]*/gi, '')
    .replace(/\s+\d{1,2}\s+(?=\d{1,2}\s)/g, ' ')
    .replace(/(?:^|\s)(?:\d{1,2}\s+){2,}\d{1,2}(?=\s|$)/g, ' ')
    .replace(/\s+\./g, '.')
    .trim();
}

/** @param {string} text */
function protectAbbreviations(text) {
  return text
    .replace(/([A-Z][a-z]{0,3})\./g, '$1\u0000')
    .replace(/\.\.\./g, '\u0001');
}

/** @param {string} text */
function unprotectAbbreviations(text) {
  return text.replace(/\u0000/g, '.').replace(/\u0001/g, '...');
}

/** @param {string} text */
function splitSentences(text) {
  const cleaned = cleanText(text);
  if (!cleaned) return [];
  const protectedText = protectAbbreviations(cleaned);
  const parts = protectedText
    .split(/(?<=[.!?])\s+(?=[A-Z"'(])/)
    .map(unprotectAbbreviations)
    .map((s) => s.trim())
    .filter((s) => s.length > 1);
  return parts.length ? parts : [cleaned];
}

/** @param {string} text */
function splitSpeakerTurns(text) {
  const cleaned = cleanText(text);
  if (!/(?:W\d*|M\d*):\s/i.test(cleaned)) {
    return splitSentences(cleaned);
  }
  return cleaned
    .split(/(?=(?:W\d*|M\d*):\s*)/i)
    .map((turn) => turn.replace(/^(?:W\d*|M\d*):\s*/i, '').trim())
    .filter(Boolean);
}

/**
 * @param {string[]} en
 * @param {string[]} vi
 * @returns {string[]}
 */
function alignTranslations(en, vi) {
  if (!vi.length) return en.map(() => '');
  if (en.length === vi.length) return vi;
  if (vi.length === 1) return en.map((_, i) => (i === 0 ? vi[0] : ''));
  const out = [];
  for (let i = 0; i < en.length; i += 1) {
    const start = Math.floor((i * vi.length) / en.length);
    const end = Math.floor(((i + 1) * vi.length) / en.length);
    out.push(vi.slice(start, end).join(' ') || vi[vi.length - 1]);
  }
  return out;
}

/**
 * @param {string} transcript
 * @param {string} [translation]
 */
function passageToSentences(transcript, translation = '') {
  const en = splitSpeakerTurns(transcript);
  const viRaw = splitSpeakerTurns(translation);
  const vi = alignTranslations(en, viRaw);
  return { en, vi };
}

/** @param {{ id: number, question?: string, translation?: string, answer?: string, options?: Record<string, string> }} q */
function isValidPart2Question(q) {
  const text = cleanText(q.question ?? '');
  if (!text || text.length < 10) return false;
  if (/^1000\s*2/i.test(text)) return false;
  if (/^TEST\b/i.test(text)) return false;
  if (!/[a-zA-Z]{3,}/.test(text)) return false;
  return true;
}

/** @param {string} translation @param {string} answerKey */
function extractPart2AnswerTranslation(translation, answerKey) {
  const text = cleanText(translation ?? '');
  if (!text || !answerKey) return '';

  const qIdx = text.indexOf('?');
  const rest = qIdx !== -1 ? text.slice(qIdx + 1).trim() : text.split(/(?<=[.!])\s+/).slice(1).join(' ');
  const optionParts = rest
    .split(/(?<=[.!])\s+/)
    .map((s) => cleanText(s))
    .filter(Boolean);
  const answerIdx = answerKey.toUpperCase().charCodeAt(0) - 'A'.charCodeAt(0);
  return optionParts[answerIdx] ?? '';
}

/** @param {{ question?: string, translation?: string, answer?: string, options?: Record<string, string> }} q */
function part2Pair(q) {
  const question = cleanText(q.question ?? '');
  const answer = cleanText(q.options?.[q.answer ?? ''] ?? '');
  const en = answer ? `${question} — ${answer}` : question;

  const text = cleanText(q.translation ?? '');
  const qIdx = text.indexOf('?');
  const qVi = qIdx !== -1
    ? text.slice(0, qIdx + 1).trim()
    : text.split(/(?<=[.!])\s+/).map((s) => s.trim()).filter(Boolean)[0] ?? text;
  const aVi = extractPart2AnswerTranslation(q.translation ?? '', q.answer ?? '');
  const vi = aVi ? `${qVi} — ${aVi}` : qVi;
  return { en, vi };
}

/**
 * @param {Array<{ id: number, question?: string, translation?: string, answer?: string, options?: Record<string, string> }>} questions
 */
function part2ToSentences(questions) {
  const seen = new Set();
  const en = [];
  const vi = [];
  const sorted = [...questions]
    .filter(isValidPart2Question)
    .sort((a, b) => a.id - b.id);

  for (const q of sorted) {
    const question = cleanText(q.question ?? '');
    if (seen.has(question)) continue;
    seen.add(question);
    const pair = part2Pair(q);
    en.push(pair.en);
    vi.push(pair.vi);
  }
  return { en, vi };
}

/** @type {Array<{ id: string, level: string, topic: string, title: string, sentences: string[] }>} */
const lessons = [];
/** @type {Record<string, string[]>} */
const translations = {};

for (let testNum = 1; testNum <= 10; testNum += 1) {
  const file = join(harkerDir, `test${String(testNum).padStart(2, '0')}.json`);
  const test = JSON.parse(readFileSync(file, 'utf8'));
  const testLabel = `Test ${String(testNum).padStart(2, '0')}`;
  const testKey = String(testNum).padStart(2, '0');

  const part2Questions = test.parts?.['2']?.questions ?? [];
  const part2 = part2ToSentences(part2Questions);
  if (part2.en.length) {
    const id = `${LEVEL}-${TOPIC}-t${testKey}-p2`;
    lessons.push({
      id,
      level: LEVEL,
      topic: TOPIC,
      title: `${testLabel} · Part 2 — Response Questions`,
      sentences: part2.en,
    });
    translations[id] = part2.vi;
  }

  for (const part of [3, 4]) {
    const partData = test.parts?.[String(part)];
    const passages = partData?.passages ?? [];
    const partLabel = part === 3 ? 'Part 3' : 'Part 4';
    const unitLabel = part === 3 ? 'Dialogue' : 'Talk';

    passages.forEach((passage, index) => {
      if (!passage.transcript) return;
      const { en, vi } = passageToSentences(passage.transcript, passage.translation ?? '');
      if (!en.length) return;

      const num = String(index + 1).padStart(2, '0');
      const id = `${LEVEL}-${TOPIC}-t${String(testNum).padStart(2, '0')}-p${part}-d${num}`;
      const title = `${testLabel} · ${partLabel} — ${unitLabel} ${index + 1}`;

      lessons.push({
        id,
        level: LEVEL,
        topic: TOPIC,
        title,
        sentences: en,
      });
      translations[id] = vi;
    });
  }
}

writeFileSync(
  join(outDir, 'toeicLessons.js'),
  `/** Auto-generated TOEIC Listening lessons from Hacker Vol.2 — do not edit by hand */\nexport const TOEIC_LESSONS = ${JSON.stringify(lessons, null, 2)};\n`,
);

writeFileSync(
  join(outDir, 'toeicTranslations.js'),
  `/** Auto-generated TOEIC Listening translations — do not edit by hand */\nexport const TOEIC_TRANSLATIONS = ${JSON.stringify(translations, null, 2)};\n`,
);

console.log(`Generated ${lessons.length} TOEIC lessons (level ${LEVEL})`);
const byPart = { 2: 0, 3: 0, 4: 0 };
for (const lesson of lessons) {
  if (lesson.id.includes('-p2')) byPart[2] += 1;
  if (lesson.id.includes('-p3-')) byPart[3] += 1;
  if (lesson.id.includes('-p4-')) byPart[4] += 1;
}
console.log(`  Part 2: ${byPart[2]}, Part 3: ${byPart[3]}, Part 4: ${byPart[4]}`);
