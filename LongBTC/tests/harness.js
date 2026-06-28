/**
 * Shared test harness for PARL unit & integration tests.
 * @module tests/harness
 */

/**
 * @typedef {Object} SuiteResult
 * @property {string} name
 * @property {number} passed
 * @property {number} failed
 * @property {string[]} failures
 */

/**
 * Create an isolated test suite with assert helpers.
 * @param {string} name
 * @returns {{ assert: (label: string, ok: boolean) => void, assertEq: (label: string, actual: unknown, expected: unknown) => void, assertThrows: (label: string, fn: () => unknown) => void, finish: () => SuiteResult }}
 */
export function createSuite(name) {
  let passed = 0;
  let failed = 0;
  /** @type {string[]} */
  const failures = [];

  /**
   * @param {string} label
   * @param {boolean} ok
   */
  function assert(label, ok) {
    if (ok) {
      passed++;
      console.log(`  ✓ ${label}`);
    } else {
      failed++;
      failures.push(label);
      console.error(`  ✗ ${label}`);
    }
  }

  /**
   * @param {string} label
   * @param {unknown} actual
   * @param {unknown} expected
   */
  function assertEq(label, actual, expected) {
    assert(label, actual === expected);
  }

  /**
   * @param {string} label
   * @param {() => unknown} fn
   */
  function assertThrows(label, fn) {
    try {
      fn();
      assert(label, false);
    } catch {
      assert(label, true);
    }
  }

  return {
    assert,
    assertEq,
    assertThrows,
    finish() {
      return { name, passed, failed, failures };
    },
  };
}

/**
 * @param {number} i
 * @param {number} o
 * @param {number} h
 * @param {number} l
 * @param {number} c
 * @param {number} [vol]
 * @param {number} [ms]
 * @returns {import('../src/data/Candle.js').Candle}
 */
export function candle(i, o, h, l, c, vol = 500, ms = 3600000) {
  return { timestamp: i * ms, open: o, high: h, low: l, close: c, volume: vol };
}

/**
 * Print suite header.
 * @param {string} name
 */
export function header(name) {
  console.log(`\n=== ${name} ===\n`);
}

/**
 * Print suite footer and return exit code.
 * @param {SuiteResult} result
 * @returns {number}
 */
export function footer(result) {
  console.log(`\n=== ${result.name}: ${result.passed} passed, ${result.failed} failed ===\n`);
  return result.failed > 0 ? 1 : 0;
}
