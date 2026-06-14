/**
 * Data Layer — Quản lý LocalStorage và schema dữ liệu
 *
 * Mở rộng: thay persist() bằng API call khi kết nối backend.
 */

const STORAGE_KEY = 'cognitive_os_v1';

/** Tạo ID duy nhất */
function generateId(prefix = 'id') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/** Schema mặc định */
function getDefaultState() {
  return {
    version: 1,
    nodes: [],
    relations: [],
    sessions: [],
    timeline: [],
    insights: {
      lastUpdated: null,
      todayDiscoveries: [],
      contradictions: [],
      biases: [],
    },
    settings: {
      theme: 'dark',
      locale: 'vi',
      insightsView: 'app',
      forestView: 'app',
      cursorBridgeUrl: 'http://127.0.0.1:3847',
    },
    aiOverlays: {
      insights: null,
      forest: null,
      timeline: null,
    },
  };
}

const DataStore = {
  _cache: null,

  /** Đọc toàn bộ state từ LocalStorage */
  load() {
    if (this._cache) return this._cache;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        this._cache = getDefaultState();
        return this._cache;
      }
      this._cache = { ...getDefaultState(), ...JSON.parse(raw) };
      return this._cache;
    } catch (e) {
      console.error('[DataStore] Load failed:', e);
      this._cache = getDefaultState();
      return this._cache;
    }
  },

  /** Lưu state vào LocalStorage */
  persist() {
    if (!this._cache) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this._cache));
    } catch (e) {
      console.error('[DataStore] Persist failed:', e);
    }
  },

  /** Cập nhật cache và persist */
  save(partial) {
    this.load();
    this._cache = { ...this._cache, ...partial };
    this.persist();
    return this._cache;
  },

  /** Lấy nodes */
  getNodes() {
    return this.load().nodes;
  },

  /** Lấy relations */
  getRelations() {
    return this.load().relations;
  },

  /** Lấy sessions */
  getSessions() {
    return this.load().sessions;
  },

  /** Lấy timeline */
  getTimeline() {
    return this.load().timeline;
  },

  /** Thêm node — delegate tới CognitiveTree */
  addNode(node) {
    this.load();
    this._cache.nodes.push(node);
    this.persist();
    return node;
  },

  /** Cập nhật node theo id */
  updateNode(id, updates) {
    this.load();
    const idx = this._cache.nodes.findIndex((n) => n.id === id);
    if (idx === -1) return null;
    this._cache.nodes[idx] = {
      ...this._cache.nodes[idx],
      ...updates,
      updatedAt: new Date().toISOString(),
    };
    this.persist();
    return this._cache.nodes[idx];
  },

  /** Tìm node theo label + type */
  findNode(type, label) {
    return this.getNodes().find(
      (n) => n.type === type && n.label.toLowerCase() === label.toLowerCase()
    );
  },

  /** Thêm relation */
  addRelation(relation) {
    this.load();
    const exists = this._cache.relations.some(
      (r) =>
        r.source === relation.source &&
        r.target === relation.target &&
        r.type === relation.type
    );
    if (!exists) {
      this._cache.relations.push(relation);
      this.persist();
    }
    return relation;
  },

  /** Thêm session */
  addSession(session) {
    this.load();
    this._cache.sessions.push(session);
    this.persist();
    return session;
  },

  /** Cập nhật session */
  updateSession(id, updates) {
    this.load();
    const idx = this._cache.sessions.findIndex((s) => s.id === id);
    if (idx === -1) return null;
    this._cache.sessions[idx] = { ...this._cache.sessions[idx], ...updates };
    this.persist();
    return this._cache.sessions[idx];
  },

  /** Xóa session theo id */
  removeSession(id) {
    this.load();
    const before = this._cache.sessions.length;
    this._cache.sessions = this._cache.sessions.filter((s) => s.id !== id);
    if (this._cache.sessions.length !== before) {
      this.persist();
      return true;
    }
    return false;
  },

  /** Xóa node (và relation liên quan) thuộc một phiên — dùng trước import Cursor finish */
  removeNodesBySession(sessionId) {
    if (!sessionId) return 0;
    this.load();
    const removeIds = new Set(
      this._cache.nodes.filter((n) => n.sourceSessionId === sessionId).map((n) => n.id)
    );
    if (removeIds.size === 0) return 0;
    this._cache.nodes = this._cache.nodes.filter((n) => !removeIds.has(n.id));
    this._cache.relations = this._cache.relations.filter(
      (r) => !removeIds.has(r.source) && !removeIds.has(r.target)
    );
    this._cache.timeline = this._cache.timeline.filter(
      (e) => !e.nodeId || !removeIds.has(e.nodeId)
    );
    this.persist();
    return removeIds.size;
  },

  /** Xóa sự kiện timeline gắn sessionId (session_start khi chat Cursor) */
  removeTimelineForSession(sessionId) {
    if (!sessionId) return 0;
    this.load();
    const before = this._cache.timeline.length;
    this._cache.timeline = this._cache.timeline.filter((e) => e.sessionId !== sessionId);
    if (this._cache.timeline.length !== before) {
      this.persist();
      return before - this._cache.timeline.length;
    }
    return 0;
  },

  /** Lấy session theo id */
  getSession(id) {
    return this.getSessions().find((s) => s.id === id);
  },

  /** Thêm sự kiện timeline */
  addTimelineEvent(event) {
    this.load();
    this._cache.timeline.push(event);
    this.persist();
    return event;
  },

  getAiOverlay(screen) {
    return this.load().aiOverlays?.[screen] || null;
  },

  setAiOverlay(screen, data) {
    this.load();
    if (!this._cache.aiOverlays) {
      this._cache.aiOverlays = { insights: null, forest: null, timeline: null };
    }
    this._cache.aiOverlays[screen] = {
      ...data,
      importedAt: new Date().toISOString(),
    };
    this.persist();
    return this._cache.aiOverlays[screen];
  },

  clearAiOverlay(screen) {
    this.load();
    if (this._cache.aiOverlays) {
      this._cache.aiOverlays[screen] = null;
      this.persist();
    }
  },

  /** Cập nhật insights cache */
  setInsights(insights) {
    this.save({
      insights: {
        ...this.load().insights,
        ...insights,
        lastUpdated: new Date().toISOString(),
      },
    });
  },

  /** Xóa toàn bộ dữ liệu (debug/reset) */
  reset() {
    const locale = this._cache?.settings?.locale;
    this._cache = getDefaultState();
    if (locale) this._cache.settings.locale = locale;
    this.persist();
  },

  /** Thay thế toàn bộ state (test mode / import) */
  replaceState(state) {
    this._cache = { ...getDefaultState(), ...state };
    this.persist();
    return this._cache;
  },

  /** Export JSON */
  exportData() {
    return JSON.stringify(this.load(), null, 2);
  },
};

if (typeof window !== 'undefined') {
  window.DataStore = DataStore;
  window.generateId = generateId;
}
