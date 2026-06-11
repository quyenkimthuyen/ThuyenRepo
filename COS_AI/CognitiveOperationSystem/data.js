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
      reflectionMode: 'rule',
      cursorProxyUrl: 'http://localhost:3001',
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
    const prev = this._cache?.settings || {};
    this._cache = getDefaultState();
    if (prev.locale) this._cache.settings.locale = prev.locale;
    if (prev.reflectionMode) this._cache.settings.reflectionMode = prev.reflectionMode;
    if (prev.cursorProxyUrl) this._cache.settings.cursorProxyUrl = prev.cursorProxyUrl;
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
