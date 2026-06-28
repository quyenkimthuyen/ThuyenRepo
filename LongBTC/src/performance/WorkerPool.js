/**
 * Web Worker pool for offloading heavy computations.
 * @module performance/WorkerPool
 */

import { createLogger } from '../utils/logger.js';

const log = createLogger('WorkerPool');

/**
 * @typedef {Object} WorkerTask
 * @property {number} id
 * @property {string} task
 * @property {unknown} payload
 * @property {(result: unknown) => void} resolve
 * @property {(error: Error) => void} reject
 */

/**
 * Pool of module workers with a shared task queue.
 */
export class WorkerPool {
  /** @type {Worker[]} */
  #workers = [];

  /** @type {WorkerTask[]} */
  #queue = [];

  /** @type {Map<number, WorkerTask>} */
  #active = new Map();

  /** @type {number} */
  #taskId = 0;

  /** @type {boolean} */
  #available = true;

  /**
   * @param {URL|string} workerUrl
   * @param {number} [poolSize]
   */
  constructor(workerUrl, poolSize = 4) {
    try {
      for (let i = 0; i < poolSize; i++) {
        const worker = new Worker(workerUrl, { type: 'module' });
        worker.onmessage = (e) => this.#onMessage(worker, e.data);
        worker.onerror = (err) => this.#onError(worker, err);
        this.#workers.push(worker);
      }
      log.info(`Worker pool started (${poolSize} workers)`);
    } catch (err) {
      this.#available = false;
      log.warn('Workers unavailable:', err);
    }
  }

  /**
   * @returns {boolean}
   */
  isAvailable() {
    return this.#available && this.#workers.length > 0;
  }

  /**
   * Dispatch a task to the worker pool.
   * @param {string} task
   * @param {unknown} payload
   * @returns {Promise<unknown>}
   */
  run(task, payload) {
    if (!this.isAvailable()) {
      return Promise.reject(new Error('Worker pool not available'));
    }

    return new Promise((resolve, reject) => {
      const id = ++this.#taskId;
      this.#queue.push({ id, task, payload, resolve, reject });
      this.#dispatch();
    });
  }

  /**
   * Terminate all workers.
   */
  terminate() {
    for (const worker of this.#workers) {
      worker.terminate();
    }
    this.#workers = [];
    this.#available = false;
  }

  #dispatch() {
    if (!this.#queue.length) return;

    for (const worker of this.#workers) {
      if (this.#active.has(worker)) continue;
      const next = this.#queue.shift();
      if (!next) return;

      this.#active.set(worker, next);
      worker.postMessage({ id: next.id, task: next.task, payload: next.payload });
    }
  }

  /**
   * @param {Worker} worker
   * @param {{ id: number, ok: boolean, result?: unknown, error?: string }} data
   */
  #onMessage(worker, data) {
    const task = this.#active.get(worker);
    if (!task || task.id !== data.id) return;

    this.#active.delete(worker);

    if (data.ok) task.resolve(data.result);
    else task.reject(new Error(data.error ?? 'Worker task failed'));

    this.#dispatch();
  }

  /**
   * @param {Worker} worker
   * @param {ErrorEvent} err
   */
  #onError(worker, err) {
    const task = this.#active.get(worker);
    if (task) {
      this.#active.delete(worker);
      task.reject(new Error(err.message));
    }
    this.#dispatch();
  }
}
