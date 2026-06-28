/**
 * Tracks the currently active workspace view for context-sensitive help.
 * @module ui/activeView
 */

/** @type {string} */
let activeViewId = 'chart';

/**
 * @param {string} viewId
 */
export function setActiveView(viewId) {
  activeViewId = viewId;
}

/**
 * @returns {string}
 */
export function getActiveView() {
  return activeViewId;
}
