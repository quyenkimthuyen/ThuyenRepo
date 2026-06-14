/**
 * Cursor Direct — client gọi bridge cục bộ (Cursor SDK)
 *
 * API key chỉ ở server Node; trình duyệt chỉ nói chuyện với localhost.
 */

const CursorDirect = {
  defaultUrl: 'http://127.0.0.1:3847',

  getBridgeUrl() {
    const settings = DataStore.load().settings || {};
    const url = (settings.cursorBridgeUrl || this.defaultUrl).trim();
    return url.replace(/\/$/, '');
  },

  setBridgeUrl(url) {
    const settings = DataStore.load().settings || {};
    const next = (url || this.defaultUrl).trim().replace(/\/$/, '');
    DataStore.save({ settings: { ...settings, cursorBridgeUrl: next } });
    return next;
  },

  async request(path, options = {}) {
    const url = `${this.getBridgeUrl()}${path}`;
    let res;
    try {
      res = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
      });
    } catch (err) {
      const error = new Error(err?.message || 'network_error');
      error.code = 'bridge_unreachable';
      throw error;
    }

    let data = {};
    try {
      data = await res.json();
    } catch {
      data = {};
    }

    if (!res.ok || data.ok === false) {
      const error = new Error(data.message || data.error || res.statusText || 'request_failed');
      error.code = data.error || 'request_failed';
      error.status = res.status;
      throw error;
    }

    return data;
  },

  async health() {
    try {
      return await this.request('/health');
    } catch (err) {
      return {
        ok: false,
        hasApiKey: false,
        sdkReady: false,
        error: err.code || 'unreachable',
        message: err.message,
      };
    }
  },

  async startSession(thought) {
    const reflectionPrompt = AiAssist.getReflectionPrompt(thought);
    return this.request('/api/session/start', {
      method: 'POST',
      body: JSON.stringify({ reflectionPrompt }),
    });
  },

  async sendMessage(sessionKey, content) {
    return this.request(`/api/session/${encodeURIComponent(sessionKey)}/message`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },

  async exportSession(sessionKey) {
    const exportPrompt = AiAssist.getExportPrompt();
    return this.request(`/api/session/${encodeURIComponent(sessionKey)}/export`, {
      method: 'POST',
      body: JSON.stringify({ exportPrompt }),
    });
  },

  async closeSession(sessionKey) {
    if (!sessionKey) return;
    try {
      await this.request(`/api/session/${encodeURIComponent(sessionKey)}`, {
        method: 'DELETE',
      });
    } catch {
      /* bridge có thể đã tắt */
    }
  },

  buildTranscript(messages) {
    const locale =
      typeof I18n !== 'undefined' && typeof I18n.getPromptLocale === 'function'
        ? I18n.getPromptLocale()
        : 'vi';
    const userLabel = locale === 'en' ? 'User' : 'Bạn';
    const guideLabel = locale === 'en' ? 'Assistant' : 'Trợ lý';

    return (messages || [])
      .map((m) => {
        const who = m.role === 'user' ? userLabel : guideLabel;
        return `${who}: ${m.content}`;
      })
      .join('\n\n');
  },

  inferFlowStep(session) {
    const flow = CognitiveLibrary.REFLECTION_FLOW;
    const userCount = (session.messages || []).filter((m) => m.role === 'user').length;
    const idx = Math.min(Math.max(userCount - 1, 0), flow.length - 1);
    return flow[idx];
  },

  isCursorSession(session) {
    return session?.source === 'cursor_direct';
  },
};

if (typeof window !== 'undefined') {
  window.CursorDirect = CursorDirect;
}
