/**
 * Report engine — assembles dashboard, heatmaps, and export payloads.
 * @module report/ReportEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { loadPersistedResult, savePersistedResult } from '../utils/resultsPersistence.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import StatisticsEngine from '../statistics/StatisticsEngine.js';
import { computeAllHeatmaps } from '../analytics/HeatmapCalculator.js';
import { buildDashboardCards } from '../analytics/DashboardSummary.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ReportEngine');

/** @typedef {import('../statistics/StatisticsCalculator.js').PerformanceStats} PerformanceStats */
/** @typedef {import('../simulation/TradeSimulator.js').TradeResult} TradeResult */
/** @typedef {import('../analytics/HeatmapCalculator.js').HeatmapData} HeatmapData */
/** @typedef {import('../analytics/DashboardSummary.js').DashboardCard} DashboardCard */

/**
 * @typedef {Object} ResearchReport
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {PerformanceStats} stats
 * @property {DashboardCard[]} dashboard
 * @property {Record<string, HeatmapData>} heatmaps
 * @property {TradeResult[]} trades
 * @property {number} signalCount
 * @property {number} durationMs
 * @property {number} generatedAt
 */

/**
 * Main report service module.
 */
class ReportEngine {
  /** @type {ResearchReport|null} */
  #lastReport = null;

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    this.#lastReport = await loadPersistedResult(Config.STORAGE_KEYS.REPORT_RESULTS, null);

    bus.on(Events.STATISTICS_COMPUTED, () => this.refreshFromSimulation());

    log.info('Report engine ready');
  }

  /**
   * @returns {ResearchReport|null}
   */
  getLastReport() {
    return this.#lastReport;
  }

  /**
   * Build a research report from simulation + statistics data.
   * @param {import('../simulation/SimulationEngine.js').SimulationResult} sim
   * @param {import('../statistics/StatisticsEngine.js').StatisticsReport} statsReport
   * @returns {ResearchReport}
   */
  buildReport(sim, statsReport) {
    const closedTrades = sim.trades.filter((t) => t.outcome !== 'open');

    const report = {
      strategyId: sim.strategyId,
      symbol: sim.symbol,
      timeframe: sim.timeframe,
      stats: statsReport.stats,
      dashboard: buildDashboardCards({
        strategyId: sim.strategyId,
        symbol: sim.symbol,
        timeframe: sim.timeframe,
        stats: statsReport.stats,
        signalCount: sim.signalCount,
        durationMs: sim.durationMs,
      }),
      heatmaps: computeAllHeatmaps(closedTrades),
      trades: closedTrades,
      signalCount: sim.signalCount,
      durationMs: sim.durationMs,
      generatedAt: Date.now(),
    };

    this.#lastReport = report;
    savePersistedResult(Config.STORAGE_KEYS.REPORT_RESULTS, report);

    bus.emit(Events.REPORT_GENERATED, report);
    bus.emit(Events.LOG_MESSAGE, {
      message: `Report ready: ${closedTrades.length} trades, ${Object.keys(report.heatmaps).length} heatmaps`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Report built for ${sim.strategyId}`);
    return report;
  }

  /**
   * Rebuild report from latest simulation and statistics.
   * @returns {ResearchReport|null}
   */
  refreshFromSimulation() {
    const sim = SimulationEngine.getLastResult();
    const statsReport = StatisticsEngine.getLastReport();

    if (!sim || !statsReport || statsReport.stats.totalTrades === 0) {
      return this.#lastReport;
    }

    return this.buildReport(sim, statsReport);
  }
}

export default new ReportEngine();
