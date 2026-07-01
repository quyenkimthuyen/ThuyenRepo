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
import { speakText, stopSpeaking, isSpeaking } from './tts.js';
import { ICONS, iconFragment } from './icons.js';

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
  autoReadSample: document.getElementById('auto-read-sample'),
  btnMicToggle: document.getElementById('btn-mic-toggle'),
  btnAutoRead: document.getElementById('btn-auto-read'),
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
let resumeMicAfterTts = false;

/** @type {typeof LESSONS[0] | null} */
let lesson = null;

/** @type {LessonState} */
let sentenceStates = [];

let currentSentenceIndex = 0;
let lessonComplete = false;
let autoReadSample = false;
let topicFilter = 'all';
let levelFilter = 'all';

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
  loadSavedLesson();
  updateMicToggleUi();
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
    }
  } catch {
    autoReadSample = false;
  }
  els.autoReadSample.checked = autoReadSample;
  updateAutoReadUi();
}

function updateAutoReadUi() {
  els.btnAutoRead.classList.toggle('is-on', autoReadSample);
  els.btnAutoRead.setAttribute('aria-pressed', String(autoReadSample));
  if (els.autoReadSample) els.autoReadSample.checked = autoReadSample;
}

function updateMicToggleUi() {
  const on = micUserEnabled;
  const live = listening;
  const sample = isSpeaking();

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
  } else if (live) {
    els.micStatus.textContent = 'Mic đang nghe…';
    els.micStatus.classList.add('is-live');
  } else {
    els.micStatus.textContent = on ? 'Mic bật' : 'Mic tắt';
    els.micStatus.classList.remove('is-live');
  }
}

function pauseMicForTts() {
  if (!listening) return;
  resumeMicAfterTts = true;
  stopMic({ keepEnabled: true });
}

async function resumeMicAfterSample() {
  if (!resumeMicAfterTts || !micUserEnabled || lessonComplete || isSpeaking()) {
    resumeMicAfterTts = false;
    updateMicToggleUi();
    return;
  }
  resumeMicAfterTts = false;
  startMic();
}

function toggleMic() {
  if (lessonComplete) return;
  if (micUserEnabled) {
    resumeMicAfterTts = false;
    stopMic();
  } else {
    micUserEnabled = true;
    if (!isSpeaking()) startMic();
    else updateMicToggleUi();
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
      JSON.stringify({ autoReadSample, topicFilter, levelFilter }),
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

function onFiltersChanged() {
  topicFilter = els.topicSelect.value;
  levelFilter = els.levelFilter.value;
  saveSettings();
  stopMic();
  populateLessonSelect();
  if (els.lessonSelect.value) {
    loadLesson(els.lessonSelect.value);
  }
}

function bindEvents() {
  els.lessonSelect.addEventListener('change', () => {
    stopMic();
    loadLesson(els.lessonSelect.value);
  });

  els.topicSelect.addEventListener('change', onFiltersChanged);
  els.levelFilter.addEventListener('change', onFiltersChanged);

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

  els.btnMicToggle.addEventListener('click', toggleMic);
  els.btnReadSample.addEventListener('click', readCurrentSample);
  els.btnPrevSentence.addEventListener('click', goPrevSentence);
  els.btnNextSentence.addEventListener('click', goNextSentence);
  els.btnResetSentence.addEventListener('click', resetCurrentSentence);
  els.btnResetLesson.addEventListener('click', resetLesson);
  els.btnRestart.addEventListener('click', () => {
    resetLesson();
    startMic();
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
  stopMic();
  loadLesson(lessonId);
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
      stopMic();
      loadLesson(item.id);
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
    stopMic();
    if (els.lessonSelect.value) {
      loadLesson(els.lessonSelect.value);
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
  if (els.lessonSelect.value) {
    loadLesson(els.lessonSelect.value);
  }
}

/**
 * @param {string} lessonId
 */
function loadLesson(lessonId) {
  const found = findLessonById(lessonId);
  if (!found) return;

  lesson = found;
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
  stopMic();
  stopSpeaking();
  sentenceStates.forEach((st) => st.matched.clear());
  currentSentenceIndex = 0;
  lessonComplete = false;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  render();
  saveProgress();
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

  currentSentenceIndex = index;
  lessonComplete = false;
  lastFinalResultIndex = -1;
  lastInterimText = '';
  render();
  saveProgress();
  maybeAutoReadSample();
}

async function readCurrentSample() {
  if (!lesson || lessonComplete || isSpeaking()) return;
  const text = lesson.sentences[currentSentenceIndex];
  if (!text) return;

  pauseMicForTts();
  updateMicToggleUi();

  try {
    const ok = await speakText(text);
    if (!ok) {
      showError('Trình duyệt không hỗ trợ đọc mẫu (Text-to-Speech).');
    }
  } finally {
    await resumeMicAfterSample();
    updateMicToggleUi();
  }
}

function maybeAutoReadSample() {
  if (!autoReadSample || lessonComplete || !lesson || isSpeaking()) return;
  void readCurrentSample();
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

    els.sentencesRoot.appendChild(p);
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
  if (lessonComplete || isSpeaking()) return;

  if (!micUserEnabled) micUserEnabled = true;

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
    updateMicToggleUi();
    hideError();
  };

  recognition.onend = () => {
    listening = false;
    updateMicToggleUi();

    if (!lessonComplete && recognition?._wantRestart && micUserEnabled && !isSpeaking()) {
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
    if (isSpeaking()) return;

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

  recognition._wantRestart = true;

  try {
    recognition.start();
  } catch {
    showError('Không thể bật mic. Hãy mở app qua http://localhost (không dùng file://).');
  }
}

function stopMic({ keepEnabled = false } = {}) {
  if (!keepEnabled) {
    micUserEnabled = false;
    resumeMicAfterTts = false;
  }

  if (!recognition) {
    listening = false;
    updateMicToggleUi();
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
