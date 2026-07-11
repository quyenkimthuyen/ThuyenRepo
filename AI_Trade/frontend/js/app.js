import {
  analyze,
  backtest,
  compareBacktests,
  deleteBacktestRun,
  deleteSetup,
  deleteBarAnnotation,
  getBacktest,
  getBacktests,
  getBarAnnotations,
  getCandles,
  getConfig,
  getImportantBars,
  getMonths,
  getPresets,
  getSetups,
  getStrategies,
  getStrategy,
  getStrategyTypes,
  inspectBar,
  saveBarAnnotation,
  saveBarDetectionConfig,
  saveSetup,
  suggestTags,
  updateSetup,
} from './api.js?v=30';
import {
  renderAnalyzeView,
  renderBacktestView,
  renderBacktestCompare,
  renderBacktestSidebarSummary,
  renderBacktestTradesPanel,
  renderError,
  renderLoading,
  renderRsiBandLegend,
} from './strategy-ui.js?v=30';
import { initSidebarResize, initChartSplit } from './layout.js?v=30';
import { TradeChart } from './chart.js?v=30';

/** @typedef {'idle' | 'new' | 'edit'} EditorMode */

const state = {
  period: 'train_2022',
  trainPeriod: 'train_2024',
  trainMonth: '2022-01',
  monthMeta: [],
  labelSubTab: 'bars',
  listFilterByMonth: false,
  mode: /** @type {EditorMode} */ ('idle'),
  direction: 'long',
  step: 'entry',
  draft: { entry: null, sl: null, tp: null, time: null },
  meta: { tags: [], note: '' },
  editingId: null,
  setups: [],
  config: null,
  strategyTypes: [],
  strategyId: 'rsi_h4_zone',
  analyzeValidationPeriod: null,
  tagPresets: [],
  sidebarTab: 'label',
  btSelectedPeriods: ['bt_2024'],
  btStrategyId: 'rsi_h4_zone',
  btStrategyPeriod: 'train_2024',
  btWorkspaceTab: 'results',
  btWorkspaceCollapsed: false,
  btCache: null,
  btRuns: [],
  activeBtRunId: null,
  compareBtIds: [],
  focusedTradeKey: null,
  focusedSetupId: null,
  showImportantBars: false,
  importantBars: [],
  inspectedBar: null,
  detectionConfig: null,
  barAnnotations: [],
  barContext: null,
};

const els = {
  periodTabs: document.getElementById('periodTabs'),
  monthTabs: document.getElementById('monthTabs'),
  periodBadge: document.getElementById('periodBadge'),
  editorPanel: document.getElementById('editorPanel'),
  modePill: document.getElementById('modePill'),
  rrPill: document.getElementById('rrPill'),
  activeBlock: document.getElementById('activeBlock'),
  newSteps: document.getElementById('newSteps'),
  setupList: document.getElementById('setupList'),
  setupCount: document.getElementById('setupCount'),
  setupTabCount: document.getElementById('setupTabCount'),
  barTabCount: document.getElementById('barTabCount'),
  labelSubtabs: document.querySelectorAll('.label-subtab'),
  labelSubviews: {
    bars: document.getElementById('labelBarsView'),
    setups: document.getElementById('labelSetupsView'),
  },
  barInspectTitle: document.getElementById('barInspectTitle'),
  fieldEntry: document.getElementById('fieldEntry'),
  fieldSL: document.getElementById('fieldSL'),
  fieldTP: document.getElementById('fieldTP'),
  fieldTime: document.getElementById('fieldTime'),
  tagCheckboxGroup: document.getElementById('tagCheckboxGroup'),
  tagSuggestPanel: document.getElementById('tagSuggestPanel'),
  tagSuggestTags: document.getElementById('tagSuggestTags'),
  tagSuggestSimilar: document.getElementById('tagSuggestSimilar'),
  barInspectPanel: document.getElementById('barInspectPanel'),
  barInspectScore: document.getElementById('barInspectScore'),
  barInspectReasons: document.getElementById('barInspectReasons'),
  barInspectTags: document.getElementById('barInspectTags'),
  barInspectSeq: document.getElementById('barInspectSeq'),
  barInspectSimilar: document.getElementById('barInspectSimilar'),
  barAnnotTags: document.getElementById('barAnnotTags'),
  importantBarListSection: document.getElementById('importantBarListSection'),
  importantBarList: document.getElementById('importantBarList'),
  importantBarListCount: document.getElementById('importantBarListCount'),
  barAnnotationList: document.getElementById('barAnnotationList'),
  barAnnotationCount: document.getElementById('barAnnotationCount'),
  chartHoverHint: document.getElementById('chartHoverHint'),
  btnSave: document.getElementById('btnSave'),
  btnDelete: document.getElementById('btnDelete'),
  chartOverlayHint: document.getElementById('chartOverlayHint'),
  analyzeResults: document.getElementById('analyzeResults'),
  analyzeStrategyType: document.getElementById('analyzeStrategyType'),
  analyzeTrainPeriod: document.getElementById('analyzeTrainPeriod'),
  analyzeValidationPeriod: document.getElementById('analyzeValidationPeriod'),
  btYearPicker: document.getElementById('btYearPicker'),
  btStrategyType: document.getElementById('btStrategyType'),
  btStrategyPeriod: document.getElementById('btStrategyPeriod'),
  btSidebarSummary: document.getElementById('btSidebarSummary'),
  btWorkspace: document.getElementById('btWorkspace'),
  btPanelResults: document.getElementById('btPanelResults'),
  btPanelTrades: document.getElementById('btPanelTrades'),
  btPanelCompare: document.getElementById('btPanelCompare'),
  chartArea: document.querySelector('.chart-area'),
  btCount: document.getElementById('btCount'),
  btSavedList: document.getElementById('btSavedList'),
  btSavedCount: document.getElementById('btSavedCount'),
  btSaveName: document.getElementById('btSaveName'),
  pipelineHint: document.getElementById('pipelineHint'),
  pipelineBanner: document.getElementById('pipelineBanner'),
  sidebarTabs: document.querySelectorAll('.sidebar-tab'),
  sidebarViews: {
    label: document.getElementById('viewLabel'),
    analyze: document.getElementById('viewAnalyze'),
    backtest: document.getElementById('viewBacktest'),
  },
};

const chart = new TradeChart(
  document.getElementById('chartMain'),
  document.getElementById('chartRsi'),
  {
    onClick: handleChartClick,
    onLevelDrag: handleLevelDrag,
    onImportantBarHover: handleImportantBarHover,
  },
);

const MODE_LABELS = { idle: 'Xem chart', new: 'Tạo mới', edit: 'Chỉnh sửa' };

const DEFAULT_TAGS = [
  { id: 'rsi_break_retest', label: 'RSI break + retest 50', hint: 'Setup 1: break vùng 48–52 rồi test lại' },
  { id: 'rsi_extreme_bounce', label: 'RSI extreme bounce', hint: 'Setup 2: chạm 70/30, hồi 50, bật lại' },
  { id: 'ema_h1_confirm', label: 'EMA H1 xác nhận', hint: 'Giá giữ hỗ trợ/kháng cự EMA 50/200 H1' },
];

const STEP_HINTS = {
  entry: 'Bước 1 — Click trên chart để đặt điểm Entry',
  sl: 'Bước 2 — Click hoặc kéo đường đỏ để đặt Stop Loss',
  tp: 'Bước 3 — Click hoặc kéo đường xanh lá để đặt Take Profit',
};

function defaultPlannedRR() {
  return Number(state.config?.quality?.default_planned_rr ?? 2.5);
}

function tpFromRisk(entry, sl, direction, rr = defaultPlannedRR()) {
  const risk = Math.abs(entry - sl);
  return Number(
    (direction === 'long' ? entry + risk * rr : entry - risk * rr).toFixed(5),
  );
}

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

function entryHasBarAnnotation() {
  if (state.draft.time == null) return false;
  const iso = isoFromUnix(state.draft.time);
  return state.barAnnotations.some(
    (a) =>
      a.confirmed !== false &&
      (a.tags || []).length &&
      (a.bar_time || '').slice(0, 16) === iso.slice(0, 16),
  );
}

function updatePipelineUI() {
  const banner = els.pipelineBanner;
  const hint = els.pipelineHint;
  if (!banner) return;

  let step = 'bar';
  if (state.sidebarTab === 'analyze') step = 'strategy';
  else if (state.sidebarTab === 'backtest') step = 'backtest';
  else if (state.labelSubTab === 'setups' && (state.mode === 'new' || state.mode === 'edit')) step = 'setup';
  else if (state.labelSubTab === 'setups') step = 'setup';
  else if (state.inspectedBar?.annotation?.tags?.length) step = 'tag';
  else if (state.inspectedBar || state.showImportantBars) step = 'bar';

  banner.querySelectorAll('.pipe-step').forEach((el) => {
    el.classList.toggle('active', el.dataset.step === step);
  });

  if (hint) {
    const hints = {
      bar: 'Bật 「Nến quan trọng」 và click một nến trên chart.',
      tag: 'Chọn tag và bấm 「Lưu tag nến」 — bước bắt buộc trước setup.',
      setup: 'Đặt SL/TP — tag setup phải khớp ít nhất 1 tag nến đã lưu.',
      strategy: `Tab Analyze → học pattern từ setup train ${periodShortLabel(state.trainPeriod)}.`,
      backtest: 'Vào lệnh khi nến đạt score + tag + giống setup train. Xem kết quả ở panel dưới chart.',
    };
    hint.textContent = hints[step] || hints.bar;
  }
}

function periodCfg(id) {
  return state.config?.periods?.[id];
}

function periodKind(id) {
  return periodCfg(id)?.kind;
}

function isTrainChartPeriod(id = state.period) {
  return periodKind(id) === 'train';
}

function isBacktestChartPeriod(id = state.period) {
  return periodKind(id) === 'backtest';
}

function defaultTrainPeriod() {
  return state.config?.period_groups?.defaults?.train
    || state.config?.defaults?.train
    || 'train_2022';
}

function defaultBtPeriods() {
  return state.config?.period_groups?.defaults?.backtest || ['bt_2023'];
}

function suggestedBtPeriodForTrain(trainPeriod) {
  const mapped = state.config?.period_groups?.train_validation?.[trainPeriod];
  if (mapped) return mapped;
  const year = periodCfg(trainPeriod)?.year;
  if (!year) return defaultBtPeriods()[0];
  const next = `bt_${year + 1}`;
  const ids = backtestPeriodIds();
  if (ids.includes(next)) return next;
  const same = `bt_${year}`;
  if (ids.includes(same)) return same;
  return defaultBtPeriods()[0];
}

function applySuggestedBtPeriod(trainPeriod) {
  const suggested = suggestedBtPeriodForTrain(trainPeriod);
  if (!suggested) return;
  state.btSelectedPeriods = [suggested];
  renderBtYearPicker();
}

function trainPeriodIds() {
  const groups = state.config?.period_groups?.train;
  if (groups?.length) return groups.map((p) => p.id);
  return Object.entries(state.config?.periods || {})
    .filter(([, cfg]) => cfg.kind === 'train')
    .map(([id]) => id);
}

function backtestPeriodIds() {
  const groups = state.config?.period_groups?.backtest;
  if (groups?.length) return groups.map((p) => p.id);
  return Object.entries(state.config?.periods || {})
    .filter(([, cfg]) => cfg.kind === 'backtest')
    .map(([id]) => id);
}

function periodShortLabel(id) {
  const cfg = periodCfg(id);
  if (cfg?.year) return String(cfg.year);
  return id;
}

function periodNameLabel(id) {
  if (periodKind(id) === 'train') return 'Train';
  if (periodKind(id) === 'backtest') return 'BT';
  return id;
}

function sortedPeriodEntries() {
  return Object.entries(state.config?.periods || {}).sort((a, b) => {
    const ka = a[1].kind === 'train' ? 0 : 1;
    const kb = b[1].kind === 'train' ? 0 : 1;
    if (ka !== kb) return ka - kb;
    return (a[1].year || 0) - (b[1].year || 0);
  });
}

function activeBtTrades() {
  return state.btCache?.trades || [];
}

function chartShowsActiveBacktest() {
  if (!isBacktestChartPeriod()) return false;
  if (!state.btCache) return false;
  const periods = state.btCache.periods || [state.btCache.period];
  return periods.includes(state.period) || state.btCache.period?.split(',').includes(state.period);
}

function activeMonth() {
  return null;
}

function listFilterMonth() {
  if (!state.listFilterByMonth || !isTrainChartPeriod()) return null;
  return state.trainMonth;
}

function barDisplayCode(item) {
  return item?.code || item?.id || '—';
}

function setupDisplayCode(item) {
  return item?.code || item?.id || '—';
}

function monthKeyFromTime(iso) {
  return (iso || '').slice(0, 7);
}

function trainSetups() {
  return state.setups.filter((s) => (s.period || defaultTrainPeriod()) === state.trainPeriod);
}

function monthChartSetups() {
  const month = listFilterMonth();
  if (!month) return trainSetups();
  return trainSetups().filter((s) => monthKeyFromTime(s.entry_time) === month);
}

function setupsForList() {
  const all = trainSetups();
  if (!state.listFilterByMonth || !isTrainChartPeriod()) return all;
  const month = listFilterMonth();
  if (!month) return all;
  return all.filter((s) => monthKeyFromTime(s.entry_time) === month);
}

function annotationsForList() {
  const all = state.barAnnotations || [];
  if (!state.listFilterByMonth || !isTrainChartPeriod()) return all;
  const month = listFilterMonth();
  if (!month) return all;
  return all.filter((a) => monthKeyFromTime(a.bar_time) === month);
}

function updateLabelTabCounts() {
  const setupTotal = trainSetups().length;
  const setupMonth = monthChartSetups().length;
  const barTotal = state.barAnnotations?.length || 0;
  const barMonth = listFilterMonth()
    ? (state.barAnnotations || []).filter((a) => monthKeyFromTime(a.bar_time) === listFilterMonth()).length
    : barTotal;
  if (els.barTabCount) {
    els.barTabCount.textContent =
      isTrainChartPeriod() && state.listFilterByMonth ? `${barMonth}/${barTotal}` : String(barTotal);
  }
  if (els.setupTabCount) {
    els.setupTabCount.textContent =
      isTrainChartPeriod() && state.listFilterByMonth ? `${setupMonth}/${setupTotal}` : String(setupTotal);
  }
}

function setLabelSubTabUI(tabId) {
  state.labelSubTab = tabId;
  els.labelSubtabs?.forEach((btn) => {
    const active = btn.dataset.labelTab === tabId;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  for (const [key, view] of Object.entries(els.labelSubviews)) {
    view?.classList.toggle('hidden', key !== tabId);
    view?.classList.toggle('active', key === tabId);
  }
  updatePipelineUI();
}

function switchLabelSubTab(tabId) {
  setLabelSubTabUI(tabId);
}

function renderMonthTabs() {
  const container = els.monthTabs;
  if (!container) return;
  container.classList.add('hidden');
  container.innerHTML = '';
}

function updateListMonthFilters() {
  const show = isTrainChartPeriod();
  document.querySelectorAll('.list-filter-check').forEach((el) => {
    el.classList.toggle('hidden', !show);
  });
}

async function switchTrainMonth(month) {
  state.trainMonth = month;
  renderSetups();
  renderBarAnnotationList();
  updateLabelTabCounts();
}

async function loadMonthMeta() {
  if (!isTrainChartPeriod()) {
    state.monthMeta = [];
    renderMonthTabs();
    return;
  }
  try {
    const data = await getMonths(state.trainPeriod);
    state.monthMeta = data.months || [];
    if (state.monthMeta.length && !state.monthMeta.some((m) => m.month === state.trainMonth)) {
      state.trainMonth = state.monthMeta[0].month;
    }
    renderMonthTabs();
    updateListMonthFilters();
  } catch (err) {
    console.warn('Month meta failed:', err);
    state.monthMeta = [];
    renderMonthTabs();
  }
}

async function loadMonthData() {
  setLoading(true);
  try {
    await Promise.all([refreshSetups(), refreshBarAnnotations()]);
    await Promise.all([loadChart(), loadImportantBars()]);
    updateLabelTabCounts();
    refreshChartAnnotations();
  } finally {
    setLoading(false);
  }
}

function tradeKey(trade) {
  return `${trade.entry_time}|${trade.direction}|${trade.entry}`;
}

function refreshChartAnnotations() {
  if (state.mode !== 'idle') return;

  if (isTrainChartPeriod()) {
    if (state.focusedSetupId) return;
    chart.showSetupMarkers(trainSetups());
    if (state.showImportantBars) {
      chart.showImportantBars(state.importantBars);
    } else {
      chart.clearImportantBars();
    }
    return;
  }

  chart.showSetupMarkers([]);
  if (isBacktestChartPeriod() && chartShowsActiveBacktest()) {
    if (state.focusedTradeKey) return;
    chart.showTradeMarkers(activeBtTrades());
  } else {
    chart.showTradeMarkers([]);
  }
  chart.clearImportantBars();
  els.chartOverlayHint?.classList.add('hidden');
}

function isTrainPeriod() {
  return isTrainChartPeriod();
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

function hideBarInspect() {
  state.inspectedBar = null;
  chart.setSelectedImportantBar(null);
  chart.clearSequenceWindow();
  els.barInspectPanel?.classList.add('hidden');
  renderImportantBarList();
}

function renderBarAnnotCheckboxes(selectedTags = []) {
  const group = els.barAnnotTags;
  if (!group) return;
  const wanted = new Set(selectedTags);
  const presets = tagPresetList();
  group.innerHTML = '';
  for (const tag of presets) {
    const label = document.createElement('label');
    label.className = 'tag-check';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = tag.id;
    input.checked = wanted.has(tag.id);
    label.appendChild(input);
    label.appendChild(document.createTextNode(tag.label));
    group.appendChild(label);
  }
  const ann = state.inspectedBar?.annotation;
  document.getElementById('btnDeleteBarAnnot')?.classList.toggle('hidden', !ann?.id);
}

function barAnnotSelectedTags() {
  if (!els.barAnnotTags) return [];
  return [...els.barAnnotTags.querySelectorAll('input:checked')].map((el) => el.value);
}

async function saveBarAnnotationFromInspect() {
  const bar = state.inspectedBar;
  if (!bar) return;
  const tags = barAnnotSelectedTags();
  if (!tags.length) {
    alert('Chọn ít nhất 1 tag trước khi lưu.');
    return;
  }
  const btn = document.getElementById('btnSaveBarAnnot');
  const original = btn?.textContent;
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Đang lưu...';
  }
  try {
    const saved = await saveBarAnnotation({
      id: bar.annotation?.id,
      bar_time: bar.entry_time,
      close: bar.close,
      tags,
      note: tags.map((id) => tagPresetList().find((t) => t.id === id)?.label || id).join(' + '),
      confirmed: true,
      auto_detected_tags: (bar.detected_tags || []).map((t) => t.tag),
      score: bar.importance?.score,
      train_period: state.trainPeriod,
    });
    await refreshBarAnnotations();
    await loadImportantBars();
    await loadMonthMeta();
    renderImportantBarList();
    const refreshed = await inspectBar(bar.entry_time, bar.close);
    renderBarInspect(refreshed);
  } catch (err) {
    alert(`Không lưu được tag nến: ${err.message || err}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = original;
    }
  }
}

async function deleteBarAnnotationFromInspect() {
  const id = state.inspectedBar?.annotation?.id;
  if (!id || !confirm('Xóa tag đã lưu cho nến này?')) return;
  await deleteBarAnnotation(id);
  await refreshBarAnnotations();
  await loadImportantBars();
  await loadMonthMeta();
  renderImportantBarList();
  if (state.inspectedBar) {
    const refreshed = await inspectBar(state.inspectedBar.entry_time, state.inspectedBar.close);
    renderBarInspect(refreshed);
  }
}

async function refreshBarAnnotations() {
  const { annotations } = await getBarAnnotations({ period: state.trainPeriod });
  state.barAnnotations = annotations || [];
  renderBarAnnotationList();
  updateLabelTabCounts();
}

function renderBarAnnotationList() {
  const list = els.barAnnotationList;
  const countEl = els.barAnnotationCount;
  if (!list) return;

  const items = annotationsForList();
  const total = (state.barAnnotations || []).length;
  if (countEl) {
    countEl.textContent =
      state.listFilterByMonth && isTrainChartPeriod() && total > items.length
        ? `${items.length}/${total}`
        : String(items.length);
  }
  list.innerHTML = '';

  if (!total) {
    list.innerHTML =
      '<li class="hint" style="padding:8px">Chưa lưu tag nến. Bật 「Nến quan trọng」 và lưu tag trên chart.</li>';
    return;
  }

  if (!items.length) {
    list.innerHTML = `<li class="hint" style="padding:8px">Không có tag nến trong tháng ${state.trainMonth?.slice(5) || '—'}. Bỏ 「Lọc tháng」 để xem tất cả ${total} tag.</li>`;
    return;
  }

  const sorted = [...items].sort((a, b) =>
    (b.bar_time || '').localeCompare(a.bar_time || ''),
  );
  for (const ann of sorted) {
    const li = document.createElement('li');
    const selected =
      state.inspectedBar?.annotation?.id === ann.id ||
      state.inspectedBar?.entry_time === ann.bar_time;
    const tags = (ann.tags || []).join(' · ') || '—';
    const time = (ann.bar_time || '').slice(0, 16).replace('T', ' ');
    const code = barDisplayCode(ann);
    li.className = `setup-item bar-item confirmed${selected ? ' selected' : ''}`;
    li.innerHTML = `
      <div class="setup-top">
        <span class="entity-code">${code}</span>
        <span class="setup-dir">${ann.score ?? '—'}</span>
        <span class="pill good">${tags}</span>
      </div>
      <div class="setup-meta">${time}${ann.setup_code ? ` · → <span class="setup-linked-bar">${ann.setup_code}</span>` : ''}</div>
    `;
    li.onclick = async () => {
      const data = await inspectBar(ann.bar_time, ann.close ?? null);
      renderBarInspect(data);
      chart.scrollToTime(data.time);
    };
    list.appendChild(li);
  }
}

function renderImportantBarList() {
  const section = els.importantBarListSection;
  const list = els.importantBarList;
  const countEl = els.importantBarListCount;
  if (!section || !list) return;

  const show = state.showImportantBars;
  section.classList.toggle('hidden', !show);
  if (!show) return;

  const bars = state.importantBars || [];
  countEl.textContent = String(bars.length);
  list.innerHTML = '';

  if (!bars.length) {
    list.innerHTML = '<li class="hint" style="padding:8px">Không có nến đạt ngưỡng score.</li>';
    return;
  }

  const sorted = [...bars].sort((a, b) => b.score - a.score);
  for (const bar of sorted) {
    const li = document.createElement('li');
    const selected = state.inspectedBar?.time === bar.time;
    const tag =
      bar.confirmed_tags?.[0] || bar.primary_tag || (bar.suggested_tags?.[0] ?? '—');
    const barCode = bar.annotation_id
      ? state.barAnnotations.find((a) => a.id === bar.annotation_id)?.code
      : null;
    li.className = `setup-item bar-item${selected ? ' selected' : ''}${bar.user_confirmed ? ' confirmed' : ''}`;
    const time = new Date(bar.time * 1000).toISOString().slice(0, 16).replace('T', ' ');
    li.innerHTML = `
      <div class="setup-top">
        ${barCode ? `<span class="entity-code">${barCode}</span>` : ''}
        <span class="setup-dir">${bar.score}</span>
        <span class="pill">${tag}</span>
        ${bar.user_confirmed ? '<span class="pill good">✓</span>' : ''}
      </div>
      <div class="setup-meta">${time}</div>
    `;
    li.onclick = async () => {
      const data = await inspectBar(new Date(bar.time * 1000).toISOString(), null);
      renderBarInspect(data);
      chart.setSelectedImportantBar(bar.time);
      chart.scrollToTime(bar.time);
    };
    list.appendChild(li);
  }
}

function handleImportantBarHover(bar) {
  const hint = els.chartHoverHint;
  if (!hint || !state.showImportantBars) return;
  if (!bar) {
    hint.classList.add('hidden');
    return;
  }
  const tag =
    bar.confirmed_tags?.[0] || bar.primary_tag || (bar.suggested_tags?.[0] ?? '—');
  const time = new Date(bar.time * 1000).toISOString().slice(0, 16).replace('T', ' ');
  hint.textContent = `${time} · score ${bar.score} · ${tag}${bar.user_confirmed ? ' · đã lưu' : ''}`;
  hint.classList.remove('hidden');
}

function renderBarInspect(data) {
  if (!els.barInspectPanel || !data) {
    hideBarInspect();
    return;
  }

  state.inspectedBar = data;
  els.barInspectPanel.classList.remove('hidden');
  if (els.barInspectTitle) {
    const code = data.annotation?.code || barDisplayCode(data.annotation || {});
    els.barInspectTitle.textContent = code !== '—' ? `Nến ${code}` : 'Nến quan trọng';
  }
  chart.setSelectedImportantBar(data.time);
  const seqWindow = data.sequence?.window ?? state.detectionConfig?.sequence_window ?? 5;
  chart.showSequenceWindow(data.time, seqWindow);
  renderImportantBarList();
  renderBarAnnotationList();

  const tagsForEdit =
    data.annotation?.tags?.length ? data.annotation.tags : data.suggested_tags || [];
  renderBarAnnotCheckboxes(tagsForEdit);

  const imp = data.importance || {};
  const score = imp.score ?? 0;
  const minScore = state.detectionConfig?.min_score ?? 35;
  const important = data.important !== false && score >= minScore;
  els.barInspectScore.innerHTML = `
    <span class="score-pill ${important ? 'hot' : 'warm'}">${score}/100</span>
    <span class="muted">${(data.entry_time || '').slice(0, 16).replace('T', ' ')} · Close ${data.close}</span>
  `;

  const reasons = imp.reason_labels || [];
  els.barInspectReasons.innerHTML = reasons.length
    ? reasons.map((r) => `<span class="reason-chip">${r}</span>`).join('')
    : '<span class="muted">Chưa đủ điểm vị trí quan trọng</span>';

  const detected = data.detected_tags || [];
  els.barInspectTags.innerHTML = detected.length
    ? detected
        .map((item) => {
          const src = (item.sources || [item.source || 'bar']).join('+');
          return `<span class="pill suggest" title="${src}">${item.tag} ${Math.round(item.score * 100)}%</span>`;
        })
        .join(' ')
    : '<span class="muted">Chưa nhận diện tag — gắn thủ công khi tạo setup</span>';

  const seqTags = data.sequence_tags || [];
  const seq = data.sequence;
  if (els.barInspectSeq) {
    const seqLabel = seqTags.length
      ? seqTags.map((t) => `${t.tag} (${t.label || t.source})`).join(' · ')
      : '—';
    const momentum = seq?.momentum_pips != null ? `${seq.momentum_pips} pips` : '—';
    els.barInspectSeq.innerHTML = `<strong>Chuỗi ${seq?.window ?? 5} nến:</strong> momentum ${momentum} · ${seqLabel}`;
  }

  const similar = data.similar_setups || [];
  els.barInspectSimilar.innerHTML = similar.length
    ? similar
        .map((item) => {
          const time = (item.entry_time || '').slice(0, 10);
          const tags = (item.tags || []).join(', ');
          return `<li>${Math.round(item.similarity * 100)}% · ${item.direction?.toUpperCase()} · ${item.result?.toUpperCase()} · ${time}${tags ? ` · ${tags}` : ''}</li>`;
        })
        .join('')
    : '<li class="muted">Chưa có setup train tương tự</li>';
  updatePipelineUI();
}

async function inspectBarAt(time, candle) {
  try {
    const data = await inspectBar(isoFromUnix(time), Number(candle.close));
    renderBarInspect(data);
    chart.scrollToTime(time);
    els.chartOverlayHint.textContent = `Nến score ${data.importance?.score ?? '—'} — ${(data.suggested_tags || []).join(', ') || 'chưa có tag'}`;
    els.chartOverlayHint.classList.remove('hidden');
  } catch (err) {
    console.warn('Inspect bar failed:', err);
  }
}

async function loadImportantBars() {
  if (!isTrainChartPeriod() || !state.showImportantBars) {
    chart.clearImportantBars();
    if (!isTrainChartPeriod()) {
      els.chartOverlayHint?.classList.add('hidden');
    }
    return;
  }
  try {
    const data = await getImportantBars(state.period, activeMonth());
    state.importantBars = data.bars || [];
    if (data.config) state.detectionConfig = data.config;
    if (state.mode === 'idle' && !state.focusedSetupId && !state.focusedTradeKey) {
      chart.showImportantBars(state.importantBars);
    }
    renderImportantBarList();
    if (state.importantBars.length && state.mode === 'idle') {
      const minScore = state.detectionConfig?.min_score ?? 35;
      els.chartOverlayHint.textContent = `${state.importantBars.length} nến ≥ score ${minScore} — click để xem tag + chuỗi nến`;
      els.chartOverlayHint.classList.remove('hidden');
    }
  } catch (err) {
    console.warn('Important bars failed:', err);
    chart.clearImportantBars();
  }
}

function bindDetectionRange(inputId, valId, { format = (v) => v } = {}) {
  const input = document.getElementById(inputId);
  const valEl = document.getElementById(valId);
  if (!input || !valEl) return;
  input.oninput = () => {
    valEl.textContent = format(input.value);
  };
}

function initDetectionSettings(config) {
  state.detectionConfig = config;
  if (!config) return;

  const sw = config.score_weights || {};
  const set = (id, valId, value, format) => {
    const el = document.getElementById(id);
    const valEl = document.getElementById(valId);
    if (!el) return;
    el.value = String(value);
    if (valEl) valEl.textContent = format ? format(value) : String(value);
  };

  set('cfgMinScore', 'cfgMinScoreVal', config.min_score ?? 35);
  set('cfgSeqWindow', 'cfgSeqWindowVal', config.sequence_window ?? 5);
  set(
    'cfgSeqMin',
    'cfgSeqMinVal',
    Math.round((config.sequence_min_score ?? 0.45) * 100),
    (v) => `${v}%`,
  );
  set('cfgWEma50', 'cfgWEma50Val', sw.near_ema50_strong ?? 22);
  set('cfgWSeq', 'cfgWSeqVal', sw.sequence_match_mult ?? 30);
  set('cfgWLabel', 'cfgWLabelVal', sw.labeled_setup ?? 40);
  set('cfgBtMinScore', 'cfgBtMinScoreVal', config.backtest_min_score ?? 35);
  const reqSeq = document.getElementById('cfgRequireSeqTag');
  if (reqSeq) reqSeq.checked = Boolean(config.require_sequence_tag);

  bindDetectionRange('cfgMinScore', 'cfgMinScoreVal');
  bindDetectionRange('cfgBtMinScore', 'cfgBtMinScoreVal');
  bindDetectionRange('cfgSeqWindow', 'cfgSeqWindowVal');
  bindDetectionRange('cfgSeqMin', 'cfgSeqMinVal', { format: (v) => `${v}%` });
  bindDetectionRange('cfgWEma50', 'cfgWEma50Val');
  bindDetectionRange('cfgWSeq', 'cfgWSeqVal');
  bindDetectionRange('cfgWLabel', 'cfgWLabelVal');
}

function collectDetectionPatch() {
  const seqPct = Number(document.getElementById('cfgSeqMin')?.value || 45);
  return {
    min_score: Number(document.getElementById('cfgMinScore')?.value || 35),
    backtest_min_score: Number(document.getElementById('cfgBtMinScore')?.value || 35),
    require_sequence_tag: Boolean(document.getElementById('cfgRequireSeqTag')?.checked),
    sequence_window: Number(document.getElementById('cfgSeqWindow')?.value || 5),
    sequence_min_score: Math.round(seqPct) / 100,
    score_weights: {
      near_ema50_strong: Number(document.getElementById('cfgWEma50')?.value || 22),
      sequence_match_mult: Number(document.getElementById('cfgWSeq')?.value || 30),
      labeled_setup: Number(document.getElementById('cfgWLabel')?.value || 40),
    },
  };
}

async function saveDetectionSettings() {
  const btn = document.getElementById('btnSaveDetection');
  const original = btn?.textContent;
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Đang lưu...';
  }
  try {
    const patch = collectDetectionPatch();
    state.detectionConfig = await saveBarDetectionConfig(patch);
    initDetectionSettings(state.detectionConfig);
    if (state.showImportantBars) await loadImportantBars();
  } catch (err) {
    alert(`Không lưu được cài đặt: ${err.message || err}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = original;
    }
  }
}

async function startSetupFromInspectedBar() {
  const bar = state.inspectedBar;
  if (!bar) return;
  if (!(bar.annotation?.tags || []).length) {
    alert('Luồng bắt buộc: lưu tag nến (bước ②) trước khi tạo setup.');
    return;
  }
  await ensureTrainPeriod();
  switchLabelSubTab('setups');
  switchSidebarTab('label', { syncPeriod: false });
  clearDraft();
  state.mode = 'new';
  state.step = 'sl';
  state.barContext = {
    entry_time: bar.entry_time,
    annotation_id: bar.annotation?.id || null,
    bar_tags: bar.annotation?.tags || bar.suggested_tags || [],
    sequence_tags: (bar.sequence_tags || []).map((t) => t.tag || t),
  };
  state.draft = {
    time: bar.time,
    entry: Number(bar.close),
    sl: null,
    tp: null,
  };
  const dir = bar.suggested_direction || 'long';
  setDirection(dir);
  const defaultSl = dir === 'long' ? bar.close - 0.003 : bar.close + 0.003;
  state.draft.sl = Number(defaultSl.toFixed(5));
  els.fieldSL.value = state.draft.sl;
  const risk = Math.abs(state.draft.entry - state.draft.sl);
  state.draft.tp = tpFromRisk(state.draft.entry, state.draft.sl, dir);
  els.fieldTP.value = state.draft.tp;
  state.step = 'tp';
  if (bar.suggested_tags?.length || bar.annotation?.tags?.length) {
    setSelectedTags(bar.annotation?.tags?.length ? bar.annotation.tags : bar.suggested_tags, {
      userEdited: false,
    });
  }
  updateModeUI();
  syncFields({ focus: true });
  refreshTagSuggest({ applyTags: false });
  hideBarInspect();
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
  if (isBacktestChartPeriod() && chartShowsActiveBacktest()) {
    const n = activeBtTrades().length;
    if (n > 0) {
      els.chartOverlayHint.textContent = `${n} lệnh backtest — chọn lệnh ở tab 「Lệnh」 dưới chart`;
      els.chartOverlayHint.classList.remove('hidden');
      return;
    }
  }
  if (isTrainChartPeriod() && trainSetups().length > 0 && state.mode === 'idle') {
    const total = trainSetups().length;
    els.chartOverlayHint.textContent = `${total} setup trên chart — click xem · double-click sửa · cuộn/zoom để xem cả năm`;
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
  state.barContext = null;
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
  renderBtTradeList();
}

async function ensureTrainPeriod() {
  if (isTrainChartPeriod()) return;
  await switchPeriod(state.trainPeriod);
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
  const barTagged = state.mode === 'edit' || entryHasBarAnnotation();
  if (ok && state.direction === 'long') {
    valid = sl < entry && tp > entry && hasTag && barTagged;
  } else if (ok && state.direction === 'short') {
    valid = sl > entry && tp < entry && hasTag && barTagged;
  }
  els.btnSave.disabled = !valid;
  if (state.mode === 'new' && ok && hasTag && !barTagged) {
    els.pipelineHint.textContent =
      'Chưa có tag nến tại entry — quay lại bước ② (lưu tag nến) trước khi lưu setup.';
  } else {
    updatePipelineUI();
  }
}

function moveDraftEntryToCandle({ time, candle }) {
  const nextEntry = Number(candle.close);

  state.draft.time = time;
  state.draft.entry = nextEntry;
  syncFields({ focus: true });
  refreshTagSuggest({ applyTags: state.mode === 'new' });
}

function handleChartClick({ time, candle, price }) {
  if (!isTrainPeriod()) {
    if (state.mode === 'idle' && state.showImportantBars) {
      inspectBarAt(time, candle);
    }
    return;
  }

  if (state.mode === 'idle' && state.showImportantBars) {
    inspectBarAt(time, candle);
    return;
  }

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
    state.draft.tp = tpFromRisk(state.draft.entry, state.draft.sl, state.direction);
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
    state.draft.tp = tpFromRisk(state.draft.entry, state.draft.sl, state.direction);
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
  switchLabelSubTab('setups');
  state.showImportantBars = true;
  const toggle = document.getElementById('toggleImportantBars');
  if (toggle) toggle.checked = true;
  await loadImportantBars();

  if (state.inspectedBar?.annotation?.tags?.length) {
    await startSetupFromInspectedBar();
    return;
  }

  switchSidebarTab('label', { syncPeriod: false });
  switchLabelSubTab('bars');
  els.chartOverlayHint.textContent =
    'Luồng: click nến → lưu tag → bấm lại 「Setup từ nến đã tag」 hoặc 「Tạo setup tại nến này」';
  els.chartOverlayHint.classList.remove('hidden');
  updatePipelineUI();
}

async function startEditSetup(setup) {
  await ensureTrainPeriod();
  switchLabelSubTab('setups');
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
  chart.viewSetup(setup, { interactive: true });
  refreshTagSuggest({ applyTags: false });
  renderSetups();
}

function cancelEditor() {
  setMode('idle');
}

function renderPeriodTabs() {
  if (!state.config?.periods) return;
  els.periodTabs.innerHTML = '';
  for (const [key, cfg] of sortedPeriodEntries()) {
    const btn = document.createElement('button');
    btn.type = 'button';
    const kind = cfg.kind || 'backtest';
    btn.className = `period-tab${key === state.period ? ' active' : ''} ${kind}`;
    btn.title = cfg.label;
    btn.innerHTML = `<span class="period-year">${periodShortLabel(key)}</span><span class="period-name">${periodNameLabel(key)}</span>`;
    btn.onclick = () => switchPeriod(key);
    els.periodTabs.appendChild(btn);
  }
}

async function switchPeriod(period, { syncSidebar = true } = {}) {
  if (!state.config?.periods?.[period]) {
    period = defaultTrainPeriod();
  }
  if (state.mode !== 'idle') cancelEditor();
  state.period = period;
  if (isTrainChartPeriod(period)) {
    state.trainPeriod = period;
  }
  state.focusedTradeKey = null;
  state.focusedSetupId = null;
  if (state.config?.periods?.[period]) {
    els.periodBadge.textContent = state.config.periods[period].label;
  }
  renderPeriodTabs();
  await loadMonthMeta();
  if (syncSidebar) {
    if (isTrainChartPeriod(period) && (state.sidebarTab === 'label' || state.sidebarTab === 'analyze')) {
      setSidebarTabUI(state.sidebarTab);
    } else if (isBacktestChartPeriod(period) && state.sidebarTab === 'backtest') {
      setSidebarTabUI('backtest');
    }
  }
  updateModeUI();
  updateListMonthFilters();
  if (isTrainChartPeriod(period)) {
    await loadMonthData();
  } else {
    chart.clearOverlay();
    chart.clearFocus();
    await loadChart();
    await refreshSetups();
    await refreshBarAnnotations();
    state.importantBars = [];
    chart.clearImportantBars();
    els.chartOverlayHint?.classList.add('hidden');
    updateLabelTabCounts();
  }
}

async function syncChartStrategyBands() {
  const legendEl = document.getElementById('rsiBandLegend');
  const trainPeriod = isTrainChartPeriod(state.period) ? state.period : state.btStrategyPeriod;
  const strategyId = isTrainChartPeriod(state.period) ? state.strategyId : state.btStrategyId;
  try {
    const strategy = await getStrategy(trainPeriod, strategyId);
    state.activeStrategy = strategy;
    const mode = strategy?.rule_mode;
    if ((mode === 'rsi_h4' || mode === 'rsi_h4_zone') && strategy.bands) {
      chart.setRsiBands(strategy.bands);
      if (legendEl) legendEl.innerHTML = renderRsiBandLegend(strategy.bands);
    } else {
      chart.clearRsiBands();
      if (legendEl) legendEl.innerHTML = '';
    }
  } catch {
    chart.clearRsiBands();
    if (legendEl) legendEl.innerHTML = '';
  }
}

async function loadChart() {
  const data = await getCandles(state.period, activeMonth());
  chart.setData(data);
  chart.resetViewport();
  await syncChartStrategyBands();
  if (state.mode !== 'idle' && state.draft.time) {
    drawOverlayOnly();
  } else {
    refreshChartAnnotations();
  }
  requestAnimationFrame(() => chart.resize?.());
}

function renderSetups() {
  const items = setupsForList();
  const total = trainSetups().length;
  const monthN = monthChartSetups().length;
  els.setupCount.textContent =
    state.listFilterByMonth && isTrainChartPeriod() && total > items.length
      ? `${items.length}/${total}`
      : String(items.length);
  updateLabelTabCounts();
  els.setupList.innerHTML = '';

  if (!total) {
    els.setupList.innerHTML =
      '<li class="hint" style="padding:8px">Chưa có setup. Tag nến ở tab 「Nến quan trọng」 trước.</li>';
    return;
  }

  if (!items.length && state.listFilterByMonth && isTrainChartPeriod()) {
    els.setupList.innerHTML = `<li class="hint" style="padding:8px">Không có setup trong tháng ${state.trainMonth?.slice(5) || '—'}. Bỏ 「Lọc tháng」 để xem tất cả ${total} setup.</li>`;
    return;
  }

  if (!items.length) {
    els.setupList.innerHTML = '<li class="hint" style="padding:8px">Không có setup.</li>';
    return;
  }

  const sorted = [...items].sort((a, b) => a.entry_time.localeCompare(b.entry_time));
  for (const s of sorted) {
    const li = document.createElement('li');
    const selected = s.id === state.editingId || s.id === state.focusedSetupId;
    li.className = `setup-item ${s.direction}${selected ? ' selected' : ''}`;
    const resClass = s.result === 'win' ? 'win' : s.result === 'loss' ? 'loss' : '';
    const code = setupDisplayCode(s);
    const barCode = s.bar_code ? `<span class="setup-linked-bar">← ${s.bar_code}</span>` : '';
    const ctxCount = s.context_bar_count ?? s.context_bars?.length ?? 0;
    const qScore = s.quality_score != null ? `<span class="pill suggest">Q${s.quality_score}</span>` : '';
    li.innerHTML = `
      <div class="setup-top">
        <span class="entity-code">${code}</span>
        ${qScore}
        <span class="setup-dir">${s.direction.toUpperCase()}</span>
        <span class="setup-result ${resClass}">${(s.result || '?').toUpperCase()}</span>
        <span style="margin-left:auto;font-size:11px;color:#fbbf24">RR ${s.planned_rr ?? '—'}</span>
      </div>
      <div class="setup-meta">${s.entry_time?.slice(0, 16).replace('T', ' ')}${barCode ? '<br>' + barCode : ''}${(s.tags || []).length ? '<br>' + s.tags.join(' · ') : ''}${ctxCount ? `<br><span class="muted">${ctxCount} nến ngữ cảnh</span>` : ''}${(s.bar_tags || []).length ? ` · tag nến: ${s.bar_tags.join(', ')}` : ''}</div>
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

function viewTradeOnChart(trade) {
  state.focusedTradeKey = tradeKey(trade);
  state.focusedSetupId = null;
  chart.viewTrade(trade);
  renderBtTradeList();
  els.chartOverlayHint.textContent = `Lệnh ${trade.direction.toUpperCase()} — ${trade.result.toUpperCase()} · ${trade.pnl_pips} pips`;
  els.chartOverlayHint.classList.remove('hidden');
}

function renderBtTradeList() {
  renderBtTradesPanel();
}

async function refreshSetups() {
  const { setups } = await getSetups({
    summary: true,
    period: state.trainPeriod,
  });
  state.setups = setups || [];
  renderSetups();
  if (state.mode === 'idle' && isTrainChartPeriod() && !state.focusedSetupId) {
    refreshChartAnnotations();
  }
}

function buildSetupBody() {
  const bar = state.inspectedBar;
  const ctx = state.barContext;
  return {
    direction: state.direction,
    entry_time: isoFromUnix(state.draft.time),
    entry_price: Number(state.draft.entry),
    stop_loss: Number(els.fieldSL.value),
    take_profit: Number(els.fieldTP.value),
    note: state.meta.note || '',
    tags: state.meta.tags || [],
    bar_tags: ctx?.bar_tags || bar?.annotation?.tags || [],
    sequence_tags:
      ctx?.sequence_tags || (bar?.sequence_tags || []).map((t) => t.tag || t),
    annotation_id: ctx?.annotation_id || bar?.annotation?.id || null,
    train_period: state.trainPeriod,
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
    await loadMonthMeta();
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
  updateBtWorkspaceVisibility();
  updatePipelineUI();
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
  if (tabId === 'backtest') {
    const bt = state.btSelectedPeriods[0] || backtestPeriodIds()[0];
    if (bt && state.period !== bt) {
      switchPeriod(bt, { syncSidebar: false });
      return;
    }
  } else if (tabId === 'label' || tabId === 'analyze') {
    if (!isTrainChartPeriod(state.period)) {
      switchPeriod(state.trainPeriod, { syncSidebar: false });
      return;
    }
  }
  refreshChartAnnotations();
}

async function loadBacktestRuns() {
  try {
    const data = await getBacktests();
    state.btRuns = data.runs || [];
    if (!state.activeBtRunId) {
      const latest = state.btRuns[0];
      if (latest) state.activeBtRunId = latest.id;
    }
    await restoreActiveBacktests();
    renderBtSavedList();
    renderBtComparePanel();
  } catch (err) {
    console.warn('Load backtests failed:', err);
  }
}

async function restoreActiveBacktests() {
  const id = state.activeBtRunId;
  if (!id) return;
  if (state.btCache?.id === id) {
    renderBtTradeList();
    return;
  }
  try {
    const run = await getBacktest(id);
    if (run?.status === 'ok') {
      state.btCache = run;
      displayBacktestResults(run);
    }
  } catch {
    state.activeBtRunId = null;
    state.btCache = null;
  }
  renderBtTradeList();
}

function updateBtWorkspaceVisibility() {
  const open = state.sidebarTab === 'backtest';
  els.btWorkspace?.classList.toggle('hidden', !open);
  els.chartArea?.classList.toggle('bt-workspace-open', open && !state.btWorkspaceCollapsed);
  els.chartArea?.classList.toggle('bt-workspace-collapsed', open && state.btWorkspaceCollapsed);
  if (open) {
    requestAnimationFrame(() => chart.resize?.());
  }
}

function setBtWorkspaceTab(tabId) {
  state.btWorkspaceTab = tabId;
  document.querySelectorAll('.bt-ws-tab').forEach((btn) => {
    const active = btn.dataset.btPanel === tabId;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  const panels = {
    results: els.btPanelResults,
    trades: els.btPanelTrades,
    library: document.getElementById('btPanelLibrary'),
    compare: els.btPanelCompare,
  };
  for (const [id, panel] of Object.entries(panels)) {
    panel?.classList.toggle('hidden', id !== tabId);
    panel?.classList.toggle('active', id === tabId);
  }
  if (tabId === 'trades') renderBtTradesPanel();
  if (tabId === 'compare') renderBtComparePanel();
}

function toggleBtWorkspaceCollapsed() {
  state.btWorkspaceCollapsed = !state.btWorkspaceCollapsed;
  updateBtWorkspaceVisibility();
}

function updateBtSidebarSummary(data) {
  if (!els.btSidebarSummary) return;
  const text = renderBacktestSidebarSummary(data);
  els.btSidebarSummary.textContent = text;
  els.btSidebarSummary.classList.remove('pass', 'fail', 'muted');
  if (!data || data.status !== 'ok') {
    els.btSidebarSummary.classList.add('muted');
    return;
  }
  els.btSidebarSummary.classList.add(data.metrics?.pass ? 'pass' : 'fail');
}

function renderBtTradesPanel() {
  const trades = activeBtTrades();
  if (els.btCount) els.btCount.textContent = String(trades.length);
  if (!els.btPanelTrades) return;

  els.btPanelTrades.innerHTML = renderBacktestTradesPanel(trades, {
    focusedKey: state.focusedTradeKey,
  });

  els.btPanelTrades.querySelectorAll('[data-trade-key]').forEach((row) => {
    row.addEventListener('click', () => {
      const key = row.dataset.tradeKey;
      const trade = trades.find((t) => tradeKey(t) === key);
      if (trade) viewTradeOnChart(trade);
    });
  });
}

function displayBacktestResults(data) {
  if (!data) return;
  const label = data.period_label || data.period || 'Backtest';
  const stratYear = data.train_year || periodShortLabel(data.train_period || state.btStrategyPeriod);
  const title = `Backtest ${label}`;
  const subtitle = data.name
    ? `「${data.name}」 · Chiến lược train ${stratYear}`
    : `Chiến lược train ${stratYear}`;

  if (els.btPanelResults) {
    els.btPanelResults.innerHTML = renderBacktestView(data, { title, subtitle, includeTrades: false });
  }
  updateBtSidebarSummary(data);
  renderBtTradesPanel();
  updateBtWorkspaceVisibility();
}

function renderBtSavedList() {
  const listEl = els.btSavedList;
  const countEl = els.btSavedCount;
  if (!listEl) return;

  const items = state.btRuns || [];
  if (countEl) countEl.textContent = String(items.length);
  listEl.innerHTML = '';

  if (!items.length) {
    listEl.innerHTML =
      '<li class="hint" style="padding:8px">Chưa lưu backtest. Chạy và đặt tên để lưu lại.</li>';
    return;
  }

  for (const run of items) {
    const li = document.createElement('li');
    const m = run.metrics || {};
    const active = state.activeBtRunId === run.id;
    const checked = state.compareBtIds.includes(run.id);
    const pass = m.pass ? '✓' : '—';
    const periodLabel = run.period_label || run.period || '—';
    li.className = `setup-item bt-saved-item${active ? ' selected' : ''}`;
    li.innerHTML = `
      <div class="bt-saved-top">
        <input type="checkbox" class="bt-check" ${checked ? 'checked' : ''} title="Chọn so sánh">
        <span class="bt-saved-name">${run.name || run.id}</span>
        <button type="button" class="bt-saved-del" title="Xóa">✕</button>
      </div>
      <div class="setup-meta">${periodLabel} · ${(run.created_at || '').slice(0, 16).replace('T', ' ')} · WR ${Math.round((m.win_rate || 0) * 100)}% · PF ${m.profit_factor ?? '—'} · ${pass}</div>
    `;
    li.querySelector('.bt-check')?.addEventListener('change', (e) => {
      e.stopPropagation();
      toggleCompareRun(run.id, e.target.checked);
    });
    li.querySelector('.bt-saved-del')?.addEventListener('click', (e) => {
      e.stopPropagation();
      removeBacktestRun(run.id);
    });
    li.onclick = () => {
      activateBacktestRun(run.id);
      setBtWorkspaceTab('results');
    };
    listEl.appendChild(li);
  }
}

function toggleCompareRun(runId, checked) {
  const set = new Set(state.compareBtIds);
  if (checked) set.add(runId);
  else set.delete(runId);
  state.compareBtIds = [...set];
  renderBtSavedList();
  renderBtComparePanel();
  if (checked) setBtWorkspaceTab('compare');
}

async function removeBacktestRun(runId) {
  if (!confirm('Xóa backtest đã lưu này?')) return;
  await deleteBacktestRun(runId);
  state.compareBtIds = state.compareBtIds.filter((id) => id !== runId);
  if (state.activeBtRunId === runId) {
    state.activeBtRunId = null;
    state.btCache = null;
  }
  await loadBacktestRuns();
}

async function activateBacktestRun(runId) {
  const summary = state.btRuns.find((r) => r.id === runId);
  if (!summary) return;
  try {
    const run = await getBacktest(runId);
    state.btCache = run;
    state.activeBtRunId = runId;
    displayBacktestResults(run);
    renderBtSavedList();
    setBtWorkspaceTab('results');
    const periods = run.periods || (run.period ? run.period.split(',') : []);
    const chartPeriod = periods[0] || backtestPeriodIds()[0];
    if (state.period !== chartPeriod) {
      switchPeriod(chartPeriod, { syncSidebar: false });
      setSidebarTabUI('backtest');
    } else {
      state.focusedTradeKey = null;
      chart.resetViewport();
      refreshChartAnnotations();
      requestAnimationFrame(() => chart.resize?.());
    }
  } catch (err) {
    alert(`Không tải được backtest: ${err.message || err}`);
  }
}

function renderBtComparePanel() {
  const selected = state.btRuns.filter((r) => state.compareBtIds.includes(r.id));
  const html = renderBacktestCompare(selected);
  if (els.btPanelCompare) els.btPanelCompare.innerHTML = html;
}

async function runAnalyze() {
  const trainPeriod = els.analyzeTrainPeriod?.value || state.trainPeriod;
  const strategyId = els.analyzeStrategyType?.value || state.strategyId;
  const validationPeriod = els.analyzeValidationPeriod?.value || null;
  const stratMeta = strategyTypeMeta(strategyId);
  const stratLabel = stratMeta?.label || strategyId;
  els.analyzeResults.innerHTML = renderLoading(
    `Phân tích ${stratLabel} · train ${periodShortLabel(trainPeriod)}...`,
  );
  try {
    const raw = await analyze(trainPeriod, {
      optimize: true,
      strategyId,
      validationPeriod,
    });
    const data = raw.analysis
      ? {
          ...raw.analysis,
          optimization: raw.optimization,
          validation_period: raw.validation_period,
        }
      : raw;
    els.analyzeResults.innerHTML = renderAnalyzeView(data);
    await loadStrategies();
    await syncChartStrategyBands();
    renderBtStrategySelect();
  } catch (e) {
    els.analyzeResults.innerHTML = renderError(e.message);
  }
}

async function runBt() {
  const periods = state.btSelectedPeriods.length ? state.btSelectedPeriods : defaultBtPeriods();
  const trainPeriod = els.btStrategyPeriod?.value || state.btStrategyPeriod;
  const strategyId = els.btStrategyType?.value || state.btStrategyId;
  if (!periods.length) {
    alert('Chọn ít nhất một năm backtest.');
    return;
  }
  const saveName = els.btSaveName?.value?.trim() || null;
  const label = periods.map(periodShortLabel).join(' + ');
  const stratMeta = strategyTypeMeta(strategyId);
  const stratLabel = stratMeta?.label || strategyId;
  els.btPanelResults.innerHTML = renderLoading(
    `Backtest ${label} · ${stratLabel} train ${periodShortLabel(trainPeriod)}...`,
  );
  setBtWorkspaceTab('results');
  state.btWorkspaceCollapsed = false;
  updateBtWorkspaceVisibility();
  try {
    const data = await backtest(periods, {
      name: saveName,
      save: true,
      trainPeriod,
      strategyId,
    });
    state.btCache = data;
    if (data.saved_run?.id) {
      state.activeBtRunId = data.saved_run.id;
      if (els.btSaveName && saveName) els.btSaveName.value = '';
    }
    await loadBacktestRuns();
    displayBacktestResults(data);
    setBtWorkspaceTab('results');
    state.focusedTradeKey = null;
    const chartPeriod = periods[0];
    if (state.period !== chartPeriod) {
      await switchPeriod(chartPeriod, { syncSidebar: false });
    } else {
      chart.resetViewport();
      refreshChartAnnotations();
      requestAnimationFrame(() => chart.resize?.());
    }
  } catch (e) {
    if (els.btPanelResults) els.btPanelResults.innerHTML = renderError(e.message);
    updateBtSidebarSummary(null);
  }
}

function strategyTypeMeta(id) {
  return (state.strategyTypes || []).find((s) => s.id === id);
}

function defaultStrategyId() {
  return state.config?.default_strategy_id
    || state.strategyTypes?.[0]?.id
    || 'rsi_h4_zone';
}

function strategiesForType(strategyId) {
  return (state.strategies || []).filter(
    (s) => !s.catalog_only && (!s.strategy_id || s.strategy_id === strategyId),
  );
}

function renderStrategyTypeSelect(selectEl, selectedId, onChange) {
  if (!selectEl) return;
  const types = state.strategyTypes.length ? state.strategyTypes : state.config?.strategy_types || [];
  selectEl.innerHTML = '';
  for (const st of types) {
    const opt = document.createElement('option');
    opt.value = st.id;
    opt.textContent = st.label || st.name || st.id;
    if (st.id === selectedId) opt.selected = true;
    selectEl.appendChild(opt);
  }
  selectEl.onchange = () => {
    onChange(selectEl.value);
  };
}

function renderBtStrategySelect() {
  if (!els.btStrategyPeriod) return;
  const strategyId = els.btStrategyType?.value || state.btStrategyId;
  const matches = strategiesForType(strategyId);
  els.btStrategyPeriod.innerHTML = '';

  if (!matches.length) {
    for (const id of trainPeriodIds()) {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = `Train ${periodShortLabel(id)} (chưa analyze)`;
      if (id === state.btStrategyPeriod) opt.selected = true;
      els.btStrategyPeriod.appendChild(opt);
    }
  } else {
    for (const s of matches) {
      const opt = document.createElement('option');
      opt.value = s.train_period;
      const wr = s.win_rate_train != null ? ` · WR ${Math.round(s.win_rate_train * 100)}%` : '';
      opt.textContent = `Train ${s.train_year || periodShortLabel(s.train_period)}${wr}`;
      if (s.train_period === state.btStrategyPeriod) opt.selected = true;
      els.btStrategyPeriod.appendChild(opt);
    }
  }

  els.btStrategyPeriod.onchange = async () => {
    state.btStrategyPeriod = els.btStrategyPeriod.value;
    applySuggestedBtPeriod(state.btStrategyPeriod);
    await syncChartStrategyBands();
  };
}

async function loadStrategies() {
  try {
    const data = await getStrategies();
    state.strategies = data.strategies || [];
    const matches = strategiesForType(state.btStrategyId);
    if (
      matches.length
      && !matches.some((s) => s.train_period === state.btStrategyPeriod)
    ) {
      state.btStrategyPeriod = matches[matches.length - 1].train_period;
    }
    renderBtStrategySelect();
    applySuggestedBtPeriod(state.btStrategyPeriod);
    await syncChartStrategyBands();
  } catch (err) {
    console.warn('Load strategies failed:', err);
    renderBtStrategySelect();
  }
}

function renderBtYearPicker() {
  if (!els.btYearPicker) return;
  els.btYearPicker.innerHTML = '';
  for (const id of backtestPeriodIds()) {
    const cfg = periodCfg(id);
    const label = document.createElement('label');
    label.className = 'bt-year-option';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = id;
    input.checked = state.btSelectedPeriods.includes(id);
    input.onchange = () => {
      const selected = [...els.btYearPicker.querySelectorAll('input:checked')].map((el) => el.value);
      state.btSelectedPeriods = selected.length ? selected : defaultBtPeriods();
    };
    label.appendChild(input);
    label.append(` ${cfg?.year || periodShortLabel(id)}`);
    els.btYearPicker.appendChild(label);
  }
}

function renderAnalyzeTrainSelect() {
  if (!els.analyzeTrainPeriod) return;
  els.analyzeTrainPeriod.innerHTML = '';
  for (const id of trainPeriodIds()) {
    const cfg = periodCfg(id);
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = cfg?.label || `Train ${cfg?.year || id}`;
    if (id === state.trainPeriod) opt.selected = true;
    els.analyzeTrainPeriod.appendChild(opt);
  }
  els.analyzeTrainPeriod.onchange = () => {
    state.trainPeriod = els.analyzeTrainPeriod.value;
    syncAnalyzeValidationDefault();
  };
}

function renderAnalyzeValidationSelect() {
  if (!els.analyzeValidationPeriod) return;
  const suggested = suggestedBtPeriodForTrain(state.trainPeriod);
  els.analyzeValidationPeriod.innerHTML = '';
  for (const id of backtestPeriodIds()) {
    const cfg = periodCfg(id);
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = cfg?.label || `BT ${cfg?.year || id}`;
    if (id === (state.analyzeValidationPeriod || suggested)) opt.selected = true;
    els.analyzeValidationPeriod.appendChild(opt);
  }
  els.analyzeValidationPeriod.onchange = () => {
    state.analyzeValidationPeriod = els.analyzeValidationPeriod.value;
  };
}

function syncAnalyzeValidationDefault() {
  const suggested = suggestedBtPeriodForTrain(state.trainPeriod);
  if (!state.analyzeValidationPeriod && suggested) {
    state.analyzeValidationPeriod = suggested;
  }
  renderAnalyzeValidationSelect();
}

function renderAnalyzeStrategySelect() {
  renderStrategyTypeSelect(els.analyzeStrategyType, state.strategyId, (id) => {
    state.strategyId = id;
  });
}

function renderBtStrategyTypeSelect() {
  renderStrategyTypeSelect(els.btStrategyType, state.btStrategyId, async (id) => {
    state.btStrategyId = id;
    const matches = strategiesForType(id);
    if (matches.length) {
      state.btStrategyPeriod = matches[matches.length - 1].train_period;
    }
    renderBtStrategySelect();
    applySuggestedBtPeriod(state.btStrategyPeriod);
    await syncChartStrategyBands();
  });
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

  document.getElementById('toggleImportantBars').onchange = async (e) => {
    state.showImportantBars = e.target.checked;
    if (!e.target.checked) {
      hideBarInspect();
      els.chartHoverHint?.classList.add('hidden');
    }
    await loadImportantBars();
    renderImportantBarList();
    if (!state.showImportantBars) updateChartHint();
  };

  document.getElementById('btnCloseBarInspect')?.addEventListener('click', hideBarInspect);
  document.getElementById('btnSetupFromBar')?.addEventListener('click', () => startSetupFromInspectedBar());
  document.getElementById('btnSaveBarAnnot')?.addEventListener('click', () => saveBarAnnotationFromInspect());
  document.getElementById('btnDeleteBarAnnot')?.addEventListener('click', () => deleteBarAnnotationFromInspect());
  document.getElementById('btnSaveDetection')?.addEventListener('click', () => saveDetectionSettings());

  els.sidebarTabs.forEach((btn) => {
    btn.onclick = () => switchSidebarTab(btn.dataset.sidebar);
  });

  els.labelSubtabs?.forEach((btn) => {
    btn.onclick = () => switchLabelSubTab(btn.dataset.labelTab);
  });

  document.getElementById('toggleListMonthFilter')?.addEventListener('change', (e) => {
    state.listFilterByMonth = e.target.checked;
    const barsToggle = document.getElementById('toggleListMonthFilterBars');
    if (barsToggle) barsToggle.checked = e.target.checked;
    renderSetups();
    renderBarAnnotationList();
    updateLabelTabCounts();
  });

  document.getElementById('toggleListMonthFilterBars')?.addEventListener('change', (e) => {
    state.listFilterByMonth = e.target.checked;
    const setupToggle = document.getElementById('toggleListMonthFilter');
    if (setupToggle) setupToggle.checked = e.target.checked;
    renderSetups();
    renderBarAnnotationList();
    updateLabelTabCounts();
  });

  document.getElementById('btnAnalyze').onclick = () => runAnalyze();
  document.getElementById('btnBacktest').onclick = () => runBt();

  document.querySelectorAll('.bt-ws-tab').forEach((btn) => {
    btn.addEventListener('click', () => setBtWorkspaceTab(btn.dataset.btPanel));
  });
  document.getElementById('btnBtWorkspaceCollapse')?.addEventListener('click', toggleBtWorkspaceCollapsed);
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

let chartSplitReady = false;

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
  if (!chartSplitReady) {
    initChartSplit({
      chartBody: document.getElementById('chartBody'),
      rsiPanel: document.getElementById('rsiPanel'),
      splitterEl: document.getElementById('chartSplitter'),
      onResize: () => chart.resize?.(),
    });
    chartSplitReady = true;
  }
  uiReady = true;
}

async function loadAppData() {
  setLoading(true);
  try {
    state.config = await fetchWithRetry(() => getConfig());
    state.strategyTypes = state.config?.strategy_types || [];
    state.strategyId = defaultStrategyId();
    state.btStrategyId = state.strategyId;
    state.trainPeriod = defaultTrainPeriod();
    state.period = state.trainPeriod;
    state.btSelectedPeriods = [...defaultBtPeriods()];
    state.analyzeValidationPeriod = suggestedBtPeriodForTrain(state.trainPeriod);
    initDetectionSettings(state.config?.bar_detection);
    await loadTagPresets();
    renderTagCheckboxes();
    renderPeriodTabs();
    renderBtYearPicker();
    renderAnalyzeStrategySelect();
    renderBtStrategyTypeSelect();
    renderBtStrategySelect();
    await loadStrategies();
    renderAnalyzeTrainSelect();
    renderAnalyzeValidationSelect();
    if (state.config?.periods?.[state.period]) {
      els.periodBadge.textContent = state.config.periods[state.period].label;
    }
    setMode('idle');
    setLabelSubTabUI(state.labelSubTab);
    setSidebarTabUI(state.sidebarTab || 'label');
    setBtWorkspaceTab(state.btWorkspaceTab || 'results');
    updateBtWorkspaceVisibility();
    await loadMonthMeta();
    await fetchWithRetry(() => loadMonthData());
    await fetchWithRetry(() => loadBacktestRuns());
    await syncChartStrategyBands();
    updatePipelineUI();
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
