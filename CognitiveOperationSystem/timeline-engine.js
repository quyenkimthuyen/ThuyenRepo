/**
 * Timeline Engine — Theo dõi sự thay đổi nhận thức theo thời gian
 *
 * Mở rộng: visualization nâng cao, so sánh periods.
 */

const TimelineEngine = {
  /**
   * Ghi nhận bắt đầu session
   */
  recordSessionStart(session, nodesCreated) {
    const event = {
      id: generateId('tl'),
      type: 'session_start',
      title: 'Bắt đầu suy ngẫm',
      description: session.initialThought.slice(0, 100),
      sessionId: session.id,
      nodeIds: nodesCreated.map((n) => n.id),
      timestamp: session.createdAt,
      year: new Date(session.createdAt).getFullYear(),
      month: new Date(session.createdAt).getMonth() + 1,
    };

    DataStore.addTimelineEvent(event);
    return event;
  },

  /**
   * Ghi nhận thay đổi node (đặc biệt khi lên verified)
   */
  recordNodeChanges(nodes) {
    for (const node of nodes) {
      if (node.status === 'verified' || node.occurrences === 2) {
        const event = {
          id: generateId('tl'),
          type: node.status === 'verified' ? 'node_verified' : 'node_candidate',
          title: `${node.type}: ${node.label}`,
          description: `Trạng thái: ${node.status} (${node.occurrences} lần)`,
          nodeId: node.id,
          nodeType: node.type,
          nodeLabel: node.label,
          status: node.status,
          timestamp: new Date().toISOString(),
          year: new Date().getFullYear(),
          month: new Date().getMonth() + 1,
        };
        DataStore.addTimelineEvent(event);
      }
    }
  },

  /**
   * Ghi nhận shift giá trị/nhận thức theo năm
   */
  recordValueShift(oldValue, newValue) {
    const event = {
      id: generateId('tl'),
      type: 'value_shift',
      title: 'Thay đổi giá trị',
      description: `Từ "${oldValue}" sang "${newValue}"`,
      from: oldValue,
      to: newValue,
      timestamp: new Date().toISOString(),
      year: new Date().getFullYear(),
    };
    DataStore.addTimelineEvent(event);
  },

  /**
   * Nhóm events theo năm
   */
  groupByYear() {
    const events = DataStore.getTimeline();
    const grouped = {};

    for (const event of events) {
      const year = event.year || new Date(event.timestamp).getFullYear();
      if (!grouped[year]) grouped[year] = [];
      grouped[year].push(event);
    }

    return Object.keys(grouped)
      .sort((a, b) => Number(b) - Number(a))
      .map((year) => ({
        year: Number(year),
        events: grouped[year].sort(
          (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
        ),
      }));
  },

  /**
   * Tạo narrative timeline từ nodes Value/Belief theo thời gian
   */
  buildCognitiveNarrative() {
    const nodes = DataStore.getNodes()
      .filter((n) => ['Value', 'Belief', 'Identity'].includes(n.type))
      .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));

    const byYear = {};
    for (const node of nodes) {
      const year = new Date(node.createdAt).getFullYear();
      if (!byYear[year]) byYear[year] = [];
      byYear[year].push(node);
    }

    const narrative = [];
    const years = Object.keys(byYear).sort((a, b) => Number(a) - Number(b));

    for (let i = 0; i < years.length; i++) {
      const year = Number(years[i]);
      const yearNodes = byYear[year];

      // Tìm value/belief nổi bật nhất trong năm
      const topValue = yearNodes
        .filter((n) => n.type === 'Value')
        .sort((a, b) => (b.occurrences || 0) - (a.occurrences || 0))[0];

      const topBelief = yearNodes
        .filter((n) => n.type === 'Belief')
        .sort((a, b) => (b.occurrences || 0) - (a.occurrences || 0))[0];

      narrative.push({
        year,
        value: topValue,
        belief: topBelief,
        nodes: yearNodes,
        transition:
          i < years.length - 1
            ? this.detectTransition(yearNodes, byYear[years[i + 1]])
            : null,
      });
    }

    return narrative;
  },

  detectTransition(currentNodes, nextYearNodes) {
    const currentTopValue = currentNodes
      .filter((n) => n.type === 'Value')
      .sort((a, b) => (b.occurrences || 0) - (a.occurrences || 0))[0];

    const nextTopValue = nextYearNodes
      .filter((n) => n.type === 'Value')
      .sort((a, b) => (b.occurrences || 0) - (a.occurrences || 0))[0];

    if (
      currentTopValue &&
      nextTopValue &&
      currentTopValue.label !== nextTopValue.label
    ) {
      return {
        type: 'value_shift',
        from: currentTopValue.label,
        to: nextTopValue.label,
      };
    }
    return null;
  },

  /**
   * Lấy timeline events đã format
   */
  getFormattedTimeline() {
    const grouped = this.groupByYear();
    const narrative = this.buildCognitiveNarrative();

    return {
      grouped,
      narrative,
      totalEvents: DataStore.getTimeline().length,
    };
  },
};

if (typeof window !== 'undefined') {
  window.TimelineEngine = TimelineEngine;
}
