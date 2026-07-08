import {
  analyze,
  backtest,
  deleteSetup,
  getCandles,
  getConfig,
  getSetups,
  saveSetup,
  updateSetup,
} from './api.js';
import { TradeChart } from './chart.js';

/** @typedef {'idle' | 'new' | 'edit'} EditorMode */

const state = {
  period: 'train',
  mode: /** @type {EditorMode} */ ('idle'),
  direction: 'long',
  step: 'entry',
  draft: { entry: null, sl: null, tp: null, time: null },
  editingId: null,
  setups: [],
  config: null,
};

const els = {
  periodTabs: document.getElementById('periodTabs'),
  periodBadge: document.getElementById('periodBadge'),
  editorPanel: document.getElementById('editorPanel'),
  modePill: document.getElementById('modePill'),
  rrPill: document.getElementById('rrPill'),
  labelHint: document.getElementById('labelHint'),
  idleBlock: document.getElementById('idleBlock'),
  activeBlock: document.getElementById('activeBlock'),
  newSteps: document.getElementById('newSteps'),
  setupList: document.getElementById('setupList'),
  setupCount: document.getElementById('setupCount'),
  fieldEntry: document.getElementById('fieldEntry'),
  fieldSL: document.getElementById('fieldSL'),
  fieldTP: document.getElementById('fieldTP'),
  fieldTime: document.getElementById('fieldTime'),
  fieldNote: document.getElementById('fieldNote'),
  fieldTags: document.getElementById('fieldTags'),
  tagPresets: document.getElementById('tagPresets'),
  notePresets: document.getElementById('notePresets'),
  btnSave: document.getElementById('btnSave'),
  btnDelete: document.getElementById('btnDelete'),
  chartOverlayHint: document.getElementById('chartOverlayHint'),
  analysisOut: document.getElementById('analysisOut'),
  backtestOut: document.getElementById('backtestOut'),
};

const chart = new TradeChart(
  document.getElementById('chartMain'),
  document.getElementById('chartRsi'),
  { onClick: handleChartClick, onLevelDrag: handleLevelDrag },
);

const MODE_LABELS = { idle: 'Xem chart', new: 'Tạo mới', edit: 'Chỉnh sửa' };

const STEP_HINTS = {
  entry: 'Bước 1 — Click trên chart để đặt điểm Entry',
  sl: 'Bước 2 — Click hoặc kéo đường đỏ để đặt Stop Loss',
  tp: 'Bước 3 — Click hoặc kéo đường xanh lá để đặt Take Profit',
};

function isoFromUnix(sec) {
  return new Date(sec * 1000).toISOString();
}

function isTrainPeriod() {
  return state.period === 'train';
}

function parseTagsFromField() {
  return els.fieldTags.value
    .split(/[,;]+/)
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
}

function setTagsToField(tags) {
  els.fieldTags.value = [...new Set(tags.map((t) => t.trim().toLowerCase()).filter(Boolean))].join(', ');
  syncTagChips();
}

function syncTagChips() {
  const active = new Set(parseTagsFromField());
  els.tagPresets?.querySelectorAll('.chip[data-tag]').forEach((chip) => {
    chip.classList.toggle('active', active.has(chip.dataset.tag));
  });
}

function toggleTag(tagId) {
  const tags = new Set(parseTagsFromField());
  tags.has(tagId) ? tags.delete(tagId) : tags.add(tagId);
  setTagsToField([...tags]);
}

function applyNotePreset(note) {
  els.fieldNote.value = note.text;
  if (note.tags?.length) {
    setTagsToField([...new Set([...parseTagsFromField(), ...note.tags])]);
  }
}

function renderPresets() {
  const presets = state.config?.presets;
  if (!presets) return;
  els.tagPresets.innerHTML = '';
  for (const tag of presets.tags || []) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chip';
    btn.dataset.tag = tag.id;
    btn.title = tag.hint || tag.label;
    btn.textContent = tag.label;
    btn.onclick = () => toggleTag(tag.id);
    els.tagPresets.appendChild(btn);
  }
  els.notePresets.innerHTML = '';
  for (const note of presets.notes || []) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chip';
    btn.textContent = note.text;
    btn.onclick = () => applyNotePreset(note);
    els.notePresets.appendChild(btn);
  }
  syncTagChips();
}

function calcRR() {
  const entry = state.draft.entry;
  const sl = Number(els.fieldSL.value);
  const tp = Number(els.fieldTP.value);
  if (!entry || !sl || !tp) return null;
  const risk = Math.abs(entry - sl);
  const reward = Math.abs(tp - entry);
  return risk > 0 ? (reward / risk).toFixed(2) : null;
}

function updateRR() {
  const rr = calcRR();
  els.rrPill.textContent = rr ? `RR ${rr}` : 'RR —';
}

function setDirection(direction) {
  state.direction = direction;
  document.querySelectorAll('.dir-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.direction === direction);
  });
}

function updateStepTrack() {
  const order = ['entry', 'sl', 'tp'];
  const currentIdx = order.indexOf(state.step);
  els.newSteps.querySelectorAll('.step-item').forEach((el) => {
    const step = el.dataset.step;
    const idx = order.indexOf(step);
    el.classList.remove('active', 'done');
    if (state.mode !== 'new') return;
    if (idx < currentIdx) el.classList.add('done');
    else if (idx === currentIdx) el.classList.add('active');
  });
}

function updateChartHint() {
  if (state.mode === 'new' && isTrainPeriod()) {
    els.chartOverlayHint.textContent = STEP_HINTS[state.step] || '';
    els.chartOverlayHint.classList.remove('hidden');
    return;
  }
  if (state.mode === 'edit') {
    els.chartOverlayHint.textContent = 'Kéo đường Entry / SL / TP để chỉnh — bấm Cập nhật khi xong';
    els.chartOverlayHint.classList.remove('hidden');
    return;
  }
  els.chartOverlayHint.classList.add('hidden');
}

function updateModeUI() {
  const { mode } = state;
  els.editorPanel.dataset.mode = mode;
  els.modePill.dataset.mode = mode;
  els.modePill.textContent = MODE_LABELS[mode];

  const editing = mode !== 'idle';
  els.idleBlock.classList.toggle('hidden', editing);
  els.activeBlock.classList.toggle('hidden', !editing);
  els.newSteps.classList.toggle('hidden', mode !== 'new');
  els.btnDelete.classList.toggle('hidden', mode !== 'edit');

  els.btnSave.textContent = mode === 'edit' ? 'Cập nhật setup' : 'Lưu setup';

  if (mode === 'idle') {
    els.labelHint.textContent = isTrainPeriod()
      ? 'Chọn setup trong thư viện để sửa, hoặc bấm 「Setup mới」.'
      : 'Tab này chỉ xem dữ liệu. Chuyển về Train 2022 để đánh dấu setup.';
  } else if (mode === 'new') {
    els.labelHint.textContent = 'Đặt Entry → SL → TP trên chart. Có thể kéo đường để tinh chỉnh.';
  } else {
    els.labelHint.textContent = 'Setup đang mở — chart đã focus. Kéo đường hoặc sửa số bên dưới.';
  }

  updateStepTrack();
  updateChartHint();
  updateRR();
}

function clearDraft() {
  state.draft = { entry: null, sl: null, tp: null, time: null };
  state.editingId = null;
  state.step = 'entry';
  els.fieldTags.value = '';
  els.fieldNote.value = '';
  syncTagChips();
  chart.clearOverlay();
  chart.clearFocus();
}

function setMode(mode) {
  state.mode = mode;
  if (mode === 'idle') {
    clearDraft();
    els.btnSave.disabled = true;
  }
  updateModeUI();
  renderSetups();
}

async function ensureTrainPeriod() {
  if (state.period === 'train') return;
  state.period = 'train';
  els.periodBadge.textContent = state.config.periods.train.label;
  renderPeriodTabs();
  await loadChart();
}

function focusAndDraw() {
  if (state.draft.entry == null || state.draft.time == null) return;
  chart.focusSetup({
    time: state.draft.time,
    entry: state.draft.entry,
    sl: Number(els.fieldSL.value) || state.draft.sl,
    tp: Number(els.fieldTP.value) || state.draft.tp,
  });
  chart.setOverlay({
    entry: state.draft.entry,
    sl: Number(els.fieldSL.value) || state.draft.sl,
    tp: Number(els.fieldTP.value) || state.draft.tp,
    direction: state.direction,
  });
}

function syncFields() {
  els.fieldEntry.value = state.draft.entry ?? '';
  els.fieldSL.value = state.draft.sl ?? '';
  els.fieldTP.value = state.draft.tp ?? '';
  els.fieldTime.value = state.draft.time ? isoFromUnix(state.draft.time) : '';
  if (state.mode !== 'idle') {
    requestAnimationFrame(() => focusAndDraw());
  }
  validateSave();
  updateRR();
  updateStepTrack();
  updateChartHint();
}

function validateSave() {
  if (state.mode === 'idle' || !isTrainPeriod()) {
    els.btnSave.disabled = true;
    return;
  }
  const sl = Number(els.fieldSL.value);
  const tp = Number(els.fieldTP.value);
  const ok =
    state.draft.entry != null &&
    state.draft.time != null &&
    !Number.isNaN(sl) &&
    !Number.isNaN(tp) &&
    sl > 0 &&
    tp > 0;

  let valid = false;
  if (ok && state.direction === 'long') {
    valid = sl < state.draft.entry && tp > state.draft.entry;
  } else if (ok && state.direction === 'short') {
    valid = sl > state.draft.entry && tp < state.draft.entry;
  }
  els.btnSave.disabled = !valid;
}

function handleLevelDrag({ role, price }) {
  if (state.mode === 'idle' || !isTrainPeriod()) return;
  if (role === 'entry') {
    state.draft.entry = price;
    els.fieldEntry.value = price;
  } else if (role === 'sl') {
    state.draft.sl = price;
    els.fieldSL.value = price;
  } else if (role === 'tp') {
    state.draft.tp = price;
    els.fieldTP.value = price;
  }
  if (state.mode === 'new' && state.step === 'entry' && role !== 'entry') {
    /* allow drag after placed */
  }
  focusAndDraw();
  validateSave();
  updateRR();
}

function handleChartClick({ time, candle, price }) {
  if (state.mode !== 'new' || !isTrainPeriod()) return;

  if (state.step === 'entry') {
    state.draft.time = time;
    state.draft.entry = candle.close;
    state.step = 'sl';
    const defaultSl =
      state.direction === 'long' ? candle.close - 0.003 : candle.close + 0.003;
    state.draft.sl = Number(defaultSl.toFixed(5));
    els.fieldSL.value = state.draft.sl;
    const risk = Math.abs(state.draft.entry - state.draft.sl);
    state.draft.tp = Number(
      (state.direction === 'long'
        ? state.draft.entry + risk * 2
        : state.draft.entry - risk * 2
      ).toFixed(5),
    );
    els.fieldTP.value = state.draft.tp;
    state.step = 'tp';
    syncFields();
    return;
  }

  if (state.step === 'sl') {
    state.draft.sl = Number(price.toFixed(5));
    els.fieldSL.value = state.draft.sl;
    const risk = Math.abs(state.draft.entry - state.draft.sl);
    state.draft.tp = Number(
      (state.direction === 'long'
        ? state.draft.entry + risk * 2
        : state.draft.entry - risk * 2
      ).toFixed(5),
    );
    els.fieldTP.value = state.draft.tp;
    state.step = 'tp';
    syncFields();
    return;
  }

  if (state.step === 'tp') {
    state.draft.tp = Number(price.toFixed(5));
    els.fieldTP.value = state.draft.tp;
    syncFields();
  }
}

async function startNewSetup() {
  await ensureTrainPeriod();
  clearDraft();
  state.mode = 'new';
  state.step = 'entry';
  setDirection('long');
  updateModeUI();
  syncFields();
}

async function startEditSetup(setup) {
  await ensureTrainPeriod();

  state.mode = 'edit';
  state.editingId = setup.id;
  state.direction = setup.direction;
  state.step = 'tp';
  state.draft = {
    time: Math.floor(new Date(setup.entry_time).getTime() / 1000),
    entry: Number(setup.entry_price),
    sl: Number(setup.stop_loss),
    tp: Number(setup.take_profit),
  };

  setDirection(setup.direction);
  els.fieldTags.value = (setup.tags || []).join(', ');
  els.fieldNote.value = setup.note || '';
  syncTagChips();
  updateModeUI();
  syncFields();
  requestAnimationFrame(() => focusAndDraw());
}

function cancelEditor() {
  setMode('idle');
}

function renderPeriodTabs() {
  els.periodTabs.innerHTML = '';
  for (const [key, cfg] of Object.entries(state.config.periods)) {
    const btn = document.createElement('button');
    btn.className = `period-tab${key === state.period ? ' active' : ''}${key === 'test' ? ' test' : ''}`;
    btn.textContent = cfg.label;
    btn.onclick = () => switchPeriod(key);
    els.periodTabs.appendChild(btn);
  }
}

async function switchPeriod(period) {
  if (state.mode !== 'idle') cancelEditor();
  state.period = period;
  els.periodBadge.textContent = state.config.periods[period].label;
  renderPeriodTabs();
  updateModeUI();
  await loadChart();
}

async function loadChart() {
  const data = await getCandles(state.period);
  chart.setData(data);
  if (state.mode !== 'idle') {
    requestAnimationFrame(() => focusAndDraw());
  }
}

function renderSetups() {
  const trainSetups = state.setups.filter((s) => (s.period || 'train') === 'train');
  els.setupCount.textContent = String(trainSetups.length);
  els.setupList.innerHTML = '';

  if (!trainSetups.length) {
    els.setupList.innerHTML =
      '<li class="hint" style="padding:8px">Chưa có setup. Bấm 「Setup mới」 để bắt đầu.</li>';
    return;
  }

  const sorted = [...trainSetups].sort((a, b) => a.entry_time.localeCompare(b.entry_time));
  for (const s of sorted) {
    const li = document.createElement('li');
    li.className = `setup-item ${s.direction}${s.id === state.editingId ? ' selected' : ''}`;
    const resClass = s.result === 'win' ? 'win' : s.result === 'loss' ? 'loss' : '';
    li.innerHTML = `
      <div class="setup-top">
        <span class="setup-dir">${s.direction.toUpperCase()}</span>
        <span class="setup-result ${resClass}">${(s.result || '?').toUpperCase()}</span>
        <span style="margin-left:auto;font-size:11px;color:#fbbf24">RR ${s.planned_rr ?? '—'}</span>
      </div>
      <div class="setup-meta">${s.entry_time?.slice(0, 16).replace('T', ' ')}${(s.tags || []).length ? '<br>' + s.tags.join(' · ') : ''}</div>
    `;
    li.onclick = () => startEditSetup(s);
    els.setupList.appendChild(li);
  }
}

async function refreshSetups() {
  const { setups } = await getSetups();
  state.setups = setups;
  renderSetups();
}

function buildSetupBody() {
  return {
    direction: state.direction,
    entry_time: isoFromUnix(state.draft.time),
    entry_price: state.draft.entry,
    stop_loss: Number(els.fieldSL.value),
    take_profit: Number(els.fieldTP.value),
    note: els.fieldNote.value,
    tags: parseTagsFromField(),
  };
}

async function onSave() {
  const body = buildSetupBody();
  if (state.mode === 'edit' && state.editingId) {
    await updateSetup(state.editingId, body);
  } else {
    await saveSetup(body);
  }
  await refreshSetups();
  setMode('idle');
}

async function onDelete() {
  if (!state.editingId) return;
  if (!confirm('Xóa setup này?')) return;
  await deleteSetup(state.editingId);
  await refreshSetups();
  setMode('idle');
}

function bindUI() {
  document.getElementById('btnNewSetup').onclick = () => startNewSetup();
  document.getElementById('btnNewFromIdle').onclick = () => startNewSetup();
  document.getElementById('btnCancel').onclick = () => cancelEditor();
  document.getElementById('btnDelete').onclick = () => onDelete();
  document.getElementById('btnSave').onclick = () => onSave();

  document.getElementById('btnLong').onclick = () => {
    setDirection('long');
    if (state.mode === 'new') {
      clearDraft();
      state.mode = 'new';
      state.step = 'entry';
      syncFields();
    } else if (state.mode === 'edit') syncFields();
  };
  document.getElementById('btnShort').onclick = () => {
    setDirection('short');
    if (state.mode === 'new') {
      clearDraft();
      state.mode = 'new';
      state.step = 'entry';
      syncFields();
    } else if (state.mode === 'edit') syncFields();
  };

  els.fieldSL.oninput = () => {
    state.draft.sl = Number(els.fieldSL.value);
    syncFields();
  };
  els.fieldTP.oninput = () => {
    state.draft.tp = Number(els.fieldTP.value);
    syncFields();
  };
  els.fieldTags.oninput = () => syncTagChips();

  document.getElementById('toggleEma50').onchange = (e) => chart.toggleEma50(e.target.checked);
  document.getElementById('toggleEma200').onchange = (e) => chart.toggleEma200(e.target.checked);
  document.getElementById('toggleRsi').onchange = (e) => chart.toggleRsi(e.target.checked);

  document.getElementById('btnAnalyze').onclick = async () => {
    els.analysisOut.textContent = 'Đang phân tích...';
    try {
      els.analysisOut.textContent = JSON.stringify(await analyze(), null, 2);
    } catch (e) {
      els.analysisOut.textContent = e.message;
    }
  };
  document.getElementById('btnBacktestVal').onclick = () => runBt('validation');
  document.getElementById('btnBacktestTest').onclick = () => runBt('test');
}

async function runBt(period) {
  els.backtestOut.textContent = `Backtest ${period}...`;
  try {
    els.backtestOut.textContent = JSON.stringify(await backtest(period), null, 2);
  } catch (e) {
    els.backtestOut.textContent = e.message;
  }
}

async function boot() {
  bindUI();
  chart.mount();
  state.config = await getConfig();
  renderPeriodTabs();
  renderPresets();
  setMode('idle');
  await loadChart();
  await refreshSetups();
}

boot().catch((err) => {
  document.body.innerHTML = `<pre style="color:#f87171;padding:20px">Boot failed: ${err.message}</pre>`;
});
