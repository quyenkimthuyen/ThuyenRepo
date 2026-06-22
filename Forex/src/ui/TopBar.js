/**
 * Top navigation bar with app branding and quick actions.
 * @module ui/TopBar
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';

/**
 * TopBar component factory.
 */
export const TopBar = {
  /**
   * Render the top bar element.
   * @returns {HTMLElement}
   */
  render() {
    return el('header', { class: 'topbar' }, [
      el('div', { class: 'topbar-left' }, [
        el('button', {
          class: 'btn-icon sidebar-toggle',
          title: 'Toggle sidebar (Ctrl+B)',
          'aria-label': 'Toggle sidebar',
        }, ['☰']),
        el('span', { class: 'app-logo' }, [Config.APP_SHORT_NAME]),
        el('span', { class: 'app-title' }, [Config.APP_NAME]),
      ]),
      el('div', { class: 'topbar-center' }, [
        el('span', { class: 'symbol-badge' }, [Config.DEFAULT_SYMBOL]),
        el('span', { class: 'timeframe-badge' }, [Config.DEFAULT_TIMEFRAME]),
      ]),
      el('div', { class: 'topbar-right' }, [
        el('button', {
          class: 'btn-icon docs-btn',
          title: 'Documentation (Ctrl+9 / F1)',
          'aria-label': 'Documentation',
        }, ['📖']),
        el('span', { class: 'version-tag' }, [`v${Config.APP_VERSION}`]),
      ]),
    ]);
  },

  /**
   * Attach event listeners after DOM insertion.
   * @param {HTMLElement} shell
   */
  init(shell) {
    const toggle = shell.querySelector('.sidebar-toggle');
    toggle?.addEventListener('click', () => bus.emit(Events.SIDEBAR_TOGGLE));

    const docsBtn = shell.querySelector('.docs-btn');
    docsBtn?.addEventListener('click', () => bus.emit(Events.NAVIGATE, { view: 'docs' }));
  },
};
