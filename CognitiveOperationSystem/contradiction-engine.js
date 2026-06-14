/**
 * Contradiction Engine — Phát hiện mâu thuẫn nhận thức
 *
 * Ví dụ: Value "Gia đình ưu tiên" vs Action "Làm việc 14h/ngày"
 *
 * Mở rộng: dùng LLM để phân tích semantic contradiction.
 */

const ContradictionEngine = {
  /**
   * Kiểm tra text có chứa keyword nào không
   */
  textMatches(text, keywords) {
    const n = (text || '').toLowerCase();
    return keywords.some((kw) => n.includes(kw.toLowerCase()));
  },

  /**
   * Kiểm tra node có match keywords
   */
  nodeMatches(node, keywords) {
    if (!node) return false;
    return this.textMatches(node.label, keywords);
  },

  /**
   * Tìm mâu thuẫn từ patterns cố định
   */
  detectFromPatterns(nodes) {
    const contradictions = [];
    const { CONTRADICTION_PATTERNS } = CognitiveLibrary;

    const values = nodes.filter((n) => n.type === 'Value');
    const beliefs = nodes.filter((n) => n.type === 'Belief');
    const actions = nodes.filter((n) => n.type === 'Action');

    for (const pattern of CONTRADICTION_PATTERNS) {
      let matchedValue = null;
      let matchedBelief = null;
      let matchedAction = null;

      if (pattern.valueKeywords) {
        matchedValue = values.find((v) => this.nodeMatches(v, pattern.valueKeywords));
      }
      if (pattern.beliefKeywords) {
        matchedBelief = beliefs.find((b) => this.nodeMatches(b, pattern.beliefKeywords));
      }
      if (pattern.actionKeywords) {
        matchedAction = actions.find((a) => this.nodeMatches(a, pattern.actionKeywords));
      }

      const hasValueBeliefConflict = matchedValue && matchedBelief && pattern.beliefKeywords;
      const hasValueActionConflict = matchedValue && matchedAction && pattern.actionKeywords;
      const hasBeliefValueConflict = matchedBelief && matchedValue && !pattern.actionKeywords;

      if (hasValueActionConflict || hasValueBeliefConflict || hasBeliefValueConflict) {
        contradictions.push({
          id: generateId('contradiction'),
          type: 'pattern',
          severity: 'medium',
          message: pattern.message,
          nodes: {
            value: matchedValue,
            belief: matchedBelief,
            action: matchedAction,
          },
          detectedAt: new Date().toISOString(),
        });
      }
    }

    return contradictions;
  },

  /**
   * Tìm mâu thuẫn từ relations conflicts
   */
  detectFromRelations() {
    const contradictions = [];
    const relations = DataStore.getRelations().filter((r) => r.type === 'conflicts');
    const nodes = DataStore.getNodes();

    for (const rel of relations) {
      const source = nodes.find((n) => n.id === rel.source);
      const target = nodes.find((n) => n.id === rel.target);
      if (source && target) {
        contradictions.push({
          id: generateId('contradiction'),
          type: 'relation',
          severity: 'high',
          message: `"${source.label}" (${source.type}) mâu thuẫn với "${target.label}" (${target.type})`,
          nodes: { source, target },
          detectedAt: new Date().toISOString(),
        });
      }
    }

    return contradictions;
  },

  /**
   * Phát hiện belief đối lập
   */
  detectOpposingBeliefs(beliefs) {
    const oppositions = [
      ['tiền mang lại hạnh phúc', 'hạnh phúc không cần tiền'],
      ['con phải nghe lời', 'con cần tự lập'],
      ['phải hoàn hảo', 'sai lầm là bình thường'],
      ['làm việc chăm chỉ', 'nghỉ ngơi'],
      ['kiểm soát', 'tự do'],
      ['con trai phải mạnh', 'được yếu đuối'],
      ['phụ nữ phải nhẫn', 'tự chủ'],
      ['sếp luôn có lý', 'công bằng'],
      ['tôi phải tự lo', 'nhờ giúp'],
      ['nợ là đáng xấu hổ', 'tiền không quyết định'],
      ['mẹ chồng luôn đúng', 'ranh giới'],
      ['thành công phải có nhà xe', 'hạnh phúc đơn giản'],
    ];

    const contradictions = [];
    const labels = beliefs.map((b) => b.label.toLowerCase());

    for (const [a, b] of oppositions) {
      const hasA = labels.some((l) => l.includes(a) || a.includes(l));
      const hasB = labels.some((l) => l.includes(b) || b.includes(l));
      if (hasA && hasB) {
        const nodeA = beliefs.find((b) => b.label.toLowerCase().includes(a.split(' ')[0]));
        const nodeB = beliefs.find((b) => b.label.toLowerCase().includes(b.split(' ')[0]));
        contradictions.push({
          id: generateId('contradiction'),
          type: 'opposing_belief',
          severity: 'medium',
          message: `Niềm tin đối lập: "${nodeA?.label || a}" và "${nodeB?.label || b}"`,
          nodes: { beliefA: nodeA, beliefB: nodeB },
          detectedAt: new Date().toISOString(),
        });
      }
    }

    return contradictions;
  },

  /**
   * Phát hiện value-action gap
   */
  detectValueActionGap(nodes) {
    const contradictions = [];
    const values = nodes.filter((n) => n.type === 'Value' && n.status !== 'draft');
    const actions = nodes.filter((n) => n.type === 'Action');

    const gaps = [
      {
        valueKw: ['gia đình', 'yêu thương'],
        actionKw: ['làm việc nhiều', '14 giờ', 'không có thời gian'],
        msg: 'coi trọng gia đình, nhưng ít thời gian thực sự dành cho gia đình',
      },
      {
        valueKw: ['sức khỏe'],
        actionKw: ['stress', 'không ngủ', 'mệt'],
        msg: 'coi trọng sức khỏe, nhưng nhịp sống hiện tại có vẻ đang gây căng thẳng',
      },
      {
        valueKw: ['phát triển', 'học hỏi'],
        actionKw: ['bắt con học', 'ép học', 'la mắng'],
        msg: 'coi trọng phát triển, nhưng đôi khi hành động có vẻ tạo áp lực hơn là khuyến khích',
      },
      {
        valueKw: ['tự chăm sóc', 'chăm sóc bản thân'],
        actionKw: ['hy sinh', '14 giờ', 'không ngủ'],
        msg: 'coi trọng tự chăm sóc, nhưng nhịp sống hiện tại có vẻ chưa dành chỗ cho bản thân',
      },
      {
        valueKw: ['biên giới', 'ranh giới', 'nói không'],
        actionKw: ['làm hài lòng', 'không dám từ chối'],
        msg: 'coi trọng ranh giới, nhưng hành động có vẻ vẫn ưu tiên làm hài lòng người khác',
      },
      {
        valueKw: ['trung thực', 'chân thành'],
        actionKw: ['im lặng', 'che giấu', 'giấu'],
        msg: 'coi trọng trung thực, nhưng đôi khi chọn im lặng hoặc che giấu',
      },
      {
        valueKw: ['hiếu thảo'],
        actionKw: ['tránh', 'im lặng', 'cãi'],
        msg: 'coi trọng hiếu thảo, nhưng giao tiếp với cha mẹ có vẻ đang khó khăn',
      },
    ];

    for (const gap of gaps) {
      const val = values.find((v) => this.nodeMatches(v, gap.valueKw));
      const act = actions.find((a) => this.nodeMatches(a, gap.actionKw));
      if (val && act) {
        contradictions.push({
          id: generateId('contradiction'),
          type: 'value_action_gap',
          severity: val.status === 'verified' ? 'high' : 'medium',
          message: gap.msg,
          nodes: { value: val, action: act },
          detectedAt: new Date().toISOString(),
        });
      }
    }

    return contradictions;
  },

  /**
   * Chạy toàn bộ phát hiện mâu thuẫn
   */
  analyze() {
    const allNodes = DataStore.getNodes();
    const nodes =
      typeof EvidenceEngine !== 'undefined'
        ? EvidenceEngine.filterInsightEligible(allNodes)
        : allNodes;
    const beliefs = nodes.filter((n) => n.type === 'Belief');

    const results = [
      ...this.detectFromPatterns(nodes),
      ...this.detectFromRelations(),
      ...this.detectOpposingBeliefs(beliefs),
      ...this.detectValueActionGap(nodes),
    ];

    // Dedupe theo message
    const seen = new Set();
    return results.filter((c) => {
      if (seen.has(c.message)) return false;
      seen.add(c.message);
      return true;
    });
  },
};

if (typeof window !== 'undefined') {
  window.ContradictionEngine = ContradictionEngine;
}
