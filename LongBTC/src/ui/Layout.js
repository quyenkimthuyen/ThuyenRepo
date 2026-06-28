/**
 * Main layout shell — LongBTC research views.
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
import { AnalysisDashboardView } from './AnalysisDashboardView.js';
import { CycleView } from './CycleView.js';
import { TrendView } from './TrendView.js';
import { ElliottView } from './ElliottView.js';
import { PsychologyView } from './PsychologyView.js';
import { DocsView } from './DocsView.js';
import { ContextHelpPanel } from './ContextHelpPanel.js';
import { setActiveView } from './activeView.js';

const log = createLogger('Layout');

/** Navigation views for BTC long-term research. */
const VIEWS = [
  { id: 'chart', label: 'Biểu đồ BTC', icon: '📈' },
  { id: 'dashboard', label: 'Tổng quan', icon: '🏠' },
  { id: 'cycle', label: 'Chu kỳ 4 năm', icon: '🔄' },
  { id: 'trend', label: 'Xu hướng', icon: '📊' },
  { id: 'elliott', label: 'Sóng Elliott', icon: '🌊' },
  { id: 'psychology', label: 'Tâm lý TT', icon: '🧠' },
  { id: 'data', label: 'Data Manager', icon: '💾' },
  { id: 'docs', label: 'Tài liệu', icon: '📖' },
];

/** @type {Record<string, { mount: Function, unmount?: Function }>} */
const VIEW_MAP = {
  chart: ChartView,
  dashboard: AnalysisDashboardView,
  cycle: CycleView,
  trend: TrendView,
  elliott: ElliottView,
  psychology: PsychologyView,
  data: DataManagerView,
  docs: DocsView,
};

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
    log.info('Building LongBTC layout shell');
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

    const viewModule = VIEW_MAP[viewId];
    if (viewModule) {
      placeholder.className = 'panel-body';
      this.#activeView = viewModule;
      if (viewId === 'docs') {
        viewModule.mount(placeholder, docsSection);
      } else {
        viewModule.mount(placeholder);
      }
    } else {
      const view = VIEWS.find((v) => v.id === viewId);
      placeholder.append(
        el('h2', { class: 'view-title' }, [view?.label ?? viewId]),
        el('p', { class: 'view-desc' }, ['Module đang phát triển.'])
      );
    }

    bus.emit(Events.VIEW_ACTIVE, { view: viewId });
  }
}

export default new Layout();
