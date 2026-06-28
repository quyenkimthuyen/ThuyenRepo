/**
 * PARL localStorage helpers.
 * Run: node tests/utils/StorageUtilsTests.js
 */

import { listParlStorageKeys, clearParlLocalStorage, saveToStorage } from '../../src/utils/dom.js';

let passed = 0;
let failed = 0;

/**
 * @param {string} name
 * @param {boolean} ok
 */
function assert(name, ok) {
  if (ok) { passed++; console.log(`  ? ${name}`); }
  else { failed++; console.error(`  ? ${name}`); }
}

if (typeof localStorage === 'undefined') {
  console.log('\n=== Storage Utils (skipped — no localStorage) ===\n');
  process.exit(0);
}

console.log('\n=== Storage Utils ===\n');

saveToStorage('parl_test_key', { ok: true });
saveToStorage('other_key', { keep: true });
assert('lists parl_ keys', listParlStorageKeys().includes('parl_test_key'));
assert('ignores non-parl keys in clear', !listParlStorageKeys().includes('other_key'));

clearParlLocalStorage();
assert('clears parl_ keys', !listParlStorageKeys().includes('parl_test_key'));
assert('keeps other keys', localStorage.getItem('other_key') !== null);

localStorage.removeItem('other_key');

console.log(`\n=== Storage Utils: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
