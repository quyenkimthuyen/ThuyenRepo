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

function qs(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== '') search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : '';
}

export const getConfig = () => api('/api/config');
export const getPresets = () => api('/api/presets');
export const getMonths = (period = 'train') => api(`/api/months${qs({ period })}`);
export const getCandles = (period, month = null) =>
  api(`/api/candles${qs({ period, month, with_indicators: true })}`);
export const getSetups = ({ month = null, summary = true, period = null } = {}) =>
  api(`/api/setups${qs({ month, summary, period })}`);
export const saveSetup = (body) => api('/api/setups', { method: 'POST', body: JSON.stringify(body) });
export const updateSetup = (id, body) => api(`/api/setups/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
export const deleteSetup = (id) => api(`/api/setups/${id}`, { method: 'DELETE' });
export const analyze = () => api('/api/analyze', { method: 'POST' });
export const backtest = (period) => api(`/api/backtest?period=${period}`, { method: 'POST' });
export const suggestTags = (body) => api('/api/tags/suggest', { method: 'POST', body: JSON.stringify(body) });
export const getTagDefinitions = () => api('/api/tags/definitions');
export const getImportantBars = (period, month = null) =>
  api(`/api/bars/important${qs({ period, month, with_tags: true })}`);
export const inspectBar = (entryTime, entryPrice) => {
  const params = new URLSearchParams({ entry_time: entryTime });
  if (entryPrice != null) params.set('entry_price', String(entryPrice));
  return api(`/api/bars/inspect?${params}`);
};
export const getBarAnnotations = (month = null) =>
  api(`/api/bar-annotations${qs({ month, summary: true })}`);
export const saveBarAnnotation = (body) =>
  api('/api/bar-annotations', { method: 'POST', body: JSON.stringify(body) });
export const deleteBarAnnotation = (id) =>
  api(`/api/bar-annotations/${id}`, { method: 'DELETE' });
export const getBarDetectionConfig = () => api('/api/bar-detection/config');
export const saveBarDetectionConfig = (body) =>
  api('/api/bar-detection/config', { method: 'PATCH', body: JSON.stringify(body) });
