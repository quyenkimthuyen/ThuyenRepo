/**
 * Replay control bar UI component.
 * @module ui/ReplayControls
 */

import { Config } from '../core/Config.js';
import { el } from '../utils/dom.js';
import {
  formatTimestamp,
  parseDatetimeLocalAsUtc,
  timestampToDatetimeLocalValue,
} from '../data/TimeframeUtils.js';
import { getSession, getSessionColor } from '../chart/SessionUtils.js';

/**
 * Replay toolbar with play/pause, step, speed, and jump controls.
 */
class ReplayControlsImpl {
  /** @type {HTMLElement|null} */
  #root = null;

  /** @type {Function|null} */
  #onAction = null;

  /**
   * Render the replay control bar.
   * @param {Function} onAction - Callback: (action: string, payload?: object) => void
   * @returns {HTMLElement}
   */
  render(onAction) {
    this.#onAction = onAction;

    this.#root = el('div', { class: 'replay-bar' }, [
      el('div', { class: 'replay-group replay-transport' }, [
        el('button', { class: 'btn btn-icon replay-btn', title: 'Previous candle (←)', dataset: { action: 'prev' } }, ['⏮']),
        el('button', { class: 'btn btn-icon replay-btn replay-play', title: 'Play/Pause (Space)', dataset: { action: 'toggle-play' } }, ['▶']),
        el('button', { class: 'btn btn-icon replay-btn', title: 'Next candle (→)', dataset: { action: 'next' } }, ['⏭']),
      ]),
      el('div', { class: 'replay-group replay-speed' }, [
        el('button', { class: 'btn btn-sm replay-speed-btn active', dataset: { action: 'speed', speed: String(Config.REPLAY.SPEED_NORMAL) } }, ['1x']),
        el('button', { class: 'btn btn-sm replay-speed-btn', dataset: { action: 'speed', speed: String(Config.REPLAY.SPEED_FAST) } }, ['4x']),
        el('button', { class: 'btn btn-sm replay-speed-btn', dataset: { action: 'speed', speed: String(Config.REPLAY.SPEED_ULTRA) } }, ['16x']),
      ]),
      el('div', { class: 'replay-group replay-jump' }, [
        el('input', {
          type: 'datetime-local',
          class: 'replay-date-input',
          id: 'replay-jump-date',
          title: 'Jump to date (UTC)',
        }),
        el('button', { class: 'btn btn-sm', dataset: { action: 'jump' } }, ['Jump']),
      ]),
      el('div', { class: 'replay-group replay-mode' }, [
        el('button', { class: 'btn btn-sm', dataset: { action: 'reset' } }, ['Reset']),
        el('button', { class: 'btn btn-sm btn-primary', dataset: { action: 'live' } }, ['Live']),
      ]),
      el('div', { class: 'replay-info' }, [
        el('span', { class: 'replay-progress', id: 'replay-progress' }, ['— / —']),
        el('span', { class: 'replay-ohlc', id: 'replay-ohlc' }, ['']),
        el('span', { class: 'replay-session', id: 'replay-session' }, ['']),
      ]),
    ]);

    this.#root.addEventListener('click', (e) => {
      const btn = /** @type {HTMLElement} */ (e.target).closest('[data-action]');
      if (!btn || !this.#onAction) return;

      const { action, speed } = btn.dataset;
      if (action === 'speed') {
        this.#onAction('speed', { speed: Number(speed) });
        this.#root?.querySelectorAll('.replay-speed-btn').forEach((b) => {
          b.classList.toggle('active', b.dataset.speed === speed);
        });
      } else if (action === 'jump') {
        const input = /** @type {HTMLInputElement} */ (
          this.#root?.querySelector('#replay-jump-date')
        );
        const date = input?.value ? parseDatetimeLocalAsUtc(input.value) : NaN;
        if (Number.isFinite(date)) {
          this.#onAction('jump', { date });
        }
      } else {
        this.#onAction(action);
      }
    });

    return this.#root;
  }

  /**
   * Update the progress and OHLC display.
   * @param {import('../replay/ReplayEngine.js').ReplayState} state
   * @param {import('../data/Candle.js').Candle} [candle]
   */
  /**
   * Sync the jump date field to a candle timestamp (UTC).
   * @param {number} timestamp
   */
  setJumpDate(timestamp) {
    const input = /** @type {HTMLInputElement|undefined} */ (
      this.#root?.querySelector('#replay-jump-date')
    );
    if (input && Number.isFinite(timestamp)) {
      input.value = timestampToDatetimeLocalValue(timestamp);
    }
  }

  update(state, candle) {
    const progress = document.getElementById('replay-progress');
    const ohlc = document.getElementById('replay-ohlc');
    const session = document.getElementById('replay-session');
    const playBtn = this.#root?.querySelector('.replay-play');

    if (progress) {
      const mode = state.mode === 'live' ? 'LIVE' : 'REPLAY';
      progress.textContent = `${mode} ${state.index + 1} / ${state.total}`;
    }

    if (playBtn) {
      playBtn.textContent = state.status === 'playing' ? '⏸' : '▶';
      playBtn.classList.toggle('active', state.status === 'playing');
    }

    if (candle && ohlc) {
      ohlc.textContent = `O ${candle.open.toFixed(5)}  H ${candle.high.toFixed(5)}  L ${candle.low.toFixed(5)}  C ${candle.close.toFixed(5)}`;
    }

    if (candle && session) {
      const sess = getSession(candle.timestamp);
      session.textContent = `${formatTimestamp(candle.timestamp)} UTC · ${sess}`;
      session.style.color = getSessionColor(sess);
    }

    if (candle) {
      this.setJumpDate(candle.timestamp);
    }
  }
}

export const ReplayControls = new ReplayControlsImpl();
