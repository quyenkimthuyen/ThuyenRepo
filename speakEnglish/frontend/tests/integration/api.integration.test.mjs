/**
 * Integration: frontend logic + backend API thật (HTTP)
 */

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import {
  validateEvaluateResponse,
  isEvaluationPassed,
  shouldAutoScoreOnUtteranceEnd,
  PRACTICE_MODE,
} from '../../js/core.js';
import {
  startBackend,
  stopBackend,
  createTestWavBuffer,
} from './server.mjs';

/** @type {{ proc?: import('node:child_process').ChildProcess, baseUrl: string } | null} */
let server = null;

describe('integration: frontend ↔ backend API', { timeout: 60000 }, () => {
  before(async () => {
    server = await startBackend();
  });

  after(() => {
    stopBackend(server);
    server = null;
  });

  it('health reachable from browser origin simulation', async () => {
    const res = await fetch(`${server.baseUrl}/api/v1/health`);
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.equal(data.status, 'ok');
    assert.ok(data.alignment_method);
    assert.ok(data.scoring_method);
  });

  it('POST /evaluate returns score-mode JSON contract', async () => {
    const wav = createTestWavBuffer();
    const form = new FormData();
    form.append('file', new Blob([wav], { type: 'audio/wav' }), 'integration.wav');
    form.append('target_word', 'hello');
    form.append('target_ipa', '/həˈloʊ/');
    form.append('target_phonemes', JSON.stringify(['h', 'ə', 'l', 'oʊ']));

    const res = await fetch(`${server.baseUrl}/api/v1/evaluate`, {
      method: 'POST',
      body: form,
    });

    const raw = await res.text();
    assert.equal(res.status, 200, raw);
    const data = JSON.parse(raw);
    assert.deepEqual(validateEvaluateResponse(data), []);
    assert.equal(data.word, 'hello');
    assert.ok(typeof isEvaluationPassed(data, 80) === 'boolean');
  });

  it('score mode routing agrees with API usage', () => {
    assert.equal(
      shouldAutoScoreOnUtteranceEnd({ practiceMode: PRACTICE_MODE.SCORE, autoEvaluate: true }),
      true,
    );
  });

  it('CORS headers present for localhost frontend', async () => {
    const res = await fetch(`${server.baseUrl}/api/v1/health`, {
      headers: { Origin: 'http://127.0.0.1:5500' },
    });
    assert.equal(res.status, 200);
    const allowOrigin = res.headers.get('access-control-allow-origin');
    assert.ok(
      allowOrigin === 'http://127.0.0.1:5500' || allowOrigin === '*',
      `unexpected CORS header: ${allowOrigin}`,
    );
  });

  it('rejects audio too short (400)', async () => {
    const form = new FormData();
    form.append('file', new Blob([Buffer.from('RIFF')], { type: 'audio/wav' }), 'tiny.wav');
    form.append('target_word', 'hello');

    const res = await fetch(`${server.baseUrl}/api/v1/evaluate`, { method: 'POST', body: form });
    assert.equal(res.status, 400);
  });
});
