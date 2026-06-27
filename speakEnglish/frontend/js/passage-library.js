/**
 * Thư viện đoạn văn — lưu localStorage, tái sử dụng sau
 */

import { splitIntoSentences } from './core.js';

export const PASSAGE_LIBRARY_KEY = 'pronouncelab_passage_library';
const LIBRARY_VERSION = 1;

function nowIso() {
  return new Date().toISOString();
}

export function createEmptyLibrary() {
  return { version: LIBRARY_VERSION, passages: [] };
}

export function loadPassageLibrary() {
  try {
    const raw = localStorage.getItem(PASSAGE_LIBRARY_KEY);
    if (!raw) return createEmptyLibrary();
    const data = JSON.parse(raw);
    if (!Array.isArray(data?.passages)) return createEmptyLibrary();
    return {
      version: LIBRARY_VERSION,
      passages: data.passages
        .filter((p) => p?.id && p?.name && p?.rawText)
        .map((p) => ({
          id: String(p.id),
          name: String(p.name).trim(),
          rawText: String(p.rawText).trim(),
          createdAt: p.createdAt || nowIso(),
          updatedAt: p.updatedAt || p.createdAt || nowIso(),
        })),
    };
  } catch {
    return createEmptyLibrary();
  }
}

export function savePassageLibrary(library) {
  localStorage.setItem(PASSAGE_LIBRARY_KEY, JSON.stringify({
    version: LIBRARY_VERSION,
    passages: library.passages || [],
  }));
}

export function generatePassageId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `p_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function deriveDefaultPassageName(rawText) {
  const first = splitIntoSentences(rawText)[0] || String(rawText || '').trim();
  if (!first) return 'Đoạn văn mới';
  const short = first.length > 48 ? `${first.slice(0, 45)}…` : first;
  return short.replace(/\s+/g, ' ');
}

export function upsertPassage(library, { id, name, rawText }) {
  const text = String(rawText || '').trim();
  const label = String(name || '').trim() || deriveDefaultPassageName(text);
  if (!text) return { library, passage: null };

  const existingIdx = id
    ? library.passages.findIndex((p) => p.id === id)
    : -1;
  const stamp = nowIso();

  if (existingIdx >= 0) {
    const updated = {
      ...library.passages[existingIdx],
      name: label,
      rawText: text,
      updatedAt: stamp,
    };
    library.passages[existingIdx] = updated;
    savePassageLibrary(library);
    return { library, passage: updated };
  }

  const created = {
    id: id || generatePassageId(),
    name: label,
    rawText: text,
    createdAt: stamp,
    updatedAt: stamp,
  };
  library.passages.unshift(created);
  savePassageLibrary(library);
  return { library, passage: created };
}

export function deletePassage(library, id) {
  library.passages = library.passages.filter((p) => p.id !== id);
  savePassageLibrary(library);
  return library;
}

export function getPassageById(library, id) {
  return library.passages.find((p) => p.id === id) ?? null;
}

export function formatPassageMeta(passage) {
  const count = splitIntoSentences(passage.rawText).length;
  const date = new Date(passage.updatedAt || passage.createdAt);
  const dateLabel = Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
  return { sentenceCount: count, dateLabel };
}
