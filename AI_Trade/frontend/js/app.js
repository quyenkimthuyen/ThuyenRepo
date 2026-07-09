import {
  analyze,
  backtest,
  deleteSetup,
  getCandles,
  getConfig,
  getPresets,
  getSetups,
  saveSetup,
  suggestTags,
  updateSetup,
} from './api.js?v=9';
import {
  renderAnalyzeView,
  renderBacktestView,
  renderError,
  renderLoading,
} from './strategy-ui.js?v=9';
import { initSidebarResize } from './layout.js?v=9';
import { TradeChart } from './chart.js?v=9';

/** @typedef {'idle' | 'new' | 'edit'} EditorMode */

const state = {
  period: 'train',
  mode: /** @type {EditorMode} */ ('idle'),
  direction: 'long',
  step: 'entry',
  draft: { entry: null, sl: null, tp: null, time: null },
  meta: { tags: [], note: '' },
  editingId: null,
  setups: [],
  config: null,
  tagPresets: [],
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
  tagCheckboxGroup: document.getElementById('tagCheckboxGroup'),
  tagSuggestPanel: document.getElementById('tagSuggestPanel'),
  tagSuggestTags: document.getElementById('tagSuggestTags'),
  tagSuggestSimilar: document.getElementById('tagSuggestSimilar'),
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

const DEFAULT_TAGS = [
  { id: 'pullback', label: 'Pullback', hint: 'Hồi về EMA / support' },
  { id: 'breakout', label: 'Breakout', hint: 'Phá vỡ vùng sideway' },
  { id: 'retest', label: 'Retest', hint: 'Retest vùng phá vỡ' },
  { id: 'rejection', label: 'Rejection', hint: 'Pin bar / từ chối giá' },
  { id: 'reversal', label: 'Reversal', hint: 'Đảo chiều cấu trúc' },
  { id: 'trend', label: 'Trend', hint: 'Theo xu hướng chính' },
  { id: 'range', label: 'Range', hint: 'Giao dịch trong vùng đi ngang' },
  { id: 'liquidity', label: 'Liquidity', hint: 'Quét thanh khoản / sweep' },
];

const STEP_HINTS = {
  entry: 'Bước 1 — Click trên chart để đặt điểm Entry',
  sl: 'Bước 2 — Click hoặc kéo đường đỏ để đặt Stop Loss',
  tp: 'Bước 3 — Click hoặc kéo đường xanh lá để đặt Take Profit',
};

function isoFromUnix(sec) {
  return new Date(sec * 1000).toISOString();
}

function datetimeLocalFromUnix(sec) {
  return new Date(sec * 1000).toISOString().slice(0, 16);
}

function unixFromDatetimeLocal(value) {
  if (!value) return null;
  const normalized = value.length === 16 ? `${value}:00Z` : `${value}Z`;
  const ms = Date.parse(normalized);
  return Number.isNaN(ms) ? null : Math.floor(ms / 1000);
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

function tagPresetList() {
  if (state.tagPresets?.length) return state.tagPresets;
  if (state.config?.presets?.tags?.length) return state.config.presets.tags;
  return DEFAULT_TAGS;
}

function renderTagCheckboxes() {
  const group = els.tagCheckboxGroup;
  if (!group) return;

  const presets = tagPresetList();
  group.innerHTML = '';
  for (const tag of presets) {
    const label = document.createElement('label');
    label.className = 'tag-check';
    label.title = tag.hint || '';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = tag.id;
    input.dataset.tagId = tag.id;
    input.onchange = () => onTagChange();
    label.appendChild(input);
    label.appendChild(document.createTextNode(tag.label));
    group.appendChild(label);
  }
  syncTagField();
}

function selectedTags() {
  if (!els.tagCheckboxGroup) return [];
  return [...els.tagCheckboxGroup.querySelectorAll('input[type="checkbox"]:checked')].map(
    (el) => el.value,
  );
}

function setSelectedTags(tags, { userEdited = false } = {}) {
  const wanted = new Set(tags || []);
  els.tagCheckboxGroup?.querySelectorAll('input[type="checkbox"]').forEach((el) => {
    el.checked = wanted.has(el.value);
    el.dataset.auto = userEdited ? '0' : el.checked ? '1' : '0';
  });
  state.meta.tags = [...wanted];
  if (wanted.size) {
    const labels = tagPresetList()
      .filter((t) => wanted.has(t.id))
      .map((t) => t.label);
    state.meta.note = labels.join(' + ');
  } else {
    state.meta.note = '';
  }
  validateSave();
}

function syncTagField() {
  const wanted = new Set(state.meta.tags || []);
  els.tagCheckboxGroup?.querySelectorAll('input[type="checkbox"]').forEach((el) => {
    el.checked = wanted.has(el.value);
  });
}

function onTagChange() {
  const tags = selectedTags();
  state.meta.tags = tags;
  if (tags.length) {
    const labels = tagPresetList()
      .filter((t) => tags.includes(t.id))
      .map((t) => t.label);
    state.meta.note = labels.join(' + ');
  } else {
    state.meta.note = '';
  }
  els.tagCheckboxGroup?.querySelectorAll('input[type="checkbox"]').forEach((el) => {
    if (el.checked) el.dataset.auto = '0';
  });
  validateSave();
}

function renderTagSuggest(data) {
  if (!els.tagSuggestPanel) return;
  if (!data) {
    els.tagSuggestPanel.classList.add('hidden');
    return;
  }

  els.tagSuggestPanel.classList.remove('hidden');
  const detected = data.detected_tags || [];
  els.tagSuggestTags.innerHTML = detected.length
    ? detected
        .map(
          (item) =>
            `<span class="pill suggest">${item.tag} ${Math.round(item.score * 100)}%</span>`,
        )
        .join(' ')
    : '<span class="muted">Chưa nhận diện tag rõ — chọn thủ công</span>';

  const similar = data.similar_setups || [];
  els.tagSuggestSimilar.innerHTML = similar.length
    ? similar
        .map((item) => {
          const time = (item.entry_time || '').slice(0, 10);
          const tags = (item.tags || []).join(', ');
          return `<li>${Math.round(item.similarity * 100)}% · ${item.direction?.toUpperCase()} · ${item.result?.toUpperCase()} · ${time}${tags ? ` · ${tags}` : ''}</li>`;
        })
        .join('')
    : '<li class="muted">Chưa có setup tương tự trong train</li>';
}

async function refreshTagSuggest({ applyTags = true } = {}) {
  if (state.draft.time == null || state.draft.entry == null) return;
  try {
    const data = await suggestTags({
      entry_time: isoFromUnix(state.draft.time),
      entry_price: Number(state.draft.entry),
    });
    renderTagSuggest(data);
    if (applyTags && data?.suggested_tags?.length) {
      const manual = selectedTags().filter((tag) => {
        const el = els.tagCheckboxGroup?.querySelector(`input[value="${tag}"]`);
        return el && el.dataset.auto !== '1';
      });
      const merged = [...new Set([...(data.suggested_tags || []), ...manual])];
      setSelectedTags(merged, { userEdited: false });
      els.tagCheckboxGroup?.querySelectorAll('input[type="checkbox"]').forEach((el) => {
        if (el.checked && (data.suggested_tags || []).includes(el.value)) {
          el.dataset.auto = '1';
        }
      });
    }
    if (data?.suggested_direction && state.mode === 'new' && state.step !== 'entry') {
      setDirection(data.suggested_direction);
    }
  } catch (err) {
    console.warn('Tag suggest failed:', err);
    renderTagSuggest(null);
  }
}

function hideTagSuggest() {
  renderTagSuggest(null);
}

async function loadTagPresets() {
  try {
    const data = await getPresets();
    if (data?.tags?.length) {
      state.tagPresets = data.tags;
      renderTagCheckboxes();
      return;
    }
  } catch {
    /* fallback below */
  }
  state.tagPresets = state.config?.presets?.tags?.length
    ? state.config.presets.tags
    : DEFAULT_TAGS;
  renderTagCheckboxes();
}

function escapeAttr(value) {
  if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
    return CSS.escape(String(value));
  }
  return String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function calcRR() {
  const entry = Number(state.draft.entry);
  const sl = Number(els.fieldSL.value);
  const tp = Number(els.fieldTP.value);
  if (!Number.isFinite(entry) || !Number.isFinite(sl) || !Number.isFinite(tp)) return null;
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
    els.chartOverlayHint.textContent = 'Click chart để đổi Entry/time, hoặc kéo Entry / SL / TP — bấm Cập nhật khi xong';
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

  if (mode !== 'idle') {
    renderTagCheckboxes();
  }

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
  els.fieldTime.value = state.draft.time ? datetimeLocalFromUnix(state.draft.time) : '';
  syncTagField();
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
  state.meta = { tags: [], note: '' };
  state.editingId = null;
  state.step = 'entry';
  state.focusedSetupId = null;
  state.focusedTradeKey = null;
  chart.clearOverlay();
  chart.clearFocus();
  hideTagSuggest();
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
  if (state.config?.periods?.train) {
    els.periodBadge.textContent = state.config.periods.train.label;
  }
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
  const entry = Number(state.draft.entry);
  const ok =
    Number.isFinite(entry) &&
    state.draft.time != null &&
    Number.isFinite(sl) &&
    Number.isFinite(tp) &&
    entry > 0 &&
    sl > 0 &&
    tp > 0;

  let valid = false;
  const hasTag = (state.meta.tags?.length ?? 0) > 0;
  if (ok && state.direction === 'long') {
    valid = sl < entry && tp > entry && hasTag;
  } else if (ok && state.direction === 'short') {
    valid = sl > entry && tp < entry && hasTag;
  }
  els.btnSave.disabled = !valid;
}

function moveDraftEntryToCandle({ time, candle }) {
  const nextEntry = Number(candle.close);

  state.draft.time = time;
  state.draft.entry = nextEntry;
  syncFields({ focus: true });
  refreshTagSuggest({ applyTags: state.mode === 'new' });
}

function handleChartClick({ time, candle, price }) {
  if (!isTrainPeriod()) return;

  if (state.mode === 'edit') {
    moveDraftEntryToCandle({ time, candle });
    return;
  }

  if (state.mode !== 'new') return;

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
    refreshTagSuggest();
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
  state.meta = {
    tags: setup.tags || [],
    note: setup.note || '',
  };
  updateModeUI();
  syncFields({ focus: true });
  refreshTagSuggest({ applyTags: false });
  renderSetups();
}

function cancelEditor() {
  setMode('idle');
}

function renderPeriodTabs() {
  if (!state.config?.periods) return;
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
  if (state.config?.periods?.[period]) {
    els.periodBadge.textContent = state.config.periods[period].label;
  }
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
      <div class="setup-meta">${t.entry_time?.slice(0, 16).replace('T', ' ')}${t.tag ? ' · ' + t.tag : ''}${(t.tags || []).length && !t.tag ? ' · ' + t.tags.join(' · ') : ''} · Entry ${t.entry}</div>
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
    entry_price: Number(state.draft.entry),
    stop_loss: Number(els.fieldSL.value),
    take_profit: Number(els.fieldTP.value),
    note: state.meta.note || '',
    tags: state.meta.tags || [],
  };
}

async function onSave() {
  if (els.btnSave.disabled) return;

  els.btnSave.disabled = true;
  const originalText = els.btnSave.textContent;
  els.btnSave.textContent = state.mode === 'edit' ? 'Đang cập nhật...' : 'Đang lưu...';

  try {
    const body = buildSetupBody();
    if (state.mode === 'edit' && state.editingId) {
      await updateSetup(state.editingId, body);
    } else {
      await saveSetup(body);
    }
    await refreshSetups();
    setMode('idle');
  } catch (e) {
    alert(`Không lưu được setup: ${e.message || e}`);
    validateSave();
  } finally {
    els.btnSave.textContent = originalText;
  }
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
      validateSave();
      updateRR();
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
      validateSave();
      updateRR();
    }
  };

  els.fieldEntry.oninput = () => {
    const entry = Number(els.fieldEntry.value);
    state.draft.entry = Number.isFinite(entry) ? entry : null;
    drawOverlayOnly();
    validateSave();
    updateRR();
  };
  els.fieldTime.oninput = () => {
    state.draft.time = unixFromDatetimeLocal(els.fieldTime.value);
    drawOverlayOnly();
    validateSave();
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

function showBootError(message) {
  const safe = String(message ?? 'Lỗi không xác định')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  let banner = document.getElementById('bootError');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'bootError';
    banner.className = 'boot-error-banner';
    document.getElementById('app')?.prepend(banner);
  }
  banner.innerHTML = `
    <div class="boot-error-inner">
      <strong>Không tải được dữ liệu</strong>
      <p>${safe}. Dữ liệu setup vẫn lưu trên server — chạy <code>./run.sh</code> rồi bấm Thử lại.</p>
      <button type="button" class="btn primary" id="btnBootRetry">Thử lại</button>
    </div>
  `;
  banner.querySelector('#btnBootRetry').onclick = () => {
    banner.remove();
    loadAppData();
  };
}

function hideBootError() {
  document.getElementById('bootError')?.remove();
}

function setLoading(on) {
  const el = document.getElementById('appLoading');
  if (el) el.classList.toggle('hidden', !on);
}

async function fetchWithRetry(fn, { retries = 3, delayMs = 800 } = {}) {
  let lastErr;
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (i < retries - 1) await new Promise((r) => setTimeout(r, delayMs * (i + 1)));
    }
  }
  throw lastErr;
}

let uiReady = false;
let layoutReady = false;

function initShell() {
  if (uiReady) return;
  bindUI();
  if (!chart.isMounted()) {
    chart.mount();
  }
  if (!layoutReady) {
    initSidebarResize({
      layoutEl: document.getElementById('layout'),
      sidebarEl: document.getElementById('sidebar'),
      resizerEl: document.getElementById('sidebarResizer'),
      onResize: () => chart.resize?.(),
    });
    layoutReady = true;
  }
  uiReady = true;
}

async function loadAppData() {
  setLoading(true);
  try {
    state.config = await fetchWithRetry(() => getConfig());
    await loadTagPresets();
    renderTagCheckboxes();
    renderPeriodTabs();
    if (state.config?.periods?.[state.period]) {
      els.periodBadge.textContent = state.config.periods[state.period].label;
    }
    setMode('idle');
    await fetchWithRetry(() => loadChart());
    await fetchWithRetry(() => refreshSetups());
    refreshChartAnnotations();
    requestAnimationFrame(() => chart.resize?.());
    hideBootError();
  } catch (err) {
    console.error('Load failed:', err);
    showBootError(err.message || 'Không kết nối được server');
  } finally {
    setLoading(false);
  }
}

async function boot() {
  initShell();
  await loadAppData();
}

window.addEventListener('error', (event) => {
  console.error('Uncaught error:', event.error || event.message);
});
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled rejection:', event.reason);
});

boot();
