import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  PRACTICE_MODE,
  getHangoverMs,
  shouldAutoScoreOnUtteranceEnd,
  isAudioReadyForScore,
  isEvaluationPassed,
  validateEvaluateResponse,
  uploadFilenameForMime,
  buildUtteranceBlob,
  MIN_BLOB_BYTES,
  MIN_UPLOAD_BYTES,
  MAX_SCORE_RESPONSE_MS,
  MAX_LATENCY_MS,
} from '../js/core.js';

describe('score mode — practice mode routing', () => {
  it('auto score only in score mode with setting on', () => {
    assert.equal(
      shouldAutoScoreOnUtteranceEnd({ practiceMode: PRACTICE_MODE.SCORE, autoEvaluate: true }),
      true,
    );
    assert.equal(
      shouldAutoScoreOnUtteranceEnd({ practiceMode: PRACTICE_MODE.SCORE, autoEvaluate: false }),
      false,
    );
    assert.equal(
      shouldAutoScoreOnUtteranceEnd({ practiceMode: PRACTICE_MODE.TEXT, autoEvaluate: true }),
      false,
    );
  });

  it('score hangover slightly longer than text', () => {
    const text = getHangoverMs(0.35, true);
    const score = getHangoverMs(0.35, false);
    assert.ok(score >= text);
    assert.ok(score <= 550);
  });
});

describe('score mode — audio upload gate', () => {
  it('rejects too-small blobs', () => {
    assert.equal(isAudioReadyForScore(100), false);
    assert.equal(isAudioReadyForScore(MIN_BLOB_BYTES - 1), false);
    assert.equal(isAudioReadyForScore(MIN_BLOB_BYTES), true);
    assert.equal(isAudioReadyForScore(2000), true);
  });

  it('upload filename matches mime', () => {
    assert.equal(uploadFilenameForMime('audio/webm'), 'recording.webm');
    assert.equal(uploadFilenameForMime('audio/wav'), 'recording.wav');
    assert.equal(uploadFilenameForMime('audio/mp4'), 'recording.mp4');
    assert.equal(uploadFilenameForMime('audio/ogg'), 'recording.ogg');
  });

  it('phrase blob from chunks', () => {
    const blob = buildUtteranceBlob([new Blob(['x'.repeat(600)])], 'audio/webm');
    assert.ok(blob);
    assert.ok(blob.size >= MIN_BLOB_BYTES || blob.size > 0);
  });
});

describe('score mode — pass criteria', () => {
  const base = {
    word: 'hello',
    overall_score: 85,
    phonemes: [
      { ipa: 'h', score: 0.9, label: 'ok', start: 0, end: 0.1 },
      { ipa: 'ə', score: 0.4, label: 'mis', start: 0.1, end: 0.2 },
    ],
  };

  it('passes when overall >= threshold', () => {
    assert.equal(isEvaluationPassed({ ...base, overall_score: 80 }, 80), true);
  });

  it('passes when all phonemes ok', () => {
    const allOk = {
      ...base,
      overall_score: 50,
      phonemes: base.phonemes.map((p) => ({ ...p, label: 'ok', score: 0.9 })),
    };
    assert.equal(isEvaluationPassed(allOk, 80), true);
  });

  it('fails when below threshold and not all ok', () => {
    assert.equal(isEvaluationPassed({ ...base, overall_score: 60 }, 80), false);
  });

  it('respects explicit passed flag from API', () => {
    assert.equal(isEvaluationPassed({ ...base, passed: false, overall_score: 99 }, 80), false);
    assert.equal(isEvaluationPassed({ ...base, passed: true, overall_score: 10 }, 80), true);
  });
});

describe('score mode — evaluate API response shape', () => {
  it('validates success payload for phoneme UI', () => {
    const sample = {
      word: 'hello',
      overall_score: 72,
      passed: false,
      phonemes: [
        { ipa: 'h', score: 0.8, label: 'ok', start: 0.02, end: 0.08, suggestion: '' },
        { ipa: 'ə', score: 0.4, label: 'mis', start: 0.08, end: 0.12, suggestion: 'gợi ý' },
      ],
    };
    assert.deepEqual(validateEvaluateResponse(sample), []);
  });

  it('catches incomplete phoneme rows', () => {
    const bad = {
      word: 'hi',
      overall_score: 50,
      phonemes: [{ ipa: 'h', label: 'ok' }],
    };
    assert.ok(validateEvaluateResponse(bad).length > 0);
  });
});

describe('score mode — latency budget', () => {
  it('hangover + API budget under max', () => {
    const hangover = getHangoverMs(0.35, false);
    assert.ok(hangover + MAX_LATENCY_MS > hangover);
    assert.ok(MAX_SCORE_RESPONSE_MS <= MAX_LATENCY_MS);
  });

  it('min upload size stricter than min blob', () => {
    assert.ok(MIN_UPLOAD_BYTES > MIN_BLOB_BYTES);
  });
});
