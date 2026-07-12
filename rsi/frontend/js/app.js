import { RsiZoneChart } from './chart.js';
import { initChartSplit } from './layout.js';

const $ = (id) => document.getElementById(id);

let chart;
let lastIndicators = null;
let lastStats = null;
let lastEvents = [];
let chartLoadedOnce = false;

function fmtTime(unixSec) {
  const d = new Date(unixSec * 1000);
  return d.toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
}

function fmtDate(iso) {
  if (!iso) return '—';
  return iso.slice(0, 10);
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function queryParams() {
  const start = $('dateStart').value;
  const end = $('dateEnd').value;
  const p = new URLSearchParams();
  if (start) p.set('start', start);
  if (end) p.set('end', end);
  return p;
}

function statsParams() {
  const p = queryParams();
  p.set('horizon_bars', $('paramHorizon').value);
  p.set('min_reversal_pips', $('paramMinPips').value);
  p.set('cooldown_bars', $('paramCooldown').value);
  return p;
}

function buildMarkers(events, show) {
  if (!show || !events?.length) return [];
  return events.map((e) => {
    const isLow = e.zone === 'low';
    const isHigh = e.zone === 'high';
    return {
      time: e.time,
      position: isLow ? 'belowBar' : 'aboveBar',
      color: e.reversed ? '#22c55e' : isLow ? '#ef4444' : '#f59e0b',
      shape: isLow ? 'arrowUp' : 'arrowDown',
      text: isLow ? 'RSI↑' : isHigh ? 'RSI↓' : '50',
    };
  });
}

function renderReportSummary(stats) {
  const zones = stats?.zones || {};
  const low = zones.low || {};
  const high = zones.high || {};
  const cfg = stats?.config || {};
  $('reportSummary').innerHTML = `
    <div class="summary-card">
      <div class="summary-label">Khoảng phân tích</div>
      <div class="summary-value" id="reportRange">—</div>
    </div>
    <div class="summary-card accent-red">
      <div class="summary-label">Vùng hỗ trợ RSI</div>
      <div class="summary-value">${low.reversal_rate ?? 0}% đảo chiều</div>
      <div class="summary-sub">${low.touches ?? 0} lần chạm · TB ${low.avg_move_pips ?? 0} pip</div>
    </div>
    <div class="summary-card accent-green">
      <div class="summary-label">Vùng kháng cự RSI</div>
      <div class="summary-value">${high.reversal_rate ?? 0}% đảo chiều</div>
      <div class="summary-sub">${high.touches ?? 0} lần chạm · TB ${high.avg_move_pips ?? 0} pip</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Tiêu chí đo</div>
      <div class="summary-value">${cfg.horizon_bars ?? 24} nến H1</div>
      <div class="summary-sub">≥ ${cfg.min_reversal_pips ?? 20} pip · cooldown ${cfg.cooldown_bars ?? 12}</div>
    </div>
  `;
}

function renderZoneTable(stats) {
  const tbody = $('zoneTable').querySelector('tbody');
  const zones = stats?.zones || {};
  const rows = ['low', 'mid', 'high'].map((key) => {
    const z = zones[key];
    if (!z) return '';
    const band = `${z.band?.[0] ?? ''}–${z.band?.[1] ?? ''}`;
    return `
      <tr class="zone-row-${key}">
        <td><strong>${z.label}</strong></td>
        <td>${band}</td>
        <td>${z.touches}</td>
        <td>${z.reversals ?? '—'}</td>
        <td class="rate">${key === 'mid' ? '—' : `${z.reversal_rate}%`}</td>
        <td>${z.avg_move_pips ?? '—'}</td>
        <td>${z.with_ema_alignment ?? '—'}</td>
        <td class="rate">${key === 'mid' ? '—' : `${z.aligned_reversal_rate}%`}</td>
        <td>${z.exit_signals ?? '—'}</td>
      </tr>`;
  });
  tbody.innerHTML = rows.join('');
}

function renderConditionTable(rows) {
  const tbody = $('conditionTable').querySelector('tbody');
  tbody.innerHTML = (rows || []).map((r) => `
    <tr>
      <td>${r.condition}</td>
      <td>${r.samples}</td>
      <td class="rate">${r.reversal_rate}%</td>
      <td class="note">${r.note}</td>
    </tr>
  `).join('');
}

function renderEventTable(events) {
  const tbody = $('eventTable').querySelector('tbody');
  lastEvents = events || [];
  tbody.innerHTML = lastEvents.map((e, i) => `
    <tr class="event-row" data-idx="${i}">
      <td class="mono">${fmtTime(e.time)}</td>
      <td><span class="tag zone-${e.zone}">${e.zone === 'low' ? 'Hỗ trợ' : e.zone === 'high' ? 'Kháng cự' : 'Vùng 50'}</span></td>
      <td class="mono">${e.rsi}</td>
      <td class="mono">${e.close.toFixed(5)}</td>
      <td><span class="tag ${e.reversed ? 'ok' : 'no'}">${e.reversed ? 'Có' : 'Không'}</span></td>
      <td class="mono">${e.move_pips ?? '—'}</td>
      <td>${e.ema_aligned ? 'Cùng chiều' : '—'}</td>
      <td>${e.h4_trend_up ? 'Tăng' : 'Giảm'}</td>
      <td>${e.exit_signal ? '✓' : '—'}</td>
    </tr>
  `).join('');

  tbody.querySelectorAll('.event-row').forEach((row) => {
    row.addEventListener('click', () => {
      const ev = lastEvents[Number(row.dataset.idx)];
      if (!ev) return;
      switchTab('chart');
      chart.focusTime(ev.time);
    });
  });
}

function renderReport(stats, rangeText) {
  lastStats = stats;
  renderReportSummary(stats);
  renderZoneTable(stats);
  renderConditionTable(stats.conditions);
  renderEventTable(stats.events);
  const rangeEl = $('reportSummary').querySelector('#reportRange');
  if (rangeEl) rangeEl.textContent = rangeText;
}

async function loadChart({ fit = false } = {}) {
  const chartData = await fetchJson(`/api/chart?${queryParams()}`);
  lastIndicators = chartData.indicators;
  chart.setData(chartData, { fit: fit || !chartLoadedOnce });
  chartLoadedOnce = true;

  if (lastStats) {
    chart.setMarkers(buildMarkers(lastStats.events, $('toggleMarkers').checked));
  }

  chart.applyEmaVisibility($('toggleEma50').checked, $('toggleEma200').checked, lastIndicators);

  return chartData;
}

async function loadStats() {
  const stats = await fetchJson(`/api/zone-stats?${statsParams()}`);
  lastStats = stats;
  chart?.setMarkers(buildMarkers(stats.events, $('toggleMarkers').checked));
  return stats;
}

async function loadAll({ fitChart = false } = {}) {
  $('dataRange').textContent = 'Đang tải…';
  const [chartData, stats] = await Promise.all([
    loadChart({ fit: fitChart }),
    loadStats(),
  ]);

  const rangeText =
    `${chartData.count.toLocaleString()} nến · ${fmtDate(chartData.range?.start)} → ${fmtDate(chartData.range?.end)}`;
  $('dataRange').textContent = rangeText;
  renderReport(stats, rangeText);
}

function switchTab(tab) {
  document.querySelectorAll('.main-tab').forEach((btn) => {
    const active = btn.dataset.tab === tab;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  $('viewChart').classList.toggle('hidden', tab !== 'chart');
  $('viewChart').classList.toggle('active', tab === 'chart');
  $('viewReport').classList.toggle('hidden', tab !== 'report');
  $('viewReport').classList.toggle('active', tab === 'report');
  if (tab === 'chart') {
    requestAnimationFrame(() => chart?.resize());
  }
}

async function init() {
  chart = new RsiZoneChart($('chartMain'), $('chartRsi'), {
    wrapEl: $('chartWrap'),
    bodyEl: $('chartBody'),
    onCrosshair: (info) => {
      const el = $('crosshairInfo');
      if (!info?.candle) {
        el.textContent = 'Kéo biểu đồ giá để pan · cuộn chuột để zoom';
        return;
      }
      const c = info.candle;
      el.textContent =
        `${fmtTime(c.time)} · O ${c.open} H ${c.high} L ${c.low} C ${c.close}` +
        (info.rsi != null ? ` · RSI H4 ${info.rsi.toFixed(1)}` : '');
    },
  });
  chart.mount();

  initChartSplit({
    chartBody: $('chartBody'),
    rsiPanel: $('rsiPanel'),
    splitterEl: $('chartSplitter'),
    onResize: () => chart.resize(),
  });

  document.querySelectorAll('.main-tab').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  const info = await fetchJson('/api/info');
  if (info.start) {
    $('dateStart').value = info.start.slice(0, 10);
    $('dateEnd').value = info.end.slice(0, 10);
  }

  $('btnLoad').addEventListener('click', () => loadAll({ fitChart: true }).catch(alert));
  $('btnRefreshStats').addEventListener('click', () => loadStats().then((stats) => {
    const rangeText = $('dataRange').textContent;
    renderReport(stats, rangeText);
  }).catch(alert));

  $('btnZoomIn').addEventListener('click', () => chart.zoomIn());
  $('btnZoomOut').addEventListener('click', () => chart.zoomOut());
  $('btnFit').addEventListener('click', () => chart.fitContent());
  $('btnLatest').addEventListener('click', () => chart.scrollToLatest());

  $('toggleEma50').addEventListener('change', () => {
    chart.applyEmaVisibility($('toggleEma50').checked, $('toggleEma200').checked, lastIndicators);
  });
  $('toggleEma200').addEventListener('change', () => {
    chart.applyEmaVisibility($('toggleEma50').checked, $('toggleEma200').checked, lastIndicators);
  });
  $('toggleMarkers').addEventListener('change', () => {
    chart.setMarkers(buildMarkers(lastStats?.events, $('toggleMarkers').checked));
  });

  await loadAll({ fitChart: true });
}

init().catch((err) => {
  console.error(err);
  $('dataRange').textContent = `Lỗi: ${err.message}`;
});
