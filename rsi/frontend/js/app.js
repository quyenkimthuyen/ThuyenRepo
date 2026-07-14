import { RsiZoneChart } from './chart.js';
import { initChartSplit } from './layout.js';

const $ = (id) => document.getElementById(id);

let chart;
let lastIndicators = null;
let lastStats = null;
let lastRecommended = null;
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

function lowSupportEvents(events) {
  return (events || []).filter((e) => e.zone === 'low');
}

function buildMarkers(events, show) {
  if (!show || !events?.length) return [];
  return lowSupportEvents(events).map((e) => ({
    time: e.time,
    position: 'belowBar',
    color: e.reversed ? '#22c55e' : '#3b82f6',
    shape: 'arrowUp',
    text: 'Long',
  }));
}

function renderRecommended(rec) {
  const el = $('recommendedContent');
  if (!el || !rec) return;
  const setup = rec.setup || {};
  const perf = rec.performance || {};
  const notes = (setup.notes || []).map((n) => `<li>${n}</li>`).join('');
  el.innerHTML = `
    <div class="recommended-hero">
      <div class="recommended-title">${setup.label || '—'}</div>
      <div class="recommended-metrics">
        <div class="metric"><span class="metric-val">${perf.expectancy_r ?? 0}R</span><span class="metric-lbl">Expectancy</span></div>
        <div class="metric"><span class="metric-val">${perf.profit_factor ?? 0}</span><span class="metric-lbl">Profit factor</span></div>
        <div class="metric"><span class="metric-val">${perf.win_rate ?? 0}%</span><span class="metric-lbl">Win rate</span></div>
        <div class="metric"><span class="metric-val">${perf.trades ?? 0}</span><span class="metric-lbl">Lệnh</span></div>
        <div class="metric"><span class="metric-val">+${perf.total_pips ?? 0}</span><span class="metric-lbl">Tổng pip</span></div>
      </div>
      <ul class="recommended-rules">${notes}</ul>
      <div class="recommended-params mono">
        SL ${setup.stop_loss_pips} pip · TP ${setup.take_profit_r}R · Horizon ${setup.max_bars} nến H1 · Spread ${setup.spread_pips} pip
      </div>
    </div>`;
}

function renderRejectedTable(rec) {
  const tbody = $('rejectedTable')?.querySelector('tbody');
  if (!tbody || !rec) return;
  const skipped = (rec.skipped || []).map((s) => `
    <tr class="rejected-row">
      <td>${s.id}</td>
      <td>—</td>
      <td>—</td>
      <td>—</td>
      <td class="note">${s.reason}</td>
    </tr>`);
  const alts = (rec.rejected_alternatives || []).map(({ label, result: r }) => `
    <tr class="rejected-row">
      <td>${label}</td>
      <td>${r?.trades ?? 0}</td>
      <td>${r?.expectancy_r ?? 0}R</td>
      <td>${r?.profit_factor ?? '—'}</td>
      <td class="note">Expectancy ${(r?.expectancy_r ?? 0) <= 0 ? '≤ 0' : 'thấp'} — không dùng</td>
    </tr>`);
  tbody.innerHTML = [...alts, ...skipped].join('');
}

function renderWalkForwardTable(wf) {
  const tbody = $('walkForwardTable')?.querySelector('tbody');
  const verdict = $('walkForwardVerdict');
  if (!tbody || !wf) return;
  tbody.innerHTML = ['train', 'test'].map((key) => {
    const p = wf[key];
    if (!p?.valid) {
      return `<tr><td>${key === 'train' ? 'Train' : 'Test'}</td><td colspan="5">Không đủ dữ liệu</td></tr>`;
    }
    return `
      <tr>
        <td><strong>${key === 'train' ? 'Train' : 'Test'}</strong></td>
        <td>${p.trades ?? 0}</td>
        <td class="rate">${p.win_rate ?? 0}%</td>
        <td class="rate">${p.expectancy_r ?? 0}R</td>
        <td>${p.profit_factor ?? '—'}</td>
        <td class="mono">${p.total_pips >= 0 ? '+' : ''}${p.total_pips ?? 0}</td>
      </tr>`;
  }).join('');
  if (verdict && wf.comparison) {
    const c = wf.comparison;
    const ok = c.stable ? 'Edge giữ được ở giai đoạn test' : 'Cần theo dõi thêm';
    verdict.textContent =
      `Δ Expectancy ${c.expectancy_r_delta >= 0 ? '+' : ''}${c.expectancy_r_delta}R · Δ Win% ${c.win_rate_delta >= 0 ? '+' : ''}${c.win_rate_delta}% — ${ok}`;
  }
}

function renderReportSummary(stats, rangeText) {
  const low = stats?.zones?.low || {};
  const el = $('reportSummary');
  if (!el) return;
  el.innerHTML = `
    <div class="summary-card">
      <div class="summary-label">Khoảng phân tích</div>
      <div class="summary-value">${rangeText || '—'}</div>
    </div>
    <div class="summary-card accent-red">
      <div class="summary-label">Vùng hỗ trợ — chạm vùng</div>
      <div class="summary-value">${low.reversal_rate ?? 0}% đảo chiều</div>
      <div class="summary-sub">${low.touches ?? 0} lần chạm · TB MAE ${low.avg_mae_pips ?? 0} · MFE ${low.avg_mfe_pips ?? 0}</div>
    </div>`;
}

function renderMaeMfeTable(maeMfe) {
  const tbody = $('maeMfeTable')?.querySelector('tbody');
  if (!tbody || !maeMfe) return;
  const m = maeMfe.touch || {};
  const surv = m.sl_survival || {};
  tbody.innerHTML = `
    <tr>
      <td><strong>Chạm vùng (long)</strong></td>
      <td>${m.samples ?? 0}</td>
      <td class="mono">${m.avg_mae ?? 0}</td>
      <td class="mono">${m.avg_mfe ?? 0}</td>
      <td class="rate">${surv['20'] ?? 0}%</td>
      <td class="rate">${surv['25'] ?? 0}%</td>
      <td class="rate">${surv['30'] ?? 0}%</td>
    </tr>`;
}

function renderEventTable(events) {
  const tbody = $('eventTable')?.querySelector('tbody');
  if (!tbody) return;
  lastEvents = lowSupportEvents(events);
  tbody.innerHTML = lastEvents.map((e, i) => `
    <tr class="event-row" data-idx="${i}">
      <td class="mono">${fmtTime(e.time)}</td>
      <td class="mono">${e.rsi}</td>
      <td class="mono">${e.close.toFixed(5)}</td>
      <td><span class="tag ${e.reversed ? 'ok' : 'no'}">${e.reversed ? 'Có' : 'Không'}</span></td>
      <td class="mono">${e.mae_pips ?? '—'}</td>
      <td class="mono">${e.mfe_pips ?? '—'}</td>
      <td>${e.h4_trend_up ? 'Tăng' : 'Giảm'}</td>
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

function renderReport(stats, recommended, rangeText) {
  lastStats = stats;
  lastRecommended = recommended;
  renderRecommended(recommended);
  renderWalkForwardTable(recommended?.walk_forward);
  renderRejectedTable(recommended);
  renderReportSummary(stats, rangeText);
  renderMaeMfeTable(stats?.mae_mfe);
  renderEventTable(stats?.events);
}

async function loadChart({ fit = false } = {}) {
  const chartData = await fetchJson(`/api/chart?${queryParams()}`);
  lastIndicators = chartData.indicators;
  chart.setData(chartData, { fit: fit || !chartLoadedOnce });
  chartLoadedOnce = true;
  chart.setMarkers(buildMarkers(lastStats?.events, $('toggleMarkers').checked));
  chart.applyEmaVisibility($('toggleEma50').checked, $('toggleEma200').checked, lastIndicators);
  return chartData;
}

async function loadStats() {
  const p = queryParams();
  p.set('split_date', $('paramSplitDate').value);
  const [stats, recommended] = await Promise.all([
    fetchJson(`/api/zone-stats?${p}`),
    fetchJson(`/api/recommended-setup?${p}`),
  ]);
  lastStats = stats;
  lastRecommended = recommended;
  chart?.setMarkers(buildMarkers(stats.events, $('toggleMarkers').checked));
  return { stats, recommended };
}

async function loadAll({ fitChart = false } = {}) {
  $('dataRange').textContent = 'Đang tải…';
  const [chartData, { stats, recommended }] = await Promise.all([
    loadChart({ fit: fitChart }),
    loadStats(),
  ]);
  const rangeText =
    `${chartData.count.toLocaleString()} nến · ${fmtDate(chartData.range?.start)} → ${fmtDate(chartData.range?.end)}`;
  $('dataRange').textContent = rangeText;
  renderReport(stats, recommended, rangeText);
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
  if (tab === 'chart') requestAnimationFrame(() => chart?.resize());
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
  $('btnRefreshStats').addEventListener('click', () => loadStats().then(({ stats, recommended }) => {
    renderReport(stats, recommended, $('dataRange').textContent);
  }).catch(alert));

  $('paramSplitDate')?.addEventListener('change', () => {
    if ($('viewReport').classList.contains('active')) {
      loadStats().then(({ stats, recommended }) =>
        renderReport(stats, recommended, $('dataRange').textContent)).catch(alert);
    }
  });

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

  await loadAll({ fitChart: false });
}

init().catch((err) => {
  console.error(err);
  $('dataRange').textContent = `Lỗi: ${err.message}`;
});
