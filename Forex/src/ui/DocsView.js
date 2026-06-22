/**
 * In-app documentation and usage guide.
 * @module ui/DocsView
 */

import { Config } from '../core/Config.js';
import { el } from '../utils/dom.js';
import { DOC_SECTIONS } from '../content/appDocs.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('DocsView');

/** @type {string} */
let activeSection = DOC_SECTIONS[0]?.id ?? 'overview';

/**
 * Documentation view controller.
 */
class DocsViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    container.appendChild(el('div', { class: 'docs-view' }, [
      el('div', { class: 'docs-header' }, [
        el('h2', { class: 'docs-title' }, ['Documentation']),
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
    return DOC_SECTIONS.map((section) => {
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
    const section = DOC_SECTIONS.find((s) => s.id === activeSection);
    if (!content || !section) return;

    content.innerHTML = '';
    content.appendChild(el('h3', { class: 'docs-section-title' }, [
      `${section.icon} ${section.title}`,
    ]));

    for (const block of section.blocks) {
      content.appendChild(this.#renderBlock(block));
    }
  }

  /**
   * @param {import('../content/appDocs.js').DocBlock} block
   * @returns {HTMLElement}
   */
  #renderBlock(block) {
    switch (block.type) {
      case 'h2':
        return el('h4', { class: 'docs-h2' }, [block.text ?? '']);
      case 'h3':
        return el('h4', { class: 'docs-h3' }, [block.text ?? '']);
      case 'p':
        return el('p', { class: 'docs-p' }, [block.text ?? '']);
      case 'ul':
        return el('ul', { class: 'docs-list' },
          (block.items ?? []).map((item) => el('li', {}, [item]))
        );
      case 'ol':
        return el('ol', { class: 'docs-list' },
          (block.items ?? []).map((item) => el('li', {}, [item]))
        );
      case 'code':
        return el('pre', { class: 'docs-code' }, [
          el('code', {}, [block.text ?? '']),
        ]);
      case 'callout':
        return el('div', { class: `docs-callout docs-callout-${block.variant ?? 'info'}` }, [
          block.text ?? '',
        ]);
      case 'steps':
        return el('div', { class: 'docs-steps' },
          (block.steps ?? []).map((step, i) =>
            el('div', { class: 'docs-step' }, [
              el('span', { class: 'docs-step-num' }, [String(i + 1)]),
              el('div', { class: 'docs-step-body' }, [
                el('strong', {}, [step.title]),
                el('p', {}, [step.body]),
              ]),
            ])
          )
        );
      case 'table': {
        const head = el('thead', {}, [
          el('tr', {}, (block.headers ?? []).map((h) => el('th', {}, [h]))),
        ]);
        const body = el('tbody', {},
          (block.rows ?? []).map((row) =>
            el('tr', {}, row.map((cell) => el('td', {}, [cell])))
          )
        );
        return el('div', { class: 'docs-table-wrap' }, [
          el('table', { class: 'docs-table' }, [head, body]),
        ]);
      }
      default:
        return el('div', {}, []);
    }
  }
}

export const DocsView = new DocsViewImpl();
