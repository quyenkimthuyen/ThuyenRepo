/**
 * PronounceLab Personal — frontend application
 */

const STORAGE_KEY = 'pronouncelab_history';
const SETTINGS_KEY = 'pronouncelab_settings';
const PRACTICE_MODE = { TEXT: 'text', SCORE: 'score' };

/** @type {object} */
let config = {};
/** @type {Array} */
let words = [];
let currentIndex = 0;
let practiceMode = PRACTICE_MODE.TEXT;
let isAdvancing = false;
let mediaRecorder = null;
let audioChunks = [];
let userAudioBlob = null;
let userAudioUrl = null;
let serverAudioUrl = null;
let audioContext = null;
let isRecording = false;

// Live mode state
let liveModeActive = false;
let speechRecognition = null;
let micStream = null;
let liveMediaRecorder = null;
let audioRingChunks = [];
let liveAnalyser = null;
let vadAnimationId = null;
let liveTranscriptFinal = '';
let liveTranscriptInterim = '';
let isEvaluating = false;
let lastEvaluateTime = 0;
const RING_CHUNK_MS = 500;
const MAX_RING_CHUNKS = 24;
const EVALUATE_COOLDOWN_MS = 1500;
const SPEECH_RMS_THRESHOLD = 0.012;
const MIN_SPEECH_MS = 300;
const MIN_BLOB_BYTES = 200;

// Utterance session (nói → im lặng 2s → đánh giá)
let utteranceActive = false;
let utteranceChunks = [];
let firstSoundAt = 0;
let lastSoundAt = 0;
let utteranceEnding = false;
let speechSilenceTimer = null;
let liveMimeType = 'audio/webm';

// DOM refs
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
  liveStatus: $('live-status'),
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
  renderWordList();
  showWord(0);
  checkBackend();
  initLiveSpeech();

  if (els.settingLiveAuto?.checked) {
    showLiveHint('Nhấn "Bật micro live" để bắt đầu (trình duyệt cần thao tác của bạn)', 'warn');
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
  els.settingSilenceSec.value = saved.silenceSec ?? 2;
  els.settingApiUrl.value = saved.apiBaseUrl ?? config.apiBaseUrl ?? 'http://127.0.0.1:8000';
  els.settingPassScore.value = saved.passScore ?? config.thresholds?.overallPass ?? 80;
  practiceMode = saved.practiceMode ?? config.practiceMode ?? PRACTICE_MODE.TEXT;
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify({
    autoPlaySample: els.settingAutoplay.checked,
    liveAutoStart: els.settingLiveAuto.checked,
    autoEvaluate: els.settingAutoEvaluate.checked,
    silenceSec: parseFloat(els.settingSilenceSec.value) || 2,
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
    showLiveHint('Đã đổi chế độ — bật lại micro live', 'warn');
  }
}

function applyPracticeModeUI() {
  const textActive = isTextMode();
  els.modeText?.classList.toggle('active', textActive);
  els.modeScore?.classList.toggle('active', !textActive);
  els.appRoot?.classList.toggle('mode-text', textActive);
  els.appRoot?.classList.toggle('mode-score', !textActive);

  if (els.liveTranscriptPlaceholder) {
    els.liveTranscriptPlaceholder.textContent = textActive
      ? 'Bật micro live — đọc đúng từ hiển thị để qua từ tiếp theo'
      : 'Bật micro live — nói từ rồi dừng ~2 giây để chấm điểm phoneme';
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

function getSilenceMs() {
  const sec = parseFloat(els.settingSilenceSec?.value) || 2;
  return Math.round(sec * 1000);
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
  resetUtteranceSession();

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

// ─── Live mode: micro liên tục + nhận dạng real-time ─────────────────────

function initLiveSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    els.liveStatus.textContent = 'Trình duyệt không hỗ trợ nhận dạng giọng nói (dùng Chrome/Edge)';
    els.btnLiveToggle.disabled = true;
    return;
  }

  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = true;
  speechRecognition.interimResults = true;
  speechRecognition.lang = 'en-US';
  speechRecognition.maxAlternatives = 1;

  speechRecognition.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const text = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        liveTranscriptFinal += text + ' ';
      } else {
        interim += text;
      }
    }
    liveTranscriptInterim = interim;
    updateLiveTranscriptUI();
    onSpeechActivity();
  };

  speechRecognition.onerror = (event) => {
    if (event.error === 'no-speech' || event.error === 'aborted') return;
    console.warn('SpeechRecognition error:', event.error);
    if (event.error === 'not-allowed') {
      els.liveStatus.textContent = 'Bị chặn quyền micro';
      stopLiveMode();
    }
  };

  speechRecognition.onend = () => {
    if (liveModeActive) {
      try {
        speechRecognition.start();
      } catch {
        // restart sau khi user gesture
      }
    }
  };
}

function normalizeWord(s) {
  return s.toLowerCase().replace(/[^a-z']/g, '').trim();
}

function wordsMatch(spoken, target) {
  const s = normalizeWord(spoken);
  const t = normalizeWord(target);
  if (!s || !t) return false;
  if (s === t || s.includes(t) || t.includes(s)) return true;
  // Cho phép sai lệch nhỏ (ví dụ "helou" ~ "hello")
  if (Math.abs(s.length - t.length) <= 2) {
    let diff = 0;
    const maxLen = Math.max(s.length, t.length);
    for (let i = 0; i < maxLen; i++) {
      if (s[i] !== t[i]) diff++;
    }
    return diff <= 2;
  }
  return false;
}

function getSpokenWord() {
  const combined = (liveTranscriptFinal + ' ' + liveTranscriptInterim).trim();
  if (!combined) return '';
  return combined.split(/\s+/).pop() || combined;
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

function resetUtteranceSession() {
  utteranceActive = false;
  utteranceChunks = [];
  firstSoundAt = 0;
  lastSoundAt = 0;
  utteranceEnding = false;
  clearSpeechSilenceTimer();
}

function clearSpeechSilenceTimer() {
  if (speechSilenceTimer) {
    clearTimeout(speechSilenceTimer);
    speechSilenceTimer = null;
  }
}

/** Text mode: khớp từ → qua từ tiếp theo */
function checkTextModePass() {
  if (!isTextMode() || !liveModeActive || isAdvancing || isEvaluating) return;

  const w = words[currentIndex];
  const spoken = getSpokenWord();
  if (!spoken || !wordsMatch(spoken, w?.word)) return;

  isAdvancing = true;
  clearSpeechSilenceTimer();
  showLiveHint(`✓ Đúng "${spoken}"! Chuyển từ tiếp theo...`, 'ok');
  recordAttempt(w.word, true, 100);

  setTimeout(() => {
    hideLiveHint();
    nextWord();
    isAdvancing = false;
  }, 700);
}

/** Backup: sau khi SpeechRecognition có text */
function onSpeechActivity() {
  if (!liveModeActive) return;

  if (isTextMode()) {
    checkTextModePass();
    clearSpeechSilenceTimer();
    speechSilenceTimer = setTimeout(() => {
      if (!liveModeActive || isAdvancing) return;
      const spoken = getSpokenWord();
      const w = words[currentIndex];
      if (spoken && w && !wordsMatch(spoken, w.word)) {
        showLiveHint(`✗ Nghe "${spoken}" — cần đọc "${w.word}" (${w.ipa})`, 'mis');
      }
    }, getSilenceMs());
    return;
  }

  if (!els.settingAutoEvaluate?.checked) return;
  clearSpeechSilenceTimer();
  speechSilenceTimer = setTimeout(() => {
    if (liveModeActive && !isEvaluating && !utteranceEnding) {
      triggerEvaluate('speech');
    }
  }, getSilenceMs());
}

function getAudioLevel() {
  if (!liveAnalyser) return { rms: 0, pct: 0 };
  const buf = new Uint8Array(liveAnalyser.fftSize);
  liveAnalyser.getByteTimeDomainData(buf);
  let sum = 0;
  for (let i = 0; i < buf.length; i++) {
    const v = (buf[i] - 128) / 128;
    sum += v * v;
  }
  const rms = Math.sqrt(sum / buf.length);
  const pct = Math.min(100, rms * 400);
  return { rms, pct };
}

function buildUtteranceBlob() {
  const chunks = utteranceChunks.length >= 2
    ? utteranceChunks
    : audioRingChunks.slice(-6);
  if (!chunks.length) return null;
  return new Blob(chunks, { type: liveMimeType });
}

async function flushRecorderData() {
  if (!liveMediaRecorder || liveMediaRecorder.state !== 'recording') return;
  return new Promise((resolve) => {
    const handler = (e) => {
      if (e.data.size > 0 && utteranceActive) {
        utteranceChunks.push(e.data);
      }
      liveMediaRecorder.removeEventListener('dataavailable', handler);
      resolve();
    };
    liveMediaRecorder.addEventListener('dataavailable', handler);
    try {
      liveMediaRecorder.requestData();
    } catch {
      resolve();
    }
    setTimeout(resolve, 300);
  });
}

async function triggerEvaluate(source = 'vad') {
  if (!isScoreMode()) return;
  if (!els.settingAutoEvaluate?.checked && source !== 'manual') return;
  if (utteranceEnding || isEvaluating) return;

  const now = Date.now();
  if (now - lastEvaluateTime < EVALUATE_COOLDOWN_MS) return;

  utteranceEnding = true;
  clearSpeechSilenceTimer();

  await flushRecorderData();

  const blob = buildUtteranceBlob();
  if (!blob || blob.size < MIN_BLOB_BYTES) {
    utteranceEnding = false;
    if (source === 'speech' && getSpokenWord()) {
      showLiveHint('Không đủ audio — nói to hơn hoặc gần micro hơn', 'warn');
    }
    return;
  }

  const speechDuration = lastSoundAt > firstSoundAt
    ? lastSoundAt - firstSoundAt
    : getSilenceMs();
  if (utteranceActive && speechDuration < MIN_SPEECH_MS && source === 'vad') {
    utteranceEnding = false;
    return;
  }

  lastEvaluateTime = now;
  els.liveStatus.textContent = 'Đang gọi API chấm điểm...';
  els.liveStatus.className = 'live-status speaking';
  showLiveHint('Đang phân tích phát âm...', 'warn');

  userAudioBlob = blob;
  if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
  userAudioUrl = URL.createObjectURL(blob);
  els.btnReplayUser.disabled = false;

  try {
    await evaluateRecording(blob, { fromLive: true });
  } finally {
    resetUtteranceSession();
  }
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
      : `✓ Nghe "${spoken}" — khớp, chờ im lặng để chấm điểm...`;
    showLiveHint(msg, 'ok');
  } else {
    showLiveHint(`✗ Nghe "${spoken}" — cần đọc "${w.word}" (${w.ipa})`, 'mis');
  }
}

function updateLiveTranscriptUI() {
  const w = words[currentIndex];
  const finalText = liveTranscriptFinal.trim();
  const interimText = liveTranscriptInterim;

  els.liveTranscriptFinal.textContent = finalText;
  els.liveTranscriptInterim.textContent = interimText;

  const hasText = finalText || interimText;
  els.liveTranscriptPlaceholder.classList.toggle('hidden', !!hasText || utteranceActive);

  const lastWord = getSpokenWord();
  if (wordsMatch(lastWord, w?.word)) {
    els.liveTranscriptInterim.classList.add('match');
    els.liveTranscriptFinal.classList.add('match');
  } else {
    els.liveTranscriptInterim.classList.remove('match');
    els.liveTranscriptFinal.classList.remove('match');
  }

  updateRealtimeHint();
  if (isTextMode()) checkTextModePass();
}

function clearLiveTranscript() {
  liveTranscriptFinal = '';
  liveTranscriptInterim = '';
  els.liveTranscriptFinal.textContent = '';
  els.liveTranscriptInterim.textContent = '';
  els.liveTranscriptFinal.classList.remove('match');
  els.liveTranscriptInterim.classList.remove('match');
  els.liveTranscriptPlaceholder.classList.remove('hidden');
  hideLiveHint();
}

async function onUtteranceEnd() {
  await triggerEvaluate('vad');
}

async function startLiveMode() {
  if (liveModeActive) return;

  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    });

    if (!audioContext) audioContext = new AudioContext();
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }

    const source = audioContext.createMediaStreamSource(micStream);
    liveAnalyser = audioContext.createAnalyser();
    liveAnalyser.fftSize = 2048;
    liveAnalyser.smoothingTimeConstant = 0.4;
    source.connect(liveAnalyser);
    startVadLoop();

    audioRingChunks = [];
    utteranceChunks = [];
    liveMimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';

    if (isScoreMode()) {
      liveMediaRecorder = new MediaRecorder(micStream, { mimeType: liveMimeType });
      liveMediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioRingChunks.push(e.data);
          if (audioRingChunks.length > MAX_RING_CHUNKS) {
            audioRingChunks.shift();
          }
          if (utteranceActive) {
            utteranceChunks.push(e.data);
          }
        }
      };
      liveMediaRecorder.start(RING_CHUNK_MS);
    }

    if (speechRecognition) {
      try {
        speechRecognition.start();
      } catch (e) {
        console.warn('SpeechRecognition start:', e);
      }
    }

    liveModeActive = true;
    utteranceEnding = false;
    els.btnLiveToggle.classList.add('active');
    els.liveToggleLabel.textContent = 'Tắt micro live';
    els.liveStatus.textContent = isTextMode()
      ? 'Đang nghe... (đọc đúng từ để qua)'
      : 'Đang nghe... (nói rồi im lặng ~2s)';
    els.liveStatus.className = 'live-status listening';
    els.recordingIndicator.classList.remove('hidden');
    els.recordingIndicator.innerHTML = isTextMode()
      ? '<span class="pulse"></span> Micro live — đọc đúng từ để qua'
      : '<span class="pulse"></span> Nói từ → im lặng ~2s để chấm điểm';
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
  clearSpeechSilenceTimer();

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
  els.liveStatus.textContent = 'Micro tắt';
  els.liveStatus.className = 'live-status';
  els.recordingIndicator.classList.add('hidden');
  els.btnRecord.disabled = false;
  els.phonemeContainer.classList.remove('live-mode');
  els.btnEvaluateNow?.classList.add('hidden');
  resetUtteranceSession();
}

function toggleLiveMode() {
  if (liveModeActive) {
    stopLiveMode();
  } else {
    startLiveMode();
  }
}

function startVadLoop() {
  if (!liveAnalyser) return;
  let vadEndPending = false;

  const tick = () => {
    if (!liveModeActive || !liveAnalyser) return;

    const { rms, pct } = getAudioLevel();
    els.vadLevel.style.width = `${pct}%`;

    const now = Date.now();
    const isSpeaking = rms > SPEECH_RMS_THRESHOLD;
    const silenceMs = getSilenceMs();

    if (isSpeaking) {
      vadEndPending = false;
      if (!utteranceActive && !isEvaluating && !utteranceEnding) {
        utteranceActive = true;
        utteranceChunks = [...audioRingChunks.slice(-3)];
        firstSoundAt = now;
        lastSoundAt = now;
        if (liveMediaRecorder?.state === 'recording') {
          try { liveMediaRecorder.requestData(); } catch { /* ignore */ }
        }
        clearLiveTranscript();
        hideLiveHint();
        els.liveTranscriptPlaceholder.classList.add('hidden');
      }
      lastSoundAt = now;
      els.liveStatus.textContent = 'Đang nghe bạn nói...';
      els.liveStatus.className = 'live-status speaking';
    } else if (utteranceActive && !isEvaluating && !utteranceEnding) {
      const silentFor = now - lastSoundAt;
      const remaining = Math.max(0, silenceMs - silentFor);
      if (silentFor >= silenceMs && isScoreMode()) {
        if (!vadEndPending) {
          vadEndPending = true;
          onUtteranceEnd();
        }
      } else if (remaining <= 1000 && isScoreMode()) {
        els.liveStatus.textContent = `Chờ im lặng ${(remaining / 1000).toFixed(1)}s...`;
        els.liveStatus.className = 'live-status listening';
      }
    } else if (liveModeActive && !isEvaluating) {
      els.liveStatus.textContent = isTextMode()
        ? 'Đang nghe... (đọc đúng từ để qua)'
        : 'Đang nghe... (nói rồi im lặng ~2s)';
      els.liveStatus.className = 'live-status listening';
    }

    vadAnimationId = requestAnimationFrame(tick);
  };
  tick();
}

// ─── Audio: TTS sample ──────────────────────────────────────────────────────

function playSample() {
  const w = words[currentIndex];
  if (w.audio_sample_url) {
    new Audio(w.audio_sample_url).play();
    return;
  }
  // Browser TTS fallback (offline)
  if ('speechSynthesis' in window) {
    const utter = new SpeechSynthesisUtterance(w.word);
    utter.lang = 'en-US';
    utter.rate = 0.85;
    speechSynthesis.cancel();
    speechSynthesis.speak(utter);
  }
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
          checkTextModePass();
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
  els.spinner.classList.remove('hidden');

  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');
  formData.append('target_word', w.word);
  formData.append('target_ipa', w.ipa);
  formData.append('target_phonemes', JSON.stringify(w.phonemes || []));

  try {
    const res = await fetch(`${getApiBase()}/api/v1/evaluate`, {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();
    els.spinner.classList.add('hidden');
    isEvaluating = false;

    if (!res.ok) {
      const msg = typeof data.detail === 'object'
        ? (data.detail?.error || JSON.stringify(data.detail))
        : (data.detail || data.error || 'Lỗi không xác định');
      if (fromLive) {
        showLiveHint('Lỗi phân tích: ' + msg, 'mis');
      } else {
        console.warn('Lỗi đánh giá:', msg);
      }
      return;
    }

    renderEvaluation(data, { fromLive });
  } catch (err) {
    els.spinner.classList.add('hidden');
    isEvaluating = false;
    if (fromLive) {
      showLiveHint(`Không kết nối backend (${getApiBase()}). Chạy: cd backend && uvicorn main:app --port 8000`, 'mis');
    } else if (!blob) {
      alert('Không kết nối được backend. Hãy chạy: uvicorn main:app --port 8000\n\n' + err.message);
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
    showLiveHint(`✓ Đúng rồi! (${data.overall_score}%) — chuyển từ tiếp theo...`, 'ok');
    const delay = fromLive ? 1200 : 1500;
    setTimeout(() => {
      hideLiveHint();
      nextWord();
    }, delay);
  } else {
    els.btnRetry.classList.remove('hidden');
    const issues = data.phonemes.filter((p) => p.label !== 'ok' && p.suggestion);
    const hintText = issues.length
      ? issues.map((p) => `${p.ipa}: ${p.suggestion}`).join(' · ')
      : `Chưa đạt (${data.overall_score}%) — thử đọc lại "${data.word}"`;
    showLiveHint(hintText, 'mis');
    if (fromLive) {
      els.liveStatus.textContent = 'Đọc lại từ này...';
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
    els.settingsPanel.classList.add('hidden');
    checkBackend();
  });

  window.addEventListener('beforeunload', () => stopLiveMode());
}

init();
