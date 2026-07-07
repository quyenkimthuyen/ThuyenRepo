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
export const getCandles = (period) => api(`/api/candles?period=${period}&with_indicators=true`);
export const getSetups = () => api('/api/setups');
export const saveSetup = (body) => api('/api/setups', { method: 'POST', body: JSON.stringify(body) });
export const deleteSetup = (id) => api(`/api/setups/${id}`, { method: 'DELETE' });
export const analyze = () => api('/api/analyze', { method: 'POST' });
export const backtest = (period) => api(`/api/backtest?period=${period}`, { method: 'POST' });
