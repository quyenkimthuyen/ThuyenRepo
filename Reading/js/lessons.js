import { LESSON_INDEX } from './lessonIndex.js';
import { LEVELS, TOPICS, DEFAULT_PRELOAD_TOPIC } from './lessonMeta.js';

/** @typedef {{ id: string, level: string, topic: string, title: string, sentences: string[], translations?: string[], custom?: boolean }} Lesson */

/** @type {Map<string, Lesson[]>} */
const topicCache = new Map();

/** @type {Map<string, Promise<Lesson[]>>} */
const topicLoading = new Map();

const TOPIC_IDS = TOPICS.filter((t) => t.id !== 'custom').map((t) => t.id);

/**
 * @param {string} topicId
 * @returns {Promise<Lesson[]>}
 */
function importTopicChunk(topicId) {
  switch (topicId) {
    case 'daily':
      return import('./chunks/daily.js').then((m) => m.TOPIC_LESSONS);
    case 'travel':
      return import('./chunks/travel.js').then((m) => m.TOPIC_LESSONS);
    case 'work':
      return import('./chunks/work.js').then((m) => m.TOPIC_LESSONS);
    case 'study':
      return import('./chunks/study.js').then((m) => m.TOPIC_LESSONS);
    case 'ielts':
      return import('./chunks/ielts.js').then((m) => m.TOPIC_LESSONS);
    case 'health':
      return import('./chunks/health.js').then((m) => m.TOPIC_LESSONS);
    case 'tech':
      return import('./chunks/tech.js').then((m) => m.TOPIC_LESSONS);
    case 'society':
      return import('./chunks/society.js').then((m) => m.TOPIC_LESSONS);
    case 'food':
      return import('./chunks/food.js').then((m) => m.TOPIC_LESSONS);
    case 'sports':
      return import('./chunks/sports.js').then((m) => m.TOPIC_LESSONS);
    case 'communication':
      return import('./chunks/communication.js').then((m) => m.TOPIC_LESSONS);
    case 'toeic':
      return import('./chunks/toeic.js').then((m) => m.TOPIC_LESSONS);
    default:
      return Promise.resolve([]);
  }
}

/**
 * @param {string} topicId
 * @returns {Promise<Lesson[]>}
 */
export function loadTopicLessons(topicId) {
  if (topicCache.has(topicId)) {
    return Promise.resolve(topicCache.get(topicId));
  }
  if (topicLoading.has(topicId)) {
    return topicLoading.get(topicId);
  }
  const promise = importTopicChunk(topicId).then((lessons) => {
    topicCache.set(topicId, lessons);
    topicLoading.delete(topicId);
    return lessons;
  });
  topicLoading.set(topicId, promise);
  return promise;
}

/**
 * @param {string[]} topicIds
 * @returns {Promise<void>}
 */
export async function preloadTopics(topicIds) {
  const unique = [...new Set(topicIds.filter((id) => TOPIC_IDS.includes(id)))];
  await Promise.all(unique.map(loadTopicLessons));
}

/** @returns {Promise<void>} */
export function preloadDefaultTopic() {
  return loadTopicLessons(DEFAULT_PRELOAD_TOPIC);
}

/**
 * @param {string} topicFilter
 * @param {string} levelFilter
 * @returns {string[] | null} null = load per lesson on demand
 */
export function topicsToPreload(topicFilter, levelFilter) {
  if (topicFilter !== 'all') return [topicFilter];
  if (levelFilter !== 'all') {
    return [
      ...new Set(
        LESSON_INDEX.filter((l) => l.level === levelFilter).map((l) => l.topic),
      ),
    ];
  }
  return null;
}

/**
 * @param {string} topicFilter
 * @param {string} levelFilter
 * @returns {Promise<void>}
 */
export async function preloadForFilters(topicFilter, levelFilter) {
  const topics = topicsToPreload(topicFilter, levelFilter);
  if (topics) {
    await preloadTopics(topics);
  }
}

/**
 * @returns {Lesson[]}
 */
export function getCachedLessons() {
  const out = [];
  for (const lessons of topicCache.values()) {
    out.push(...lessons);
  }
  return out;
}

/**
 * @param {string} lessonId
 * @returns {Promise<Lesson | undefined>}
 */
export async function getLessonById(lessonId) {
  const meta = LESSON_INDEX.find((l) => l.id === lessonId);
  if (!meta) return undefined;
  const lessons = await loadTopicLessons(meta.topic);
  return lessons.find((l) => l.id === lessonId);
}

/**
 * @param {{ topic?: string, level?: string }} filters
 * @param {Array<{ id: string, level: string, topic: string, title: string, custom?: boolean }>} [source]
 */
export function filterLessons(filters = {}, source = LESSON_INDEX) {
  return source.filter((lesson) => {
    if (filters.topic && filters.topic !== 'all' && lesson.topic !== filters.topic) {
      return false;
    }
    if (filters.level && filters.level !== 'all' && lesson.level !== filters.level) {
      return false;
    }
    return true;
  });
}

/**
 * @param {string} levelId
 */
export function getLessonsByLevel(levelId) {
  return LESSON_INDEX.filter((l) => l.level === levelId);
}

/**
 * @param {string} topicId
 */
export function getLessonsByTopic(topicId) {
  return LESSON_INDEX.filter((l) => l.topic === topicId);
}

export { LEVELS, TOPICS, DEFAULT_PRELOAD_TOPIC } from './lessonMeta.js';
export { LESSON_INDEX };

/** @deprecated Use LESSON_INDEX for listings; load chunks for full content. */
export const LESSONS = LESSON_INDEX;

/**
 * @param {string} levelId
 * @returns {string}
 */
export function getLevelLabel(levelId) {
  return LEVELS.find((l) => l.id === levelId)?.label ?? levelId.toUpperCase();
}

/**
 * @param {string} topicId
 * @returns {string}
 */
export function getTopicLabel(topicId) {
  return TOPICS.find((t) => t.id === topicId)?.label ?? topicId;
}
