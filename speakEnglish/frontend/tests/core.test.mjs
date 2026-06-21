import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeWord,
  wordsMatch,
  extractSpokenWord,
  getSilenceMsFromSetting,
  getSilenceMsForMode,
  getFastProcessDelay,
  getBlockMsFromSetting,
  msUntilNextBlock,
  shouldProcessBlock,
  computeRms,
  isSpeaking,
  TEXT_FAST_MS,
  SCORE_FAST_MS,
  DEFAULT_BLOCK_SEC,
  MAX_TEXT_RESPONSE_MS,
  MAX_SCORE_RESPONSE_MS,
} from '../js/core.js';

describe('normalizeWord', () => {
  it('lowercases and strips punctuation', () => {
    assert.equal(normalizeWord('Hello!'), 'hello');
    assert.equal(normalizeWord("  Don't "), "don't");
  });
});

describe('wordsMatch', () => {
  it('exact match', () => {
    assert.equal(wordsMatch('hello', 'hello'), true);
  });

  it('case insensitive', () => {
    assert.equal(wordsMatch('Hello', 'hello'), true);
  });

  it('substring match', () => {
    assert.equal(wordsMatch('say hello', 'hello'), true);
  });

  it('fuzzy match within 2 edits', () => {
    assert.equal(wordsMatch('helo', 'hello'), true);
    assert.equal(wordsMatch('hellu', 'hello'), true);
  });

  it('reject clearly wrong', () => {
    assert.equal(wordsMatch('world', 'hello'), false);
    assert.equal(wordsMatch('xyzab', 'hello'), false);
  });
});

describe('extractSpokenWord', () => {
  it('returns last token', () => {
    assert.equal(extractSpokenWord('i said ', 'hello'), 'hello');
    assert.equal(extractSpokenWord('hello ', ''), 'hello');
  });

  it('empty input', () => {
    assert.equal(extractSpokenWord('', ''), '');
  });
});

describe('block processor timing', () => {
  it('default 2s block', () => {
    assert.equal(getBlockMsFromSetting(2), 2000);
    assert.equal(getBlockMsFromSetting(undefined), DEFAULT_BLOCK_SEC * 1000);
  });

  it('clamps block range', () => {
    assert.equal(getBlockMsFromSetting(0.1), 500);
    assert.equal(getBlockMsFromSetting(99), 10000);
  });

  it('countdown until next block', () => {
    const start = 1000;
    const blockMs = 2000;
    assert.equal(msUntilNextBlock(1500, start, blockMs), 1500);
    assert.equal(msUntilNextBlock(3000, start, blockMs), 0);
  });

  it('shouldProcessBlock requires signal', () => {
    assert.equal(shouldProcessBlock({ hadSpeech: false, hasText: false, hasAudio: false }), false);
    assert.equal(shouldProcessBlock({ hadSpeech: true, hasText: false, hasAudio: false }), true);
    assert.equal(shouldProcessBlock({ hadSpeech: false, hasText: true, hasAudio: false }), true);
  });
});

describe('silence timing (legacy helpers)', () => {
  it('default 0.5s silence', () => {
    assert.equal(getSilenceMsFromSetting(0.5), 500);
  });

  it('text mode caps at 500ms', () => {
    assert.equal(getSilenceMsForMode(1.0, true), 500);
  });

  it('score mode caps at 700ms', () => {
    assert.equal(getSilenceMsForMode(1.0, false), 700);
  });

  it('fast path text final under budget', () => {
    assert.ok(getFastProcessDelay(true, true, 0.5) <= MAX_TEXT_RESPONSE_MS);
  });

  it('fast path score final under budget', () => {
    assert.ok(getFastProcessDelay(false, true, 0.5) <= MAX_SCORE_RESPONSE_MS);
  });

  it('text final faster than score', () => {
    assert.ok(TEXT_FAST_MS < SCORE_FAST_MS);
  });
});

describe('VAD computeRms', () => {
  it('silence near zero', () => {
    const silent = new Uint8Array(128).fill(128);
    assert.ok(computeRms(silent) < 0.01);
  });

  it('detects synthetic signal', () => {
    const buf = new Uint8Array(256);
    for (let i = 0; i < buf.length; i++) {
      buf[i] = 128 + Math.sin(i / 4) * 40;
    }
    assert.ok(isSpeaking(computeRms(buf)));
  });
});
