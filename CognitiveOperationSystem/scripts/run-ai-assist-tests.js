#!/usr/bin/env node
/**
 * Chạy test hồi quy ChatGPT gián tiếp (CLI)
 *
 * Usage: node scripts/run-ai-assist-tests.js [scenario-id]
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');

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
    'ai-assist-screens.js',
    'ai-assist-test-scenarios.js',
    'ai-assist-test-runner.js',
  ]);

  ctx.CognitiveLibrary = ctx.window.CognitiveLibrary;
  ctx.DataStore = ctx.window.DataStore;
  ctx.I18n = ctx.window.I18n;
  ctx.EvidenceEngine = ctx.window.EvidenceEngine;
  ctx.CognitiveTree = ctx.window.CognitiveTree;
  ctx.ReflectionEngine = ctx.window.ReflectionEngine;
  ctx.ContradictionEngine = ctx.window.ContradictionEngine;
  ctx.InsightEngine = ctx.window.InsightEngine;
  ctx.TimelineEngine = ctx.window.TimelineEngine;
  ctx.AiAssist = ctx.window.AiAssist;
  ctx.AiAssistScreens = ctx.window.AiAssistScreens;
  ctx.AiAssistTestRunner = ctx.window.AiAssistTestRunner;
  ctx.generateId = ctx.window.generateId;

  ctx.DataStore.load();
  ctx.I18n.locale = 'vi';
  return ctx;
}

function printResult(r) {
  const icon = r.ok ? '✓' : '✗';
  console.log(`${icon} ${r.scenarioId} — ${r.title || ''}`);
  if (!r.ok) {
    for (const f of r.failures || []) {
      console.log(`    • [${f.check}] ${f.message}${f.detail ? `: ${f.detail}` : ''}`);
    }
  }
  for (const s of r.steps || []) {
    if (!s.ok) console.log(`    step ${s.id}: ${s.detail}`);
  }
}

function main() {
  const ctx = bootstrap();
  const runner = ctx.AiAssistTestRunner;
  const filterId = process.argv[2];

  if (filterId) {
    const r = runner.runOne(filterId, { backup: false });
    printResult(r);
    process.exit(r.ok ? 0 : 1);
  }

  const summary = runner.runAll({ backup: false });
  console.log(`\nChatGPT gián tiếp: ${summary.passed}/${summary.total} passed\n`);
  for (const r of summary.results) printResult(r);
  process.exit(summary.ok ? 0 : 1);
}

main();
