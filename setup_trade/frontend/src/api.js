const BASE = "/api";

export async function apiGet(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const url = qs ? `${BASE}${path}?${qs}` : `${BASE}${path}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function apiPost(path, params = {}, body = null) {
  const qs = new URLSearchParams(params).toString();
  const url = qs ? `${BASE}${path}?${qs}` : `${BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export function loadPeriods() {
  return apiGet("/config/periods");
}

export function loadFolds() {
  return apiGet("/folds");
}

export function loadCandles(period, limit = 2000) {
  return apiGet("/candles", { period, limit });
}

export function validateSetup(payload) {
  return apiPost("/setups/validate", {}, payload);
}

export function saveSetup(payload) {
  return apiPost("/setups", {}, payload);
}

export function analyzePeriod(period, full = true, applyDisable = false) {
  return apiGet("/analyze", { period, full, apply_disable: applyDisable });
}

export function runBacktestExplore(period) {
  return apiPost("/backtest/explore", { period });
}

export function runBacktestFinal(period) {
  return apiPost("/backtest", { period });
}

export function runOptimize(period, method = "greedy") {
  return apiPost("/optimize", { period, method, save_best: true });
}

export function foldStep(foldId, step, params = {}) {
  return apiPost(`/fold/${foldId}/${step}`, params);
}

export function runValidation(foldId, skipOptimize = false) {
  return apiPost(`/validation/${foldId}`, { skip_optimize: skipOptimize, save_strategy: true });
}

export function validationReportUrl(foldId) {
  return `${BASE}/validation/${foldId}/report`;
}
