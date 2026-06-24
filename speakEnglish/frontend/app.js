/**
 * PronounceLab Personal — frontend application
 */

import {
  PRACTICE_MODE,
  MIC_STATE,
  wordsMatch,
  getHangoverMs,
  computeRms,
  TEXT_MATCH_DELAY_MS,
  shouldAutoScoreOnUtteranceEnd,
  MIN_SPEECH_MS,
} from './js/core.js';
import { MicEngine, MIC_PHASE } from './js/mic-engine.js';

const STORAGE_KEY = 'pronouncelab_history';

/** @type {object} */
let config = {};
/** @type {Array} */
let words = [];
let currentIndex = 0;
let practiceMode = PRACTICE_MODE.TEXT;
let isAdvancing = false;
let micState = MIC_STATE.OFF;
let autoStartDone = false;
let mediaRecorder = null;
let audioChunks = [];
let userAudioBlob = null;
let userAudioUrl = null;
let serverAudioUrl = null;
let audioContext = null;
let isRecording = false;

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
let isEvaluating = false;
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
const EVAL_CACHE_KEY = 'pronouncelab_eval_cache';
/** @type {Record<string, object>} Kết quả chấm gần nhất theo từ */
const lastEvaluations = {};
/** Kết quả đang hiển thị cho từ hiện tại */
let currentWordEvaluation = null;
let passAdvanceTimer = null;
let suppressWordSelectChange = false;

const $ = (id) => document.getElementById(id);

const els = {
  wordSelect: $('word-select'),
  wordIndex: $('word-index'),
  historyBadge: $('history-badge'),
  currentWord: $('current-word'),
  currentIpa: $('current-ipa'),
  btnPlaySample: $('btn-play-sample'),
  btnRecord: $('btn-record'),
  btnStop: $('btn-stop'),
  btnReplayUser: $('btn-replay-user'),
  btnRetry: $('btn-retry'),
  btnPrev: $('btn-prev'),
  btnNext: $('btn-next'),
  btnSettings: $('btn-settings'),
  btnCloseSettings: $('btn-close-settings'),
  recordingIndicator: $('recording-indicator'),
  spinner: $('spinner'),
  scoreSection: $('score-section'),
  overallScore: $('overall-score'),
  passStatus: $('pass-status'),
  phonemeContainer: $('phoneme-container'),
  feedbackSection: $('feedback-section'),
  feedbackList: $('feedback-list'),
  settingsPanel: $('settings-panel'),
  settingAutoplay: $('setting-autoplay'),
  settingLiveAuto: $('setting-live-auto'),
  settingAutoEvaluate: $('setting-auto-evaluate'),
  settingApiUrl: $('setting-api-url'),
  settingPassScore: $('setting-pass-score'),
  serviceStatus: $('service-status'),
  btnLiveToggle: $('btn-live-toggle'),
  btnEvaluateNow: $('btn-evaluate-now'),
  micStatusLabel: $('mic-status-label'),
  vadLevel: $('vad-level'),
  liveTranscriptFinal: $('live-transcript-final'),
  liveTranscriptInterim: $('live-transcript-interim'),
  liveTranscriptPlaceholder: $('live-transcript-placeholder'),
  liveHint: $('live-hint'),
  settingSilenceSec: $('setting-silence-sec'),
  modeText: $('mode-text'),
  modeScore: $('mode-score'),
  appRoot: document.querySelector('.app'),
};

// ─── Init ───────────────────────────────────────────────────────────────────

async function init() {
  await loadConfig();
  await loadWords();
  loadEvalCache();
  loadSettings();
  applyPracticeModeUI();
  bindEvents();
  setupAutoStartMic();
  renderWordList();
  const savedIndex = parseInt(sessionStorage.getItem(WORD_INDEX_KEY) || '0', 10);
  showWord(Number.isFinite(savedIndex) ? savedIndex : 0);
  checkBackend();
  initLiveSpeech();
  setMicState(MIC_STATE.OFF, 'Micro tắt');

  if (els.settingLiveAuto?.checked) {
    showLiveHint('Chạm màn hình để bật micro tự động', 'warn');
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
  micState = state;
  if (els.btnLiveToggle) {
    els.btnLiveToggle.dataset.state = state;
    els.btnLiveToggle.setAttribute('aria-pressed', state !== MIC_STATE.OFF ? 'true' : 'false');
  }
  if (els.micStatusLabel && label) {
    els.micStatusLabel.textContent = label;
  }
}

async function loadConfig() {
  try {
    const res = await fetch('config.json');
    config = await res.json();
  } catch {
    config = { apiBaseUrl: 'http://127.0.0.1:8000', autoPlaySample: true };
  }
}

async function loadWords() {
  const res = await fetch('data/words.json');
  const data = await res.json();
  words = data.words || [];
}

function loadSettings() {
  const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
  els.settingAutoplay.checked = saved.autoPlaySample ?? config.autoPlaySample ?? true;
  els.settingLiveAuto.checked = saved.liveAutoStart ?? true;
  els.settingAutoEvaluate.checked = saved.autoEvaluate ?? true;
  els.settingSilenceSec.value = saved.silenceSec ?? config.silenceSec ?? 0.35;
  els.settingApiUrl.value = saved.apiBaseUrl ?? config.apiBaseUrl ?? 'http://127.0.0.1:8000';
  els.settingPassScore.value = saved.passScore ?? config.thresholds?.overallPass ?? 80;
  practiceMode = saved.practiceMode ?? config.practiceMode ?? PRACTICE_MODE.TEXT;
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify({
    autoPlaySample: els.settingAutoplay.checked,
    liveAutoStart: els.settingLiveAuto.checked,
    autoEvaluate: els.settingAutoEvaluate.checked,
    silenceSec: parseFloat(els.settingSilenceSec.value) || 0.35,
    apiBaseUrl: els.settingApiUrl.value,
    passScore: parseInt(els.settingPassScore.value, 10),
    practiceMode,
  }));
}

function isScoreMode() {
  return practiceMode === PRACTICE_MODE.SCORE;
}

function isTextMode() {
  return practiceMode === PRACTICE_MODE.TEXT;
}

function setPracticeMode(mode) {
  practiceMode = mode;
  saveSettings();
  applyPracticeModeUI();
  if (liveModeActive) {
    stopLiveMode();
    showLiveHint('Đã đổi chế độ — chạm để bật lại micro', 'warn');
    autoStartDone = false;
    setupAutoStartMic();
  }
}

function applyPracticeModeUI() {
  const textActive = isTextMode();
  els.modeText?.classList.toggle('active', textActive);
  els.modeScore?.classList.toggle('active', !textActive);
  els.appRoot?.classList.toggle('mode-text', textActive);
  els.appRoot?.classList.toggle('mode-score', !textActive);

  if (!textActive) {
    restoreWordScoreUI(words[currentIndex]);
  }

  if (els.liveTranscriptPlaceholder) {
    const sec = parseFloat(els.settingSilenceSec?.value) || 0.35;
    els.liveTranscriptPlaceholder.textContent = isTextMode()
      ? 'Đọc đúng từ → tự chuyển từ tiếp theo'
      : `Đọc từ → im lặng ~${sec}s → tự chấm → đạt thì chuyển từ`;
  }

  els.btnEvaluateNow?.classList.add('hidden');
  els.settingAutoEvaluate?.closest('.setting-row')?.classList.toggle('hidden', textActive);
  els.settingPassScore?.closest('.setting-row')?.classList.toggle('hidden', textActive);

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
    onSpeechStart: () => {
      if (isScoreMode()) {
        startPhraseRecording();
        startUtteranceCapture();
      }
    },
    onPhaseChange: (phase, label) => {
      if (phase !== MIC_PHASE.OFF) {
        setMicState(micPhaseToState(phase), label);
      }
    },
    onLevel: (_rms, pct) => {
      if (els.vadLevel) els.vadLevel.style.width = `${pct}%`;
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

// ─── Word navigation ────────────────────────────────────────────────────────

function renderWordList() {
  els.wordSelect.innerHTML = words
    .map((w, i) => `<option value="${i}">${w.word}</option>`)
    .join('');
}

function clearPassAdvanceTimer() {
  if (passAdvanceTimer) {
    clearTimeout(passAdvanceTimer);
    passAdvanceTimer = null;
  }
}

function showWord(index, options = {}) {
  const { autoplay = true } = options;
  const idx = Number(index);
  if (!Number.isFinite(idx)) return;

  clearPassAdvanceTimer();
  isAdvancing = false;

  currentIndex = Math.max(0, Math.min(idx, words.length - 1));
  sessionStorage.setItem(WORD_INDEX_KEY, String(currentIndex));
  const w = words[currentIndex];

  suppressWordSelectChange = true;
  els.wordSelect.value = String(currentIndex);
  suppressWordSelectChange = false;

  els.wordIndex.textContent = `${currentIndex + 1} / ${words.length}`;
  els.currentWord.textContent = w.word;
  els.currentIpa.textContent = w.ipa;
  updateHistoryBadge(w.word);

  resetEvaluationUI();
  restoreWordScoreUI(w);
  clearLiveTranscript();
  hideLiveHint();
  clearTextMatchTimer();
  clearScoreMatchTimer();
  micEngine?.resetSession();
  syncTranscriptFromEngine();

  if (autoplay && els.settingAutoplay.checked) {
    playSample();
  }
}

function resetEvaluationUI() {
  els.feedbackSection.classList.add('hidden');
  els.btnRetry.classList.add('hidden');
  if (!liveModeActive) {
    els.btnReplayUser.disabled = true;
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

function beginScoringOverlay() {
  if (!isScoreMode()) return;
  els.phonemeContainer?.classList.add('scoring');
  els.scoreSection?.classList.add('scoring');
}

function endScoringOverlay() {
  els.phonemeContainer?.classList.remove('scoring');
  els.scoreSection?.classList.remove('scoring');
}

function restoreWordScoreUI(word) {
  if (!isScoreMode() || !word) return;
  endScoringOverlay();

  const cached = getCachedEvaluation(word.word);
  if (cached) {
    renderEvaluationDisplay(cached, { showSuggestionsAlways: liveModeActive });
    return;
  }
  if (currentWordEvaluation && normalizeWordKey(currentWordEvaluation.word) === normalizeWordKey(word.word)) {
    renderEvaluationDisplay(currentWordEvaluation, { showSuggestionsAlways: liveModeActive });
    return;
  }

  els.scoreSection.classList.add('hidden');
  els.phonemeContainer?.classList.remove('has-results');
  renderPendingPhonemes(word.phonemes || []);
}

function renderPendingPhonemes(phonemes) {
  if (!isScoreMode()) return;
  if (hasEvaluationForWord(words[currentIndex])) return;

  endScoringOverlay();
  els.phonemeContainer.classList.remove('has-results');
  els.phonemeContainer.innerHTML = phonemes
    .map((p) => `
      <div class="phoneme-box" data-ipa="${p}">
        <div class="phoneme-char pending">${p}</div>
        <span class="phoneme-score">—</span>
      </div>
    `)
    .join('');
}

function renderEvaluationDisplay(data, options = {}) {
  const { showSuggestionsAlways = false } = options;
  if (!data?.phonemes?.length) return false;

  endScoringOverlay();
  currentWordEvaluation = data;

  const passScore = parseInt(els.settingPassScore.value, 10);
  const allOk = data.phonemes.every((p) => p.label === 'ok');
  const passed = data.passed ?? (allOk || data.overall_score >= passScore);

  els.scoreSection.classList.remove('hidden');
  els.overallScore.textContent = `${data.overall_score}%`;
  els.passStatus.textContent = passed ? '✓ Đạt' : '✗ Chưa đạt';
  els.passStatus.className = `pass-status ${passed ? 'passed' : 'failed'}`;

  serverAudioUrl = data.audio_url
    ? `${getApiBase()}${data.audio_url}`
    : null;

  els.phonemeContainer?.classList.add('has-results');
  renderPhonemeResults(data.phonemes, showSuggestionsAlways);
  renderFeedback(data.phonemes);
  return true;
}

function nextWord(options = {}) {
  if (currentIndex < words.length - 1) {
    showWord(currentIndex + 1, options);
  }
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
    syncTranscriptFromEngine();
    updateRealtimeHint();
    if (isScoreMode() && liveModeActive && (finalPart || interim)) {
      startUtteranceCapture();
      startPhraseRecording();
      setMicState(MIC_STATE.HEARING, 'Đang nghe bạn nói...');
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
  const finalText = micEngine.transcriptFinal.trim();
  const interimText = micEngine.transcriptInterim;
  els.liveTranscriptFinal.textContent = finalText;
  els.liveTranscriptInterim.textContent = interimText;
  const hasText = finalText || interimText;
  els.liveTranscriptPlaceholder.classList.toggle('hidden', !!hasText);

  const w = words[currentIndex];
  const lastWord = micEngine.getSpokenWord();
  const match = wordsMatch(lastWord, w?.word);
  els.liveTranscriptInterim.classList.toggle('match', match);
  els.liveTranscriptFinal.classList.toggle('match', match);
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
  if (!isScoreMode() || !liveModeActive || isListeningBlocked() || isAdvancing || isEvaluating) {
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
    if (!liveModeActive || !isScoreMode() || isEvaluating || isAdvancing || isListeningBlocked()) {
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
  if (!w || !spoken || !wordsMatch(spoken, w.word)) {
    clearTextMatchTimer();
    return;
  }

  if (textMatchTimer) return;

  showLiveHint(`✓ "${spoken}" khớp — chuyển từ...`, 'ok');
  textMatchTimer = setTimeout(async () => {
    textMatchTimer = null;
    if (!liveModeActive || isAdvancing || !isTextMode()) return;
    const latest = getSpokenWord();
    if (latest && wordsMatch(latest, w.word)) {
      await processTextUtterance(latest);
    }
  }, TEXT_MATCH_DELAY_MS);
}

function showLiveHint(message, type = 'warn') {
  if (!els.liveHint) return;
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

/** Ghi âm 1 câu — cùng cơ chế với nút Ghi âm 1 lần (webm/mp4 hợp lệ) */
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

/** Live score: ưu tiên webm từ phraseRecorder (giống Ghi âm 1 lần), PCM chỉ dự phòng */
async function getScoreAudioBlob() {
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
  if (!liveModeActive || isListeningBlocked() || isAdvancing || isEvaluating) return;

  if (isTextMode()) {
    await processTextUtterance(payload.spoken);
    return;
  }

  if (!shouldAutoScoreOnUtteranceEnd({
    practiceMode,
    autoEvaluate: els.settingAutoEvaluate?.checked,
  })) {
    return;
  }

  clearScoreMatchTimer();
  await processScoreUtterance();
}

/** Score mode: im lặng sau câu → tự gọi API chấm (cùng pipeline với Ghi âm 1 lần) */
async function processScoreUtterance() {
  if (isEvaluating) return;

  clearScoreMatchTimer();

  await new Promise((r) => setTimeout(r, 80));

  const blob = await getScoreAudioBlob();
  if (!blob || blob.size < MIN_BLOB_BYTES) {
    showLiveHint('Không đủ audio — nói rõ hơn (~0.5s)', 'warn');
    restoreWordScoreUI(words[currentIndex]);
    return;
  }

  userAudioBlob = blob;
  if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
  userAudioUrl = URL.createObjectURL(blob);
  els.btnReplayUser.disabled = false;

  showLiveHint('Đang chấm điểm...', 'warn');
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

  if (!wordsMatch(word, w.word)) {
    showLiveHint(`✗ Nghe "${word}" — cần "${w.word}" (${w.ipa})`, 'mis');
    return;
  }

  isAdvancing = true;
  showLiveHint(`✓ Đúng "${word}"!`, 'ok');
  recordAttempt(w.word, true, 100);
  await new Promise((r) => setTimeout(r, 100));
  hideLiveHint();
  micEngine?.clearTranscript();
  syncTranscriptFromEngine();
  nextWord();
  isAdvancing = false;
}

function updateRealtimeHint() {
  const w = words[currentIndex];
  if (!w || isEvaluating || isAdvancing) return;

  const spoken = getSpokenWord();
  if (!spoken) {
    if (!isTextMode()) hideLiveHint();
    return;
  }

  if (wordsMatch(spoken, w.word)) {
    const msg = isTextMode()
      ? `✓ Nghe "${spoken}" — khớp!`
      : `✓ Nghe "${spoken}" — im lặng ngắn để tự chấm`;
    showLiveHint(msg, 'ok');
  } else {
    showLiveHint(`✗ Nghe "${spoken}" — cần đọc "${w.word}" (${w.ipa})`, 'mis');
  }
}

function clearLiveTranscript() {
  micEngine?.clearTranscript();
  syncTranscriptFromEngine();
  hideLiveHint();
}

async function startLiveMode() {
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

    liveMimeType = pickRecorderMimeType();
    audioRingChunks = [];
    if (isScoreMode()) {
      ensurePcmCaptureGraph();
    } else {
      setupMediaRecorder();
    }

    micEngine = createMicEngine();
    micEngine.setHangoverMs(getHangoverMsSetting());
    startVadLoop();

    if (speechRecognition) {
      try { speechRecognition.start(); } catch (e) {
        console.warn('SpeechRecognition start:', e);
      }
    }

    liveModeActive = true;
    micEngine.start();
    const hangSec = (getHangoverMsSetting() / 1000).toFixed(1);
    els.recordingIndicator.innerHTML =
      `<span class="pulse"></span> Nói xong → im lặng ~${hangSec}s → phản hồi`;
    els.recordingIndicator.classList.remove('hidden');
    els.btnRecord.disabled = true;
    if (isScoreMode()) {
      els.phonemeContainer.classList.add('live-mode');
      restoreWordScoreUI(words[currentIndex]);
    }
    hideLiveHint();
  } catch (err) {
    alert('Không thể bật micro: ' + err.message);
  }
}

function stopLiveMode() {
  if (!liveModeActive) return;

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
  els.vadLevel.style.width = '0%';

  setMicState(MIC_STATE.OFF, 'Micro tắt');
  els.recordingIndicator.classList.add('hidden');
  els.btnRecord.disabled = false;
  els.phonemeContainer.classList.remove('live-mode');
  els.btnEvaluateNow?.classList.add('hidden');
}

function toggleLiveMode() {
  if (liveModeActive) stopLiveMode();
  else startLiveMode();
}

function startVadLoop() {
  if (!liveAnalyser || !micEngine) return;

  const buf = new Uint8Array(liveAnalyser.fftSize);

  const tick = () => {
    if (!liveModeActive || !liveAnalyser || !micEngine) return;

    if (isListeningBlocked()) {
      els.vadLevel.style.width = '0%';
      vadAnimationId = requestAnimationFrame(tick);
      return;
    }

    liveAnalyser.getByteTimeDomainData(buf);
    const rms = computeRms(buf);
    micEngine.tick(rms);
    vadAnimationId = requestAnimationFrame(tick);
  };
  tick();
}

function pauseListeningForSample() {
  if (sampleResumeTimer) {
    clearTimeout(sampleResumeTimer);
    sampleResumeTimer = null;
  }
  isSamplePlaying = true;
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

  if (speechRecognition && liveModeActive) {
    try { speechRecognition.stop(); } catch { /* ignore */ }
  }
  setMicState(MIC_STATE.SAMPLE, 'Đang phát mẫu...');
}

function resumeListeningAfterSample() {
  if (!isSamplePlaying) return;
  if (sampleResumeTimer) clearTimeout(sampleResumeTimer);

  sampleResumeTimer = setTimeout(() => {
    sampleResumeTimer = null;
    if (!isSamplePlaying) return;

    isSamplePlaying = false;
    speechRecognitionPaused = false;
    micEngine?.resume();
    resumeRingRecorder();

    if (liveModeActive && speechRecognition) {
      try { speechRecognition.start(); } catch { /* ignore */ }
      setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    }
  }, SAMPLE_TAIL_MS);
}

function isListeningBlocked() {
  return isSamplePlaying || speechRecognitionPaused;
}

// ─── Audio: TTS sample ──────────────────────────────────────────────────────

function playSample() {
  const w = words[currentIndex];
  const guardMic = liveModeActive;

  if (guardMic) pauseListeningForSample();

  const finishSample = () => {
    if (guardMic) resumeListeningAfterSample();
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
    utter.lang = 'en-US';
    utter.rate = 0.85;
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

    // Một số trình duyệt không gọi onend — dự phòng
    if (guardMic) {
      const maxMs = Math.max(2500, w.word.length * 180);
      setTimeout(() => {
        if (isSamplePlaying && !speechSynthesis.speaking) done();
      }, maxMs);
    }
    return;
  }

  finishSample();
}

// ─── Audio: Recording ───────────────────────────────────────────────────────

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';
    mediaRecorder = new MediaRecorder(stream, { mimeType });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      userAudioBlob = new Blob(audioChunks, { type: mimeType });
      userAudioUrl = URL.createObjectURL(userAudioBlob);
      els.btnReplayUser.disabled = false;
      if (isScoreMode()) {
        await evaluateRecording();
      } else {
        const spoken = getSpokenWord();
        const w = words[currentIndex];
        if (spoken && wordsMatch(spoken, w?.word)) {
          setMicState(MIC_STATE.PROCESSING, 'Đang xử lý...');
          await processTextUtterance(spoken);
          if (liveModeActive) setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
        } else {
          showLiveHint(`Bật micro live và đọc "${w?.word}" — hoặc chuyển sang chế độ Chấm điểm`, 'warn');
        }
      }
    };

    mediaRecorder.start();
    isRecording = true;
    els.btnRecord.classList.add('recording');
    els.btnRecord.disabled = true;
    els.btnStop.disabled = false;
    els.recordingIndicator.classList.remove('hidden');
  } catch (err) {
    alert('Không thể truy cập microphone: ' + err.message);
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    els.btnRecord.classList.remove('recording');
    els.btnRecord.disabled = false;
    els.btnStop.disabled = true;
    els.recordingIndicator.classList.add('hidden');
  }
}

function replayUserAudio() {
  if (userAudioUrl) {
    new Audio(userAudioUrl).play();
  }
}

// ─── Evaluation API ─────────────────────────────────────────────────────────

async function evaluateRecording(blob = null, options = {}) {
  const { fromLive = false } = options;
  const evalWordIndex = currentIndex;
  const w = words[evalWordIndex];
  const audioBlob = blob || userAudioBlob;
  if (!audioBlob || !w) return;

  clearPassAdvanceTimer();
  isAdvancing = false;

  isEvaluating = true;
  setMicState(MIC_STATE.PROCESSING, 'Đang chấm điểm...');
  els.spinner.classList.remove('hidden');
  beginScoringOverlay();
  els.phonemeContainer?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  let uploadBlob;
  let filename;
  try {
    ({ blob: uploadBlob, filename } = await prepareUploadBlob(audioBlob));
  } catch (prepErr) {
    els.spinner.classList.add('hidden');
    isEvaluating = false;
    let msg = prepErr.message || 'Không xử lý được audio';
    if (/decode|encoding|Unable to decode/i.test(msg)) {
      msg = 'Không đọc được audio — nói rõ hơn (~0.5s) rồi thử lại';
    }
    showLiveHint('Lỗi audio: ' + msg, 'mis');
    restoreWordScoreUI(words[currentIndex]);
    if (liveModeActive) setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    return;
  }

  const formData = new FormData();
  formData.append('file', uploadBlob, filename);
  formData.append('target_word', w.word);
  formData.append('target_ipa', w.ipa);
  formData.append('target_phonemes', JSON.stringify(w.phonemes || []));

  try {
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

    els.spinner.classList.add('hidden');
    isEvaluating = false;

    if (!res.ok) {
      let msg = typeof data.detail === 'object'
        ? (data.detail?.error || JSON.stringify(data.detail))
        : (data.detail || data.error || `HTTP ${res.status}`);
      if (/ffmpeg failed/i.test(msg)) {
        msg = 'File audio không hợp lệ — nói rõ hơn (~0.5s) rồi thử lại';
      }
      showLiveHint('Lỗi chấm điểm: ' + msg, 'mis');
      restoreWordScoreUI(words[currentIndex]);
      if (liveModeActive) setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
      return;
    }

    renderEvaluation(data, { fromLive });
  } catch (err) {
    els.spinner.classList.add('hidden');
    isEvaluating = false;
    const msg = `Không kết nối backend (${getApiBase()}). Chạy: ./run_backend.sh`;
    if (fromLive) {
      showLiveHint(msg, 'mis');
      restoreWordScoreUI(words[currentIndex]);
      if (liveModeActive) setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    } else if (!blob) {
      alert(msg + '\n\n' + err.message);
    }
  }
}

function renderEvaluation(data, options = {}) {
  const { fromLive = false } = options;

  cacheEvaluation(data);
  if (!renderEvaluationDisplay(data, { showSuggestionsAlways: fromLive || liveModeActive })) {
    showLiveHint('Phản hồi thiếu dữ liệu phoneme', 'mis');
    restoreWordScoreUI(words[currentIndex]);
    if (liveModeActive) setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    return;
  }

  els.phonemeContainer?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  const passScore = parseInt(els.settingPassScore.value, 10);
  const allOk = data.phonemes.every((p) => p.label === 'ok');
  const passed = data.passed ?? (allOk || data.overall_score >= passScore);

  recordAttempt(data.word, passed, data.overall_score);

  if (passed) {
    els.btnRetry.classList.add('hidden');
    showLiveHint(
      `✓ Đạt ${data.overall_score}% — kết quả giữ tới lần chấm sau (bấm → để sang từ tiếp)`,
      'ok',
    );
    if (fromLive && liveModeActive) {
      setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    }
  } else {
    els.btnRetry.classList.remove('hidden');
    const issues = data.phonemes.filter((p) => p.label !== 'ok' && p.suggestion);
    const hintText = issues.length
      ? issues.map((p) => `${p.ipa}: ${p.suggestion}`).join(' · ')
      : `Chưa đạt (${data.overall_score}%) — thử đọc lại "${data.word}"`;
    showLiveHint(hintText, 'mis');
    if (fromLive && liveModeActive) {
      setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    }
  }
}

function renderPhonemeResults(phonemes, showSuggestionsAlways = false) {
  endScoringOverlay();
  els.phonemeContainer.classList.add('has-results');
  els.phonemeContainer.innerHTML = phonemes
    .map((p, i) => `
      <div class="phoneme-box${showSuggestionsAlways && p.suggestion ? ' show-suggestion' : ''}" data-index="${i}" data-start="${p.start}" data-end="${p.end}">
        <div class="phoneme-char ${p.label}">${p.ipa}</div>
        <span class="phoneme-score">${Math.round(p.score * 100)}%</span>
        ${p.suggestion ? `<span class="phoneme-suggestion">${p.suggestion}</span>` : ''}
      </div>
    `)
    .join('');

  els.phonemeContainer.querySelectorAll('.phoneme-box').forEach((box) => {
    box.addEventListener('click', () => replaySegment(box));
    box.addEventListener('touchstart', (e) => {
      e.preventDefault();
      box.classList.toggle('show-suggestion');
    });
  });
}

function renderFeedback(phonemes) {
  const issues = phonemes.filter((p) => p.label !== 'ok' && p.suggestion);
  if (issues.length === 0) {
    els.feedbackSection.classList.add('hidden');
    return;
  }
  els.feedbackSection.classList.remove('hidden');
  els.feedbackList.innerHTML = issues
    .map((p) => `<li><strong>${p.ipa}</strong>: ${p.suggestion} (${Math.round(p.score * 100)}%)</li>`)
    .join('');
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
  els.btnRecord.addEventListener('click', startRecording);
  els.btnStop.addEventListener('click', stopRecording);
  els.btnReplayUser.addEventListener('click', replayUserAudio);
  els.btnRetry.addEventListener('click', () => {
    els.btnRetry.classList.add('hidden');
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
  els.btnSettings.addEventListener('click', () => els.settingsPanel.classList.remove('hidden'));
  els.btnCloseSettings.addEventListener('click', () => {
    saveSettings();
    applyPracticeModeUI();
    micEngine?.setHangoverMs(getHangoverMsSetting());
    els.settingsPanel.classList.add('hidden');
    checkBackend();
  });

  window.addEventListener('beforeunload', () => stopLiveMode());
}

init();
