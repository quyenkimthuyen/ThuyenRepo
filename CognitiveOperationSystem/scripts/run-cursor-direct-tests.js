#!/usr/bin/env node
/**
 * Chạy test mode Cursor trực tiếp
 *
 * Mock (mặc định): node scripts/run-cursor-direct-tests.js
 * Live (bridge + API key): node scripts/run-cursor-direct-tests.js --live
 * Một kịch bản: node scripts/run-cursor-direct-tests.js [scenario-id]
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const BRIDGE_URL = process.env.CURSOR_BRIDGE_URL || 'http://127.0.0.1:3847';
const BRIDGE_START_TIMEOUT_MS = 90000;

function loadApiKey() {
  if (process.env.CURSOR_API_KEY?.trim()) return process.env.CURSOR_API_KEY.trim();
  const candidates = [
    process.env.CURSOR_KEY_FILE,
    path.join(ROOT, 'server', 'key.txt'),
    '/home/toc/thuyen/repo/CognitiveOperationSystem/server/key.txt',
  ].filter(Boolean);
  for (const file of candidates) {
    try {
      const key = fs
        .readFileSync(file, 'utf8')
        .split('\n')
        .map((l) => l.trim())
        .find((l) => l && !l.startsWith('#'));
      if (key) return key;
    } catch {
      /* next */
    }
  }
  return null;
}

function loadScripts(ctx, files) {
  for (const f of files) {
    vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), ctx);
  }
}

function bootstrap() {
  const ctx = {
    window: {},
    console,
    document: {
      documentElement: { lang: 'vi' },
      title: '',
      querySelector: () => null,
    },
    localStorage: {
      _data: null,
      getItem(k) {
        return this._data;
      },
      setItem(k, v) {
        this._data = v;
      },
      removeItem() {
        this._data = null;
      },
    },
  };
  vm.createContext(ctx);

  loadScripts(ctx, [
    'cognitive-library.js',
    'data.js',
    'i18n.js',
    'evidence-engine.js',
    'cognitive-tree.js',
    'reflection-engine.js',
    'contradiction-engine.js',
    'insight-engine.js',
    'timeline-engine.js',
    'ai-assist.js',
  ]);
  ctx.CognitiveLibrary = ctx.window.CognitiveLibrary;
  ctx.DataStore = ctx.window.DataStore;
  ctx.I18n = ctx.window.I18n;
  ctx.EvidenceEngine = ctx.window.EvidenceEngine;
  ctx.CognitiveTree = ctx.window.CognitiveTree;
  ctx.ReflectionEngine = ctx.window.ReflectionEngine;
  ctx.InsightEngine = ctx.window.InsightEngine;
  ctx.AiAssist = ctx.window.AiAssist;
  ctx.generateId = ctx.window.generateId;

  loadScripts(ctx, [
    'cursor-direct.js',
    'cursor-direct-test-scenarios.js',
    'cursor-direct-test-runner.js',
  ]);

  ctx.CursorDirect = ctx.window.CursorDirect;
  ctx.CursorDirectTestRunner = ctx.window.CursorDirectTestRunner;
  ctx.DataStore.load();
  ctx.I18n.locale = 'vi';
  return ctx;
}

function printResult(r) {
  const icon = r.ok ? '✓' : '✗';
  const mode = r.mode ? ` [${r.mode}]` : '';
  console.log(`${icon} ${r.scenarioId} — ${r.title || ''}${mode}`);
  if (!r.ok && r.error) console.log(`    error: ${r.error}`);
  for (const f of r.failures || []) {
    console.log(`    • [${f.check}] ${f.message}${f.detail ? `: ${f.detail}` : ''}`);
  }
  for (const s of r.steps || []) {
    if (!s.ok) console.log(`    step ${s.id}: ${s.detail}`);
  }
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    const err = new Error(data.message || data.error || res.statusText);
    err.code = data.error;
    err.status = res.status;
    throw err;
  }
  return data;
}

async function waitForBridge(url, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const data = await fetchJson(`${url}/health`);
      if (data.ok && data.sdkReady && data.hasApiKey) return true;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 800));
  }
  return false;
}

async function ensureBridgeRunning(apiKey) {
  try {
    const health = await fetchJson(`${BRIDGE_URL}/health`);
    if (health.ok && health.sdkReady && health.hasApiKey) {
      return { child: null, started: false };
    }
  } catch {
    /* start below */
  }

  const child = spawn('node', ['cursor-bridge.mjs'], {
    cwd: path.join(ROOT, 'server'),
    env: { ...process.env, CURSOR_API_KEY: apiKey },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  const ready = await waitForBridge(BRIDGE_URL, BRIDGE_START_TIMEOUT_MS);
  if (!ready) {
    child.kill();
    throw new Error('bridge_start_timeout');
  }
  return { child, started: true };
}

async function runLiveScenario(ctx, scenario) {
  const failures = [];
  const steps = [];
  const { AiAssist } = ctx;

  const health = await fetchJson(`${BRIDGE_URL}/health`);
  steps.push({
    id: 'bridge_health',
    ok: health.ok && health.hasApiKey && health.sdkReady,
    detail: `hasApiKey=${health.hasApiKey}, sdk=${health.sdkReady}`,
  });
  if (!health.ok || !health.hasApiKey || !health.sdkReady) {
    return {
      ok: false,
      scenarioId: scenario.id,
      title: scenario.title,
      mode: 'live',
      error: 'bridge_not_ready',
      failures: [{ check: 'bridge_health', message: 'Bridge chưa sẵn sàng' }],
      steps,
    };
  }

  const reflectionPrompt = AiAssist.getReflectionPrompt(scenario.initialThought);
  const start = await fetchJson(`${BRIDGE_URL}/api/session/start`, {
    method: 'POST',
    body: { reflectionPrompt },
  });
  const replyOk = Boolean(start.reply?.trim());
  steps.push({
    id: 'session_start',
    ok: replyOk,
    detail: replyOk ? `reply ${start.reply.length} chars` : 'empty reply',
  });
  if (!replyOk) {
    failures.push({ check: 'session_start', message: 'Bridge không trả lời mở đầu' });
  }

  const turns = (scenario.userDialogue || []).slice(0, scenario.liveMaxTurns || 1);
  for (const turn of turns) {
    const msg = await fetchJson(
      `${BRIDGE_URL}/api/session/${encodeURIComponent(start.sessionKey)}/message`,
      { method: 'POST', body: { content: turn.content } }
    );
    const ok = Boolean(msg.reply?.trim());
    steps.push({
      id: `message_${turn.step}`,
      ok,
      detail: ok ? 'có reply' : 'reply trống',
    });
    if (!ok) failures.push({ check: 'message_reply', message: `Không có reply sau ${turn.step}` });
  }

  const exportRes = await fetchJson(
    `${BRIDGE_URL}/api/session/${encodeURIComponent(start.sessionKey)}/export`,
    { method: 'POST', body: { exportPrompt: AiAssist.getExportPrompt() } }
  );
  const payload = AiAssist.extractJsonBlock(exportRes.raw || '');
  const parseOk = Boolean(payload);
  steps.push({
    id: 'export_json',
    ok: parseOk,
    detail: parseOk ? 'JSON hợp lệ' : 'Không parse được JSON',
  });
  if (!parseOk) {
    failures.push({ check: 'export_json', message: 'Export không phải JSON hợp lệ' });
  } else {
    for (const field of scenario.expectExportFields || []) {
      const has = payload[field] !== undefined && payload[field] !== null;
      steps.push({ id: `field_${field}`, ok: has, detail: has ? 'có' : 'thiếu' });
      if (!has) failures.push({ check: 'export_field', message: `Thiếu field ${field}` });
    }
    if (scenario.initialThought) {
      const thoughtOk =
        String(payload.initialThought || '')
          .toLowerCase()
          .includes(scenario.initialThought.slice(0, 12).toLowerCase()) ||
        String(payload.event?.detail || '')
          .toLowerCase()
          .includes(scenario.initialThought.slice(0, 12).toLowerCase());
      steps.push({
        id: 'export_thought_anchor',
        ok: thoughtOk,
        detail: thoughtOk ? 'initialThought/event bám ý mở đầu' : 'lệch suy nghĩ ban đầu',
      });
      if (!thoughtOk) {
        failures.push({ check: 'export_thought', message: 'JSON không bám initialThought' });
      }
    }
  }

  try {
    await fetch(`${BRIDGE_URL}/api/session/${encodeURIComponent(start.sessionKey)}`, {
      method: 'DELETE',
    });
  } catch {
    /* ignore */
  }

  return {
    ok: failures.length === 0,
    scenarioId: scenario.id,
    title: scenario.title,
    mode: 'live',
    failures,
    steps,
  };
}

async function main() {
  const args = process.argv.slice(2);
  const live = args.includes('--live');
  const filterId = args.find((a) => !a.startsWith('--'));

  if (live) {
    const apiKey = loadApiKey();
    if (!apiKey) {
      console.error('Không tìm thấy API key — đặt CURSOR_API_KEY hoặc server/key.txt');
      process.exit(1);
    }

    let bridgeChild = null;
    try {
      const bridge = await ensureBridgeRunning(apiKey);
      bridgeChild = bridge.child;

      const ctx = bootstrap();
      const scenarios = filterId
        ? [ctx.CursorDirectTestRunner.getScenario(filterId)].filter(Boolean)
        : ctx.window.CURSOR_DIRECT_TEST_SCENARIOS.filter((s) => s.liveOnly);

      if (!scenarios.length) {
        console.error(filterId ? `Không tìm thấy kịch bản live: ${filterId}` : 'Không có kịch bản live');
        process.exit(1);
      }

      const results = [];
      for (const scenario of scenarios) {
        results.push(await runLiveScenario(ctx, scenario));
      }

      const passed = results.filter((r) => r.ok).length;
      console.log(`\nCursor trực tiếp (live): ${passed}/${results.length} passed\n`);
      for (const r of results) printResult(r);
      process.exit(passed === results.length ? 0 : 1);
    } finally {
      if (bridgeChild) bridgeChild.kill();
    }
    return;
  }

  const ctx = bootstrap();
  const runner = ctx.CursorDirectTestRunner;

  if (filterId) {
    const r = runner.runOne(filterId, { backup: false });
    printResult(r);
    process.exit(r.ok ? 0 : 1);
  }

  const summary = runner.runAll({ backup: false });
  console.log(`\nCursor trực tiếp (mock): ${summary.passed}/${summary.total} passed\n`);
  for (const r of summary.results) printResult(r);
  process.exit(summary.ok ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
