/**
 * Insight Engine — Phân tích patterns nhận thức
 *
 * - Niềm tin / cảm xúc / giá trị xuất hiện nhiều nhất
 * - Mâu thuẫn nhận thức
 * - Thiên kiến nhận thức
 *
 * Mở rộng: clustering, trend analysis qua AI.
 */

const InsightEngine = {
  /**
   * Top nodes theo occurrences
   */
  getTopByType(type, limit = 5) {
    return DataStore.getNodes()
      .filter((n) => n.type === type)
      .sort((a, b) => (b.occurrences || 0) - (a.occurrences || 0))
      .slice(0, limit);
  },

  /**
   * Khám phá hôm nay — nodes mới hoặc cập nhật hôm nay
   */
  getTodayDiscoveries() {
    const today = new Date().toDateString();
    const nodes = DataStore.getNodes();

    return nodes
      .filter((n) => {
        const updated = new Date(n.updatedAt).toDateString();
        const created = new Date(n.createdAt).toDateString();
        return updated === today || created === today;
      })
      .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
      .slice(0, 10)
      .map((n) => ({
        node: n,
        label: n.label,
        type: n.type,
        status: n.status,
        isNew: new Date(n.createdAt).toDateString() === today,
      }));
  },

  /**
   * Phát hiện thiên kiến từ sessions gần đây
   */
  detectBiasesFromSessions() {
    const sessions = DataStore.getSessions();
    const recentTexts = sessions
      .slice(-5)
      .flatMap((s) => s.messages.filter((m) => m.role === 'user').map((m) => m.content))
      .join(' ');

    const matches = ReflectionEngine.matchFromLibrary(
      recentTexts,
      CognitiveLibrary.COGNITIVE_BIASES
    );

    return matches.map((b) => ({
      label: b.labelVi || b.label,
      labelEn: b.label,
      score: b.score,
      description: this.getBiasDescription(b.label),
    }));
  },

  getBiasDescription(biasName) {
    const descriptions = {
      'Confirmation Bias': 'Bạn có thể chỉ chú ý thông tin xác nhận niềm tin sẵn có.',
      Overgeneralization: 'Dùng từ "luôn luôn", "không bao giờ" có thể phóng đại thực tế.',
      'Black and White Thinking': 'Nhìn vấn đề theo hai cực, bỏ qua vùng xám.',
      Catastrophizing: 'Dự đoán kết quả tồi tệ nhất có thể.',
      'Mind Reading': 'Giả định biết người khác đang nghĩ gì.',
      'Should Statements': 'Quy tắc "phải/nên" cứng nhắc gây áp lực.',
      Personalization: 'Gán trách nhiệm quá mức cho bản thân.',
    };
    return descriptions[biasName] || 'Thiên kiến nhận thức có thể ảnh hưởng cách bạn diễn giải sự việc.';
  },

  /**
   * Tổng hợp insight đầy đủ
   */
  analyze() {
    const contradictions = ContradictionEngine.analyze();
    const todayDiscoveries = this.getTodayDiscoveries();
    const topBeliefs = this.getTopByType('Belief', 5);
    const topValues = this.getTopByType('Value', 5);
    const topEmotions = this.getTopByType('Emotion', 5);
    const biases = this.detectBiasesFromSessions();

    // Nodes vừa lên verified
    const recentlyVerified = DataStore.getNodes()
      .filter((n) => n.status === 'verified')
      .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
      .slice(0, 5);

    return {
      todayDiscoveries,
      topBeliefs,
      topValues,
      topEmotions,
      contradictions,
      biases,
      recentlyVerified,
      stats: CognitiveTree.getStats(),
      generatedAt: new Date().toISOString(),
    };
  },

  /**
   * Format node cho hiển thị
   */
  formatNodeCard(node) {
    const colors = CognitiveLibrary.NODE_TYPE_COLORS[node.type] || {};
    return {
      ...node,
      colors,
      statusLabel: { draft: 'Nháp', candidate: 'Ứng viên', verified: 'Xác nhận' }[node.status],
    };
  },
};

if (typeof window !== 'undefined') {
  window.InsightEngine = InsightEngine;
}
