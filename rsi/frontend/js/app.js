import { RsiZoneChart } from './chart.js';

const $ = (id) => document.getElementById(id);

let chart;
let lastIndicators = null;
let lastEvents = [];

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
    const reversed = e.reversed;
    return {
      time: e.time,
      position: isLow ? 'belowBar' : 'aboveBar',
      color: reversed ? '#22c55e' : isLow ? '#ef4444' : '#f59e0b',
      shape: isLow ? 'arrowUp' : 'arrowDown',
      text: isLow ? 'RSI↑' : isHigh ? 'RSI↓' : '50',
    };
  });
}

function renderZoneSummary(data) {
  const el = $('zoneSummary');
  const zones = data?.zones || {};
  const cards = ['low', 'mid', 'high'].map((key) => {
    const z = zones[key];
    if (!z) return '';
    return `
      <div class="zone-card ${key}">
        <h3>${z.label}</h3>
        <div class="stat-row"><span>Lần chạm vùng</span><strong>${z.touches}</strong></div>
        <div class="stat-row"><span>Đảo chiều giá</span><strong>${z.reversals} (${z.reversal_rate}%)</strong></div>
        <div class="stat-row"><span>TB biên độ (pip)</span><strong>${z.avg_move_pips}</strong></div>
        ${key !== 'mid' ? `
        <div class="stat-row"><span>EMA cùng chiều</span><strong>${z.with_ema_alignment}</strong></div>
        <div class="stat-row"><span>Đảo chiều khi EMA OK</span><strong>${z.aligned_reversal_rate}%</strong></div>
        <div class="stat-row"><span>Tín hiệu rời vùng</span><strong>${z.exit_signals}</strong></div>
        ` : ''}
      </div>`;
  });
  el.innerHTML = cards.join('');
}

function renderConditions(rows) {
  const el = $('conditionTable');
  el.innerHTML = (rows || []).map((r) => `
    <div class="cond-row">
      <div class="cond-name">${r.condition}</div>
      <div class="cond-meta">
        <span>${r.samples} mẫu</span>
        <span class="cond-rate">${r.reversal_rate}%</span>
      </div>
      <div class="cond-note">${r.note}</div>
    </div>
  `).join('');
}

function renderEvents(events) {
  const el = $('eventList');
  lastEvents = events || [];
  el.innerHTML = lastEvents.slice(0, 200).map((e, i) => `
    <div class="event-item" data-idx="${i}">
      <div class="time">${fmtTime(e.time)}</div>
      <div>RSI H4: <strong>${e.rsi}</strong> · Close: ${e.close.toFixed(5)}</div>
      <div class="tags">
        <span class="tag zone-${e.zone}">${e.zone === 'low' ? 'Hỗ trợ' : e.zone === 'high' ? 'Kháng cự' : 'Vùng 50'}</span>
        <span class="tag ${e.reversed ? 'ok' : 'no'}">${e.reversed ? `Đảo ${e.move_pips}pip` : 'Không đảo'}</span>
        ${e.ema_aligned ? '<span class="tag ok">EMA OK</span>' : ''}
        ${e.exit_signal ? '<span class="tag ok">Rời vùng</span>' : ''}
      </div>
    </div>
  `).join('');

  el.querySelectorAll('.event-item').forEach((node) => {
    node.addEventListener('click', () => {
      const ev = lastEvents[Number(node.dataset.idx)];
      if (ev) chart.focusTime(ev.time);
    });
  });
}

async function loadAll() {
  $('dataRange').textContent = 'Đang tải…';
  const [chartData, stats] = await Promise.all([
    fetchJson(`/api/chart?${queryParams()}`),
    fetchJson(`/api/zone-stats?${statsParams()}`),
  ]);

  lastIndicators = chartData.indicators;
  chart.setData(chartData);
  chart.setMarkers(buildMarkers(stats.events, $('toggleMarkers').checked));
  chart.applyEmaVisibility($('toggleEma50').checked, $('toggleEma200').checked, lastIndicators);

  $('dataRange').textContent =
    `${chartData.count.toLocaleString()} nến · ${fmtDate(chartData.range?.start)} → ${fmtDate(chartData.range?.end)}`;

  renderZoneSummary(stats);
  renderConditions(stats.conditions);
  renderEvents(stats.events);
}

async function init() {
  chart = new RsiZoneChart($('chartMain'), $('chartRsi'), {
    onCrosshair: (info) => {
      const el = $('crosshairInfo');
      if (!info?.candle) {
        el.textContent = '';
        return;
      }
      const c = info.candle;
      el.textContent =
        `${fmtTime(c.time)} · O ${c.open} H ${c.high} L ${c.low} C ${c.close}` +
        (info.rsi != null ? ` · RSI H4 ${info.rsi.toFixed(1)}` : '');
    },
  });
  chart.mount();

  const info = await fetchJson('/api/info');
  if (info.start) {
    $('dateStart').value = info.start.slice(0, 10);
    $('dateEnd').value = info.end.slice(0, 10);
  }

  $('btnLoad').addEventListener('click', () => loadAll().catch(alert));
  $('btnRefreshStats').addEventListener('click', () => loadAll().catch(alert));
  $('toggleEma50').addEventListener('change', () => {
    chart.applyEmaVisibility($('toggleEma50').checked, $('toggleEma200').checked, lastIndicators);
  });
  $('toggleEma200').addEventListener('change', () => {
    chart.applyEmaVisibility($('toggleEma50').checked, $('toggleEma200').checked, lastIndicators);
  });
  $('toggleMarkers').addEventListener('change', async () => {
    const stats = await fetchJson(`/api/zone-stats?${statsParams()}`);
    chart.setMarkers(buildMarkers(stats.events, $('toggleMarkers').checked));
  });

  await loadAll();
}

init().catch((err) => {
  console.error(err);
  $('dataRange').textContent = `Lỗi: ${err.message}`;
});
