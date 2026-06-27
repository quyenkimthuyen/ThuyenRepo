/**
 * PronounceLab Personal — frontend application
 */

import {
  PRACTICE_MODE,
  MIC_STATE,
  wordsMatch,
  textMatchExact,
  textMatchPractice,
  textMatchWithThreshold,
  textSimilarityPercent,
  extractPracticeMatchSnippet,
  extractSpokenText,
  getHangoverMs,
  computeRms,
  TEXT_MATCH_DELAY_MS,
  shouldAutoScoreOnUtteranceEnd,
  MIN_SPEECH_MS,
} from './js/core.js';
import { MicEngine, MIC_PHASE } from './js/mic-engine.js';
import { loadManifest, buildQuizSession } from './js/vocabulary.js';

const STORAGE_KEY = 'pronouncelab_history';

/** @type {object} */
let config = {};
/** @type {Array} */
let words = [];
/** @type {object|null} */
let vocabularyManifest = null;
let currentQuizMeta = { topicId: '', quizSize: 30, totalInTopic: 0 };
let currentIndex = 0;
let practiceMode = PRACTICE_MODE.TEXT;
let isAdvancing = false;
let micState = MIC_STATE.OFF;
let autoStartDone = false;
let userAudioBlob = null;
let userAudioUrl = null;
let serverAudioUrl = null;
let audioContext = null;

// Live mic pipeline
let micEngine = null;
let liveModeActive = false;
let speechRecognition = null;
let micStream = null;
let micSourceNode = null;
let liveMediaRecorder = null;
let audioRingChunks = [];
let liveAnalyser = null;
let vadAnimationId = null;
let scoreApiBusy = false;
let lastMicUiState = MIC_STATE.OFF;
let lastMicUiLabel = 'Micro tắt';
let liveMimeType = 'audio/webm';
let phraseRecorder = null;
let phraseChunks = [];
let textMatchTimer = null;
let scoreMatchTimer = null;
let utterancePcmChunks = [];
let utteranceCapturing = false;
let pcmCaptureNode = null;
let pcmSilentGain = null;

let isSamplePlaying = false;
let speechRecognitionPaused = false;
let sampleResumeTimer = null;
const RING_CHUNK_MS = 100;
const MAX_RING_CHUNKS = 30;
const SAMPLE_TAIL_MS = 500;
const MAX_SCORE_AUDIO_SEC = 3;
const MIN_BLOB_BYTES = 500;
const MIN_UPLOAD_BYTES = 800;
const SETTINGS_KEY = 'pronouncelab_settings';
const WORD_INDEX_KEY = 'pronouncelab_word_index';
const QUIZ_SESSION_KEY = 'pronouncelab_quiz_session';
const EVAL_CACHE_KEY = 'pronouncelab_eval_cache';
/** @type {Record<string, object>} Kết quả chấm gần nhất theo từ */
const lastEvaluations = {};
/** Kết quả đang hiển thị cho từ hiện tại */
let currentWordEvaluation = null;
let passAdvanceTimer = null;
let idleSampleTimer = null;
let idleSampleArmed = false;
let suppressWordSelectChange = false;
/** @type {Array<{word:string, text:object, score:object}>} */
let quizSessionResults = [];
let lastScoredAtIndex = -1;
const SAMPLE_REPLAY_AFTER_FAILS = 3;
const PASS_ADVANCE_DELAY_MS = 1500;
let wordFailStreak = 0;
let passAdvancePending = false;
let passAdvancePayload = null;

const $ = (id) => document.getElementById(id);

const els = {
  wordSelect: $('word-select'),
  wordIndex: $('word-index'),
  historyBadge: $('history-badge'),
  currentWord: $('current-word'),
  currentIpa: $('current-ipa'),
  currentMeaning: $('current-meaning'),
  quizInfo: $('quiz-info'),
  btnPlaySample: $('btn-play-sample'),
  btnRetry: $('btn-retry'),
  btnPrev: $('btn-prev'),
  btnNext: $('btn-next'),
  btnSettings: $('btn-settings'),
  btnCloseSettings: $('btn-close-settings'),
  recordingIndicator: $('recording-indicator'),
  spinner: $('spinner'),
  scoreSection: $('score-section'),
  scoreZone: $('score-zone'),
  scoreStatusLabel: $('score-status-label'),
  scoreSpinner: $('score-spinner'),
  overallScore: $('overall-score'),
  passStatus: $('pass-status'),
  phonemeContainer: $('phoneme-container'),
  quizResultsBody: $('quiz-results-body'),
  quizSummaryStats: $('quiz-summary-stats'),
  quizSummaryTitle: $('quiz-summary-title'),
  settingsPanel: $('settings-panel'),
  settingAutoplay: $('setting-autoplay'),
  settingTtsVoice: $('setting-tts-voice'),
  settingIdleSampleSec: $('setting-idle-sample-sec'),
  settingLiveAuto: $('setting-live-auto'),
  settingAutoEvaluate: $('setting-auto-evaluate'),
  settingApiUrl: $('setting-api-url'),
  settingPassScore: $('setting-pass-score'),
  settingTextPassScore: $('setting-text-pass-score'),
  serviceStatus: $('service-status'),
  btnLiveToggle: $('btn-live-toggle'),
  micStatusLabel: $('mic-status-label'),
  vadLevel: $('vad-level'),
  liveTranscriptFinal: $('live-transcript-final'),
  liveTranscriptInterim: $('live-transcript-interim'),
  liveTranscriptPlaceholder: $('live-transcript-placeholder'),
  liveHint: $('live-hint'),
  settingSilenceSec: $('setting-silence-sec'),
  settingTopic: $('setting-topic'),
  settingQuizSize: $('setting-quiz-size'),
  btnNewQuiz: $('btn-new-quiz'),
  modeText: $('mode-text'),
  modeScore: $('mode-score'),
  appRoot: document.querySelector('.app'),
};

// ─── Init ───────────────────────────────────────────────────────────────────

let initRunCount = 0;
/** E2E: inject audio cho processScoreUtterance khi fake mic không ghi được */
let e2eInjectScoreBlob = null;

async function init() {
  initRunCount += 1;
  await loadConfig();
  loadEvalCache();
  loadSettings();
  await initVocabulary();
  applyPracticeModeUI();
  bindEvents();
  bindPhonemeDelegation();
  setupAutoStartMic();
  initTtsVoiceSelect();
  checkBackend();
  initLiveSpeech();
  setMicState(MIC_STATE.OFF, 'Micro tắt');
  resetMicLevelVisual();

  if (els.settingLiveAuto?.checked) {
    startLiveMode({ silent: true }).catch(() => {
      showLiveHint('Chạm màn hình để bật micro tự động', 'warn');
    });
  }
}

function setupAutoStartMic() {
  const tryStart = () => {
    if (autoStartDone || liveModeActive || !els.settingLiveAuto?.checked) return;
    autoStartDone = true;
    hideLiveHint();
    startLiveMode();
  };
  els.appRoot?.addEventListener('click', tryStart, { once: true });
  els.btnLiveToggle?.addEventListener('click', () => { autoStartDone = true; }, { once: true });
}

function setMicState(state, label) {
  if (state !== MIC_STATE.BUSY && state !== MIC_STATE.PROCESSING) {
    lastMicUiState = state;
    if (label) lastMicUiLabel = label;
  }

  micState = state;
  if (els.btnLiveToggle) {
    els.btnLiveToggle.dataset.state = state;
    els.btnLiveToggle.setAttribute('aria-pressed', state !== MIC_STATE.OFF ? 'true' : 'false');
  }
  if (els.micStatusLabel && label) {
    els.micStatusLabel.textContent = label;
  }
  syncMicLevelLiveFlag();
}

function syncMicLevelLiveFlag() {
  const btn = els.btnLiveToggle;
  if (!btn) return;
  const state = btn.dataset.state || MIC_STATE.OFF;
  const levelLive = liveModeActive
    && state !== MIC_STATE.OFF
    && state !== MIC_STATE.SAMPLE
    && state !== MIC_STATE.BUSY
    && state !== MIC_STATE.PROCESSING;
  btn.dataset.levelLive = levelLive ? 'true' : 'false';
  if (!levelLive) {
    btn.style.removeProperty('--mic-level-scale');
    btn.style.removeProperty('--mic-level-glow');
  }
}

function updateMicLevelVisual(pct) {
  if (isMicInputBlocked()) pct = 0;
  const level = Math.min(100, Math.max(0, pct)) / 100;
  if (els.vadLevel) {
    els.vadLevel.style.transform = `scaleX(${level})`;
  }
  const btn = els.btnLiveToggle;
  if (!btn || btn.dataset.levelLive !== 'true') return;
  btn.style.setProperty('--mic-level-scale', String(1 + level * 0.14));
  btn.style.setProperty('--mic-level-glow', String(level));
}

function resetMicLevelVisual() {
  if (els.vadLevel) {
    els.vadLevel.style.transform = 'scaleX(0)';
  }
  const btn = els.btnLiveToggle;
  if (!btn) return;
  btn.dataset.levelLive = 'false';
  btn.style.removeProperty('--mic-level-scale');
  btn.style.removeProperty('--mic-level-glow');
}

function setScoreState(mode, text) {
  if (els.scoreStatusLabel && text) {
    els.scoreStatusLabel.textContent = text;
  }
  els.scoreZone?.classList.toggle('scoring', mode === 'scoring');
  els.scoreSpinner?.classList.toggle('hidden', mode !== 'scoring');
}

function getPassThreshold() {
  const n = parseInt(els.settingPassScore?.value, 10);
  if (!Number.isFinite(n)) return 80;
  return Math.min(100, Math.max(50, n));
}

function getTextPassThreshold() {
  const n = parseInt(els.settingTextPassScore?.value, 10);
  if (!Number.isFinite(n)) return 100;
  return Math.min(100, Math.max(50, n));
}

function spokenMatchesTarget(spoken, target) {
  if (isTextMode()) return textMatchWithThreshold(spoken, target, getTextPassThreshold());
  return wordsMatch(spoken, target);
}

function createEmptyQuizModeResult() {
  return { score: null, passed: null, status: 'pending' };
}

function createEmptyQuizResultRow(word) {
  return {
    word,
    text: createEmptyQuizModeResult(),
    score: createEmptyQuizModeResult(),
  };
}

function normalizeQuizResultRow(row, word = row?.word) {
  if (row?.text && row?.score) {
    return { word: word || row.word, text: { ...row.text }, score: { ...row.score } };
  }
  const legacy = {
    score: row?.score ?? null,
    passed: row?.passed ?? null,
    status: row?.status ?? 'pending',
  };
  const fresh = createEmptyQuizResultRow(word || row?.word || '');
  fresh.score = { ...legacy };
  return fresh;
}

function getQuizModeKey(mode = practiceMode) {
  return mode === PRACTICE_MODE.TEXT ? 'text' : 'score';
}

function getQuizRowsForMode(mode = practiceMode) {
  const key = getQuizModeKey(mode);
  const source = quizSessionResults.length
    ? quizSessionResults
    : words.map((w) => createEmptyQuizResultRow(w.word));
  return source.map((row) => {
    const normalized = normalizeQuizResultRow(row);
    return { word: normalized.word, ...normalized[key] };
  });
}

function getSilenceSecSetting() {
  const sec = parseFloat(els.settingSilenceSec?.value);
  if (!Number.isFinite(sec)) return 0.35;
  return Math.round(Math.min(1.2, Math.max(0.2, sec)) * 100) / 100;
}

function formatSilenceSecLabel(sec) {
  const s = Math.round(sec * 100) / 100;
  if (Number.isInteger(s)) return String(s);
  return s.toFixed(2).replace(/0$/, '');
}

function getLiveSilenceHintText() {
  const hangSec = formatSilenceSecLabel(getSilenceSecSetting());
  const action = isTextMode() ? 'chuyển từ' : 'chấm điểm';
  return `Nói xong → im lặng ~${hangSec}s → ${action}`;
}

function refreshSilenceHints() {
  if (els.recordingIndicator && liveModeActive) {
    els.recordingIndicator.innerHTML = `<span class="pulse"></span> ${getLiveSilenceHintText()}`;
  }
  const idleHint = els.phonemeContainer?.querySelector('.phoneme-idle-hint');
  if (idleHint) {
    idleHint.textContent = `${getLiveSilenceHintText()} — chi tiết IPA`;
  }
}

function initQuizSessionResults() {
  quizSessionResults = words.map((w) => createEmptyQuizResultRow(w.word));
  renderQuizSummary();
}

function persistQuizSession() {
  if (!words.length) return;
  try {
    sessionStorage.setItem(QUIZ_SESSION_KEY, JSON.stringify({
      topicId: currentQuizMeta.topicId,
      quizSize: words.length,
      words,
      quizSessionResults,
      currentIndex,
    }));
  } catch {
    /* ignore quota */
  }
}

function restoreQuizSession(topicId, quizSize) {
  try {
    const raw = sessionStorage.getItem(QUIZ_SESSION_KEY);
    if (!raw) return false;
    const saved = JSON.parse(raw);
    if (saved.topicId !== topicId) return false;
    if (!Array.isArray(saved.words) || !saved.words.length) return false;
    if (saved.quizSize !== quizSize && saved.words.length !== quizSize) return false;

    words = saved.words;
    currentQuizMeta = {
      topicId: saved.topicId,
    quizSize: saved.words.length,
    totalInTopic: vocabularyManifest?.topics?.find((t) => t.id === saved.topicId)?.count
      ?? currentQuizMeta.totalInTopic
      ?? saved.words.length,
  };
    quizSessionResults = Array.isArray(saved.quizSessionResults)
      && saved.quizSessionResults.length === words.length
      ? saved.quizSessionResults.map((row, i) => normalizeQuizResultRow(row, words[i]?.word))
      : words.map((w) => createEmptyQuizResultRow(w.word));
    return true;
  } catch {
    return false;
  }
}

function clearQuizSessionStorage() {
  sessionStorage.removeItem(QUIZ_SESSION_KEY);
}

function recordQuizSessionResult(word, score, passed, kind = 'score', wordIndex = null) {
  const idx = wordIndex != null
    ? wordIndex
    : words.findIndex((w) => normalizeWordKey(w.word) === normalizeWordKey(word));
  if (idx < 0 || idx >= words.length) return;
  const modeKey = kind === 'text' ? 'text' : 'score';
  if (!quizSessionResults[idx]) {
    quizSessionResults[idx] = createEmptyQuizResultRow(words[idx].word);
  } else {
    quizSessionResults[idx] = normalizeQuizResultRow(quizSessionResults[idx], words[idx].word);
  }
  quizSessionResults[idx][modeKey] = {
    score,
    passed,
    status: passed ? 'pass' : 'fail',
  };
  updateQuizRow(idx);
  persistQuizSession();
}

function renderQuizSummary() {
  if (!els.quizResultsBody) return;

  const rows = getQuizRowsForMode();
  const modeLabel = isTextMode() ? 'Chỉ text' : 'Chấm điểm';
  if (els.quizSummaryTitle) {
    els.quizSummaryTitle.textContent = `Bảng tổng kết bài quiz · ${modeLabel}`;
  }

  els.quizResultsBody.innerHTML = rows.map((row, i) => {
    const isCurrent = i === currentIndex;
    const scoreText = row.score == null ? '—' : `${row.score}%`;
    let resultLabel = 'Chưa đọc';
    let resultClass = 'pending';
    if (row.status === 'pass') {
      resultLabel = '✓ Đạt';
      resultClass = 'pass';
    } else if (row.status === 'fail') {
      resultLabel = '✗ Chưa';
      resultClass = 'fail';
    }

    return `<tr class="quiz-row ${resultClass}${isCurrent ? ' current' : ''}" data-index="${i}">
      <td>${i + 1}</td>
      <td>${row.word}</td>
      <td>${scoreText}</td>
      <td><span class="quiz-result-badge ${resultClass}">${resultLabel}</span></td>
    </tr>`;
  }).join('');

  updateQuizSummaryStats(rows);
  bindQuizRowClicks();
}

function updateQuizSummaryStats(rows = null) {
  const data = rows ?? getQuizRowsForMode();
  const threshold = isScoreMode() ? getPassThreshold() : getTextPassThreshold();
  const scored = data.filter((r) => r.score != null);
  const passedCount = data.filter((r) => r.passed).length;
  const avg = scored.length
    ? Math.round(scored.reduce((sum, r) => sum + r.score, 0) / scored.length)
    : null;
  if (els.quizSummaryStats) {
    els.quizSummaryStats.textContent = `${passedCount}/${data.length} đạt · TB ${avg ?? '—'}% · ngưỡng ${threshold}%`;
  }
}

function bindQuizRowClicks() {
  els.quizResultsBody?.querySelectorAll('.quiz-row').forEach((tr) => {
    tr.addEventListener('click', () => {
      showWord(parseInt(tr.dataset.index, 10), { autoplay: false });
    });
  });
}

/** Chỉ đổi dòng hiện tại — tránh rebuild bảng quiz khi chuyển từ */
function updateQuizCurrentRow() {
  if (!els.quizResultsBody?.children.length) {
    renderQuizSummary();
    return;
  }
  els.quizResultsBody.querySelectorAll('.quiz-row').forEach((tr) => {
    const idx = parseInt(tr.dataset.index, 10);
    tr.classList.toggle('current', idx === currentIndex);
  });
}

/** Cập nhật một dòng quiz — tránh rebuild cả bảng sau mỗi lần chấm */
function updateQuizRow(index) {
  if (!els.quizResultsBody) return;
  const row = getQuizRowsForMode()[index];
  if (!row) return;

  let tr = els.quizResultsBody.querySelector(`tr.quiz-row[data-index="${index}"]`);
  if (!tr) {
    renderQuizSummary();
    return;
  }

  const scoreText = row.score == null ? '—' : `${row.score}%`;
  let resultLabel = 'Chưa đọc';
  let resultClass = 'pending';
  if (row.status === 'pass') {
    resultLabel = '✓ Đạt';
    resultClass = 'pass';
  } else if (row.status === 'fail') {
    resultLabel = '✗ Chưa';
    resultClass = 'fail';
  }

  tr.className = `quiz-row ${resultClass}${index === currentIndex ? ' current' : ''}`;
  if (tr.cells[2]) tr.cells[2].textContent = scoreText;
  if (tr.cells[3]) {
    tr.cells[3].innerHTML = `<span class="quiz-result-badge ${resultClass}">${resultLabel}</span>`;
  }
  updateQuizSummaryStats();
}

function capturePageScroll() {
  return { x: window.scrollX, y: window.scrollY };
}

function restorePageScroll(pos) {
  if (!pos) return;
  const apply = () => {
    if (window.scrollX !== pos.x || window.scrollY !== pos.y) {
      window.scrollTo(pos.x, pos.y);
    }
  };
  apply();
  requestAnimationFrame(apply);
  requestAnimationFrame(() => requestAnimationFrame(apply));
}

function runWithPreservedScroll(fn) {
  const scrollPos = capturePageScroll();
  try {
    return fn();
  } finally {
    restorePageScroll(scrollPos);
  }
}

async function runWithPreservedScrollAsync(fn) {
  const scrollPos = capturePageScroll();
  try {
    return await fn();
  } finally {
    restorePageScroll(scrollPos);
  }
}

function syncMicStateFromEngine() {
  refreshMicAvailabilityUi();
}

function isMicInputBlocked() {
  if (!liveModeActive || isSamplePlaying) return false;
  if (passAdvancePending || scoreApiBusy || isAdvancing) return true;
  if (!micEngine) return false;
  if (micEngine._processing) return true;
  if (micEngine.phase === MIC_PHASE.PROCESSING) return true;
  if (micEngine.phase === MIC_PHASE.COOLDOWN) return true;
  return false;
}

function getMicBusyLabel() {
  if (passAdvancePending) return 'Đã đạt — chuẩn bị chuyển từ...';
  if (scoreApiBusy) return 'Đang chấm điểm — chưa nghe';
  if (isAdvancing) return 'Đang chuyển từ...';
  if (micEngine?.phase === MIC_PHASE.PROCESSING) return 'Đang xử lý...';
  if (micEngine?.phase === MIC_PHASE.COOLDOWN) return 'Chuẩn bị nghe...';
  return 'Micro đang bận...';
}

function refreshMicAvailabilityUi() {
  if (!liveModeActive) return;
  if (isSamplePlaying) return;

  if (isMicInputBlocked()) {
    setMicState(MIC_STATE.BUSY, getMicBusyLabel());
    updateMicLevelVisual(0);
    return;
  }

  if (!micEngine) return;

  const phase = micEngine.phase;
  const labels = isScoreMode()
    ? {
        [MIC_PHASE.READY]: 'Sẵn sàng thu âm',
        [MIC_PHASE.HEARING]: 'Đang nghe...',
        [MIC_PHASE.SAMPLE]: 'Đang phát mẫu...',
      }
    : {
        [MIC_PHASE.READY]: 'Sẵn sàng thu âm',
        [MIC_PHASE.HEARING]: 'Đang nghe bạn nói...',
        [MIC_PHASE.SAMPLE]: 'Đang phát mẫu...',
      };
  setMicState(micPhaseToState(phase), labels[phase] || lastMicUiLabel);
}

function prepareMicForNextUtterance() {
  if (!liveModeActive || !micEngine) return;
  micEngine.clearTranscript();
  syncTranscriptFromEngine();
  micEngine.clearCooldown();
  if (micEngine.phase === MIC_PHASE.COOLDOWN || micEngine.phase === MIC_PHASE.PROCESSING) {
    micEngine.setPhase(MIC_PHASE.READY, 'Sẵn sàng thu âm');
  }
  syncMicStateFromEngine();
}

async function loadConfig() {
  try {
    const res = await fetch('config.json');
    config = await res.json();
  } catch {
    config = { apiBaseUrl: 'http://127.0.0.1:8000', autoPlaySample: true };
  }
}

async function loadDemoWords() {
  const res = await fetch('data/words.json');
  const data = await res.json();
  words = data.words || [];
  currentQuizMeta = { topicId: 'demo', quizSize: words.length, totalInTopic: words.length };
  updateQuizInfo();
  renderWordList();
  initQuizSessionResults();
}

function getTopicId() {
  return els.settingTopic?.value
    || vocabularyManifest?.defaultTopicId
    || '';
}

function getQuizSize() {
  const n = parseInt(els.settingQuizSize?.value, 10);
  if (Number.isFinite(n) && n > 0) return n;
  return vocabularyManifest?.defaultQuizSize ?? config.defaultQuizSize ?? 30;
}

function populateTopicSelect() {
  if (!vocabularyManifest?.topics?.length || !els.settingTopic) return;
  els.settingTopic.innerHTML = vocabularyManifest.topics
    .map((t) => `<option value="${t.id}">${t.label} (${t.count})</option>`)
    .join('');
  const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
  const topicId = saved.topicId || vocabularyManifest.defaultTopicId;
  if (topicId && [...els.settingTopic.options].some((o) => o.value === topicId)) {
    els.settingTopic.value = topicId;
  }
}

function updateQuizInfo() {
  if (!els.quizInfo) return;
  const topic = vocabularyManifest?.topics?.find((t) => t.id === currentQuizMeta.topicId);
  const label = topic?.label || (currentQuizMeta.topicId === 'demo' ? 'Demo' : 'Chủ đề');
  els.quizInfo.textContent = `Quiz ${label} · ${words.length}/${currentQuizMeta.totalInTopic || words.length} từ`;
}

async function initVocabulary() {
  try {
    vocabularyManifest = await loadManifest();
    populateTopicSelect();
    const savedIndex = parseInt(sessionStorage.getItem(WORD_INDEX_KEY) || '0', 10);
    await startQuizSession({
      index: Number.isFinite(savedIndex) ? savedIndex : 0,
      autoplay: false,
    });
  } catch (err) {
    console.warn('Vocabulary load failed, using demo words.json:', err);
    await loadDemoWords();
    const savedIndex = parseInt(sessionStorage.getItem(WORD_INDEX_KEY) || '0', 10);
    showWord(Number.isFinite(savedIndex) ? savedIndex : 0, { autoplay: false });
  }
}

async function startQuizSession(options = {}) {
  const topicId = options.topicId ?? getTopicId();
  const quizSize = options.quizSize ?? getQuizSize();
  const forceNew = options.newQuiz === true;

  if (!vocabularyManifest || !topicId) {
    await loadDemoWords();
    showWord(options.index ?? 0, { autoplay: options.autoplay !== false });
    return;
  }

  if (!forceNew && restoreQuizSession(topicId, quizSize)) {
    updateQuizInfo();
    renderWordList();
    const maxIdx = Math.max(0, words.length - 1);
    const saved = Number.isFinite(options.index)
      ? options.index
      : parseInt(sessionStorage.getItem(WORD_INDEX_KEY) || '0', 10);
    const index = Math.min(Math.max(0, saved), maxIdx);
    showWord(index, { autoplay: options.autoplay !== false });
    return;
  }

  const session = await buildQuizSession({ topicId, quizSize });
  words = session.words;
  currentQuizMeta = {
    topicId: session.topicId,
    quizSize: session.quizSize,
    totalInTopic: session.totalInTopic,
  };
  lastScoredAtIndex = -1;
  updateQuizInfo();
  renderWordList();
  initQuizSessionResults();
  persistQuizSession();

  const maxIdx = Math.max(0, words.length - 1);
  let index = 0;
  if (forceNew) {
    sessionStorage.setItem(WORD_INDEX_KEY, '0');
    index = 0;
  } else {
    const saved = Number.isFinite(options.index)
      ? options.index
      : parseInt(sessionStorage.getItem(WORD_INDEX_KEY) || '0', 10);
    index = Math.min(Math.max(0, saved), maxIdx);
  }
  showWord(index, { autoplay: options.autoplay !== false });
}

function loadSettings() {
  const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
  els.settingAutoplay.checked = saved.autoPlaySample ?? config.autoPlaySample ?? true;
  if (els.settingIdleSampleSec) {
    els.settingIdleSampleSec.value = saved.idleSampleSec ?? config.idleSampleSec ?? 10;
  }
  els.settingLiveAuto.checked = saved.liveAutoStart ?? config.liveAutoStart ?? true;
  els.settingAutoEvaluate.checked = saved.autoEvaluate ?? true;
  els.settingSilenceSec.value = saved.silenceSec ?? config.silenceSec ?? 0.35;
  els.settingApiUrl.value = saved.apiBaseUrl ?? config.apiBaseUrl ?? 'http://127.0.0.1:8000';
  els.settingPassScore.value = saved.passScore ?? config.thresholds?.overallPass ?? 80;
  els.settingTextPassScore.value = saved.textPassScore ?? config.thresholds?.textPass ?? 100;
  els.settingQuizSize.value = saved.quizSize ?? config.defaultQuizSize ?? vocabularyManifest?.defaultQuizSize ?? 30;
  practiceMode = saved.practiceMode ?? config.practiceMode ?? PRACTICE_MODE.TEXT;
  if (els.settingTtsVoice && saved.ttsVoiceUri) {
    els.settingTtsVoice.dataset.savedUri = saved.ttsVoiceUri;
  }
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify({
    autoPlaySample: els.settingAutoplay.checked,
    idleSampleSec: parseInt(els.settingIdleSampleSec?.value, 10) || 0,
    liveAutoStart: els.settingLiveAuto.checked,
    autoEvaluate: els.settingAutoEvaluate.checked,
    silenceSec: parseFloat(els.settingSilenceSec.value) || 0.35,
    apiBaseUrl: els.settingApiUrl.value,
    passScore: parseInt(els.settingPassScore.value, 10),
    textPassScore: parseInt(els.settingTextPassScore.value, 10),
    topicId: els.settingTopic?.value || vocabularyManifest?.defaultTopicId || '',
    quizSize: getQuizSize(),
    practiceMode,
    ttsVoiceUri: els.settingTtsVoice?.value || '',
  }));
}

function escapeHtmlAttr(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;');
}

function getTtsVoices() {
  if (!('speechSynthesis' in window)) return [];
  return speechSynthesis.getVoices();
}

function getEnglishTtsVoices() {
  return getTtsVoices()
    .filter((v) => /^en([-_]|$)/i.test(v.lang))
    .sort((a, b) => {
      const rank = (v) => {
        if (/en-US/i.test(v.lang)) return 0;
        if (/en-GB/i.test(v.lang)) return 1;
        if (/en-AU/i.test(v.lang)) return 2;
        return 3;
      };
      const byLocale = rank(a) - rank(b);
      if (byLocale !== 0) return byLocale;
      return a.name.localeCompare(b.name);
    });
}

function populateTtsVoiceSelect() {
  const sel = els.settingTtsVoice;
  if (!sel) return;

  const voices = getEnglishTtsVoices();
  const savedUri = sel.dataset.savedUri || sel.value || '';
  const options = ['<option value="">Mặc định trình duyệt</option>'];
  voices.forEach((v) => {
    const label = `${v.name} (${v.lang})`;
    options.push(`<option value="${escapeHtmlAttr(v.voiceURI)}">${escapeHtmlAttr(label)}</option>`);
  });
  sel.innerHTML = options.join('');

  if (savedUri && [...sel.options].some((o) => o.value === savedUri)) {
    sel.value = savedUri;
  } else {
    sel.value = '';
  }
}

function initTtsVoiceSelect() {
  if (!els.settingTtsVoice) return;
  const refresh = () => populateTtsVoiceSelect();
  refresh();
  if ('speechSynthesis' in window) {
    speechSynthesis.addEventListener('voiceschanged', refresh);
  }
}

function resolveSelectedTtsVoice() {
  const uri = els.settingTtsVoice?.value;
  if (!uri) return null;
  return getTtsVoices().find((v) => v.voiceURI === uri) || null;
}

function configureSampleUtterance(utter) {
  const voice = resolveSelectedTtsVoice();
  utter.lang = voice?.lang || 'en-US';
  utter.rate = 0.85;
  if (voice) utter.voice = voice;
}

function isScoreMode() {
  return practiceMode === PRACTICE_MODE.SCORE;
}

function isTextMode() {
  return practiceMode === PRACTICE_MODE.TEXT;
}

function setPracticeMode(mode) {
  if (practiceMode === mode) return;
  practiceMode = mode;
  saveSettings();
  const wasLive = liveModeActive;
  applyPracticeModeUI();
  if (wasLive) {
    reconfigureLiveMode();
  } else if (els.settingLiveAuto?.checked) {
    autoStartDone = true;
    startLiveMode();
  }
}

function applyPracticeModeUI() {
  const textActive = isTextMode();
  els.modeText?.classList.toggle('active', textActive);
  els.modeScore?.classList.toggle('active', !textActive);
  els.modeText?.setAttribute('aria-selected', textActive ? 'true' : 'false');
  els.modeScore?.setAttribute('aria-selected', textActive ? 'false' : 'true');
  els.appRoot?.classList.toggle('mode-text', textActive);
  els.appRoot?.classList.toggle('mode-score', !textActive);

  if (!textActive) {
    restoreWordScoreUI(words[currentIndex]);
  }

  renderQuizSummary();

  if (els.liveTranscriptPlaceholder) {
    els.liveTranscriptPlaceholder.textContent = isTextMode()
      ? 'Đọc đúng 100% (từ hoặc cụm từ) → tự chuyển tiếp'
      : 'Đọc từ → im lặng ngắn để chấm IPA bên dưới';
  }

  if (textActive) {
    els.serviceStatus.textContent = '● Chế độ text — không cần backend';
    els.serviceStatus.className = 'status-online';
  } else {
    checkBackend();
  }
}

function getHangoverMsSetting() {
  return getHangoverMs(parseFloat(els.settingSilenceSec?.value) || 0.35, isTextMode());
}

function micPhaseToState(phase) {
  const map = {
    [MIC_PHASE.OFF]: MIC_STATE.OFF,
    [MIC_PHASE.READY]: MIC_STATE.READY,
    [MIC_PHASE.HEARING]: MIC_STATE.HEARING,
    [MIC_PHASE.PROCESSING]: MIC_STATE.PROCESSING,
    [MIC_PHASE.COOLDOWN]: MIC_STATE.READY,
    [MIC_PHASE.SAMPLE]: MIC_STATE.SAMPLE,
  };
  return map[phase] ?? MIC_STATE.READY;
}

function createMicEngine() {
  return new MicEngine({
    hangoverMs: getHangoverMsSetting(),
    allowAudioOnly: isScoreMode(),
    cooldownMs: isScoreMode() ? 80 : undefined,
    skipUtteranceCooldown: isScoreMode(),
    onSpeechStart: () => {
      noteUserInput();
      if (isScoreMode()) {
        startPhraseRecording();
        startUtteranceCapture();
      }
    },
    onPhaseChange: (phase, label) => {
      if (phase === MIC_PHASE.OFF) {
        setMicState(MIC_STATE.OFF, label || 'Micro tắt');
        return;
      }
      refreshMicAvailabilityUi();
    },
    onLevel: (_rms, pct) => {
      updateMicLevelVisual(pct);
    },
    onUtteranceComplete: handleUtteranceComplete,
  });
}

function getApiBase() {
  return els.settingApiUrl.value.replace(/\/$/, '');
}

// ─── History (localStorage) ─────────────────────────────────────────────────

function getHistory() {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
}

function saveHistory(history) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function recordAttempt(word, passed, overallScore) {
  const history = getHistory();
  if (!history[word]) {
    history[word] = { attempts: 0, passedAt: null, bestScore: 0 };
  }
  history[word].attempts += 1;
  history[word].bestScore = Math.max(history[word].bestScore, overallScore);
  if (passed && !history[word].passedAt) {
    history[word].passedAt = new Date().toISOString();
  }
  saveHistory(history);
  updateHistoryBadge(word);
}

function updateHistoryBadge(word) {
  const h = getHistory()[word];
  els.historyBadge.textContent = h ? `${h.attempts} lần` : '0 lần';
}

function resetWordFailStreak() {
  wordFailStreak = 0;
}

/** Sau N lần đọc/chấm chưa đạt → tự phát mẫu */
function registerWordFailure() {
  if (isSamplePlaying) return;
  wordFailStreak += 1;
  if (wordFailStreak < SAMPLE_REPLAY_AFTER_FAILS) return;

  wordFailStreak = 0;
  if (isScoreMode()) {
    setScoreState('done', 'Nghe lại mẫu...');
  } else {
    showLiveHint(`Nghe lại mẫu (sai ${SAMPLE_REPLAY_AFTER_FAILS} lần)`, 'warn');
  }
  if (shouldAutoplaySample()) playSample();
}

// ─── Word navigation ────────────────────────────────────────────────────────

function renderWordList() {
  els.wordSelect.innerHTML = words
    .map((w, i) => {
      const prefix = w.emoji ? `${w.emoji} ` : '';
      return `<option value="${i}">${prefix}${w.word}</option>`;
    })
    .join('');
}

function clearPassAdvanceTimer() {
  if (passAdvanceTimer) {
    clearTimeout(passAdvanceTimer);
    passAdvanceTimer = null;
  }
  passAdvancePending = false;
  passAdvancePayload = null;
}

function scheduleAdvanceAfterPass(data, atIndex) {
  clearPassAdvanceTimer();
  passAdvancePending = true;
  passAdvancePayload = { data, atIndex };
  refreshMicAvailabilityUi();
  setScoreState('done', `✓ Đạt ${data.overall_score}% — chuyển từ sau ${PASS_ADVANCE_DELAY_MS / 1000}s`);

  passAdvanceTimer = setTimeout(() => {
    passAdvanceTimer = null;
    const payload = passAdvancePayload;
    passAdvancePayload = null;
    passAdvancePending = false;
    if (!payload || !liveModeActive || currentIndex !== payload.atIndex) {
      refreshMicAvailabilityUi();
      return;
    }
    void advanceAfterPass(payload.data);
  }, PASS_ADVANCE_DELAY_MS);
}

function flushPassAdvance() {
  if (!passAdvanceTimer || !passAdvancePayload) return false;
  clearTimeout(passAdvanceTimer);
  passAdvanceTimer = null;
  const payload = passAdvancePayload;
  passAdvancePayload = null;
  passAdvancePending = false;
  if (!liveModeActive || currentIndex !== payload.atIndex) {
    refreshMicAvailabilityUi();
    return false;
  }
  void advanceAfterPass(payload.data);
  return true;
}

function shouldAutoplaySample() {
  return Boolean(els.settingAutoplay?.checked && liveModeActive);
}

function getIdleSampleSec() {
  const sec = parseInt(els.settingIdleSampleSec?.value, 10);
  if (!Number.isFinite(sec) || sec <= 0) return 0;
  return Math.min(120, sec);
}

function clearIdleSampleTimer() {
  if (idleSampleTimer) {
    clearTimeout(idleSampleTimer);
    idleSampleTimer = null;
  }
}

function disarmIdleSampleTimer() {
  idleSampleArmed = false;
  clearIdleSampleTimer();
}

function noteUserInput() {
  if (!idleSampleArmed) return;
  scheduleIdleSample();
}

function scheduleIdleSample() {
  clearIdleSampleTimer();
  const sec = getIdleSampleSec();
  if (!sec || !words.length || !idleSampleArmed || !shouldAutoplaySample()) return;

  idleSampleTimer = setTimeout(() => {
    idleSampleTimer = null;
    if (!idleSampleArmed || !words.length) return;
    if (isSamplePlaying || isAdvancing || scoreApiBusy) {
      scheduleIdleSample();
      return;
    }
    playSample({
      fromIdle: true,
      onDone: () => {
        if (idleSampleArmed) scheduleIdleSample();
      },
    });
  }, sec * 1000);
}

function armIdleSampleTimer() {
  if (!shouldAutoplaySample()) {
    disarmIdleSampleTimer();
    return;
  }
  const sec = getIdleSampleSec();
  if (!sec) {
    disarmIdleSampleTimer();
    return;
  }
  idleSampleArmed = true;
  scheduleIdleSample();
}

function updateWordHero(index) {
  const w = words[index];
  if (!w) return;

  suppressWordSelectChange = true;
  els.wordSelect.value = String(index);
  suppressWordSelectChange = false;

  els.wordIndex.textContent = `${index + 1} / ${words.length}`;
  els.currentWord.textContent = w.word;
  els.currentIpa.textContent = w.ipa || '—';
  if (els.currentMeaning) {
    const parts = [];
    if (w.emoji) parts.push(w.emoji);
    if (w.meaning) parts.push(w.meaning);
    els.currentMeaning.textContent = parts.join(' ') || '';
    els.currentMeaning.classList.toggle('hidden', parts.length === 0);
  }
  updateHistoryBadge(w.word);
}

/** Index từ tiếp theo; từ cuối → quay về đầu bài */
function getNextWordIndex(fromIndex = currentIndex) {
  if (!words.length) return 0;
  return fromIndex >= words.length - 1 ? 0 : fromIndex + 1;
}

/** Chuyển từ sau khi đạt — không reset micro / rebuild toàn trang */
function advanceScoreWordLive(options = {}) {
  runWithPreservedScroll(() => {
    const { autoplay = false } = options;
    if (!words.length) return;

    const nextIndex = getNextWordIndex();

    clearPassAdvanceTimer();
    disarmIdleSampleTimer();

    currentIndex = nextIndex;
    sessionStorage.setItem(WORD_INDEX_KEY, String(currentIndex));

    updateWordHero(currentIndex);
    hideLiveHint();
    clearTextMatchTimer();
    clearScoreMatchTimer();
    lastScoredAtIndex = -1;
    resetWordFailStreak();
    els.btnRetry.classList.add('hidden');

    prepareMicForNextUtterance();
    syncScorePanelForWord(words[currentIndex]);
    updateQuizCurrentRow();
    persistQuizSession();

    if (autoplay && shouldAutoplaySample()) {
      playSample({ fromAutoplay: true });
    }
    armIdleSampleTimer();
  });
}

function showWord(index, options = {}) {
  const { autoplay = true, preserveLiveMic = false } = options;
  const idx = Number(index);
  if (!Number.isFinite(idx)) return;

  clearPassAdvanceTimer();
  disarmIdleSampleTimer();
  isAdvancing = false;

  currentIndex = Math.max(0, Math.min(idx, words.length - 1));
  sessionStorage.setItem(WORD_INDEX_KEY, String(currentIndex));
  const w = words[currentIndex];
  lastAppliedEvalSignature = '';

  updateWordHero(currentIndex);

  if (!preserveLiveMic || !liveModeActive) {
    resetEvaluationUI();
  } else {
    els.btnRetry.classList.add('hidden');
  }
  if (isScoreMode()) {
    syncScorePanelForWord(w, { force: !preserveLiveMic });
  }
  if (!preserveLiveMic || !liveModeActive) {
    clearLiveTranscript();
    hideLiveHint();
    clearTextMatchTimer();
    clearScoreMatchTimer();
    micEngine?.resetSession();
    syncTranscriptFromEngine();
  } else {
    clearTextMatchTimer();
    clearScoreMatchTimer();
    prepareMicForNextUtterance();
  }

  if (autoplay && shouldAutoplaySample()) {
    playSample({ fromAutoplay: true });
  }
  lastScoredAtIndex = -1;
  resetWordFailStreak();
  updateQuizCurrentRow();
  persistQuizSession();
  armIdleSampleTimer();
}

function resetEvaluationUI() {
  els.btnRetry.classList.add('hidden');
  if (!liveModeActive) {
    userAudioBlob = null;
    if (userAudioUrl) {
      URL.revokeObjectURL(userAudioUrl);
      userAudioUrl = null;
    }
  }
  serverAudioUrl = null;
}

function normalizeWordKey(word) {
  return String(word || '').toLowerCase().trim();
}

function loadEvalCache() {
  try {
    const raw = sessionStorage.getItem(EVAL_CACHE_KEY);
    if (!raw) return;
    Object.assign(lastEvaluations, JSON.parse(raw));
  } catch {
    /* ignore */
  }
}

function persistEvalCache() {
  try {
    sessionStorage.setItem(EVAL_CACHE_KEY, JSON.stringify(lastEvaluations));
  } catch {
    /* ignore */
  }
}

function cacheEvaluation(data) {
  if (!data?.word || !Array.isArray(data.phonemes) || !data.phonemes.length) return;
  const key = normalizeWordKey(data.word);
  lastEvaluations[key] = data;
  if (words[currentIndex] && normalizeWordKey(words[currentIndex].word) === key) {
    currentWordEvaluation = data;
  }
  persistEvalCache();
}

function getCachedEvaluation(word) {
  return lastEvaluations[normalizeWordKey(word)] || null;
}

function hasEvaluationForWord(word) {
  if (!word) return false;
  const key = normalizeWordKey(word.word || word);
  if (lastEvaluations[key]) return true;
  return Boolean(
    currentWordEvaluation && normalizeWordKey(currentWordEvaluation.word) === key,
  );
}

function beginScoringOverlay(options = {}) {
  if (!isScoreMode()) return;
  const preserve = options.preservePhonemeResults
    && els.phonemeContainer?.classList.contains('has-results');
  if (!preserve) {
    els.phonemeContainer?.classList.add('scoring');
    els.scoreSection?.classList.add('scoring');
  } else {
    els.scoreZone?.classList.add('scoring-live-rescore');
  }
  els.scoreZone?.classList.add('scoring');
}

function endScoringOverlay() {
  els.phonemeContainer?.classList.remove('scoring');
  els.scoreSection?.classList.remove('scoring');
  els.scoreZone?.classList.remove('scoring', 'scoring-live-rescore');
}

let lastAppliedEvalSignature = '';

function patchText(el, value) {
  if (el && el.textContent !== value) el.textContent = value;
}

function patchClass(el, className) {
  if (el && el.className !== className) el.className = className;
}

function evaluationSignature(data) {
  if (!data?.phonemes?.length) return '';
  const parts = data.phonemes.map(
    (p) => `${p.ipa}:${p.label}:${Math.round(p.score * 100)}:${p.suggestion || ''}`,
  );
  return `${normalizeWordKey(data.word)}|${data.overall_score}|${parts.join(',')}`;
}

function clearPhonemeIdleHint(container) {
  container?.querySelector('.phoneme-idle-hint')?.remove();
}

function createPendingPhonemeBoxHtml(ipa, index) {
  return `
    <div class="phoneme-box phoneme-box-pending" data-index="${index}">
      <div class="phoneme-char pending">${ipa}</div>
      <span class="phoneme-score">—</span>
      <span class="phoneme-suggestion phoneme-suggestion-slot" aria-hidden="true">&nbsp;</span>
    </div>
  `;
}

function createEmptyPhonemeBoxHtml(index) {
  return `
    <div class="phoneme-box phoneme-box-pending" data-index="${index}">
      <div class="phoneme-char pending">?</div>
      <span class="phoneme-score">—</span>
      <span class="phoneme-suggestion phoneme-suggestion-slot" aria-hidden="true">&nbsp;</span>
    </div>
  `;
}

/** Giữ DOM phoneme boxes — chỉ thêm/xóa khi số lượng đổi */
function ensurePhonemeBoxes(count, buildHtml) {
  const container = els.phonemeContainer;
  if (!container) return [];

  clearPhonemeIdleHint(container);
  let boxes = [...container.querySelectorAll('.phoneme-box')];

  while (boxes.length > count) {
    boxes[boxes.length - 1]?.remove();
    boxes = [...container.querySelectorAll('.phoneme-box')];
  }

  while (boxes.length < count) {
    const i = boxes.length;
    container.insertAdjacentHTML('beforeend', buildHtml(i));
    boxes = [...container.querySelectorAll('.phoneme-box')];
  }

  return boxes;
}

function patchPhonemeBoxPending(box, ipa, index) {
  const char = box.querySelector('.phoneme-char');
  if (char) {
    patchText(char, ipa);
    patchClass(char, 'phoneme-char pending');
  }
  const scoreEl = box.querySelector('.phoneme-score');
  patchText(scoreEl, '—');
  const sug = box.querySelector('.phoneme-suggestion');
  if (sug) {
    patchText(sug, '\u00a0');
    patchClass(sug, 'phoneme-suggestion phoneme-suggestion-slot');
    sug.setAttribute('aria-hidden', 'true');
  }
  patchClass(box, 'phoneme-box phoneme-box-pending');
  box.classList.remove('show-suggestion', 'active');
  box.dataset.index = String(index);
  delete box.dataset.start;
  delete box.dataset.end;
}

function patchPhonemeBoxResult(box, p, index, showSuggestionsAlways) {
  const char = box.querySelector('.phoneme-char');
  if (char) {
    patchText(char, p.ipa);
    patchClass(char, `phoneme-char ${p.label}`);
  }
  const scoreEl = box.querySelector('.phoneme-score');
  patchText(scoreEl, `${Math.round(p.score * 100)}%`);

  let sug = box.querySelector('.phoneme-suggestion');
  if (p.suggestion) {
    if (!sug) {
      sug = document.createElement('span');
      box.appendChild(sug);
    }
    patchText(sug, p.suggestion);
    patchClass(sug, 'phoneme-suggestion');
    sug.removeAttribute('aria-hidden');
  } else if (sug) {
    patchText(sug, '\u00a0');
    patchClass(sug, 'phoneme-suggestion phoneme-suggestion-slot');
    sug.setAttribute('aria-hidden', 'true');
  }

  const boxClass = `phoneme-box${showSuggestionsAlways && p.suggestion ? ' show-suggestion' : ''}`;
  patchClass(box, boxClass);
  box.dataset.index = String(index);
  const start = String(p.start);
  const end = String(p.end);
  if (box.dataset.start !== start) box.dataset.start = start;
  if (box.dataset.end !== end) box.dataset.end = end;
}

function updateScoreHero(overallScore, passed, options = {}) {
  const { pending = false } = options;
  if (!els.scoreSection) return;

  els.scoreSection.classList.remove('hidden');

  if (pending) {
    patchText(els.overallScore, '—');
    patchText(els.passStatus, 'Chưa chấm');
    patchClass(els.passStatus, 'pass-status pass-status-pending');
    return;
  }

  patchText(els.overallScore, `${overallScore}%`);
  patchText(els.passStatus, passed ? '✓ Đạt' : '✗ Chưa đạt');
  patchClass(els.passStatus, `pass-status ${passed ? 'passed' : 'failed'}`);
}

function syncPhonemeStripPending(targetPhonemes) {
  const container = els.phonemeContainer;
  if (!container) return;

  if (!targetPhonemes?.length) {
    container.querySelectorAll('.phoneme-box').forEach((box) => box.remove());
    container.classList.remove('has-results');
    let hint = container.querySelector('.phoneme-idle-hint');
    const hintText = `${getLiveSilenceHintText()} — chi tiết IPA`;
    if (!hint) {
      container.insertAdjacentHTML('beforeend', `<p class="phoneme-idle-hint">${hintText}</p>`);
    } else {
      patchText(hint, hintText);
    }
    return;
  }

  const boxes = ensurePhonemeBoxes(targetPhonemes.length, (i) => createPendingPhonemeBoxHtml(targetPhonemes[i], i));
  targetPhonemes.forEach((ipa, i) => patchPhonemeBoxPending(boxes[i], ipa, i));
  container.classList.remove('has-results');
}

function syncPhonemeStripResults(phonemes, showSuggestionsAlways = false) {
  const container = els.phonemeContainer;
  if (!container || !phonemes?.length) return;

  const boxes = ensurePhonemeBoxes(phonemes.length, createEmptyPhonemeBoxHtml);
  phonemes.forEach((p, i) => patchPhonemeBoxResult(boxes[i], p, i, showSuggestionsAlways));
  container.classList.add('has-results');
}

function syncScorePanelForWord(word, options = {}) {
  const { force = false } = options;
  if (!isScoreMode() || !word) return;

  endScoringOverlay();

  const cached = getCachedEvaluation(word.word);
  if (cached) {
    applyEvaluationDisplay(cached, { showSuggestionsAlways: liveModeActive, force });
    setScoreState('done', `Điểm ${cached.overall_score}%`);
    return;
  }

  if (
    !force
    && currentWordEvaluation
    && normalizeWordKey(currentWordEvaluation.word) === normalizeWordKey(word.word)
  ) {
    applyEvaluationDisplay(currentWordEvaluation, { showSuggestionsAlways: liveModeActive, force });
    setScoreState('done', `Điểm ${currentWordEvaluation.overall_score}%`);
    return;
  }

  lastAppliedEvalSignature = '';
  setScoreState('idle', 'Sẵn sàng chấm');
  updateScoreHero(0, false, { pending: true });
  syncPhonemeStripPending(word.phonemes || []);
}

function applyEvaluationDisplay(data, options = {}) {
  const { showSuggestionsAlways = false, force = false } = options;
  if (!data?.phonemes?.length) return false;

  const signature = evaluationSignature(data);
  if (!force && signature === lastAppliedEvalSignature) {
    endScoringOverlay();
    return true;
  }
  lastAppliedEvalSignature = signature;

  endScoringOverlay();
  currentWordEvaluation = data;

  const passScore = getPassThreshold();
  const allOk = data.phonemes.every((p) => p.label === 'ok');
  const passed = data.passed ?? (allOk || data.overall_score >= passScore);

  updateScoreHero(data.overall_score, passed);

  const nextAudioUrl = data.audio_url ? `${getApiBase()}${data.audio_url}` : null;
  if (serverAudioUrl !== nextAudioUrl) serverAudioUrl = nextAudioUrl;

  syncPhonemeStripResults(data.phonemes, showSuggestionsAlways);
  return true;
}

function setScoreHeroPending() {
  updateScoreHero(0, false, { pending: true });
}

function showScoreEvalError(message, wordIndex = currentIndex) {
  setScoreState('error', 'Lỗi chấm điểm');
  showLiveHint(message, 'mis');
  const w = words[wordIndex];
  const cached = w ? getCachedEvaluation(w.word) : null;
  if (cached) {
    applyEvaluationDisplay(cached, { showSuggestionsAlways: liveModeActive });
    setScoreState('done', `Điểm ${cached.overall_score}%`);
    return;
  }
  if (
    currentWordEvaluation
    && w
    && normalizeWordKey(currentWordEvaluation.word) === normalizeWordKey(w.word)
  ) {
    applyEvaluationDisplay(currentWordEvaluation, { showSuggestionsAlways: liveModeActive });
    setScoreState('done', `Điểm ${currentWordEvaluation.overall_score}%`);
    return;
  }
  restoreWordScoreUI(w);
}

function restoreWordScoreUI(word) {
  syncScorePanelForWord(word);
}

function renderPhonemeIdle(word = words[currentIndex]) {
  if (!isScoreMode()) return;
  syncPhonemeStripPending(word?.phonemes || []);
}

function renderPendingPhonemes(_phonemes) {
  renderPhonemeIdle(words[currentIndex]);
}

function renderEvaluationDisplay(data, options = {}) {
  return applyEvaluationDisplay(data, options);
}

function nextWord(options = {}) {
  if (!words.length) return;
  showWord(getNextWordIndex(), options);
}

function prevWord() {
  if (currentIndex > 0) {
    showWord(currentIndex - 1);
  }
}

// ─── Live mic (MicEngine + VAD năng lượng) ─────────────────────────────────

function initLiveSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    setMicState(MIC_STATE.OFF, 'Trình duyệt không hỗ trợ (dùng Chrome/Edge)');
    els.btnLiveToggle.disabled = true;
    return;
  }

  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = true;
  speechRecognition.interimResults = true;
  speechRecognition.lang = 'en-US';
  speechRecognition.maxAlternatives = 1;

  speechRecognition.onresult = (event) => {
    if (!micEngine || isListeningBlocked()) return;
    let interim = '';
    let finalPart = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const text = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalPart += text;
      else interim += text;
    }
    if (finalPart) micEngine.pushTranscript(finalPart, interim);
    else if (interim) micEngine.pushTranscript('', interim);
    if (finalPart || interim) noteUserInput();
    syncTranscriptFromEngine();
    updateRealtimeHint();
    if (isScoreMode() && liveModeActive && (finalPart || interim)) {
      startUtteranceCapture();
      startPhraseRecording();
      tryScheduleScoreEvaluate();
    }
    tryScheduleTextAdvance();
  };

  speechRecognition.onerror = (event) => {
    if (event.error === 'no-speech' || event.error === 'aborted') return;
    console.warn('SpeechRecognition error:', event.error);
    if (event.error === 'not-allowed') {
      setMicState(MIC_STATE.OFF, 'Bị chặn quyền micro');
      stopLiveMode();
    }
  };

  speechRecognition.onend = () => {
    if (liveModeActive && !speechRecognitionPaused && !isSamplePlaying) {
      try { speechRecognition.start(); } catch { /* ignore */ }
    }
  };
}

function syncTranscriptFromEngine() {
  if (!micEngine) return;
  const rawFinal = micEngine.transcriptFinal.trim();
  const rawInterim = micEngine.transcriptInterim;
  const combined = extractSpokenText(rawFinal, rawInterim);
  const w = words[currentIndex];

  let displayFinal = rawFinal;
  let displayInterim = rawInterim;
  if (isTextMode() && w?.word && combined) {
    const snippet = extractPracticeMatchSnippet(combined, w.word);
    if (snippet) {
      displayFinal = snippet;
      displayInterim = '';
    }
  }

  els.liveTranscriptFinal.textContent = displayFinal;
  els.liveTranscriptInterim.textContent = displayInterim;
  const hasText = Boolean(displayFinal || displayInterim);
  els.liveTranscriptPlaceholder.classList.toggle('hidden', !!hasText);

  if (!isScoreMode()) {
    const match = spokenMatchesTarget(combined || rawFinal, w?.word);
    els.liveTranscriptInterim.classList.toggle('match', match);
    els.liveTranscriptFinal.classList.toggle('match', match);
  } else {
    els.liveTranscriptInterim.classList.remove('match');
    els.liveTranscriptFinal.classList.remove('match');
  }
}

function getSpokenWord() {
  return micEngine?.getSpokenWord() || '';
}

function clearTextMatchTimer() {
  if (textMatchTimer) {
    clearTimeout(textMatchTimer);
    textMatchTimer = null;
  }
}

function clearScoreMatchTimer() {
  if (scoreMatchTimer) {
    clearTimeout(scoreMatchTimer);
    scoreMatchTimer = null;
  }
}

/** Chế độ chấm điểm: SR nghe được từ → im lặng hangover → tự chấm (không phụ thuộc VAD) */
function tryScheduleScoreEvaluate() {
  if (!isScoreMode() || !liveModeActive || isListeningBlocked() || isAdvancing || scoreApiBusy) {
    clearScoreMatchTimer();
    return;
  }
  if (lastScoredAtIndex === currentIndex) {
    clearScoreMatchTimer();
    return;
  }
  if (!shouldAutoScoreOnUtteranceEnd({
    practiceMode,
    autoEvaluate: els.settingAutoEvaluate?.checked,
  })) {
    return;
  }

  const spoken = getSpokenWord()?.trim();
  if (!spoken) {
    clearScoreMatchTimer();
    return;
  }

  clearScoreMatchTimer();
  const hangMs = getHangoverMsSetting();

  scoreMatchTimer = setTimeout(async () => {
    scoreMatchTimer = null;
    if (!liveModeActive || !isScoreMode() || scoreApiBusy || isAdvancing || isListeningBlocked()) {
      return;
    }
    if (!getSpokenWord()?.trim()) return;
    await processScoreUtterance();
  }, hangMs);
}

/** Chế độ text: thấy khớp → chuyển từ ngay (không chờ im lặng) */
function tryScheduleTextAdvance() {
  if (!isTextMode() || !liveModeActive || isAdvancing || isListeningBlocked()) {
    clearTextMatchTimer();
    return;
  }

  const w = words[currentIndex];
  const spoken = getSpokenWord();
  if (!w || !spoken || !spokenMatchesTarget(spoken, w.word)) {
    clearTextMatchTimer();
    return;
  }

  if (textMatchTimer) return;

  showLiveHint(`✓ "${spoken}" khớp — chuyển từ...`, 'ok');
  textMatchTimer = setTimeout(async () => {
    textMatchTimer = null;
    if (!liveModeActive || isAdvancing || !isTextMode()) return;
    const latest = getSpokenWord();
    if (latest && spokenMatchesTarget(latest, w.word)) {
      await processTextUtterance(latest);
    }
  }, TEXT_MATCH_DELAY_MS);
}

function showLiveHint(message, type = 'warn', options = {}) {
  if (!els.liveHint) return;
  if (isScoreMode() && !options.force) return;
  els.liveHint.textContent = message;
  els.liveHint.className = `live-hint ${type}`;
  els.liveHint.classList.remove('hidden');
}

function hideLiveHint() {
  if (!els.liveHint) return;
  els.liveHint.classList.add('hidden');
  els.liveHint.textContent = '';
}

// ─── PCM capture (score mode) — ổn định hơn MediaRecorder ghép chunk ───────

function ensurePcmCaptureGraph() {
  if (pcmCaptureNode || !micSourceNode || !audioContext) return;

  pcmCaptureNode = audioContext.createScriptProcessor(2048, 1, 1);
  pcmSilentGain = audioContext.createGain();
  pcmSilentGain.gain.value = 0;
  pcmCaptureNode.onaudioprocess = (e) => {
    if (!utteranceCapturing) return;
    utterancePcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  };
  micSourceNode.connect(pcmCaptureNode);
  pcmCaptureNode.connect(pcmSilentGain);
  pcmSilentGain.connect(audioContext.destination);
}

function startUtteranceCapture() {
  if (!isScoreMode() || !liveModeActive || isListeningBlocked()) return;
  if (!utteranceCapturing) utterancePcmChunks = [];
  utteranceCapturing = true;
  ensurePcmCaptureGraph();
}

function stopUtteranceCapture() {
  utteranceCapturing = false;
}

function teardownPcmCapture() {
  stopUtteranceCapture();
  utterancePcmChunks = [];
  if (pcmCaptureNode) {
    try { pcmCaptureNode.disconnect(); } catch { /* ignore */ }
    pcmCaptureNode.onaudioprocess = null;
    pcmCaptureNode = null;
  }
  if (pcmSilentGain) {
    try { pcmSilentGain.disconnect(); } catch { /* ignore */ }
    pcmSilentGain = null;
  }
}

function pcmFloat32ToWavBlob(floatSamples, sampleRate) {
  const pcm = new Int16Array(floatSamples.length);
  for (let i = 0; i < floatSamples.length; i++) {
    const sample = Math.max(-1, Math.min(1, floatSamples[i]));
    pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }

  const wavBuf = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(wavBuf);
  const writeStr = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + pcm.length * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, pcm.length * 2, true);
  let off = 44;
  for (let i = 0; i < pcm.length; i++, off += 2) {
    view.setInt16(off, pcm[i], true);
  }

  return new Blob([wavBuf], { type: 'audio/wav' });
}

async function resampleFloat32ToWav(float32Data, srcSampleRate) {
  const targetSr = 16000;
  const maxSamples = Math.floor(srcSampleRate * MAX_SCORE_AUDIO_SEC);
  const startSample = Math.max(0, float32Data.length - maxSamples);
  const sliceLen = float32Data.length - startSample;
  const slice = float32Data.subarray(startSample);

  const offline = new OfflineAudioContext(
    1,
    Math.max(1, Math.ceil(sliceLen * targetSr / srcSampleRate)),
    targetSr,
  );
  const sliceBuf = offline.createBuffer(1, sliceLen, srcSampleRate);
  sliceBuf.copyToChannel(slice, 0);
  const src = offline.createBufferSource();
  src.buffer = sliceBuf;
  src.connect(offline.destination);
  src.start();
  const rendered = await offline.startRendering();
  return pcmFloat32ToWavBlob(rendered.getChannelData(0), targetSr);
}

async function buildWavFromPcmChunks(chunks, srcSampleRate) {
  if (!chunks?.length) return null;
  const totalLen = chunks.reduce((n, c) => n + c.length, 0);
  const minSamples = Math.floor(srcSampleRate * (MIN_SPEECH_MS / 1000) * 0.75);
  if (totalLen < minSamples) return null;

  const merged = new Float32Array(totalLen);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return resampleFloat32ToWav(merged, srcSampleRate);
}

function setupMediaRecorder() {
  if (!micStream || isScoreMode()) return;
  if (phraseRecorder?.state === 'recording') return;

  stopRingRecorder();

  liveMimeType = pickRecorderMimeType();

  liveMediaRecorder = new MediaRecorder(micStream, { mimeType: liveMimeType });
  liveMediaRecorder.ondataavailable = (e) => {
    if (e.data.size <= 0) return;
    audioRingChunks.push(e.data);
    if (audioRingChunks.length > MAX_RING_CHUNKS) audioRingChunks.shift();
  };
  liveMediaRecorder.start(RING_CHUNK_MS);
}

function stopRingRecorder() {
  if (!liveMediaRecorder) return;
  if (liveMediaRecorder.state !== 'inactive') {
    try { liveMediaRecorder.stop(); } catch { /* ignore */ }
  }
  liveMediaRecorder = null;
}

function resumeRingRecorder() {
  if (!micStream || !liveModeActive || isScoreMode()) return;
  if (phraseRecorder?.state === 'recording') return;
  if (!liveMediaRecorder || liveMediaRecorder.state === 'inactive') {
    setupMediaRecorder();
  }
}

function pickRecorderMimeType() {
  if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) return 'audio/webm;codecs=opus';
  if (MediaRecorder.isTypeSupported('audio/webm')) return 'audio/webm';
  if (MediaRecorder.isTypeSupported('audio/mp4')) return 'audio/mp4';
  return 'audio/webm';
}

/** Ghi âm 1 câu — webm/mp4 từ phraseRecorder */
function startPhraseRecording() {
  if (!micStream || phraseRecorder?.state === 'recording') return;

  stopPhraseRecordingSync();
  stopRingRecorder();
  phraseChunks = [];
  liveMimeType = pickRecorderMimeType();

  try {
    phraseRecorder = new MediaRecorder(micStream, { mimeType: liveMimeType });
    phraseRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) phraseChunks.push(e.data);
    };
    phraseRecorder.start();
  } catch (e) {
    console.warn('phraseRecorder start:', e);
    phraseRecorder = null;
    resumeRingRecorder();
  }
}

function phraseBlobFromChunks() {
  if (!phraseChunks.length) return null;
  if (phraseChunks.length === 1) return phraseChunks[0];
  return phraseChunks.reduce((best, c) => (c.size > best.size ? c : best), phraseChunks[0]);
}

function stopPhraseRecordingSync() {
  if (phraseRecorder?.state === 'recording') {
    try { phraseRecorder.stop(); } catch { /* ignore */ }
  }
}

function stopPhraseRecording() {
  return new Promise((resolve) => {
    const finish = () => {
      const blob = phraseBlobFromChunks();
      phraseRecorder = null;
      phraseChunks = [];
      resumeRingRecorder();
      resolve(blob);
    };

    if (!phraseRecorder || phraseRecorder.state === 'inactive') {
      finish();
      return;
    }

    phraseRecorder.onstop = finish;

    const stopNow = () => {
      try {
        phraseRecorder.stop();
      } catch {
        finish();
      }
    };

    try {
      phraseRecorder.requestData();
    } catch { /* ignore */ }
    setTimeout(stopNow, 120);
  });
}

/** Live score: ưu tiên webm từ phraseRecorder, PCM dự phòng */
async function getScoreAudioBlob() {
  if (e2eInjectScoreBlob) {
    const injected = e2eInjectScoreBlob;
    e2eInjectScoreBlob = null;
    stopUtteranceCapture();
    utterancePcmChunks = [];
    await stopPhraseRecording();
    return injected;
  }

  stopUtteranceCapture();
  const pcmChunks = utterancePcmChunks;
  utterancePcmChunks = [];

  const phraseBlob = await stopPhraseRecording();
  if (phraseBlob && phraseBlob.size >= MIN_BLOB_BYTES) {
    return phraseBlob;
  }

  if (pcmChunks.length && audioContext) {
    try {
      const wav = await buildWavFromPcmChunks(pcmChunks, audioContext.sampleRate);
      if (wav && wav.size >= MIN_BLOB_BYTES) return wav;
    } catch (e) {
      console.warn('PCM → WAV failed:', e);
    }
  }

  if (phraseBlob && phraseBlob.size > 0) return phraseBlob;
  return null;
}

async function flushRecorderData() {
  if (!liveMediaRecorder || liveMediaRecorder.state !== 'recording') return;
  return new Promise((resolve) => {
    const handler = (e) => {
      if (e.data.size > 0) audioRingChunks.push(e.data);
      liveMediaRecorder.removeEventListener('dataavailable', handler);
      resolve();
    };
    liveMediaRecorder.addEventListener('dataavailable', handler);
    try { liveMediaRecorder.requestData(); } catch { resolve(); }
    setTimeout(resolve, 80);
  });
}

/** Chuyển blob → WAV 16kHz mono (backend/ffmpeg ổn định) */
async function convertBlobToWav(blob) {
  if (!audioContext) audioContext = new AudioContext();
  if (audioContext.state === 'suspended') await audioContext.resume();

  const arrayBuffer = await blob.arrayBuffer();
  const decoded = await audioContext.decodeAudioData(arrayBuffer.slice(0));

  const merged = new Float32Array(decoded.length);
  for (let i = 0; i < decoded.length; i++) {
    let sum = 0;
    for (let c = 0; c < decoded.numberOfChannels; c++) {
      sum += decoded.getChannelData(c)[i];
    }
    merged[i] = sum / decoded.numberOfChannels;
  }

  return resampleFloat32ToWav(merged, decoded.sampleRate);
}

async function prepareUploadBlob(blob) {
  if (!blob || blob.size < MIN_BLOB_BYTES) {
    throw new Error('Audio quá ngắn — nói rõ hơn và thử lại');
  }
  if (blob.type === 'audio/wav' && blob.size >= MIN_UPLOAD_BYTES) {
    return { blob, filename: 'recording.wav' };
  }
  const wav = await convertBlobToWav(blob);
  if (wav.size < MIN_UPLOAD_BYTES) {
    throw new Error('WAV quá ngắn sau khi xử lý');
  }
  return { blob: wav, filename: 'recording.wav' };
}

async function handleUtteranceComplete(payload) {
  if (!liveModeActive || isListeningBlocked() || isAdvancing) return;
  if (payload?.spoken) noteUserInput();

  if (isTextMode()) {
    await processTextUtterance(payload.spoken);
    return;
  }

  // Score mode: SR + tryScheduleScoreEvaluate xử lý chấm — tránh chấm/VAD trùng
}

/** Score mode: im lặng sau câu → tự gọi API chấm */
async function processScoreUtterance() {
  if (scoreApiBusy) return;
  if (lastScoredAtIndex === currentIndex) return;
  noteUserInput();

  clearScoreMatchTimer();

  await new Promise((r) => setTimeout(r, 80));

  const blob = await getScoreAudioBlob();
  if (!blob || blob.size < MIN_BLOB_BYTES) {
    setScoreState('error', 'Không đủ audio — nói rõ hơn');
    showLiveHint('Không đủ audio — nói rõ hơn', 'warn');
    prepareMicForNextUtterance();
    return;
  }

  userAudioBlob = blob;
  if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
  userAudioUrl = URL.createObjectURL(blob);

  await evaluateRecording(blob, { fromLive: true });
}

/** Text mode: khớp → chuyển từ tiếp theo */
async function processTextUtterance(spoken) {
  if (isAdvancing) return;
  clearTextMatchTimer();

  const w = words[currentIndex];
  const word = spoken || getSpokenWord();

  if (!word) {
    showLiveHint('Không nghe rõ — thử đọc lại', 'warn');
    return;
  }

  if (!spokenMatchesTarget(word, w.word)) {
    const score = textSimilarityPercent(word, w.word);
    const need = getTextPassThreshold();
    const display = extractPracticeMatchSnippet(word, w.word) || word;
    showLiveHint(`✗ "${display}" — ${score}% (cần ≥${need}%) · "${w.word}"`, 'mis');
    registerWordFailure();
    micEngine?.clearTranscript();
    syncTranscriptFromEngine();
    return;
  }

  isAdvancing = true;
  refreshMicAvailabilityUi();
  resetWordFailStreak();
  const score = textSimilarityPercent(word, w.word);
  const need = getTextPassThreshold();
  showLiveHint(
    score >= 100 ? `✓ Đúng "${word}"!` : `✓ "${word}" ~${score}% (≥${need}%)`,
    'ok',
  );
  recordAttempt(w.word, true, score);
  recordQuizSessionResult(w.word, score, true, 'text', currentIndex);
  await new Promise((r) => setTimeout(r, 100));
  hideLiveHint();
  micEngine?.clearTranscript();
  syncTranscriptFromEngine();
  nextWord();
  isAdvancing = false;
  refreshMicAvailabilityUi();
}

function updateRealtimeHint() {
  if (isScoreMode()) return;

  const w = words[currentIndex];
  if (!w || isAdvancing) return;

  const spoken = getSpokenWord();
  const display = isTextMode() && w?.word
    ? (extractPracticeMatchSnippet(spoken, w.word) || spoken)
    : spoken;
  if (!spoken) {
    if (!isTextMode()) hideLiveHint();
    return;
  }

  if (spokenMatchesTarget(spoken, w.word)) {
    const score = textSimilarityPercent(spoken, w.word);
    const need = getTextPassThreshold();
    const msg = score >= 100
      ? `✓ "${display}" — khớp!`
      : `✓ "${display}" ~${score}% (≥${need}%)`;
    showLiveHint(msg, 'ok');
  } else {
    const score = textSimilarityPercent(spoken, w.word);
    const need = getTextPassThreshold();
    showLiveHint(`✗ "${display}" — ${score}% (cần ≥${need}%) · "${w.word}"`, 'mis');
  }
}

function clearLiveTranscript() {
  micEngine?.clearTranscript();
  syncTranscriptFromEngine();
  hideLiveHint();
}

function updateLiveModeChrome() {
  refreshSilenceHints();
  els.recordingIndicator.classList.remove('hidden');
  els.phonemeContainer.classList.toggle('live-mode', isScoreMode());
  if (isScoreMode()) {
    restoreWordScoreUI(words[currentIndex]);
  }
  hideLiveHint();
}

function attachLivePipeline() {
  liveMimeType = pickRecorderMimeType();
  audioRingChunks = [];

  stopPhraseRecordingSync();
  phraseRecorder = null;
  phraseChunks = [];
  stopRingRecorder();
  teardownPcmCapture();

  if (isScoreMode()) {
    ensurePcmCaptureGraph();
  } else {
    setupMediaRecorder();
  }

  if (micEngine) {
    micEngine.stop();
    micEngine = null;
  }
  clearPassAdvanceTimer();
  isAdvancing = false;
  clearTextMatchTimer();
  clearScoreMatchTimer();

  micEngine = createMicEngine();
  micEngine.setHangoverMs(getHangoverMsSetting());
  startVadLoop();
  liveModeActive = true;
  micEngine.start();
  updateLiveModeChrome();
  armIdleSampleTimer();
}

function reconfigureLiveMode() {
  if (!micStream) return;
  attachLivePipeline();
  syncMicStateFromEngine();
}

async function startLiveMode(options = {}) {
  const { silent = false } = options;
  if (liveModeActive) return;

  try {
    autoStartDone = true;
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });

    if (!audioContext) audioContext = new AudioContext();
    if (audioContext.state === 'suspended') await audioContext.resume();

    micSourceNode = audioContext.createMediaStreamSource(micStream);
    liveAnalyser = audioContext.createAnalyser();
    liveAnalyser.fftSize = 1024;
    liveAnalyser.smoothingTimeConstant = 0.3;
    micSourceNode.connect(liveAnalyser);

    attachLivePipeline();

    if (speechRecognition) {
      try { speechRecognition.start(); } catch (e) {
        console.warn('SpeechRecognition start:', e);
      }
    }
  } catch (err) {
    if (!silent) alert('Không thể bật micro: ' + err.message);
    throw err;
  }
}

function stopLiveMode() {
  if (!liveModeActive) return;

  disarmIdleSampleTimer();
  liveModeActive = false;
  clearPassAdvanceTimer();
  isAdvancing = false;
  clearTextMatchTimer();
  clearScoreMatchTimer();
  micEngine?.stop();
  micEngine = null;
  teardownPcmCapture();
  stopPhraseRecordingSync();
  phraseRecorder = null;
  phraseChunks = [];

  if (sampleResumeTimer) {
    clearTimeout(sampleResumeTimer);
    sampleResumeTimer = null;
  }
  isSamplePlaying = false;
  speechRecognitionPaused = false;
  speechSynthesis?.cancel();

  if (speechRecognition) {
    try { speechRecognition.stop(); } catch { /* ignore */ }
  }

  if (liveMediaRecorder?.state !== 'inactive') {
    try { liveMediaRecorder.stop(); } catch { /* ignore */ }
  }
  liveMediaRecorder = null;

  if (micSourceNode) {
    try { micSourceNode.disconnect(); } catch { /* ignore */ }
    micSourceNode = null;
  }
  liveAnalyser = null;

  if (micStream) {
    micStream.getTracks().forEach((t) => t.stop());
    micStream = null;
  }

  if (vadAnimationId) {
    cancelAnimationFrame(vadAnimationId);
    vadAnimationId = null;
  }
  resetMicLevelVisual();

  setMicState(MIC_STATE.OFF, 'Micro tắt');
  els.recordingIndicator.classList.add('hidden');
  els.phonemeContainer.classList.remove('live-mode');
}

function toggleLiveMode() {
  if (liveModeActive) stopLiveMode();
  else startLiveMode().then(() => armIdleSampleTimer()).catch(() => {});
}

function startVadLoop() {
  if (!liveAnalyser || !micEngine) return;
  if (vadAnimationId) {
    cancelAnimationFrame(vadAnimationId);
    vadAnimationId = null;
  }

  const buf = new Uint8Array(liveAnalyser.fftSize);

  const tick = () => {
    if (!liveModeActive || !liveAnalyser || !micEngine) return;

    liveAnalyser.getByteTimeDomainData(buf);
    const listening = !isSamplePlaying && !isListeningBlocked();

    if (isSamplePlaying) {
      updateMicLevelVisual(100);
      vadAnimationId = requestAnimationFrame(tick);
      return;
    }

    if (!listening) {
      updateMicLevelVisual(0);
      vadAnimationId = requestAnimationFrame(tick);
      return;
    }

    const rms = computeRms(buf);
    micEngine.tick(rms);
    vadAnimationId = requestAnimationFrame(tick);
  };
  tick();
}

function beginSamplePlayback() {
  if (sampleResumeTimer) {
    clearTimeout(sampleResumeTimer);
    sampleResumeTimer = null;
  }
  isSamplePlaying = true;
  setMicState(MIC_STATE.SAMPLE, 'Đang phát mẫu...');
  updateMicLevelVisual(100);

  if (!liveModeActive) return;

  speechRecognitionPaused = true;
  stopPhraseRecordingSync();
  phraseChunks = [];
  stopUtteranceCapture();
  utterancePcmChunks = [];
  clearScoreMatchTimer();
  stopRingRecorder();
  micEngine?.setSampleMode(true);
  micEngine?.pause();
  clearLiveTranscript();

  if (speechRecognition) {
    try { speechRecognition.stop(); } catch { /* ignore */ }
  }
}

function endSamplePlayback() {
  if (!isSamplePlaying) return;
  if (sampleResumeTimer) clearTimeout(sampleResumeTimer);

  sampleResumeTimer = setTimeout(() => {
    sampleResumeTimer = null;
    if (!isSamplePlaying) return;

    isSamplePlaying = false;
    speechRecognitionPaused = false;

    if (liveModeActive) {
      micEngine?.setSampleMode(false);
      micEngine?.resume();
      resumeRingRecorder();
      if (speechRecognition) {
        try { speechRecognition.start(); } catch { /* ignore */ }
      }
      setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    } else {
      setMicState(MIC_STATE.OFF, 'Micro tắt');
    }
    updateMicLevelVisual(0);
  }, SAMPLE_TAIL_MS);
}

function isListeningBlocked() {
  return isSamplePlaying || speechRecognitionPaused;
}

// ─── Audio: TTS sample ──────────────────────────────────────────────────────

function playSample(options = {}) {
  const { onDone, fromIdle = false, fromAutoplay = false } = options;
  if (!fromIdle && !fromAutoplay) noteUserInput();

  const w = words[currentIndex];
  beginSamplePlayback();

  const finishSample = () => {
    endSamplePlayback();
    onDone?.();
  };

  if (w.audio_sample_url) {
    const audio = new Audio(w.audio_sample_url);
    audio.onended = finishSample;
    audio.onerror = finishSample;
    audio.play().catch(finishSample);
    return;
  }

  if ('speechSynthesis' in window) {
    const utter = new SpeechSynthesisUtterance(w.word);
    configureSampleUtterance(utter);
    let finished = false;
    const done = () => {
      if (finished) return;
      finished = true;
      finishSample();
    };
    utter.onend = done;
    utter.onerror = done;
    speechSynthesis.cancel();
    speechSynthesis.speak(utter);

    const maxMs = Math.max(2500, w.word.length * 180);
    setTimeout(() => {
      if (isSamplePlaying && !speechSynthesis.speaking) done();
    }, maxMs);
    return;
  }

  finishSample();
}

// ─── Evaluation API ─────────────────────────────────────────────────────────

async function evaluateRecording(blob = null, options = {}) {
  const { fromLive = false } = options;
  const evalWordIndex = currentIndex;
  const w = words[evalWordIndex];
  const audioBlob = blob || userAudioBlob;
  if (!audioBlob || !w) return;
  if (scoreApiBusy) return;

  return runWithPreservedScrollAsync(async () => {
  clearPassAdvanceTimer();
  scoreApiBusy = true;
  refreshMicAvailabilityUi();

  setScoreState('scoring', 'Đang chấm điểm...');
  if (!fromLive) els.spinner.classList.remove('hidden');
  beginScoringOverlay({
    preservePhonemeResults: fromLive && els.phonemeContainer?.classList.contains('has-results'),
  });

  try {
    let uploadBlob;
    let filename;
    try {
      ({ blob: uploadBlob, filename } = await prepareUploadBlob(audioBlob));
    } catch (prepErr) {
      let msg = prepErr.message || 'Không xử lý được audio';
      if (/decode|encoding|Unable to decode/i.test(msg)) {
        msg = 'Không đọc được audio — nói rõ hơn (~0.5s) rồi thử lại';
      }
      setScoreState('error', 'Lỗi audio');
      showLiveHint('Lỗi audio: ' + msg, 'mis');
      showScoreEvalError('Lỗi audio: ' + msg, evalWordIndex);
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadBlob, filename);
    formData.append('target_word', w.word);
    formData.append('target_ipa', w.ipa);
    formData.append('target_phonemes', JSON.stringify(w.phonemes || []));

    const res = await fetch(`${getApiBase()}/api/v1/evaluate`, {
      method: 'POST',
      body: formData,
    });

    const raw = await res.text();
    let data;
    try {
      data = JSON.parse(raw);
    } catch {
      data = { error: raw || 'Phản hồi không hợp lệ từ server' };
    }

    if (!res.ok) {
      let msg = typeof data.detail === 'object'
        ? (data.detail?.error || JSON.stringify(data.detail))
        : (data.detail || data.error || `HTTP ${res.status}`);
      if (/ffmpeg failed/i.test(msg)) {
        msg = 'File audio không hợp lệ — nói rõ hơn (~0.5s) rồi thử lại';
      }
      setScoreState('error', 'Lỗi chấm điểm');
      showScoreEvalError('Lỗi chấm điểm: ' + msg, evalWordIndex);
      return;
    }

    renderEvaluation(data, { fromLive, wordIndex: evalWordIndex });
    if (fromLive && liveModeActive) {
      lastScoredAtIndex = evalWordIndex;
    }
  } catch (err) {
    const msg = `Không kết nối backend (${getApiBase()}). Chạy: ./run_backend.sh`;
    setScoreState('error', 'Lỗi kết nối');
    if (fromLive) {
      showScoreEvalError(msg, evalWordIndex);
    } else if (!blob) {
      alert(msg + '\n\n' + err.message);
    }
  } finally {
    scoreApiBusy = false;
    if (!fromLive) els.spinner.classList.add('hidden');
    refreshMicAvailabilityUi();
  }
  });
}

function renderEvaluation(data, options = {}) {
  runWithPreservedScroll(() => {
  const { fromLive = false, wordIndex = currentIndex } = options;
  const atIndex = Math.min(Math.max(0, wordIndex), words.length - 1);

  cacheEvaluation(data);
  if (!renderEvaluationDisplay(data, { showSuggestionsAlways: fromLive || liveModeActive })) {
    showScoreEvalError('Phản hồi thiếu dữ liệu phoneme', atIndex);
    return;
  }

  setScoreState('done', `Điểm ${data.overall_score}%`);

  const passScore = getPassThreshold();
  const allOk = data.phonemes.every((p) => p.label === 'ok');
  const passed = data.passed ?? (allOk || data.overall_score >= passScore);

  recordAttempt(data.word, passed, data.overall_score);
  recordQuizSessionResult(data.word, data.overall_score, passed, 'score', atIndex);

  if (passed) {
    resetWordFailStreak();
    els.btnRetry.classList.add('hidden');
    if (fromLive && liveModeActive && atIndex === currentIndex) {
      scheduleAdvanceAfterPass(data, atIndex);
    }
  } else {
    els.btnRetry.classList.remove('hidden');
    registerWordFailure();
    if (fromLive && liveModeActive && atIndex === currentIndex) {
      lastScoredAtIndex = -1;
      prepareMicForNextUtterance();
    }
  }
  });
}

async function advanceAfterPass(data) {
  const atLast = currentIndex >= words.length - 1;

  isAdvancing = true;
  refreshMicAvailabilityUi();
  clearScoreMatchTimer();
  hideLiveHint();

  if (atLast) {
    setScoreState('done', `Hết bài — từ đầu · ${data.overall_score}%`);
  }

  if (liveModeActive && isScoreMode()) {
    advanceScoreWordLive({ autoplay: false });
  } else {
    prepareMicForNextUtterance();
    nextWord({ autoplay: false, preserveLiveMic: liveModeActive });
  }
  isAdvancing = false;
  refreshMicAvailabilityUi();
}

function renderPhonemeResults(phonemes, showSuggestionsAlways = false) {
  syncPhonemeStripResults(phonemes, showSuggestionsAlways);
}

function bindPhonemeDelegation() {
  if (!els.phonemeContainer || els.phonemeContainer.dataset.bound) return;
  els.phonemeContainer.dataset.bound = '1';

  els.phonemeContainer.addEventListener('click', (e) => {
    const box = e.target.closest('.phoneme-box');
    if (box) replaySegment(box);
  });

  els.phonemeContainer.addEventListener('touchstart', (e) => {
    const box = e.target.closest('.phoneme-box');
    if (!box) return;
    e.preventDefault();
    box.classList.toggle('show-suggestion');
  }, { passive: false });
}

function bindPhonemeBoxEvents() {
  /* delegated — bindPhonemeDelegation */
}

// ─── Segment replay ─────────────────────────────────────────────────────────

async function replaySegment(box) {
  const start = parseFloat(box.dataset.start);
  const end = parseFloat(box.dataset.end);

  els.phonemeContainer.querySelectorAll('.phoneme-box').forEach((b) => b.classList.remove('active'));
  box.classList.add('active');

  const audioSrc = serverAudioUrl || userAudioUrl;
  if (!audioSrc) return;

  if (serverAudioUrl) {
    // Use HTMLAudio with time range (approximate)
    const audio = new Audio(audioSrc);
    audio.currentTime = start;
    audio.play();
    setTimeout(() => {
      audio.pause();
      box.classList.remove('active');
    }, (end - start) * 1000 + 100);
    return;
  }

  // Slice user blob via Web Audio API
  try {
    if (!audioContext) audioContext = new AudioContext();
    const res = await fetch(userAudioUrl);
    const buf = await res.arrayBuffer();
    const decoded = await audioContext.decodeAudioData(buf);
    const sr = decoded.sampleRate;
    const s = Math.floor(start * sr);
    const e = Math.floor(end * sr);
    const slice = audioContext.createBuffer(
      decoded.numberOfChannels,
      e - s,
      sr,
    );
    for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
      slice.copyToChannel(decoded.getChannelData(ch).slice(s, e), ch);
    }
    const source = audioContext.createBufferSource();
    source.buffer = slice;
    source.connect(audioContext.destination);
    source.onended = () => box.classList.remove('active');
    source.start();
  } catch {
    new Audio(userAudioUrl).play();
  }
}

// ─── Backend health ─────────────────────────────────────────────────────────

async function checkBackend() {
  if (isTextMode()) {
    els.serviceStatus.textContent = '● Chế độ text — không cần backend';
    els.serviceStatus.className = 'status-online';
    return;
  }
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(`${getApiBase()}/api/v1/health`, { signal: controller.signal });
    clearTimeout(timeoutId);
    if (res.ok) {
      const data = await res.json();
      els.serviceStatus.textContent = `● Backend: online (${data.alignment_method}/${data.scoring_method})`;
      els.serviceStatus.className = 'status-online';
    } else {
      throw new Error('not ok');
    }
  } catch {
    els.serviceStatus.textContent = '● Backend: offline — chạy uvicorn main:app --port 8000';
    els.serviceStatus.className = 'status-offline';
  }
}

// ─── Events ─────────────────────────────────────────────────────────────────

function bindEvents() {
  els.modeText?.addEventListener('click', () => setPracticeMode(PRACTICE_MODE.TEXT));
  els.modeScore?.addEventListener('click', () => setPracticeMode(PRACTICE_MODE.SCORE));
  els.btnPlaySample.addEventListener('click', playSample);
  els.btnLiveToggle.addEventListener('click', toggleLiveMode);
  els.btnRetry.addEventListener('click', () => {
    els.btnRetry.classList.add('hidden');
    lastScoredAtIndex = -1;
    resetWordFailStreak();
    clearLiveTranscript();
    hideLiveHint();
    restoreWordScoreUI(words[currentIndex]);
  });
  els.btnPrev.addEventListener('click', prevWord);
  els.btnNext.addEventListener('click', nextWord);
  els.wordSelect.addEventListener('change', (e) => {
    if (suppressWordSelectChange) return;
    showWord(parseInt(e.target.value, 10));
  });
  let settingsTopicId = getTopicId();
  let settingsQuizSize = getQuizSize();
  els.btnSettings.addEventListener('click', () => {
    settingsTopicId = getTopicId();
    settingsQuizSize = getQuizSize();
    els.settingsPanel.classList.remove('hidden');
    refreshSilenceHints();
    populateTtsVoiceSelect();
  });
  els.btnNewQuiz?.addEventListener('click', () => {
    startQuizSession({ newQuiz: true });
  });
  els.btnCloseSettings.addEventListener('click', async () => {
    const topicChanged = els.settingTopic?.value !== settingsTopicId;
    const sizeChanged = getQuizSize() !== settingsQuizSize;
    saveSettings();
    applyPracticeModeUI();
    micEngine?.setHangoverMs(getHangoverMsSetting());
    refreshSilenceHints();
    armIdleSampleTimer();
    els.settingsPanel.classList.add('hidden');
    checkBackend();
    if (topicChanged || sizeChanged) {
      await startQuizSession({ newQuiz: true });
    }
  });

  els.settingSilenceSec?.addEventListener('input', () => {
    micEngine?.setHangoverMs(getHangoverMsSetting());
    refreshSilenceHints();
  });

  els.settingIdleSampleSec?.addEventListener('input', () => {
    if (idleSampleArmed) armIdleSampleTimer();
  });

  els.settingAutoplay?.addEventListener('change', () => {
    if (shouldAutoplaySample()) armIdleSampleTimer();
    else disarmIdleSampleTimer();
  });

  window.addEventListener('beforeunload', () => stopLiveMode());
}

/** WAV 16kHz mono — đủ lớn cho upload evaluate (E2E) */
function createTestWavBlob(durationSec = 0.6, sampleRate = 16000, freq = 440) {
  const numSamples = Math.floor(durationSec * sampleRate);
  const dataSize = numSamples * 2;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  const writeStr = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, dataSize, true);
  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;
    const sample = Math.sin(2 * Math.PI * freq * t) * 0.25;
    const int16 = Math.max(-32768, Math.min(32767, Math.floor(sample * 32767)));
    view.setInt16(44 + i * 2, int16, true);
  }
  return new Blob([buffer], { type: 'audio/wav' });
}

/** Hooks cho E2E — mô phỏng thao tác người dùng trên browser */
window.__pronounceLabTest = {
  getInitCount: () => initRunCount,
  getCurrentIndex: () => currentIndex,
  getPracticeMode: () => practiceMode,
  getCurrentWord: () => {
    const w = words[currentIndex];
    return w
      ? { word: w.word, ipa: w.ipa, phonemes: [...(w.phonemes || [])] }
      : null;
  },
  getState: () => ({
    initCount: initRunCount,
    currentIndex,
    practiceMode,
    liveModeActive,
    word: words[currentIndex]?.word ?? null,
    quizSize: words.length,
  }),
  getPhonemeBoxCount: () => els.phonemeContainer?.querySelectorAll('.phoneme-box').length ?? 0,
  getPhonemeBoxNodes: () => [...(els.phonemeContainer?.querySelectorAll('.phoneme-box') || [])],
  getQuizRow: (index = currentIndex) => {
    const row = getQuizRowsForMode()[index];
    return row ? { ...row } : null;
  },
  getQuizSummaryTitle: () => els.quizSummaryTitle?.textContent ?? '',
  navigateToWord: (index, options = {}) => {
    showWord(index, { autoplay: false, ...options });
    return { index: currentIndex, word: words[currentIndex]?.word };
  },
  clickNext: (options = {}) => {
    const before = currentIndex;
    nextWord({ autoplay: false, ...options });
    return { before, after: currentIndex, word: words[currentIndex]?.word };
  },
  clickPrev: () => {
    const before = currentIndex;
    prevWord();
    return { before, after: currentIndex, word: words[currentIndex]?.word };
  },
  runMockEvaluate: async (overallScore = 55, passed = false) => {
    const w = words[currentIndex];
    if (!w) return null;
    const phonemes = (w.phonemes || ['ə']).map((ipa, i) => ({
      ipa,
      score: overallScore / 100,
      label: overallScore >= 80 ? 'ok' : 'mis',
      start: i * 0.1,
      end: (i + 1) * 0.1,
      suggestion: overallScore >= 80 ? '' : 'thử lại',
    }));
    renderEvaluation({
      word: w.word,
      ipa: w.ipa,
      overall_score: overallScore,
      passed,
      phonemes,
    }, { fromLive: liveModeActive, wordIndex: currentIndex });
    return { index: currentIndex, word: w.word };
  },
  flushPassAdvance: () => flushPassAdvance(),
  createTestWavBlob,
  /** Đọc xong (transcript) → gọi evaluateRecording + fetch API thật trong page */
  simulateScoreReadAndEvaluate: async () => {
    const w = words[currentIndex];
    if (!w || !isScoreMode()) return { error: 'not_score_mode' };
    if (!liveModeActive) return { error: 'mic_off' };

    micEngine?.pushTranscript(w.word, '');
    syncTranscriptFromEngine();
    noteUserInput();

    const before = {
      initCount: initRunCount,
      index: currentIndex,
      word: w.word,
      boxCount: els.phonemeContainer?.querySelectorAll('.phoneme-box').length ?? 0,
    };

    const blob = createTestWavBlob();
    await evaluateRecording(blob, { fromLive: true });

    return {
      before,
      after: {
        initCount: initRunCount,
        index: currentIndex,
        word: words[currentIndex]?.word ?? null,
        boxCount: els.phonemeContainer?.querySelectorAll('.phoneme-box').length ?? 0,
      },
    };
  },
  simulateTextPass: async () => {
    const w = words[currentIndex];
    if (!w || !isTextMode()) return null;
    const before = currentIndex;
    await processTextUtterance(w.word);
    return { before, after: currentIndex, word: words[currentIndex]?.word };
  },
  getIdleSampleState: () => ({
    armed: idleSampleArmed,
    hasTimer: Boolean(idleSampleTimer),
    isSamplePlaying,
    idleSec: getIdleSampleSec(),
    shouldAutoplay: shouldAutoplaySample(),
  }),
  getScoreSilenceState: () => ({
    hasTimer: Boolean(scoreMatchTimer),
    hangMs: getHangoverMsSetting(),
    spoken: getSpokenWord()?.trim() || '',
    scoreApiBusy,
  }),
  /** SR có transcript → lên lịch chấm sau hangover (E2E inject audio) */
  armScoreSilenceEvaluate: () => {
    const w = words[currentIndex];
    if (!w || !isScoreMode() || !liveModeActive) return { error: 'precondition' };
    e2eInjectScoreBlob = createTestWavBlob();
    micEngine?.pushTranscript(w.word, '');
    syncTranscriptFromEngine();
    tryScheduleScoreEvaluate();
    return {
      hasTimer: Boolean(scoreMatchTimer),
      hangMs: getHangoverMsSetting(),
      spoken: getSpokenWord()?.trim() || '',
    };
  },
  /** Chạy ngay callback timer im lặng (cùng logic sau hangover) */
  flushScoreSilenceTimer: async () => {
    if (!scoreMatchTimer) return { error: 'no_timer' };
    clearTimeout(scoreMatchTimer);
    scoreMatchTimer = null;
    if (!liveModeActive || !isScoreMode() || scoreApiBusy || isAdvancing || isListeningBlocked()) {
      return { error: 'blocked' };
    }
    if (!getSpokenWord()?.trim()) return { error: 'no_spoken' };
    const initBefore = initRunCount;
    await processScoreUtterance();
    return { initCount: initRunCount, unchanged: initRunCount === initBefore };
  },
};

init();
