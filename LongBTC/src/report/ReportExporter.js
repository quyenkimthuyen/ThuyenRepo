/**
 * Report export utilities — CSV, JSON, PNG, and printable HTML.
 * @module report/ReportExporter
 */

import { downloadFile } from '../data/DataExporter.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';

/** @typedef {import('../simulation/TradeSimulator.js').TradeResult} TradeResult */
/** @typedef {import('./ReportEngine.js').ResearchReport} ResearchReport */

/**
 * Convert trade results to CSV string.
 * @param {TradeResult[]} trades
 * @returns {string}
 */
export function exportTradesCSV(trades) {
  const header = [
    'id', 'strategyId', 'symbol', 'timeframe', 'direction', 'outcome',
    'entryTime', 'exitTime', 'entryPrice', 'exitPrice', 'sl', 'tp',
    'pips', 'profit', 'commission', 'durationBars', 'exitReason', 'reason',
  ].join(',');

  const rows = trades.map((t) => [
    t.id,
    t.strategyId,
    t.symbol,
    t.timeframe,
    t.direction,
    t.outcome,
    t.entryTime,
    formatTimestamp(t.entryTime),
    t.entryPrice,
    t.exitPrice,
    t.sl,
    t.tp,
    t.pips,
    t.profit,
    t.commission,
    t.durationBars,
    t.exitReason,
    `"${(t.reason ?? '').replace(/"/g, '""')}"`,
  ].join(','));

  return [header, ...rows].join('\n');
}

/**
 * Serialize a full research report to JSON.
 * @param {ResearchReport} report
 * @returns {string}
 */
export function exportReportJSON(report) {
  return JSON.stringify(report, null, 2);
}

/**
 * Trigger CSV download of trades.
 * @param {TradeResult[]} trades
 * @param {string} [filename='trades.csv']
 */
export function downloadTradesCSV(trades, filename = 'trades.csv') {
  downloadFile(exportTradesCSV(trades), filename, 'text/csv');
}

/**
 * Trigger JSON download of full report.
 * @param {ResearchReport} report
 * @param {string} [filename='research_report.json']
 */
export function downloadReportJSON(report, filename = 'research_report.json') {
  downloadFile(exportReportJSON(report), filename, 'application/json');
}

/**
 * Download a canvas element as PNG.
 * @param {HTMLCanvasElement} canvas
 * @param {string} [filename='dashboard.png']
 */
export function downloadCanvasPNG(canvas, filename = 'dashboard.png') {
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }, 'image/png');
}

/**
 * Build printable HTML document for PDF via browser print.
 * @param {ResearchReport} report
 * @returns {string}
 */
export function buildPrintableHTML(report) {
  const { stats, strategyId, symbol, timeframe, trades } = report;
  const rows = trades.map((t) => `
    <tr>
      <td>${t.id}</td>
      <td>${t.direction}</td>
      <td>${t.outcome}</td>
      <td>${formatTimestamp(t.entryTime)}</td>
      <td>${t.entryPrice}</td>
      <td>${t.exitPrice}</td>
      <td>${t.profit.toFixed(2)}</td>
    </tr>
  `).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PARL Research Report</title>
  <style>
    body { font-family: Inter, sans-serif; padding: 24px; color: #1a1a1a; }
    h1 { font-size: 20px; margin-bottom: 4px; }
    .meta { color: #555; font-size: 13px; margin-bottom: 20px; }
    .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
    .metric { border: 1px solid #ddd; border-radius: 6px; padding: 10px; }
    .metric label { font-size: 11px; color: #666; text-transform: uppercase; }
    .metric span { display: block; font-size: 18px; font-weight: 600; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
    th { background: #f5f5f5; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>
  <h1>Price Action Research Lab — Report</h1>
  <p class="meta">${strategyId} · ${symbol} ${timeframe} · ${stats.totalTrades} trades · Generated ${new Date(report.generatedAt).toLocaleString()}</p>
  <div class="metrics">
    <div class="metric"><label>Net Profit</label><span>$${stats.netProfit.toFixed(2)}</span></div>
    <div class="metric"><label>Win Rate</label><span>${stats.winRate.toFixed(1)}%</span></div>
    <div class="metric"><label>Profit Factor</label><span>${stats.profitFactor === Infinity ? '∞' : stats.profitFactor.toFixed(2)}</span></div>
    <div class="metric"><label>Max Drawdown</label><span>$${stats.maxDrawdown.toFixed(2)}</span></div>
    <div class="metric"><label>Expectancy</label><span>$${stats.expectancy.toFixed(2)}</span></div>
    <div class="metric"><label>Sharpe</label><span>${stats.sharpeRatio.toFixed(2)}</span></div>
    <div class="metric"><label>Gross Profit</label><span>$${stats.grossProfit.toFixed(2)}</span></div>
    <div class="metric"><label>Gross Loss</label><span>$${stats.grossLoss.toFixed(2)}</span></div>
  </div>
  <h2>Trade Log</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>Dir</th><th>Outcome</th><th>Entry</th><th>Entry Px</th><th>Exit Px</th><th>P/L</th></tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>
</body>
</html>`;
}

/**
 * Open printable report in a new window for Save as PDF.
 * @param {ResearchReport} report
 */
export function openPrintReport(report) {
  const html = buildPrintableHTML(report);
  const win = window.open('', '_blank', 'width=900,height=700');
  if (!win) return;
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 300);
}
