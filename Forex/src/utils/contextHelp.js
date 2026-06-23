/**
 * Context-sensitive help — open docs for the current view or section.
 * @module utils/contextHelp
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from './dom.js';

/**
 * Open the slide-over help panel for a documentation section id.
 * @param {string} contextId — section id (chart, data, strategy, …)
 */
export function openContextHelp(contextId) {
  bus.emit(Events.DOCS_OPEN, { section: contextId });
}

/**
 * Toolbar help button tied to a documentation section.
 * @param {string} contextId
 * @param {string} [label]
 * @returns {HTMLButtonElement}
 */
export function createHelpButton(contextId, label = '📖 Hướng dẫn') {
  const btn = el('button', {
    class: 'btn btn-sm btn-help',
    type: 'button',
    title: 'Giải thích chi tiết mục này',
  }, [label]);
  btn.addEventListener('click', () => openContextHelp(contextId));
  return btn;
}
