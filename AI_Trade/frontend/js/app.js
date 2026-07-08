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

const state = {
  period: 'train',
  direction: 'long',
  step: 'entry',
  draft: { entry: null, sl: null, tp: null, time: null },
  editingId: null,
  setups: [],
  config: null,
  labelAllowed: true,
};

const els = {
  periodTabs: document.getElementById('periodTabs'),
  periodBadge: document.getElementById('periodBadge'),
  labelHint: document.getElementById('labelHint'),
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
  analysisOut: document.getElementById('analysisOut'),
  backtestOut: document.getElementById('backtestOut'),
};

const chart = new TradeChart(
  document.getElementById('chartMain'),
  document.getElementById('chartRsi'),
  { onClick: handleChartClick, onLevelDrag: handleLevelDrag },
);

function parseTagsFromField() {
  return els.fieldTags.value
    .split(/[,;]+/)
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
}

function setTagsToField(tags) {
  const unique = [...new Set(tags.map((t) => t.trim().toLowerCase()).filter(Boolean))];
  els.fieldTags.value = unique.join(', ');
  syncTagChips();
}

function toggleTag(tagId) {
  const tags = new Set(parseTagsFromField());
  if (tags.has(tagId)) tags.delete(tagId);
  else tags.add(tagId);
  setTagsToField([...tags]);
}

function syncTagChips() {
  const active = new Set(parseTagsFromField());
  els.tagPresets?.querySelectorAll('.chip[data-tag]').forEach((chip) => {
    chip.classList.toggle('active', active.has(chip.dataset.tag));
  });
}

function applyNotePreset(note) {
  els.fieldNote.value = note.text;
  if (note.tags?.length) {
    const merged = new Set([...parseTagsFromField(), ...note.tags]);
    setTagsToField([...merged]);
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

function isoFromUnix(sec) {
  return new Date(sec * 1000).toISOString();
}

function setDirectionUi(direction) {
  document.getElementById('btnLong').classList.toggle('active', direction === 'long');
  document.getElementById('btnShort').classList.toggle('active', direction === 'short');
  state.direction = direction;
}

function setLabelHint() {
  if (state.editingId) {
    els.labelHint.textContent =
      'Đang sửa setup — kéo đường Entry/SL/TP hoặc chỉnh input, rồi bấm Cập nhật.';
    return;
  }
  els.labelHint.textContent = state.labelAllowed
    ? 'Click: Entry → SL → TP. Kéo đường để chỉnh giá. Click setup đã lưu để sửa.'
    : 'Chế độ xem — chuyển về Train để label hoặc sửa setup.';
}

function resetDraft() {
  state.draft = { entry: null, sl: null, tp: null, time: null };
  state.editingId = null;
  state.step = 'entry';
  els.fieldTags.value = '';
  els.fieldNote.value = '';
  syncTagChips();
  els.btnSave.textContent = 'Lưu setup';
  updateStepUI();
  syncFields();
  chart.clearOverlay();
  chart.clearFocus();
  els.btnSave.disabled = true;
  setLabelHint();
  renderSetups();
}

function updateStepUI() {
  document.querySelectorAll('.step').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.step === state.step);
  });
}

function focusDraftOnChart() {
  if (state.draft.time == null) return;
  chart.focusSetup({
    time: state.draft.time,
    entry: state.draft.entry,
    sl: Number(els.fieldSL.value) || state.draft.sl,
    tp: Number(els.fieldTP.value) || state.draft.tp,
  });
}

function syncFields() {
  els.fieldEntry.value = state.draft.entry ?? '';
  els.fieldSL.value = state.draft.sl ?? '';
  els.fieldTP.value = state.draft.tp ?? '';
  els.fieldTime.value = state.draft.time ? isoFromUnix(state.draft.time) : '';
  chart.setOverlay({
    entry: state.draft.entry,
    sl: Number(els.fieldSL.value) || state.draft.sl,
    tp: Number(els.fieldTP.value) || state.draft.tp,
    direction: state.direction,
  });
  if (state.draft.entry != null) {
    focusDraftOnChart();
  }
  validateSave();
}

function canEditLevels() {
  return state.labelAllowed || state.editingId;
}

function validateSave() {
  const sl = Number(els.fieldSL.value);
  const tp = Number(els.fieldTP.value);
  const ok =
    canEditLevels() &&
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
  if (!canEditLevels()) return;
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
  focusDraftOnChart();
  validateSave();
}

function handleChartClick({ time, candle, price }) {
  if (!state.labelAllowed || state.editingId) return;

  if (state.step === 'entry') {
    state.draft.time = time;
    state.draft.entry = candle.close;
    state.step = 'sl';
    const defaultSl =
      state.direction === 'long' ? candle.close - 0.003 : candle.close + 0.003;
    state.draft.sl = Number(defaultSl.toFixed(5));
    els.fieldSL.value = state.draft.sl;
    updateStepUI();
    syncFields();
    return;
  }

  if (state.step === 'sl') {
    state.draft.sl = Number(price.toFixed(5));
    els.fieldSL.value = state.draft.sl;
    state.step = 'tp';
    const risk = Math.abs(state.draft.entry - state.draft.sl);
    const defaultTp =
      state.direction === 'long'
        ? state.draft.entry + risk * 2
        : state.draft.entry - risk * 2;
    state.draft.tp = Number(defaultTp.toFixed(5));
    els.fieldTP.value = state.draft.tp;
    updateStepUI();
    syncFields();
    return;
  }

  if (state.step === 'tp') {
    state.draft.tp = Number(price.toFixed(5));
    els.fieldTP.value = state.draft.tp;
    syncFields();
  }
}

function renderPeriodTabs() {
  els.periodTabs.innerHTML = '';
  const periods = state.config.periods;
  for (const [key, cfg] of Object.entries(periods)) {
    const btn = document.createElement('button');
    btn.className = `period-tab${key === state.period ? ' active' : ''}${key === 'test' ? ' test' : ''}`;
    btn.textContent = `${cfg.label}`;
    btn.onclick = () => switchPeriod(key);
    els.periodTabs.appendChild(btn);
  }
}

async function switchPeriod(period) {
  state.period = period;
  state.labelAllowed = period === 'train';
  els.periodBadge.textContent = state.config.periods[period].label;
  renderPeriodTabs();
  resetDraft();
  await loadChart();
  setLabelHint();
}

async function loadChart() {
  const data = await getCandles(state.period);
  chart.setData(data);
  if (state.editingId && state.draft.time) {
    focusDraftOnChart();
    syncFields();
  }
}

async function selectSetup(setup) {
  const targetPeriod = setup.period || 'train';
  if (targetPeriod !== 'train') {
    alert('Chỉ có thể sửa setup trong năm Train (2022).');
    return;
  }

  if (state.period !== targetPeriod) {
    state.period = targetPeriod;
    state.labelAllowed = true;
    els.periodBadge.textContent = state.config.periods[targetPeriod].label;
    renderPeriodTabs();
    await loadChart();
  }

  state.editingId = setup.id;
  state.direction = setup.direction;
  state.step = 'tp';
  state.draft = {
    time: Math.floor(new Date(setup.entry_time).getTime() / 1000),
    entry: setup.entry_price,
    sl: setup.stop_loss,
    tp: setup.take_profit,
  };

  setDirectionUi(setup.direction);
  els.fieldTags.value = (setup.tags || []).join(', ');
  els.fieldNote.value = setup.note || '';
  syncTagChips();
  els.btnSave.textContent = 'Cập nhật setup';
  updateStepUI();
  syncFields();
  setLabelHint();
  renderSetups();
}

function renderSetups() {
  els.setupCount.textContent = String(state.setups.length);
  els.setupList.innerHTML = '';
  const sorted = [...state.setups].sort((a, b) => a.entry_time.localeCompare(b.entry_time));
  for (const s of sorted) {
    const li = document.createElement('li');
    li.className = `setup-item ${s.direction}${s.id === state.editingId ? ' selected' : ''}`;
    li.innerHTML = `
      <div><strong>${s.direction.toUpperCase()}</strong> · RR ${s.planned_rr ?? '-'} · <span>${s.result ?? '?'}</span></div>
      <div class="setup-meta">${s.entry_time?.slice(0, 16)}${(s.tags || []).length ? ' · ' + (s.tags || []).join(', ') : ''}</div>
    `;
    li.onclick = () => selectSetup(s);
    const del = document.createElement('button');
    del.className = 'btn danger';
    del.textContent = 'Xóa';
    del.style.marginTop = '6px';
    del.onclick = async (e) => {
      e.stopPropagation();
      if (state.editingId === s.id) resetDraft();
      await deleteSetup(s.id);
      await refreshSetups();
    };
    li.appendChild(del);
    els.setupList.appendChild(li);
  }
}

async function refreshSetups() {
  const { setups } = await getSetups();
  state.setups = setups;
  renderSetups();
}

function buildSetupBody() {
  const tags = parseTagsFromField();
  return {
    direction: state.direction,
    entry_time: isoFromUnix(state.draft.time),
    entry_price: state.draft.entry,
    stop_loss: Number(els.fieldSL.value),
    take_profit: Number(els.fieldTP.value),
    note: els.fieldNote.value,
    tags,
  };
}

async function onSave() {
  const body = buildSetupBody();
  if (state.editingId) {
    await updateSetup(state.editingId, body);
  } else {
    await saveSetup(body);
  }
  await refreshSetups();
  resetDraft();
}

function bindUI() {
  document.getElementById('btnLong').onclick = () => {
    setDirectionUi('long');
    if (!state.editingId) resetDraft();
    else syncFields();
  };
  document.getElementById('btnShort').onclick = () => {
    setDirectionUi('short');
    if (!state.editingId) resetDraft();
    else syncFields();
  };

  document.querySelectorAll('.step').forEach((btn) => {
    btn.onclick = () => {
      if (state.editingId) return;
      state.step = btn.dataset.step;
      updateStepUI();
    };
  });

  els.fieldSL.oninput = () => {
    state.draft.sl = Number(els.fieldSL.value);
    syncFields();
  };
  els.fieldTP.oninput = () => {
    state.draft.tp = Number(els.fieldTP.value);
    syncFields();
  };
  els.fieldTags.oninput = () => syncTagChips();

  document.getElementById('btnSave').onclick = onSave;
  document.getElementById('btnReset').onclick = resetDraft;

  document.getElementById('toggleEma50').onchange = (e) => chart.toggleEma50(e.target.checked);
  document.getElementById('toggleEma200').onchange = (e) => chart.toggleEma200(e.target.checked);
  document.getElementById('toggleRsi').onchange = (e) => chart.toggleRsi(e.target.checked);

  document.getElementById('btnAnalyze').onclick = async () => {
    els.analysisOut.textContent = 'Đang phân tích...';
    try {
      const res = await analyze();
      els.analysisOut.textContent = JSON.stringify(res, null, 2);
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
    const res = await backtest(period);
    els.backtestOut.textContent = JSON.stringify(res, null, 2);
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
  setLabelHint();
  await loadChart();
  await refreshSetups();
}

boot().catch((err) => {
  document.body.innerHTML = `<pre style="color:#f87171;padding:20px">Boot failed: ${err.message}\n\nChạy: python scripts/fetch_data.py</pre>`;
});
