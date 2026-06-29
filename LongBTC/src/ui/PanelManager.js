/**
 * Resizable panel manager for the main content area.
 * @module ui/PanelManager
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, clamp, loadFromStorage, saveToStorage } from '../utils/dom.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('PanelManager');

/**
 * Manages resizable split panels in the main workspace.
 */
class PanelManagerImpl {
  /** @type {number} */
  bottomPanelHeight = 200;

  /**
   * Render the panel layout.
   * @returns {HTMLElement}
   */
  render() {
    const saved = loadFromStorage(Config.STORAGE_KEYS.PANEL_SIZES, {
      bottom: 200,
    });

    this.bottomPanelHeight = saved.bottom ?? 200;

    return el('div', { class: 'panel-workspace', id: 'panel-workspace' }, [
      el('div', { class: 'panel-row panel-row-top' }, [
        el('div', { class: 'panel panel-center', id: 'panel-center' }, [
          el('div', { class: 'panel-header' }, [
            el('span', { class: 'panel-title' }, ['Workspace']),
          ]),
          el('div', { class: 'panel-body panel-body-fill', id: 'view-placeholder' }),
        ]),
      ]),
      el('div', { class: 'resize-handle resize-h', 'data-resize': 'bottom' }),
      el('div', {
        class: 'panel panel-bottom',
        id: 'panel-bottom',
        style: `height: ${this.bottomPanelHeight}px`,
      }, [
        el('div', { class: 'panel-header' }, [
          el('span', { class: 'panel-title' }, ['Output / Log']),
        ]),
        el('div', { class: 'panel-body panel-log', id: 'panel-log' }, [
          el('div', { class: 'log-entry log-info' }, [
            `[${new Date().toLocaleTimeString()}] ${Config.APP_NAME} initialized.`,
          ]),
          el('div', { class: 'log-entry' }, [
            'Pipeline: Chu k\u1ef3 4 n\u0103m \u2192 Xu h\u01b0\u1edbng \u2192 Elliott \u2192 T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng.',
          ]),
        ]),
      ]),
    ]);
  }

  /**
   * Attach resize drag handlers.
   * @param {HTMLElement} shell
   */
  init(shell) {
    const workspace = shell.querySelector('.panel-workspace');
    if (!workspace) return;

    workspace.querySelectorAll('.resize-handle').forEach((handle) => {
      handle.addEventListener('mousedown', (e) => this.#startResize(e, handle, workspace));
    });

    bus.on(Events.VIEW_ACTIVE, ({ view }) => this.#onViewActive(view));
    bus.on(Events.LOG_MESSAGE, ({ message, level, time }) => {
      this.#appendLog(message, level, time);
    });

    log.info('Panel manager initialized');
  }

  /**
   * Chart view uses full workspace height (no log strip).
   * @param {string} viewId
   */
  #onViewActive(viewId) {
    const workspace = document.getElementById('panel-workspace');
    if (!workspace) return;
    workspace.classList.toggle('chart-fullbleed', viewId === 'chart');
  }

  /**
   * @param {string} message
   * @param {string} [level='info']
   * @param {Date} [time=new Date()]
   */
  #appendLog(message, level = 'info', time = new Date()) {
    const logPanel = document.getElementById('panel-log');
    if (!logPanel) return;

    const entry = el('div', { class: `log-entry log-${level}` }, [
      `[${time.toLocaleTimeString()}] ${message}`,
    ]);
    logPanel.appendChild(entry);
    logPanel.scrollTop = logPanel.scrollHeight;
  }

  /**
   * @param {MouseEvent} e
   * @param {HTMLElement} handle
   * @param {HTMLElement} workspace
   */
  #startResize(e, handle, workspace) {
    e.preventDefault();
    const direction = handle.dataset.resize;
    const startY = e.clientY;
    const startBottom = this.bottomPanelHeight;

    document.body.classList.add('resizing');

    /**
     * @param {MouseEvent} moveEvent
     */
    const onMove = (moveEvent) => {
      if (direction === 'bottom') {
        const delta = startY - moveEvent.clientY;
        this.bottomPanelHeight = clamp(
          startBottom + delta,
          Config.LAYOUT.PANEL_MIN_HEIGHT,
          workspace.clientHeight * 0.6
        );
        const panel = workspace.querySelector('#panel-bottom');
        if (panel) panel.style.height = `${this.bottomPanelHeight}px`;
      }

      bus.emit(Events.PANEL_RESIZE, {
        bottom: this.bottomPanelHeight,
      });
    };

    const onUp = () => {
      document.body.classList.remove('resizing');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      saveToStorage(Config.STORAGE_KEYS.PANEL_SIZES, {
        bottom: this.bottomPanelHeight,
      });
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }
}

export const PanelManager = new PanelManagerImpl();
