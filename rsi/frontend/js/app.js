import { RsiZoneChart } from './chart.js';
import { initChartSplit } from './layout.js';

const $ = (id) => document.getElementById(id);

let chart;
let lastIndicators = null;
let lastStats = null;
let lastRecommended = null;
let lastTrades = [];
let lastEvents = [];
let lastDivergences = [];
let selectedTradeId = null;
let chartLoadedOnce = false;

function applyEmaToggles() {
  chart.applyEmaVisibility(
    $('toggleEma50').checked,
    $('toggleEma200').checked,
    $('toggleEma800')?.checked ?? true,
    lastIndicators,
  );
}

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

function resultLabel(t) {
  if (t.result === 'win') return 'Thắng';
  if (t.result === 'loss') return 'Thua';
  return t.exit_reason || t.result;
}

function resultTagClass(t) {
  if (t.result === 'win') return 'ok';
  if (t.result === 'loss') return 'no';
  return '';
}

function exitReasonLabel(reason) {
  if (reason === 'tp' || reason === 'rsi_tp') return 'TP';
  if (reason === 'sl') return 'SL';
  if (reason === 'timeout') return 'Hết hạn';
  if (reason === 'both_same_bar') return 'SL/TP cùng nến';
  return reason || '—';
}

function directionLabel(t) {
  return t.direction === 'short' ? 'Short' : 'Long';
}

function tradeRowHtml(t, compact = false) {
  const pip = t.pnl_pips >= 0 ? `+${t.pnl_pips}` : `${t.pnl_pips}`;
  const selected = t.id === selectedTradeId ? ' selected' : '';
  if (compact) {
    return `
      <tr class="trade-row${selected}" data-trade-id="${t.id}">
        <td class="mono">${t.id}</td>
        <td class="mono">${directionLabel(t)} · ${fmtTime(t.entry_time).slice(0, 10)}</td>
        <td><span class="tag ${resultTagClass(t)}">${resultLabel(t)}</span></td>
        <td class="mono">${pip}</td>
        <td class="mono">${t.r_multiple}R</td>
      </tr>`;
  }
  return `
    <tr class="trade-row${selected}" data-trade-id="${t.id}">
      <td class="mono">${t.id}</td>
      <td class="mono">${directionLabel(t)} · ${fmtTime(t.entry_time)}</td>
      <td class="mono">${fmtTime(t.exit_time)}</td>
      <td class="mono">${t.entry_price}</td>
      <td class="mono">${t.exit_price}</td>
      <td class="mono">${t.sl_price}</td>
      <td class="mono">${t.tp_price}</td>
      <td><span class="tag ${resultTagClass(t)}">${resultLabel(t)} (${exitReasonLabel(t.exit_reason)})</span></td>
      <td class="mono">${pip}</td>
      <td class="mono">${t.r_multiple}R</td>
      <td class="mono">${t.bars_held}</td>
    </tr>`;
}

function bindTradeRows(root) {
  root.querySelectorAll('.trade-row').forEach((row) => {
    row.addEventListener('click', () => {
      const id = Number(row.dataset.tradeId);
      focusTrade(id);
    });
  });
}

function focusTrade(id) {
  const trade = lastTrades.find((t) => t.id === id);
  if (!trade) return;
  selectedTradeId = id;
  switchTab('chart');
  if ($('toggleTrades')?.checked) {
    chart.setTradeMarkers(lastTrades, { show: true });
  }
  if ($('toggleSlTp')?.checked) {
    chart.highlightTrade(trade);
  } else {
    chart.focusTradeRange(trade.entry_time, trade.exit_time);
  }
  renderTradeTables();
  const el = $('crosshairInfo');
  if (el) {
    el.textContent =
      `Lệnh #${trade.id} ${directionLabel(trade)} · ${resultLabel(trade)} ${trade.pnl_pips >= 0 ? '+' : ''}${trade.pnl_pips} pip · ` +
      `Entry ${trade.entry_price} → ${trade.exit_price} · SL ${trade.sl_price} TP ${trade.tp_price}`;
  }
}

function renderTradeTables() {
  const compactBody = $('tradeHistoryTable')?.querySelector('tbody');
  const reportBody = $('tradeReportTable')?.querySelector('tbody');
  const countEl = $('tradesCount');

  if (countEl) {
    const wins = lastTrades.filter((t) => t.result === 'win').length;
    const longN = lastTrades.filter((t) => t.direction !== 'short').length;
    const shortN = lastTrades.filter((t) => t.direction === 'short').length;
    countEl.textContent = `${lastTrades.length} lệnh (${longN} long · ${shortN} short) · ${wins} thắng`;
  }
  if (compactBody) {
    compactBody.innerHTML = lastTrades.map((t) => tradeRowHtml(t, true)).join('');
    bindTradeRows(compactBody.parentElement);
  }
  if (reportBody) {
    reportBody.innerHTML = lastTrades.map((t) => tradeRowHtml(t, false)).join('');
    bindTradeRows(reportBody.parentElement);
  }
}

function applyTradeOverlay() {
  if ($('toggleTrades')?.checked) {
    chart.setTradeMarkers(lastTrades, { show: true });
  } else {
    chart.setTradeMarkers([], { show: false });
  }
  if ($('toggleSlTp')?.checked && selectedTradeId) {
    const trade = lastTrades.find((t) => t.id === selectedTradeId);
    chart.highlightTrade(trade || null);
  } else {
    chart.highlightTrade(null);
  }
}

function renderRecommended(rec, side = 'long') {
  const elId = side === 'short' ? 'recommendedContentShort' : 'recommendedContentLong';
  const el = $(elId);
  if (!el) return;
  const block = side === 'short' ? rec?.short : rec;
  if (!block?.setup) {
    el.innerHTML = '<p class="hint">—</p>';
    return;
  }
  const setup = block.setup || {};
  const perf = block.performance || {};
  const entryLabels = {
    touch: 'Vào ngay khi chạm vùng',
    delay_1: 'Delay 1 nến sau chạm',
    delay_3: 'Delay 3 nến',
    delay_5: 'Delay 5 nến',
    confirm_candle: 'Chờ nến xác nhận',
    confirm_delay1: 'Delay 1 + nến xác nhận',
    touch_div: 'Chạm vùng + phân kỳ H4',
    ema_touch_2: 'Chạm EMA lần 2',
    ema_touch_3: 'Chạm EMA lần 3',
    ema_reject_2: 'Từ chối EMA lần 2',
    ema_reject_3: 'Từ chối EMA lần 3',
    ema_reject_3_pb10: 'EMA lần 3 + pullback 10 pip',
  };
  const entryText = entryLabels[setup.entry_strategy] || setup.entry_strategy || 'Chạm vùng';
  const slText = setup.sl_mode === 'swing' ? 'SL swing' : setup.sl_mode === 'atr' ? 'SL ATR' : `SL ${setup.stop_loss_pips} pip`;
  const tpText = perf.params?.take_profit_mode === 'rsi_zone' || perf.config?.take_profit_mode === 'rsi_zone' || setup.take_profit_mode === 'rsi_zone'
    ? 'TP vùng RSI đối diện'
    : `TP ${setup.take_profit_r}R`;
  const notes = (setup.notes || []).map((n) => `<li>${n}</li>`).join('');
  const filterText = (setup.entry_filters || []).includes('min_ema_sep')
    ? ' · EMA50/200 sep ≥ 15 pip'
    : '';
  const sl2Text = setup.sl_two_opposite ? ' · 2 SL → chờ RSI 68–72' : '';
  const warnClass = block.warning ? ' warn' : '';
  const badge = side === 'short'
    ? '<span class="tag no" style="margin-left:8px">Tham khảo</span>'
    : '<span class="tag ok" style="margin-left:8px">Khuyến nghị</span>';
  el.innerHTML = `
    <div class="recommended-hero">
      <div class="recommended-title${warnClass}">${setup.label || '—'}${badge}</div>
      <div class="recommended-metrics">
        <div class="metric"><span class="metric-val">${perf.expectancy_r ?? 0}R</span><span class="metric-lbl">Expectancy</span></div>
        <div class="metric"><span class="metric-val">${perf.profit_factor ?? 0}</span><span class="metric-lbl">Profit factor</span></div>
        <div class="metric"><span class="metric-val">${perf.win_rate ?? 0}%</span><span class="metric-lbl">Win rate</span></div>
        <div class="metric"><span class="metric-val">${perf.trades ?? 0}</span><span class="metric-lbl">Lệnh</span></div>
        <div class="metric"><span class="metric-val">+${perf.total_pips ?? 0}</span><span class="metric-lbl">Tổng pip</span></div>
      </div>
      <ul class="recommended-rules">${notes}</ul>
      <div class="recommended-params mono">
        ${entryText} · ${slText} · ${tpText} · Horizon ${setup.max_bars} nến H1 · Spread ${setup.spread_pips} pip${filterText}${sl2Text}
      </div>
    </div>`;
}

function renderRegimeTable(rec) {
  const ra = rec?.regime_analysis;
  const tbody = $('regimeTable')?.querySelector('tbody');
  const h4body = $('regimeH4Table')?.querySelector('tbody');
  const hints = $('regimeHints');
  const verdict = $('regimeVerdict');
  if (!ra || !tbody) return;

  const rowHtml = (row, withShare = false) => {
    const expCls = (row.expectancy_r ?? 0) < 0 ? 'bad' : (row.expectancy_r ?? 0) > 0.35 ? 'good' : '';
    const shareCol = withShare ? `<td>${row.pip_share_pct ?? 0}%</td>` : '';
    return `
      <tr class="${expCls}">
        <td><strong>${row.label}</strong></td>
        <td>${row.trades ?? 0}</td>
        <td class="rate">${row.win_rate ?? 0}%</td>
        <td class="rate">${row.sl_rate ?? 0}%</td>
        <td class="rate">${row.expectancy_r ?? 0}R</td>
        <td>${row.profit_factor ?? '—'}</td>
        <td class="mono">${(row.total_pips ?? 0) >= 0 ? '+' : ''}${row.total_pips ?? 0}</td>
        ${shareCol}
      </tr>`;
  };

  tbody.innerHTML = (ra.by_regime || []).map((r) => rowHtml(r, true)).join('');
  if (h4body) {
    h4body.innerHTML = (ra.by_h4_trend || []).map((r) => rowHtml(r, false)).join('');
  }
  if (hints) {
    hints.innerHTML = (ra.trading_hints || []).map((h) => `<li>${h}</li>`).join('');
  }
  if (verdict) {
    const parts = [ra.conclusion, ra.filter_note].filter(Boolean);
    verdict.textContent = parts.join(' · ');
  }
}

function renderOptimizationTable(rec) {
  const tbody = $('optimizationTable')?.querySelector('tbody');
  const verdict = $('optimizationVerdict');
  const review = rec?.optimization_review;
  if (!tbody || !review) return;
  const statusLabels = {
    selected: 'Đang dùng',
    replaced: 'Đã thay',
    alternative: 'Thay thế',
    rejected: 'Loại',
  };
  const statusClass = {
    selected: 'good',
    replaced: 'muted',
    alternative: 'ok',
    rejected: 'bad',
  };
  tbody.innerHTML = (review.comparisons || []).map((row) => {
    const st = row.status || '';
    const cls = statusClass[st] || '';
    const fmt = (v, suffix = '') => (v == null ? '—' : `${v}${suffix}`);
    return `
      <tr class="${cls}">
        <td><strong>${row.idea}</strong></td>
        <td>${statusLabels[st] || st}</td>
        <td>${fmt(row.trades)}</td>
        <td class="rate">${fmt(row.win_rate, '%')}</td>
        <td class="rate">${row.expectancy_r == null ? '—' : `${row.expectancy_r}R`}</td>
        <td>${fmt(row.profit_factor)}</td>
        <td class="mono">${row.total_pips == null ? '—' : (row.total_pips >= 0 ? '+' : '') + row.total_pips}</td>
        <td class="note">${row.note || ''}</td>
      </tr>`;
  }).join('');
  if (verdict) {
    const hc = rec?.horizon_comparison;
    const parts = [review.conclusion, hc?.conclusion].filter(Boolean);
    verdict.textContent = parts.join(' · ');
  }
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

function renderWalkForwardTable(wf, side = 'long') {
  const tableId = side === 'short' ? 'walkForwardTableShort' : 'walkForwardTable';
  const verdictId = side === 'short' ? 'walkForwardVerdictShort' : 'walkForwardVerdict';
  const tbody = $(tableId)?.querySelector('tbody');
  const verdict = $(verdictId);
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
  const zones = stats?.zones || {};
  const low = zones.low || {};
  const high = zones.high || {};
  const cfg = stats?.config || {};
  const el = $('reportSummary');
  if (!el) return;
  el.innerHTML = `
    <div class="summary-card">
      <div class="summary-label">Khoảng phân tích</div>
      <div class="summary-value" id="reportRange">${rangeText || '—'}</div>
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
      <div class="summary-value">${cfg.horizon_bars ?? 48} nến H1</div>
      <div class="summary-sub">≥ ${cfg.min_reversal_pips ?? 20} pip · cooldown ${cfg.cooldown_bars ?? 12}</div>
    </div>`;
}

function renderZoneTable(stats) {
  const tbody = $('zoneTable')?.querySelector('tbody');
  if (!tbody) return;
  const zones = stats?.zones || {};
  tbody.innerHTML = ['low', 'mid', 'high'].map((key) => {
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
  }).join('');
}

function renderConditionTable(rows) {
  const tbody = $('conditionTable')?.querySelector('tbody');
  if (!tbody) return;
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
  const tbody = $('eventTable')?.querySelector('tbody');
  if (!tbody) return;
  lastEvents = events || [];
  tbody.innerHTML = lastEvents.map((e, i) => `
    <tr class="event-row" data-idx="${i}">
      <td class="mono">${fmtTime(e.time)}</td>
      <td><span class="tag zone-${e.zone}">${e.zone === 'low' ? 'Hỗ trợ' : e.zone === 'high' ? 'Kháng cự' : 'Vùng 50'}</span></td>
      <td class="mono">${e.rsi}</td>
      <td class="mono">${Number(e.close).toFixed(5)}</td>
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

function renderDivergenceTable(stats) {
  const tbody = $('divergenceTable')?.querySelector('tbody');
  if (!tbody) return;
  const rows = [
    ['Tổng', stats?.overall],
    ['Bullish', stats?.bullish],
    ['Bearish', stats?.bearish],
  ];
  tbody.innerHTML = rows.map(([label, r]) => `
    <tr>
      <td><strong>${label}</strong></td>
      <td>${r?.count ?? 0}</td>
      <td>${r?.reversals ?? 0}</td>
      <td class="rate">${r?.reversal_rate ?? 0}%</td>
      <td class="mono">${r?.avg_move_pips ?? '—'}</td>
      <td class="mono">${r?.avg_adverse_pips ?? '—'}</td>
      <td class="mono">${r?.avg_bars_to_extreme ?? '—'}</td>
    </tr>
  `).join('');
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

function renderReport(stats, recommended, rangeText) {
  lastStats = stats;
  lastRecommended = recommended;
  lastTrades = recommended?.trade_history || [];
  renderRecommended(recommended, 'long');
  renderRecommended(recommended, 'short');
  renderRegimeTable(recommended);
  renderOptimizationTable(recommended);
  renderWalkForwardTable(recommended?.walk_forward, 'long');
  renderWalkForwardTable(recommended?.short?.walk_forward, 'short');
  renderRejectedTable(recommended);
  renderReportSummary(stats, rangeText);
  renderZoneTable(stats);
  renderConditionTable(stats?.conditions);
  renderDivergenceTable(stats?.divergence_stats);
  renderEventTable(stats?.events);
  renderMaeMfeTable(stats?.mae_mfe);
  renderTradeTables();
  applyTradeOverlay();
}

async function loadChart({ fit = false } = {}) {
  const chartData = await fetchJson(`/api/chart?${queryParams()}`);
  lastIndicators = chartData.indicators;
  lastDivergences = chartData.divergences || [];
  chart.setData(chartData, { fit: fit || !chartLoadedOnce });
  chartLoadedOnce = true;
  applyTradeOverlay();
  chart.setDivergences(lastDivergences, { show: $('toggleDivergence')?.checked ?? true });
  applyEmaToggles();
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
  lastTrades = recommended?.trade_history || [];
  applyTradeOverlay();
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
  $('viewGuide').classList.toggle('hidden', tab !== 'guide');
  $('viewGuide').classList.toggle('active', tab === 'guide');
  if (tab === 'chart') requestAnimationFrame(() => chart?.resize());
}

async function init() {
  chart = new RsiZoneChart($('chartHost'), {
    wrapEl: $('chartWrap'),
    bodyEl: $('chartBody'),
    rsiPanel: $('rsiPanel'),
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
  $('btnGuide')?.addEventListener('click', () => switchTab('guide'));
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
    applyEmaToggles();
  });
  $('toggleEma200').addEventListener('change', () => {
    applyEmaToggles();
  });
  $('toggleEma800')?.addEventListener('change', () => applyEmaToggles());
  $('toggleDivergence')?.addEventListener('change', () => {
    chart.setDivergences(lastDivergences, { show: $('toggleDivergence').checked });
  });
  $('toggleTrades')?.addEventListener('change', () => applyTradeOverlay());
  $('toggleSlTp')?.addEventListener('change', () => applyTradeOverlay());

  await loadAll({ fitChart: false });
}

init().catch((err) => {
  console.error(err);
  $('dataRange').textContent = `Lỗi: ${err.message}`;
});
