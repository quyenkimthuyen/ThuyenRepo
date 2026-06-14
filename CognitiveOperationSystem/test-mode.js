/**
 * Test Mode — Mô phỏng và kiểm thử app bằng kịch bản mẫu
 *
 * Mở rộng: thêm scenario trong test-scenarios.js, UI tự liệt kê.
 */

const TestMode = {
  selectedScenarioId: null,
  selectedAiAssistScenarioId: null,
  simulationAbort: false,
  lastSnapshot: null,
  isSimulating: false,
  /** @type {Record<string, Array<{step: string, content: string, note?: string}>>} */
  dialogueEdits: {},

  getScenarios() {
    return typeof TEST_SCENARIOS !== 'undefined' ? TEST_SCENARIOS : [];
  },

  getScenario(id) {
    return this.getScenarios().find((s) => s.id === id) || null;
  },

  getCategoryLabel(category) {
    if (typeof I18n !== 'undefined') return I18n.forestLabel(category);
    const tree = CognitiveLibrary.FOREST_TREES.find((t) => t.id === category);
    return tree ? tree.label : category;
  },

  selectScenario(id) {
    this.selectedScenarioId = id;
    this.selectedAiAssistScenarioId = null;
    return this.getScenario(id);
  },

  getAiAssistScenarios() {
    return typeof AiAssistTestRunner !== 'undefined'
      ? AiAssistTestRunner.getScenarios()
      : [];
  },

  selectAiAssistScenario(id) {
    this.selectedAiAssistScenarioId = id;
    this.selectedScenarioId = null;
    return typeof AiAssistTestRunner !== 'undefined'
      ? AiAssistTestRunner.getScenario(id)
      : null;
  },

  /** Hội thoại đang dùng (bản gốc hoặc đã chỉnh sửa) */
  getEffectiveDialogue(scenarioId) {
    if (this.dialogueEdits[scenarioId]) {
      return this.dialogueEdits[scenarioId];
    }
    const scenario = this.getScenario(scenarioId);
    return scenario ? scenario.dialogue.map((turn) => ({ ...turn })) : [];
  },

  hasDialogueEdits(scenarioId) {
    const scenario = this.getScenario(scenarioId);
    if (!scenario || !this.dialogueEdits[scenarioId]) return false;
    return this.dialogueEdits[scenarioId].some(
      (turn, i) => turn.content !== scenario.dialogue[i]?.content
    );
  },

  /** Lưu chỉnh sửa từ mảng hội thoại */
  setDialogueEdits(scenarioId, dialogue) {
    const scenario = this.getScenario(scenarioId);
    if (!scenario) return;

    const changed = dialogue.some((turn, i) => turn.content !== scenario.dialogue[i]?.content);
    if (changed) {
      this.dialogueEdits[scenarioId] = dialogue.map((turn) => ({ ...turn }));
    } else {
      delete this.dialogueEdits[scenarioId];
    }
  },

  resetDialogueEdits(scenarioId) {
    delete this.dialogueEdits[scenarioId];
  },

  /** Điền suy nghĩ ban đầu vào Home */
  applyToHome(scenarioId) {
    const scenario = this.getScenario(scenarioId);
    if (!scenario) return null;

    const input = document.getElementById('home-thought-input');
    if (input) input.value = scenario.initialThought;
    return scenario;
  },

  /** Sao lưu state hiện tại trước khi mô phỏng */
  snapshot() {
    this.lastSnapshot = JSON.parse(DataStore.exportData());
    return this.lastSnapshot;
  },

  /** Khôi phục state trước mô phỏng */
  restoreSnapshot() {
    if (!this.lastSnapshot) return false;
    DataStore.replaceState(this.lastSnapshot);
    this.lastSnapshot = null;
    return true;
  },

  hasSnapshot() {
    return !!this.lastSnapshot;
  },

  stopSimulation() {
    this.simulationAbort = true;
  },

  delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  },

  /**
   * Chạy mô phỏng đầy đủ một kịch bản
   * @param {string} scenarioId
   * @param {{ reset?: boolean, delayMs?: number, backup?: boolean }} options
   */
  async runSimulation(scenarioId, options = {}) {
    const { reset = true, delayMs = 500, backup = true } = options;
    const scenario = this.getScenario(scenarioId);

    if (!scenario) {
      throw new Error(`Không tìm thấy kịch bản: ${scenarioId}`);
    }

    if (this.isSimulating) {
      throw new Error('Đang có mô phỏng khác chạy');
    }

    this.isSimulating = true;
    this.simulationAbort = false;

    if (backup) {
      this.snapshot();
    }

    if (reset) {
      DataStore.reset();
    }

    const dialogue = options.dialogue || this.getEffectiveDialogue(scenarioId);
    const { session } = ReflectionEngine.createSession(scenario.initialThought);
    const progress = {
      scenarioId,
      sessionId: session.id,
      totalSteps: dialogue.length,
      completedSteps: 0,
      steps: [],
      usedEditedDialogue: this.hasDialogueEdits(scenarioId),
    };

    for (const turn of dialogue) {
      if (this.simulationAbort) {
        progress.aborted = true;
        break;
      }

      if (delayMs > 0) {
        await this.delay(delayMs);
      }

      const result = ReflectionEngine.continueSession(session.id, turn.content);
      progress.completedSteps += 1;
      progress.steps.push({
        step: turn.step,
        content: turn.content,
        flowStep: result?.result?.flowStep,
      });

      if (typeof options.onProgress === 'function') {
        options.onProgress({ ...progress, currentTurn: turn });
      }
    }

    const insights = InsightEngine.analyze();
    DataStore.setInsights(insights);

    const finalSession = DataStore.getSession(session.id);
    progress.session = finalSession;
    progress.insights = insights;
    progress.stats = CognitiveTree.getStats();
    progress.aborted = progress.aborted || false;

    this.isSimulating = false;
    return progress;
  },
};

if (typeof window !== 'undefined') {
  window.TestMode = TestMode;
}
