/**
 * Vocabulary manifest + topic quiz session.
 */

const MANIFEST_URL = 'data/vocabulary/manifest.json';
const topicCache = new Map();

export function pickRandom(items, count) {
  const pool = [...items];
  for (let i = pool.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, Math.min(count, pool.length));
}

export async function loadManifest() {
  const res = await fetch(MANIFEST_URL);
  if (!res.ok) throw new Error(`manifest HTTP ${res.status}`);
  return res.json();
}

export async function loadTopicWords(topicId) {
  if (!topicId) return [];
  if (topicCache.has(topicId)) return topicCache.get(topicId);

  const res = await fetch(`data/vocabulary/topics/${topicId}.json`);
  if (!res.ok) throw new Error(`topic HTTP ${res.status}`);
  const data = await res.json();
  const words = Array.isArray(data.words) ? data.words : [];
  topicCache.set(topicId, words);
  return words;
}

export function validateWordEntry(w, i = 0) {
  const errors = [];
  if (!w?.word) errors.push(`words[${i}]: missing word`);
  if (!w?.ipa) errors.push(`words[${i}]: missing ipa`);
  if (!Array.isArray(w?.phonemes) || !w.phonemes.length) {
    errors.push(`words[${i}]: phonemes must be non-empty array`);
  }
  return errors;
}

export function validateManifest(data) {
  const errors = [];
  if (!data || typeof data !== 'object') return ['manifest must be object'];
  if (!Array.isArray(data.topics) || !data.topics.length) {
    errors.push('manifest.topics must be non-empty array');
  }
  return errors;
}

export async function buildQuizSession({ topicId, quizSize }) {
  const allWords = await loadTopicWords(topicId);
  if (!allWords.length) {
    throw new Error('Topic không có từ nào');
  }
  const words = pickRandom(allWords, quizSize);
  return {
    words,
    topicId,
    quizSize: words.length,
    totalInTopic: allWords.length,
  };
}
