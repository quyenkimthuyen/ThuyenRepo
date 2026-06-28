#!/usr/bin/env node
/**
 * Convenience wrapper — run full PARL test suite.
 * Usage: node scripts/run-tests.mjs
 */
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const result = spawnSync(process.execPath, [join(root, 'tests/run-all.mjs')], {
  stdio: 'inherit',
  cwd: root,
});
process.exit(result.status ?? 1);
