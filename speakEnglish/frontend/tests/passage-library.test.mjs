import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  PASSAGE_LIBRARY_KEY,
  createEmptyLibrary,
  upsertPassage,
  deletePassage,
  getPassageById,
  deriveDefaultPassageName,
  formatPassageMeta,
} from '../js/passage-library.js';

function installLocalStorageMock() {
  const store = new Map();
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => { store.set(key, String(value)); },
    removeItem: (key) => { store.delete(key); },
    clear: () => { store.clear(); },
  };
}

describe('passage library', () => {
  beforeEach(() => {
    installLocalStorageMock();
    localStorage.removeItem(PASSAGE_LIBRARY_KEY);
  });

  afterEach(() => {
    localStorage.removeItem(PASSAGE_LIBRARY_KEY);
  });

  it('derives default name from first sentence', () => {
    const name = deriveDefaultPassageName('Hello world. Next sentence.');
    assert.equal(name, 'Hello world.');
  });

  it('upserts and retrieves passages', () => {
    let library = createEmptyLibrary();
    const first = upsertPassage(library, {
      name: 'Morning',
      rawText: 'The sun rises. Birds sing.',
    });
    library = first.library;
    assert.equal(library.passages.length, 1);
    assert.equal(getPassageById(library, first.passage.id)?.name, 'Morning');

    const second = upsertPassage(library, {
      id: first.passage.id,
      name: 'Morning updated',
      rawText: 'The sun rises. Birds sing.',
    });
    library = second.library;
    assert.equal(library.passages.length, 1);
    assert.equal(library.passages[0].name, 'Morning updated');
  });

  it('deletes passage by id', () => {
    let library = createEmptyLibrary();
    const { library: withItem, passage } = upsertPassage(library, {
      name: 'Test',
      rawText: 'One. Two.',
    });
    library = deletePassage(withItem, passage.id);
    assert.equal(library.passages.length, 0);
  });

  it('formats metadata with sentence count', () => {
    const meta = formatPassageMeta({
      rawText: 'A. B. C.',
      createdAt: '2026-01-01T00:00:00.000Z',
      updatedAt: '2026-01-02T00:00:00.000Z',
    });
    assert.equal(meta.sentenceCount, 3);
    assert.match(meta.dateLabel, /2026/);
  });
});
