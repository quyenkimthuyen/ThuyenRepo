/**
 * Test Mode — Mô phỏng và kiểm thử app bằng kịch bản mẫu
 *
 * Mở rộng: thêm scenario trong test-scenarios.js, UI tự liệt kê.
 */

const TestMode = {
  selectedScenarioId: null,
  simulationAbort: false,
  lastSnapshot: null,
  isSimulating: false,

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
    return this.getScenario(id);
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

    const { session } = await ReflectionEngine.createSession(scenario.initialThought, {
      forceRule: true,
    });
    const progress = {
      scenarioId,
      sessionId: session.id,
      totalSteps: scenario.dialogue.length,
      completedSteps: 0,
      steps: [],
    };

    for (const turn of scenario.dialogue) {
      if (this.simulationAbort) {
        progress.aborted = true;
        break;
      }

      if (delayMs > 0) {
        await this.delay(delayMs);
      }

      const result = await ReflectionEngine.continueSession(session.id, turn.content, {
        forceRule: true,
      });
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
