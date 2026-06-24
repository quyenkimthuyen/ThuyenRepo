/**
 * Built-in strategy plugin registration.
 * @module strategies/index
 */

import { registry } from '../plugin/PluginRegistry.js';
import { BreakRetestStrategy } from './BreakRetestStrategy.js';
import { EMAPullbackStrategy } from './EMAPullbackStrategy.js';
import { LiquidityGrabStrategy } from './LiquidityGrabStrategy.js';
import { InsideBarBreakoutStrategy } from './InsideBarBreakoutStrategy.js';
import { PinBarRejectionStrategy } from './PinBarRejectionStrategy.js';

/** All built-in strategy classes. */
export const BUILTIN_STRATEGIES = [
  BreakRetestStrategy,
  EMAPullbackStrategy,
  LiquidityGrabStrategy,
  InsideBarBreakoutStrategy,
  PinBarRejectionStrategy,
];

/**
 * Register all built-in strategy plugins with the registry.
 */
export function registerBuiltinStrategies() {
  registry.registerAll(BUILTIN_STRATEGIES);
}
