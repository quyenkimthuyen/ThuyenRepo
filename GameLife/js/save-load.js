const SaveLoad = {
  STORAGE_KEY: 'gamelife_save',

  save(state) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (e) {
      console.error('Save failed:', e);
      return false;
    }
  },

  load() {
    try {
      const data = localStorage.getItem(this.STORAGE_KEY);
      if (!data) return null;
      return JSON.parse(data);
    } catch (e) {
      console.error('Load failed:', e);
      return null;
    }
  },

  hasSave() {
    return !!localStorage.getItem(this.STORAGE_KEY);
  },

  clear() {
    localStorage.removeItem(this.STORAGE_KEY);
  }
};
