/**
 * AI Assist — Bản đồ, Khám phá, Dòng thời gian
 * Prompt → ChatGPT → paste JSON → app xử lý
 */

const AI_SCREEN_PROMPTS = {
  vi: {
    insights: {
      analysisIntro: `Bạn là chuyên gia phân tích nhận thức (không phải bác sĩ tâm lý). Phân tích dữ liệu bản đồ suy nghĩ dưới đây.

Quy tắc:
- Chỉ đưa câu hỏi suy ngẫm, không ra lệnh hành động
- Không chẩn đoán bệnh lý
- Tìm mâu thuẫn NGỮ NGHĨA (không chỉ trùng từ)
- Nhận diện pattern lặp, thiên kiến, chủ đề ẩn
- Trả lời tiếng Việt khi trao đổi với user`,
      export: `Xuất phân tích KHÁM PHÁ theo JSON (chỉ JSON, có thể bọc \`\`\`json):

{
  "summary": "tóm tắt 2-4 câu",
  "contradictions": [{ "message": "mô tả mâu thuẫn ngắn", "severity": "medium|high" }],
  "explorationPrompts": [{ "source": "nhãn nguồn", "prompt": "câu hỏi suy ngẫm", "seedThought": "câu mở để user tiếp tục" }],
  "biases": [{ "label": "tên thiên kiến", "description": "giải thích ngắn" }],
  "patterns": [{ "label": "pattern", "detail": "mô tả" }]
}

Tối đa 5 mâu thuẫn, 4 gợi ý, 3 thiên kiến, 4 pattern.`,
    },
    forest: {
      analysisIntro: `Bạn là chuyên gia tổ chức tri thức cá nhân. Phân tích bản đồ suy nghĩ (nodes theo lĩnh vực).

Quy tắc:
- Đề xuất quan hệ có ý nghĩa giữa các ghi nhận (supports/conflicts/causes)
- Gợi ý chỉnh lĩnh vực (family/work/finance/learning/health/self) nếu lệch
- Không chẩn đoán; tone khám phá
- Trả lời tiếng Việt`,
      export: `Xuất phân tích BẢN ĐỒ theo JSON:

{
  "summary": "tóm tắt 2-3 câu",
  "relations": [{ "sourceType": "Belief", "sourceLabel": "...", "targetType": "Value", "targetLabel": "...", "relationType": "conflicts|supports|causes|related" }],
  "nodeUpdates": [{ "type": "Belief", "label": "...", "category": "family|work|finance|learning|health|self", "note": "ghi chú ngắn" }],
  "treeInsights": [{ "treeId": "family", "theme": "chủ đề", "observation": "nhận xét" }]
}

Dùng đúng type EEIBVIA: Event, Emotion, Interpretation, Belief, Value, Identity, Action.
Tối đa 8 relations, 6 nodeUpdates, 6 treeInsights.`,
    },
    timeline: {
      analysisIntro: `Bạn là người kể câu chuyện phát triển nhận thức. Phân tích dòng thời gian và ghi nhận theo thời gian.

Quy tắc:
- Nhận ra bước ngoặt, chuyển giá trị/niềm tin, arc phát triển
- Không tiên đoán tương lai cứng nhắc
- Câu hỏi suy ngẫm, không mệnh lệnh
- Trả lời tiếng Việt`,
      export: `Xuất phân tích DÒNG THỜI GIAN theo JSON:

{
  "narrativeArc": "câu chuyện 3-5 câu",
  "milestones": [{ "title": "...", "description": "...", "period": "2024 hoặc 2024-Q2", "type": "shift|insight|turning_point" }],
  "valueShifts": [{ "from": "...", "to": "...", "note": "...", "period": "..." }],
  "reflectionPrompt": "một câu hỏi suy ngẫm về hành trình"
}

Tối đa 6 milestones, 4 valueShifts.`,
    },
  },
  en: {
    insights: {
      analysisIntro: `You analyze personal cognitive maps (not a therapist). Analyze the data below.

Rules:
- Reflective questions only, no commands
- No clinical diagnosis
- Find semantic contradictions, not just keyword overlap
- Identify recurring patterns and biases
- Reply in English when chatting`,
      export: `Export EXPLORE analysis as JSON only:

{
  "summary": "2-4 sentences",
  "contradictions": [{ "message": "short contradiction", "severity": "medium|high" }],
  "explorationPrompts": [{ "source": "label", "prompt": "reflective question", "seedThought": "seed for home input" }],
  "biases": [{ "label": "bias name", "description": "short explanation" }],
  "patterns": [{ "label": "pattern", "detail": "description" }]
}`,
    },
    forest: {
      analysisIntro: `You organize personal knowledge maps. Analyze nodes by life area.

Rules:
- Suggest meaningful relations (supports/conflicts/causes)
- Suggest category fixes (family/work/finance/learning/health/self)
- Exploratory tone, no diagnosis
- Reply in English`,
      export: `Export MAP analysis as JSON:

{
  "summary": "2-3 sentences",
  "relations": [{ "sourceType": "Belief", "sourceLabel": "...", "targetType": "Value", "targetLabel": "...", "relationType": "conflicts|supports|causes|related" }],
  "nodeUpdates": [{ "type": "Belief", "label": "...", "category": "family", "note": "short note" }],
  "treeInsights": [{ "treeId": "family", "theme": "theme", "observation": "note" }]
}`,
    },
    timeline: {
      analysisIntro: `You narrate cognitive development over time. Analyze timeline and dated entries.

Rules:
- Turning points, value/belief shifts, development arc
- No rigid fortune-telling
- Reflective questions only
- Reply in English`,
      export: `Export TIMELINE analysis as JSON:

{
  "narrativeArc": "3-5 sentence story",
  "milestones": [{ "title": "...", "description": "...", "period": "2024 or 2024-Q2", "type": "shift|insight|turning_point" }],
  "valueShifts": [{ "from": "...", "to": "...", "note": "...", "period": "..." }],
  "reflectionPrompt": "one reflective question about the journey"
}`,
    },
  },
};

const AiAssistScreens = {
  SCREENS: ['insights', 'forest', 'timeline'],

  locale() {
    return typeof I18n !== 'undefined' && I18n.locale === 'en' ? 'en' : 'vi';
  },

  pack(nodes, limit = 40) {
    return nodes.slice(0, limit).map((n) => ({
      type: n.type,
      label: n.label,
      category: n.category,
      status: n.status,
      occurrences: n.occurrences,
    }));
  },

  buildContext(screenId) {
    const nodes = DataStore.getNodes();
    const sessions = DataStore.getSessions();
    const relations = DataStore.getRelations();
    const timeline = DataStore.getTimeline();

    const base = {
      generatedAt: new Date().toISOString(),
      nodeCount: nodes.length,
      sessionCount: sessions.length,
    };

    if (screenId === 'insights') {
      const ruleContradictions =
        typeof ContradictionEngine !== 'undefined' ? ContradictionEngine.analyze() : [];
      return {
        ...base,
        nodesByType: Object.fromEntries(
          CognitiveLibrary.REFLECTION_FLOW.map((t) => [
            t,
            nodes.filter((n) => n.type === t).map((n) => n.label).slice(0, 15),
          ])
        ),
        topBeliefs: nodes
          .filter((n) => n.type === 'Belief')
          .sort((a, b) => (b.occurrences || 0) - (a.occurrences || 0))
          .slice(0, 8)
          .map((n) => n.label),
        topValues: nodes
          .filter((n) => n.type === 'Value')
          .sort((a, b) => (b.occurrences || 0) - (a.occurrences || 0))
          .slice(0, 8)
          .map((n) => n.label),
        ruleContradictions: ruleContradictions.slice(0, 8).map((c) => c.message),
        recentSessions: sessions.slice(-5).map((s) => ({
          date: s.createdAt,
          thought: (s.initialThought || '').slice(0, 120),
          source: s.source || 'app',
        })),
      };
    }

    if (screenId === 'forest') {
      const byTree = {};
      for (const tree of CognitiveLibrary.FOREST_TREES) {
        byTree[tree.id] = this.pack(
          nodes.filter((n) => n.category === tree.id),
          20
        );
      }
      return {
        ...base,
        trees: byTree,
        relationCount: relations.length,
        existingRelations: relations.slice(-12).map((r) => {
          const sn = nodes.find((n) => n.id === r.source);
          const tn = nodes.find((n) => n.id === r.target);
          return {
            type: r.type,
            source: sn ? `${sn.type}:${sn.label}` : r.source,
            target: tn ? `${tn.type}:${tn.label}` : r.target,
          };
        }),
      };
    }

    if (screenId === 'timeline') {
      const narrative =
        typeof TimelineEngine !== 'undefined' ? TimelineEngine.buildCognitiveNarrative() : [];
      return {
        ...base,
        timelineEvents: timeline.slice(-15).map((e) => ({
          type: e.type,
          title: e.title,
          description: (e.description || '').slice(0, 100),
          when: e.timestamp,
        })),
        narrativeByYear: narrative.map((entry) => ({
          year: entry.year,
          value: entry.value?.label,
          belief: entry.belief?.label,
          transition: entry.transition,
        })),
        datedNodes: nodes
          .filter((n) => ['Value', 'Belief', 'Identity'].includes(n.type))
          .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt))
          .slice(-25)
          .map((n) => ({
            type: n.type,
            label: n.label,
            at: n.createdAt,
          })),
      };
    }

    return base;
  },

  getAnalysisPrompt(screenId) {
    const loc = this.locale();
    const intro = AI_SCREEN_PROMPTS[loc][screenId]?.analysisIntro || '';
    const context = this.buildContext(screenId);
    const ctxJson = JSON.stringify(context, null, 2);
    const discuss =
      loc === 'en'
        ? 'Discuss your findings with me, then wait for my export prompt.'
        : 'Trao đổi phân tích với tôi, sau đó chờ prompt xuất JSON.';
    return `${intro}\n\n--- DỮ LIỆU APP / APP DATA ---\n${ctxJson}\n\n---\n${discuss}`;
  },

  getExportPrompt(screenId) {
    return AI_SCREEN_PROMPTS[this.locale()][screenId]?.export || '';
  },

  parseImport(screenId, text) {
    const json = typeof AiAssist !== 'undefined' ? AiAssist.extractJsonBlock(text) : null;
    if (!json) return { ok: false, error: 'invalid_json' };
    const normalized = this.normalizePayload(screenId, json);
    if (!normalized) return { ok: false, error: 'invalid_payload' };
    return { ok: true, payload: normalized };
  },

  normalizePayload(screenId, data) {
    if (!data || typeof data !== 'object') return null;

    if (screenId === 'insights') {
      return {
        summary: String(data.summary || '').trim(),
        contradictions: (data.contradictions || [])
          .filter((c) => c?.message)
          .slice(0, 6)
          .map((c) => ({
            message: String(c.message).trim(),
            severity: c.severity === 'high' ? 'high' : 'medium',
          })),
        explorationPrompts: (data.explorationPrompts || [])
          .filter((p) => p?.prompt)
          .slice(0, 5)
          .map((p) => ({
            source: String(p.source || 'ChatGPT').trim(),
            prompt: String(p.prompt).trim(),
            seedThought: String(p.seedThought || p.prompt).trim(),
          })),
        biases: (data.biases || [])
          .filter((b) => b?.label)
          .slice(0, 4)
          .map((b) => ({
            label: String(b.label).trim(),
            description: String(b.description || '').trim(),
          })),
        patterns: (data.patterns || [])
          .filter((p) => p?.label)
          .slice(0, 5)
          .map((p) => ({
            label: String(p.label).trim(),
            detail: String(p.detail || '').trim(),
          })),
      };
    }

    if (screenId === 'forest') {
      const validTrees = new Set(CognitiveLibrary.FOREST_TREES.map((t) => t.id));
      const validTypes = new Set(CognitiveLibrary.REFLECTION_FLOW);
      return {
        summary: String(data.summary || '').trim(),
        relations: (data.relations || [])
          .filter((r) => r?.sourceLabel && r?.targetLabel)
          .slice(0, 10)
          .map((r) => ({
            sourceType: validTypes.has(r.sourceType) ? r.sourceType : 'Belief',
            sourceLabel: String(r.sourceLabel).trim(),
            targetType: validTypes.has(r.targetType) ? r.targetType : 'Value',
            targetLabel: String(r.targetLabel).trim(),
            relationType: ['conflicts', 'supports', 'causes', 'related'].includes(r.relationType)
              ? r.relationType
              : 'related',
          })),
        nodeUpdates: (data.nodeUpdates || [])
          .filter((n) => n?.label && validTypes.has(n.type))
          .slice(0, 8)
          .map((n) => ({
            type: n.type,
            label: String(n.label).trim(),
            category: validTrees.has(n.category) ? n.category : null,
            note: String(n.note || '').trim(),
          })),
        treeInsights: (data.treeInsights || [])
          .filter((t) => t?.treeId && validTrees.has(t.treeId))
          .slice(0, 6)
          .map((t) => ({
            treeId: t.treeId,
            theme: String(t.theme || '').trim(),
            observation: String(t.observation || '').trim(),
          })),
      };
    }

    if (screenId === 'timeline') {
      return {
        narrativeArc: String(data.narrativeArc || '').trim(),
        reflectionPrompt: String(data.reflectionPrompt || '').trim(),
        milestones: (data.milestones || [])
          .filter((m) => m?.title)
          .slice(0, 8)
          .map((m) => ({
            title: String(m.title).trim(),
            description: String(m.description || '').trim(),
            period: String(m.period || '').trim(),
            type: m.type || 'insight',
          })),
        valueShifts: (data.valueShifts || [])
          .filter((v) => v?.from && v?.to)
          .slice(0, 5)
          .map((v) => ({
            from: String(v.from).trim(),
            to: String(v.to).trim(),
            note: String(v.note || '').trim(),
            period: String(v.period || '').trim(),
          })),
      };
    }

    return null;
  },

  buildPreview(screenId, text) {
    const parsed = this.parseImport(screenId, text);
    if (!parsed.ok) return parsed;
    return { ok: true, payload: parsed.payload, rows: this.previewRows(screenId, parsed.payload) };
  },

  previewRows(screenId, payload) {
    if (screenId === 'insights') {
      return [
        { label: 'summary', items: payload.summary ? [payload.summary] : [] },
        { label: 'contradictions', items: payload.contradictions.map((c) => c.message) },
        { label: 'exploration', items: payload.explorationPrompts.map((p) => p.prompt) },
        { label: 'biases', items: payload.biases.map((b) => b.label) },
        { label: 'patterns', items: payload.patterns.map((p) => p.label) },
      ];
    }
    if (screenId === 'forest') {
      return [
        { label: 'summary', items: payload.summary ? [payload.summary] : [] },
        {
          label: 'relations',
          items: payload.relations.map(
            (r) => `${r.sourceType}:${r.sourceLabel} → ${r.targetType}:${r.targetLabel} (${r.relationType})`
          ),
        },
        {
          label: 'nodeUpdates',
          items: payload.nodeUpdates.map((n) => `${n.type}: ${n.label}${n.category ? ` [${n.category}]` : ''}`),
        },
        { label: 'treeInsights', items: payload.treeInsights.map((t) => `${t.treeId}: ${t.theme}`) },
      ];
    }
    return [
      { label: 'narrative', items: payload.narrativeArc ? [payload.narrativeArc] : [] },
      { label: 'milestones', items: payload.milestones.map((m) => m.title) },
      { label: 'valueShifts', items: payload.valueShifts.map((v) => `${v.from} → ${v.to}`) },
      { label: 'reflection', items: payload.reflectionPrompt ? [payload.reflectionPrompt] : [] },
    ];
  },

  findNode(type, label) {
    const nodes = DataStore.getNodes().filter((n) => n.type === type);
    const key = (label || '').toLowerCase().trim();
    let hit = nodes.find((n) => n.label.toLowerCase().trim() === key);
    if (hit) return hit;
    hit = nodes.find(
      (n) => n.label.toLowerCase().includes(key) || key.includes(n.label.toLowerCase())
    );
    return hit || null;
  },

  importPayload(screenId, payload) {
    const data = this.normalizePayload(screenId, payload);
    if (!data) return { ok: false, error: 'invalid_payload' };

    if (screenId === 'insights') {
      DataStore.setAiOverlay('insights', data);
      const insights = InsightEngine.analyze();
      DataStore.setInsights(insights);
      return { ok: true, insights };
    }

    if (screenId === 'forest') {
      const applied = { relations: 0, updates: 0, missed: [] };

      for (const rel of data.relations) {
        const source = this.findNode(rel.sourceType, rel.sourceLabel);
        const target = this.findNode(rel.targetType, rel.targetLabel);
        if (source && target) {
          CognitiveTree.linkNodes(source.id, target.id, rel.relationType);
          applied.relations += 1;
        } else {
          applied.missed.push(`${rel.sourceLabel} → ${rel.targetLabel}`);
        }
      }

      for (const upd of data.nodeUpdates) {
        const node = this.findNode(upd.type, upd.label);
        if (!node) {
          applied.missed.push(upd.label);
          continue;
        }
        const patch = {};
        if (upd.category) patch.category = upd.category;
        if (upd.note) patch.aiNote = upd.note;
        DataStore.updateNode(node.id, patch);
        applied.updates += 1;
      }

      DataStore.setAiOverlay('forest', { ...data, applied });
      return { ok: true, applied };
    }

    if (screenId === 'timeline') {
      const applied = { milestones: 0, shifts: 0 };

      for (const m of data.milestones) {
        const yearMatch = (m.period || '').match(/\d{4}/);
        const year = yearMatch ? Number(yearMatch[0]) : new Date().getFullYear();
        DataStore.addTimelineEvent({
          id: generateId('tl'),
          type: 'ai_milestone',
          title: m.title,
          description: m.description || m.period,
          timestamp: new Date().toISOString(),
          year,
          month: new Date().getMonth() + 1,
          source: 'ai',
          milestoneType: m.type,
        });
        applied.milestones += 1;
      }

      for (const vs of data.valueShifts) {
        TimelineEngine.recordValueShift(vs.from, vs.to);
        applied.shifts += 1;
      }

      DataStore.setAiOverlay('timeline', { ...data, applied });
      return { ok: true, applied };
    }

    return { ok: false, error: 'unknown_screen' };
  },

  importFromText(screenId, text) {
    const parsed = this.parseImport(screenId, text);
    if (!parsed.ok) return parsed;
    return this.importPayload(screenId, parsed.payload);
  },
};

if (typeof window !== 'undefined') {
  window.AiAssistScreens = AiAssistScreens;
}
