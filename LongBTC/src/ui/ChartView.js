/**
 * Chart view — candlestick chart with replay controls and data loading.
 * @module ui/ChartView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import { ChartEngine } from '../chart/ChartEngine.js';
import {
  mountPsychologyChartBg,
  updatePsychologyChartBg,
} from '../chart/PsychologyChartOverlay.js';
import {
  CHART_OVERLAY_PRESETS,
  clearPresetActiveState,
  mountChartContextBar,
  mountOverlayPresets,
  syncOverlayCheckboxes,
  updateChartContextBar,
} from './ChartResearchUi.js';
import { ReplayEngine } from '../replay/ReplayEngine.js';
import { ReplayControls } from './ReplayControls.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';
import {
  buildSymbolOptions,
  buildTimeframeOptions,
  fillDatasetSelectors,
  resolveDatasetSelection,
} from '../utils/runnableDatasets.js';
import { takePendingChartFocus } from '../utils/chartNavigation.js';
import { alignToTimeframe, formatTimestamp } from '../data/TimeframeUtils.js';
import { getLastAnalysis, analyzeLongTerm } from '../analysis/LongTermAnalysisEngine.js';
import {
  SETUP_LEVEL_STYLES,
  TRADE_LEVEL_STYLES,
  MARKER_ROLE_COLORS,
} from '../chart/SetupAnnotationStyles.js';

const log = createLogger('ChartView');

/**
 * Main chart workspace view.
 */
class ChartViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {ChartEngine|null} */
  #chart = null;

  /** @type {ReplayEngine|null} */
  #replay = null;

  /** @type {string} */
  #symbol = Config.DEFAULT_SYMBOL;

  /** @type {string} */
  #timeframe = Config.DEFAULT_TIMEFRAME;

  /** @type {import('../data/Candle.js').DatasetMetadata[]} */
  #runnableDatasets = [];

  /** @type {Function|null} */
  #unsubs = null;

  /** @type {number|null} */
  #pendingJump = null;

  /** @type {import('../utils/chartNavigation.js').ChartSignalHighlight|null} */
  #pendingSignal = null;

  /** @type {import('../utils/chartNavigation.js').ChartSignalHighlight|null} */
  #activeSignal = null;

  /** @type {boolean|null} */
  #emaRestore = null;

  /** @type {{ swings: boolean, trends: boolean, cycle: boolean, elliott: boolean, halving: boolean, psychology: boolean, psychologyBg: boolean }} */
  #overlayToggles = { ...CHART_OVERLAY_PRESETS.clean };

  /** @type {HTMLElement|null} */
  #contextBar = null;

  /** @type {HTMLElement|null} */
  #psychologyChartBg = null;

  /** @type {{ candle: import('../data/Candle.js').Candle, index: number, analysis: import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult }|null} */
  #hoverFocus = null;

  /** @type {ReturnType<typeof setTimeout>|null} */
  #hoverAnalysisTimer = null;

  /**
   * Mount the chart view.
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');
    container.classList.add('chart-view-root');

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    this.#symbol = settings.symbol ?? Config.DEFAULT_SYMBOL;
    this.#timeframe = settings.timeframe ?? Config.DEFAULT_TIMEFRAME;

    const pending = takePendingChartFocus();
    if (pending) {
      this.#symbol = pending.symbol;
      this.#timeframe = pending.timeframe;
      if (pending.jumpTo != null) this.#pendingJump = pending.jumpTo;
      if (pending.signal) this.#pendingSignal = pending.signal;
    }

    this.#runnableDatasets = await DataManager.listRunnableDatasets();
    const resolved = resolveDatasetSelection(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );
    if (resolved.symbol) this.#symbol = resolved.symbol;
    if (resolved.timeframe) this.#timeframe = resolved.timeframe;

    const chartContainer = el('div', { class: 'chart-container', id: 'chart-container' });

    this.#replay = new ReplayEngine();
    this.#chart = new ChartEngine();

    const chartMain = el('div', { class: 'chart-main' }, [
      el('div', { class: 'chart-setup-legend', id: 'chart-setup-legend', hidden: true }),
      chartContainer,
      ReplayControls.render((action, payload) => this.#handleReplayAction(action, payload)),
    ]);

    container.appendChild(el('div', { class: 'chart-view', id: 'chart-view-root' }, [
      this.#renderToolbar(),
      el('div', { class: 'chart-body', id: 'chart-body' }, [
        chartMain,
        el('aside', { class: 'chart-signal-panel', id: 'chart-signal-panel', hidden: true }),
      ]),
    ]));

    this.#contextBar = mountChartContextBar(chartMain);
    this.#psychologyChartBg = mountPsychologyChartBg(chartContainer);
    this.#chart.mount(chartContainer);
    const toolbar = container.querySelector('.chart-toolbar');
    if (toolbar) {
      mountOverlayPresets(toolbar, (preset) => this.#applyOverlayPreset(preset));
    }
    this.#chart.onVisibleRangeChange(() => this.#updateResearchUi());
    this.#wireCrosshair();
    this.#wireReplay();
    this.#bindEvents();
    await this.#loadChart();

    log.info('Chart view mounted');
  }

  /**
   * Tear down the view.
   */
  unmount() {
    this.#clearHoverFocus();
    this.#unsubs?.();
    this.#unsubs = null;
    this.#replay?.destroy();
    this.#chart?.destroy();
    this.#psychologyChartBg = null;
    this.#replay = null;
    this.#chart = null;

    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.remove('chart-view-root');
      this.#container.classList.add('panel-body-fill');
    }
  }

  /**
   * @returns {HTMLElement}
   */
  #renderToolbar() {
    const symbolOptions = buildSymbolOptions(this.#runnableDatasets, this.#symbol);
    const tfOptions = buildTimeframeOptions(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );

    return el('div', { class: 'chart-toolbar' }, [
      el('div', { class: 'chart-toolbar-group' }, [
        el('select', {
          class: 'data-select',
          id: 'chart-symbol',
          disabled: this.#runnableDatasets.length === 0,
        }, symbolOptions),
        el('select', {
          class: 'data-select',
          id: 'chart-timeframe',
          disabled: this.#runnableDatasets.length === 0,
        }, tfOptions),
      ]),
      el('div', { class: 'chart-toolbar-group' }, [
        el('label', { class: 'chart-toggle' }, [
          el('input', { type: 'checkbox', id: 'chart-ema', checked: true }),
          ' EMA 200',
        ]),
      ]),
      el('details', { class: 'chart-overlay-details' }, [
        el('summary', {}, ['L\u1edbp ph\u1ee7']),
        el('div', { class: 'chart-analysis-toggles' }, [
          el('label', {}, [
            el('input', { type: 'checkbox', id: 'chart-overlay-swings' }),
            ' Swing',
          ]),
          el('label', {}, [
            el('input', { type: 'checkbox', id: 'chart-overlay-trends' }),
            ' Xu h\u01b0\u1edbng',
          ]),
          el('label', {}, [
            el('input', { type: 'checkbox', id: 'chart-overlay-cycle', checked: true }),
            ' Chu k\u1ef3',
          ]),
          el('label', {}, [
            el('input', { type: 'checkbox', id: 'chart-overlay-elliott' }),
            ' Elliott',
          ]),
          el('label', {}, [
            el('input', { type: 'checkbox', id: 'chart-overlay-halving', checked: true }),
            ' Halving',
          ]),
          el('label', {}, [
            el('input', { type: 'checkbox', id: 'chart-overlay-psychology', checked: true }),
            ' T\u00e2m l\u00fd',
          ]),
          el('label', {}, [
            el('input', { type: 'checkbox', id: 'chart-overlay-psychology-bg', checked: true }),
            ' N\u1ec1n giai \u0111o\u1ea1n t\u00e2m l\u00fd',
          ]),
        ]),
      ]),
      el('div', { class: 'chart-toolbar-group chart-status', id: 'chart-status' }, [
        'Loading…',
      ]),
      createHelpButton('chart'),
    ]);
  }

  #wireReplay() {
    if (!this.#replay) return;

    this.#replay.onTick(({ visible, candle, index, total, fullRefresh }) => {
      if (!this.#chart) return;

      this.#clearHoverFocus();

      if (fullRefresh || index < 2) {
        const replayMode = this.#replay?.getState().mode === 'replay';
        this.#chart.setCandles(visible, { fit: !this.#activeSignal && !replayMode });
        if (this.#activeSignal) {
          this.#chart.setSignalOverlay(this.#activeSignal, visible);
        } else if (replayMode && visible.length > 0) {
          this.#chart.focusOnCandleIndex(visible.length - 1);
        }
      } else {
        this.#chart.updateCandle(candle, visible);
      }

      ReplayControls.update(this.#replay.getState(), candle);
      bus.emit(Events.REPLAY_TICK, { index, total, candle });

      if (this.#symbol === 'BTCUSD' && visible.length >= 20 && (fullRefresh || index % 3 === 0)) {
        this.#runChartAnalysis(visible);
      } else {
        this.#updateResearchUi();
      }
    });

    this.#replay.onStateChange((state) => {
      ReplayControls.update(state, this.#replay?.getCurrentCandle());
      bus.emit(Events.REPLAY_STATE, state);
    });
  }

  #bindEvents() {
    const unsubs = [];

    unsubs.push(bus.on(Events.CHART_LOAD, ({ symbol, timeframe, jumpTo, signal }) => {
      this.#symbol = symbol;
      this.#timeframe = timeframe;
      if (jumpTo != null) this.#pendingJump = jumpTo;
      if (signal) this.#pendingSignal = signal;
      this.#syncSelectors();
      this.#loadChart();
    }));

    unsubs.push(bus.on(Events.REPLAY_COMMAND, ({ action, ...payload }) => {
      this.#handleReplayAction(action, payload);
    }));

    unsubs.push(bus.on(Events.PANEL_RESIZE, () => {
      this.#updateResearchUi();
    }));

    unsubs.push(bus.on(Events.DATA_UPDATED, async () => {
      if (this.#container) {
        await this.#refreshDatasetSelectors();
        this.#loadChart();
      }
    }));

    this.#container?.querySelector('#chart-symbol')?.addEventListener('change', (e) => {
      this.#symbol = /** @type {HTMLSelectElement} */ (e.target).value;
      this.#clearSignalContext();
      this.#syncTimeframeOptions();
      this.#loadChart();
    });

    this.#container?.querySelector('#chart-timeframe')?.addEventListener('change', (e) => {
      this.#timeframe = /** @type {HTMLSelectElement} */ (e.target).value;
      this.#clearSignalContext();
      this.#loadChart();
    });

    this.#container?.querySelector('#chart-ema')?.addEventListener('change', (e) => {
      this.#chart?.setEmaVisible(/** @type {HTMLInputElement} */ (e.target).checked);
      const visible = this.#replay?.getVisibleCandles() ?? [];
      if (visible.length) this.#chart?.setCandles(visible);
    });

    for (const [id, key] of [
      ['chart-overlay-swings', 'swings'],
      ['chart-overlay-trends', 'trends'],
      ['chart-overlay-cycle', 'cycle'],
      ['chart-overlay-elliott', 'elliott'],
      ['chart-overlay-halving', 'halving'],
      ['chart-overlay-psychology', 'psychology'],
      ['chart-overlay-psychology-bg', 'psychologyBg'],
    ]) {
      this.#container?.querySelector(`#${id}`)?.addEventListener('change', (e) => {
        this.#overlayToggles[/** @type {keyof typeof this.#overlayToggles} */ (key)] =
          /** @type {HTMLInputElement} */ (e.target).checked;
        const toolbar = this.#container?.querySelector('.chart-toolbar');
        if (toolbar) clearPresetActiveState(toolbar);
        this.#applyAnalysisOverlay();
        this.#updateResearchUi();
      });
    }

    unsubs.push(bus.on(Events.ANALYSIS_COMPLETE, () => this.#applyAnalysisOverlay()));

    this.#unsubs = () => unsubs.forEach((fn) => fn());
  }

  /** Run analysis on visible candles and refresh chart overlay + HUD. */
  #runChartAnalysis(visible) {
    if (!this.#chart || this.#symbol !== 'BTCUSD' || visible.length < 20) return;

    const analysis = analyzeLongTerm(visible, {
      symbol: this.#symbol,
      timeframe: this.#timeframe,
    });
    bus.emit(Events.ANALYSIS_COMPLETE, analysis);
    this.#applyAnalysisOverlay();
  }

  /** Paint analysis overlay from last result (no re-run). */
  #applyAnalysisOverlay() {
    if (!this.#chart || this.#symbol !== 'BTCUSD') return;

    const visible = this.#replay?.getVisibleCandles() ?? [];
    const analysis = getLastAnalysis();
    if (!analysis) return;

    this.#chart.setAnalysisOverlay(analysis, {
      candles: visible,
      showSwings: this.#overlayToggles.swings,
      showTrends: this.#overlayToggles.trends,
      showCycle: this.#overlayToggles.cycle,
      showElliott: this.#overlayToggles.elliott,
      showHalving: this.#overlayToggles.halving,
    });
    this.#updateResearchUi();
  }

  /**
   * @param {keyof typeof CHART_OVERLAY_PRESETS} preset
   */
  #applyOverlayPreset(preset) {
    this.#overlayToggles = { ...CHART_OVERLAY_PRESETS[preset] };
    const toolbar = this.#container?.querySelector('.chart-toolbar');
    if (toolbar) syncOverlayCheckboxes(toolbar, this.#overlayToggles);
    this.#applyAnalysisOverlay();
  }

  /** Context bar, legend, psychology zones, insight card. */
  #updateResearchUi() {
    const visible = this.#replay?.getVisibleCandles() ?? [];
    const focus = this.#hoverFocus;
    const activeCandle = focus?.candle ?? (visible.length > 0 ? visible[visible.length - 1] : null);
    const analysis = focus?.analysis ?? getLastAnalysis();
    const cursorTs = activeCandle?.timestamp ?? Date.now();

    const viewport = this.#chart?.getVisibleTimeRangeMs();
    const rangeFromTs = viewport?.from ?? visible[0]?.timestamp ?? cursorTs;
    const rangeToTs = viewport?.to ?? visible[visible.length - 1]?.timestamp ?? cursorTs;

    const showResearch = this.#symbol === 'BTCUSD' && !this.#activeSignal && analysis != null;

    if (this.#psychologyChartBg && this.#chart) {
      updatePsychologyChartBg(this.#psychologyChartBg, {
        timeScale: this.#chart.getTimeScale(),
        plotWidth: this.#chart.getPlotWidth(),
        chartWidth: this.#chart.getChartWidth(),
        analysis,
        rangeFromTs,
        rangeToTs,
        cursorTs,
        visible: showResearch && this.#overlayToggles.psychologyBg,
      });
    }

    const replayState = this.#replay?.getState();
    const replayIndex = focus != null ? focus.index + 1 : visible.length;

    updateChartContextBar(this.#contextBar, {
      candle: activeCandle,
      analysis,
      toggles: this.#overlayToggles,
      timeframe: this.#timeframe,
      replayIndex,
      replayTotal: replayState?.total ?? visible.length,
      visible: showResearch,
      inspecting: focus != null,
    });
  }

  #wireCrosshair() {
    this.#chart?.onCrosshairMove((hit) => {
      if (!hit || this.#activeSignal) {
        if (this.#hoverFocus) {
          this.#clearHoverFocus();
          this.#updateResearchUi();
        }
        return;
      }

      const visible = this.#replay?.getVisibleCandles() ?? [];
      if (visible.length === 0) return;

      const index = this.#candleIndexAtOrBefore(visible, hit.timeMs);
      const candle = visible[index];
      if (!candle) return;

      if (this.#hoverFocus?.candle.timestamp === candle.timestamp) {
        return;
      }

      this.#hoverFocus = {
        candle,
        index,
        analysis: getLastAnalysis(),
      };
      this.#updateResearchUi();
      this.#scheduleHoverAnalysis(index, candle);
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} timeMs
   * @returns {number}
   */
  #candleIndexAtOrBefore(candles, timeMs) {
    let index = 0;
    for (let i = 0; i < candles.length; i++) {
      if (candles[i].timestamp <= timeMs) index = i;
      else break;
    }
    return index;
  }

  /**
   * @param {number} index
   * @param {import('../data/Candle.js').Candle} candle
   */
  #scheduleHoverAnalysis(index, candle) {
    const targetTs = candle.timestamp;
    clearTimeout(this.#hoverAnalysisTimer ?? undefined);
    this.#hoverAnalysisTimer = setTimeout(() => {
      this.#hoverAnalysisTimer = null;
      if (this.#hoverFocus?.candle.timestamp !== targetTs) return;

      const current = this.#replay?.getVisibleCandles() ?? [];
      const idx = this.#candleIndexAtOrBefore(current, targetTs);
      const active = current[idx];
      if (!active || active.timestamp !== targetTs) return;

      if (this.#symbol !== 'BTCUSD' || current.length < 20 || idx < 19) return;

      const analysis = analyzeLongTerm(current.slice(0, idx + 1), {
        symbol: this.#symbol,
        timeframe: this.#timeframe,
        persist: false,
      });
      this.#hoverFocus = { candle: active, index: idx, analysis };
      this.#updateResearchUi();
    }, 100);
  }

  #clearHoverFocus() {
    clearTimeout(this.#hoverAnalysisTimer ?? undefined);
    this.#hoverAnalysisTimer = null;
    this.#hoverFocus = null;
  }

  async #loadChart() {
    const status = document.getElementById('chart-status');
    if (status) status.textContent = `Loading ${this.#symbol} ${this.#timeframe}…`;

    try {
      const candles = await DataManager.getCandles(this.#symbol, this.#timeframe);

      if (candles.length === 0) {
        if (status) {
          status.textContent = 'No data — import or reload defaults in Data Manager';
        }
        this.#replay?.load([]);
        this.#chart?.setCandles([]);
        return;
      }

      this.#replay?.load(candles);

      if (this.#pendingJump != null) {
        this.#replay.jumpToDate(alignToTimeframe(this.#pendingJump, this.#timeframe));
        this.#pendingJump = null;
      } else {
        const visible = this.#replay.getVisibleCandles();
        this.#chart?.setCandles(visible);
      }

      ReplayControls.update(this.#replay.getState(), this.#replay.getCurrentCandle());

      if (this.#pendingSignal) {
        this.#activeSignal = this.#pendingSignal;
        this.#pendingSignal = null;
        const visible = this.#replay.getVisibleCandles();
        this.#chart?.setSignalOverlay(this.#activeSignal, visible);
        this.#showSignalPanel(this.#activeSignal);
        this.#renderSetupLegend(this.#activeSignal);
        this.#applySignalEmaMode(true);
      }

      if (status) {
        if (this.#activeSignal) {
          status.textContent = `${this.#activeSignal.symbol} ${this.#activeSignal.timeframe} · ${this.#activeSignal.strategyName} · ${this.#activeSignal.direction.toUpperCase()} @ ${formatTimestamp(this.#activeSignal.time)}`;
        } else {
          const visibleCount = this.#replay?.getVisibleCandles().length ?? candles.length;
          status.textContent = `${visibleCount.toLocaleString()} / ${candles.length.toLocaleString()} candles`;
        }
      }

      bus.emit(Events.CHART_LOADED, {
        symbol: this.#symbol,
        timeframe: this.#timeframe,
        count: candles.length,
        candles,
      });

      if (this.#symbol === 'BTCUSD') {
        const visible = this.#replay?.getVisibleCandles() ?? [];
        if (visible.length >= 20) {
          this.#runChartAnalysis(visible);
        } else {
          this.#applyAnalysisOverlay();
        }
      }

      bus.emit(Events.LOG_MESSAGE, {
        message: `Chart loaded: ${this.#symbol} ${this.#timeframe} (${candles.length} candles)`,
        level: 'info',
        time: new Date(),
      });
    } catch (err) {
      if (status) status.textContent = `Error: ${err.message}`;
      bus.emit(Events.LOG_MESSAGE, {
        message: `Chart load failed: ${err.message}`,
        level: 'error',
        time: new Date(),
      });
    }
  }

  /**
   * @param {string} action
   * @param {Record<string, unknown>} [payload]
   */
  #handleReplayAction(action, payload = {}) {
    if (!this.#replay) return;

    switch (action) {
      case 'toggle-play':
        if (this.#replay.getState().status === 'playing') {
          this.#replay.pause();
        } else {
          this.#replay.play();
        }
        break;
      case 'play':
        this.#replay.play();
        break;
      case 'pause':
        this.#replay.pause();
        break;
      case 'next':
        this.#replay.next();
        break;
      case 'prev':
        this.#replay.prev();
        break;
      case 'reset':
        this.#replay.resetReplay();
        break;
      case 'live':
        this.#replay.goLive();
        break;
      case 'speed':
        this.#replay.setSpeed(/** @type {number} */ (payload.speed));
        break;
      case 'jump': {
        const raw = /** @type {number} */ (payload.date);
        if (!Number.isFinite(raw)) break;
        const aligned = alignToTimeframe(raw, this.#timeframe);
        this.#replay.jumpToDate(aligned);
        break;
      }
      default:
        break;
    }
  }

  #syncSelectors() {
    const sym = this.#container?.querySelector('#chart-symbol');
    const tf = this.#container?.querySelector('#chart-timeframe');
    if (sym) /** @type {HTMLSelectElement} */ (sym).value = this.#symbol;
    if (tf) /** @type {HTMLSelectElement} */ (tf).value = this.#timeframe;
  }

  async #refreshDatasetSelectors() {
    this.#runnableDatasets = await DataManager.listRunnableDatasets();
    const symSel = this.#container?.querySelector('#chart-symbol');
    const tfSel = this.#container?.querySelector('#chart-timeframe');
    if (!symSel || !tfSel) return;

    const resolved = fillDatasetSelectors(
      /** @type {HTMLSelectElement} */ (symSel),
      /** @type {HTMLSelectElement} */ (tfSel),
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );
    if (resolved.symbol) this.#symbol = resolved.symbol;
    if (resolved.timeframe) this.#timeframe = resolved.timeframe;
  }

  #syncTimeframeOptions() {
    const tfSel = this.#container?.querySelector('#chart-timeframe');
    if (!tfSel) return;

    const resolved = resolveDatasetSelection(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );
    this.#timeframe = resolved.timeframe ?? this.#timeframe;

    tfSel.innerHTML = '';
    for (const opt of buildTimeframeOptions(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    )) {
      tfSel.appendChild(opt);
    }
    if (this.#timeframe) /** @type {HTMLSelectElement} */ (tfSel).value = this.#timeframe;
  }

  #clearSignalContext() {
    const hadSignal = this.#activeSignal != null;
    this.#activeSignal = null;
    this.#pendingSignal = null;
    this.#chart?.clearSignalOverlay();
    this.#applySignalEmaMode(false);

    const panel = this.#container?.querySelector('#chart-signal-panel');
    if (panel) {
      panel.hidden = true;
      panel.innerHTML = '';
    }
    const legend = this.#container?.querySelector('#chart-setup-legend');
    if (legend) {
      legend.hidden = true;
      legend.innerHTML = '';
    }

    this.#container?.querySelector('#chart-view-root')?.classList.remove('chart-signal-active');
    this.#container?.querySelector('#chart-body')?.classList.remove('chart-signal-active');

    if (hadSignal) {
      bus.emit(Events.CHART_SIGNAL_REVIEW, { active: false });
    }
  }

  #dismissSignalReview() {
    this.#clearSignalContext();
    const candles = this.#replay?.getVisibleCandles();
    if (candles?.length) {
      this.#chart?.setCandles(candles, { fit: true });
    }
    const status = this.#container?.querySelector('#chart-status');
    if (status && this.#replay) {
      const total = this.#replay.getState().total ?? candles?.length ?? 0;
      status.textContent = `${candles?.length.toLocaleString() ?? 0} / ${total.toLocaleString()} candles`;
    }
  }

  /**
   * @param {boolean} hideForSignal
   */
  #applySignalEmaMode(hideForSignal) {
    const checkbox = this.#container?.querySelector('#chart-ema');
    if (hideForSignal) {
      if (this.#emaRestore === null) {
        this.#emaRestore = /** @type {HTMLInputElement} */ (checkbox)?.checked ?? true;
      }
      if (checkbox) /** @type {HTMLInputElement} */ (checkbox).checked = false;
      this.#chart?.setEmaVisible(false);
    } else if (this.#emaRestore !== null) {
      if (checkbox) /** @type {HTMLInputElement} */ (checkbox).checked = this.#emaRestore;
      this.#chart?.setEmaVisible(this.#emaRestore);
      this.#emaRestore = null;
    }
  }

  /**
   * @param {import('../utils/chartNavigation.js').ChartSignalHighlight} signal
   */
  #showSignalPanel(signal) {
    const panel = this.#container?.querySelector('#chart-signal-panel');
    if (!panel) return;

    panel.hidden = false;
    panel.innerHTML = '';

    this.#container?.querySelector('#chart-view-root')?.classList.add('chart-signal-active');
    this.#container?.querySelector('#chart-body')?.classList.add('chart-signal-active');
    bus.emit(Events.CHART_SIGNAL_REVIEW, { active: true });

    const header = el('div', { class: 'chart-signal-panel-head' }, [
      el('div', { class: 'chart-signal-panel-title' }, [
        el('span', { class: 'chart-signal-chip chart-signal-chip-strategy' }, [signal.strategyName]),
        el('span', { class: `chart-signal-dir chart-signal-dir-${signal.direction}` }, [
          signal.direction.toUpperCase(),
        ]),
      ]),
      el('button', {
        type: 'button',
        class: 'btn btn-sm chart-signal-close',
        title: 'Đóng hướng dẫn signal',
      }, ['×']),
    ]);
    header.querySelector('.chart-signal-close')?.addEventListener('click', () => this.#dismissSignalReview());
    panel.appendChild(header);

    const meta = [
      el('span', { class: 'chart-signal-meta-item' }, [signal.symbol]),
      el('span', { class: 'chart-signal-meta-item' }, [signal.timeframe]),
    ];
    if (signal.candleIndex != null) {
      meta.push(el('span', { class: 'chart-signal-meta-item' }, [`Bar ${signal.candleIndex}`]));
    }
    meta.push(el('span', { class: 'chart-signal-meta-item chart-signal-meta-time' }, [
      formatTimestamp(signal.time),
    ]));
    if (signal.score != null) {
      meta.push(el('span', { class: 'chart-signal-meta-item chart-signal-meta-score' }, [
        `AI ${Math.round(signal.score)}/100`,
      ]));
    }
    panel.appendChild(el('div', { class: 'chart-signal-meta' }, meta));

    if (signal.reason) {
      panel.appendChild(el('p', { class: 'chart-signal-reason' }, [signal.reason]));
    }

    panel.appendChild(el('div', { class: 'chart-signal-levels-grid' }, [
      el('div', { class: 'chart-signal-level' }, [
        el('span', { class: 'chart-signal-level-label' }, ['Entry']),
        el('span', { class: 'chart-signal-level-value' }, [signal.entry.toFixed(5)]),
      ]),
      el('div', { class: 'chart-signal-level' }, [
        el('span', { class: 'chart-signal-level-label' }, ['SL']),
        el('span', { class: 'chart-signal-level-value chart-signal-level-sl' }, [signal.sl.toFixed(5)]),
      ]),
      el('div', { class: 'chart-signal-level' }, [
        el('span', { class: 'chart-signal-level-label' }, ['TP']),
        el('span', { class: 'chart-signal-level-value chart-signal-level-tp' }, [signal.tp.toFixed(5)]),
      ]),
      el('div', { class: 'chart-signal-level' }, [
        el('span', { class: 'chart-signal-level-label' }, ['RR']),
        el('span', { class: 'chart-signal-level-value' }, [`${signal.rr.toFixed(1)}R`]),
      ]),
    ]));

    if (signal.setup?.steps?.length) {
      panel.appendChild(el('div', { class: 'chart-signal-steps-wrap' }, [
        el('span', { class: 'chart-signal-steps-title' }, ['Các bước setup']),
        el('ol', { class: 'chart-signal-steps' }, signal.setup.steps.map((step) =>
          el('li', {}, [step])
        )),
      ]));
    }

    panel.appendChild(el('p', { class: 'chart-signal-hint' }, [
      'Replay dừng tại nến signal. Dùng ← → để xem từng bước (không lộ tương lai). EMA ẩn khi xem signal.',
    ]));
  }

  /**
   * @param {import('../utils/chartNavigation.js').ChartSignalHighlight} signal
   */
  #renderSetupLegend(signal) {
    const legend = this.#container?.querySelector('#chart-setup-legend');
    if (!legend) return;

    const items = [];

    for (const level of signal.setup?.levels ?? []) {
      const style = SETUP_LEVEL_STYLES[level.kind] ?? { color: '#94a3b8' };
      items.push(el('span', { class: 'chart-legend-item' }, [
        el('span', { class: 'chart-legend-swatch', style: `background:${style.color}` }),
        level.label,
      ]));
    }

    for (const [key, style] of Object.entries(TRADE_LEVEL_STYLES)) {
      items.push(el('span', { class: 'chart-legend-item' }, [
        el('span', { class: 'chart-legend-swatch', style: `background:${style.color}` }),
        style.title,
      ]));
    }

    for (const m of signal.setup?.markers ?? []) {
      const color = MARKER_ROLE_COLORS[m.role ?? 'entry'] ?? '#94a3b8';
      items.push(el('span', { class: 'chart-legend-item' }, [
        el('span', { class: 'chart-legend-dot', style: `background:${color}` }),
        m.label,
      ]));
    }

    if (items.length === 0) {
      legend.hidden = true;
      return;
    }

    legend.hidden = false;
    legend.innerHTML = '';
    legend.appendChild(el('span', { class: 'chart-legend-title' }, ['Chú thích:']));
    legend.appendChild(el('div', { class: 'chart-legend-items' }, items));
  }
}

export const ChartView = new ChartViewImpl();
