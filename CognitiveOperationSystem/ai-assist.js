/**
 * AI Assist (gián tiếp) — Prompt ChatGPT + nhập kết quả vào app
 *
 * Luồng: Prompt 1 → chat ChatGPT → Prompt 2 → paste JSON → import EEIBVIA
 */

const AI_ASSIST_PROMPTS = {
  vi: {
    reflection: (thought) => `Bạn là người dẫn suy ngẫm (reflection guide). Bạn KHÔNG phải bác sĩ tâm lý, KHÔNG chẩn đoán, KHÔNG kê đơn, và KHÔNG ra lệnh hành động ("bạn nên...", "phải làm...").

Nhiệm vụ: dẫn tôi qua khung 7 bước EEIBVIA:
1. Event — Việc xảy ra (tình huống cụ thể)
2. Emotion — Cảm xúc nổi bật
3. Interpretation — Cách tôi hiểu / lo điều gì
4. Belief — Niềm tin ẩn dưới cách hiểu đó
5. Value — Điều quan trọng với tôi trong việc này
6. Identity — Tôi thấy mình là ai trong tình huống này
7. Action — Hành động tôi đang cân nhắc (không bắt buộc phải quyết ngay)

Quy tắc bắt buộc:
- Hỏi TỪNG bước một; chờ tôi trả lời rồi mới chuyển bước tiếp theo
- Dùng câu hỏi mở, phản chiếu, không phán xét
- Tóm tắt ngắn những gì bạn nghe được trước khi hỏi tiếp
- Không nhảy cóc, không gom nhiều bước trong một câu hỏi
- Nếu tôi đề cập tự hại / tự tử / muốn chết: nhắc tôi liên hệ đường dây nóng 111 hoặc Tổng đài tâm lý 18001929 và tìm người hỗ trợ gần
- Trả lời bằng tiếng Việt

Suy nghĩ ban đầu của tôi (bước Event):
"""
${thought}
"""

Hãy xác nhận ngắn gọn bạn đã hiểu tình huống, rồi bắt đầu hỏi về cảm xúc (bước Emotion).`,

    export: `Dựa trên TOÀN BỘ cuộc hội thoại suy ngẫm vừa rồi, hãy xuất kết quả theo ĐÚNG định dạng JSON sau.

Yêu cầu:
- Chỉ trả về một khối JSON hợp lệ (có thể bọc trong \`\`\`json ... \`\`\`)
- Không thêm giải thích ngoài JSON
- label: nhãn ngắn gọn tiếng Việt
- quote: trích sát ý tôi đã nói (hoặc tóm tắt 1 câu)
- Mỗi mảng tối đa 3 phần tử; thiếu thông tin thì dùng [] hoặc null

Schema:
{
  "initialThought": "suy nghĩ mở đầu",
  "event": { "label": "tóm tắt việc xảy ra", "detail": "chi tiết ngắn" },
  "emotions": [{ "label": "Lo lắng", "quote": "..." }],
  "interpretation": { "label": "...", "detail": "..." },
  "beliefs": [{ "label": "...", "quote": "..." }],
  "values": [{ "label": "...", "quote": "..." }],
  "identity": [{ "label": "...", "quote": "..." }],
  "actions": [{ "label": "...", "quote": "..." }],
  "summary": "tóm tắt 2-3 câu toàn phiên",
  "reframe": "một góc nhìn nhẹ hơn (không ra lệnh)",
  "smallStep": "một bước nhỏ người dùng có thể cân nhắc (không mệnh lệnh)"
}`,
  },

  en: {
    reflection: (thought) => `You are a reflection guide. You are NOT a therapist, you do NOT diagnose, prescribe, or give commands ("you should...", "you must...").

Guide me through the 7-step EEIBVIA framework:
1. Event — What happened (concrete situation)
2. Emotion — Prominent feelings
3. Interpretation — What I fear or how I read the situation
4. Belief — Hidden beliefs under that interpretation
5. Value — What matters most to me here
6. Identity — Who I see myself as in this situation
7. Action — What I am considering (no pressure to decide now)

Rules:
- Ask ONE step at a time; wait for my reply before the next step
- Use open, reflective questions; no judgment
- Briefly mirror what you heard before asking the next question
- Do not skip steps or bundle multiple steps in one question
- If I mention self-harm or suicide: encourage contacting local crisis lines and trusted support
- Reply in English

My initial thought (Event step):
"""
${thought}
"""

Please briefly confirm you understand, then ask about emotions (step 2).`,

    export: `Based on our ENTIRE reflection conversation, export the result in this EXACT JSON format.

Requirements:
- Return only valid JSON (may wrap in \`\`\`json ... \`\`\`)
- No explanation outside JSON
- label: short label in English
- quote: close to what I said (or one-sentence summary)
- Max 3 items per array; use [] or null if missing

Schema:
{
  "initialThought": "opening thought",
  "event": { "label": "event summary", "detail": "short detail" },
  "emotions": [{ "label": "Anxious", "quote": "..." }],
  "interpretation": { "label": "...", "detail": "..." },
  "beliefs": [{ "label": "...", "quote": "..." }],
  "values": [{ "label": "...", "quote": "..." }],
  "identity": [{ "label": "...", "quote": "..." }],
  "actions": [{ "label": "...", "quote": "..." }],
  "summary": "2-3 sentence session summary",
  "reframe": "a gentler perspective (not a command)",
  "smallStep": "one small step to consider (not an order)"
}`,
  },
};

const AiAssist = {
  getLocale() {
    return typeof I18n !== 'undefined' && I18n.locale === 'en' ? 'en' : 'vi';
  },

  getReflectionPrompt(thought) {
    const locale = this.getLocale();
    const t = (thought || '').trim();
    return AI_ASSIST_PROMPTS[locale].reflection(t || (locale === 'en' ? '(your thought)' : '(suy nghĩ của bạn)'));
  },

  getExportPrompt() {
    return AI_ASSIST_PROMPTS[this.getLocale()].export;
  },

  /**
   * Trích JSON từ phản hồi ChatGPT (raw text)
   */
  extractJsonBlock(text) {
    const raw = (text || '').trim();
    if (!raw) return null;

    const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
    if (fenced) {
      try {
        return JSON.parse(fenced[1].trim());
      } catch {
        /* fall through */
      }
    }

    const firstBrace = raw.indexOf('{');
    const lastBrace = raw.lastIndexOf('}');
    if (firstBrace !== -1 && lastBrace > firstBrace) {
      try {
        return JSON.parse(raw.slice(firstBrace, lastBrace + 1));
      } catch {
        /* fall through */
      }
    }

    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  normalizeItem(item) {
    if (!item) return null;
    if (typeof item === 'string') {
      const label = item.trim();
      return label ? { label, quote: label } : null;
    }
    if (typeof item === 'object' && item.label) {
      return {
        label: String(item.label).trim(),
        quote: item.quote ? String(item.quote).trim() : String(item.label).trim(),
      };
    }
    return null;
  },

  normalizeItems(items) {
    if (!items) return [];
    const arr = Array.isArray(items) ? items : [items];
    return arr.map((i) => this.normalizeItem(i)).filter(Boolean);
  },

  normalizeField(field) {
    if (!field) return null;
    if (typeof field === 'string') {
      const label = field.trim();
      return label ? { label, detail: label } : null;
    }
    if (typeof field === 'object' && field.label) {
      return {
        label: String(field.label).trim(),
        detail: field.detail ? String(field.detail).trim() : String(field.label).trim(),
      };
    }
    return null;
  },

  /**
   * Chuẩn hóa payload sau parse
   */
  normalizePayload(data) {
    if (!data || typeof data !== 'object') return null;

    const event = this.normalizeField(data.event);
    const interpretation = this.normalizeField(data.interpretation);

    return {
      initialThought: String(data.initialThought || event?.detail || event?.label || '').trim(),
      event,
      emotions: this.normalizeItems(data.emotions),
      interpretation,
      beliefs: this.normalizeItems(data.beliefs),
      values: this.normalizeItems(data.values),
      identity: this.normalizeItems(data.identity),
      actions: this.normalizeItems(data.actions),
      summary: data.summary ? String(data.summary).trim() : '',
      reframe: data.reframe ? String(data.reframe).trim() : '',
      smallStep: data.smallStep ? String(data.smallStep).trim() : '',
    };
  },

  parseExport(text) {
    const json = this.extractJsonBlock(text);
    if (!json) {
      return { ok: false, error: 'invalid_json' };
    }
    const payload = this.normalizePayload(json);
    if (!payload?.initialThought && !payload?.event?.label) {
      return { ok: false, error: 'missing_event' };
    }
    return { ok: true, payload };
  },

  buildCombinedText(data) {
    const parts = [data.initialThought];
    if (data.event?.detail) parts.push(data.event.detail);
    if (data.event?.label) parts.push(data.event.label);
    if (data.interpretation?.detail) parts.push(data.interpretation.detail);
    if (data.interpretation?.label) parts.push(data.interpretation.label);
    for (const list of [
      data.emotions,
      data.beliefs,
      data.values,
      data.identity,
      data.actions,
    ]) {
      for (const item of list || []) {
        if (item?.quote) parts.push(item.quote);
        if (item?.label) parts.push(item.label);
      }
    }
    if (data.summary) parts.push(data.summary);
    if (data.reframe) parts.push(data.reframe);
    if (data.smallStep) parts.push(data.smallStep);
    return parts.filter(Boolean).join('\n');
  },

  scanRuleEngine(text) {
    if (typeof ReflectionEngine === 'undefined') {
      return {
        emotions: [],
        beliefs: [],
        values: [],
        identity: [],
        actions: [],
        biases: [],
      };
    }
    return {
      emotions: ReflectionEngine.extractEmotions(text),
      beliefs: ReflectionEngine.extractBeliefs(text),
      values: ReflectionEngine.extractValues(text),
      identity: ReflectionEngine.extractIdentity(text),
      actions: ReflectionEngine.extractActions(text),
      biases: ReflectionEngine.extractBiases(text),
    };
  },

  labelKey(type, label) {
    return `${type}:${(label || '').toLowerCase().trim()}`;
  },

  collectLabelKeys(nodes) {
    const keys = new Set();
    for (const n of nodes || []) {
      keys.add(this.labelKey(n.type, n.label));
    }
    return keys;
  },

  filterRuleAdds(ruleMatches, existingKeys, type, limit = 3) {
    const items = ruleMatches[type] || [];
    const adds = [];
    for (const item of items) {
      const key = this.labelKey(type, item.label);
      if (existingKeys.has(key)) continue;
      existingKeys.add(key);
      adds.push({ label: item.label, source: 'rule' });
      if (adds.length >= limit) break;
    }
    return adds;
  },

  /**
   * Xem trước trước khi nhập — không ghi DB
   */
  buildImportPreview(text) {
    const parsed = this.parseExport(text);
    if (!parsed.ok) return parsed;

    const data = parsed.payload;
    const combined = this.buildCombinedText(data);
    const rule = this.scanRuleEngine(combined);
    const existingKeys = new Set();

    const aiRow = (step, type, items) => {
      const labels = (items || [])
        .map((i) => i?.label)
        .filter(Boolean)
        .map((label) => {
          existingKeys.add(this.labelKey(type, label));
          return { label, source: 'ai' };
        });
      return { step, type, items: labels };
    };

    const rows = [
      aiRow('Event', 'Event', data.event ? [data.event] : []),
      aiRow('Emotion', 'Emotion', data.emotions),
      aiRow('Interpretation', 'Interpretation', data.interpretation ? [data.interpretation] : []),
      aiRow('Belief', 'Belief', data.beliefs),
      aiRow('Value', 'Value', data.values),
      aiRow('Identity', 'Identity', data.identity),
      aiRow('Action', 'Action', data.actions),
    ];

    const ruleEnrichments = [
      { step: 'Emotion', type: 'Emotion', items: this.filterRuleAdds(rule, existingKeys, 'emotions') },
      { step: 'Belief', type: 'Belief', items: this.filterRuleAdds(rule, existingKeys, 'beliefs') },
      { step: 'Value', type: 'Value', items: this.filterRuleAdds(rule, existingKeys, 'values') },
      { step: 'Identity', type: 'Identity', items: this.filterRuleAdds(rule, existingKeys, 'identity') },
      { step: 'Action', type: 'Action', items: this.filterRuleAdds(rule, existingKeys, 'actions') },
    ].filter((r) => r.items.length > 0);

    const biases = (rule.biases || []).slice(0, 3).map((b) => ({
      label: typeof I18n !== 'undefined' ? I18n.biasLabel(b) : b.labelVi || b.label,
      source: 'rule',
    }));

    return {
      ok: true,
      payload: data,
      combined,
      rows,
      ruleEnrichments,
      biases,
    };
  },

  enrichFromRuleEngine(data, nodeIds, nodesCreated) {
    const combined = this.buildCombinedText(data);
    const rule = this.scanRuleEngine(combined);
    const existingKeys = this.collectLabelKeys(nodesCreated);

    const addFromRule = (type, items, limit = 2) => {
      for (const item of (items || []).slice(0, limit)) {
        const key = this.labelKey(type, item.label);
        if (existingKeys.has(key)) continue;
        existingKeys.add(key);
        this.upsertTypedNode(
          type,
          { label: item.label, quote: combined },
          combined,
          nodeIds,
          nodesCreated
        );
      }
    };

    addFromRule('Emotion', rule.emotions);
    addFromRule('Belief', rule.beliefs);
    addFromRule('Value', rule.values);
    addFromRule('Identity', rule.identity);
    addFromRule('Action', rule.actions);

    return rule.biases || [];
  },

  appendQuoteMessages(session, data) {
    const locale = this.getLocale();
    const ts = () => new Date().toISOString();
    const pushQuote = (content, flowStep) => {
      const text = (content || '').trim();
      if (!text) return;
      session.messages.push({
        id: generateId('msg'),
        role: 'user',
        content: text,
        flowStep,
        timestamp: ts(),
        imported: true,
      });
    };

    for (const em of data.emotions) pushQuote(em.quote || em.label, 'Emotion');
    pushQuote(data.interpretation?.detail || data.interpretation?.label, 'Interpretation');
    for (const b of data.beliefs) pushQuote(b.quote || b.label, 'Belief');
    for (const v of data.values) pushQuote(v.quote || v.label, 'Value');
    for (const id of data.identity) pushQuote(id.quote || id.label, 'Identity');
    for (const a of data.actions) pushQuote(a.quote || a.label, 'Action');
    if (data.summary) pushQuote(data.summary, 'Interpretation');
  },

  buildEeibviaSummaryMessage(data) {
    const locale = this.getLocale();
    const empty = locale === 'en' ? '(not recorded)' : '(chưa ghi nhận)';
    const label = (step) =>
      typeof CognitiveLibrary !== 'undefined'
        ? CognitiveLibrary.getFrameworkLabel(step)
        : step;
    const fmt = (items) =>
      (items || [])
        .map((i) => i?.label)
        .filter(Boolean)
        .join(', ') || empty;
    const lines = [
      `📍 ${label('Event')}: ${data.event?.label || data.initialThought || empty}`,
      `💭 ${label('Emotion')}: ${fmt(data.emotions)}`,
      `🔍 ${label('Interpretation')}: ${data.interpretation?.label || empty}`,
      `💡 ${label('Belief')}: ${fmt(data.beliefs)}`,
      `🌟 ${label('Value')}: ${fmt(data.values)}`,
      `🪞 ${label('Identity')}: ${fmt(data.identity)}`,
      `⚡ ${label('Action')}: ${fmt(data.actions)}`,
    ];
    const title =
      locale === 'en' ? 'EEIBVIA summary (from ChatGPT)' : 'Tóm tắt 7 bước (từ ChatGPT)';
    return {
      id: generateId('msg'),
      role: 'guide',
      content: `${title}\n\n${lines.join('\n')}`,
      flowStep: 'Action',
      timestamp: new Date().toISOString(),
      imported: true,
    };
  },

  upsertTypedNode(type, item, sourceText, nodeIds, nodesCreated) {
    if (!item?.label) return null;
    const { node } = CognitiveTree.upsertNode({
      type,
      label: item.label,
      sourceText: item.quote || sourceText,
    });
    nodesCreated.push(node);
    if (nodeIds.length > 0) {
      CognitiveTree.linkNodes(nodeIds[nodeIds.length - 1], node.id, 'causes');
    }
    nodeIds.push(node.id);
    return node;
  },

  /**
   * Nhập kết quả ChatGPT → phiên + nodes + insights
   */
  importSession(payload) {
    const data = this.normalizePayload(payload);
    if (!data) {
      return { ok: false, error: 'invalid_payload' };
    }

    const initialThought =
      data.initialThought || data.event?.detail || data.event?.label || '';
    if (!initialThought.trim()) {
      return { ok: false, error: 'missing_event' };
    }

    const session = {
      id: generateId('session'),
      initialThought,
      messages: [],
      flowStep: 'Action',
      nodeIds: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'completed',
      source: 'ai_assist',
    };

    const nodesCreated = [];
    const nodeIds = [];

    const eventLabel = data.event?.label || initialThought.slice(0, 80);
    const eventNode = this.upsertTypedNode(
      'Event',
      { label: eventLabel, quote: data.event?.detail || initialThought },
      initialThought,
      nodeIds,
      nodesCreated
    );

    for (const em of data.emotions.slice(0, 3)) {
      this.upsertTypedNode('Emotion', em, em.quote || initialThought, nodeIds, nodesCreated);
    }

    if (data.interpretation) {
      this.upsertTypedNode(
        'Interpretation',
        data.interpretation,
        data.interpretation.detail || data.interpretation.label,
        nodeIds,
        nodesCreated
      );
    }

    for (const b of data.beliefs.slice(0, 3)) {
      this.upsertTypedNode('Belief', b, b.quote || initialThought, nodeIds, nodesCreated);
    }
    for (const v of data.values.slice(0, 3)) {
      this.upsertTypedNode('Value', v, v.quote || initialThought, nodeIds, nodesCreated);
    }
    for (const id of data.identity.slice(0, 3)) {
      this.upsertTypedNode('Identity', id, id.quote || initialThought, nodeIds, nodesCreated);
    }
    for (const a of data.actions.slice(0, 3)) {
      this.upsertTypedNode('Action', a, a.quote || initialThought, nodeIds, nodesCreated);
    }

    this.enrichFromRuleEngine(data, nodeIds, nodesCreated);
    session.nodeIds = nodeIds;

    const locale = this.getLocale();
    const importedNote =
      locale === 'en'
        ? '(Imported from ChatGPT reflection)'
        : '(Đã nhập từ phiên suy ngẫm ChatGPT)';

    session.messages.push({
      id: generateId('msg'),
      role: 'user',
      content: initialThought,
      flowStep: 'Event',
      timestamp: new Date().toISOString(),
      imported: true,
    });

    this.appendQuoteMessages(session, data);

    const summaryParts = [];
    if (data.summary) summaryParts.push(data.summary);
    if (data.reframe) {
      summaryParts.push(
        locale === 'en' ? `Reframe: ${data.reframe}` : `Góc nhìn khác: ${data.reframe}`
      );
    }
    if (data.smallStep) {
      summaryParts.push(
        locale === 'en' ? `Small step: ${data.smallStep}` : `Bước nhỏ: ${data.smallStep}`
      );
    }

    const endMarker =
      typeof I18n !== 'undefined'
        ? I18n.t('reflection.sessionEndMarker')
        : locale === 'en'
          ? 'Explore'
          : 'Góc khám phá';

    const guideContent =
      summaryParts.length > 0
        ? `${importedNote}\n\n${summaryParts.join('\n\n')}\n\n${
            locale === 'en'
              ? `Recorded in your cognitive map. See more in ${endMarker}.`
              : `Đã ghi nhận vào bản đồ suy nghĩ. Xem thêm ở ${endMarker}.`
          }`
        : typeof I18n !== 'undefined'
          ? I18n.t('reflection.sessionEnd')
          : locale === 'en'
            ? 'Thank you for sharing. Recorded in your cognitive map.'
            : 'Cảm ơn bạn đã chia sẻ. Đã ghi nhận vào bản đồ suy nghĩ.';

    session.messages.push(this.buildEeibviaSummaryMessage(data));

    session.messages.push({
      id: generateId('msg'),
      role: 'guide',
      content: guideContent,
      flowStep: 'Action',
      extracted: { event: eventNode },
      timestamp: new Date().toISOString(),
      imported: true,
    });

    DataStore.addSession(session);
    TimelineEngine.recordSessionStart(session, nodesCreated);
    TimelineEngine.recordNodeChanges(nodesCreated);

    const insights = InsightEngine.analyze();
    DataStore.setInsights(insights);

    return { ok: true, session, nodesCreated, insights };
  },

  importFromText(text) {
    const parsed = this.parseExport(text);
    if (!parsed.ok) return parsed;
    return this.importSession(parsed.payload);
  },
};

if (typeof window !== 'undefined') {
  window.AiAssist = AiAssist;
}
