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
      label: typeof I18n !== 'undefined' ? I18n.biasLabel(b) : b.labelVi || b.label,
      labelEn: b.label,
      score: b.score,
      description: this.getBiasDescription(b.label),
    }));
  },

  getBiasDescription(biasName) {
    if (typeof I18n !== 'undefined') return I18n.biasDescription(biasName);
    return 'Kiểu suy nghĩ này có thể ảnh hưởng cách bạn hiểu sự việc.';
  },

  /**
   * Gợi ý suy ngẫm tiếp — bám mâu thuẫn, thiên kiến, niềm tin nổi bật
   */
  getExplorationPrompts(insights) {
    const rules = CognitiveLibrary.EXPLORATION_PROMPT_RULES || [];
    const sorted = [...rules].sort((a, b) => (a.priority ?? 50) - (b.priority ?? 50));
    const matched = [];
    const seenIds = new Set();

    for (const rule of sorted) {
      if (seenIds.has(rule.id)) continue;
      if (!rule.matches(insights)) continue;

      const vars = typeof rule.vars === 'function' ? rule.vars(insights) : {};
      const data =
        typeof I18n !== 'undefined' ? I18n.explorationPrompt(rule.id, vars) : null;
      if (!data) continue;

      matched.push(data);
      seenIds.add(rule.id);
      if (matched.length >= 4) break;
    }

    return matched;
  },

  /**
   * Tổng hợp insight đầy đủ
   */
  mergeAiInsights(base) {
    const overlay = DataStore.getAiOverlay('insights');
    if (!overlay) return base;

    const seenMsg = new Set(base.contradictions.map((c) => c.message));
    const aiContradictions = (overlay.contradictions || [])
      .filter((c) => c.message && !seenMsg.has(c.message))
      .map((c) => ({
        id: generateId('contradiction'),
        type: 'ai',
        severity: c.severity === 'high' ? 'high' : 'medium',
        message: c.message,
        detectedAt: overlay.importedAt,
      }));

    const aiExploration = (overlay.explorationPrompts || []).map((p) => ({
      source: p.source,
      prompt: p.prompt,
      seedThought: p.seedThought,
      fromAi: true,
    }));

    const biasKeys = new Set(base.biases.map((b) => b.label.toLowerCase()));
    const aiBiases = (overlay.biases || [])
      .filter((b) => b.label && !biasKeys.has(b.label.toLowerCase()))
      .map((b) => ({
        label: b.label,
        labelEn: b.label,
        score: 1,
        description: b.description || '',
        fromAi: true,
      }));

    return {
      ...base,
      contradictions: [...base.contradictions, ...aiContradictions],
      explorationPrompts: [...aiExploration, ...base.explorationPrompts].slice(0, 6),
      biases: [...aiBiases, ...base.biases].slice(0, 8),
      aiSummary: overlay.summary || '',
      aiPatterns: overlay.patterns || [],
      aiImportedAt: overlay.importedAt,
    };
  },

  analyzeRules() {
    const contradictions = ContradictionEngine.analyze();
    const todayDiscoveries = this.getTodayDiscoveries();
    const topBeliefs = this.getTopByType('Belief', 5);
    const topValues = this.getTopByType('Value', 5);
    const topEmotions = this.getTopByType('Emotion', 5);
    const biases = this.detectBiasesFromSessions();

    const recentlyVerified = DataStore.getNodes()
      .filter((n) => n.status === 'verified')
      .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
      .slice(0, 5);

    const partial = {
      todayDiscoveries,
      topBeliefs,
      topValues,
      topEmotions,
      contradictions,
      biases,
      recentlyVerified,
    };

    return {
      ...partial,
      explorationPrompts: this.getExplorationPrompts(partial),
      stats: CognitiveTree.getStats(),
      generatedAt: new Date().toISOString(),
    };
  },

  /** Chỉ nội dung overlay ChatGPT — không trộn rule */
  getAiInsights() {
    const overlay = DataStore.getAiOverlay('insights');
    if (!overlay) return null;

    return {
      aiSummary: overlay.summary || '',
      aiPatterns: overlay.patterns || [],
      contradictions: (overlay.contradictions || []).map((c) => ({
        id: generateId('contradiction'),
        type: 'ai',
        severity: c.severity === 'high' ? 'high' : 'medium',
        message: c.message,
        detectedAt: overlay.importedAt,
      })),
      explorationPrompts: (overlay.explorationPrompts || []).map((p) => ({
        source: p.source,
        prompt: p.prompt,
        seedThought: p.seedThought,
        fromAi: true,
      })),
      biases: (overlay.biases || []).map((b) => ({
        label: b.label,
        labelEn: b.label,
        score: 1,
        description: b.description || '',
        fromAi: true,
      })),
      aiImportedAt: overlay.importedAt,
    };
  },

  analyze() {
    return this.analyzeRules();
  },

  /**
   * Format node cho hiển thị
   */
  formatNodeCard(node) {
    const colors = CognitiveLibrary.NODE_TYPE_COLORS[node.type] || {};
    return {
      ...node,
      colors,
      typeLabel: CognitiveLibrary.getFrameworkLabel(node.type),
      statusLabel: CognitiveLibrary.getNodeStatusLabel(node.status),
    };
  },
};

if (typeof window !== 'undefined') {
  window.InsightEngine = InsightEngine;
}
