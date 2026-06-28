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
import { WyckoffSpringUtadStrategy } from './WyckoffSpringUtadStrategy.js';
import { WyckoffRangeTestStrategy } from './WyckoffRangeTestStrategy.js';
import { SessionLiquiditySweepStrategy } from './SessionLiquiditySweepStrategy.js';
import { BtcDailySweepStrategy } from './BtcDailySweepStrategy.js';
import { BtcCycleDcaStrategy } from './BtcCycleDcaStrategy.js';

/** All built-in strategy classes. */
export const BUILTIN_STRATEGIES = [
  BreakRetestStrategy,
  EMAPullbackStrategy,
  LiquidityGrabStrategy,
  InsideBarBreakoutStrategy,
  PinBarRejectionStrategy,
  WyckoffSpringUtadStrategy,
  WyckoffRangeTestStrategy,
  SessionLiquiditySweepStrategy,
  BtcDailySweepStrategy,
  BtcCycleDcaStrategy,
];

/** @type {boolean} */
let builtinsRegistered = false;

/**
 * Register all built-in strategy plugins with the registry.
 * Safe to call multiple times (main thread and workers).
 */
export function registerBuiltinStrategies() {
  if (builtinsRegistered) return;
  registry.registerAll(BUILTIN_STRATEGIES);
  builtinsRegistered = true;
}
