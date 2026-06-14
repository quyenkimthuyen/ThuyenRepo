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
   * Phủ định gần keyword — giảm false positive (vd. "không lo" không ghi Lo lắng)
   */
  isKeywordNegated(normalized, index) {
    const before = normalized.slice(Math.max(0, index - 18), index);
    return /\b(không|chưa|chẳng|đừng|không hề|chưa hề|không còn)\s+$/.test(before);
  },

  /**
   * Match item từ library theo keywords — yêu cầu đủ keyword hit để tránh false positive
   */
  matchFromLibrary(text, library, options = {}) {
    const normalized = this.normalize(text);
    const matches = [];

    for (const item of library) {
      let score = 0;
      let keywordHits = 0;

      for (const kw of item.keywords) {
        const k = kw.toLowerCase();
        let searchFrom = 0;
        let kwMatched = false;
        while (searchFrom < normalized.length) {
          const idx = normalized.indexOf(k, searchFrom);
          if (idx === -1) break;
          if (!this.isKeywordNegated(normalized, idx)) {
            score += k.length;
            kwMatched = true;
            if (k.length <= 3) {
              const chBefore = idx > 0 ? normalized[idx - 1] : ' ';
              const chAfter =
                idx + k.length < normalized.length ? normalized[idx + k.length] : ' ';
              if (/[\s,.;!?]/.test(chBefore) && /[\s,.;!?]/.test(chAfter)) {
                score += 1;
              }
            }
          }
          searchFrom = idx + 1;
        }
        if (kwMatched) keywordHits += 1;
      }

      const requiredHits =
        options.minKeywordHits ??
        (item.keywords.length >= 3 ? 2 : item.keywords.length >= 2 ? 2 : 1);

      if (keywordHits >= requiredHits && score > 0) {
        matches.push({ ...item, score, keywordHits });
      }
    }

    matches.sort((a, b) => b.score - a.score || b.keywordHits - a.keywordHits);
    return matches;
  },

  /** Rút gọn nhãn từ câu user khi không khớp library */
  summarizeUserPhrase(text, maxLen = 60) {
    const t = (text || '').trim().replace(/\s+/g, ' ');
    if (!t) return '';
    return t.length > maxLen ? `${t.slice(0, maxLen)}...` : t;
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
    const patterns = CognitiveLibrary.ACTION_PATTERNS || [];
    return this.matchFromLibrary(text, patterns).slice(0, 2);
  },

  /**
   * Phát hiện identity từ text
   */
  extractIdentity(text) {
    const patterns = CognitiveLibrary.IDENTITY_PATTERNS || [];
    return this.matchFromLibrary(text, patterns).slice(0, 2);
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
   * Chip trả lời ngắn (cảm xúc nhanh, "không biết"...)
   */
  getShortSuggestions(session) {
    const flowStep = session?.flowStep || CognitiveLibrary.REFLECTION_FLOW[1];
    const pool =
      typeof I18n !== 'undefined' ? I18n.shortChips(flowStep) : [];
    if (pool.length === 0) return [];

    const lastGuide = [...(session.messages || [])]
      .reverse()
      .find((m) => m.role === 'guide');
    if (
      typeof I18n !== 'undefined'
        ? I18n.isSessionEndContent(lastGuide?.content)
        : lastGuide?.content?.includes('Góc khám phá')
    ) {
      return [];
    }

    return pool;
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
   * Tóm tắt phiên từ các ghi nhận
   */
  buildSessionSummary(session) {
    const nodeIds = session?.nodeIds || [];
    const nodes = DataStore.getNodes().filter((n) => nodeIds.includes(n.id));
    const pick = (type) => nodes.filter((n) => n.type === type).map((n) => n.label);
    const first = (type) => pick(type)[0] || '—';
    const join = (type) => pick(type).join(', ') || '—';

    if (typeof I18n !== 'undefined') {
      return I18n.t('reflection.summaryTemplate', {
        event: first('Event') !== '—' ? first('Event') : (session.initialThought || '—').slice(0, 60),
        emotion: join('Emotion'),
        interpretation: first('Interpretation'),
        belief: join('Belief'),
        value: join('Value'),
      });
    }

    return `Event: ${first('Event')}; Emotion: ${join('Emotion')}`;
  },

  /**
   * Tin nhắn kết thúc phiên: tóm tắt + reframe + bước nhỏ
   */
  buildSessionEndMessage(session) {
    const summary = this.buildSessionSummary(session);
    if (typeof I18n !== 'undefined') {
      return [
        `${I18n.t('reflection.summaryTitle')}: ${summary}`,
        I18n.t('reflection.sessionEnd'),
        I18n.t('reflection.reframeQuestion'),
        I18n.t('reflection.smallStepQuestion'),
      ].join('\n\n');
    }
    return 'Cảm ơn bạn đã chia sẻ.';
  },

  /**
   * Định dạng tin nhắn người dẫn — giọng phản chiếu, ít kỹ thuật
   */
  formatGuideMessage(result) {
    const stepChanged = result.flowStep !== result.previousStep;
    if (!stepChanged) return result.nextQuestion;
    return `${result.guidePrefix}\n\n${result.nextQuestion}`;
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
        evidenceType: 'direct_quote',
        evidence: [text],
        sourceSessionId: session.id,
      });
      extracted.event = node;
      nodesCreated.push(node);
      nodeIds.push(node.id);
    }

    // Chỉ trích xuất theo bước EEIBVIA hiện tại — tránh gán nhầm từ keyword lẫn bước
    const emotions = currentStep === 'Emotion' ? this.extractEmotions(text) : [];
    const values = currentStep === 'Value' ? this.extractValues(text) : [];
    const beliefs = currentStep === 'Belief' ? this.extractBeliefs(text) : [];
    const actions = currentStep === 'Action' ? this.extractActions(text) : [];
    const identities = currentStep === 'Identity' ? this.extractIdentity(text) : [];
    const biases = this.extractBiases(text);

    if (currentStep === 'Emotion') {
      const items = emotions.length > 0 ? emotions : [{ label: this.summarizeUserPhrase(text, 50), score: 1 }];
      for (const em of items.slice(0, 2)) {
        const label = em.label || text.slice(0, 40);
        const fromLibrary = em.score !== undefined && em.keywordHits !== undefined;
        const { node } = CognitiveTree.upsertNode({
          type: 'Emotion',
          label,
          sourceText: text,
          evidenceType: fromLibrary ? 'paraphrase' : 'direct_quote',
          evidence: [text],
          sourceSessionId: session.id,
          fromLibrary,
          matchScore: em.score,
          keywordHits: em.keywordHits,
        });
        extracted.emotions.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
        if (nodeIds.length >= 2) {
          CognitiveTree.linkNodes(nodeIds[nodeIds.length - 2], node.id, 'causes');
        }
      }
    }

    if (currentStep === 'Interpretation') {
      const interpLabel = text.length > 60 ? text.slice(0, 60) + '...' : text;
      const { node } = CognitiveTree.upsertNode({
        type: 'Interpretation',
        label: interpLabel,
        sourceText: text,
        evidenceType: 'direct_quote',
        evidence: [text],
        sourceSessionId: session.id,
      });
      extracted.interpretation = node;
      nodesCreated.push(node);
      nodeIds.push(node.id);
    }

    if (currentStep === 'Belief') {
      const items = beliefs.length > 0 ? [...beliefs] : [];
      if (items.length === 0 && (this.looksLikeBelief(text) || currentStep === 'Belief')) {
        items.push({ label: this.summarizeUserPhrase(text, 60) });
      }
      for (const b of items.slice(0, 2)) {
        const fromLibrary = b.score !== undefined && b.keywordHits !== undefined;
        const { node } = CognitiveTree.upsertNode({
          type: 'Belief',
          label: b.label,
          sourceText: text,
          evidenceType: fromLibrary ? 'paraphrase' : 'direct_quote',
          evidence: [text],
          sourceSessionId: session.id,
          fromLibrary,
          matchScore: b.score,
          keywordHits: b.keywordHits,
        });
        extracted.beliefs.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
      }
    }

    if (currentStep === 'Value') {
      const valueItems =
        values.length > 0
          ? values
          : this.looksLikeValue(text)
            ? [{ label: this.summarizeUserPhrase(text, 50) }]
            : [];
      for (const v of valueItems.slice(0, 2)) {
        const fromLibrary = v.score !== undefined && v.keywordHits !== undefined;
        const { node } = CognitiveTree.upsertNode({
          type: 'Value',
          label: v.label,
          sourceText: text,
          evidenceType: fromLibrary ? 'paraphrase' : 'direct_quote',
          evidence: [text],
          sourceSessionId: session.id,
          fromLibrary,
          matchScore: v.score,
          keywordHits: v.keywordHits,
        });
        extracted.values.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
      }
    }

    if (currentStep === 'Identity') {
      const identityItems =
        identities.length > 0
          ? identities
          : this.looksLikeIdentity(text)
            ? [{ label: this.summarizeUserPhrase(text, 50) }]
            : [];
      for (const id of identityItems.slice(0, 2)) {
        const fromLibrary = id.score !== undefined && id.keywordHits !== undefined;
        const { node } = CognitiveTree.upsertNode({
          type: 'Identity',
          label: id.label,
          sourceText: text,
          evidenceType: fromLibrary ? 'paraphrase' : 'direct_quote',
          evidence: [text],
          sourceSessionId: session.id,
          fromLibrary,
          matchScore: id.score,
          keywordHits: id.keywordHits,
        });
        extracted.identity.push(node);
        nodesCreated.push(node);
        nodeIds.push(node.id);
      }
    }

    if (currentStep === 'Action') {
      const actionItems =
        actions.length > 0
          ? actions
          : this.looksLikeAction(text)
            ? [{ label: this.summarizeUserPhrase(text, 50) }]
            : [];
      for (const a of actionItems.slice(0, 2)) {
        const fromLibrary = a.score !== undefined && a.keywordHits !== undefined;
        const { node } = CognitiveTree.upsertNode({
          type: 'Action',
          label: a.label,
          sourceText: text,
          evidenceType: fromLibrary ? 'paraphrase' : 'direct_quote',
          evidence: [text],
          sourceSessionId: session.id,
          fromLibrary,
          matchScore: a.score,
          keywordHits: a.keywordHits,
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
    const enteringNewStep = nextStep !== currentStep;

    if (enteringNewStep && nextStep === 'Value' && typeof I18n !== 'undefined') {
      nextQuestion = I18n.t('reflection.contextQuestion');
    } else if (enteringNewStep && nextStep === 'Identity' && typeof I18n !== 'undefined') {
      nextQuestion = I18n.t('reflection.powerQuestion');
    } else if (enteringNewStep || userMessageCount === 0) {
      nextQuestion = this.generateQuestion(nextStep, context);
    } else {
      nextQuestion = this.generateQuestion(currentStep, context);
    }

    // Kết thúc luồng — tổng kết + reframe + bước nhỏ
    if (nextStep === 'Action' && currentStep === 'Action' && userMessageCount >= 6) {
      nextQuestion = this.buildSessionEndMessage(session);
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
    const markers = [
      'lo rằng',
      'sợ rằng',
      'e rằng',
      'nghĩ rằng',
      'có lẽ',
      'có thể',
      'hình như',
      'có vẻ',
      'dường như',
      'cảm giác như',
      'tôi hiểu là',
      'tôi lo',
      'tôi sợ',
      'nếu không',
      'chắc chắn sẽ',
    ];
    if (markers.some((m) => n.includes(m))) return true;
    return /\b(sẽ|sẽ bị|sẽ không)\b/.test(n);
  },

  looksLikeBelief(text) {
    const n = this.normalize(text);
    const markers = [
      'tin rằng',
      'tôi tin',
      'niềm tin',
      'phải',
      'nên',
      'bắt buộc',
      'cần phải',
      'đáng lẽ',
      'luôn luôn',
      'không bao giờ',
      'mọi người đều',
      'ai cũng',
      'tất cả đều',
    ];
    return markers.some((m) => n.includes(m));
  },

  looksLikeValue(text) {
    const n = this.normalize(text);
    return (
      n.includes('quan trọng') ||
      n.includes('coi trọng') ||
      n.includes('trân trọng') ||
      n.includes('ưu tiên') ||
      n.includes('điều tôi quý') ||
      n.includes('giá trị')
    );
  },

  looksLikeIdentity(text) {
    const n = this.normalize(text);
    return (
      n.includes('tôi là') ||
      n.includes('mình là') ||
      n.includes('tôi thấy mình') ||
      n.includes('vai trò') ||
      n.includes('là người') ||
      n.includes('là một người') ||
      n.includes('là kiểu người') ||
      n.includes('tôi như một') ||
      n.includes('cảm giác mình là')
    );
  },

  looksLikeAction(text) {
    const n = this.normalize(text);
    const markers = [
      'tôi sẽ',
      'mình sẽ',
      'tôi muốn',
      'mình muốn',
      'tôi định',
      'đang cân nhắc',
      'dự định',
      'sẽ thử',
      'sẽ làm',
      'nhờ',
      'tìm cách',
    ];
    if (markers.some((m) => n.includes(m))) return true;
    return CognitiveLibrary.ACTION_PATTERNS?.some((item) =>
      item.keywords.some((kw) => n.includes(kw.toLowerCase()))
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
      content: this.formatGuideMessage(result),
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

  /**
   * Bỏ qua bước hiện tại — không ép người dùng trả lời
   */
  skipCurrentStep(sessionId) {
    const session = DataStore.getSession(sessionId);
    if (!session) return null;

    const flow = CognitiveLibrary.REFLECTION_FLOW;
    const currentIdx = flow.indexOf(session.flowStep);
    if (currentIdx === -1 || currentIdx >= flow.length - 1) return null;

    const currentStep = session.flowStep;
    const nextStep = flow[currentIdx + 1];

    session.messages.push({
      id: generateId('msg'),
      role: 'user',
      content:
        typeof I18n !== 'undefined'
          ? I18n.t('reflection.skippedStep')
          : '(Đã bỏ qua bước này)',
      flowStep: currentStep,
      timestamp: new Date().toISOString(),
    });

    const context = {
      eventLabel: session.initialThought,
    };

    let nextQuestion;
    if (nextStep === 'Value' && typeof I18n !== 'undefined') {
      nextQuestion = I18n.t('reflection.contextQuestion');
    } else if (nextStep === 'Identity' && typeof I18n !== 'undefined') {
      nextQuestion = I18n.t('reflection.powerQuestion');
    } else {
      nextQuestion = this.generateQuestion(nextStep, context);
    }

    const guidePrefix = this.getGuidePrefix(nextStep);
    const skipNote =
      typeof I18n !== 'undefined' ? I18n.t('reflection.skipNote') : 'Không sao.';
    const guideMsg = {
      id: generateId('msg'),
      role: 'guide',
      content: `${skipNote}\n\n${guidePrefix}\n\n${nextQuestion}`,
      flowStep: nextStep,
      timestamp: new Date().toISOString(),
    };

    session.messages.push(guideMsg);
    session.flowStep = nextStep;
    session.updatedAt = new Date().toISOString();

    DataStore.updateSession(sessionId, session);

    return { session, guideMessage: guideMsg };
  },

  /**
   * Chạy lại xử lý toàn phiên — giữ nguyên tin user, cập nhật câu người dẫn từ vị trí sửa
   */
  replaySessionFromUserIndex(session, editedUserIdx) {
    const nodesCreated = [];
    let nodeIds = [];

    for (let i = 0; i < session.messages.length; ) {
      const userMsg = session.messages[i];
      if (userMsg.role !== 'user') {
        i += 1;
        continue;
      }

      const prefix = session.messages.slice(0, i + 1);
      const result = this.processMessage(userMsg.content, {
        initialThought: session.initialThought,
        messages: prefix,
        flowStep: userMsg.flowStep,
        nodeIds: [...nodeIds],
      });
      nodeIds = result.nodeIds;
      nodesCreated.push(...result.nodesCreated);

      const guideIdx = i + 1;
      if (guideIdx < session.messages.length && session.messages[guideIdx].role === 'guide') {
        if (i >= editedUserIdx) {
          if (userMsg.flowStep === 'Event') {
            session.messages[guideIdx].content = this.getOpeningQuestion(userMsg.content);
            session.messages[guideIdx].flowStep = 'Emotion';
          } else {
            session.messages[guideIdx].content = this.formatGuideMessage(result);
            session.messages[guideIdx].flowStep = result.flowStep;
            session.messages[guideIdx].extracted = result.extracted;
          }
        }
        i = guideIdx + 1;
      } else {
        i += 1;
      }
    }

    const lastGuide = [...session.messages].reverse().find((m) => m.role === 'guide');
    session.flowStep = lastGuide?.flowStep ?? session.flowStep;
    session.nodeIds = nodeIds;

    return nodesCreated;
  },

  /**
   * Sửa tin nhắn user — giữ hội thoại phía sau, chạy lại xử lý để cập nhật ghi nhận
   */
  editUserMessage(sessionId, messageId, newText) {
    const session = DataStore.getSession(sessionId);
    if (!session || !newText?.trim()) return null;

    const idx = session.messages.findIndex((m) => m.id === messageId);
    if (idx === -1 || session.messages[idx].role !== 'user') return null;

    const trimmed = newText.trim();
    session.messages[idx].content = trimmed;
    session.messages[idx].editedAt = new Date().toISOString();

    if (session.messages[idx].flowStep === 'Event') {
      session.initialThought = trimmed;
    }

    const nodesCreated = this.replaySessionFromUserIndex(session, idx);
    session.updatedAt = new Date().toISOString();

    DataStore.updateSession(sessionId, session);
    TimelineEngine.recordNodeChanges(nodesCreated);

    const insights = InsightEngine.analyze();
    DataStore.setInsights(insights);

    return { session, nodesCreated };
  },
};

if (typeof window !== 'undefined') {
  window.ReflectionEngine = ReflectionEngine;
}
