/**
 * Main layout shell — assembles TopBar, Sidebar, content panels, and StatusBar.
 * @module ui/Layout
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, $, loadFromStorage, saveToStorage } from '../utils/dom.js';
import { createLogger } from '../utils/logger.js';
import { TopBar } from './TopBar.js';
import { Sidebar } from './Sidebar.js';
import { StatusBar } from './StatusBar.js';
import { PanelManager } from './PanelManager.js';
import { DataManagerView } from './DataManagerView.js';
import { ChartView } from './ChartView.js';
import { StrategyView } from './StrategyView.js';
import { SimulationView } from './SimulationView.js';
import { StatisticsView } from './StatisticsView.js';
import { ReportsView } from './ReportsView.js';
import { OptimizerView } from './OptimizerView.js';
import { SignalsView } from './SignalsView.js';
import { DocsView } from './DocsView.js';
import { ContextHelpPanel } from './ContextHelpPanel.js';
import { setActiveView } from './activeView.js';

const log = createLogger('Layout');

/** Navigation views available in Phase 1. */
const VIEWS = [
  { id: 'chart', label: 'Chart', icon: '📈' },
  { id: 'data', label: 'Data Manager', icon: '💾' },
  { id: 'strategy', label: 'Strategies', icon: '⚙️' },
  { id: 'simulation', label: 'Simulation', icon: '🔬' },
  { id: 'statistics', label: 'Statistics', icon: '📊' },
  { id: 'reports', label: 'Reports', icon: '📋' },
  { id: 'optimizer', label: 'Optimizer', icon: '🧪' },
  { id: 'signals', label: 'AI Signals', icon: '🎯' },
  { id: 'docs', label: 'Tài liệu', icon: '📖' },
];

/**
 * Layout module — builds the professional trading shell.
 */
class Layout {
  /** @type {string} */
  currentView = 'chart';

  /** @type {{ unmount?: Function }|null} */
  #activeView = null;

  /**
   * Initialize the layout inside #app.
   * @param {{ bus: import('../core/EventBus.js').EventBus }} ctx
   */
  async initialize({ bus: eventBus }) {
    log.info('Building layout shell');
    const root = $('#app');
    root.innerHTML = '';
    root.className = 'app-shell';

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    const collapsed = settings.sidebarCollapsed ?? false;

    const shell = el('div', { class: 'shell', dataset: { collapsed: String(collapsed) } }, [
      TopBar.render(),
      el('div', { class: 'shell-body' }, [
        Sidebar.render(VIEWS, collapsed),
        el('main', { class: 'main-content', id: 'main-content' }, [
          PanelManager.render(),
        ]),
      ]),
      StatusBar.render(),
    ]);

    root.appendChild(shell);

    TopBar.init(shell);
    Sidebar.init(shell, VIEWS);
    PanelManager.init(shell);
    StatusBar.init(shell);
    ContextHelpPanel.init(document.body);

    this.#bindEvents(eventBus);
    this.#navigate('chart');
    log.info('Layout ready');
  }

  /**
   * @param {import('../core/EventBus.js').EventBus} eventBus
   */
  #bindEvents(eventBus) {
    eventBus.on(Events.NAVIGATE, ({ view, section }) => this.#navigate(view, section));
    eventBus.on(Events.SIDEBAR_TOGGLE, () => {
      const shell = $('.shell');
      const collapsed = shell.dataset.collapsed === 'true';
      shell.dataset.collapsed = String(!collapsed);
      const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
      saveToStorage(Config.STORAGE_KEYS.SETTINGS, {
        ...settings,
        sidebarCollapsed: !collapsed,
      });
    });
  }

  /**
   * Switch the active view in the main content area.
   * @param {string} viewId
   * @param {string} [docsSection]
   */
  #navigate(viewId, docsSection) {
    this.currentView = viewId;
    setActiveView(viewId);

    document.querySelectorAll('.nav-item').forEach((item) => {
      item.classList.toggle('active', item.dataset.view === viewId);
    });

    const placeholder = $('#view-placeholder');
    this.#activeView?.unmount?.();
    this.#activeView = null;
    placeholder.innerHTML = '';
    placeholder.className = 'panel-body panel-body-fill';

    if (viewId === 'data') {
      placeholder.className = 'panel-body';
      this.#activeView = DataManagerView;
      DataManagerView.mount(placeholder);
    } else if (viewId === 'chart') {
      placeholder.className = 'panel-body';
      this.#activeView = ChartView;
      ChartView.mount(placeholder);
    } else if (viewId === 'strategy') {
      placeholder.className = 'panel-body';
      this.#activeView = StrategyView;
      StrategyView.mount(placeholder);
    } else if (viewId === 'simulation') {
      placeholder.className = 'panel-body';
      this.#activeView = SimulationView;
      SimulationView.mount(placeholder);
    } else if (viewId === 'statistics') {
      placeholder.className = 'panel-body';
      this.#activeView = StatisticsView;
      StatisticsView.mount(placeholder);
    } else if (viewId === 'reports') {
      placeholder.className = 'panel-body';
      this.#activeView = ReportsView;
      ReportsView.mount(placeholder);
    } else if (viewId === 'optimizer') {
      placeholder.className = 'panel-body';
      this.#activeView = OptimizerView;
      OptimizerView.mount(placeholder);
    } else if (viewId === 'signals') {
      placeholder.className = 'panel-body';
      this.#activeView = SignalsView;
      SignalsView.mount(placeholder);
    } else if (viewId === 'docs') {
      placeholder.className = 'panel-body';
      this.#activeView = DocsView;
      DocsView.mount(placeholder, docsSection);
    } else {
      const view = VIEWS.find((v) => v.id === viewId);
      const title = el('h2', { class: 'view-title' }, [view?.label ?? viewId]);
      const desc = el('p', { class: 'view-desc' }, [
        this.#getViewDescription(viewId),
      ]);
      const badge = el('span', { class: 'phase-badge' }, [
        this.#getPhaseBadge(viewId),
      ]);
      placeholder.append(title, desc, badge);
    }

    bus.emit(Events.VIEW_ACTIVE, { view: viewId });
  }

  /**
   * @param {string} viewId
   * @returns {string}
   */
  #getPhaseBadge(viewId) {
    if (viewId === 'chart') return 'Phase 3 — Chart & Replay active';
    if (viewId === 'data') return 'Phase 2 — Data Manager active';
    if (viewId === 'strategy') return 'Phase 5 — Price Action setups active';
    if (viewId === 'simulation') return 'Phase 6 — Trade Engine active';
    if (viewId === 'statistics') return 'Phase 7 — Statistics active';
    if (viewId === 'reports') return 'Phase 8 — Dashboard & Reports active';
    if (viewId === 'optimizer') return 'Phase 9 — Optimizer active';
    if (viewId === 'signals') return 'Phase 10 — AI Scoring active';
    if (viewId === 'docs') return 'Documentation & usage guide';
    return 'Coming in a future phase';
  }

  /**
   * @param {string} viewId
   * @returns {string}
   */
  #getViewDescription(viewId) {
    const descriptions = {
      chart: 'Professional candlestick chart with replay, drawing tools, and trade markers.',
      data: 'Download, store, and manage historical OHLCV data locally via IndexedDB.',
      strategy: 'Plugin-based Price Action strategy engine with configurable parameters.',
      simulation: 'Backtest setups across pairs, timeframes, and parameter combinations.',
      statistics: 'Expectancy, profit factor, drawdown, and performance analytics.',
      reports: 'Export results as CSV, JSON, PNG, or PDF reports.',
      optimizer: 'Grid search, walk-forward validation, and Monte Carlo risk analysis.',
      signals: 'AI signal scores with trend, momentum, session, and PA quality factors.',
      docs: 'Installation, usage guide, keyboard shortcuts, and FAQ.',
    };
    return descriptions[viewId] ?? 'Module under development.';
  }
}

export default new Layout();
