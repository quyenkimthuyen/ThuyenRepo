/**
 * PronounceLab Personal — frontend application
 */

const STORAGE_KEY = 'pronouncelab_history';
const SETTINGS_KEY = 'pronouncelab_settings';

/** @type {object} */
let config = {};
/** @type {Array} */
let words = [];
let currentIndex = 0;
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
const MAX_RING_CHUNKS = 24; // ~12 giây
const EVALUATE_COOLDOWN_MS = 2500;

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
  liveToggleLabel: $('live-toggle-label'),
  liveStatus: $('live-status'),
  vadLevel: $('vad-level'),
  liveTranscriptFinal: $('live-transcript-final'),
  liveTranscriptInterim: $('live-transcript-interim'),
  liveTranscriptPlaceholder: $('live-transcript-placeholder'),
};

// ─── Init ───────────────────────────────────────────────────────────────────

async function init() {
  await loadConfig();
  await loadWords();
  loadSettings();
  bindEvents();
  renderWordList();
  showWord(0);
  checkBackend();
  initLiveSpeech();

  if (els.settingLiveAuto?.checked) {
    // Cần user gesture trên một số trình duyệt — thử bật sau 500ms
    setTimeout(() => startLiveMode(), 600);
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
  els.settingApiUrl.value = saved.apiBaseUrl ?? config.apiBaseUrl ?? 'http://127.0.0.1:8000';
  els.settingPassScore.value = saved.passScore ?? config.thresholds?.overallPass ?? 80;
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify({
    autoPlaySample: els.settingAutoplay.checked,
    liveAutoStart: els.settingLiveAuto.checked,
    autoEvaluate: els.settingAutoEvaluate.checked,
    apiBaseUrl: els.settingApiUrl.value,
    passScore: parseInt(els.settingPassScore.value, 10),
  }));
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
        onFinalSpeech(text.trim());
      } else {
        interim += text;
      }
    }
    liveTranscriptInterim = interim;
    updateLiveTranscriptUI();
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

function onFinalSpeech(text) {
  if (!text) return;
  const w = words[currentIndex];
  const tokens = text.split(/\s+/).filter(Boolean);
  const lastToken = tokens[tokens.length - 1] || text;

  if (els.settingAutoEvaluate?.checked && wordsMatch(lastToken, w.word)) {
    maybeAutoEvaluate();
  }
}

async function maybeAutoEvaluate() {
  const now = Date.now();
  if (isEvaluating || now - lastEvaluateTime < EVALUATE_COOLDOWN_MS) return;
  if (!audioRingChunks.length) return;

  lastEvaluateTime = now;
  const mimeType = liveMediaRecorder?.mimeType || 'audio/webm';
  const blob = new Blob(audioRingChunks, { type: mimeType });
  if (blob.size < 500) return;

  userAudioBlob = blob;
  if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
  userAudioUrl = URL.createObjectURL(blob);
  els.btnReplayUser.disabled = false;

  await evaluateRecording(blob);
}

function updateLiveTranscriptUI() {
  const w = words[currentIndex];
  const finalText = liveTranscriptFinal.trim();
  const interimText = liveTranscriptInterim;

  els.liveTranscriptFinal.textContent = finalText;
  els.liveTranscriptInterim.textContent = interimText;

  const hasText = finalText || interimText;
  els.liveTranscriptPlaceholder.classList.toggle('hidden', !!hasText);

  // Highlight nếu khớp từ mục tiêu
  const combined = (finalText + ' ' + interimText).trim();
  const lastWord = combined.split(/\s+/).pop() || '';
  if (wordsMatch(lastWord, w?.word)) {
    els.liveTranscriptInterim.classList.add('match');
    els.liveTranscriptFinal.classList.add('match');
  } else {
    els.liveTranscriptInterim.classList.remove('match');
    els.liveTranscriptFinal.classList.remove('match');
  }
}

function clearLiveTranscript() {
  liveTranscriptFinal = '';
  liveTranscriptInterim = '';
  els.liveTranscriptFinal.textContent = '';
  els.liveTranscriptInterim.textContent = '';
  els.liveTranscriptFinal.classList.remove('match');
  els.liveTranscriptInterim.classList.remove('match');
  els.liveTranscriptPlaceholder.classList.remove('hidden');
}

async function startLiveMode() {
  if (liveModeActive) return;

  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // VAD visualizer
    if (!audioContext) audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(micStream);
    liveAnalyser = audioContext.createAnalyser();
    liveAnalyser.fftSize = 256;
    source.connect(liveAnalyser);
    startVadLoop();

    // Rolling audio buffer cho đánh giá phát âm
    audioRingChunks = [];
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';
    liveMediaRecorder = new MediaRecorder(micStream, { mimeType });
    liveMediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        audioRingChunks.push(e.data);
        if (audioRingChunks.length > MAX_RING_CHUNKS) {
          audioRingChunks.shift();
        }
      }
    };
    liveMediaRecorder.start(RING_CHUNK_MS);

    // Speech recognition
    speechRecognition.start();

    liveModeActive = true;
    els.btnLiveToggle.classList.add('active');
    els.liveToggleLabel.textContent = 'Tắt micro live';
    els.liveStatus.textContent = 'Đang nghe...';
    els.liveStatus.className = 'live-status listening';
    els.recordingIndicator.classList.remove('hidden');
    els.recordingIndicator.innerHTML = '<span class="pulse"></span> Micro live — nói để thấy text';
    els.btnRecord.disabled = true;
  } catch (err) {
    alert('Không thể bật micro: ' + err.message);
  }
}

function stopLiveMode() {
  if (!liveModeActive) return;

  liveModeActive = false;

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
  const data = new Uint8Array(liveAnalyser.frequencyBinCount);

  const tick = () => {
    if (!liveModeActive || !liveAnalyser) return;
    liveAnalyser.getByteFrequencyData(data);
    const avg = data.reduce((a, b) => a + b, 0) / data.length;
    const pct = Math.min(100, (avg / 128) * 100);
    els.vadLevel.style.width = `${pct}%`;

    if (pct > 15) {
      els.liveStatus.textContent = 'Đang nghe bạn nói...';
      els.liveStatus.className = 'live-status speaking';
    } else if (liveModeActive) {
      els.liveStatus.textContent = 'Đang nghe...';
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
      await evaluateRecording();
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

async function evaluateRecording(blob = null) {
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
      const msg = data.detail?.error || data.error || 'Lỗi không xác định';
      console.warn('Lỗi đánh giá:', msg);
      return;
    }

    renderEvaluation(data);
  } catch (err) {
    els.spinner.classList.add('hidden');
    isEvaluating = false;
    if (!blob) {
      alert('Không kết nối được backend. Hãy chạy: uvicorn main:app --port 8000\n\n' + err.message);
    }
  }
}

function renderEvaluation(data) {
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

  renderPhonemeResults(data.phonemes);
  renderFeedback(data.phonemes);
  recordAttempt(data.word, passed, data.overall_score);

  if (passed) {
    els.btnRetry.classList.add('hidden');
    setTimeout(() => nextWord(), 1500);
  } else {
    els.btnRetry.classList.remove('hidden');
  }
}

function renderPhonemeResults(phonemes) {
  els.phonemeContainer.innerHTML = phonemes
    .map((p, i) => `
      <div class="phoneme-box" data-index="${i}" data-start="${p.start}" data-end="${p.end}">
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
  els.btnPlaySample.addEventListener('click', playSample);
  els.btnLiveToggle.addEventListener('click', toggleLiveMode);
  els.btnRecord.addEventListener('click', startRecording);
  els.btnStop.addEventListener('click', stopRecording);
  els.btnReplayUser.addEventListener('click', replayUserAudio);
  els.btnRetry.addEventListener('click', () => {
    resetEvaluationUI();
    const w = words[currentIndex];
    renderPendingPhonemes(w.phonemes || []);
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
