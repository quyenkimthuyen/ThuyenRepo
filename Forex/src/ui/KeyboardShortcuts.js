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
  'ctrl+4': () => bus.emit(Events.NAVIGATE, { view: 'compare' }),
  'ctrl+5': () => bus.emit(Events.NAVIGATE, { view: 'simulation' }),
  'ctrl+6': () => bus.emit(Events.NAVIGATE, { view: 'statistics' }),
  'ctrl+7': () => bus.emit(Events.NAVIGATE, { view: 'reports' }),
  'ctrl+8': () => bus.emit(Events.NAVIGATE, { view: 'optimizer' }),
  'ctrl+9': () => bus.emit(Events.NAVIGATE, { view: 'signals' }),
  'ctrl+0': () => bus.emit(Events.NAVIGATE, { view: 'docs' }),
  'f1': () => bus.emit(Events.NAVIGATE, { view: 'docs' }),
};

/** Chart replay shortcuts — only when chart view is active. */
const CHART_SHORTCUTS = {
  ' ': () => bus.emit(Events.REPLAY_COMMAND, { action: 'toggle-play' }),
  'arrowright': () => bus.emit(Events.REPLAY_COMMAND, { action: 'next' }),
  'arrowleft': () => bus.emit(Events.REPLAY_COMMAND, { action: 'prev' }),
  'home': () => bus.emit(Events.REPLAY_COMMAND, { action: 'reset' }),
  'end': () => bus.emit(Events.REPLAY_COMMAND, { action: 'live' }),
};

/**
 * Keyboard shortcuts module.
 */
class KeyboardShortcuts {
  /** @type {string} */
  activeView = 'chart';

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} ctx
   */
  async initialize(ctx) {
    ctx.bus.on(Events.VIEW_ACTIVE, ({ view }) => {
      this.activeView = view;
    });
    document.addEventListener('keydown', (e) => this.#handleKeydown(e));
    log.info('Keyboard shortcuts active');
  }

  /**
   * @param {KeyboardEvent} e
   */
  #handleKeydown(e) {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      return;
    }

    const parts = [];
    if (e.ctrlKey || e.metaKey) parts.push('ctrl');
    if (e.shiftKey) parts.push('shift');
    if (e.altKey) parts.push('alt');
    parts.push(e.key.toLowerCase());

    const combo = parts.join('+');

    const globalAction = SHORTCUTS[combo];
    if (globalAction) {
      e.preventDefault();
      globalAction();
      return;
    }

    if (this.activeView === 'chart') {
      const chartAction = CHART_SHORTCUTS[combo];
      if (chartAction) {
        e.preventDefault();
        chartAction();
      }
    }
  }
}

export default new KeyboardShortcuts();
