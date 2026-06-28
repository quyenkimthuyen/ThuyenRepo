/**
 * Left sidebar navigation with collapsible state.
 * @module ui/Sidebar
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';

/**
 * Sidebar navigation component.
 */
export const Sidebar = {
  /**
   * Render the sidebar element.
   * @param {Array<{id: string, label: string, icon: string}>} views
   * @param {boolean} collapsed
   * @returns {HTMLElement}
   */
  render(views, collapsed) {
    const navItems = views.map((view) =>
      el('button', {
        class: `nav-item${view.id === 'chart' ? ' active' : ''}`,
        dataset: { view: view.id },
        title: view.label,
      }, [
        el('span', { class: 'nav-icon' }, [view.icon]),
        el('span', { class: 'nav-label' }, [view.label]),
      ])
    );

    return el('aside', { class: 'sidebar', 'aria-label': 'Main navigation' }, [
      el('nav', { class: 'sidebar-nav' }, navItems),
      el('div', { class: 'sidebar-footer' }, [
        el('span', { class: 'sidebar-footer-text' }, ['BTC Research']),
      ]),
    ]);
  },

  /**
   * Attach navigation click handlers.
   * @param {HTMLElement} shell
   * @param {Array<{id: string}>} views
   */
  init(shell, views) {
    shell.querySelectorAll('.nav-item').forEach((item) => {
      item.addEventListener('click', () => {
        const view = item.dataset.view;
        if (view) bus.emit(Events.NAVIGATE, { view });
      });
    });
  },
};
