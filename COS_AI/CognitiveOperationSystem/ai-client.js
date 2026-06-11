/**
 * AI Client — gọi Cursor proxy (local server)
 */

const AiClient = {
  DEFAULT_PROXY_URL: 'http://localhost:3001',

  getSettings() {
    const s = DataStore.load().settings || {};
    return {
      reflectionMode: s.reflectionMode || 'rule',
      cursorProxyUrl: s.cursorProxyUrl || this.DEFAULT_PROXY_URL,
    };
  },

  isEnabled() {
    return this.getSettings().reflectionMode === 'cursor';
  },

  setMode(mode) {
    const settings = DataStore.load().settings || {};
    DataStore.save({
      settings: {
        ...settings,
        reflectionMode: mode === 'cursor' ? 'cursor' : 'rule',
      },
    });
  },

  setProxyUrl(url) {
    const settings = DataStore.load().settings || {};
    DataStore.save({
      settings: {
        ...settings,
        cursorProxyUrl: (url || this.DEFAULT_PROXY_URL).replace(/\/$/, ''),
      },
    });
  },

  getProxyUrl() {
    return this.getSettings().cursorProxyUrl;
  },

  async checkHealth() {
    const url = `${this.getProxyUrl()}/api/health`;
    const res = await fetch(url, { method: 'GET' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async reflect({ message, session, phase = 'continue' }) {
    const locale =
      typeof I18n !== 'undefined' && I18n.getLocale ? I18n.getLocale() : 'vi';
    const url = `${this.getProxyUrl()}/api/reflect`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session, locale, phase }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || data.hint || `AI proxy error (${res.status})`);
    }
    return data;
  },
};

if (typeof window !== 'undefined') {
  window.AiClient = AiClient;
}
