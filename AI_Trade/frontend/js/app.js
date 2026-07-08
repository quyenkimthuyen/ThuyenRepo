import {
  analyze,
  backtest,
  deleteSetup,
  getCandles,
  getConfig,
  getSetups,
  saveSetup,
} from './api.js';
import { TradeChart } from './chart.js';

const state = {
  period: 'train',
  direction: 'long',
  step: 'entry',
  draft: { entry: null, sl: null, tp: null, time: null },
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
  btnSave: document.getElementById('btnSave'),
  analysisOut: document.getElementById('analysisOut'),
  backtestOut: document.getElementById('backtestOut'),
};

const chart = new TradeChart(
  document.getElementById('chartMain'),
  document.getElementById('chartRsi'),
  { onClick: handleChartClick, onLevelDrag: handleLevelDrag },
);

function isoFromUnix(sec) {
  return new Date(sec * 1000).toISOString();
}

function resetDraft() {
  state.draft = { entry: null, sl: null, tp: null, time: null };
  state.step = 'entry';
  updateStepUI();
  syncFields();
  chart.clearOverlay();
  els.btnSave.disabled = true;
}

function updateStepUI() {
  document.querySelectorAll('.step').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.step === state.step);
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
  validateSave();
}

function validateSave() {
  const sl = Number(els.fieldSL.value);
  const tp = Number(els.fieldTP.value);
  const ok =
    state.labelAllowed &&
    state.draft.entry != null &&
    state.draft.time != null &&
    !Number.isNaN(sl) &&
    !Number.isNaN(tp) &&
    sl > 0 &&
    tp > 0;
  if (ok && state.direction === 'long') {
    els.btnSave.disabled = !(sl < state.draft.entry && tp > state.draft.entry);
  } else if (ok && state.direction === 'short') {
    els.btnSave.disabled = !(sl > state.draft.entry && tp < state.draft.entry);
  } else {
    els.btnSave.disabled = true;
  }
}

function handleLevelDrag({ role, price }) {
  if (!state.labelAllowed) return;
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
}

function handleChartClick({ time, candle, price }) {
  if (!state.labelAllowed) return;

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
  els.labelHint.textContent = state.labelAllowed
    ? 'Click: Entry → SL → TP. Sau đó kéo các đường lên/xuống để chỉnh giá.'
    : 'Chế độ xem — không thể thêm setup. Chuyển về Train để label.';
  els.periodBadge.textContent = state.config.periods[period].label;
  renderPeriodTabs();
  resetDraft();
  await loadChart();
}

async function loadChart() {
  const data = await getCandles(state.period);
  chart.setData(data);
}

function renderSetups() {
  els.setupCount.textContent = String(state.setups.length);
  els.setupList.innerHTML = '';
  const sorted = [...state.setups].sort((a, b) => a.entry_time.localeCompare(b.entry_time));
  for (const s of sorted) {
    const li = document.createElement('li');
    li.className = `setup-item ${s.direction}`;
    li.innerHTML = `
      <div><strong>${s.direction.toUpperCase()}</strong> · RR ${s.planned_rr ?? '-'} · <span>${s.result ?? '?'}</span></div>
      <div class="setup-meta">${s.entry_time?.slice(0, 16)}${(s.tags || []).length ? ' · ' + (s.tags || []).join(', ') : ''}</div>
    `;
    li.onclick = () => {
      const t = Math.floor(new Date(s.entry_time).getTime() / 1000);
      chart.scrollToTime(t);
    };
    const del = document.createElement('button');
    del.className = 'btn danger';
    del.textContent = 'Xóa';
    del.style.marginTop = '6px';
    del.onclick = async (e) => {
      e.stopPropagation();
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

async function onSave() {
  const tags = els.fieldTags.value
    .split(/[,;]+/)
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
  const body = {
    direction: state.direction,
    entry_time: isoFromUnix(state.draft.time),
    entry_price: state.draft.entry,
    stop_loss: Number(els.fieldSL.value),
    take_profit: Number(els.fieldTP.value),
    note: els.fieldNote.value,
    tags,
  };
  await saveSetup(body);
  await refreshSetups();
  resetDraft();
}

function bindUI() {
  document.getElementById('btnLong').onclick = (e) => {
    document.getElementById('btnLong').classList.add('active');
    document.getElementById('btnShort').classList.remove('active');
    state.direction = 'long';
    resetDraft();
  };
  document.getElementById('btnShort').onclick = () => {
    document.getElementById('btnShort').classList.add('active');
    document.getElementById('btnLong').classList.remove('active');
    state.direction = 'short';
    resetDraft();
  };

  document.querySelectorAll('.step').forEach((btn) => {
    btn.onclick = () => {
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
  await loadChart();
  await refreshSetups();
}

boot().catch((err) => {
  document.body.innerHTML = `<pre style="color:#f87171;padding:20px">Boot failed: ${err.message}\n\nChạy: python scripts/fetch_data.py</pre>`;
});
