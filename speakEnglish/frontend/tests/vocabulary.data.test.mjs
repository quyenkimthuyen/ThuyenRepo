import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  validateManifest,
  validateWordEntry,
  pickRandom,
} from '../js/vocabulary.js';

const dir = dirname(fileURLToPath(import.meta.url));
const manifestPath = join(dir, '../data/vocabulary/manifest.json');

describe('vocabulary manifest', () => {
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

  it('has no validation errors', () => {
    assert.deepEqual(validateManifest(manifest), []);
  });

  it('has topics with words', () => {
    assert.ok(manifest.topics.length >= 10);
    assert.ok(manifest.totalWords >= 1000);
    assert.equal(manifest.topicNaming, 'filename');
  });

  it('topic file words pass schema', () => {
    const topic = manifest.topics[0];
    const topicPath = join(dir, `../data/vocabulary/topics/${topic.id}.json`);
    const data = JSON.parse(readFileSync(topicPath, 'utf8'));
    assert.equal(data.topic, topic.id);
    assert.ok(data.words.length >= 5);
    const errors = data.words.flatMap((w, i) => validateWordEntry(w, i));
    assert.deepEqual(errors, []);
  });
});

describe('pickRandom', () => {
  const items = Array.from({ length: 50 }, (_, i) => i);

  it('returns at most count items', () => {
    assert.equal(pickRandom(items, 30).length, 30);
  });

  it('returns all when pool smaller than count', () => {
    assert.equal(pickRandom([1, 2, 3], 30).length, 3);
  });
});
