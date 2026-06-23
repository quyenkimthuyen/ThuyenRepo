/**
 * In-app documentation — full Vietnamese guide with per-view sections.
 * @module ui/DocsView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { CONTEXT_DOC_SECTIONS } from '../content/contextDocsVi.js';
import { renderDocBlock } from './DocRenderer.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('DocsView');

/** @type {string} */
let activeSection = CONTEXT_DOC_SECTIONS[0]?.id ?? 'overview';

/**
 * @param {string} sectionId
 */
export function setDocsSection(sectionId) {
  if (CONTEXT_DOC_SECTIONS.some((s) => s.id === sectionId)) {
    activeSection = sectionId;
  }
}

/**
 * Documentation view controller.
 */
class DocsViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /**
   * @param {HTMLElement} container
   * @param {string} [sectionId]
   */
  async mount(container, sectionId) {
    if (sectionId) setDocsSection(sectionId);
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    container.appendChild(el('div', { class: 'docs-view' }, [
      el('div', { class: 'docs-header' }, [
        el('h2', { class: 'docs-title' }, ['Tài liệu hướng dẫn']),
        el('span', { class: 'docs-version' }, [`${Config.APP_NAME} v${Config.APP_VERSION}`]),
      ]),
      el('div', { class: 'docs-body' }, [
        el('nav', { class: 'docs-nav', id: 'docs-nav' }, this.#renderNav()),
        el('article', { class: 'docs-content', id: 'docs-content' }),
      ]),
    ]));

    this.#renderSection();
    log.info('Docs view mounted');
  }

  unmount() {
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.add('panel-body-fill');
    }
  }

  /**
   * @returns {HTMLElement[]}
   */
  #renderNav() {
    return CONTEXT_DOC_SECTIONS.map((section) => {
      const btn = el('button', {
        class: `docs-nav-item${section.id === activeSection ? ' active' : ''}`,
        dataset: { section: section.id },
      }, [
        el('span', { class: 'docs-nav-icon' }, [section.icon]),
        el('span', { class: 'docs-nav-label' }, [section.title]),
      ]);

      btn.addEventListener('click', () => {
        activeSection = section.id;
        this.#container?.querySelectorAll('.docs-nav-item').forEach((item) => {
          item.classList.toggle('active', item.dataset.section === activeSection);
        });
        this.#renderSection();
      });

      return btn;
    });
  }

  #renderSection() {
    const content = this.#container?.querySelector('#docs-content');
    const section = CONTEXT_DOC_SECTIONS.find((s) => s.id === activeSection);
    if (!content || !section) return;

    content.innerHTML = '';
    content.appendChild(el('h3', { class: 'docs-section-title' }, [
      `${section.icon} ${section.title}`,
    ]));
    if (section.subtitle) {
      content.appendChild(el('p', { class: 'docs-p docs-subtitle' }, [section.subtitle]));
    }

    for (const block of section.blocks) {
      content.appendChild(renderDocBlock(block));
    }
  }
}

export const DocsView = new DocsViewImpl();

bus.on(Events.NAVIGATE, ({ view, section }) => {
  if (view === 'docs' && section) setDocsSection(section);
});
