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
- quote: trích ĐÚNG câu user đã nói trong hội thoại (không tự bịa niềm tin/giá trị mới)
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
- quote: EXACT words the user said in the conversation (do not invent new beliefs/values)
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
    if (typeof I18n !== 'undefined' && typeof I18n.getPromptLocale === 'function') {
      return I18n.getPromptLocale();
    }
    return typeof I18n !== 'undefined' && I18n.locale === 'en' ? 'en' : 'vi';
  },

  getReflectionPrompt(thought) {
    const locale = this.getLocale();
    const t = (thought || '').trim();
    return AI_ASSIST_PROMPTS[locale].reflection(t || (locale === 'en' ? '(your thought)' : '(suy nghĩ của bạn)'));
  },

  getExportPrompt() {
    const locale = this.getLocale();
    const base = AI_ASSIST_PROMPTS[locale].export;
    const langLine =
      locale === 'en'
        ? '\n\nAll JSON string values must be in English.'
        : '\n\nMọi giá trị chuỗi trong JSON phải bằng tiếng Việt.';
    return base + langLine;
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

  diagnoseJsonError(text) {
    const raw = (text || '').trim();
    if (!raw) return 'empty';
    if (raw.includes('```') && !raw.includes('{')) return 'fenced_no_json';
    if (!raw.includes('{')) return 'no_object';
    const slice = raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1);
    try {
      JSON.parse(slice);
      return 'parse_failed';
    } catch (e) {
      return e.message || 'parse_failed';
    }
  },

  parseExport(text) {
    const raw = (text || '').trim();
    if (!raw) {
      return { ok: false, error: 'empty', hint: 'empty' };
    }
    const json = this.extractJsonBlock(text);
    if (!json) {
      return { ok: false, error: 'invalid_json', hint: this.diagnoseJsonError(text) };
    }
    const payload = this.normalizePayload(json);
    if (!payload?.initialThought && !payload?.event?.label) {
      return { ok: false, error: 'missing_event', hint: 'missing_event' };
    }
    return { ok: true, payload };
  },

  mapTranscriptRole(label) {
    const key = (label || '').toLowerCase();
    if (['user', 'you', 'human', 'bạn', 'tôi', 'me'].includes(key)) return 'user';
    return 'guide';
  },

  /**
   * Parse nhật ký ChatGPT dạng "User: ..." / "ChatGPT: ..."
   */
  parseTranscript(text) {
    const trimmed = (text || '').trim();
    if (!trimmed) return [];

    const headerRe =
      /^(?:#{1,3}\s*)?(User|You|Human|Bạn|Tôi|Me|Assistant|ChatGPT|AI|Trợ lý)\s*:\s*/gim;
    const hasHeaders = headerRe.test(trimmed);
    headerRe.lastIndex = 0;

    if (!hasHeaders) {
      return [{ role: 'user', content: trimmed }];
    }

    const parts = [];
    let lastIndex = 0;
    let lastRole = null;
    let match;

    while ((match = headerRe.exec(trimmed)) !== null) {
      if (lastRole !== null) {
        const content = trimmed.slice(lastIndex, match.index).trim();
        if (content) parts.push({ role: lastRole, content });
      }
      lastRole = this.mapTranscriptRole(match[1]);
      lastIndex = match.index + match[0].length;
    }

    if (lastRole !== null) {
      const content = trimmed.slice(lastIndex).trim();
      if (content) parts.push({ role: lastRole, content });
    }

    return parts;
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

  normalizeForMatch(text) {
    return (text || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{M}/gu, '')
      .trim();
  },

  significantWords(text) {
    return this.normalizeForMatch(text)
      .split(/[^\p{L}\p{N}]+/u)
      .filter((w) => w.length >= 2);
  },

  /** Corpus neo bằng chứng: transcript user hoặc các bước EEIBVIA trước Belief/Value/... */
  collectAnchorCorpus(data, transcript) {
    if ((transcript || '').trim()) {
      return this.parseTranscript(transcript)
        .filter((t) => t.role === 'user')
        .map((t) => t.content)
        .join('\n');
    }
    const parts = [data.initialThought];
    if (data.event?.detail) parts.push(data.event.detail);
    if (data.event?.label) parts.push(data.event.label);
    for (const em of data.emotions || []) {
      if (em?.quote) parts.push(em.quote);
      else if (em?.label) parts.push(em.label);
    }
    if (data.interpretation?.detail) parts.push(data.interpretation.detail);
    if (data.interpretation?.label) parts.push(data.interpretation.label);
    return parts.filter(Boolean).join('\n');
  },

  isQuoteAnchored(quote, anchorCorpus, { minOverlap = 2 } = {}) {
    const q = this.normalizeForMatch(quote);
    const corpus = this.normalizeForMatch(anchorCorpus);
    if (!q || !corpus) return false;
    if (corpus.includes(q)) return true;
    if (q.length >= 10) {
      const snippet = q.slice(0, Math.min(24, q.length));
      if (corpus.includes(snippet)) return true;
    }
    const qWords = this.significantWords(quote);
    const cWords = new Set(this.significantWords(anchorCorpus));
    let overlap = 0;
    for (const w of qWords) {
      if (cWords.has(w)) overlap += 1;
    }
    const required = q.length <= 20 ? 1 : minOverlap;
    return overlap >= required;
  },

  isKnownLibraryLabel(label, type) {
    if (typeof CognitiveLibrary === 'undefined' || !label) return false;
    const libs = {
      Belief: CognitiveLibrary.BELIEFS,
      Value: CognitiveLibrary.VALUES,
      Emotion: CognitiveLibrary.EMOTIONS,
    };
    const lib = libs[type];
    if (!lib) return false;
    const n = this.normalizeForMatch(label);
    return lib.some((item) => this.normalizeForMatch(item.label) === n);
  },

  validateImportAnchoring(data, transcript) {
    const unanchored = [];
    const baseAnchor = this.collectAnchorCorpus(data, '');

    if ((transcript || '').trim()) {
      const userCorpus = this.collectAnchorCorpus(data, transcript);
      const lists = [
        ['Belief', data.beliefs],
        ['Value', data.values],
        ['Identity', data.identity],
        ['Action', data.actions],
      ];
      for (const [type, items] of lists) {
        for (const item of items || []) {
          const quote = (item?.quote || item?.detail || item?.label || '').trim();
          if (!quote) continue;
          if (!this.isQuoteAnchored(quote, userCorpus, { minOverlap: 2 })) {
            unanchored.push({ type, label: item.label, quote });
          }
        }
      }
      return { anchor: userCorpus, unanchored };
    }

    const lists = [
      ['Belief', data.beliefs],
      ['Value', data.values],
      ['Identity', data.identity],
      ['Action', data.actions],
    ];

    for (const [type, items] of lists) {
      for (const item of items || []) {
        const quote = (item?.quote || item?.detail || item?.label || '').trim();
        if (!quote) continue;

        const isLibrary = this.isKnownLibraryLabel(item.label, type);
        const quoteEqualsLabel =
          this.normalizeForMatch(quote) === this.normalizeForMatch(item.label);
        const anchored = this.isQuoteAnchored(quote, baseAnchor, { minOverlap: 2 });

        const suspicious =
          (isLibrary && !anchored) ||
          (quoteEqualsLabel && quote.length > 28 && !anchored && type === 'Belief');

        if (suspicious) {
          unanchored.push({ type, label: item.label, quote });
        }
      }
    }

    return { anchor: baseAnchor, unanchored };
  },

  isItemAnchored(type, item, anchoring) {
    if (!item?.label || !anchoring?.unanchored?.length) return true;
    const label = item.label;
    return !anchoring.unanchored.some((u) => u.type === type && u.label === label);
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
  buildImportPreview(text, options = {}) {
    const parsed = this.parseExport(text);
    if (!parsed.ok) return parsed;

    const data = parsed.payload;
    const combined = this.buildCombinedText(data);
    const anchoring = this.validateImportAnchoring(data, options.transcript || '');
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

    const emptySteps = rows
      .filter((r) => !r.items.length && r.type !== 'Event')
      .map((r) => r.type);
    const aiCount = rows.reduce((n, r) => n + r.items.length, 0);
    const ruleCount = ruleEnrichments.reduce((n, r) => n + r.items.length, 0);

    const warnings = [];
    if (ruleCount > 0) {
      warnings.push('rule_suggestions_skipped');
    }
    if (emptySteps.length >= 4) {
      warnings.push('many_empty_steps');
    }
    if (!data.interpretation?.label) {
      warnings.push('no_interpretation');
    }
    if (!data.emotions?.length) {
      warnings.push('no_emotions');
    }
    if (anchoring.unanchored.length > 0) {
      warnings.push('unanchored_quotes');
    }

    return {
      ok: true,
      payload: data,
      combined,
      rows,
      ruleEnrichments,
      biases,
      anchoring,
      stats: {
        aiCount,
        ruleCount,
        emptySteps,
        stepCount: rows.filter((r) => r.items.length).length,
        unanchoredCount: anchoring.unanchored.length,
      },
      warnings,
    };
  },

  /**
   * Không thêm node từ rule engine khi import ChatGPT — chỉ dùng JSON đã nhập.
   * Rule suggestions chỉ hiện ở preview, không ghi DB.
   */
  enrichFromRuleEngine() {
    return [];
  },

  appendTranscriptMessages(session, turns) {
    const ts = () => new Date().toISOString();
    for (const turn of turns || []) {
      const content = (turn.content || '').trim();
      if (!content) continue;
      session.messages.push({
        id: generateId('msg'),
        role: turn.role === 'guide' ? 'guide' : 'user',
        content,
        flowStep: turn.role === 'guide' ? session.flowStep || 'Interpretation' : 'Event',
        timestamp: ts(),
        imported: true,
        fromTranscript: true,
      });
    }
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
    const title = I18n.t('aiAssist.eeibviaSummaryTitle');
    return {
      id: generateId('msg'),
      role: 'guide',
      content: `${title}\n\n${lines.join('\n')}`,
      flowStep: 'Action',
      timestamp: new Date().toISOString(),
      imported: true,
    };
  },

  upsertTypedNode(type, item, sourceText, nodeIds, nodesCreated, sessionId, meta = {}) {
    if (!item?.label) return null;
    const quote = (item.quote || '').trim();
    const anchored = meta.anchored !== false;
    const { node } = CognitiveTree.upsertNode({
      type,
      label: item.label,
      sourceText: quote || sourceText,
      evidenceType: anchored ? 'imported' : 'inferred',
      evidence: quote ? [quote] : sourceText ? [sourceText] : [],
      sourceSessionId: sessionId,
      userConfirmed: anchored ? null : false,
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
  importSession(payload, options = {}) {
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
    const anchoring = this.validateImportAnchoring(data, options.transcript || '');
    const nodeMeta = (type, item) => ({
      anchored: this.isItemAnchored(type, item, anchoring),
    });

    const eventLabel = data.event?.label || initialThought.slice(0, 80);
    const eventNode = this.upsertTypedNode(
      'Event',
      { label: eventLabel, quote: data.event?.detail || initialThought },
      initialThought,
      nodeIds,
      nodesCreated,
      session.id
    );

    for (const em of data.emotions.slice(0, 3)) {
      this.upsertTypedNode(
        'Emotion',
        em,
        em.quote || initialThought,
        nodeIds,
        nodesCreated,
        session.id,
        nodeMeta('Emotion', em)
      );
    }

    if (data.interpretation) {
      this.upsertTypedNode(
        'Interpretation',
        data.interpretation,
        data.interpretation.detail || data.interpretation.label,
        nodeIds,
        nodesCreated,
        session.id,
        nodeMeta('Interpretation', data.interpretation)
      );
    }

    for (const b of data.beliefs.slice(0, 3)) {
      this.upsertTypedNode(
        'Belief',
        b,
        b.quote || initialThought,
        nodeIds,
        nodesCreated,
        session.id,
        nodeMeta('Belief', b)
      );
    }
    for (const v of data.values.slice(0, 3)) {
      this.upsertTypedNode(
        'Value',
        v,
        v.quote || initialThought,
        nodeIds,
        nodesCreated,
        session.id,
        nodeMeta('Value', v)
      );
    }
    for (const id of data.identity.slice(0, 3)) {
      this.upsertTypedNode(
        'Identity',
        id,
        id.quote || initialThought,
        nodeIds,
        nodesCreated,
        session.id,
        nodeMeta('Identity', id)
      );
    }
    for (const a of data.actions.slice(0, 3)) {
      this.upsertTypedNode(
        'Action',
        a,
        a.quote || initialThought,
        nodeIds,
        nodesCreated,
        session.id,
        nodeMeta('Action', a)
      );
    }

    session.nodeIds = nodeIds;

    const locale = this.getLocale();
    const importedNote =
      typeof I18n !== 'undefined' ? I18n.t('aiAssist.importedNote') : '(Từ phiên ChatGPT)';

    session.messages.push({
      id: generateId('msg'),
      role: 'user',
      content: initialThought,
      flowStep: 'Event',
      timestamp: new Date().toISOString(),
      imported: true,
    });

    const transcriptTurns = options.transcript
      ? this.parseTranscript(options.transcript)
      : [];
    if (transcriptTurns.length > 0) {
      session.transcriptImported = true;
      this.appendTranscriptMessages(session, transcriptTurns);
    } else {
      this.appendQuoteMessages(session, data);
    }

    const summaryParts = [];
    if (data.summary) summaryParts.push(data.summary);
    if (data.reframe) {
      const label =
        typeof I18n !== 'undefined' ? I18n.t('aiAssist.reframeLabel') : 'Góc nhìn khác';
      summaryParts.push(`${label}: ${data.reframe}`);
    }
    if (data.smallStep) {
      const label =
        typeof I18n !== 'undefined' ? I18n.t('aiAssist.smallStepLabel') : 'Bước nhỏ';
      summaryParts.push(`${label}: ${data.smallStep}`);
    }

    const endMarker =
      typeof I18n !== 'undefined'
        ? I18n.t('reflection.sessionEndMarker')
        : locale === 'en'
          ? 'Explore'
          : 'Khám phá';

    const guideContent =
      summaryParts.length > 0
        ? `${importedNote}\n\n${summaryParts.join('\n\n')}\n\n${
            typeof I18n !== 'undefined'
              ? I18n.t('aiAssist.recordedInMap', { marker: endMarker })
              : `Đã ghi vào bản đồ suy nghĩ. Mở ${endMarker}.`
          }`
        : typeof I18n !== 'undefined'
          ? I18n.t('reflection.sessionEnd')
          : locale === 'en'
            ? 'Thank you for sharing. Saved to your thought map.'
            : 'Cảm ơn bạn đã chia sẻ. Đã ghi vào bản đồ suy nghĩ.';

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

    return { ok: true, session, nodesCreated, insights, anchoring };
  },

  importFromText(text, options = {}) {
    const parsed = this.parseExport(text);
    if (!parsed.ok) return parsed;
    const preview = this.buildImportPreview(text, options);
    return this.importSession(parsed.payload, { ...options, anchoring: preview.anchoring });
  },
};

if (typeof window !== 'undefined') {
  window.AiAssist = AiAssist;
}
