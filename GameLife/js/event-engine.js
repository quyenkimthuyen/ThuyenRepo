const EventEngine = {
  getRandomEvent(state) {
    const available = EVENTS.filter((e) => !state.usedEventIds.includes(e.id));

    if (available.length === 0) {
      state.usedEventIds = [];
      return this.pickWeighted(EVENTS);
    }

    return this.pickWeighted(available);
  },

  pickWeighted(events) {
    const weights = { finance: 1, health: 1, relationships: 1, learning: 1, crisis: 0.6 };
    const weighted = events.map((e) => ({
      event: e,
      weight: weights[e.category] || 1
    }));
    const total = weighted.reduce((sum, w) => sum + w.weight, 0);
    let rand = Math.random() * total;

    for (const item of weighted) {
      rand -= item.weight;
      if (rand <= 0) return item.event;
    }
    return events[Math.floor(Math.random() * events.length)];
  },

  getCategoryLabel(category) {
    const labels = {
      finance: 'Tài chính',
      health: 'Sức khỏe',
      relationships: 'Quan hệ',
      learning: 'Học tập',
      crisis: 'Khủng hoảng'
    };
    return labels[category] || category;
  }
};
