const SECTIONS = {
  listening: {
    label: 'Listening',
    dataPath: (id) => `public/data/test${String(id).padStart(2, '0')}.json`,
    timerSec: 45 * 60,
    maxQ: 100,
    parts: {
      1: { start: 1, end: 6, label: 'Part 1', count: '6 câu' },
      2: { start: 7, end: 31, label: 'Part 2', count: '25 câu' },
      3: { start: 32, end: 70, label: 'Part 3', count: '39 câu' },
      4: { start: 71, end: 100, label: 'Part 4', count: '30 câu' },
    },
    hasAudio: true,
    hasAccent: true,
  },
  reading: {
    label: 'Reading',
    dataPath: (id) => `public/data/reading/test${String(id).padStart(2, '0')}.json`,
    timerSec: 75 * 60,
    maxQ: 200,
    parts: {
      5: { start: 101, end: 130, label: 'Part 5', count: '30 câu' },
      6: { start: 131, end: 146, label: 'Part 6', count: '16 câu' },
      7: { start: 147, end: 200, label: 'Part 7', count: '54 câu' },
    },
    hasAudio: false,
    hasAccent: false,
  },
};

const state = {
  section: 'listening',
  mode: null,
  testId: null,
  testData: null,
  currentPart: null,
  currentQ: null,
  answers: {},
  submitted: false,
  timerInterval: null,
  timeLeft: 45 * 60,
  studyToggles: { transcript: true, translation: true, answer: true, accent: true },
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function cfg() { return SECTIONS[state.section]; }
function partRanges() { return cfg().parts; }

async function init() {
  bindHomeEvents();
  bindPracticeEvents();
  await loadTestGrid();
}

async function loadTestGrid() {
  const indexPath = state.section === 'reading'
    ? 'public/data/reading/index.json'
    : 'public/data/index.json';
  const index = await fetch(indexPath).then(r => r.json());
  renderTestGrid(index);
}

function renderTestGrid(tests) {
  const grid = $('#test-grid');
  grid.innerHTML = tests.map(t => `
    <button class="test-btn ready" data-test="${t.id}" ${state.mode ? '' : 'disabled'}>
      ${t.title}
    </button>
  `).join('');
}

function bindHomeEvents() {
  $$('.section-tab').forEach(tab => {
    tab.addEventListener('click', async () => {
      $$('.section-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.section = tab.dataset.section;
      await loadTestGrid();
    });
  });

  $$('.mode-card').forEach(card => {
    card.addEventListener('click', () => {
      $$('.mode-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      state.mode = card.dataset.mode;
      $$('.test-btn').forEach(btn => btn.disabled = false);
    });
  });

  $('#test-grid').addEventListener('click', async (e) => {
    const btn = e.target.closest('.test-btn');
    if (!btn || !state.mode) return;
    await startPractice(parseInt(btn.dataset.test));
  });
}

async function startPractice(testId) {
  const c = cfg();
  state.testId = testId;
  state.answers = {};
  state.submitted = false;
  state.timeLeft = c.timerSec;
  const firstPart = parseInt(Object.keys(c.parts)[0]);
  state.currentPart = firstPart;
  state.currentQ = c.parts[firstPart].start;

  state.testData = await fetch(c.dataPath(testId)).then(r => r.json());

  $('#practice-test-name').textContent = `${state.testData.title} · ${c.label}`;
  const badge = $('#practice-mode-badge');
  badge.textContent = state.mode === 'exam' ? 'Thi' : 'Học';
  badge.className = 'badge' + (state.mode === 'exam' ? ' badge--exam' : '');

  const layout = $('.practice-layout');
  const studyPanel = $('#study-panel');
  const accentWrap = $('#toggle-accent-wrap');
  if (state.mode === 'study') {
    layout.classList.add('study-mode');
    studyPanel.classList.remove('hidden');
  } else {
    layout.classList.remove('study-mode');
    studyPanel.classList.add('hidden');
    startTimer();
    $('#exam-timer').classList.remove('hidden');
    $('#exam-submit-panel').classList.remove('hidden');
  }

  const audioPanel = $('#audio-panel');
  if (c.hasAudio) {
    audioPanel.classList.remove('hidden');
    $('#audio-player').src = `public/${state.testData.audio}`;
  } else {
    audioPanel.classList.add('hidden');
  }

  accentWrap.classList.toggle('hidden', !c.hasAccent);
  renderPartNav();
  showScreen('practice');
  renderPart(state.currentPart);
  renderQuestionNav();
  renderCurrentQuestion();
}

function renderPartNav() {
  const nav = $('#part-nav');
  const parts = partRanges();
  nav.innerHTML = Object.entries(parts).map(([num, p]) => `
    <button class="part-tab${parseInt(num) === state.currentPart ? ' active' : ''}" data-part="${num}">
      ${p.label} <small>${p.count}</small>
    </button>
  `).join('');
}

function showScreen(name) {
  $$('.screen').forEach(s => s.classList.remove('active'));
  $(`#screen-${name}`).classList.add('active');
}

function bindPracticeEvents() {
  $('#btn-back').addEventListener('click', () => {
    stopTimer();
    showScreen('home');
  });

  $('#part-nav').addEventListener('click', (e) => {
    const tab = e.target.closest('.part-tab');
    if (!tab) return;
    const part = parseInt(tab.dataset.part);
    state.currentPart = part;
    state.currentQ = partRanges()[part].start;
    renderPartNav();
    renderPart(part);
    renderQuestionNav();
    renderCurrentQuestion();
  });

  $('#question-nav').addEventListener('click', (e) => {
    const btn = e.target.closest('.q-nav-btn');
    if (!btn) return;
    state.currentQ = parseInt(btn.dataset.q);
    renderQuestionNav();
    renderCurrentQuestion();
  });

  ['transcript', 'translation', 'answer', 'accent'].forEach(key => {
    $(`#toggle-${key}`).addEventListener('change', (e) => {
      state.studyToggles[key] = e.target.checked;
      renderStudyPanel();
    });
  });

  $('#btn-submit-exam').addEventListener('click', submitExam);
  $('#btn-close-results').addEventListener('click', () => $('#modal-results').classList.add('hidden'));
  $('#btn-review').addEventListener('click', () => {
    $('#modal-results').classList.add('hidden');
    state.submitted = true;
    renderCurrentQuestion();
    renderQuestionNav();
  });
}

function renderPart(part) {
  state.currentPart = part;
  $$('.part-tab').forEach(t => {
    t.classList.toggle('active', parseInt(t.dataset.part) === part);
  });
}

function renderQuestionNav() {
  const range = partRanges()[state.currentPart];
  const nav = $('#question-nav');
  nav.innerHTML = '';
  for (let q = range.start; q <= range.end; q++) {
    if (!questionExists(q)) continue;
    const btn = document.createElement('button');
    btn.className = 'q-nav-btn';
    btn.dataset.q = q;
    btn.textContent = q;
    if (q === state.currentQ) btn.classList.add('active');
    if (state.answers[q]) btn.classList.add('answered');
    if (state.submitted) {
      const correct = getCorrectAnswer(q);
      if (state.answers[q] === correct) btn.classList.add('correct');
      else if (state.answers[q]) btn.classList.add('wrong');
    }
    nav.appendChild(btn);
  }
}

function questionExists(qId) {
  const d = state.testData;
  if (state.section === 'reading') {
    if (qId <= 130) return d.parts['5'].questions.some(q => q.id === qId);
    if (qId <= 146) return d.parts['6'].passages.some(p => p.questionIds.includes(qId));
    return d.parts['7'].passages.some(p => p.questionIds.includes(qId));
  }
  if (qId <= 6) return d.parts['1'].questions.some(q => q.id === qId);
  if (qId <= 31) return d.parts['2'].questions.some(q => q.id === qId);
  if (qId <= 70) return d.parts['3'].passages.some(p => p.questionIds.includes(qId));
  return d.parts['4'].passages.some(p => p.questionIds.includes(qId));
}

function getCorrectAnswer(qId) {
  return state.testData.answers[String(qId)] || '';
}

function getPartForQ(qId) {
  if (state.section === 'reading') {
    if (qId <= 130) return 5;
    if (qId <= 146) return 6;
    return 7;
  }
  if (qId <= 6) return 1;
  if (qId <= 31) return 2;
  if (qId <= 70) return 3;
  return 4;
}

function getQuestionData(qId) {
  const d = state.testData;
  if (state.section === 'reading') {
    if (qId <= 130) {
      return { type: 'single', data: d.parts['5'].questions.find(q => q.id === qId), part: 5 };
    }
    const partKey = qId <= 146 ? '6' : '7';
    const passage = d.parts[partKey].passages.find(p => p.questionIds.includes(qId));
    const q = passage?.questions?.find(q => q.id === qId);
    return { type: 'passage', passage, data: q, part: parseInt(partKey) };
  }
  if (qId <= 6) return { type: 'single', data: d.parts['1'].questions.find(q => q.id === qId), part: 1 };
  if (qId <= 31) return { type: 'single', data: d.parts['2'].questions.find(q => q.id === qId), part: 2 };
  if (qId <= 70) {
    const passage = d.parts['3'].passages.find(p => p.questionIds.includes(qId));
    return { type: 'passage', passage, data: passage?.questions?.find(q => q.id === qId), part: 3 };
  }
  const passage = d.parts['4'].passages.find(p => p.questionIds.includes(qId));
  return { type: 'passage', passage, data: passage?.questions?.find(q => q.id === qId), part: 4 };
}

function renderCurrentQuestion() {
  const area = $('#question-area');
  const qId = state.currentQ;
  const { type, data, passage, part } = getQuestionData(qId);

  if (!data && type === 'passage') {
    area.innerHTML = renderReadingPassageGroup(passage, part) + renderNavButtons(qId, part);
    bindOptionClicks(area);
    bindNavButtons(area);
    renderStudyPanel();
    return;
  }

  if (!data) {
    area.innerHTML = `<div class="question-card"><p>Câu ${qId} — dữ liệu chưa có.</p>${renderNavButtons(qId, part)}</div>`;
    bindNavButtons(area);
    renderStudyPanel();
    return;
  }

  if (type === 'passage') {
    const html = state.section === 'reading'
      ? renderReadingPassageGroup(passage, part)
      : renderListeningPassageGroup(passage, part);
    area.innerHTML = html + renderNavButtons(qId, part);
    bindOptionClicks(area);
    bindNavButtons(area);
    renderStudyPanel();
    return;
  }

  let html = `<div class="question-card">`;
  html += `<div class="q-header"><span class="q-number">Câu ${qId}</span><span class="q-part-label">Part ${part}</span></div>`;

  if (part === 1) {
    const imgPath = `public/images/test${String(state.testId).padStart(2, '0')}/q${String(qId).padStart(2, '0')}.png`;
    html += `<div class="q-image"><img src="${imgPath}" alt="Q${qId}" onerror="this.parentElement.innerHTML='<div class=\\'q-image-placeholder\\'>Ảnh câu ${qId}</div>'"></div>`;
    html += `<p class="q-prompt">Chọn câu mô tả đúng nhất bức tranh.</p>`;
    html += renderOptions(data.options, qId);
  } else if (part === 2) {
    html += `<p class="q-prompt">${esc(data.question)}</p>`;
    html += renderOptions(data.options, qId);
  } else if (part === 5) {
    html += `<p class="q-prompt sentence-block">${highlightBlank(data.sentence)}</p>`;
    html += `<p class="exam-hint">Chọn từ/cụm từ phù hợp nhất điền vào chỗ trống.</p>`;
    html += renderOptions(data.options, qId);
  }

  html += renderNavButtons(qId, part) + `</div>`;
  area.innerHTML = html;
  bindOptionClicks(area);
  bindNavButtons(area);
  renderStudyPanel();
}

function highlightBlank(sentence) {
  return esc(sentence).replace(/(\s{2,}|_{2,})/g, ' <span class="blank">______</span> ');
}

function renderReadingPassageGroup(passage, part) {
  if (!passage) return '<div class="question-card"><p>Không tìm thấy đoạn văn.</p></div>';
  const qId = state.currentQ;
  const currentQ = (passage.questions || []).find(q => q.id === qId);
  const showPassage = state.mode === 'study' && state.studyToggles.transcript;

  let html = `<div class="question-card">`;
  html += `<div class="q-header"><span class="q-number">Câu ${qId}</span><span class="q-part-label">Part ${part} · ${passage.type || 'text'}</span></div>`;

  if (showPassage && passage.passage) {
    html += `<div class="passage-block passage-block--reading">${esc(passage.passage)}</div>`;
  } else if (state.mode === 'exam') {
    html += `<p class="exam-hint">Đọc đoạn văn và trả lời câu hỏi.</p>`;
  }

  if (currentQ) {
    if (part === 7 && currentQ.question) {
      html += `<p class="q-prompt">${esc(currentQ.question)}</p>`;
    } else if (part === 6) {
      html += `<p class="q-prompt">Chọn đáp án phù hợp cho vị trí <strong>${qId}</strong> trong đoạn văn.</p>`;
    }
    html += renderOptions(currentQ.options || {}, qId);
  } else {
    html += `<p class="q-prompt q-prompt--missing">Câu ${qId} — đang cập nhật.</p>`;
  }
  html += `</div>`;
  return html;
}

function renderListeningPassageGroup(passage, part) {
  if (!passage) return '<div class="question-card"><p>Không tìm thấy đoạn hội thoại.</p></div>';
  const qId = state.currentQ;
  const currentQ = (passage.questions || []).find(q => q.id === qId);
  const showTranscript = state.mode === 'study' && state.studyToggles.transcript;

  let html = `<div class="question-card">`;
  html += `<div class="q-header"><span class="q-number">Câu ${qId}</span><span class="q-part-label">Part ${part} · Nhóm ${passage.questionIds.join('–')}</span></div>`;

  if (showTranscript) {
    html += `<div class="passage-block">${formatTranscript(passage.transcript)}</div>`;
  } else if (state.mode === 'exam') {
    html += `<p class="exam-hint">Nghe đoạn hội thoại / bài nói và trả lời câu hỏi.</p>`;
  }

  if (state.mode === 'study' && state.studyToggles.translation && passage.translation) {
    html += `<div class="passage-block passage-block--vi">${esc(passage.translation)}</div>`;
  }

  if (currentQ) {
    if (currentQ.question) html += `<p class="q-prompt">${esc(currentQ.question)}</p>`;
    html += renderOptions(currentQ.options || {}, qId);
  }
  html += `</div>`;
  return html;
}

function renderNavButtons(qId, part) {
  const range = partRanges()[part];
  return `<div class="q-nav-row">
    <button class="btn-secondary btn-nav" data-dir="prev" ${qId <= range.start ? 'disabled' : ''}>← Câu trước</button>
    <button class="btn-secondary btn-nav" data-dir="next" ${qId >= range.end ? 'disabled' : ''}>Câu sau →</button>
  </div>`;
}

function bindNavButtons(container) {
  container.querySelectorAll('.btn-nav').forEach(btn => {
    btn.addEventListener('click', () => {
      const dir = btn.dataset.dir === 'prev' ? -1 : 1;
      const maxQ = cfg().maxQ;
      let next = state.currentQ + dir;
      while (next >= 1 && next <= maxQ && !questionExists(next)) next += dir;
      if (questionExists(next)) {
        state.currentQ = next;
        const part = getPartForQ(next);
        if (part !== state.currentPart) { state.currentPart = part; renderPartNav(); renderPart(part); }
        renderQuestionNav();
        renderCurrentQuestion();
      }
    });
  });
}

function formatTranscript(text) {
  if (!text) return '';
  return esc(text).replace(/^(W\d?):/gm, '<strong>$1:</strong>').replace(/^(M):/gm, '<strong>M:</strong>');
}

function renderOptions(options, qId) {
  const letters = Object.keys(options).sort();
  const selected = state.answers[qId];
  const correct = getCorrectAnswer(qId);
  const showResult = state.submitted || (state.mode === 'study' && state.studyToggles.answer);
  const disabled = state.submitted || (state.mode === 'study' && state.studyToggles.answer);

  return `<div class="options-list">${letters.map(letter => {
    let cls = 'option-btn';
    if (selected === letter) cls += ' selected';
    if (showResult && letter === correct) cls += ' correct';
    if (showResult && selected === letter && letter !== correct) cls += ' wrong';
    return `<button class="${cls}" data-q="${qId}" data-letter="${letter}" ${disabled ? 'disabled' : ''}>
      <span class="option-letter">${letter}</span><span>${esc(options[letter])}</span>
    </button>`;
  }).join('')}</div>`;
}

function bindOptionClicks(container) {
  container.querySelectorAll('.option-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      state.answers[parseInt(btn.dataset.q)] = btn.dataset.letter;
      state.currentQ = parseInt(btn.dataset.q);
      renderQuestionNav();
      renderCurrentQuestion();
    });
  });
}

function renderStudyPanel() {
  if (state.mode !== 'study') return;
  const panel = $('#study-content');
  const qId = state.currentQ;
  const { data, passage, part } = getQuestionData(qId);
  let html = '';

  if (cfg().hasAccent && state.studyToggles.accent) {
    const accent = part <= 2 ? data?.accent : passage?.accent;
    if (accent) {
      html += `<div class="study-section"><h4>Giải thích — Accent</h4><span class="accent-tag">🎙 ${esc(accent)}</span></div>`;
    }
  }

  if (state.studyToggles.transcript) {
    html += `<div class="study-section"><h4>${state.section === 'reading' ? 'Đoạn văn' : 'Transcript'}</h4>`;
    if (part === 5 && data?.sentence) {
      html += `<pre>${esc(data.sentence)}</pre>`;
    } else if (part <= 2 && data) {
      html += `<pre>${part === 1 ? formatPart1Transcript(data) : esc(data.question)}</pre>`;
    } else if (passage) {
      const text = passage.passage || passage.transcript || '';
      html += `<pre>${esc(text)}</pre>`;
    }
    html += `</div>`;
  }

  if (state.studyToggles.translation && passage?.translation) {
    html += `<div class="study-section"><h4>Dịch tiếng Việt</h4><pre class="translation-text">${esc(passage.translation)}</pre></div>`;
  } else if (state.studyToggles.translation && data?.translation) {
    html += `<div class="study-section"><h4>Dịch tiếng Việt</h4><pre class="translation-text">${esc(data.translation)}</pre></div>`;
  }

  if (state.studyToggles.answer) {
    const answer = getCorrectAnswer(qId);
    html += `<div class="study-section"><h4>Đáp án đúng</h4><div class="answer-reveal">✓ ${answer}</div></div>`;
    if (data?.options?.[answer]) {
      html += `<div class="study-section"><h4>Giải thích</h4><p>Đáp án <strong>${answer}</strong>: "${esc(data.options[answer])}"</p></div>`;
    }
  }

  panel.innerHTML = html || '<p class="translation-note">Chọn câu hỏi để xem chi tiết.</p>';
}

function formatPart1Transcript(q) {
  return Object.entries(q.options || {}).map(([k, v]) => `(${k}) ${v}`).join('\n');
}

function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function startTimer() {
  stopTimer();
  updateTimerDisplay();
  state.timerInterval = setInterval(() => {
    state.timeLeft--;
    updateTimerDisplay();
    if (state.timeLeft <= 0) { stopTimer(); submitExam(); }
  }, 1000);
}

function stopTimer() {
  if (state.timerInterval) { clearInterval(state.timerInterval); state.timerInterval = null; }
  $('#exam-timer').classList.add('hidden');
  $('#exam-submit-panel').classList.add('hidden');
}

function updateTimerDisplay() {
  const m = Math.floor(state.timeLeft / 60);
  const s = state.timeLeft % 60;
  const el = $('#timer-display');
  el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  el.classList.toggle('warning', state.timeLeft < 300);
}

function submitExam() {
  stopTimer();
  state.submitted = true;
  const c = cfg();
  let correct = 0;
  const breakdown = {};
  Object.keys(c.parts).forEach(p => { breakdown[p] = { c: 0, t: 0 }; });

  for (let q = 1; q <= c.maxQ; q++) {
    if (!questionExists(q)) continue;
    const part = getPartForQ(q);
    breakdown[part].t++;
    if (state.answers[q] === getCorrectAnswer(q)) { correct++; breakdown[part].c++; }
  }

  $('#score-value').textContent = correct;
  $('.score-total').textContent = `/ ${c.maxQ}`;
  $('#score-breakdown').innerHTML = Object.entries(c.parts).map(([p, info]) => `
    <div class="score-part">${info.label}<strong>${breakdown[p]?.c || 0} / ${breakdown[p]?.t || 0}</strong></div>
  `).join('');

  $('#modal-results').classList.remove('hidden');
  renderQuestionNav();
  renderCurrentQuestion();
}

init();
