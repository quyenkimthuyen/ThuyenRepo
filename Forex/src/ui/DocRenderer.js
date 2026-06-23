/**
 * Shared documentation block renderer.
 * @module ui/DocRenderer
 */

import { el } from '../utils/dom.js';

/**
 * @param {import('../content/contextDocsVi.js').DocBlock} block
 * @returns {HTMLElement}
 */
export function renderDocBlock(block) {
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

/**
 * @param {HTMLElement} container
 * @param {import('../content/contextDocsVi.js').DocSection} section
 */
export function renderDocSection(container, section) {
  container.innerHTML = '';
  container.appendChild(el('h3', { class: 'docs-section-title' }, [
    `${section.icon} ${section.title}`,
  ]));
  if (section.subtitle) {
    container.appendChild(el('p', { class: 'docs-p docs-subtitle' }, [section.subtitle]));
  }
  for (const block of section.blocks) {
    container.appendChild(renderDocBlock(block));
  }
}
