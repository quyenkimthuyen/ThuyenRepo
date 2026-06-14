/**
 * CursorDirectTestRunner — Kiểm thử mode Cursor trực tiếp
 *
 * Mock: mô phỏng bridge + luồng finish (export → import + transcript)
 * Live: HTTP tới bridge thật (CLI --live)
 */

const CursorDirectTestRunner = {
  getScenarios(options = {}) {
    const all =
      typeof CURSOR_DIRECT_TEST_SCENARIOS !== 'undefined' ? CURSOR_DIRECT_TEST_SCENARIOS : [];
    if (options.liveOnly) return all.filter((s) => s.liveOnly);
    if (options.mockOnly !== false && !options.includeLive) {
      return all.filter((s) => !s.liveOnly);
    }
    return all;
  },

  getScenario(id) {
    return this.getScenarios({ includeLive: true }).find((s) => s.id === id) || null;
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

  buildMockMessages(scenario) {
    const messages = [
      {
        id: generateId('msg'),
        role: 'user',
        content: scenario.initialThought,
        flowStep: 'Event',
        timestamp: new Date().toISOString(),
      },
      {
        id: generateId('msg'),
        role: 'guide',
        content: scenario.openingReply || '...',
        flowStep: 'Emotion',
        timestamp: new Date().toISOString(),
      },
    ];

    for (const turn of scenario.userDialogue || []) {
      messages.push({
        id: generateId('msg'),
        role: 'user',
        content: turn.content,
        flowStep: turn.step,
        timestamp: new Date().toISOString(),
      });
      messages.push({
        id: generateId('msg'),
        role: 'guide',
        content: `(mock reply sau ${turn.step})`,
        flowStep: turn.step,
        timestamp: new Date().toISOString(),
      });
    }

    return messages;
  },

  simulateCursorSession(scenario) {
    const messages = this.buildMockMessages(scenario);
    const session = {
      id: generateId('session'),
      initialThought: scenario.initialThought,
      messages,
      flowStep: CursorDirect.inferFlowStep({ messages }),
      nodeIds: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'active',
      source: 'cursor_direct',
      cursorBridgeKey: 'mock_cs_test',
    };
    return session;
  },

  purgeCursorSessionArtifacts(sessionId) {
    if (!sessionId || typeof DataStore.removeNodesBySession !== 'function') return;
    DataStore.removeNodesBySession(sessionId);
    if (typeof DataStore.removeTimelineForSession === 'function') {
      DataStore.removeTimelineForSession(sessionId);
    }
  },

  /**
   * Mô phỏng App: sync node/timeline/insights sau mỗi tin user trong phiên cursor_direct
   */
  replayCursorLiveSync(session) {
    if (!session || typeof CursorDirect.syncSessionData !== 'function') return session;

    session.nodeIds = [];
    let flowStep = 'Emotion';
    let guideCount = 0;
    const replayed = [];

    for (const msg of session.messages || []) {
      replayed.push(msg);
      if (msg.role === 'user') {
        const partial = {
          ...session,
          messages: [...replayed],
          flowStep,
          nodeIds: [...(session.nodeIds || [])],
        };
        CursorDirect.syncSessionData(partial, msg.content);
        session.nodeIds = partial.nodeIds;
      } else if (msg.role === 'guide') {
        guideCount += 1;
        // Opening guide (sau tin user đầu) không đổi flowStep — khớp startCursorReflection
        if (guideCount > 1) {
          flowStep = CursorDirect.inferFlowStep({ messages: replayed });
        }
      }
    }

    session.flowStep = flowStep;
    DataStore.updateSession(session.id, { nodeIds: session.nodeIds, flowStep: session.flowStep });
    return session;
  },

  getSessionNodes(session) {
    const byIds = (session.nodeIds || [])
      .map((id) => DataStore.getNodes().find((n) => n.id === id))
      .filter(Boolean);
    if (byIds.length > 0) return byIds;
    return typeof DataStore.getNodesBySession === 'function'
      ? DataStore.getNodesBySession(session.id)
      : DataStore.getNodes().filter((n) => n.sourceSessionId === session.id);
  },

  assertDuringChatSync(scenario, session, failures, steps) {
    const spec = scenario.expectDuringChat;
    if (!spec) return;

    const sessionNodes = this.getSessionNodes(session);
    const nodeMinOk = !spec.sessionNodeMin || sessionNodes.length >= spec.sessionNodeMin;
    steps.push({
      id: 'during_chat_session_nodes',
      ok: nodeMinOk,
      detail: `${sessionNodes.length} node(s) gắn phiên`,
    });
    this.fail(failures, nodeMinOk, 'during_chat_session_nodes', `cần >= ${spec.sessionNodeMin}`);

    for (const nodeSpec of spec.nodesPresent || []) {
      const matched = this.findNodesMatching(sessionNodes, nodeSpec);
      const ok = matched.length > 0;
      steps.push({
        id: `during_chat_present_${nodeSpec.type}_${nodeSpec.labelContains || nodeSpec.quoteContains || 'any'}`,
        ok,
        detail: ok ? matched[0].label : 'Không tìm thấy trong phiên',
      });
      this.fail(
        failures,
        ok,
        'during_chat_nodes_present',
        `${nodeSpec.type}: ${nodeSpec.labelContains || nodeSpec.quoteContains || '?'}`
      );
    }

    const timeline = DataStore.getTimeline();
    if (spec.timelineSessionStart) {
      const hasStart = timeline.some(
        (e) => e.type === 'session_start' && e.sessionId === session.id
      );
      steps.push({
        id: 'during_chat_timeline_session_start',
        ok: hasStart,
        detail: hasStart ? 'Có session_start' : 'Thiếu session_start',
      });
      this.fail(failures, hasStart, 'during_chat_timeline_session_start');
    }

    if (spec.timelineMinCount) {
      const tlOk = timeline.length >= spec.timelineMinCount;
      steps.push({
        id: 'during_chat_timeline_min',
        ok: tlOk,
        detail: `${timeline.length} sự kiện timeline`,
      });
      this.fail(failures, tlOk, 'during_chat_timeline_min', `cần >= ${spec.timelineMinCount}`);
    }

    const insights = DataStore.load().insights || {};
    if (spec.insightsUpdated) {
      const updatedOk = Boolean(insights.lastUpdated);
      steps.push({
        id: 'during_chat_insights_updated',
        ok: updatedOk,
        detail: updatedOk ? insights.lastUpdated : 'insights chưa cập nhật',
      });
      this.fail(failures, updatedOk, 'during_chat_insights_updated');
    }

    if (spec.todayDiscoveriesMin) {
      const discoveries = InsightEngine.analyze().todayDiscoveries || [];
      const discOk = discoveries.length >= spec.todayDiscoveriesMin;
      steps.push({
        id: 'during_chat_today_discoveries',
        ok: discOk,
        detail: `${discoveries.length} khám phá hôm nay`,
      });
      this.fail(
        failures,
        discOk,
        'during_chat_today_discoveries',
        `cần >= ${spec.todayDiscoveriesMin}`
      );
    }

    if (spec.topEmotionsContains) {
      const topEmotions = InsightEngine.analyze().topEmotions || [];
      const emoOk = topEmotions.some((e) => this.containsText(e.label, spec.topEmotionsContains));
      steps.push({
        id: 'during_chat_top_emotions',
        ok: emoOk,
        detail: emoOk ? topEmotions[0]?.label : 'Không có emotion khớp',
      });
      this.fail(failures, emoOk, 'during_chat_top_emotions', spec.topEmotionsContains);
    }
  },

  assertAfterFinishCleanup(oldSessionId, failures, steps) {
    const orphanNodes =
      typeof DataStore.getNodesBySession === 'function'
        ? DataStore.getNodesBySession(oldSessionId)
        : DataStore.getNodes().filter((n) => n.sourceSessionId === oldSessionId);
    const ok = orphanNodes.length === 0;
    steps.push({
      id: 'finish_no_orphan_nodes',
      ok,
      detail: ok ? 'Không còn node phiên cursor cũ' : orphanNodes.map((n) => n.label).join(', '),
    });
    this.fail(failures, ok, 'finish_no_orphan_nodes');
  },

  assertImportOutcome(scenario, importResult, failures, steps) {
    const nodes = DataStore.getNodes();

    steps.push({
      id: 'import_session',
      ok: importResult.ok === true,
      detail: importResult.ok ? `Session ${importResult.session?.id}` : importResult.error,
    });
    this.fail(failures, importResult.ok, 'import_session', importResult.error);

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

    for (const forbidden of scenario.expectAbsent || []) {
      const hit = nodes.find((n) => this.containsText(n.label, forbidden));
      const ok = !hit;
      steps.push({
        id: `absent_${forbidden.slice(0, 24)}`,
        ok,
        detail: hit ? `Xuất hiện: ${hit.label}` : 'Không có',
      });
      this.fail(failures, ok, 'expect_absent', forbidden);
    }

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
    this.fail(failures, noRuleOk, 'no_rule_match');

    for (const label of scenario.expectUnanchored || []) {
      const node = nodes.find((n) => this.containsText(n.label, label));
      const inferredOk = node && node.evidenceType === 'inferred';
      steps.push({
        id: `unanchored_inferred_${label.slice(0, 20)}`,
        ok: inferredOk,
        detail: node ? node.evidenceType : 'không có node',
      });
      this.fail(failures, inferredOk, 'expect_unanchored_inferred', label);
    }

    for (const label of scenario.expectNotInInsights || []) {
      const inTop = InsightEngine.analyzeRules().topBeliefs.some((b) =>
        this.containsText(b.label, label)
      );
      const ok = !inTop;
      steps.push({
        id: `not_in_insights_${label.slice(0, 20)}`,
        ok,
        detail: ok ? 'Không trong topBeliefs' : 'Lọt vào topBeliefs',
      });
      this.fail(failures, ok, 'expect_not_in_insights', label);
    }

    return { nodes, frameworkNodes };
  },

  runOneMock(scenarioId, options = {}) {
    const scenario = this.getScenario(scenarioId);
    if (!scenario) {
      return { ok: false, scenarioId, error: 'scenario_not_found', failures: [], steps: [] };
    }
    if (scenario.liveOnly) {
      return { ok: false, scenarioId, error: 'live_only_scenario', failures: [], steps: [] };
    }

    if (typeof CursorDirect === 'undefined' || typeof AiAssist === 'undefined') {
      return { ok: false, scenarioId, error: 'cursor_direct_missing', failures: [], steps: [] };
    }

    const failures = [];
    const steps = [];
    const backup = options.backup !== false;

    if (backup && typeof TestMode !== 'undefined' && TestMode.snapshot) {
      TestMode.snapshot();
    }

    DataStore.reset();
    this.setLocale(scenario.locale || 'vi');

    const reflectionPrompt = AiAssist.getReflectionPrompt(scenario.initialThought);
    const reflectionOk =
      this.containsText(reflectionPrompt, scenario.initialThought) &&
      (scenario.expectPrompt?.reflectionContains || []).every((frag) =>
        this.containsText(reflectionPrompt, frag)
      );
    steps.push({
      id: 'prompt_reflection',
      ok: reflectionOk,
      detail: reflectionOk ? 'Prompt reflection đúng' : 'Prompt thiếu nội dung',
    });
    this.fail(failures, reflectionOk, 'prompt_reflection');

    const exportPrompt = AiAssist.getExportPrompt();
    const exportPromptOk = (scenario.expectPrompt?.exportContains || ['JSON']).every((frag) =>
      this.containsText(exportPrompt, frag)
    );
    steps.push({
      id: 'prompt_export',
      ok: exportPromptOk,
      detail: exportPromptOk ? 'Prompt export đúng' : 'Prompt export thiếu',
    });
    this.fail(failures, exportPromptOk, 'prompt_export');

    const mockSession = this.simulateCursorSession(scenario);
    DataStore.addSession(mockSession);

    if (scenario.testLiveSync || scenario.expectDuringChat) {
      this.replayCursorLiveSync(mockSession);
      this.assertDuringChatSync(scenario, mockSession, failures, steps);
    }

    const transcript = CursorDirect.buildTranscript(mockSession.messages);
    const transcriptOk = this.containsText(transcript, scenario.initialThought);
    steps.push({
      id: 'transcript_build',
      ok: transcriptOk,
      detail: transcriptOk ? 'Transcript chứa lời user' : 'Transcript thiếu',
    });
    this.fail(failures, transcriptOk, 'transcript_build');

    const flowOk = mockSession.flowStep === CursorDirect.inferFlowStep(mockSession);
    steps.push({
      id: 'flow_step_infer',
      ok: flowOk,
      detail: `flowStep=${mockSession.flowStep}`,
    });
    this.fail(failures, flowOk, 'flow_step_infer');

    const exportData = scenario.cursorExport;
    if (!exportData) {
      this.fail(failures, false, 'missing_cursor_export');
      return { ok: false, scenarioId, title: scenario.title, failures, steps };
    }

    const preview = AiAssist.buildImportPreview(JSON.stringify(exportData, null, 2), {
      transcript,
    });
    steps.push({
      id: 'import_preview',
      ok: preview.ok === true,
      detail: preview.ok ? `anchored: ${preview.stats?.anchoredCount ?? '?'}` : preview.error,
    });
    this.fail(failures, preview.ok, 'import_preview', preview.error);

    const oldSessionId = mockSession.id;
    this.purgeCursorSessionArtifacts(oldSessionId);
    DataStore.removeSession(oldSessionId);
    const importResult = AiAssist.importSession(exportData, { transcript });
    this.assertImportOutcome(scenario, importResult, failures, steps);

    if (scenario.expectAfterFinish?.noOrphanSessionNodes) {
      this.assertAfterFinishCleanup(oldSessionId, failures, steps);
    }

    const ok = failures.length === 0;
    return {
      ok,
      scenarioId: scenario.id,
      title: scenario.title,
      mode: 'mock',
      failures,
      steps,
    };
  },

  runOne(scenarioId, options = {}) {
    return this.runOneMock(scenarioId, options);
  },

  runAll(options = {}) {
    const scenarios = this.getScenarios({ mockOnly: true, includeLive: false });
    const results = scenarios.map((s) => this.runOneMock(s.id, { ...options, backup: false }));
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
  window.CursorDirectTestRunner = CursorDirectTestRunner;
}
