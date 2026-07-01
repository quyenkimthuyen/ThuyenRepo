import { LEVELS, TOPICS } from './lessons.js';

export const CUSTOM_LESSONS_KEY = 'reading-aloud-custom-lessons';

const LEVEL_IDS = new Set(LEVELS.map((l) => l.id));
const TOPIC_IDS = new Set(TOPICS.map((t) => t.id));

/**
 * @returns {import('./lessons.js').Lesson[]}
 */
export function loadCustomLessons() {
  try {
    const raw = localStorage.getItem(CUSTOM_LESSONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => normalizeLesson(item))
      .filter((item) => item !== null);
  } catch {
    return [];
  }
}

/**
 * @param {import('./lessons.js').Lesson[]} lessons
 */
export function saveCustomLessons(lessons) {
  const payload = lessons.map((lesson) => ({
    id: lesson.id,
    title: lesson.title,
    level: lesson.level,
    topic: lesson.topic,
    sentences: lesson.sentences,
    ...(lesson.translations?.length ? { translations: lesson.translations } : {}),
    custom: true,
    createdAt: lesson.createdAt ?? Date.now(),
  }));
  localStorage.setItem(CUSTOM_LESSONS_KEY, JSON.stringify(payload));
}

/**
 * @param {unknown} raw
 * @returns {import('./lessons.js').Lesson | null}
 */
export function normalizeLesson(raw) {
  if (!raw || typeof raw !== 'object') return null;

  const data = /** @type {Record<string, unknown>} */ (raw);
  const title = String(data.title ?? '').trim();
  const sentences = normalizeSentences(data.sentences ?? data.text ?? data.content);
  const translations = normalizeSentences(data.translations);

  if (!title || !sentences.length) return null;

  const level = LEVEL_IDS.has(String(data.level)) ? String(data.level) : 'b1';
  const topic = TOPIC_IDS.has(String(data.topic)) ? String(data.topic) : 'custom';

  const id =
    typeof data.id === 'string' && data.id.startsWith('custom-')
      ? data.id
      : generateLessonId(title);

  return {
    id,
    title,
    level,
    topic,
    sentences,
    ...(translations.length ? { translations } : {}),
    custom: true,
    createdAt: typeof data.createdAt === 'number' ? data.createdAt : Date.now(),
  };
}

/**
 * @param {unknown} value
 * @returns {string[]}
 */
export function normalizeSentences(value) {
  if (Array.isArray(value)) {
    return value.map((s) => String(s).trim()).filter(Boolean);
  }
  if (typeof value === 'string') {
    return sentencesFromText(value);
  }
  return [];
}

/**
 * @param {string} text
 * @returns {string[]}
 */
export function sentencesFromText(text) {
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

/**
 * @param {string} title
 * @returns {string}
 */
export function generateLessonId(title) {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40);
  return `custom-${slug || 'lesson'}-${Date.now().toString(36)}`;
}

/**
 * @param {{ title: string, sentences: string[], level?: string, topic?: string }} input
 * @returns {{ lesson: import('./lessons.js').Lesson | null, errors: string[] }}
 */
export function buildCustomLesson(input) {
  const errors = [];
  const title = input.title.trim();
  const sentences = normalizeSentences(input.sentences);

  if (!title) errors.push('Cần nhập tiêu đề bài.');
  if (!sentences.length) errors.push('Cần ít nhất một câu (mỗi dòng một câu).');

  if (errors.length) return { lesson: null, errors };

  const lesson = normalizeLesson({
    title,
    sentences,
    level: input.level,
    topic: input.topic ?? 'custom',
  });

  if (!lesson) {
    return { lesson: null, errors: ['Không thể tạo bài từ dữ liệu đã nhập.'] };
  }

  return { lesson, errors: [] };
}

/**
 * @param {string} text
 * @returns {{ lessons: import('./lessons.js').Lesson[], errors: string[] }}
 */
export function parseImportJson(text) {
  const errors = [];
  let data;

  try {
    data = JSON.parse(text);
  } catch {
    return { lessons: [], errors: ['JSON không hợp lệ.'] };
  }

  /** @type {unknown[]} */
  let items = [];
  if (Array.isArray(data)) {
    items = data;
  } else if (data && typeof data === 'object' && Array.isArray(data.lessons)) {
    items = data.lessons;
  } else if (data && typeof data === 'object') {
    items = [data];
  } else {
    return { lessons: [], errors: ['Định dạng JSON không được hỗ trợ.'] };
  }

  const lessons = [];
  items.forEach((item, index) => {
    const lesson = normalizeLesson(item);
    if (lesson) {
      lessons.push(lesson);
    } else {
      errors.push(`Bài #${index + 1}: thiếu tiêu đề hoặc câu hợp lệ.`);
    }
  });

  if (!lessons.length && !errors.length) {
    errors.push('Không tìm thấy bài hợp lệ trong file.');
  }

  return { lessons, errors };
}

/**
 * @param {import('./lessons.js').Lesson[]} lessons
 * @param {import('./lessons.js').Lesson} lesson
 * @returns {import('./lessons.js').Lesson[]}
 */
export function addCustomLesson(lessons, lesson) {
  return [...lessons, { ...lesson, custom: true }];
}

/**
 * @param {import('./lessons.js').Lesson[]} lessons
 * @param {string} id
 * @returns {import('./lessons.js').Lesson[]}
 */
export function removeCustomLesson(lessons, id) {
  return lessons.filter((l) => l.id !== id);
}
