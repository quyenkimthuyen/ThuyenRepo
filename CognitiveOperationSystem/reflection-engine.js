/**
 * Reflection Engine — Mô phỏng AI bằng rule engine
 *
 * Nhiệm vụ:
 * 1. Phân loại dữ liệu vào framework EEIBVIA
 * 2. Chọn cảm xúc, giá trị, niềm tin phù hợp
 * 3. Sinh câu hỏi tiếp theo theo luồng
 *
 * Mở rộng: thay processMessage() bằng OpenAI/Cursor API call.
 * Giữ interface { extracted, nextQuestion, flowStep, nodesCreated }
 */

const ReflectionEngine = {
  /**
   * Chuẩn hóa text để match
   */
  normalize(text) {
    return (text || '').toLowerCase().trim();
  },

  /**
   * Match item từ library theo keywords
   */
  matchFromLibrary(text, library) {
    const normalized = this.normalize(text);
    const matches = [];

    for (const item of library) {
      const score = item.keywords.reduce((s, kw) => {
        if (normalized.includes(kw.toLowerCase())) return s + kw.length;
        return s;
      }, 0);
      if (score > 0) {
        matches.push({ ...item, score });
      }
    }

    matches.sort((a, b) => b.score - a.score);
    return matches;
  },

  /**
   * Trích xuất cảm xúc từ text
   */
  extractEmotions(text) {
    return this.matchFromLibrary(text, CognitiveLibrary.EMOTIONS).slice(0, 3);
  },

  /**
   * Trích xuất giá trị
   */
  extractValues(text) {
    return this.matchFromLibrary(text, CognitiveLibrary.VALUES).slice(0, 3);
  },

  /**
   * Trích xuất niềm tin
   */
  extractBeliefs(text) {
    return this.matchFromLibrary(text, CognitiveLibrary.BELIEFS).slice(0, 3);
  },

  /**
   * Trích xuất thiên kiến
   */
  extractBiases(text) {
    return this.matchFromLibrary(text, CognitiveLibrary.COGNITIVE_BIASES).slice(0, 2);
  },

  /**
   * Phát hiện hành động từ text
   */
  extractActions(text) {
    const normalized = this.normalize(text);
    const actionPatterns = [
      { label: 'Làm việc nhiều giờ', keywords: ['14 giờ', 'làm việc nhiều', 'overtime', 'làm đêm'] },
      { label: 'La mắng / kỷ luật con', keywords: ['la mắng', 'phạt', 'đánh', 'mắng'] },
      { label: 'Bắt con học', keywords: ['bắt học', 'ép học', 'phải học'] },
      { label: 'Tránh né / im lặng', keywords: ['im lặng', 'tránh', 'không nói'] },
      { label: 'Tìm kiếm giải pháp', keywords: ['tìm cách', 'giải quyết', 'làm gì'] },
      { label: 'Tự trách móc', keywords: ['tự trách', 'trách mình', 'tại tôi'] },
      { label: 'Nhờ giúp đỡ', keywords: ['nhờ', 'hỏi', 'tư vấn'] },
      { label: 'Nghỉ ngơi', keywords: ['nghỉ', 'nghỉ ngơi', 'thư giãn'] },
      { label: 'Đầu tư thời gian cho gia đình', keywords: ['dành thời gian', 'ở bên', 'chơi cùng'] },
      { label: 'So sánh với người khác', keywords: ['so sánh', 'nhà hàng xóm', 'con nhà'] },
    ];

    return this.matchFromLibrary(text, actionPatterns).slice(0, 2);
  },

  /**
   * Phát hiện identity từ text
   */
  extractIdentity(text) {
    const normalized = this.normalize(text);
    const identities = [
      { label: 'Người cha/mẹ', keywords: ['cha', 'mẹ', 'bố', 'ba', 'làm cha', 'làm mẹ'] },
      { label: 'Người làm việc', keywords: ['nhân viên', 'làm việc', 'công việc'] },
      { label: 'Người học', keywords: ['học sinh', 'sinh viên', 'học'] },
      { label: 'Người trưởng thành', keywords: ['trưởng thành', 'người lớn'] },
      { label: 'Người thất bại', keywords: ['thất bại', 'tồi', 'không đủ'] },
      { label: 'Người bảo vệ', keywords: ['bảo vệ', 'che chở', 'hy sinh'] },
      { label: 'Người kiểm soát', keywords: ['kiểm soát', 'quản lý', 'ra lệnh'] },
    ];

    return this.matchFromLibrary(text, identities).slice(0, 2);
  },

  /**
   * Xác định bước tiếp theo trong luồng EEIBVIA
   */
  getNextFlowStep(currentStep, messageCount) {
    const flow = CognitiveLibrary.REFLECTION_FLOW;
    const currentIdx = flow.indexOf(currentStep);

    if (currentIdx === -1) return flow[0];

    // Sau mỗi 1-2 tin nhắn user, tiến bước
    if (messageCount > 0 && messageCount % 1 === 0 && currentIdx < flow.length - 1) {
      return flow[currentIdx + 1];
    }

    return currentStep;
  },

  /**
   * Sinh câu hỏi phản chiếu
   */
  generateQuestion(flowStep, context = {}) {
    const questions =
      typeof I18n !== 'undefined'
        ? I18n.reflectionQuestions(flowStep)
        : CognitiveLibrary.REFLECTION_QUESTIONS[flowStep];
    if (!questions || questions.length === 0) {
      return typeof I18n !== 'undefined'
        ? I18n.t('reflection.shareMore')
        : 'Bạn muốn chia sẻ thêm điều gì?';
    }

    if (flowStep === 'Emotion' && context.eventLabel) {
      return typeof I18n !== 'undefined'
        ? I18n.t('reflection.emotionWithEvent', { event: context.eventLabel })
        : `Khi nghĩ về "${context.eventLabel}", bạn cảm thấy thế nào?`;
    }
    if (flowStep === 'Interpretation' && context.emotionLabel) {
      return typeof I18n !== 'undefined'
        ? I18n.t('reflection.interpretationWithEmotion', {
            emotion: context.emotionLabel.toLowerCase(),
          })
        : `Bạn lo điều gì sẽ xảy ra khi cảm thấy ${context.emotionLabel.toLowerCase()}?`;
    }
    if (flowStep === 'Belief' && context.interpretation) {
      return typeof I18n !== 'undefined'
        ? I18n.t('reflection.beliefPrompt')
        : 'Điều gì khiến bạn tin như vậy?';
    }

    const idx = Math.floor(Math.random() * questions.length);
    return questions[idx];
  },

  /**
   * Gợi ý mẫu trả lời theo bước hiện tại trong session
   */
  getSuggestions(session) {
    const flowStep = session?.flowStep || CognitiveLibrary.REFLECTION_FLOW[1];
    const pool =
      typeof I18n !== 'undefined'
        ? I18n.reflectionSuggestions(flowStep)
        : CognitiveLibrary.REFLECTION_SUGGESTIONS[flowStep] || [];
    if (pool.length === 0) return [];

    const lastGuide = [...(session.messages || [])]
      .reverse()
      .find((m) => m.role === 'guide');
    if (typeof I18n !== 'undefined' ? I18n.isSessionEndContent(lastGuide?.content) : lastGuide?.content?.includes('Góc khám phá')) {
      return [];
    }

    const eventSnippet = (session.initialThought || '').slice(0, 30);
    const suggestions = [...pool];

    if (flowStep === 'Emotion' && eventSnippet) {
      suggestions[0] =
        typeof I18n !== 'undefined'
          ? I18n.t('reflection.emotionSuggestion')
          : 'Khi nghĩ về việc đó, tôi cảm thấy lo lắng và căng thẳng';
    }

    return suggestions.slice(0, 5);
  },

  /**
   * Câu mở đầu session
   */
  getOpeningQuestion(initialThought) {
    const snippet = `${initialThought.slice(0, 60)}${initialThought.length > 60 ? '...' : ''}`;
    const emotions = this.extractEmotions(initialThought);
    if (typeof I18n !== 'undefined') {
      return emotions.length > 0
        ? I18n.t('reflection.openingWithThought', { thought: snippet })
        : I18n.t('reflection.openingDefault');
    }
    if (emotions.length > 0) {
      return `Tôi nghe thấy bạn đang đề cập đến "${snippet}". Điều đó khiến bạn cảm thấy thế nào?`;
    }
    return 'Điều đó khiến bạn cảm thấy thế nào?';
  },

  /**
   * Xử lý tin nhắn user — core processing
   * @returns {Object} Kết quả xử lý
   */
  processMessage(text, session) {
    const flow = CognitiveLibrary.REFLECTION_FLOW;
    let currentStep = session.flowStep || flow[0];
    const userMessageCount = (session.messages || []).filter((m) => m.role === 'user').length;

    const extracted = {
      event: null,
      emotions: [],
      interpretation: null,
      beliefs: [],
      values: [],
      identity: [],
      actions: [],
      biases: [],
    };

    const nodesCreated = [];
    const nodeIds = session.nodeIds || [];

    // Bước đầu: Event từ initial thought hoặc message hiện tại
    if (userMessageCount === 0 || currentStep === 'Event') {
      const eventLabel = text.length > 80 ? text.slice(0, 80) + '...' : text;
      const { node } = CognitiveTree.upsertNode({
        type: 'Event',
        label: eventLabel,
        sourceText: text,
      });
      extracted.event = node;
      nodesCreated.push(node);
      nodeIds.push(node.id);
    }

    // Trích xuất theo bước hiện tại và text
    const emotions = this.extractEmotions(text);
    const values = this.extractValues(text);
    const beliefs = this.extractBeliefs(text);
    const actions = this.extractActions(text);
    const identities = this.extractIdentity(text);
    const biases = this.extractBiases(text);

    // Luôn cố gắng map vào framework từ mọi message
    if (currentStep === 'Emotion' || emotions.length > 0) {
      const items = emotions.length > 0 ? emotions : [{ label: text.slice(0, 50), score: 1 }];
      for (const em of items.slice(0, 2)) {
        const label = em.label || text.slice(0, 40);
        const { node } = CognitiveTree.upsertNode({
          type: 'Emotion',
          label,
          sourceText: text,
        });
        extracted.emotions.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
        if (nodeIds.length >= 2) {
          CognitiveTree.linkNodes(nodeIds[nodeIds.length - 2], node.id, 'causes');
        }
      }
    }

    if (currentStep === 'Interpretation' || this.looksLikeInterpretation(text)) {
      const interpLabel = text.length > 60 ? text.slice(0, 60) + '...' : text;
      const { node } = CognitiveTree.upsertNode({
        type: 'Interpretation',
        label: interpLabel,
        sourceText: text,
      });
      extracted.interpretation = node;
      nodesCreated.push(node);
      nodeIds.push(node.id);
    }

    if (currentStep === 'Belief' || beliefs.length > 0) {
      const items = beliefs.length > 0 ? beliefs : [];
      if (items.length === 0 && this.looksLikeBelief(text)) {
        items.push({ label: text.slice(0, 60) });
      }
      for (const b of items.slice(0, 2)) {
        const { node } = CognitiveTree.upsertNode({
          type: 'Belief',
          label: b.label,
          sourceText: text,
        });
        extracted.beliefs.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
      }
    }

    if (currentStep === 'Value' || values.length > 0) {
      for (const v of values.slice(0, 2)) {
        const { node } = CognitiveTree.upsertNode({
          type: 'Value',
          label: v.label,
          sourceText: text,
        });
        extracted.values.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
      }
    }

    if (currentStep === 'Identity' || identities.length > 0) {
      for (const id of identities.slice(0, 2)) {
        const { node } = CognitiveTree.upsertNode({
          type: 'Identity',
          label: id.label,
          sourceText: text,
        });
        extracted.identity.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
      }
    }

    if (currentStep === 'Action' || actions.length > 0) {
      for (const a of actions.slice(0, 2)) {
        const { node } = CognitiveTree.upsertNode({
          type: 'Action',
          label: a.label,
          sourceText: text,
        });
        extracted.actions.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
      }
    }

    // Ghi nhận biases (không tạo node framework chính, lưu vào insights)
    extracted.biases = biases;

    // Tiến luồng
    const nextStep = this.getNextFlowStep(currentStep, userMessageCount + 1);

    const context = {
      eventLabel: extracted.event?.label || session.initialThought,
      emotionLabel: extracted.emotions[0]?.label,
      interpretation: extracted.interpretation?.label,
    };

    let nextQuestion;
    if (nextStep !== currentStep || userMessageCount === 0) {
      nextQuestion = this.generateQuestion(nextStep, context);
    } else {
      nextQuestion = this.generateQuestion(currentStep, context);
    }

    // Kết thúc luồng — tổng kết
    if (nextStep === 'Action' && currentStep === 'Action' && userMessageCount >= 6) {
      nextQuestion =
        typeof I18n !== 'undefined'
          ? I18n.t('reflection.sessionEnd')
          : 'Cảm ơn bạn đã chia sẻ. Tôi đã cập nhật bản đồ suy nghĩ của bạn. Bạn có muốn xem Góc khám phá không?';
    }

    return {
      extracted,
      nodesCreated,
      nodeIds,
      flowStep: nextStep,
      previousStep: currentStep,
      nextQuestion,
      guidePrefix: this.getGuidePrefix(nextStep),
    };
  },

  /**
   * Prefix cho Reflection Guide theo bước
   */
  getGuidePrefix(step) {
    const label = CognitiveLibrary.getFrameworkLabel(step);
    const icons = {
      Event: '📍',
      Emotion: '💭',
      Interpretation: '🔍',
      Belief: '💡',
      Value: '🌟',
      Identity: '🪞',
      Action: '⚡',
    };
    const icon = icons[step] || '🧠';
    const fallback =
      typeof I18n !== 'undefined' ? I18n.t('reflection.fallbackReflection') : 'Suy ngẫm';
    return `${icon} ${label || fallback}`;
  },

  looksLikeInterpretation(text) {
    const n = this.normalize(text);
    return (
      n.includes('sẽ') ||
      n.includes('có thể') ||
      n.includes('lo rằng') ||
      n.includes('nghĩ rằng') ||
      n.includes('có lẽ')
    );
  },

  looksLikeBelief(text) {
    const n = this.normalize(text);
    return (
      n.includes('phải') ||
      n.includes('luôn') ||
      n.includes('không bao giờ') ||
      n.includes('tin rằng') ||
      n.includes('nên')
    );
  },

  /**
   * Tạo session mới
   */
  createSession(initialThought) {
    const session = {
      id: generateId('session'),
      initialThought,
      messages: [],
      flowStep: 'Event',
      nodeIds: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'active',
    };

    DataStore.addSession(session);

    // Xử lý initial thought như event
    const result = this.processMessage(initialThought, session);

    const openingMsg = {
      id: generateId('msg'),
      role: 'guide',
      content: this.getOpeningQuestion(initialThought),
      flowStep: 'Emotion',
      timestamp: new Date().toISOString(),
    };

    session.messages.push({
      id: generateId('msg'),
      role: 'user',
      content: initialThought,
      flowStep: 'Event',
      timestamp: new Date().toISOString(),
    });

    session.messages.push(openingMsg);
    session.flowStep = 'Emotion';
    session.nodeIds = result.nodeIds;

    DataStore.updateSession(session.id, session);

    // Timeline event
    TimelineEngine.recordSessionStart(session, result.nodesCreated);

    return { session, openingQuestion: openingMsg.content };
  },

  /**
   * Tiếp tục session với user reply
   */
  continueSession(sessionId, userText) {
    const session = DataStore.getSession(sessionId);
    if (!session) return null;

    session.messages.push({
      id: generateId('msg'),
      role: 'user',
      content: userText,
      flowStep: session.flowStep,
      timestamp: new Date().toISOString(),
    });

    const result = this.processMessage(userText, session);

    const guideMsg = {
      id: generateId('msg'),
      role: 'guide',
      content: `${result.guidePrefix}: ${result.nextQuestion}`,
      flowStep: result.flowStep,
      extracted: result.extracted,
      timestamp: new Date().toISOString(),
    };

    session.messages.push(guideMsg);
    session.flowStep = result.flowStep;
    session.nodeIds = result.nodeIds;
    session.updatedAt = new Date().toISOString();

    DataStore.updateSession(sessionId, session);

    // Cập nhật timeline khi có node verified mới
    TimelineEngine.recordNodeChanges(result.nodesCreated);

    // Refresh insights
    const insights = InsightEngine.analyze();
    DataStore.setInsights(insights);

    return { session, result, guideMessage: guideMsg };
  },
};

if (typeof window !== 'undefined') {
  window.ReflectionEngine = ReflectionEngine;
}
