/**
 * PronounceLab Personal — frontend application
 */

import {
  PRACTICE_MODE,
  MIC_STATE,
  wordsMatch,
  getHangoverMs,
  computeRms,
  buildUtteranceBlob,
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
let liveMediaRecorder = null;
let audioRingChunks = [];
let liveAnalyser = null;
let vadAnimationId = null;
let isEvaluating = false;
let liveMimeType = 'audio/webm';

let isSamplePlaying = false;
let speechRecognitionPaused = false;
let sampleResumeTimer = null;
const RING_CHUNK_MS = 100;
const MAX_RING_CHUNKS = 30;
const SAMPLE_TAIL_MS = 500;
const MAX_SCORE_AUDIO_SEC = 3;
const MIN_BLOB_BYTES = 100;
const SETTINGS_KEY = 'pronouncelab_settings';

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
  liveToggleLabel: $('live-toggle-label'),
  micIndicator: $('mic-indicator'),
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
  loadSettings();
  applyPracticeModeUI();
  bindEvents();
  setupAutoStartMic();
  renderWordList();
  showWord(0);
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
  if (els.micIndicator) {
    els.micIndicator.dataset.state = state;
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

  if (els.liveTranscriptPlaceholder) {
    const sec = parseFloat(els.settingSilenceSec?.value) || 0.35;
    els.liveTranscriptPlaceholder.textContent =
      `Nói từ — im lặng ~${sec}s → phản hồi ngay`;
  }

  els.btnEvaluateNow?.classList.toggle('hidden', textActive || !liveModeActive);
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
    onSpeechStart: () => {
      micEngine?.beginCapture(audioRingChunks.slice(-4));
      if (liveMediaRecorder?.state === 'recording') {
        try { liveMediaRecorder.requestData(); } catch { /* ignore */ }
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

function showWord(index) {
  currentIndex = Math.max(0, Math.min(index, words.length - 1));
  const w = words[currentIndex];

  els.wordSelect.value = currentIndex;
  els.wordIndex.textContent = `${currentIndex + 1} / ${words.length}`;
  els.currentWord.textContent = w.word;
  els.currentIpa.textContent = w.ipa;
  updateHistoryBadge(w.word);

  resetEvaluationUI();
  renderPendingPhonemes(w.phonemes || []);
  clearLiveTranscript();
  hideLiveHint();
  micEngine?.resetSession();
  syncTranscriptFromEngine();

  if (els.settingAutoplay.checked) {
    playSample();
  }
}

function resetEvaluationUI() {
  els.scoreSection.classList.add('hidden');
  els.feedbackSection.classList.add('hidden');
  els.btnRetry.classList.add('hidden');
  els.btnReplayUser.disabled = true;
  userAudioBlob = null;
  serverAudioUrl = null;
  if (userAudioUrl) {
    URL.revokeObjectURL(userAudioUrl);
    userAudioUrl = null;
  }
}

function renderPendingPhonemes(phonemes) {
  els.phonemeContainer.innerHTML = phonemes
    .map((p) => `
      <div class="phoneme-box" data-ipa="${p}">
        <div class="phoneme-char pending">${p}</div>
        <span class="phoneme-score">—</span>
      </div>
    `)
    .join('');
}

function nextWord() {
  if (currentIndex < words.length - 1) {
    showWord(currentIndex + 1);
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

function setupMediaRecorder() {
  if (!micStream) return;
  if (liveMediaRecorder?.state === 'recording') {
    try { liveMediaRecorder.stop(); } catch { /* ignore */ }
  }

  liveMimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : 'audio/mp4';

  liveMediaRecorder = new MediaRecorder(micStream, { mimeType: liveMimeType });
  liveMediaRecorder.ondataavailable = (e) => {
    if (e.data.size <= 0) return;
    audioRingChunks.push(e.data);
    if (audioRingChunks.length > MAX_RING_CHUNKS) audioRingChunks.shift();
    micEngine?.pushAudioChunk(e.data);
  };
  liveMediaRecorder.start(RING_CHUNK_MS);
}

async function flushRecorderData() {
  if (!liveMediaRecorder || liveMediaRecorder.state !== 'recording') return;
  return new Promise((resolve) => {
    const handler = (e) => {
      if (e.data.size > 0) {
        audioRingChunks.push(e.data);
        micEngine?.pushAudioChunk(e.data);
      }
      liveMediaRecorder.removeEventListener('dataavailable', handler);
      resolve();
    };
    liveMediaRecorder.addEventListener('dataavailable', handler);
    try { liveMediaRecorder.requestData(); } catch { resolve(); }
    setTimeout(resolve, 80);
  });
}

/** Chuyển blob audio → WAV 16kHz mono */
async function convertBlobToWav(blob) {
  if (!audioContext) audioContext = new AudioContext();
  if (audioContext.state === 'suspended') await audioContext.resume();

  const arrayBuffer = await blob.arrayBuffer();
  const decoded = await audioContext.decodeAudioData(arrayBuffer.slice(0));

  const sr = decoded.sampleRate;
  const ch = decoded.numberOfChannels;
  const fullLen = decoded.length;
  const maxSamples = Math.floor(sr * MAX_SCORE_AUDIO_SEC);
  const startSample = Math.max(0, fullLen - maxSamples);
  const len = fullLen - startSample;
  const pcm = new Int16Array(len);

  for (let i = 0; i < len; i++) {
    const idx = startSample + i;
    let sample = decoded.getChannelData(0)[idx];
    if (ch > 1) {
      let mix = sample;
      for (let c = 1; c < ch; c++) mix += decoded.getChannelData(c)[idx];
      sample = mix / ch;
    }
    sample = Math.max(-1, Math.min(1, sample));
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
  view.setUint32(24, sr, true);
  view.setUint32(28, sr * 2, true);
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

async function prepareUploadBlob(blob) {
  try {
    const wav = await convertBlobToWav(blob);
    return { blob: wav, filename: 'recording.wav' };
  } catch (e) {
    console.warn('WAV convert failed, send webm:', e);
    return { blob, filename: 'recording.webm' };
  }
}

async function handleUtteranceComplete(payload) {
  if (!liveModeActive || isListeningBlocked() || isAdvancing) return;

  await flushRecorderData();

  if (isTextMode()) {
    await processTextUtterance(payload.spoken);
    return;
  }

  if (!els.settingAutoEvaluate?.checked) return;

  const blob = payload.getBlob(liveMimeType);
  if (!blob || blob.size < MIN_BLOB_BYTES) {
    showLiveHint('Không đủ audio — nói rõ hơn', 'warn');
    return;
  }

  userAudioBlob = blob;
  if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
  userAudioUrl = URL.createObjectURL(blob);
  els.btnReplayUser.disabled = false;

  showLiveHint('Đang phân tích phát âm...', 'warn');
  await evaluateRecording(blob, { fromLive: true });
}

/** Text mode: so khớp ngay khi kết thúc câu */
async function processTextUtterance(spoken) {
  const w = words[currentIndex];
  const word = spoken || getSpokenWord();

  if (!word) {
    showLiveHint('Không nghe rõ — thử đọc lại', 'warn');
    return;
  }

  if (wordsMatch(word, w.word)) {
    isAdvancing = true;
    showLiveHint(`✓ Đúng "${word}"! Chuyển từ...`, 'ok');
    recordAttempt(w.word, true, 100);
    await new Promise((r) => setTimeout(r, 120));
    hideLiveHint();
    micEngine?.clearTranscript();
    syncTranscriptFromEngine();
    nextWord();
    isAdvancing = false;
  } else {
    showLiveHint(`✗ Nghe "${word}" — cần "${w.word}" (${w.ipa})`, 'mis');
  }
}

async function triggerEvaluate(source = 'manual') {
  if (!isScoreMode() || isListeningBlocked() || isEvaluating) return false;

  await flushRecorderData();
  const blob = micEngine?.getBlob(liveMimeType)
    || buildUtteranceBlob(audioRingChunks.slice(-8), liveMimeType);

  if (!blob || blob.size < MIN_BLOB_BYTES) {
    if (source === 'manual') showLiveHint('Chưa có audio — nói trước rồi bấm Chấm điểm', 'warn');
    return false;
  }

  userAudioBlob = blob;
  if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
  userAudioUrl = URL.createObjectURL(blob);
  els.btnReplayUser.disabled = false;

  await evaluateRecording(blob, { fromLive: true });
  return true;
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
      : `✓ Nghe "${spoken}" — im lặng ngắn để chấm`;
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

    const source = audioContext.createMediaStreamSource(micStream);
    liveAnalyser = audioContext.createAnalyser();
    liveAnalyser.fftSize = 1024;
    liveAnalyser.smoothingTimeConstant = 0.3;
    source.connect(liveAnalyser);

    micEngine = createMicEngine();
    micEngine.setHangoverMs(getHangoverMsSetting());
    audioRingChunks = [];
    setupMediaRecorder();
    startVadLoop();

    if (speechRecognition) {
      try { speechRecognition.start(); } catch (e) {
        console.warn('SpeechRecognition start:', e);
      }
    }

    liveModeActive = true;
    micEngine.start();
    els.btnLiveToggle.classList.add('active');
    els.liveToggleLabel.textContent = 'Tắt micro';
    const hangSec = (getHangoverMsSetting() / 1000).toFixed(1);
    els.recordingIndicator.innerHTML =
      `<span class="pulse"></span> Nói xong → im lặng ~${hangSec}s → phản hồi`;
    els.recordingIndicator.classList.remove('hidden');
    els.btnRecord.disabled = true;
    if (isScoreMode()) {
      els.phonemeContainer.classList.add('live-mode');
      els.btnEvaluateNow?.classList.remove('hidden');
    }
    hideLiveHint();
  } catch (err) {
    alert('Không thể bật micro: ' + err.message);
  }
}

function stopLiveMode() {
  if (!liveModeActive) return;

  liveModeActive = false;
  micEngine?.stop();
  micEngine = null;

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
    liveMediaRecorder.stop();
  }
  liveMediaRecorder = null;

  if (micStream) {
    micStream.getTracks().forEach((t) => t.stop());
    micStream = null;
  }

  if (vadAnimationId) {
    cancelAnimationFrame(vadAnimationId);
    vadAnimationId = null;
  }
  els.vadLevel.style.width = '0%';

  els.btnLiveToggle.classList.remove('active');
  els.liveToggleLabel.textContent = 'Bật micro live';
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
  const w = words[currentIndex];
  const audioBlob = blob || userAudioBlob;
  if (!audioBlob) return;

  isEvaluating = true;
  setMicState(MIC_STATE.PROCESSING, 'Đang chấm điểm...');
  els.spinner.classList.remove('hidden');

  const { blob: uploadBlob, filename } = await prepareUploadBlob(audioBlob);

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
      const msg = typeof data.detail === 'object'
        ? (data.detail?.error || JSON.stringify(data.detail))
        : (data.detail || data.error || `HTTP ${res.status}`);
      showLiveHint('Lỗi chấm điểm: ' + msg, 'mis');
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
      if (liveModeActive) setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    } else if (!blob) {
      alert(msg + '\n\n' + err.message);
    }
  }
}

function renderEvaluation(data, options = {}) {
  const { fromLive = false } = options;
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

  renderPhonemeResults(data.phonemes, fromLive);
  renderFeedback(data.phonemes);
  recordAttempt(data.word, passed, data.overall_score);

  if (passed) {
    els.btnRetry.classList.add('hidden');
    showLiveHint(`✓ Đúng rồi! (${data.overall_score}%) — chuyển từ...`, 'ok');
    const delay = fromLive ? 350 : 1200;
    setTimeout(() => {
      hideLiveHint();
      nextWord();
      if (liveModeActive) setMicState(MIC_STATE.READY, 'Sẵn sàng thu âm');
    }, delay);
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
  els.btnEvaluateNow?.addEventListener('click', () => triggerEvaluate('manual'));
  els.btnRecord.addEventListener('click', startRecording);
  els.btnStop.addEventListener('click', stopRecording);
  els.btnReplayUser.addEventListener('click', replayUserAudio);
  els.btnRetry.addEventListener('click', () => {
    resetEvaluationUI();
    const w = words[currentIndex];
    renderPendingPhonemes(w.phonemes || []);
    clearLiveTranscript();
    hideLiveHint();
  });
  els.btnPrev.addEventListener('click', prevWord);
  els.btnNext.addEventListener('click', nextWord);
  els.wordSelect.addEventListener('change', (e) => showWord(parseInt(e.target.value, 10)));
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
