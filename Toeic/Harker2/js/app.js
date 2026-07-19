const state = {
  mode: null,       // 'exam' | 'study'
  testId: null,
  testData: null,
  currentPart: 1,
  currentQ: 1,
  answers: {},      // { questionId: 'A' }
  submitted: false,
  timerInterval: null,
  timeLeft: 45 * 60,
  studyToggles: { transcript: true, answer: true, accent: true },
};

const PART_RANGES = {
  1: { start: 1, end: 6, count: 6 },
  2: { start: 7, end: 31, count: 25 },
  3: { start: 32, end: 70, count: 39 },
  4: { start: 71, end: 100, count: 30 },
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function init() {
  const index = await fetch('public/data/index.json').then(r => r.json());
  renderTestGrid(index);
  bindHomeEvents();
  bindPracticeEvents();
}

function renderTestGrid(tests) {
  const grid = $('#test-grid');
  grid.innerHTML = tests.map(t => `
    <button class="test-btn ready" data-test="${t.id}" disabled>
      ${t.title}
    </button>
  `).join('');
}

function bindHomeEvents() {
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
    const testId = parseInt(btn.dataset.test);
    await startPractice(testId);
  });
}

async function startPractice(testId) {
  state.testId = testId;
  state.answers = {};
  state.submitted = false;
  state.currentPart = 1;
  state.currentQ = 1;
  state.timeLeft = 45 * 60;

  const file = `public/data/test${String(testId).padStart(2, '0')}.json`;
  state.testData = await fetch(file).then(r => r.json());

  $('#practice-test-name').textContent = state.testData.title;
  const badge = $('#practice-mode-badge');
  badge.textContent = state.mode === 'exam' ? 'Thi' : 'Học';
  badge.className = 'badge' + (state.mode === 'exam' ? ' badge--exam' : '');

  const layout = $('.practice-layout');
  const studyPanel = $('#study-panel');
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

  const audio = $('#audio-player');
  audio.src = `public/${state.testData.audio}`;

  showScreen('practice');
  renderPart(1);
  renderQuestionNav();
  renderCurrentQuestion();
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

  $$('.part-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const part = parseInt(tab.dataset.part);
      state.currentPart = part;
      state.currentQ = PART_RANGES[part].start;
      $$('.part-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      renderQuestionNav();
      renderCurrentQuestion();
    });
  });

  $('#question-nav').addEventListener('click', (e) => {
    const btn = e.target.closest('.q-nav-btn');
    if (!btn) return;
    state.currentQ = parseInt(btn.dataset.q);
    renderQuestionNav();
    renderCurrentQuestion();
  });

  ['transcript', 'answer', 'accent'].forEach(key => {
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
  const range = PART_RANGES[state.currentPart];
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
  if (qId <= 6) return d.parts['1'].questions.some(q => q.id === qId);
  if (qId <= 31) return d.parts['2'].questions.some(q => q.id === qId);
  if (qId <= 70) {
    return d.parts['3'].passages.some(p => p.questionIds.includes(qId));
  }
  return d.parts['4'].passages.some(p => p.questionIds.includes(qId));
}

function getCorrectAnswer(qId) {
  return state.testData.answers[String(qId)] || '';
}

function getQuestionData(qId) {
  const d = state.testData;
  if (qId <= 6) {
    return { type: 'single', data: d.parts['1'].questions.find(q => q.id === qId), part: 1 };
  }
  if (qId <= 31) {
    return { type: 'single', data: d.parts['2'].questions.find(q => q.id === qId), part: 2 };
  }
  if (qId <= 70) {
    const passage = d.parts['3'].passages.find(p => p.questionIds.includes(qId));
    const q = passage?.questions?.find(q => q.id === qId);
    return { type: 'passage', passage, data: q, part: 3 };
  }
  const passage = d.parts['4'].passages.find(p => p.questionIds.includes(qId));
  const q = passage?.questions?.find(q => q.id === qId);
  return { type: 'passage', passage, data: q, part: 4 };
}

function renderCurrentQuestion() {
  const area = $('#question-area');
  const qId = state.currentQ;
  const { type, data, passage, part } = getQuestionData(qId);

  if (!data) {
    area.innerHTML = `<div class="question-card"><p>Câu ${qId} — dữ liệu chưa có.</p></div>`;
    renderStudyPanel();
    return;
  }

  if (type === 'passage') {
    area.innerHTML = renderPassageGroup(passage, part) + renderNavButtons(qId, part);
    bindOptionClicks(area);
    bindNavButtons(area);
    renderStudyPanel();
    return;
  }

  let html = `<div class="question-card">`;
  html += `<div class="q-header">
    <span class="q-number">Câu ${qId}</span>
    <span class="q-part-label">Part ${part}</span>
  </div>`;

  if (part === 1) {
    const imgPath = `public/images/test${String(state.testId).padStart(2, '0')}/q${String(qId).padStart(2, '0')}.png`;
    html += `<div class="q-image">
      <img src="${imgPath}" alt="Question ${qId}" onerror="this.parentElement.innerHTML='<div class=\\'q-image-placeholder\\'>Ảnh câu ${qId} — đang cập nhật</div>'">
    </div>`;
    html += `<p class="q-prompt">Chọn câu mô tả đúng nhất bức tranh.</p>`;
    html += renderOptions(data.options, qId);
  } else if (part === 2) {
    html += `<p class="q-prompt">${esc(data.question)}</p>`;
    html += `<p style="font-size:.85rem;color:var(--text-muted);margin-bottom:1rem">Chọn câu trả lời phù hợp nhất.</p>`;
    html += renderOptions(data.options, qId);
  }

  html += renderNavButtons(qId, part);
  html += `</div>`;
  area.innerHTML = html;
  bindOptionClicks(area);
  bindNavButtons(area);
  renderStudyPanel();
}

function renderNavButtons(qId, part) {
  const range = PART_RANGES[part];
  return `<div class="q-nav-row">
    <button class="btn-secondary btn-nav" data-dir="prev" ${qId <= range.start ? 'disabled' : ''}>← Câu trước</button>
    <button class="btn-secondary btn-nav" data-dir="next" ${qId >= range.end ? 'disabled' : ''}>Câu sau →</button>
  </div>`;
}

function bindNavButtons(container) {
  container.querySelectorAll('.btn-nav').forEach(btn => {
    btn.addEventListener('click', () => {
      const dir = btn.dataset.dir === 'prev' ? -1 : 1;
      let next = state.currentQ + dir;
      while (next >= 1 && next <= 100 && !questionExists(next)) next += dir;
      if (questionExists(next)) {
        state.currentQ = next;
        const part = next <= 6 ? 1 : next <= 31 ? 2 : next <= 70 ? 3 : 4;
        if (part !== state.currentPart) renderPart(part);
        renderQuestionNav();
        renderCurrentQuestion();
      }
    });
  });
}

function renderPassageGroup(passage, part) {
  if (!passage) return '<div class="question-card"><p>Không tìm thấy đoạn hội thoại.</p></div>';

  const showTranscript = state.mode === 'study' && state.studyToggles.transcript;
  const firstQ = passage.questionIds[0];

  let html = `<div class="question-card">`;
  html += `<div class="q-header">
    <span class="q-number">Câu ${passage.questionIds.join(' – ')}</span>
    <span class="q-part-label">Part ${part}</span>
  </div>`;

  if (showTranscript) {
    html += `<div class="passage-block">${esc(passage.transcript)}</div>`;
  } else if (state.mode === 'exam') {
    html += `<p style="font-size:.85rem;color:var(--text-muted);margin-bottom:1rem">Nghe đoạn hội thoại / bài nói và trả lời các câu hỏi.</p>`;
  }

  html += `<div class="sub-questions">`;
  for (const q of (passage.questions || [])) {
    const isActive = q.id === state.currentQ;
    html += `<div class="sub-question" id="subq-${q.id}" style="${isActive ? '' : 'opacity:.55'}">`;
    html += `<div class="q-header" style="margin-bottom:.75rem">
      <span class="q-number">Câu ${q.id}</span>
    </div>`;
    if (q.question) html += `<p class="q-prompt">${esc(q.question)}</p>`;
    html += renderOptions(q.options, q.id);
    html += `</div>`;
  }
  html += `</div></div>`;
  return html;
}

function renderOptions(options, qId) {
  const letters = Object.keys(options).sort();
  const selected = state.answers[qId];
  const correct = getCorrectAnswer(qId);
  const showResult = state.submitted || (state.mode === 'study' && state.studyToggles.answer);

  return `<div class="options-list">${letters.map(letter => {
    let cls = 'option-btn';
    if (selected === letter) cls += ' selected';
    if (showResult && letter === correct) cls += ' correct';
    if (showResult && selected === letter && letter !== correct) cls += ' wrong';
    const disabled = state.submitted || (state.mode === 'study' && state.studyToggles.answer);
    return `<button class="${cls}" data-q="${qId}" data-letter="${letter}" ${disabled ? 'disabled' : ''}>
      <span class="option-letter">${letter}</span>
      <span>${esc(options[letter])}</span>
    </button>`;
  }).join('')}</div>`;
}

function bindOptionClicks(container) {
  container.querySelectorAll('.option-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      const qId = parseInt(btn.dataset.q);
      const letter = btn.dataset.letter;
      state.answers[qId] = letter;
      state.currentQ = qId;
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
  if (!data) { panel.innerHTML = ''; return; }

  let html = '';

  if (state.studyToggles.accent) {
    const accent = part <= 2 ? data.accent : passage?.accent;
    if (accent) {
      html += `<div class="study-section">
        <h4>Giải thích — Accent / Phát âm</h4>
        <span class="accent-tag">🎙 ${esc(accent)}</span>
        <p style="margin-top:.6rem;font-size:.8rem;color:var(--text-muted)">
          Câu hỏi sử dụng giọng ${esc(accent)}. Luyện nghe kỹ sự khác biệt phát âm giữa các vùng.
        </p>
      </div>`;
    }
  }

  if (state.studyToggles.transcript) {
    html += `<div class="study-section"><h4>Transcript</h4>`;
    if (part === 1) {
      html += `<pre>${formatPart1Transcript(data)}</pre>`;
    } else if (part === 2) {
      html += `<pre><strong>Câu hỏi:</strong> ${esc(data.question)}
${formatOptionsTranscript(data.options)}</pre>`;
    } else if (passage) {
      html += `<pre>${esc(passage.transcript)}</pre>`;
    }
    html += `</div>`;

    html += `<div class="study-section">
      <h4>Dịch tiếng Việt</h4>
      <div class="translation-note">
        Bản dịch tiếng Việt sẽ được bổ sung trong phiên bản tiếp theo.
        Hiện tại hãy sử dụng transcript tiếng Anh kèm từ điển để tra nghĩa.
      </div>
    </div>`;
  }

  if (state.studyToggles.answer) {
    const answer = getCorrectAnswer(qId);
    html += `<div class="study-section">
      <h4>Đáp án đúng</h4>
      <div class="answer-reveal">✓ ${answer}</div>
    </div>`;

    if (part <= 2 && data.options?.[answer]) {
      html += `<div class="study-section">
        <h4>Giải thích</h4>
        <p>Đáp án <strong>${answer}</strong>: "${esc(data.options[answer])}"</p>
      </div>`;
    } else if (data?.options?.[answer]) {
      html += `<div class="study-section">
        <h4>Giải thích câu ${qId}</h4>
        <p>Đáp án <strong>${answer}</strong>: "${esc(data.options[answer])}"</p>
      </div>`;
    }
  }

  panel.innerHTML = html;
}

function formatPart1Transcript(q) {
  if (!q?.options) return '';
  return Object.entries(q.options).map(([k, v]) => `(${k}) ${v}`).join('\n');
}

function formatOptionsTranscript(opts) {
  return Object.entries(opts).map(([k, v]) => `(${k}) ${v}`).join('\n');
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
    if (state.timeLeft <= 0) {
      stopTimer();
      submitExam();
    }
  }, 1000);
}

function stopTimer() {
  if (state.timerInterval) {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
  }
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

  let correct = 0;
  const breakdown = { 1: { c: 0, t: 0 }, 2: { c: 0, t: 0 }, 3: { c: 0, t: 0 }, 4: { c: 0, t: 0 } };

  for (let q = 1; q <= 100; q++) {
    if (!questionExists(q)) continue;
    const part = q <= 6 ? 1 : q <= 31 ? 2 : q <= 70 ? 3 : 4;
    breakdown[part].t++;
    if (state.answers[q] === getCorrectAnswer(q)) {
      correct++;
      breakdown[part].c++;
    }
  }

  $('#score-value').textContent = correct;
  $('#score-breakdown').innerHTML = [1, 2, 3, 4].map(p => `
    <div class="score-part">
      Part ${p}
      <strong>${breakdown[p].c} / ${breakdown[p].t}</strong>
    </div>
  `).join('');

  $('#modal-results').classList.remove('hidden');
  renderQuestionNav();
  renderCurrentQuestion();
}

init();
