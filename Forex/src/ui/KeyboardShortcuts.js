/**
 * Global keyboard shortcut handler.
 * @module ui/KeyboardShortcuts
 */

import { bus, Events } from '../core/EventBus.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('KeyboardShortcuts');

/** Shortcut registry: key combo → action name. */
const SHORTCUTS = {
  'ctrl+b': () => bus.emit(Events.SIDEBAR_TOGGLE),
  'ctrl+1': () => bus.emit(Events.NAVIGATE, { view: 'chart' }),
  'ctrl+2': () => bus.emit(Events.NAVIGATE, { view: 'data' }),
  'ctrl+3': () => bus.emit(Events.NAVIGATE, { view: 'strategy' }),
  'ctrl+4': () => bus.emit(Events.NAVIGATE, { view: 'simulation' }),
  'ctrl+5': () => bus.emit(Events.NAVIGATE, { view: 'statistics' }),
  'ctrl+6': () => bus.emit(Events.NAVIGATE, { view: 'reports' }),
};

/**
 * Keyboard shortcuts module.
 */
const KeyboardShortcuts = {
  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    document.addEventListener('keydown', this.#handleKeydown);
    log.info('Keyboard shortcuts active');
  },

  /**
   * @param {KeyboardEvent} e
   */
  #handleKeydown(e) {
    const parts = [];
    if (e.ctrlKey || e.metaKey) parts.push('ctrl');
    if (e.shiftKey) parts.push('shift');
    if (e.altKey) parts.push('alt');
    parts.push(e.key.toLowerCase());

    const combo = parts.join('+');
    const action = SHORTCUTS[combo];

    if (action) {
      e.preventDefault();
      action();
    }
  },
};

export default KeyboardShortcuts;
