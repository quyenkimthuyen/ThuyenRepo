/**
 * Strategy parameter schema definitions and validation.
 * @module strategy/ParameterSchema
 */

/**
 * @typedef {'number'|'integer'|'boolean'|'select'} ParamType
 */

/**
 * @typedef {Object} ParamDefinition
 * @property {string} key - Parameter key
 * @property {string} label - Display label
 * @property {ParamType} type - Input type
 * @property {number|boolean|string} default - Default value
 * @property {number} [min] - Minimum (number types)
 * @property {number} [max] - Maximum (number types)
 * @property {number} [step] - Step increment
 * @property {Array<number|string>} [options] - Options for select type
 * @property {string} [description] - Help text
 */

/**
 * Apply defaults from a parameter schema to a partial params object.
 * @param {ParamDefinition[]} schema
 * @param {Record<string, unknown>} [overrides]
 * @returns {Record<string, unknown>}
 */
export function applyDefaults(schema, overrides = {}) {
  const params = {};

  for (const def of schema) {
    params[def.key] = overrides[def.key] ?? def.default;
  }

  return params;
}

/**
 * Validate params against schema constraints.
 * @param {ParamDefinition[]} schema
 * @param {Record<string, unknown>} params
 * @returns {{ valid: boolean, errors: string[] }}
 */
export function validateParams(schema, params) {
  const errors = [];

  for (const def of schema) {
    const value = params[def.key];

    if (value === undefined || value === null) {
      errors.push(`Missing parameter: ${def.label}`);
      continue;
    }

    if (def.type === 'number' || def.type === 'integer') {
      const num = Number(value);
      if (Number.isNaN(num)) {
        errors.push(`${def.label} must be a number`);
        continue;
      }
      if (def.min !== undefined && num < def.min) {
        errors.push(`${def.label} must be >= ${def.min}`);
      }
      if (def.max !== undefined && num > def.max) {
        errors.push(`${def.label} must be <= ${def.max}`);
      }
    }

    if (def.type === 'select' && def.options && !def.options.includes(value)) {
      errors.push(`${def.label} must be one of: ${def.options.join(', ')}`);
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Clone params object.
 * @param {Record<string, unknown>} params
 * @returns {Record<string, unknown>}
 */
export function cloneParams(params) {
  return { ...params };
}
