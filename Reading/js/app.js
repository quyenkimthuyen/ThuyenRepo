import { LESSONS, LEVELS, TOPICS, filterLessons, getTopicLabel } from './lessons.js';
import {
  loadCustomLessons,
  saveCustomLessons,
  buildCustomLesson,
  parseImportJson,
  addCustomLesson,
  removeCustomLesson,
} from './customLessons.js';
import {
  tokenizeSentence,
  wordsFromTranscript,
  matchAccumulating,
  isSentenceComplete,
} from './matcher.js';
import {
  speakText,
  stopSpeaking,
  isSpeaking,
  getEnglishVoices,
  onVoicesReady,
  setSelectedVoiceUri,
  getSelectedVoiceUri,
  formatVoiceLabel,
  isTtsSupported,
} from './tts.js';
import { ICONS, iconFragment } from './icons.js';
import { getLessonTranslations } from './lessonTranslations.js';

const STORAGE_KEY = 'reading-aloud-progress';
const SETTINGS_KEY = 'reading-aloud-settings';

/** Old lesson ids before level-based naming */
const LEGACY_LESSON_IDS = {
  'self-intro': 'a2-self-intro',
  weekend: 'a2-weekend',
};

/**
 * @param {string} id
 * @returns {string}
 */
function resolveLessonId(id) {
  return LEGACY_LESSON_IDS[id] ?? id;
}

/** @typedef {{ tokens: { display: string, normalized: string }[], matched: Set<number> }[]} LessonState */

const els = {
  topicSelect: document.getElementById('topic-select'),
  levelFilter: document.getElementById('level-filter'),
  lessonSelect: document.getElementById('lesson-select'),
  voiceSelect: document.getElementById('voice-select'),
  autoReadSample: document.getElementById('auto-read-sample'),
  btnMicToggle: document.getElementById('btn-mic-toggle'),
  btnAutoRead: document.getElementById('btn-auto-read'),
  btnShowVietnamese: document.getElementById('btn-show-vietnamese'),
  btnReadSample: document.getElementById('btn-read-sample'),
  btnPrevSentence: document.getElementById('btn-prev-sentence'),
  btnNextSentence: document.getElementById('btn-next-sentence'),
  btnResetSentence: document.getElementById('btn-reset-sentence'),
  btnResetLesson: document.getElementById('btn-reset-lesson'),
  btnRestart: document.getElementById('btn-restart'),
  micStatus: document.getElementById('mic-status'),
  progressText: document.getElementById('progress-text'),
  liveTranscript: document.getElementById('live-transcript'),
  lessonTitle: document.getElementById('lesson-title'),
  sentencesRoot: document.getElementById('sentences-root'),
  completionBanner: document.getElementById('completion-banner'),
  errorBanner: document.getElementById('error-banner'),
  importLevel: document.getElementById('import-level'),
  importTopic: document.getElementById('import-topic'),
  importTitle: document.getElementById('import-title'),
  importFormat: document.getElementById('import-format'),
  importContent: document.getElementById('import-content'),
  importContentLabel: document.getElementById('import-content-label'),
  importFile: document.getElementById('import-file'),
  btnImportSave: document.getElementById('btn-import-save'),
  importFeedback: document.getElementById('import-feedback'),
  customLessonsList: document.getElementById('custom-lessons-list'),
  customLessonsUl: document.getElementById('custom-lessons-ul'),
  btnDeleteCustom: document.getElementById('btn-delete-custom'),
  btnImportToggle: document.getElementById('btn-import-toggle'),
  btnImportClose: document.getElementById('btn-import-close'),
  importPanel: document.getElementById('import-panel'),
};

/** @type {SpeechRecognition | null} */
let recognition = null;
let listening = false;
let micUserEnabled = false;
let micStarting = false;
let samplePlaying = false;
let samplePlayGeneration = 0;
let micSessionGeneration = 0;
let micRestartTimer = 0;

/** @type {typeof LESSONS[0] | null} */
let lesson = null;

/** @type {LessonState} */
let sentenceStates = [];

let currentSentenceIndex = 0;
let lessonComplete = false;
let autoReadSample = false;
let topicFilter = 'all';
let levelFilter = 'all';
let ttsVoiceUri = '';
let pendingAutoStartMic = false;
let micAwaitingGesture = false;
let gestureMicListenerAttached = false;
let showVietnamese = false;

/** Track processed final result index to avoid double-processing */
let lastFinalResultIndex = -1;

/** Last interim text for display only */
let lastInterimText = '';

/** Skip auto-read when restoring saved lesson on first paint */
let suppressAutoReadOnce = false;

/** @type {import('./lessons.js').Lesson[]} */
let customLessons = [];

function getAllLessons() {
  return [...LESSONS, ...customLessons];
}

/**
 * @param {string} id
 * @returns {import('./lessons.js').Lesson | undefined}
 */
function findLessonById(id) {
  const resolved = resolveLessonId(id);
  return getAllLessons().find((l) => l.id === resolved);
}

init();

function init() {
  customLessons = loadCustomLessons();
  loadSettings();
  populateFilters();
  populateImportForm();
  populateLessonSelect();
  renderCustomLessonsList();
  bindEvents();
  onVoicesReady(populateVoiceSelect);
  loadSavedLesson();
  updateMicToggleUi();
}

function populateVoiceSelect() {
  const voices = getEnglishVoices();
  const previous = els.voiceSelect.value || ttsVoiceUri || getSelectedVoiceUri() || '';

  els.voiceSelect.innerHTML = '';

  if (!voices.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = isTtsSupported() ? 'Không có giọng tiếng Anh' : 'TTS không hỗ trợ';
    els.voiceSelect.appendChild(opt);
    els.voiceSelect.disabled = true;
    return;
  }

  els.voiceSelect.disabled = false;

  const groups = [
    { id: 'us', label: 'US English', match: (/** @type {SpeechSynthesisVoice} */ v) => v.lang.toLowerCase().startsWith('en-us') },
    { id: 'gb', label: 'UK English', match: (/** @type {SpeechSynthesisVoice} */ v) => v.lang.toLowerCase().startsWith('en-gb') },
    { id: 'other', label: 'Khác', match: () => true },
  ];

  const used = new Set();

  for (const group of groups) {
    const inGroup = voices.filter((v) => {
      if (used.has(v.voiceURI)) return false;
      if (group.id === 'other') {
        return !v.lang.toLowerCase().startsWith('en-us') && !v.lang.toLowerCase().startsWith('en-gb');
      }
      return group.match(v);
    });
    inGroup.forEach((v) => used.add(v.voiceURI));
    if (!inGroup.length) continue;

    const optgroup = document.createElement('optgroup');
    optgroup.label = group.label;
    for (const voice of inGroup) {
      const opt = document.createElement('option');
      opt.value = voice.voiceURI;
      opt.textContent = formatVoiceLabel(voice);
      optgroup.appendChild(opt);
    }
    els.voiceSelect.appendChild(optgroup);
  }

  const hasPrevious = voices.some((v) => v.voiceURI === previous);
  const fallback = resolveDefaultVoiceUri(voices);
  const chosen = hasPrevious ? previous : fallback;

  els.voiceSelect.value = chosen;
  ttsVoiceUri = chosen;
  setSelectedVoiceUri(chosen);
  saveSettings();
}

/**
 * @param {SpeechSynthesisVoice[]} voices
 * @returns {string}
 */
function resolveDefaultVoiceUri(voices) {
  const pick =
    voices.find((v) => v.lang.toLowerCase().startsWith('en-us') && v.localService) ||
    voices.find((v) => v.lang.toLowerCase().startsWith('en-us')) ||
    voices.find((v) => v.lang.toLowerCase().startsWith('en-gb')) ||
    voices[0];
  return pick?.voiceURI ?? '';
}

function tryAutoStartMic() {
  if (lessonComplete || !pendingAutoStartMic) return;
  pendingAutoStartMic = false;
  armMicByDefault();
}

function armMicByDefault() {
  if (lessonComplete) return;
  micUserEnabled = true;
  micAwaitingGesture = false;
  startMic();
  attachMicGestureListener();
}

function attachMicGestureListener() {
  if (gestureMicListenerAttached) return;
  gestureMicListenerAttached = true;

  const tryStartFromGesture = () => {
    if (!micUserEnabled || listening || lessonComplete || isSpeaking() || samplePlaying) return;
    micAwaitingGesture = false;
    startMic();
  };

  document.addEventListener('pointerdown', tryStartFromGesture, { passive: true });
  document.addEventListener('keydown', tryStartFromGesture);
}

function populateImportForm() {
  els.importLevel.innerHTML = LEVELS.map(
    (l) => `<option value="${l.id}">${l.label}</option>`,
  ).join('');
  els.importTopic.innerHTML = TOPICS.map(
    (t) => `<option value="${t.id}">${t.label}</option>`,
  ).join('');
  els.importLevel.value = 'b1';
  els.importTopic.value = 'custom';
}

function populateFilters() {
  els.topicSelect.innerHTML =
    '<option value="all">Tất cả chủ đề</option>' +
    TOPICS.map((t) => `<option value="${t.id}">${t.label}</option>`).join('');

  els.levelFilter.innerHTML =
    '<option value="all">Tất cả cấp độ</option>' +
    LEVELS.map((l) => `<option value="${l.id}">${l.label}</option>`).join('');

  els.topicSelect.value = topicFilter;
  els.levelFilter.value = levelFilter;
}

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) {
      const settings = JSON.parse(raw);
      autoReadSample = Boolean(settings.autoReadSample);
      if (settings.topicFilter) topicFilter = settings.topicFilter;
      if (settings.levelFilter) levelFilter = settings.levelFilter;
      if (settings.ttsVoiceUri) ttsVoiceUri = settings.ttsVoiceUri;
      if (ttsVoiceUri) setSelectedVoiceUri(ttsVoiceUri);
      showVietnamese = Boolean(settings.showVietnamese);
    }
  } catch {
    autoReadSample = false;
  }
  els.autoReadSample.checked = autoReadSample;
  updateAutoReadUi();
  updateVietnameseUi();
}

function updateVietnameseUi() {
  if (!els.btnShowVietnamese) return;
  els.btnShowVietnamese.classList.toggle('is-on', showVietnamese);
  els.btnShowVietnamese.setAttribute('aria-pressed', String(showVietnamese));
  document.body.classList.toggle('show-vietnamese', showVietnamese);
}

function updateAutoReadUi() {
  els.btnAutoRead.classList.toggle('is-on', autoReadSample);
  els.btnAutoRead.setAttribute('aria-pressed', String(autoReadSample));
  if (els.autoReadSample) els.autoReadSample.checked = autoReadSample;
}

function updateMicToggleUi() {
  const on = micUserEnabled;
  const live = listening;
  const sample = samplePlaying || isSpeaking();
  const starting = micStarting || micRestartTimer > 0;

  els.btnMicToggle.classList.toggle('is-on', on);
  els.btnMicToggle.setAttribute('aria-pressed', String(on));
  els.btnMicToggle.disabled = lessonComplete;
  els.btnMicToggle.title = on ? 'Tắt mic' : 'Bật mic';
  els.btnMicToggle.setAttribute('aria-label', on ? 'Tắt mic' : 'Bật mic');
  els.btnMicToggle.querySelector('.mic-icon-on')?.classList.toggle('hidden', on);
  els.btnMicToggle.querySelector('.mic-icon-off')?.classList.toggle('hidden', !on);

  if (sample) {
    els.micStatus.textContent = 'Đang phát mẫu…';
    els.micStatus.classList.remove('is-live');
  } else if (starting) {
    els.micStatus.textContent = 'Đang bật mic…';
    els.micStatus.classList.remove('is-live');
  } else if (live) {
    els.micStatus.textContent = 'Mic đang nghe…';
    els.micStatus.classList.add('is-live');
  } else {
    els.micStatus.textContent = on ? 'Mic bật' : 'Mic tắt';
    els.micStatus.classList.remove('is-live');
  }
}

function setSampleControlsBusy(busy) {
  samplePlaying = busy;
  const disabled = lessonComplete || busy;
  els.btnReadSample.disabled = disabled;
  els.btnReadSample.classList.toggle('is-busy', busy);
  els.btnAutoRead.disabled = busy;
}

function pauseMicForSample() {
  if (!listening) return;
  stopMic({ keepEnabled: true });
}

function clearMicRestartTimer() {
  if (!micRestartTimer) return;
  window.clearTimeout(micRestartTimer);
  micRestartTimer = 0;
}

function invalidateMicSession() {
  micSessionGeneration += 1;
  lastFinalResultIndex = -1;
  lastInterimText = '';
}

function scheduleMicRestart(delay = 120) {
  clearMicRestartTimer();
  if (!micUserEnabled || micAwaitingGesture || lessonComplete || isSpeaking() || samplePlaying) {
    updateMicToggleUi();
    return;
  }

  micRestartTimer = window.setTimeout(() => {
    micRestartTimer = 0;
    if (micUserEnabled && !micAwaitingGesture && !lessonComplete && !isSpeaking() && !samplePlaying) {
      startMic();
    } else {
      updateMicToggleUi();
    }
  }, delay);
  updateMicToggleUi();
}

/** Dừng recognition hiện tại và bật lại nếu mic vẫn đang bật (không tắt hẳn). */
function restartMic() {
  if (!micUserEnabled || lessonComplete || isSpeaking() || samplePlaying) return;

  if (listening || recognition) {
    stopMic({ keepEnabled: true });
    scheduleMicRestart();
    return;
  }

  if (!micAwaitingGesture) {
    scheduleMicRestart(40);
  }
}

/**
 * @param {{ autoEnableMic?: boolean }=} options
 */
function pauseMicForContextChange(options = {}) {
  if (options.autoEnableMic) {
    micUserEnabled = true;
    micAwaitingGesture = false;
  }

  if (!micUserEnabled || micAwaitingGesture) {
    invalidateMicSession();
    return false;
  }

  invalidateMicSession();

  if (listening || recognition || micStarting || micRestartTimer) {
    stopMic({ keepEnabled: true });
  }

  return true;
}

function resumeMicAfterContextChange(shouldResume) {
  if (!shouldResume) {
    updateMicToggleUi();
    return;
  }
  restartMic();
}

/**
 * @param {string} lessonId
 * @param {{ autoEnableMic?: boolean }=} options
 */
function switchLesson(lessonId, options = {}) {
  const shouldResumeMic = pauseMicForContextChange(options);
  loadLesson(lessonId);
  resumeMicAfterContextChange(shouldResumeMic);
}

async function readCurrentSample() {
  if (!lesson || lessonComplete || samplePlaying) return;
  const text = lesson.sentences[currentSentenceIndex];
  if (!text) return;

  const playGen = ++samplePlayGeneration;
  const micShouldResume = micUserEnabled && !micAwaitingGesture;

  setSampleControlsBusy(true);
  pauseMicForSample();
  updateMicToggleUi();

  let ok = false;
  try {
    ok = await speakText(text);
  } catch {
    ok = false;
  }

  if (playGen !== samplePlayGeneration) return;

  setSampleControlsBusy(false);

  if (!ok) {
    showError('Trình duyệt không hỗ trợ đọc mẫu (Text-to-Speech).');
  }

  if (micShouldResume && micUserEnabled && !lessonComplete && !listening) {
    startMic();
  }
  updateMicToggleUi();
}

function maybeAutoReadSample() {
  if (!autoReadSample || lessonComplete || !lesson || samplePlaying || isSpeaking()) return;
  void readCurrentSample();
}

function toggleMic() {
  if (lessonComplete || micStarting || samplePlaying) return;
  if (micUserEnabled) {
    stopMic();
  } else {
    micUserEnabled = true;
    micAwaitingGesture = false;
    if (!isSpeaking() && !samplePlaying) startMic();
    else updateMicToggleUi();
  }
}

function invalidateSamplePlayback() {
  samplePlayGeneration += 1;
  if (samplePlaying) {
    stopSpeaking();
    setSampleControlsBusy(false);
  }
}

function toggleImportPanel(forceOpen) {
  const open =
    typeof forceOpen === 'boolean'
      ? forceOpen
      : els.importPanel.classList.contains('hidden');
  els.importPanel.classList.toggle('hidden', !open);
  els.btnImportToggle.classList.toggle('is-on', open);
  els.btnImportToggle.setAttribute('aria-expanded', String(open));
}

function saveSettings() {
  try {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({ autoReadSample, topicFilter, levelFilter, ttsVoiceUri, showVietnamese }),
    );
  } catch {
    /* ignore */
  }
}

function populateLessonSelect() {
  const filtered = filterLessons({ topic: topicFilter, level: levelFilter }, getAllLessons());
  const previousId = els.lessonSelect.value;
  els.lessonSelect.innerHTML = '';

  if (!filtered.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Không có bài phù hợp';
    opt.disabled = true;
    els.lessonSelect.appendChild(opt);
    return;
  }

  const customFiltered = filtered.filter((l) => l.custom);
  const builtInFiltered = filtered.filter((l) => !l.custom);

  if (customFiltered.length) {
    const customGroup = document.createElement('optgroup');
    customGroup.label = 'Bài của tôi';

    for (const item of customFiltered) {
      const opt = document.createElement('option');
      opt.value = item.id;
      const topicName = getTopicLabel(item.topic);
      opt.textContent = `${item.title} · ${topicName}`;
      customGroup.appendChild(opt);
    }

    els.lessonSelect.appendChild(customGroup);
  }

  for (const lvl of LEVELS) {
    const lessonsAtLevel = builtInFiltered.filter((l) => l.level === lvl.id);
    if (!lessonsAtLevel.length) continue;

    const group = document.createElement('optgroup');
    group.label = lvl.label;

    for (const item of lessonsAtLevel) {
      const opt = document.createElement('option');
      opt.value = item.id;
      const topicName = getTopicLabel(item.topic);
      opt.textContent = `${item.title} · ${topicName}`;
      group.appendChild(opt);
    }

    els.lessonSelect.appendChild(group);
  }

  const stillVisible = filtered.some((l) => l.id === resolveLessonId(previousId));
  if (stillVisible && previousId) {
    els.lessonSelect.value = resolveLessonId(previousId);
  }
}

/**
 * @param {{ autoEnableMic?: boolean }=} options
 */
function onFiltersChanged(options = {}) {
  topicFilter = els.topicSelect.value;
  levelFilter = els.levelFilter.value;
  saveSettings();
  populateLessonSelect();
  if (els.lessonSelect.value) {
    switchLesson(els.lessonSelect.value, options);
  }
}

function bindEvents() {
  els.lessonSelect.addEventListener('change', () => {
    switchLesson(els.lessonSelect.value);
  });

  els.voiceSelect.addEventListener('change', () => {
    ttsVoiceUri = els.voiceSelect.value;
    setSelectedVoiceUri(ttsVoiceUri);
    saveSettings();
  });

  els.topicSelect.addEventListener('change', () => onFiltersChanged({ autoEnableMic: true }));
  els.levelFilter.addEventListener('change', () => onFiltersChanged({ autoEnableMic: true }));

  els.autoReadSample.addEventListener('change', () => {
    autoReadSample = els.autoReadSample.checked;
    updateAutoReadUi();
    saveSettings();
  });

  els.btnAutoRead.addEventListener('click', () => {
    autoReadSample = !autoReadSample;
    updateAutoReadUi();
    saveSettings();
  });

  els.btnShowVietnamese?.addEventListener('click', () => {
    showVietnamese = !showVietnamese;
    updateVietnameseUi();
    saveSettings();
    render();
  });

  els.btnMicToggle.addEventListener('click', toggleMic);
  els.btnReadSample.addEventListener('click', readCurrentSample);
  els.btnPrevSentence.addEventListener('click', goPrevSentence);
  els.btnNextSentence.addEventListener('click', goNextSentence);
  els.btnResetSentence.addEventListener('click', resetCurrentSentence);
  els.btnResetLesson.addEventListener('click', resetLesson);
  els.btnRestart.addEventListener('click', () => {
    resetLesson();
    if (!micUserEnabled) {
      micUserEnabled = true;
      micAwaitingGesture = false;
      startMic();
    }
  });

  els.btnImportSave.addEventListener('click', handleImportSave);
  els.importFile.addEventListener('change', handleImportFile);
  els.importFormat.addEventListener('change', updateImportFormatUi);
  els.btnDeleteCustom.addEventListener('click', deleteCurrentCustomLesson);
  els.btnImportToggle.addEventListener('click', () => toggleImportPanel());
  els.btnImportClose.addEventListener('click', () => toggleImportPanel(false));

  updateImportFormatUi();
}

function updateImportFormatUi() {
  const isJson = els.importFormat.value === 'json';
  els.importContentLabel.textContent = isJson
    ? 'Nội dung JSON'
    : 'Nội dung các câu';
  els.importContent.placeholder = isJson
    ? '{\n  "title": "My lesson",\n  "level": "b1",\n  "sentences": ["Line one.", "Line two."]\n}'
    : "Hello, my name is Linh.\nI am studying for the IELTS exam.";
  els.importTitle.closest('.import-field')?.classList.toggle('hidden', isJson);
  els.importLevel.closest('.import-field')?.classList.toggle('hidden', isJson);
  els.importTopic.closest('.import-field')?.classList.toggle('hidden', isJson);
}

/**
 * @param {string} message
 * @param {boolean} isError
 */
function showImportFeedback(message, isError = false) {
  els.importFeedback.textContent = message;
  els.importFeedback.classList.remove('hidden', 'ok', 'err');
  els.importFeedback.classList.add(isError ? 'err' : 'ok');
}

function hideImportFeedback() {
  els.importFeedback.classList.add('hidden');
}

function handleImportSave() {
  hideError();
  const format = els.importFormat.value;
  const content = els.importContent.value.trim();

  if (!content) {
    showImportFeedback('Hãy nhập nội dung hoặc chọn file.', true);
    return;
  }

  if (format === 'json') {
    const { lessons, errors } = parseImportJson(content);
    if (!lessons.length) {
      showImportFeedback(errors.join(' ') || 'JSON không hợp lệ.', true);
      return;
    }
    customLessons = [...customLessons, ...lessons];
    saveCustomLessons(customLessons);
    const last = lessons[lessons.length - 1];
    afterCustomLessonsChanged(last.id, `Đã lưu ${lessons.length} bài từ JSON.`);
    return;
  }

  const { lesson: newLesson, errors } = buildCustomLesson({
    title: els.importTitle.value,
    sentences: content,
    level: els.importLevel.value,
    topic: els.importTopic.value,
  });

  if (!newLesson) {
    showImportFeedback(errors.join(' '), true);
    return;
  }

  customLessons = addCustomLesson(customLessons, newLesson);
  saveCustomLessons(customLessons);
  els.importContent.value = '';
  els.importTitle.value = '';
  afterCustomLessonsChanged(newLesson.id, `Đã lưu bài "${newLesson.title}".`);
}

/**
 * @param {Event} event
 */
function handleImportFile(event) {
  const input = /** @type {HTMLInputElement} */ (event.target);
  const file = input.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result ?? '');
    els.importContent.value = text;

    if (file.name.toLowerCase().endsWith('.json')) {
      els.importFormat.value = 'json';
      updateImportFormatUi();
      try {
        const data = JSON.parse(text);
        const item = Array.isArray(data) ? data[0] : data.lessons?.[0] ?? data;
        if (item?.title) els.importTitle.value = String(item.title);
      } catch {
        /* ignore */
      }
    } else {
      els.importFormat.value = 'text';
      updateImportFormatUi();
      if (!els.importTitle.value.trim()) {
        const baseName = file.name.replace(/\.[^.]+$/, '');
        els.importTitle.value = baseName;
      }
    }

    showImportFeedback(`Đã tải file "${file.name}". Bấm Lưu bài để hoàn tất.`);
  };
  reader.readAsText(file);
  input.value = '';
}

/**
 * @param {string} lessonId
 * @param {string} message
 */
function afterCustomLessonsChanged(lessonId, message) {
  topicFilter = 'all';
  levelFilter = 'all';
  els.topicSelect.value = topicFilter;
  els.levelFilter.value = levelFilter;
  populateLessonSelect();
  renderCustomLessonsList();
  els.lessonSelect.value = lessonId;
  switchLesson(lessonId);
  showImportFeedback(message);
}

function renderCustomLessonsList() {
  if (!customLessons.length) {
    els.customLessonsList.classList.add('hidden');
    els.customLessonsUl.innerHTML = '';
    return;
  }

  els.customLessonsList.classList.remove('hidden');
  els.customLessonsUl.innerHTML = '';

  const sorted = [...customLessons].sort(
    (a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0),
  );

  for (const item of sorted) {
    const li = document.createElement('li');

    const name = document.createElement('span');
    name.textContent = item.title;

    const meta = document.createElement('span');
    meta.className = 'custom-meta';
    meta.textContent = `${item.level.toUpperCase()} · ${getTopicLabel(item.topic)} · ${item.sentences.length} câu`;

    const btnOpen = document.createElement('button');
    btnOpen.type = 'button';
    btnOpen.className = 'icon-btn icon-btn-ghost';
    btnOpen.title = 'Mở';
    btnOpen.setAttribute('aria-label', `Mở ${item.title}`);
    btnOpen.appendChild(iconFragment(ICONS.play));

    const btnDel = document.createElement('button');
    btnDel.type = 'button';
    btnDel.className = 'icon-btn icon-btn-danger';
    btnDel.title = 'Xóa';
    btnDel.setAttribute('aria-label', `Xóa ${item.title}`);
    btnDel.appendChild(iconFragment(ICONS.trash));

    btnOpen.addEventListener('click', () => {
      els.lessonSelect.value = item.id;
      switchLesson(item.id);
    });
    btnDel.addEventListener('click', () => deleteCustomLessonById(item.id));

    li.append(name, meta, btnOpen, btnDel);
    els.customLessonsUl.appendChild(li);
  }
}

/**
 * @param {string} lessonId
 */
function deleteCustomLessonById(lessonId) {
  const target = customLessons.find((l) => l.id === lessonId);
  if (!target) return;
  if (!confirm(`Xóa bài "${target.title}"?`)) return;

  customLessons = removeCustomLesson(customLessons, lessonId);
  saveCustomLessons(customLessons);

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved.lessonId === lessonId) {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  } catch {
    /* ignore */
  }

  renderCustomLessonsList();
  populateLessonSelect();

  if (lesson?.id === lessonId) {
    if (els.lessonSelect.value) {
      switchLesson(els.lessonSelect.value);
    }
  }

  showImportFeedback(`Đã xóa bài "${target.title}".`);
}

function deleteCurrentCustomLesson() {
  if (!lesson?.custom) return;
  deleteCustomLessonById(lesson.id);
}

function loadSavedLesson() {
  let savedId = '';

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved.lessonId) {
        savedId = resolveLessonId(saved.lessonId);
      }
    }
  } catch {
    /* ignore */
  }

  const savedLesson = savedId ? findLessonById(savedId) : null;
  if (savedLesson) {
    const visible = filterLessons(
      { topic: topicFilter, level: levelFilter },
      getAllLessons(),
    ).some((l) => l.id === savedLesson.id);
    if (!visible) {
      topicFilter = 'all';
      levelFilter = 'all';
      els.topicSelect.value = topicFilter;
      els.levelFilter.value = levelFilter;
      populateLessonSelect();
    }
    els.lessonSelect.value = savedLesson.id;
  }

  suppressAutoReadOnce = true;
  pendingAutoStartMic = true;
  if (els.lessonSelect.value) {
    loadLesson(els.lessonSelect.value);
  }
  tryAutoStartMic();
}

/**
 * @param {import('./lessons.js').Lesson} found
 */
function enrichLesson(found) {
  const translations =
    found.translations?.length ? found.translations : getLessonTranslations(found.id);
  return { ...found, translations };
}

/**
 * @param {number} index
 * @returns {string | null}
 */
function getSentenceTranslation(index) {
  const text = lesson?.translations?.[index];
  return text ? String(text) : null;
}

/**
 * @param {string} lessonId
 */
function loadLesson(lessonId) {
  invalidateSamplePlayback();
  const found = findLessonById(lessonId);
  if (!found) return;

  lesson = enrichLesson(found);
  sentenceStates = lesson.sentences.map((s) => ({
    tokens: tokenizeSentence(s),
    matched: new Set(),
  }));

  currentSentenceIndex = 0;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved.lessonId === resolveLessonId(lessonId) && Array.isArray(saved.matchedBySentence)) {
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

  if (!allPriorSentencesComplete(currentSentenceIndex)) {
    currentSentenceIndex = findFirstIncompleteSentence();
  }

  lessonComplete = currentSentenceIndex >= sentenceStates.length;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  hideError();
  render();
  saveProgress();

  if (!suppressAutoReadOnce) {
    maybeAutoReadSample();
  }
  suppressAutoReadOnce = false;
}

function allPriorSentencesComplete(upToIndex) {
  for (let i = 0; i < upToIndex; i++) {
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
  const shouldResumeMic = pauseMicForContextChange();
  invalidateSamplePlayback();
  stopSpeaking();
  sentenceStates.forEach((st) => st.matched.clear());
  currentSentenceIndex = 0;
  lessonComplete = false;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  render();
  saveProgress();
  resumeMicAfterContextChange(shouldResumeMic);
  maybeAutoReadSample();
}

function resetCurrentSentence() {
  if (lessonComplete || !sentenceStates[currentSentenceIndex]) return;
  sentenceStates[currentSentenceIndex].matched.clear();
  lessonComplete = false;
  lastFinalResultIndex = -1;
  render();
  saveProgress();
}

function goPrevSentence() {
  if (lessonComplete || currentSentenceIndex <= 0) return;
  goToSentence(currentSentenceIndex - 1);
}

function goNextSentence() {
  if (lessonComplete) return;
  if (currentSentenceIndex < sentenceStates.length - 1) {
    goToSentence(currentSentenceIndex + 1);
  }
}

/**
 * @param {number} index
 */
function goToSentence(index) {
  if (!sentenceStates[index] || lessonComplete) return;

  const shouldResumeMic = pauseMicForContextChange();
  currentSentenceIndex = index;
  lessonComplete = false;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  render();
  saveProgress();
  resumeMicAfterContextChange(shouldResumeMic);
  maybeAutoReadSample();
}

function render() {
  if (!lesson) return;

  els.lessonTitle.replaceChildren();

  const topicTag = document.createElement('span');
  topicTag.className = 'topic-tag';
  topicTag.dataset.topic = lesson.topic;
  topicTag.textContent = getTopicLabel(lesson.topic);

  const levelTag = document.createElement('span');
  levelTag.className = 'level-tag';
  levelTag.dataset.level = lesson.level;
  levelTag.textContent = lesson.level.toUpperCase();

  const titleText = document.createElement('span');
  titleText.className = 'title-text';
  titleText.textContent = ` ${lesson.title}`;

  els.lessonTitle.append(topicTag, levelTag, titleText);
  els.sentencesRoot.innerHTML = '';

  sentenceStates.forEach((st, i) => {
    const block = document.createElement('div');
    block.className = 'sentence-block';

    const p = document.createElement('p');
    p.className = 'sentence';
    p.dataset.index = String(i);

    const complete = isSentenceComplete(st.matched, st.tokens.length);

    if (complete) {
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
      if (st.matched.has(ti) || complete) {
        span.classList.add('matched');
      }
      p.appendChild(span);
      if (ti < st.tokens.length - 1) {
        p.appendChild(document.createTextNode(' '));
      }
    });

    block.appendChild(p);

    const viText = getSentenceTranslation(i);
    if (viText) {
      const vi = document.createElement('p');
      vi.className = 'sentence-vi';
      vi.textContent = viText;
      block.appendChild(vi);
    }

    els.sentencesRoot.appendChild(block);
  });

  const total = sentenceStates.length;
  const doneCount = sentenceStates.filter((st) =>
    isSentenceComplete(st.matched, st.tokens.length),
  ).length;

  els.progressText.textContent = lessonComplete
    ? `Hoàn thành ${total} / ${total} câu`
    : `Câu ${currentSentenceIndex + 1} / ${total} · Đã xong ${doneCount} câu`;

  els.completionBanner.classList.toggle('hidden', !lessonComplete);
  els.sentencesRoot.classList.toggle('hidden', lessonComplete);

  els.btnPrevSentence.disabled = lessonComplete || currentSentenceIndex <= 0;
  els.btnNextSentence.disabled =
    lessonComplete || currentSentenceIndex >= sentenceStates.length - 1;
  els.btnReadSample.disabled = lessonComplete;
  els.btnResetSentence.disabled = lessonComplete;
  els.btnDeleteCustom.classList.toggle('hidden', !lesson.custom);
  updateMicToggleUi();

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

function processTranscript(transcript) {
  if (isSpeaking() || lessonComplete || !sentenceStates[currentSentenceIndex]) return;

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
  if (currentSentenceIndex >= sentenceStates.length - 1) {
    currentSentenceIndex = sentenceStates.length;
    lessonComplete = true;
    stopMic();
    stopSpeaking();
    render();
    saveProgress();
    return;
  }

  currentSentenceIndex += 1;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  render();
  saveProgress();
  maybeAutoReadSample();
}

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function startMic() {
  if (lessonComplete || isSpeaking() || samplePlaying || micStarting) return;
  clearMicRestartTimer();

  if (!micUserEnabled) micUserEnabled = true;

  const Ctor = getSpeechRecognitionCtor();
  if (!Ctor) {
    showError(
      'Trình duyệt không hỗ trợ nhận dạng giọng nói. Hãy dùng Chrome hoặc Edge.',
    );
    return;
  }

  if (listening || recognition) return;

  micStarting = true;
  const sessionGeneration = ++micSessionGeneration;
  const currentRecognition = new Ctor();
  recognition = currentRecognition;
  currentRecognition.lang = 'en-US';
  currentRecognition.continuous = true;
  currentRecognition.interimResults = true;
  currentRecognition.maxAlternatives = 1;

  lastFinalResultIndex = -1;
  lastInterimText = '';

  currentRecognition.onstart = () => {
    if (sessionGeneration !== micSessionGeneration) return;
    micStarting = false;
    listening = true;
    updateMicToggleUi();
    hideError();
  };

  currentRecognition.onend = () => {
    if (sessionGeneration !== micSessionGeneration) return;
    listening = false;
    micStarting = false;
    const shouldRestart =
      currentRecognition._wantRestart &&
      micUserEnabled &&
      !lessonComplete &&
      !isSpeaking() &&
      !samplePlaying;
    recognition = null;
    if (shouldRestart) {
      scheduleMicRestart();
    } else {
      updateMicToggleUi();
    }
  };

  currentRecognition.onerror = (event) => {
    if (sessionGeneration !== micSessionGeneration) return;
    if (event.error === 'not-allowed') {
      showError('Cần quyền microphone. Hãy cho phép quyền mic trong trình duyệt.');
      stopMic({ keepEnabled: true });
      micAwaitingGesture = true;
      updateMicToggleUi();
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

  currentRecognition.onresult = (event) => {
    if (sessionGeneration !== micSessionGeneration || isSpeaking() || samplePlaying) return;

    let interim = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const text = result[0].transcript;

      if (result.isFinal) {
        if (i > lastFinalResultIndex) {
          processTranscript(text);
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
      processTranscript(interim);
    } else if (event.results[event.results.length - 1]?.isFinal) {
      const finalText = event.results[event.results.length - 1][0].transcript.trim();
      els.liveTranscript.textContent = finalText || '—';
    }
  };

  currentRecognition._wantRestart = true;

  try {
    currentRecognition.start();
  } catch {
    if (sessionGeneration === micSessionGeneration) {
      invalidateMicSession();
    }
    micStarting = false;
    if (recognition === currentRecognition) {
      recognition = null;
    }
    micAwaitingGesture = micUserEnabled;
    showError('Không thể bật mic. Hãy bấm nút mic để thử lại.');
    updateMicToggleUi();
  }
}

function stopMic({ keepEnabled = false } = {}) {
  clearMicRestartTimer();

  if (!keepEnabled) {
    micUserEnabled = false;
    micAwaitingGesture = false;
  }

  invalidateMicSession();

  if (!recognition) {
    listening = false;
    micStarting = false;
    updateMicToggleUi();
    return;
  }

  const currentRecognition = recognition;
  currentRecognition._wantRestart = false;
  try {
    currentRecognition.stop();
  } catch {
    /* ignore */
  }
  recognition = null;
  listening = false;
  micStarting = false;
  updateMicToggleUi();
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
