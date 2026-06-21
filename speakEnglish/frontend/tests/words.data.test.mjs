import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { validateWordsJson } from '../js/core.js';

const dir = dirname(fileURLToPath(import.meta.url));
const wordsPath = join(dir, '../data/words.json');

describe('words.json schema', () => {
  const data = JSON.parse(readFileSync(wordsPath, 'utf8'));

  it('has no validation errors', () => {
    const errors = validateWordsJson(data);
    assert.deepEqual(errors, []);
  });

  it('has at least 20 demo words', () => {
    assert.ok(data.words.length >= 20);
  });

  it('each word has unique id', () => {
    const words = data.words.map((w) => w.word);
    assert.equal(new Set(words).size, words.length);
  });
});
