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
import {
  renderAnalyzeView,
  renderBacktestView,
  renderError,
  renderLoading,
} from './strategy-ui.js';
import { initSidebarResize } from './layout.js';
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
  sidebarTab: 'label',
  btCache: { validation: null, test: null },
  focusedTradeKey: null,
  focusedSetupId: null,
};

const els = {
  periodTabs: document.getElementById('periodTabs'),
  periodBadge: document.getElementById('periodBadge'),
  editorPanel: document.getElementById('editorPanel'),
  modePill: document.getElementById('modePill'),
  rrPill: document.getElementById('rrPill'),
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
  analyzeResults: document.getElementById('analyzeResults'),
  btValResults: document.getElementById('btValResults'),
  btTestResults: document.getElementById('btTestResults'),
  btValTradeList: document.getElementById('btValTradeList'),
  btTestTradeList: document.getElementById('btTestTradeList'),
  btValCount: document.getElementById('btValCount'),
  btTestCount: document.getElementById('btTestCount'),
  sidebarTabs: document.querySelectorAll('.sidebar-tab'),
  sidebarViews: {
    label: document.getElementById('viewLabel'),
    analyze: document.getElementById('viewAnalyze'),
    validation: document.getElementById('viewValidation'),
    test: document.getElementById('viewTest'),
  },
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

const SIDEBAR_PERIOD = {
  label: 'train',
  analyze: 'train',
  validation: 'validation',
  test: 'test',
};

const PERIOD_SIDEBAR = {
  train: 'label',
  validation: 'validation',
  test: 'test',
};

function trainSetups() {
  return state.setups.filter((s) => (s.period || 'train') === 'train');
}

function tradeKey(trade) {
  return `${trade.entry_time}|${trade.direction}|${trade.entry}`;
}

function refreshChartAnnotations() {
  if (state.mode !== 'idle') return;

  if (state.period === 'train') {
    if (state.focusedSetupId) return;
    chart.showSetupMarkers(trainSetups());
    return;
  }

  if (state.period === 'validation' || state.period === 'test') {
    if (state.focusedTradeKey) return;
    const trades = state.btCache[state.period]?.trades || [];
    chart.showTradeMarkers(trades);
  }
}

function isTrainPeriod() {
  return state.period === 'train';
}

function clearChartFocus() {
  state.focusedTradeKey = null;
  state.focusedSetupId = null;
  chart.clearOverlay();
  chart.clearFocus();
  refreshChartAnnotations();
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
  if (state.focusedSetupId || state.focusedTradeKey) {
    els.chartOverlayHint.textContent = 'Click setup/lệnh khác trong danh sách — hoặc scroll chart để xem tất cả marker';
    els.chartOverlayHint.classList.remove('hidden');
    return;
  }
  if (state.period === 'validation' || state.period === 'test') {
    const n = state.btCache[state.period]?.trades?.length || 0;
    if (n > 0) {
      els.chartOverlayHint.textContent = `${n} lệnh backtest trên chart — chọn lệnh trong danh sách bên trái`;
      els.chartOverlayHint.classList.remove('hidden');
      return;
    }
  }
  if (state.period === 'train' && trainSetups().length > 0 && state.mode === 'idle') {
    els.chartOverlayHint.textContent = `${trainSetups().length} setup trên chart — click xem · double-click sửa`;
    els.chartOverlayHint.classList.remove('hidden');
    return;
  }
  els.chartOverlayHint.classList.add('hidden');
}

function updateModeUI() {
  const { mode } = state;
  els.editorPanel.dataset.mode = mode;
  els.editorPanel.classList.toggle('hidden', mode === 'idle');
  els.modePill.dataset.mode = mode;
  els.modePill.textContent = MODE_LABELS[mode];

  els.newSteps.classList.toggle('hidden', mode !== 'new');
  els.btnDelete.classList.toggle('hidden', mode !== 'edit');

  els.btnSave.textContent = mode === 'edit' ? 'Cập nhật setup' : 'Lưu setup';

  updateStepTrack();
  updateChartHint();
  updateRR();
}

function overlayPayload() {
  if (state.draft.entry == null || state.draft.time == null) return null;
  return {
    time: state.draft.time,
    entry: state.draft.entry,
    sl: Number(els.fieldSL.value) || state.draft.sl,
    tp: Number(els.fieldTP.value) || state.draft.tp,
    direction: state.direction,
  };
}

function drawOverlayOnly() {
  const payload = overlayPayload();
  if (!payload) return;
  if (chart.hasOverlay()) {
    chart.updateLevelPrices(payload);
  } else {
    chart.setOverlay({ ...payload, interactive: true });
  }
}

function focusChartOnSetup() {
  const payload = overlayPayload();
  if (!payload) return;
  chart.focusSetup(payload);
  chart.setOverlay({ ...payload, interactive: true });
}

function syncFields({ focus = false } = {}) {
  els.fieldEntry.value = state.draft.entry ?? '';
  els.fieldSL.value = state.draft.sl ?? '';
  els.fieldTP.value = state.draft.tp ?? '';
  els.fieldTime.value = state.draft.time ? isoFromUnix(state.draft.time) : '';
  if (state.mode !== 'idle') {
    if (focus) focusChartOnSetup();
    else drawOverlayOnly();
  }
  validateSave();
  updateRR();
  updateStepTrack();
  updateChartHint();
}

function clearDraft() {
  state.draft = { entry: null, sl: null, tp: null, time: null };
  state.editingId = null;
  state.step = 'entry';
  state.focusedSetupId = null;
  state.focusedTradeKey = null;
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
    refreshChartAnnotations();
  }
  updateModeUI();
  renderSetups();
  renderBtTradeLists();
}

async function ensureTrainPeriod() {
  if (state.period === 'train') return;
  state.period = 'train';
  els.periodBadge.textContent = state.config.periods.train.label;
  renderPeriodTabs();
  await loadChart();
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
  validateSave();
  updateRR();
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
    syncFields({ focus: true });
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
  switchSidebarTab('label', { syncPeriod: false });
  clearDraft();
  state.mode = 'new';
  state.step = 'entry';
  setDirection('long');
  updateModeUI();
  syncFields();
}

async function startEditSetup(setup) {
  await ensureTrainPeriod();
  switchSidebarTab('label', { syncPeriod: false });

  state.focusedTradeKey = null;
  state.focusedSetupId = setup.id;
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
  syncFields({ focus: true });
  renderSetups();
}

function cancelEditor() {
  setMode('idle');
}

function renderPeriodTabs() {
  els.periodTabs.innerHTML = '';
  for (const [key, cfg] of Object.entries(state.config.periods)) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `period-tab${key === state.period ? ' active' : ''}${key === 'test' ? ' test' : ''}`;
    btn.title = cfg.label;
    const short = { train: '2022', validation: '2023', test: '2024–26' }[key] || key;
    btn.innerHTML = `<span class="period-year">${short}</span><span class="period-name">${key === 'train' ? 'Train' : key === 'validation' ? 'Val' : 'Test'}</span>`;
    btn.onclick = () => switchPeriod(key);
    els.periodTabs.appendChild(btn);
  }
}

async function switchPeriod(period, { syncSidebar = true } = {}) {
  if (state.mode !== 'idle') cancelEditor();
  state.period = period;
  state.focusedTradeKey = null;
  state.focusedSetupId = null;
  els.periodBadge.textContent = state.config.periods[period].label;
  renderPeriodTabs();
  if (syncSidebar && state.sidebarTab !== 'analyze') {
    const tab = PERIOD_SIDEBAR[period];
    if (tab) setSidebarTabUI(tab);
  }
  updateModeUI();
  await loadChart();
}

async function loadChart() {
  const data = await getCandles(state.period);
  chart.setData(data);
  if (state.mode !== 'idle' && state.draft.time) {
    drawOverlayOnly();
  } else {
    refreshChartAnnotations();
  }
}

function renderSetups() {
  const items = trainSetups();
  els.setupCount.textContent = String(items.length);
  els.setupList.innerHTML = '';

  if (!items.length) {
    els.setupList.innerHTML =
      '<li class="hint" style="padding:8px">Chưa có setup. Bấm 「Setup mới」 để bắt đầu.</li>';
    return;
  }

  const sorted = [...items].sort((a, b) => a.entry_time.localeCompare(b.entry_time));
  for (const s of sorted) {
    const li = document.createElement('li');
    const selected = s.id === state.editingId || s.id === state.focusedSetupId;
    li.className = `setup-item ${s.direction}${selected ? ' selected' : ''}`;
    const resClass = s.result === 'win' ? 'win' : s.result === 'loss' ? 'loss' : '';
    li.innerHTML = `
      <div class="setup-top">
        <span class="setup-dir">${s.direction.toUpperCase()}</span>
        <span class="setup-result ${resClass}">${(s.result || '?').toUpperCase()}</span>
        <span style="margin-left:auto;font-size:11px;color:#fbbf24">RR ${s.planned_rr ?? '—'}</span>
      </div>
      <div class="setup-meta">${s.entry_time?.slice(0, 16).replace('T', ' ')}${(s.tags || []).length ? '<br>' + s.tags.join(' · ') : ''}</div>
    `;
    li.onclick = () => viewSetupOnChart(s);
    li.ondblclick = (e) => {
      e.preventDefault();
      startEditSetup(s);
    };
    els.setupList.appendChild(li);
  }
}

function viewSetupOnChart(setup) {
  state.focusedSetupId = setup.id;
  state.focusedTradeKey = null;
  chart.viewSetup(setup, { interactive: false });
  renderSetups();
  updateChartHint();
}

function viewTradeOnChart(period, trade) {
  if (state.period !== period) return;
  state.focusedTradeKey = tradeKey(trade);
  state.focusedSetupId = null;
  chart.viewTrade(trade);
  renderBtTradeLists();
  els.chartOverlayHint.textContent = `Lệnh ${trade.direction.toUpperCase()} — ${trade.result.toUpperCase()} · ${trade.pnl_pips} pips`;
  els.chartOverlayHint.classList.remove('hidden');
}

function renderBtTradeList(period) {
  const isVal = period === 'validation';
  const listEl = isVal ? els.btValTradeList : els.btTestTradeList;
  const countEl = isVal ? els.btValCount : els.btTestCount;
  const data = state.btCache[period];
  const trades = data?.trades || [];

  countEl.textContent = String(trades.length);
  listEl.innerHTML = '';

  if (!trades.length) {
    listEl.innerHTML =
      '<li class="hint" style="padding:8px">Chưa có lệnh. Chạy backtest để xem lệnh trên chart.</li>';
    return;
  }

  const sorted = [...trades].sort((a, b) => a.entry_time.localeCompare(b.entry_time));
  for (const t of sorted) {
    const li = document.createElement('li');
    const key = tradeKey(t);
    const win = t.result === 'win';
    li.className = `setup-item ${t.direction}${state.focusedTradeKey === key ? ' selected' : ''}`;
    li.innerHTML = `
      <div class="setup-top">
        <span class="setup-dir">${t.direction.toUpperCase()}</span>
        <span class="setup-result ${win ? 'win' : 'loss'}">${t.result.toUpperCase()}</span>
        <span style="margin-left:auto;font-size:11px;color:${win ? '#86efac' : '#fca5a5'}">${t.pnl_pips} pips</span>
      </div>
      <div class="setup-meta">${t.entry_time?.slice(0, 16).replace('T', ' ')} · Entry ${t.entry}</div>
    `;
    li.onclick = () => viewTradeOnChart(period, t);
    listEl.appendChild(li);
  }
}

function renderBtTradeLists() {
  renderBtTradeList('validation');
  renderBtTradeList('test');
}

async function refreshSetups() {
  const { setups } = await getSetups();
  state.setups = setups;
  renderSetups();
  if (state.mode === 'idle' && state.period === 'train' && !state.focusedSetupId) {
    refreshChartAnnotations();
  }
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

function setSidebarTabUI(tabId) {
  state.sidebarTab = tabId;
  els.sidebarTabs.forEach((btn) => {
    const active = btn.dataset.sidebar === tabId;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  for (const [key, view] of Object.entries(els.sidebarViews)) {
    view.classList.toggle('hidden', key !== tabId);
    view.classList.toggle('active', key === tabId);
  }
}

function switchSidebarTab(tabId, { syncPeriod = true } = {}) {
  if (state.mode !== 'idle' && tabId !== 'label') {
    cancelEditor();
  }
  setSidebarTabUI(tabId);
  if (!syncPeriod) {
    refreshChartAnnotations();
    return;
  }
  const period = SIDEBAR_PERIOD[tabId];
  if (period && state.period !== period) {
    switchPeriod(period, { syncSidebar: false });
  } else {
    refreshChartAnnotations();
  }
}

async function runAnalyze() {
  els.analyzeResults.innerHTML = renderLoading('Đang phân tích setup train...');
  try {
    const data = await analyze();
    els.analyzeResults.innerHTML = renderAnalyzeView(data);
  } catch (e) {
    els.analyzeResults.innerHTML = renderError(e.message);
  }
}

async function runBt(period) {
  const isVal = period === 'validation';
  const outEl = isVal ? els.btValResults : els.btTestResults;
  const label = isVal ? 'Validation 2023' : 'Test 2024–2026';
  outEl.innerHTML = renderLoading(`Đang chạy backtest ${label}...`);
  try {
    const data = await backtest(period);
    state.btCache[period] = data;
    outEl.innerHTML = renderBacktestView(data, {
      title: isVal ? 'Backtest 2023' : 'Backtest 2024–26',
      subtitle: isVal
        ? 'Dùng để tinh chỉnh chiến lược trước khi test out-of-sample.'
        : 'Kết quả out-of-sample — không nên optimize thêm sau bước này.',
    });
    state.focusedTradeKey = null;
    renderBtTradeLists();
    if (state.period === period) {
      refreshChartAnnotations();
    }
  } catch (e) {
    outEl.innerHTML = renderError(e.message);
  }
}

function bindUI() {
  document.getElementById('btnNewSetup').onclick = () => startNewSetup();
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
    } else if (state.mode === 'edit') {
      const payload = overlayPayload();
      if (payload) chart.setOverlay({ ...payload, interactive: true });
    }
  };
  document.getElementById('btnShort').onclick = () => {
    setDirection('short');
    if (state.mode === 'new') {
      clearDraft();
      state.mode = 'new';
      state.step = 'entry';
      syncFields();
    } else if (state.mode === 'edit') {
      const payload = overlayPayload();
      if (payload) chart.setOverlay({ ...payload, interactive: true });
    }
  };

  els.fieldSL.oninput = () => {
    state.draft.sl = Number(els.fieldSL.value);
    drawOverlayOnly();
    validateSave();
    updateRR();
  };
  els.fieldTP.oninput = () => {
    state.draft.tp = Number(els.fieldTP.value);
    drawOverlayOnly();
    validateSave();
    updateRR();
  };
  els.fieldTags.oninput = () => syncTagChips();

  document.getElementById('toggleEma50').onchange = (e) => chart.toggleEma50(e.target.checked);
  document.getElementById('toggleEma200').onchange = (e) => chart.toggleEma200(e.target.checked);
  document.getElementById('toggleRsi').onchange = (e) => chart.toggleRsi(e.target.checked);

  els.sidebarTabs.forEach((btn) => {
    btn.onclick = () => switchSidebarTab(btn.dataset.sidebar);
  });

  document.getElementById('btnAnalyze').onclick = () => runAnalyze();
  document.getElementById('btnBacktestVal').onclick = () => runBt('validation');
  document.getElementById('btnBacktestTest').onclick = () => runBt('test');
}

async function boot() {
  bindUI();
  chart.mount();
  initSidebarResize({
    layoutEl: document.getElementById('layout'),
    sidebarEl: document.getElementById('sidebar'),
    resizerEl: document.getElementById('sidebarResizer'),
    onResize: () => chart.resize?.(),
  });
  state.config = await getConfig();
  renderPeriodTabs();
  renderPresets();
  setMode('idle');
  await loadChart();
  await refreshSetups();
  refreshChartAnnotations();
}

boot().catch((err) => {
  document.body.innerHTML = `<pre style="color:#f87171;padding:20px">Boot failed: ${err.message}</pre>`;
});
