import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeWord,
  normalizeTextForMatch,
  wordsMatch,
  wordsMatchExact,
  textMatchExact,
  textMatchPractice,
  textMatchWithThreshold,
  textSimilarityPercent,
  similarityPercent,
  collapseConsecutiveTokens,
  extractSpokenWord,
  extractSpokenText,
  expandTokenSpellingVariants,
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

describe('textMatchExact', () => {
  it('single word exact', () => {
    assert.equal(textMatchExact('hello', 'hello'), true);
    assert.equal(textMatchExact('Hello', 'hello'), true);
  });

  it('rejects fuzzy or extra words for single target', () => {
    assert.equal(textMatchExact('helo', 'hello'), false);
    assert.equal(textMatchExact('say hello', 'hello'), false);
  });

  it('matches multi-word phrases', () => {
    assert.equal(textMatchExact('living room', 'living room'), true);
    assert.equal(textMatchExact('Living Room', 'living room'), true);
    assert.equal(textMatchExact('police officer', 'police officer'), true);
  });

  it('rejects partial phrase', () => {
    assert.equal(textMatchExact('room', 'living room'), false);
    assert.equal(textMatchExact('living', 'living room'), false);
    assert.equal(textMatchExact('the living room', 'living room'), false);
  });

  it('accepts BrE/AmE spelling variants', () => {
    assert.equal(textMatchExact('livable', 'liveable'), true);
    assert.equal(textMatchExact('liveable', 'livable'), true);
    assert.equal(textMatchExact('organize', 'organise'), true);
    assert.equal(textMatchExact('color', 'colour'), true);
  });

  it('still rejects real mispronunciation spellings', () => {
    assert.equal(textMatchExact('livible', 'liveable'), false);
    assert.equal(textMatchExact('livebel', 'liveable'), false);
  });
});

describe('textMatchPractice', () => {
  it('keeps strict exact behaviour', () => {
    assert.equal(textMatchPractice('timetable', 'timetable'), true);
    assert.equal(textMatchPractice('living room', 'living room'), true);
  });

  it('rejects say + target (not isolated word)', () => {
    assert.equal(textMatchPractice('say hello', 'hello'), false);
  });

  it('accepts SR duplicate tail', () => {
    assert.equal(textMatchPractice('timetable timetable', 'timetable'), true);
    assert.equal(textMatchPractice('tito timetable timetable', 'timetable'), true);
  });

  it('accepts article prefix for phrases', () => {
    assert.equal(textMatchPractice('the living room', 'living room'), true);
    assert.equal(textMatchPractice('the timetable', 'timetable'), true);
  });

  it('rejects partial phrase', () => {
    assert.equal(textMatchPractice('room', 'living room'), false);
    assert.equal(textMatchPractice('tito room', 'timetable'), false);
  });

  it('accepts SR merged phrase token for spaced target', () => {
    assert.equal(textMatchPractice('vietnam', 'Viet Nam'), true);
    assert.equal(textMatchPractice('viet nam', 'Viet Nam'), true);
    assert.equal(
      textMatchPractice(
        'vietnam vietnam vietnam vietnam vape nam vietnam vietnam vietnam vietnam vietnam',
        'Viet Nam',
      ),
      true,
    );
    assert.equal(textMatchPractice('vietnamese', 'Viet Nam'), false);
  });
});

describe('textMatchWithThreshold', () => {
  it('100% keeps practice-only pass', () => {
    assert.equal(textMatchWithThreshold('timetable', 'timetable', 100), true);
    assert.equal(textMatchWithThreshold('there', 'their', 100), false);
  });

  it('lower threshold allows near homophones', () => {
    assert.equal(textMatchWithThreshold('there', 'their', 60), true);
    assert.equal(textMatchWithThreshold('meet', 'meat', 75), true);
  });

  it('rejects clearly different words', () => {
    assert.equal(textMatchWithThreshold('world', 'hello', 80), false);
  });
});

describe('textSimilarityPercent', () => {
  it('returns 100 on practice match', () => {
    assert.equal(textSimilarityPercent('tito timetable timetable', 'timetable'), 100);
  });

  it('scores homophone pairs below 100', () => {
    assert.ok(textSimilarityPercent('there', 'their') >= 50);
    assert.ok(textSimilarityPercent('there', 'their') < 100);
  });
});

describe('expandTokenSpellingVariants', () => {
  it('links liveable and livable', () => {
    const liveable = expandTokenSpellingVariants('liveable');
    const livable = expandTokenSpellingVariants('livable');
    assert.ok(liveable.has('livable'));
    assert.ok(livable.has('liveable'));
  });
});

describe('wordsMatchExact', () => {
  it('aliases textMatchExact', () => {
    assert.equal(wordsMatchExact('hello', 'hello'), true);
    assert.equal(wordsMatchExact('living room', 'living room'), true);
  });
});

describe('extractSpokenText', () => {
  it('merges final and interim into phrase', () => {
    assert.equal(extractSpokenText('living ', 'living room'), 'living room');
    assert.equal(extractSpokenText('police ', 'officer'), 'police officer');
  });

  it('returns full line for sentence-ready matching', () => {
    assert.equal(extractSpokenText('I like ', 'apples'), 'i like apples');
  });

  it('empty input', () => {
    assert.equal(extractSpokenText('', ''), '');
  });
});

describe('extractSpokenWord', () => {
  it('returns last token from phrase', () => {
    assert.equal(extractSpokenWord('living room', ''), 'room');
    assert.equal(extractSpokenWord('i said ', 'hello'), 'hello');
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
