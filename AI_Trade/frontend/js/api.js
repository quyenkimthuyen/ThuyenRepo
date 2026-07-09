const API = '';

export async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const getConfig = () => api('/api/config');
export const getPresets = () => api('/api/presets');
export const getCandles = (period) => api(`/api/candles?period=${period}&with_indicators=true`);
export const getSetups = () => api('/api/setups');
export const saveSetup = (body) => api('/api/setups', { method: 'POST', body: JSON.stringify(body) });
export const updateSetup = (id, body) => api(`/api/setups/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
export const deleteSetup = (id) => api(`/api/setups/${id}`, { method: 'DELETE' });
export const analyze = () => api('/api/analyze', { method: 'POST' });
export const backtest = (period) => api(`/api/backtest?period=${period}`, { method: 'POST' });
export const suggestTags = (body) => api('/api/tags/suggest', { method: 'POST', body: JSON.stringify(body) });
export const getTagDefinitions = () => api('/api/tags/definitions');
export const getImportantBars = (period) =>
  api(`/api/bars/important?period=${period}&with_tags=true`);
export const inspectBar = (entryTime, entryPrice) => {
  const params = new URLSearchParams({ entry_time: entryTime });
  if (entryPrice != null) params.set('entry_price', String(entryPrice));
  return api(`/api/bars/inspect?${params}`);
};
export const getBarAnnotations = () => api('/api/bar-annotations');
export const saveBarAnnotation = (body) =>
  api('/api/bar-annotations', { method: 'POST', body: JSON.stringify(body) });
export const deleteBarAnnotation = (id) =>
  api(`/api/bar-annotations/${id}`, { method: 'DELETE' });
export const getBarDetectionConfig = () => api('/api/bar-detection/config');
export const saveBarDetectionConfig = (body) =>
  api('/api/bar-detection/config', { method: 'PATCH', body: JSON.stringify(body) });
