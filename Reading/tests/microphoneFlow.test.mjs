function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function tick(ms = 0) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class FakeClassList {
  constructor() {
    this.items = new Set();
  }

  add(...names) {
    names.forEach((name) => this.items.add(name));
  }

  remove(...names) {
    names.forEach((name) => this.items.delete(name));
  }

  contains(name) {
    return this.items.has(name);
  }

  toggle(name, force) {
    const shouldAdd = typeof force === 'boolean' ? force : !this.items.has(name);
    if (shouldAdd) this.items.add(name);
    else this.items.delete(name);
    return shouldAdd;
  }
}

class FakeElement {
  constructor(tagName = 'div', id = '') {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.children = [];
    this.parentNode = null;
    this.dataset = {};
    this.attributes = new Map();
    this.listeners = new Map();
    this.classList = new FakeClassList();
    this.style = {};
    this.checked = false;
    this.disabled = false;
    this.hidden = false;
    this.type = '';
    this.title = '';
    this.label = '';
    this.placeholder = '';
    this.files = null;
    this._value = '';
    this._textContent = '';
    this._innerHTML = '';
  }

  get value() {
    if (this._value) return this._value;
    return this.findFirstOption()?.value ?? '';
  }

  set value(value) {
    this._value = String(value ?? '');
  }

  get textContent() {
    if (this.children.length) {
      return this.children.map((child) => child.textContent ?? '').join('');
    }
    return this._textContent;
  }

  set textContent(value) {
    this._textContent = String(value ?? '');
    this.children = [];
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set innerHTML(value) {
    this._innerHTML = String(value ?? '');
    this.children = [];
    if (this.tagName === 'SELECT') this._value = '';
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  append(...nodes) {
    nodes.forEach((node) => this.appendChild(typeof node === 'string' ? new FakeTextNode(node) : node));
  }

  replaceChildren(...nodes) {
    this.children = [];
    this._textContent = '';
    this.append(...nodes);
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  addEventListener(type, callback) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(callback);
  }

  dispatchEvent(event) {
    event.target ??= this;
    for (const callback of this.listeners.get(event.type) ?? []) {
      callback(event);
    }
    return true;
  }

  click() {
    this.dispatchEvent({ type: 'click' });
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] ?? null;
  }

  querySelectorAll(selector) {
    const selectors = selector.split('.').filter(Boolean);
    const found = [];
    const visit = (node) => {
      if (node instanceof FakeElement) {
        if (selectors.length && selectors.every((name) => node.classList.contains(name))) {
          found.push(node);
        }
        node.children.forEach(visit);
      }
    };
    this.children.forEach(visit);
    return found;
  }

  closest() {
    return this.parentNode ?? this;
  }

  scrollIntoView() {}

  findFirstOption() {
    if (this.tagName === 'OPTION') return this;
    for (const child of this.children) {
      const opt = child.findFirstOption?.();
      if (opt) return opt;
    }
    return null;
  }
}

class FakeTextNode {
  constructor(text) {
    this.textContent = String(text);
    this.parentNode = null;
  }
}

class FakeDocument {
  constructor(ids) {
    const selectIds = new Set([
      'topic-select',
      'level-filter',
      'lesson-select',
      'voice-select',
      'import-level',
      'import-topic',
      'import-format',
    ]);
    this.nodes = new Map(
      ids.map((id) => [id, new FakeElement(selectIds.has(id) ? 'select' : 'div', id)]),
    );
    this.listeners = new Map();
    this.body = new FakeElement('body', 'body');
  }

  getElementById(id) {
    if (!this.nodes.has(id)) this.nodes.set(id, new FakeElement('div', id));
    return this.nodes.get(id);
  }

  createElement(tagName) {
    const el = new FakeElement(tagName);
    if (tagName.toLowerCase() === 'template') {
      el.content = new FakeElement('fragment');
    }
    return el;
  }

  createTextNode(text) {
    return new FakeTextNode(text);
  }

  addEventListener(type, callback) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(callback);
  }

  dispatchEvent(event) {
    event.target ??= this;
    for (const callback of this.listeners.get(event.type) ?? []) {
      callback(event);
    }
    return true;
  }
}

class FakeLocalStorage {
  constructor() {
    this.store = new Map();
  }

  getItem(key) {
    return this.store.has(key) ? this.store.get(key) : null;
  }

  setItem(key, value) {
    this.store.set(key, String(value));
  }

  removeItem(key) {
    this.store.delete(key);
  }
}

class FakeUtterance {
  constructor(text) {
    this.text = text;
    this.lang = '';
    this.rate = 1;
    this.voice = null;
    this.onend = null;
    this.onerror = null;
  }
}

class FakeRecognition {
  static instances = [];

  constructor() {
    this.active = false;
    this.startCalls = 0;
    this.stopCalls = 0;
    this._wantRestart = false;
    FakeRecognition.instances.push(this);
  }

  start() {
    this.startCalls += 1;
    this.active = true;
    this.onstart?.();
  }

  stop() {
    this.stopCalls += 1;
    this.active = false;
    this.onend?.();
  }
}

const ids = [
  'topic-select',
  'level-filter',
  'lesson-select',
  'voice-select',
  'auto-read-sample',
  'btn-mic-toggle',
  'btn-auto-read',
  'btn-show-vietnamese',
  'btn-read-sample',
  'btn-prev-sentence',
  'btn-next-sentence',
  'btn-reset-sentence',
  'btn-reset-lesson',
  'btn-restart',
  'mic-status',
  'progress-text',
  'live-transcript',
  'lesson-title',
  'sentences-root',
  'completion-banner',
  'error-banner',
  'import-level',
  'import-topic',
  'import-title',
  'import-format',
  'import-content',
  'import-content-label',
  'import-file',
  'btn-import-save',
  'import-feedback',
  'custom-lessons-list',
  'custom-lessons-ul',
  'btn-delete-custom',
  'btn-import-toggle',
  'btn-import-close',
  'import-panel',
  'btn-history-toggle',
  'btn-history-close',
  'btn-history-clear',
  'history-panel',
  'history-summary',
  'history-list',
  'history-detail',
];

const document = new FakeDocument(ids);
const spoken = [];
const speechSynthesis = {
  onvoiceschanged: null,
  speaking: false,
  pendingUtterance: null,
  getVoices() {
    return [{ name: 'Test English', lang: 'en-US', voiceURI: 'test-en-us', localService: true }];
  },
  speak(utterance) {
    this.speaking = true;
    this.pendingUtterance = utterance;
    spoken.push(utterance.text);
  },
  cancel() {
    this.speaking = false;
    this.pendingUtterance = null;
  },
  finish(ok = true) {
    const utterance = this.pendingUtterance;
    this.speaking = false;
    this.pendingUtterance = null;
    if (ok) utterance?.onend?.();
    else utterance?.onerror?.();
  },
};

const window = {
  document,
  localStorage: new FakeLocalStorage(),
  speechSynthesis,
  SpeechSynthesisUtterance: FakeUtterance,
  SpeechRecognition: FakeRecognition,
  webkitSpeechRecognition: FakeRecognition,
  setTimeout,
  clearTimeout,
};

globalThis.window = window;
globalThis.document = document;
globalThis.localStorage = window.localStorage;
globalThis.SpeechSynthesisUtterance = FakeUtterance;
globalThis.confirm = () => true;
globalThis.FileReader = class {};

function activeRecognitionCount() {
  return FakeRecognition.instances.filter((instance) => instance.active).length;
}

let fakeResultIndex = 0;

function emitFinalTranscript(recognition, transcript) {
  const resultIndex = fakeResultIndex;
  fakeResultIndex += 1;
  const results = Array.from({ length: resultIndex + 1 }, () => ({
    0: { transcript: '' },
    isFinal: true,
  }));
  results[resultIndex] = {
    0: { transcript },
    isFinal: true,
  };
  recognition.onresult?.({
    resultIndex,
    results,
  });
}

async function finishSampleAndAssertMicResumes(stepName) {
  assert(document.getElementById('mic-status').textContent === 'Đang phát mẫu…', `${stepName}: status shows sample playback`);
  assert(activeRecognitionCount() === 0, `${stepName}: mic is paused while sample plays`);
  speechSynthesis.finish();
  await tick();
  assert(document.getElementById('mic-status').textContent === 'Mic đang nghe…', `${stepName}: mic resumes after sample`);
  assert(activeRecognitionCount() === 1, `${stepName}: exactly one active recognition after resume`);
  assert(!document.getElementById('btn-read-sample').disabled, `${stepName}: sample button is not stuck busy`);
}

const { appReady } = await import(`../js/app.js?microphone-flow=${Date.now()}`);
await appReady;
await tick();

const micStatus = document.getElementById('mic-status');
const topicSelect = document.getElementById('topic-select');
const lessonSelect = document.getElementById('lesson-select');
const btnMic = document.getElementById('btn-mic-toggle');
const btnReadSample = document.getElementById('btn-read-sample');
const btnAutoRead = document.getElementById('btn-auto-read');
const btnNext = document.getElementById('btn-next-sentence');
const btnPrev = document.getElementById('btn-prev-sentence');

assert(lessonSelect.value === 'a1-greetings', 'first lesson loads by default');
assert(micStatus.textContent === 'Mic đang nghe…', 'mic starts by default on load');
assert(activeRecognitionCount() === 1, 'one recognition is active after load');

btnReadSample.click();
await tick();
assert(spoken.at(-1) === 'Hello.', 'manual sample reads current sentence');
await finishSampleAndAssertMicResumes('manual sample');

btnAutoRead.click();
const staleRecognition = FakeRecognition.instances.find((instance) => instance.active);
lessonSelect.value = 'a1-my-family';
lessonSelect.dispatchEvent({ type: 'change' });
await tick();
assert(spoken.at(-1) === 'This is my mother.', 'lesson change auto-plays the new first sentence');
emitFinalTranscript(staleRecognition, 'This is my mother');
assert(document.getElementById('progress-text').textContent.startsWith('Câu 1 / 5'), 'stale transcript from previous mic session is ignored');
await finishSampleAndAssertMicResumes('lesson change');

btnNext.click();
await tick();
assert(spoken.at(-1) === 'This is my father.', 'next sentence auto-plays sample');
await finishSampleAndAssertMicResumes('next sentence');

btnPrev.click();
await tick();
assert(spoken.at(-1) === 'This is my mother.', 'previous sentence auto-plays sample');
await finishSampleAndAssertMicResumes('previous sentence');

btnMic.click();
await tick();
assert(micStatus.textContent === 'Mic tắt', 'mic toggle turns mic off');
assert(activeRecognitionCount() === 0, 'no active recognition after mic off');

btnMic.click();
await tick();
assert(micStatus.textContent === 'Mic đang nghe…', 'mic toggle turns mic back on');
assert(activeRecognitionCount() === 1, 'one active recognition after mic on');

for (const lessonId of ['a1-at-home', 'morning-routine', 'a1-food']) {
  lessonSelect.value = lessonId;
  lessonSelect.dispatchEvent({ type: 'change' });
  await tick();
  assert(activeRecognitionCount() === 0, `${lessonId}: no mic runs during auto sample`);
  speechSynthesis.finish();
  await tick();
  assert(micStatus.textContent === 'Mic đang nghe…', `${lessonId}: mic status is stable after sample`);
  assert(activeRecognitionCount() === 1, `${lessonId}: only one recognition is active`);
}

btnMic.click();
await tick();
assert(micStatus.textContent === 'Mic tắt', 'mic is off before topic auto-read test');

topicSelect.value = 'travel';
topicSelect.dispatchEvent({ type: 'change' });
await tick();
assert(spoken.at(-1) === 'I am at the park.', 'topic change auto-plays the first filtered lesson');
assert(activeRecognitionCount() === 0, 'topic change keeps mic paused while sample plays');
await finishSampleAndAssertMicResumes('topic change with auto sample');

btnAutoRead.click();
btnMic.click();
await tick();
assert(micStatus.textContent === 'Mic tắt', 'mic is off before topic no-sample test');

topicSelect.value = 'study';
topicSelect.dispatchEvent({ type: 'change' });
await tick(180);
assert(micStatus.textContent === 'Mic đang nghe…', 'topic change starts mic when no sample plays');
assert(activeRecognitionCount() === 1, 'topic change starts exactly one recognition when no sample plays');

for (const transcript of [
  'The sky is blue',
  'The sun is yellow',
  'I have three red apples',
  'There are ten students in the class',
  'My favourite color is green',
]) {
  const active = FakeRecognition.instances.find((instance) => instance.active);
  emitFinalTranscript(active, transcript);
  await tick();
}

assert(document.getElementById('progress-text').textContent === 'Hoàn thành 5 / 5 câu', 'lesson can complete');
assert(micStatus.textContent === 'Mic bật', 'mic remains enabled after lesson completion');
assert(activeRecognitionCount() === 0, 'recognition stops while completion banner is shown');

btnAutoRead.click();
lessonSelect.value = 'a1-greetings';
lessonSelect.dispatchEvent({ type: 'change' });
await tick();
assert(spoken.at(-1) === 'Hello.', 'next lesson still auto-plays after completing previous lesson');
await finishSampleAndAssertMicResumes('new lesson after completion');

const history = JSON.parse(localStorage.getItem('reading-aloud-history'));
assert(Array.isArray(history), 'history is stored as an array');
assert(history.length > 0, 'history has study sessions');

const skippedSession = history.find((session) => session.manualSkipCount > 0);
assert(skippedSession, 'history records manual sentence skips');
assert(skippedSession.manualSkippedSentences.length > 0, 'history stores skipped sentence details');
assert(skippedSession.manualSkippedSentences[0].matchedWordCount < skippedSession.manualSkippedSentences[0].totalWordCount, 'skip detail captures incomplete progress');

const completedStudySession = history.find((session) => session.lessonId === 'a1-colors-numbers');
assert(completedStudySession?.percentComplete === 100, 'history records completed lesson percent');
assert(completedStudySession.completedSentenceCount === completedStudySession.totalSentenceCount, 'history records completed sentence count');

const incompleteSession = history.find((session) =>
  session.sentences?.some((sentence) => sentence.missingWords?.length),
);
assert(incompleteSession, 'history keeps missing words for review');

console.log('microphoneFlow tests: ok');
