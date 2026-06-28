/**
 * Slide-over context help panel — Vietnamese docs for the active view.
 * @module ui/ContextHelpPanel
 */

import { bus, Events } from '../core/EventBus.js';
import { getLongBtcDoc } from '../content/longbtcDocsVi.js';
import { renderDocSection } from './DocRenderer.js';
import { el } from '../utils/dom.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ContextHelpPanel');

/** @type {HTMLElement|null} */
let backdrop = null;

/** @type {HTMLElement|null} */
let panel = null;

/** @type {HTMLElement|null} */
let contentEl = null;

/** @type {string|null} */
let currentSectionId = null;

/**
 * @param {string} sectionId
 */
function showSection(sectionId) {
  const section = getLongBtcDoc(sectionId);
  if (!section || !contentEl || !panel || !backdrop) return;

  currentSectionId = sectionId;
  renderDocSection(contentEl, section);
  panel.dataset.section = sectionId;
  backdrop.classList.add('open');
  panel.classList.add('open');
  panel.setAttribute('aria-hidden', 'false');
  log.info(`Context help opened: ${sectionId}`);
}

function close() {
  backdrop?.classList.remove('open');
  panel?.classList.remove('open');
  panel?.setAttribute('aria-hidden', 'true');
}

/**
 * Context help panel singleton.
 */
export const ContextHelpPanel = {
  /**
   * Mount panel into the document (once).
   * @param {HTMLElement} [root]
   */
  init(root = document.body) {
    if (panel) return;

    backdrop = el('div', { class: 'context-help-backdrop', id: 'context-help-backdrop' });
    contentEl = el('div', { class: 'context-help-content', id: 'context-help-content' });

    panel = el('aside', {
      class: 'context-help-panel',
      id: 'context-help-panel',
      role: 'dialog',
      'aria-label': 'Hướng dẫn sử dụng',
      'aria-hidden': 'true',
    }, [
      el('header', { class: 'context-help-header' }, [
        el('h2', { class: 'context-help-title' }, ['Hướng dẫn']),
        el('button', {
          class: 'btn-icon context-help-close',
          type: 'button',
          'aria-label': 'Đóng',
        }, ['✕']),
      ]),
      contentEl,
      el('footer', { class: 'context-help-footer' }, [
        el('button', {
          class: 'btn btn-sm btn-secondary',
          type: 'button',
          id: 'context-help-full-docs',
        }, ['📚 Xem tài liệu đầy đủ']),
      ]),
    ]);

    root.appendChild(backdrop);
    root.appendChild(panel);

    backdrop.addEventListener('click', close);
    panel.querySelector('.context-help-close')?.addEventListener('click', close);
    panel.querySelector('#context-help-full-docs')?.addEventListener('click', () => {
      close();
      bus.emit(Events.NAVIGATE, { view: 'docs', section: currentSectionId ?? 'overview' });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && panel?.classList.contains('open')) {
        e.preventDefault();
        close();
      }
    });

    bus.on(Events.DOCS_OPEN, ({ section }) => {
      if (section) showSection(section);
    });

    log.info('Context help panel ready');
  },
};
