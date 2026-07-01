import { LESSONS } from './lessons.js';
import {
  tokenizeSentence,
  wordsFromTranscript,
  matchAccumulating,
  isSentenceComplete,
} from './matcher.js';

const STORAGE_KEY = 'reading-aloud-progress';

/** @typedef {{ tokens: { display: string, normalized: string }[], matched: Set<number> }[]} LessonState */

const els = {
  lessonSelect: document.getElementById('lesson-select'),
  btnStart: document.getElementById('btn-start'),
  btnStop: document.getElementById('btn-stop'),
  btnResetSentence: document.getElementById('btn-reset-sentence'),
  btnResetLesson: document.getElementById('btn-reset-lesson'),
  btnRestart: document.getElementById('btn-restart'),
  micDot: document.getElementById('mic-dot'),
  micStatus: document.getElementById('mic-status'),
  progressText: document.getElementById('progress-text'),
  liveTranscript: document.getElementById('live-transcript'),
  lessonTitle: document.getElementById('lesson-title'),
  sentencesRoot: document.getElementById('sentences-root'),
  completionBanner: document.getElementById('completion-banner'),
  errorBanner: document.getElementById('error-banner'),
};

/** @type {SpeechRecognition | null} */
let recognition = null;
let listening = false;

/** @type {typeof LESSONS[0] | null} */
let lesson = null;

/** @type {LessonState} */
let sentenceStates = [];

let currentSentenceIndex = 0;
let lessonComplete = false;

/** Track processed final result index to avoid double-processing */
let lastFinalResultIndex = -1;

/** Last interim text for display only */
let lastInterimText = '';

init();

function init() {
  populateLessonSelect();
  bindEvents();
  loadSavedLesson();
}

function populateLessonSelect() {
  els.lessonSelect.innerHTML = LESSONS.map(
    (l) => `<option value="${l.id}">${l.title}</option>`,
  ).join('');
}

function bindEvents() {
  els.lessonSelect.addEventListener('change', () => {
    stopMic();
    loadLesson(els.lessonSelect.value);
  });

  els.btnStart.addEventListener('click', startMic);
  els.btnStop.addEventListener('click', stopMic);
  els.btnResetSentence.addEventListener('click', resetCurrentSentence);
  els.btnResetLesson.addEventListener('click', resetLesson);
  els.btnRestart.addEventListener('click', () => {
    resetLesson();
    startMic();
  });
}

function loadSavedLesson() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved.lessonId && LESSONS.some((l) => l.id === saved.lessonId)) {
        els.lessonSelect.value = saved.lessonId;
      }
    }
  } catch {
    /* ignore */
  }
  loadLesson(els.lessonSelect.value);
}

/**
 * @param {string} lessonId
 */
function loadLesson(lessonId) {
  const found = LESSONS.find((l) => l.id === lessonId);
  if (!found) return;

  lesson = found;
  sentenceStates = lesson.sentences.map((s) => ({
    tokens: tokenizeSentence(s),
    matched: new Set(),
  }));

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved.lessonId === lessonId && Array.isArray(saved.matchedBySentence)) {
        saved.matchedBySentence.forEach((indices, i) => {
          if (!sentenceStates[i]) return;
          indices.forEach((idx) => sentenceStates[i].matched.add(idx));
        });
        if (typeof saved.currentSentenceIndex === 'number') {
          currentSentenceIndex = clampSentenceIndex(saved.currentSentenceIndex);
        }
      }
    }
  } catch {
    currentSentenceIndex = 0;
  }

  if (!savedProgressValid()) {
    currentSentenceIndex = findFirstIncompleteSentence();
  }

  lessonComplete = currentSentenceIndex >= sentenceStates.length;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  hideError();
  render();
  saveProgress();
}

function savedProgressValid() {
  for (let i = 0; i < currentSentenceIndex; i++) {
    const st = sentenceStates[i];
    if (!isSentenceComplete(st.matched, st.tokens.length)) return false;
  }
  return true;
}

function findFirstIncompleteSentence() {
  for (let i = 0; i < sentenceStates.length; i++) {
    const st = sentenceStates[i];
    if (!isSentenceComplete(st.matched, st.tokens.length)) return i;
  }
  return sentenceStates.length;
}

function clampSentenceIndex(idx) {
  return Math.max(0, Math.min(idx, sentenceStates.length));
}

function resetLesson() {
  stopMic();
  sentenceStates.forEach((st) => st.matched.clear());
  currentSentenceIndex = 0;
  lessonComplete = false;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  render();
  saveProgress();
}

function resetCurrentSentence() {
  if (lessonComplete || !sentenceStates[currentSentenceIndex]) return;
  sentenceStates[currentSentenceIndex].matched.clear();
  lessonComplete = false;
  lastFinalResultIndex = -1;
  render();
  saveProgress();
}

function render() {
  if (!lesson) return;

  els.lessonTitle.textContent = lesson.title;
  els.sentencesRoot.innerHTML = '';

  sentenceStates.forEach((st, i) => {
    const p = document.createElement('p');
    p.className = 'sentence';
    p.dataset.index = String(i);

    if (lessonComplete || i < currentSentenceIndex) {
      p.classList.add('done');
    } else if (i === currentSentenceIndex) {
      p.classList.add('active');
    } else {
      p.classList.add('pending');
    }

    st.tokens.forEach((tok, ti) => {
      const span = document.createElement('span');
      span.className = 'word';
      span.textContent = tok.display;
      if (st.matched.has(ti) || i < currentSentenceIndex || lessonComplete) {
        span.classList.add('matched');
      }
      p.appendChild(span);
      if (ti < st.tokens.length - 1) {
        p.appendChild(document.createTextNode(' '));
      }
    });

    els.sentencesRoot.appendChild(p);
  });

  const total = sentenceStates.length;
  const doneCount = lessonComplete
    ? total
    : sentenceStates.filter((st, i) =>
        i < currentSentenceIndex || isSentenceComplete(st.matched, st.tokens.length),
      ).length;

  els.progressText.textContent = lessonComplete
    ? `Hoàn thành ${total} / ${total} câu`
    : `Câu ${Math.min(currentSentenceIndex + 1, total)} / ${total} · Đã xong ${doneCount} câu`;

  els.completionBanner.classList.toggle('hidden', !lessonComplete);
  els.sentencesRoot.classList.toggle('hidden', lessonComplete);

  const activeEl = els.sentencesRoot.querySelector('.sentence.active');
  if (activeEl) {
    activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function saveProgress() {
  if (!lesson) return;
  const payload = {
    lessonId: lesson.id,
    currentSentenceIndex,
    matchedBySentence: sentenceStates.map((st) => [...st.matched]),
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* ignore quota */
  }
}

function processTranscript(transcript, isFinal) {
  if (lessonComplete || !sentenceStates[currentSentenceIndex]) return;

  const spokenWords = wordsFromTranscript(transcript);
  if (!spokenWords.length) return;

  const st = sentenceStates[currentSentenceIndex];
  const newlyMatched = matchAccumulating(spokenWords, st.tokens, st.matched);

  if (newlyMatched.length) {
    render();
    saveProgress();
  }

  if (isSentenceComplete(st.matched, st.tokens.length)) {
    advanceSentence();
  }
}

function advanceSentence() {
  currentSentenceIndex += 1;
  lastFinalResultIndex = -1;
  lastInterimText = '';

  if (currentSentenceIndex >= sentenceStates.length) {
    lessonComplete = true;
    stopMic();
  }

  render();
  saveProgress();
}

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function startMic() {
  if (lessonComplete) return;

  const Ctor = getSpeechRecognitionCtor();
  if (!Ctor) {
    showError(
      'Trình duyệt không hỗ trợ nhận dạng giọng nói. Hãy dùng Chrome hoặc Edge.',
    );
    return;
  }

  if (listening) return;

  recognition = new Ctor();
  recognition.lang = 'en-US';
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  lastFinalResultIndex = -1;
  lastInterimText = '';

  recognition.onstart = () => {
    listening = true;
    els.micDot.classList.add('listening');
    els.micStatus.textContent = 'Đang nghe…';
    els.btnStart.disabled = true;
    els.btnStop.disabled = false;
    hideError();
  };

  recognition.onend = () => {
    listening = false;
    els.micDot.classList.remove('listening');
    els.micStatus.textContent = 'Mic đã dừng';
    els.btnStart.disabled = lessonComplete;
    els.btnStop.disabled = true;

    if (!lessonComplete && recognition?._wantRestart) {
      try {
        recognition.start();
      } catch {
        /* ignore */
      }
    }
  };

  recognition.onerror = (event) => {
    if (event.error === 'not-allowed') {
      showError('Cần quyền microphone. Hãy cho phép truy cập mic và thử lại.');
      stopMic();
      return;
    }
    if (event.error === 'no-speech') {
      return;
    }
    if (event.error === 'aborted') {
      return;
    }
    showError(`Lỗi mic: ${event.error}`);
  };

  recognition.onresult = (event) => {
    let interim = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const text = result[0].transcript;

      if (result.isFinal) {
        if (i > lastFinalResultIndex) {
          processTranscript(text, true);
          lastFinalResultIndex = i;
        }
        interim = '';
      } else {
        interim += text;
      }
    }

    if (interim) {
      lastInterimText = interim.trim();
      els.liveTranscript.textContent = lastInterimText || '—';
      processTranscript(interim, false);
    } else if (event.results[event.results.length - 1]?.isFinal) {
      const finalText = event.results[event.results.length - 1][0].transcript.trim();
      els.liveTranscript.textContent = finalText || '—';
    }
  };

  recognition._wantRestart = true;

  try {
    recognition.start();
  } catch (err) {
    showError('Không thể bật mic. Hãy mở app qua http://localhost (không dùng file://).');
  }
}

function stopMic() {
  if (!recognition) {
    listening = false;
    els.micDot.classList.remove('listening');
    els.micStatus.textContent = 'Mic chưa bật';
    els.btnStart.disabled = lessonComplete;
    els.btnStop.disabled = true;
    return;
  }

  recognition._wantRestart = false;
  try {
    recognition.stop();
  } catch {
    /* ignore */
  }
  recognition = null;
  listening = false;
  els.micDot.classList.remove('listening');
  els.micStatus.textContent = 'Mic đã dừng';
  els.btnStart.disabled = lessonComplete;
  els.btnStop.disabled = true;
}

/**
 * @param {string} message
 */
function showError(message) {
  els.errorBanner.textContent = message;
  els.errorBanner.classList.remove('hidden');
}

function hideError() {
  els.errorBanner.classList.add('hidden');
  els.errorBanner.textContent = '';
}
