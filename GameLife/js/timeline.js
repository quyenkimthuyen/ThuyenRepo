const TimelineModule = {
  render(container, timeline) {
    if (!timeline.length) {
      container.innerHTML = '<p class="empty-state">Chưa có lịch sử. Hãy đưa ra quyết định đầu tiên.</p>';
      return;
    }

    container.innerHTML = timeline.slice(0, 30).map((entry) => {
      const typeClass = `timeline-${entry.type}`;
      const dayLabel = `Ngày ${entry.day}`;
      let effectsHtml = '';

      if (entry.effects) {
        const parts = Object.entries(entry.effects)
          .filter(([, v]) => v !== 0)
          .map(([k, v]) => `<span class="effect ${v > 0 ? 'positive' : 'negative'}">${this.statLabel(k)} ${v > 0 ? '+' : ''}${v}</span>`);
        if (parts.length) effectsHtml = `<div class="timeline-effects">${parts.join('')}</div>`;
      }

      return `
        <div class="timeline-item ${typeClass}">
          <div class="timeline-day">${dayLabel}</div>
          <div class="timeline-message">${entry.message}</div>
          ${effectsHtml}
        </div>
      `;
    }).join('');
  },

  statLabel(key) {
    const labels = {
      health: 'Sức khỏe',
      wealth: 'Tài sản',
      happiness: 'Hạnh phúc',
      knowledge: 'Kiến thức',
      relationships: 'Quan hệ',
      energy: 'Năng lượng'
    };
    return labels[key] || key;
  }
};
