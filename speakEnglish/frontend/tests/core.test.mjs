import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeWord,
  wordsMatch,
  wordsMatchExact,
  extractSpokenWord,
  getSilenceMsFromSetting,
  getHangoverMs,
  canStartProcessing,
  createVadState,
  updateEnergyVad,
  buildUtteranceBlob,
  computeRms,
  isSpeaking,
  PROCESS_COOLDOWN_MS,
  MIN_SPEECH_MS,
  MAX_TEXT_RESPONSE_MS,
} from '../js/core.js';

describe('normalizeWord', () => {
  it('lowercases and strips punctuation', () => {
    assert.equal(normalizeWord('Hello!'), 'hello');
    assert.equal(normalizeWord("  Don't "), "don't");
  });
});

describe('wordsMatchExact', () => {
  it('requires exact normalized match', () => {
    assert.equal(wordsMatchExact('hello', 'hello'), true);
    assert.equal(wordsMatchExact('Hello', 'hello'), true);
  });

  it('rejects fuzzy or partial', () => {
    assert.equal(wordsMatchExact('helo', 'hello'), false);
    assert.equal(wordsMatchExact('say hello', 'hello'), false);
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

describe('energy VAD', () => {
  it('default hangover ~350ms', () => {
    assert.equal(getSilenceMsFromSetting(0.35), 350);
    assert.ok(getHangoverMs(0.35, true) <= 400);
  });

  it('detects speech start and end', () => {
    let state = createVadState();
    const hangover = 300;
    state = updateEnergyVad(state, 0.05, 1000, { hangoverMs: hangover });
    assert.equal(state.speechStarted, true);
    state = updateEnergyVad(state, 0.05, 1200, { hangoverMs: hangover });
    state = updateEnergyVad(state, 0.001, 1300, { hangoverMs: hangover });
    state = updateEnergyVad(state, 0.001, 1610, { hangoverMs: hangover });
    assert.equal(state.speechEnded, true);
  });

  it('ignores too-short bursts', () => {
    let state = createVadState();
    const hangover = 200;
    state = updateEnergyVad(state, 0.04, 0, { hangoverMs: hangover });
    state = updateEnergyVad(state, 0.001, 250, { hangoverMs: hangover });
    assert.equal(state.speechEnded, false);
  });

  it('processing cooldown', () => {
    assert.equal(canStartProcessing(0, 500, PROCESS_COOLDOWN_MS), true);
    assert.equal(canStartProcessing(100, 400, PROCESS_COOLDOWN_MS), false);
    assert.equal(canStartProcessing(100, 500, PROCESS_COOLDOWN_MS), true);
  });

  it('text hangover under latency budget', () => {
    assert.ok(getHangoverMs(0.35, true) + PROCESS_COOLDOWN_MS < MAX_TEXT_RESPONSE_MS);
  });
});

describe('buildUtteranceBlob', () => {
  it('returns null for empty', () => {
    assert.equal(buildUtteranceBlob([]), null);
  });

  it('merges chunks', () => {
    const b = buildUtteranceBlob([new Blob(['a']), new Blob(['b'])], 'audio/webm');
    assert.ok(b instanceof Blob);
    assert.equal(b.type, 'audio/webm');
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
