/**
 * Parameter grid utilities — parse ranges and build combinations.
 * @module optimizer/ParameterGrid
 */

/** @typedef {import('../strategy/ParameterSchema.js').ParamDefinition} ParamDefinition */

/**
 * Parse a comma-separated or range string into numeric values.
 * Supports "10,20,30" and "10:50:10" (start:end:step).
 * @param {string} input
 * @returns {number[]}
 */
export function parseValueList(input) {
  const trimmed = input.trim();
  if (!trimmed) return [];

  if (trimmed.includes(':')) {
    const parts = trimmed.split(':').map(Number);
    if (parts.length !== 3 || parts.some(Number.isNaN)) return [];
    const [start, end, step] = parts;
    if (step === 0) return [];
    const values = [];
    for (let v = start; v <= end + step * 0.001; v += step) {
      values.push(Number(v.toFixed(6)));
    }
    return values;
  }

  return trimmed.split(',')
    .map((s) => Number(s.trim()))
    .filter((n) => !Number.isNaN(n));
}

/**
 * Build cartesian product of parameter value lists.
 * @param {Record<string, number[]|string[]|boolean[]>} paramValues
 * @returns {Record<string, unknown>[]}
 */
export function buildCombinations(paramValues) {
  const keys = Object.keys(paramValues);
  if (keys.length === 0) return [{}];

  /** @type {Record<string, unknown>[]} */
  let combos = [{}];

  for (const key of keys) {
    const values = paramValues[key];
    if (!values.length) continue;

    const next = [];
    for (const combo of combos) {
      for (const value of values) {
        next.push({ ...combo, [key]: value });
      }
    }
    combos = next;
  }

  return combos;
}

/**
 * Count total combinations without building them.
 * @param {Record<string, number[]|string[]|boolean[]>} paramValues
 * @returns {number}
 */
export function countCombinations(paramValues) {
  const keys = Object.keys(paramValues);
  if (keys.length === 0) return 1;
  return keys.reduce((total, key) => total * (paramValues[key].length || 1), 1);
}

/**
 * Build default grid values for a numeric parameter (3 values around default).
 * @param {ParamDefinition} def
 * @returns {number[]}
 */
export function defaultGridForParam(def) {
  if (def.type !== 'number' && def.type !== 'integer') return [];

  const base = Number(def.default);
  const step = def.step ?? (def.type === 'integer' ? 1 : 0.5);
  const values = [base - step, base, base + step].filter((v) => {
    if (def.min !== undefined && v < def.min) return false;
    if (def.max !== undefined && v > def.max) return false;
    return true;
  });

  return [...new Set(values.map((v) => def.type === 'integer' ? Math.round(v) : v))];
}
