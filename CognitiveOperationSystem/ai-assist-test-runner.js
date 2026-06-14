/**
 * AiAssistTestRunner — Kiểm thử hồi quy luồng ChatGPT gián tiếp
 *
 * Mô phỏng: User → prompt app → ChatGPT JSON → import → kiểm tra node/bằng chứng
 */

const AiAssistTestRunner = {
  getScenarios() {
    return typeof AI_ASSIST_TEST_SCENARIOS !== 'undefined' ? AI_ASSIST_TEST_SCENARIOS : [];
  },

  getScenario(id) {
    return this.getScenarios().find((s) => s.id === id) || null;
  },

  setLocale(locale) {
    const next = locale === 'en' ? 'en' : 'vi';
    if (typeof I18n !== 'undefined') {
      I18n.locale = next;
      if (typeof I18n.applyDocumentLang === 'function') I18n.applyDocumentLang();
    }
    const settings = DataStore.load().settings || {};
    DataStore.save({ settings: { ...settings, locale: next } });
  },

  normalize(text) {
    return (text || '').toLowerCase().trim();
  },

  containsText(haystack, needle) {
    return this.normalize(haystack).includes(this.normalize(needle));
  },

  collectUserCorpus(scenario) {
    const parts = [scenario.initialThought];
    for (const turn of scenario.userDialogue || []) {
      if (turn.content) parts.push(turn.content);
    }
    return parts.join('\n');
  },

  fail(failures, check, message, detail = '') {
    if (!check) failures.push({ check, message, detail });
    return check;
  },

  nodeMatchesSpec(node, spec) {
    if (spec.type && node.type !== spec.type) return false;
    if (spec.labelContains && !this.containsText(node.label, spec.labelContains)) return false;
    const evidence = [...(node.evidence || []), node.sourceText || ''].filter(Boolean);
    if (spec.quoteContains) {
      return evidence.some((e) => this.containsText(e, spec.quoteContains));
    }
    return true;
  },

  findNodesMatching(nodes, spec) {
    return nodes.filter((n) => this.nodeMatchesSpec(n, spec));
  },

  /**
   * Kiểm tra quote trong JSON ChatGPT có bám userDialogue
   */
  validateExportQuotes(scenario) {
    const failures = [];
    const corpus = this.collectUserCorpus(scenario);
    const exportData = scenario.chatgptExport || {};
    const lists = [
      ['emotions', exportData.emotions],
      ['beliefs', exportData.beliefs],
      ['values', exportData.values],
      ['identity', exportData.identity],
      ['actions', exportData.actions],
    ];

    for (const [field, items] of lists) {
      for (const item of items || []) {
        if (!item?.quote) continue;
        const quote = item.quote.trim();
        if (quote.length < 4) continue;
        const snippet = quote.slice(0, Math.min(24, quote.length));
        if (!this.containsText(corpus, snippet)) {
          failures.push({
            check: 'export_quote_alignment',
            message: `ChatGPT JSON.${field} quote không khớp lời user`,
            detail: quote.slice(0, 80),
          });
        }
      }
    }

    if (exportData.interpretation?.quote || exportData.interpretation?.detail) {
      const q = exportData.interpretation.quote || exportData.interpretation.detail;
      const snippet = q.slice(0, Math.min(20, q.length));
      if (!this.containsText(corpus, snippet)) {
        failures.push({
          check: 'export_quote_alignment',
          message: 'ChatGPT interpretation không khớp lời user',
          detail: q.slice(0, 80),
        });
      }
    }

    return failures;
  },

  runOne(scenarioId, options = {}) {
    const scenario = this.getScenario(scenarioId);
    if (!scenario) {
      return { ok: false, scenarioId, error: 'scenario_not_found', failures: [], steps: [] };
    }

    if (typeof AiAssist === 'undefined') {
      return { ok: false, scenarioId, error: 'ai_assist_missing', failures: [], steps: [] };
    }

    const failures = [];
    const steps = [];
    const backup = options.backup !== false;

    if (backup && typeof TestMode !== 'undefined' && TestMode.snapshot) {
      TestMode.snapshot();
    }

    DataStore.reset();
    this.setLocale(scenario.locale || 'vi');

    // ── Bước 1: Prompt reflection ──
    const reflectionPrompt = AiAssist.getReflectionPrompt(scenario.initialThought);
    const reflectionOk =
      this.containsText(reflectionPrompt, scenario.initialThought) &&
      (scenario.expectPrompt?.reflectionContains || []).every((frag) =>
        this.containsText(reflectionPrompt, frag)
      );
    steps.push({
      id: 'prompt_reflection',
      ok: reflectionOk,
      detail: reflectionOk ? 'Prompt chứa suy nghĩ ban đầu và locale đúng' : 'Prompt reflection thiếu nội dung',
    });
    this.fail(failures, reflectionOk, 'prompt_reflection', reflectionPrompt.slice(0, 120));

    // ── Bước 2: Prompt export ──
    const exportPrompt = AiAssist.getExportPrompt();
    const exportPromptOk = (scenario.expectPrompt?.exportContains || ['JSON']).every((frag) =>
      this.containsText(exportPrompt, frag)
    );
    steps.push({
      id: 'prompt_export',
      ok: exportPromptOk,
      detail: exportPromptOk ? 'Prompt export đúng locale/schema' : 'Prompt export thiếu',
    });
    this.fail(failures, exportPromptOk, 'prompt_export');

    // ── Bước 3: JSON ChatGPT khớp user ──
    const quoteFailures = this.validateExportQuotes(scenario);
    failures.push(...quoteFailures);
    steps.push({
      id: 'export_quote_alignment',
      ok: quoteFailures.length === 0,
      detail:
        quoteFailures.length === 0
          ? 'JSON mô phỏng bám lời user'
          : `${quoteFailures.length} quote không khớp`,
    });

    // ── Bước 4: Preview import ──
    const jsonText = JSON.stringify(scenario.chatgptExport, null, 2);
    const preview = AiAssist.buildImportPreview(jsonText);
    const previewOk = preview.ok === true;
    steps.push({
      id: 'import_preview',
      ok: previewOk,
      detail: previewOk ? `AI: ${preview.stats?.aiCount ?? 0}, rule gợi ý: ${preview.stats?.ruleCount ?? 0}` : preview.error,
    });
    this.fail(failures, previewOk, 'import_preview', preview.error || preview.hint);

    if (previewOk && preview.stats?.ruleCount > 0) {
      steps.push({
        id: 'rule_preview_only',
        ok: true,
        detail: `Rule gợi ý ${preview.stats.ruleCount} mục — chỉ preview, không import`,
      });
    }

    // ── Bước 5: Import ──
    let importResult = { ok: false };
    if (previewOk) {
      importResult = AiAssist.importSession(scenario.chatgptExport);
    }
    steps.push({
      id: 'import_session',
      ok: importResult.ok === true,
      detail: importResult.ok ? `Session ${importResult.session?.id}` : importResult.error,
    });
    this.fail(failures, importResult.ok, 'import_session', importResult.error);

    const nodes = DataStore.getNodes();

    // ── Bước 6: Node phải có ──
    for (const spec of scenario.expectPresent || []) {
      const matched = this.findNodesMatching(nodes, spec);
      const ok = matched.length > 0;
      steps.push({
        id: `present_${spec.type}_${spec.labelContains || spec.quoteContains || 'any'}`,
        ok,
        detail: ok ? matched[0].label : 'Không tìm thấy',
      });
      this.fail(
        failures,
        ok,
        'expect_present',
        `${spec.type}: ${spec.labelContains || spec.quoteContains || '?'}`
      );
    }

    // ── Bước 7: Node không được có ──
    for (const forbidden of scenario.expectAbsent || []) {
      const hit = nodes.find((n) => this.containsText(n.label, forbidden));
      const ok = !hit;
      steps.push({
        id: `absent_${forbidden.slice(0, 24)}`,
        ok,
        detail: hit ? `Xuất hiện: ${hit.label} (${hit.evidenceType || '?'})` : 'Không có',
      });
      this.fail(failures, ok, 'expect_absent', forbidden);
    }

    // ── Bước 8: Bằng chứng imported, không rule_match ──
    const frameworkNodes = nodes.filter((n) =>
      ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'].includes(n.type)
    );
    const ruleMatchNodes = frameworkNodes.filter((n) => n.evidenceType === 'rule_match');
    const noRuleOk = ruleMatchNodes.length === 0;
    steps.push({
      id: 'no_rule_match_nodes',
      ok: noRuleOk,
      detail: noRuleOk ? 'Không có node rule_match' : ruleMatchNodes.map((n) => n.label).join(', '),
    });
    this.fail(failures, noRuleOk, 'no_rule_match', ruleMatchNodes.map((n) => n.label).join('; '));

    const importedNodes = frameworkNodes.filter((n) => n.evidenceType === 'imported');
    const importedOk = importedNodes.length >= (scenario.expectPresent?.length ? 2 : 1);
    steps.push({
      id: 'evidence_imported',
      ok: importedOk,
      detail: `${importedNodes.length} node imported / ${frameworkNodes.length} tổng`,
    });
    this.fail(failures, importedOk, 'evidence_imported');

    // ── Bước 9: Insight context chỉ node có bằng chứng ──
    if (typeof AiAssistScreens !== 'undefined' && importResult.ok) {
      const ctx = AiAssistScreens.buildContext('insights');
      const ctxBeliefs = ctx.topBeliefs || [];
      const leaked = (scenario.expectAbsent || []).filter((f) =>
        ctxBeliefs.some((b) => this.containsText(b, f))
      );
      const ctxOk = leaked.length === 0;
      steps.push({
        id: 'insights_context_clean',
        ok: ctxOk,
        detail: ctxOk ? 'Prompt Khám phá không chứa niềm tin cấm' : leaked.join(', '),
      });
      this.fail(failures, ctxOk, 'insights_context', leaked.join('; '));
    }

    const ok = failures.length === 0;
    return {
      ok,
      scenarioId: scenario.id,
      title: scenario.title,
      failures,
      steps,
      stats: {
        nodes: nodes.length,
        beliefs: nodes.filter((n) => n.type === 'Belief').length,
        imported: importedNodes.length,
      },
    };
  },

  runAll(options = {}) {
    const scenarios = this.getScenarios();
    const results = scenarios.map((s) => this.runOne(s.id, { ...options, backup: false }));
    if (options.backup !== false && typeof TestMode !== 'undefined' && TestMode.restoreSnapshot) {
      TestMode.restoreSnapshot();
    }
    const passed = results.filter((r) => r.ok).length;
    return {
      ok: passed === results.length,
      total: results.length,
      passed,
      failed: results.length - passed,
      results,
    };
  },
};

if (typeof window !== 'undefined') {
  window.AiAssistTestRunner = AiAssistTestRunner;
}
