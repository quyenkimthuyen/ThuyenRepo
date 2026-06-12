/**
 * Cognitive OS — Main Application
 *
 * Điều phối 5 màn hình: Home, Reflection, Forest, Insights, Timeline
 * Mở rộng: thay ReflectionEngine bằng API client (OpenAI/Cursor)
 */

const App = {
  currentScreen: 'home',
  activeSessionId: null,
  editingMessageId: null,
  aiImportPreviewPayload: null,
  aiAssistStep: 1,
  aiScreenId: null,
  aiScreenStep: 1,
  aiScreenPreviewPayload: null,
  selectedForestTree: null,
  nodeFilter: 'all',

  /**
   * Khởi tạo ứng dụng
   */
  init() {
    DataStore.load();
    I18n.init();
    this.bindEvents();
    I18n.applyStatic();
    I18n.onChange(() => {
      I18n.applyStatic();
      this.refreshAiAssistPrompts();
      this.renderAiEeibviaTrack();
      this.navigate(this.currentScreen);
    });
    this.renderHomeStats();
    this.navigate('home');
  },

  /**
   * Gắn event listeners
   */
  bindEvents() {
    // Navigation
    document.querySelectorAll('.nav-link').forEach((btn) => {
      btn.addEventListener('click', () => {
        const screen = btn.dataset.screen;
        this.navigate(screen);
      });
    });

    // Home — bắt đầu suy ngẫm
    document.getElementById('btn-start-reflection').addEventListener('click', () => {
      this.startReflection();
    });

    document.getElementById('btn-ai-assist').addEventListener('click', () => {
      this.openAiAssistModal();
    });
    document.getElementById('ai-assist-close').addEventListener('click', () => {
      document.getElementById('ai-assist-modal').close();
    });
    document.querySelectorAll('.ai-copy-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const which = btn.dataset.copyTarget || 'reflection';
        this.copyAiPrompt(which, btn);
      });
    });
    document.getElementById('ai-modal-thought')?.addEventListener('input', (e) => {
      const thought = e.target.value;
      const homeInput = document.getElementById('home-thought-input');
      if (homeInput) homeInput.value = thought;
      this.refreshAiAssistPrompts(thought);
    });
    document.getElementById('btn-ai-step-next-1')?.addEventListener('click', () => {
      this.setAiAssistStep(2);
    });
    document.getElementById('btn-ai-step-back-2')?.addEventListener('click', () => {
      this.setAiAssistStep(1);
    });
    document.getElementById('btn-ai-step-next-2')?.addEventListener('click', () => {
      this.refreshAiAssistPrompts();
      this.setAiAssistStep(3);
    });
    document.getElementById('btn-ai-step-back-3')?.addEventListener('click', () => {
      this.hideAiImportPreview();
      this.setAiAssistStep(2);
    });
    document.querySelectorAll('.ai-stepper-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const step = Number(btn.dataset.aiStep);
        if (step === 3 && !document.getElementById('ai-import-input')?.value.trim()) {
          this.setAiAssistStep(3);
          return;
        }
        if (step <= this.aiAssistStep || step === 1) {
          this.hideAiImportPreview();
          this.setAiAssistStep(step);
        }
      });
    });
    document.getElementById('ai-import-input')?.addEventListener('focus', () => {
      document.getElementById('ai-paste-zone')?.classList.add('focused');
    });
    document.getElementById('ai-import-input')?.addEventListener('blur', () => {
      document.getElementById('ai-paste-zone')?.classList.remove('focused');
    });
    document.getElementById('btn-ai-preview').addEventListener('click', () => {
      this.previewAiImport();
    });
    document.getElementById('btn-ai-preview-back').addEventListener('click', () => {
      this.hideAiImportPreview();
    });
    document.getElementById('btn-ai-import-confirm').addEventListener('click', () => {
      this.confirmAiImport();
    });

    document.querySelectorAll('.ai-screen-trigger').forEach((btn) => {
      btn.addEventListener('click', () => this.openAiScreenAssist(btn.dataset.aiScreen));
    });
    document.getElementById('ai-screen-close')?.addEventListener('click', () => {
      document.getElementById('ai-screen-modal').close();
    });
    document.getElementById('ai-screen-next-1')?.addEventListener('click', () => this.setAiScreenStep(2));
    document.getElementById('ai-screen-back-2')?.addEventListener('click', () => this.setAiScreenStep(1));
    document.getElementById('ai-screen-next-2')?.addEventListener('click', () => this.setAiScreenStep(3));
    document.getElementById('ai-screen-back-3')?.addEventListener('click', () => {
      this.hideAiScreenPreview();
      this.setAiScreenStep(2);
    });
    document.querySelectorAll('[data-screen-copy]').forEach((btn) => {
      btn.addEventListener('click', () => this.copyAiScreenPrompt(btn.dataset.screenCopy, btn));
    });
    document.getElementById('ai-screen-preview')?.addEventListener('click', () => this.previewAiScreenImport());
    document.getElementById('ai-screen-preview-back')?.addEventListener('click', () => this.hideAiScreenPreview());
    document.getElementById('ai-screen-confirm')?.addEventListener('click', () => this.confirmAiScreenImport());
    document.querySelectorAll('.ai-screen-stepper .ai-stepper-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const step = Number(btn.dataset.aiScreenStep);
        if (step <= this.aiScreenStep || step === 1) {
          this.hideAiScreenPreview();
          this.setAiScreenStep(step);
        }
      });
    });
    document.getElementById('ai-screen-import')?.addEventListener('focus', () => {
      document.getElementById('ai-screen-paste-zone')?.classList.add('focused');
    });
    document.getElementById('ai-screen-import')?.addEventListener('blur', () => {
      document.getElementById('ai-screen-paste-zone')?.classList.remove('focused');
    });

    // Reset dữ liệu
    document.getElementById('btn-reset-data').addEventListener('click', () => {
      this.openResetModal();
    });
    document.getElementById('btn-reset-cancel').addEventListener('click', () => {
      document.getElementById('reset-modal').close();
    });
    document.getElementById('reset-modal-close').addEventListener('click', () => {
      document.getElementById('reset-modal').close();
    });
    document.getElementById('btn-reset-confirm').addEventListener('click', () => {
      this.resetAllData();
    });

    document.querySelectorAll('[data-lang]').forEach((btn) => {
      btn.addEventListener('click', () => I18n.setLocale(btn.dataset.lang));
    });

    // Chat form
    document.getElementById('chat-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.sendChatMessage();
    });

    // Forest back
    document.getElementById('forest-back').addEventListener('click', () => {
      this.showForestGrid();
    });

    // Modal close
    document.getElementById('modal-close').addEventListener('click', () => {
      document.getElementById('node-modal').close();
    });

    // Enter to send (Shift+Enter for newline)
    document.getElementById('chat-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendChatMessage();
      }
    });

    // Gợi ý trả lời — chọn mẫu câu
    const onSuggestionPick = (e) => {
      const chip = e.target.closest('.suggestion-chip');
      if (!chip) return;
      const text = chip.dataset.text;
      if (!text) return;
      const input = document.getElementById('chat-input');
      input.value = text;
      input.focus();
      this.sendChatMessage();
    };
    document.getElementById('suggestions-list').addEventListener('click', onSuggestionPick);
    document.getElementById('short-suggestions-list').addEventListener('click', onSuggestionPick);

    document.getElementById('btn-skip-step').addEventListener('click', () => {
      this.skipReflectionStep();
    });

    document.getElementById('chat-messages').addEventListener('click', (e) => {
      const editBtn = e.target.closest('[data-edit-message]');
      if (editBtn) {
        this.startEditMessage(editBtn.dataset.editMessage);
        return;
      }
      const saveBtn = e.target.closest('[data-save-edit]');
      if (saveBtn) {
        this.saveEditMessage(saveBtn.dataset.saveEdit);
        return;
      }
      const cancelBtn = e.target.closest('[data-cancel-edit]');
      if (cancelBtn) {
        this.cancelEditMessage();
      }
    });

    document.getElementById('btn-crisis-understood').addEventListener('click', () => {
      document.getElementById('crisis-modal').close();
    });

    // Test mode — chọn kịch bản & hành động
    document.getElementById('test-scenario-list').addEventListener('click', (e) => {
      const card = e.target.closest('.test-scenario-card');
      if (card) {
        if (TestMode.selectedScenarioId) {
          this.collectTestDialogueEdits(TestMode.selectedScenarioId);
        }
        TestMode.selectScenario(card.dataset.scenarioId);
        this.renderTestMode();
        return;
      }
    });

    document.getElementById('test-scenario-detail').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-test-action]');
      if (!btn) return;
      const action = btn.dataset.testAction;
      const scenarioId = btn.dataset.scenarioId || TestMode.selectedScenarioId;
      if (!scenarioId) return;

      switch (action) {
        case 'apply-home':
          TestMode.applyToHome(scenarioId);
          this.showToast(I18n.t('test.filledHome'));
          this.navigate('home');
          break;
        case 'simulate':
          this.runTestSimulation(scenarioId, { delayMs: 500 });
          break;
        case 'simulate-fast':
          this.runTestSimulation(scenarioId, { delayMs: 0 });
          break;
        case 'simulate-rerun':
          this.runTestSimulation(scenarioId, { reset: false, backup: false, delayMs: 500 });
          break;
        case 'reset-dialogue':
          TestMode.resetDialogueEdits(scenarioId);
          this.renderTestMode();
          this.showToast(I18n.t('test.dialogueRestored'));
          break;
        case 'restore':
          if (TestMode.restoreSnapshot()) {
            this.showToast(I18n.t('test.restored'));
            this.renderHomeStats();
            this.renderTestMode();
          } else {
            this.showToast(I18n.t('test.noBackup'));
          }
          break;
      }
    });

    document.getElementById('btn-stop-simulation').addEventListener('click', () => {
      TestMode.stopSimulation();
    });

    document.getElementById('insights-grid').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-exploration-seed]');
      if (btn) {
        this.applyExplorationSeed(btn.dataset.explorationSeed);
      }
    });
  },

  /**
   * Điều hướng giữa các màn hình
   */
  navigate(screen) {
    this.currentScreen = screen;

    document.querySelectorAll('.screen').forEach((el) => {
      el.classList.remove('active');
      el.hidden = true;
    });

    const target = document.getElementById(`screen-${screen}`);
    if (target) {
      target.classList.add('active');
      target.hidden = false;
    }

    document.querySelectorAll('.nav-link').forEach((btn) => {
      const isActive = btn.dataset.screen === screen;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive);
    });

    // Render màn hình tương ứng
    switch (screen) {
      case 'home':
        this.renderHomeStats();
        break;
      case 'reflection':
        this.renderReflection();
        break;
      case 'forest':
        this.renderForest();
        break;
      case 'insights':
        this.renderInsights();
        break;
      case 'timeline':
        this.renderTimeline();
        break;
      case 'test':
        this.renderTestMode();
        break;
    }
  },

  /**
   * Hiển thị toast
   */
  showToast(message, duration = 3000) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
  },

  // ─── HOME ───

  renderHomeStats() {
    const stats = CognitiveTree.getStats();
    const el = document.getElementById('home-stats');
    const resetEl = document.getElementById('home-reset');
    if (!el) return;

    const hasData =
      stats.total > 0 ||
      DataStore.getSessions().length > 0 ||
      DataStore.getTimeline().length > 0;

    el.innerHTML = `
      <div class="stat-item">
        <div class="stat-value">${stats.total}</div>
        <div class="stat-label">${I18n.t('home.statEntries')}</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${stats.byStatus?.verified || 0}</div>
        <div class="stat-label">${I18n.t('home.statVerified')}</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${DataStore.getSessions().length}</div>
        <div class="stat-label">${I18n.t('home.statSessions')}</div>
      </div>
    `;

    if (resetEl) {
      resetEl.hidden = !hasData;
    }
  },

  openResetModal() {
    document.getElementById('reset-modal').showModal();
  },

  resetAllData() {
    DataStore.reset();

    this.activeSessionId = null;
    this.selectedForestTree = null;
    this.nodeFilter = 'all';

    if (typeof TestMode !== 'undefined') {
      TestMode.lastSnapshot = null;
      TestMode.simulationAbort = false;
      TestMode.isSimulating = false;
      TestMode.dialogueEdits = {};
    }

    const homeInput = document.getElementById('home-thought-input');
    const chatInput = document.getElementById('chat-input');
    if (homeInput) homeInput.value = '';
    if (chatInput) chatInput.value = '';

    document.getElementById('node-modal').close();
    document.getElementById('reset-modal').close();

    this.renderHomeStats();
    this.navigate('home');
    this.showToast(I18n.t('home.dataReset'));
  },

  openAiAssistModal() {
    const input = document.getElementById('home-thought-input');
    const thought = input?.value.trim() || '';
    const modalThought = document.getElementById('ai-modal-thought');
    if (modalThought) modalThought.value = thought;

    this.aiImportPreviewPayload = null;
    this.hideAiImportPreview();
    this.setAiAssistStep(1);
    this.refreshAiAssistPrompts(thought);
    this.renderAiEeibviaTrack();
    document.getElementById('ai-assist-modal').showModal();

    if (!thought) {
      modalThought?.focus();
    }
  },

  formatAiJsonHint(hint) {
    if (!hint || hint === 'empty') return I18n.t('aiAssist.importEmpty');
    if (hint === 'no_object' || hint === 'fenced_no_json') {
      return I18n.locale === 'en' ? 'No JSON object found' : 'Không thấy khối JSON';
    }
    if (hint === 'missing_event') return I18n.t('aiAssist.importMissingEvent');
    if (hint === 'invalid_payload') {
      return I18n.locale === 'en' ? 'JSON shape not supported' : 'Cấu trúc JSON không đúng màn hình';
    }
    return String(hint).slice(0, 140);
  },

  setAiAssistStep(step) {
    this.aiAssistStep = step;
    document.querySelectorAll('.ai-wizard-panel').forEach((panel) => {
      const n = Number(panel.dataset.aiPanel);
      panel.hidden = n !== step;
      panel.classList.toggle('active', n === step);
    });
    document.querySelectorAll('.ai-stepper-btn').forEach((btn) => {
      const n = Number(btn.dataset.aiStep);
      btn.classList.toggle('active', n === step);
      btn.classList.toggle('done', n < step);
    });
    const flowNodes = document.querySelectorAll('.ai-flow-strip .ai-flow-node');
    flowNodes.forEach((node, i) => {
      const active = (step === 1 && i === 0) || (step === 2 && i === 1) || (step === 3 && i === 2);
      node.classList.toggle('active', active);
      node.classList.toggle('done', (step === 2 && i === 0) || (step === 3 && i <= 1));
    });
    if (step === 3) {
      document.getElementById('ai-import-input')?.focus();
    }
  },

  renderAiEeibviaTrack() {
    const track = document.getElementById('ai-eeibvia-track');
    if (!track || typeof CognitiveLibrary === 'undefined') return;
    const steps = CognitiveLibrary.REFLECTION_FLOW || [];
    const icons = {
      Event: '📍',
      Emotion: '💭',
      Interpretation: '🔍',
      Belief: '💡',
      Value: '🌟',
      Identity: '🪞',
      Action: '⚡',
    };
    track.innerHTML = steps
      .map((step) => {
        const label = CognitiveLibrary.getFrameworkLabel(step);
        return `<span class="ai-eeibvia-chip" title="${this.escapeAttr(label)}">${icons[step] || '·'} ${this.escapeHtml(label)}</span>`;
      })
      .join('');
  },

  hideAiImportPreview() {
    const panel = document.getElementById('ai-import-preview');
    const body = document.getElementById('ai-preview-body');
    const statsEl = document.getElementById('ai-preview-stats');
    const warnEl = document.getElementById('ai-preview-warnings');
    if (panel) panel.hidden = true;
    if (body) body.innerHTML = '';
    if (statsEl) {
      statsEl.hidden = true;
      statsEl.textContent = '';
    }
    if (warnEl) {
      warnEl.hidden = true;
      warnEl.innerHTML = '';
    }
    this.aiImportPreviewPayload = null;
    this.aiImportTranscript = '';
  },

  refreshAiAssistPrompts(thoughtOverride) {
    if (typeof AiAssist === 'undefined') return;
    const input = document.getElementById('home-thought-input');
    const thought = thoughtOverride ?? input?.value.trim() ?? '';
    const p1 = document.getElementById('ai-prompt-reflection');
    const p2 = document.getElementById('ai-prompt-export');
    if (p1) p1.value = AiAssist.getReflectionPrompt(thought);
    if (p2) p2.value = AiAssist.getExportPrompt();
  },

  async copyAiPrompt(which, btnEl) {
    if (which === 'reflection') {
      const thought = document.getElementById('ai-modal-thought')?.value.trim() || '';
      if (!thought) {
        this.showToast(I18n.t('aiAssist.needThought'));
        document.getElementById('ai-modal-thought')?.focus();
        return;
      }
      this.refreshAiAssistPrompts(thought);
    }
    const elId = which === 'export' ? 'ai-prompt-export' : 'ai-prompt-reflection';
    const text = document.getElementById(elId)?.value || '';
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      if (btnEl) {
        btnEl.classList.add('copied');
        const label = btnEl.querySelector('span:last-child');
        const prev = label?.textContent;
        if (label) label.textContent = I18n.t('aiAssist.copyDone');
        setTimeout(() => {
          btnEl.classList.remove('copied');
          if (label && prev) label.textContent = prev;
        }, 2000);
      }
      this.showToast(I18n.t('aiAssist.copied'));
    } catch {
      const el = document.getElementById(elId);
      el?.focus();
      el?.select();
      this.showToast(I18n.t('aiAssist.copyFailed'));
    }
  },

  previewAiImport() {
    const raw = document.getElementById('ai-import-input')?.value.trim() || '';
    if (!raw) {
      this.showToast(I18n.t('aiAssist.importEmpty'));
      return;
    }

    if (this.checkCrisisAndShow(raw)) return;

    const transcript = document.getElementById('ai-import-transcript')?.value.trim() || '';
    if (transcript && this.checkCrisisAndShow(transcript)) return;

    const preview = AiAssist.buildImportPreview(raw);
    if (!preview.ok) {
      const key =
        preview.error === 'missing_event'
          ? 'aiAssist.importMissingEvent'
          : 'aiAssist.previewInvalid';
      let msg = I18n.t(key);
      if (preview.hint) {
        msg += ` — ${this.formatAiJsonHint(preview.hint)}`;
      }
      this.showToast(msg);
      this.hideAiImportPreview();
      return;
    }

    preview.transcriptTurns = transcript ? AiAssist.parseTranscript(transcript).length : 0;
    this.aiImportPreviewPayload = preview.payload;
    this.aiImportTranscript = transcript;
    this.renderAiImportPreview(preview);
    document.getElementById('ai-import-preview').hidden = false;
    document.getElementById('ai-import-preview')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  },

  renderAiImportPreview(preview) {
    const statsEl = document.getElementById('ai-preview-stats');
    const warnEl = document.getElementById('ai-preview-warnings');
    const body = document.getElementById('ai-preview-body');
    if (!body) return;

    if (statsEl && preview.stats) {
      statsEl.hidden = false;
      let statsText = I18n.t('aiAssist.previewStats', {
        ai: preview.stats.aiCount,
        rule: preview.stats.ruleCount,
        steps: preview.stats.stepCount,
      });
      if (preview.transcriptTurns > 0) {
        statsText += ` · ${I18n.t('aiAssist.previewStatsTranscript', { n: preview.transcriptTurns })}`;
      }
      statsEl.textContent = statsText;
    }

    if (warnEl) {
      const warns = [];
      if (preview.warnings?.includes('many_empty_steps')) {
        warns.push(I18n.t('aiAssist.previewWarnManyEmpty'));
      }
      if (preview.warnings?.includes('no_interpretation')) {
        warns.push(I18n.t('aiAssist.previewWarnNoInterpretation'));
      }
      if (preview.warnings?.includes('no_emotions')) {
        warns.push(I18n.t('aiAssist.previewWarnNoEmotions'));
      }
      if (warns.length) {
        warnEl.hidden = false;
        warnEl.innerHTML = warns
          .map((w) => `<div class="ai-preview-warn">${this.escapeHtml(w)}</div>`)
          .join('');
      } else {
        warnEl.hidden = true;
        warnEl.innerHTML = '';
      }
    }

    const fmtItems = (items) => {
      if (!items?.length) {
        return `<span class="ai-preview-empty">${this.escapeHtml(I18n.t('aiAssist.previewEmptyStep'))}</span>`;
      }
      return items
        .map((item) => {
          const cls = item.source === 'rule' ? 'ai-preview-tag rule' : 'ai-preview-tag ai';
          const title =
            item.source === 'rule'
              ? I18n.t('aiAssist.previewFromRule')
              : I18n.t('aiAssist.previewFromAi');
          return `<span class="${cls}" title="${this.escapeAttr(title)}">${this.escapeHtml(item.label)}</span>`;
        })
        .join('');
    };

    const stepLabel = (type) => CognitiveLibrary.getFrameworkLabel(type);

    const stepColor = (type) =>
      CognitiveLibrary.NODE_TYPE_COLORS[type]?.border || 'var(--accent)';

    let html = '<div class="ai-preview-cards">';
    for (const row of preview.rows) {
      html += `
        <div class="ai-preview-card" style="--step-color: ${stepColor(row.type)}">
          <div class="ai-preview-card-head">
            <span class="ai-preview-dot"></span>
            <span class="ai-preview-step">${this.escapeHtml(stepLabel(row.type))}</span>
          </div>
          <div class="ai-preview-items">${fmtItems(row.items)}</div>
        </div>`;
    }
    html += '</div>';

    if (preview.ruleEnrichments?.length) {
      html += `<div class="ai-preview-section-title">${this.escapeHtml(I18n.t('aiAssist.previewFromRule'))}</div>`;
      html += '<div class="ai-preview-cards ai-preview-cards--rule">';
      for (const row of preview.ruleEnrichments) {
        html += `
          <div class="ai-preview-card ai-preview-card--compact" style="--step-color: ${stepColor(row.type)}">
            <div class="ai-preview-card-head">
              <span class="ai-preview-dot"></span>
              <span class="ai-preview-step">${this.escapeHtml(stepLabel(row.type))}</span>
            </div>
            <div class="ai-preview-items">${fmtItems(row.items)}</div>
          </div>`;
      }
      html += '</div>';
    }

    if (preview.biases?.length) {
      html += `<div class="ai-preview-section-title">${this.escapeHtml(I18n.t('aiAssist.previewBiases'))}</div>`;
      html += `<div class="ai-preview-items">${fmtItems(preview.biases)}</div>`;
    }

    body.innerHTML = html;
  },

  // ─── AI ASSIST — Bản đồ / Khám phá / Timeline ───

  openAiScreenAssist(screenId) {
    if (typeof AiAssistScreens === 'undefined') return;
    if (!AiAssistScreens.SCREENS.includes(screenId)) return;

    if (DataStore.getNodes().length === 0) {
      this.showToast(I18n.t('aiScreen.needData'));
      return;
    }

    this.aiScreenId = screenId;
    this.aiScreenPreviewPayload = null;
    this.hideAiScreenPreview();
    this.setAiScreenStep(1);
    this.refreshAiScreenPrompts();

    const titleKey = `aiScreen.title_${screenId}`;
    document.getElementById('ai-screen-title').textContent = I18n.t(titleKey);
    const descEl = document.getElementById('ai-screen-step1-desc');
    if (descEl) descEl.textContent = I18n.t(`aiScreen.desc_${screenId}`);

    document.getElementById('ai-screen-modal').showModal();
  },

  setAiScreenStep(step) {
    this.aiScreenStep = step;
    document.querySelectorAll('[data-ai-screen-panel]').forEach((panel) => {
      const n = Number(panel.dataset.aiScreenPanel);
      panel.hidden = n !== step;
      panel.classList.toggle('active', n === step);
    });
    document.querySelectorAll('.ai-screen-stepper .ai-stepper-btn').forEach((btn) => {
      const n = Number(btn.dataset.aiScreenStep);
      btn.classList.toggle('active', n === step);
      btn.classList.toggle('done', n < step);
    });
    if (step === 1 || step === 3) {
      this.refreshAiScreenPrompts({ notify: step === 3 });
    }
    if (step === 3) {
      this.showAiScreenContextNote();
      document.getElementById('ai-screen-import')?.focus();
    } else {
      const note = document.getElementById('ai-screen-context-note');
      if (note) note.hidden = true;
    }
  },

  showAiScreenContextNote() {
    const el = document.getElementById('ai-screen-context-note');
    if (!el || !this.aiScreenContextSyncedAt) return;
    const time = this.aiScreenContextSyncedAt.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    });
    el.textContent = I18n.t('aiAssist.contextNote', { time });
    el.hidden = false;
  },

  refreshAiScreenPrompts(options = {}) {
    if (!this.aiScreenId || typeof AiAssistScreens === 'undefined') return;
    const analysis = document.getElementById('ai-screen-prompt-analysis');
    const exp = document.getElementById('ai-screen-prompt-export');
    if (analysis) analysis.value = AiAssistScreens.getAnalysisPrompt(this.aiScreenId);
    if (exp) exp.value = AiAssistScreens.getExportPrompt(this.aiScreenId);
    this.aiScreenContextSyncedAt = new Date();
    if (options.notify) {
      this.showToast(I18n.t('aiAssist.contextRefreshed'));
    }
  },

  async copyAiScreenPrompt(which, btnEl) {
    const elId = which === 'export' ? 'ai-screen-prompt-export' : 'ai-screen-prompt-analysis';
    const text = document.getElementById(elId)?.value || '';
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      if (btnEl) {
        btnEl.classList.add('copied');
        setTimeout(() => btnEl.classList.remove('copied'), 2000);
      }
      this.showToast(I18n.t('aiAssist.copied'));
    } catch {
      document.getElementById(elId)?.select();
      this.showToast(I18n.t('aiAssist.copyFailed'));
    }
  },

  hideAiScreenPreview() {
    const panel = document.getElementById('ai-screen-preview-panel');
    const body = document.getElementById('ai-screen-preview-body');
    const statsEl = document.getElementById('ai-screen-preview-stats');
    const warnEl = document.getElementById('ai-screen-preview-warnings');
    if (panel) panel.hidden = true;
    if (body) body.innerHTML = '';
    if (statsEl) {
      statsEl.hidden = true;
      statsEl.textContent = '';
    }
    if (warnEl) {
      warnEl.hidden = true;
      warnEl.innerHTML = '';
    }
    this.aiScreenPreviewPayload = null;
    this.aiScreenPreviewMatchPlan = null;
  },

  previewAiScreenImport() {
    const raw = document.getElementById('ai-screen-import')?.value.trim() || '';
    if (!raw) {
      this.showToast(I18n.t('aiAssist.importEmpty'));
      return;
    }
    if (this.checkCrisisAndShow(raw)) return;

    const preview = AiAssistScreens.buildPreview(this.aiScreenId, raw);
    if (!preview.ok) {
      let msg = I18n.t('aiAssist.previewInvalid');
      if (preview.hint) {
        msg += ` — ${this.formatAiJsonHint(preview.hint)}`;
      }
      this.showToast(msg);
      this.hideAiScreenPreview();
      return;
    }

    this.aiScreenPreviewPayload = preview.payload;
    this.aiScreenPreviewMatchPlan = preview.matchPlan;
    this.renderAiScreenPreview(preview);
    document.getElementById('ai-screen-preview-panel').hidden = false;
  },

  renderAiScreenMatchBadge(status) {
    const key =
      status === 'apply' ? 'aiAssist.matchApply' : status === 'fuzzy' ? 'aiAssist.matchFuzzy' : 'aiAssist.matchMiss';
    return `<span class="ai-match-badge ai-match-badge--${status}">${this.escapeHtml(I18n.t(key))}</span>`;
  },

  renderForestMatchPlan(matchPlan) {
    if (!matchPlan) return '';

    let html = `<div class="ai-preview-section-title">${this.escapeHtml(I18n.t('aiScreen.preview_relations'))}</div>`;
    html += '<div class="ai-match-list">';

    matchPlan.relations.forEach((row, idx) => {
      const rel = row.rel;
      const line = `${rel.sourceType}: ${rel.sourceLabel} → ${rel.targetType}: ${rel.targetLabel} (${rel.relationType})`;
      html += `<div class="ai-match-row ai-match-row--${row.status}">`;
      html += `<div class="ai-match-row-head">${this.renderAiScreenMatchBadge(row.status)}<span>${this.escapeHtml(line)}</span></div>`;
      if (row.source.node) {
        html += `<div class="ai-match-resolved">${this.escapeHtml(I18n.t('aiAssist.matchResolvedAs', { label: row.source.node.label }))}</div>`;
      }
      if (row.target.node) {
        html += `<div class="ai-match-resolved">${this.escapeHtml(I18n.t('aiAssist.matchResolvedAs', { label: row.target.node.label }))}</div>`;
      }
      if (row.status === 'miss') {
        html += `<p class="ai-match-resolved">${this.escapeHtml(I18n.t('aiAssist.editLabelHint'))}</p>`;
        html += `<div class="ai-match-edit">
          <input type="text" data-rel-fix="source" data-rel-idx="${idx}" value="${this.escapeAttr(rel.sourceLabel)}" aria-label="source" />
          <input type="text" data-rel-fix="target" data-rel-idx="${idx}" value="${this.escapeAttr(rel.targetLabel)}" aria-label="target" />
        </div>`;
      }
      html += '</div>';
    });
    html += '</div>';

    if (matchPlan.nodeUpdates.length) {
      html += `<div class="ai-preview-section-title">${this.escapeHtml(I18n.t('aiScreen.preview_nodeUpdates'))}</div>`;
      html += '<div class="ai-match-list">';
      for (const row of matchPlan.nodeUpdates) {
        const upd = row.upd;
        const line = `${upd.type}: ${upd.label}${upd.category ? ` [${upd.category}]` : ''}`;
        html += `<div class="ai-match-row ai-match-row--${row.status}">`;
        html += `<div class="ai-match-row-head">${this.renderAiScreenMatchBadge(row.status)}<span>${this.escapeHtml(line)}</span></div>`;
        if (row.node) {
          html += `<div class="ai-match-resolved">${this.escapeHtml(I18n.t('aiAssist.matchResolvedAs', { label: row.node.label }))}</div>`;
        }
        html += '</div>';
      }
      html += '</div>';
    }

    return html;
  },

  syncForestPreviewEdits() {
    if (!this.aiScreenPreviewPayload?.relations) return;

    document.querySelectorAll('#ai-screen-preview-body [data-rel-fix]').forEach((input) => {
      const idx = Number(input.dataset.relIdx);
      const field = input.dataset.relFix;
      const rel = this.aiScreenPreviewPayload.relations[idx];
      if (!rel) return;
      if (field === 'source') rel.sourceLabel = input.value.trim();
      if (field === 'target') rel.targetLabel = input.value.trim();
    });
  },

  renderAiScreenPreview(preview) {
    const statsEl = document.getElementById('ai-screen-preview-stats');
    const warnEl = document.getElementById('ai-screen-preview-warnings');
    const body = document.getElementById('ai-screen-preview-body');
    if (!body) return;

    if (statsEl && preview.stats) {
      statsEl.hidden = false;
      if (this.aiScreenId === 'forest') {
        statsEl.textContent = I18n.t('aiAssist.previewForestStats', {
          apply: preview.stats.applyRelations,
          total: preview.stats.totalRelations,
          updates: preview.stats.applyUpdates,
          totalUpdates: preview.stats.totalUpdates,
        });
      } else if (this.aiScreenId === 'insights') {
        statsEl.textContent = I18n.t('aiAssist.previewInsightsStats', {
          n: preview.stats.contradictions,
          e: preview.stats.exploration,
          new: preview.stats.aiOnlyContradictions,
        });
      } else if (this.aiScreenId === 'timeline') {
        statsEl.textContent = I18n.t('aiAssist.previewTimelineStats', {
          m: preview.stats.milestones,
          v: preview.stats.valueShifts,
        });
      }
    }

    if (warnEl && preview.warnings?.length) {
      const msgs = [];
      const missRel = preview.matchPlan?.relations.filter((r) => r.status === 'miss').length || 0;
      const fuzzyRel = preview.matchPlan?.relations.filter((r) => r.status === 'fuzzy').length || 0;
      const overlap = preview.stats?.contradictions
        ? preview.stats.contradictions - (preview.stats.aiOnlyContradictions || 0)
        : 0;

      if (preview.warnings.includes('forest_relations_miss') && missRel) {
        msgs.push(I18n.t('aiAssist.warnForestMiss', { n: missRel }));
      }
      if (preview.warnings.includes('forest_relations_fuzzy') && fuzzyRel) {
        msgs.push(I18n.t('aiAssist.warnForestFuzzy', { n: fuzzyRel }));
      }
      if (preview.warnings.includes('insights_overlap_rule') && overlap > 0) {
        msgs.push(I18n.t('aiAssist.warnInsightsOverlap', { n: overlap }));
      }

      if (msgs.length) {
        warnEl.hidden = false;
        warnEl.innerHTML = msgs
          .map((m, i) => {
            const cls = i === 0 && missRel ? 'ai-preview-warn ai-preview-warn--error' : 'ai-preview-warn';
            return `<div class="${cls}">${this.escapeHtml(m)}</div>`;
          })
          .join('');
      } else {
        warnEl.hidden = true;
        warnEl.innerHTML = '';
      }
    } else if (warnEl) {
      warnEl.hidden = true;
      warnEl.innerHTML = '';
    }

    const rowLabel = (key) => I18n.t(`aiScreen.preview_${key}`) || key;
    let html = '';

    if (this.aiScreenId === 'forest' && preview.matchPlan) {
      html += this.renderForestMatchPlan(preview.matchPlan);
      const summaryRow = preview.rows.find((r) => r.label === 'summary');
      if (summaryRow?.items?.length) {
        html += `<div class="ai-preview-section-title">${this.escapeHtml(rowLabel('summary'))}</div>`;
        html += `<p class="ai-summary-text">${this.escapeHtml(summaryRow.items[0])}</p>`;
      }
      const trees = preview.rows.find((r) => r.label === 'treeInsights');
      if (trees?.items?.length) {
        html += `<div class="ai-preview-section-title">${this.escapeHtml(rowLabel('treeInsights'))}</div>`;
        html += '<ul class="ai-screen-preview-ul">';
        for (const item of trees.items) {
          html += `<li>${this.escapeHtml(item)}</li>`;
        }
        html += '</ul>';
      }
    } else {
      html += '<div class="ai-screen-preview-list">';
      for (const row of preview.rows) {
        if (!row.items?.length) continue;
        html += `<div class="ai-screen-preview-block"><div class="ai-preview-section-title">${this.escapeHtml(rowLabel(row.label))}</div>`;
        html += '<ul class="ai-screen-preview-ul">';
        for (const item of row.items) {
          html += `<li>${this.escapeHtml(item)}</li>`;
        }
        html += '</ul></div>';
      }
      html += '</div>';
    }

    body.innerHTML = html || `<p class="ai-preview-empty">${this.escapeHtml(I18n.t('aiScreen.previewEmpty'))}</p>`;
  },

  confirmAiScreenImport() {
    if (!this.aiScreenPreviewPayload) {
      this.previewAiScreenImport();
      return;
    }

    if (this.aiScreenId === 'forest') {
      this.syncForestPreviewEdits();
    }

    const result = AiAssistScreens.importPayload(this.aiScreenId, this.aiScreenPreviewPayload);
    if (!result.ok) {
      this.showToast(I18n.t('aiAssist.importInvalid'));
      return;
    }

    document.getElementById('ai-screen-import').value = '';
    this.hideAiScreenPreview();
    document.getElementById('ai-screen-modal').close();

    this.showToast(I18n.t(`aiScreen.importSuccess_${this.aiScreenId}`));
    this.renderHomeStats();
    if (this.aiScreenId === 'insights') this.renderInsights();
    if (this.aiScreenId === 'forest') this.renderForest();
    if (this.aiScreenId === 'timeline') this.renderTimeline();
  },

  renderForestAiBanner() {
    const banner = document.getElementById('forest-ai-banner');
    const overlay = DataStore.getAiOverlay('forest');
    if (!banner) return;

    if (!overlay?.summary && !(overlay?.treeInsights?.length)) {
      banner.hidden = true;
      return;
    }

    const trees = (overlay.treeInsights || [])
      .map((t) => `<li><strong>${this.escapeHtml(I18n.forestLabel(t.treeId))}</strong>: ${this.escapeHtml(t.observation || t.theme)}</li>`)
      .join('');

    banner.hidden = false;
    banner.innerHTML = `
      <div class="ai-screen-banner-title">${this.escapeHtml(I18n.t('aiScreen.bannerForest'))}</div>
      ${overlay.summary ? `<p>${this.escapeHtml(overlay.summary)}</p>` : ''}
      ${trees ? `<ul class="ai-screen-banner-list">${trees}</ul>` : ''}
    `;
  },

  confirmAiImport() {
    if (!this.aiImportPreviewPayload) {
      this.previewAiImport();
      return;
    }

    const raw = document.getElementById('ai-import-input')?.value.trim() || '';
    if (raw && this.checkCrisisAndShow(raw)) return;

    const transcript = this.aiImportTranscript || document.getElementById('ai-import-transcript')?.value.trim() || '';
    if (transcript && this.checkCrisisAndShow(transcript)) return;

    const result = AiAssist.importSession(this.aiImportPreviewPayload, { transcript });
    if (!result.ok) {
      const key =
        result.error === 'missing_event' ? 'aiAssist.importMissingEvent' : 'aiAssist.importInvalid';
      this.showToast(I18n.t(key));
      return;
    }

    document.getElementById('ai-import-input').value = '';
    const transcriptEl = document.getElementById('ai-import-transcript');
    if (transcriptEl) transcriptEl.value = '';
    this.hideAiImportPreview();
    document.getElementById('ai-assist-modal').close();

    this.activeSessionId = result.session.id;
    this.editingMessageId = null;
    this.renderHomeStats();
    this.showToast(I18n.t('aiAssist.importSuccess'));
    this.navigate('reflection');
  },

  startReflection() {
    const input = document.getElementById('home-thought-input');
    const thought = input.value.trim();

    if (!thought) {
      this.showToast(I18n.t('home.shareFirst'));
      input.focus();
      return;
    }

    if (this.checkCrisisAndShow(thought)) return;

    const { session } = ReflectionEngine.createSession(thought);
    this.activeSessionId = session.id;
    this.editingMessageId = null;
    input.value = '';

    this.showToast(I18n.t('home.sessionStarted'));
    this.navigate('reflection');
  },

  applyExplorationSeed(seedThought) {
    if (!seedThought) return;
    if (this.checkCrisisAndShow(seedThought)) return;

    const input = document.getElementById('home-thought-input');
    if (input) {
      input.value = seedThought;
      input.focus();
    }

    this.navigate('home');
    this.showToast(I18n.t('insights.explorationFilled'));
  },

  // ─── REFLECTION ───

  renderReflection() {
    const session = this.activeSessionId
      ? DataStore.getSession(this.activeSessionId)
      : DataStore.getSessions().slice(-1)[0];

    if (!session) {
      this.renderEmptyReflection();
      return;
    }

    this.activeSessionId = session.id;
    this.renderFlowIndicator(session.flowStep);
    this.renderSessionTimeline(session);
    this.renderChatMessages(session);
    this.renderReflectionSuggestions(session);
  },

  renderEmptyReflection() {
    this.editingMessageId = null;
    document.getElementById('chat-messages').innerHTML = `
      <div class="insight-empty" style="text-align:center;padding:2rem;">
        ${I18n.t('reflection.empty')}<br>
        ${I18n.t('reflection.emptyHint')}
      </div>
    `;
    document.getElementById('flow-indicator').innerHTML = '';
    document.getElementById('session-timeline-steps').innerHTML = '';
    document.getElementById('chat-suggestions').hidden = true;
    document.getElementById('suggestions-list').innerHTML = '';
    document.getElementById('short-suggestions').hidden = true;
    document.getElementById('short-suggestions-list').innerHTML = '';
  },

  renderSuggestionChips(listEl, items, chipClass = 'suggestion-chip') {
    listEl.innerHTML = items
      .map(
        (text) => `
          <button
            type="button"
            class="${chipClass}"
            data-text="${this.escapeAttr(text)}"
            role="option"
            title="${this.escapeAttr(I18n.t('reflection.suggestionTitle'))}"
          >${this.escapeHtml(text)}</button>
        `
      )
      .join('');
  },

  renderReflectionSuggestions(session) {
    const container = document.getElementById('chat-suggestions');
    const list = document.getElementById('suggestions-list');
    const shortWrap = document.getElementById('short-suggestions');
    const shortList = document.getElementById('short-suggestions-list');
    const suggestions = ReflectionEngine.getSuggestions(session);
    const shortSuggestions = ReflectionEngine.getShortSuggestions(session);
    const skipBtn = document.getElementById('btn-skip-step');
    const flow = CognitiveLibrary.REFLECTION_FLOW;
    const atLastStep = flow.indexOf(session.flowStep) >= flow.length - 1;
    const sessionEnded = session.messages?.some(
      (m) => m.role === 'guide' && I18n.isSessionEndContent(m.content)
    );

    if (skipBtn) {
      skipBtn.hidden = !session || atLastStep || sessionEnded;
    }

    if (!suggestions.length && !shortSuggestions.length) {
      container.hidden = true;
      list.innerHTML = '';
      shortWrap.hidden = true;
      shortList.innerHTML = '';
      return;
    }

    container.hidden = false;

    if (shortSuggestions.length) {
      shortWrap.hidden = false;
      this.renderSuggestionChips(shortList, shortSuggestions, 'suggestion-chip suggestion-chip-short');
    } else {
      shortWrap.hidden = true;
      shortList.innerHTML = '';
    }

    if (suggestions.length) {
      this.renderSuggestionChips(list, suggestions);
    } else {
      list.innerHTML = '';
    }
  },

  renderFlowIndicator(currentStep) {
    const flow = CognitiveLibrary.REFLECTION_FLOW;
    const currentIdx = flow.indexOf(currentStep);

    const html = flow
      .map((step, idx) => {
        let cls = 'flow-step';
        if (idx === currentIdx) cls += ' active';
        else if (idx < currentIdx) cls += ' done';
        return `<span class="${cls}">${CognitiveLibrary.getFrameworkLabel(step)}</span>`;
      })
      .join('');

    document.getElementById('flow-indicator').innerHTML = html;
  },

  renderSessionTimeline(session) {
    const flow = CognitiveLibrary.REFLECTION_FLOW;
    const currentIdx = flow.indexOf(session.flowStep);

    const html = flow
      .map((step, idx) => {
        const cls = idx <= currentIdx ? 'timeline-step-item active' : 'timeline-step-item';
        const icon = idx < currentIdx ? '✓' : idx === currentIdx ? '●' : '○';
        return `<div class="${cls}">${icon} ${CognitiveLibrary.getFrameworkLabel(step)}</div>`;
      })
      .join('');

    document.getElementById('session-timeline-steps').innerHTML = html;
  },

  renderChatMessages(session) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = session.messages
      .map((msg) => {
        const isUser = msg.role === 'user';
        const time = I18n.localeTime(msg.timestamp);
        const editedTag = msg.editedAt
          ? ` · ${I18n.t('reflection.editedLabel')}`
          : '';

        if (isUser && this.editingMessageId === msg.id) {
          return `
            <div class="message message-user message-editing" data-message-id="${this.escapeAttr(msg.id)}">
              <textarea
                class="message-edit-input"
                id="message-edit-input-${this.escapeAttr(msg.id)}"
                rows="3"
                aria-label="${this.escapeAttr(I18n.t('reflection.editMessage'))}"
              >${this.escapeHtml(msg.content)}</textarea>
              <div class="message-edit-actions">
                <button type="button" class="btn btn-primary btn-sm" data-save-edit="${this.escapeAttr(msg.id)}">
                  ${I18n.t('reflection.saveEdit')}
                </button>
                <button type="button" class="btn btn-ghost btn-sm" data-cancel-edit>
                  ${I18n.t('reflection.cancelEdit')}
                </button>
              </div>
            </div>
          `;
        }

        const editBtn = isUser
          ? `<button
              type="button"
              class="message-edit-btn"
              data-edit-message="${this.escapeAttr(msg.id)}"
              title="${this.escapeAttr(I18n.t('reflection.editMessage'))}"
              aria-label="${this.escapeAttr(I18n.t('reflection.editMessage'))}"
            >✎</button>`
          : '';

        return `
          <div class="message message-${isUser ? 'user' : 'guide'}">
            <div class="message-body">${this.escapeHtml(msg.content)}</div>
            <div class="message-meta">
              ${isUser ? I18n.t('reflection.you') : I18n.t('reflection.guide')} · ${time}${editedTag}
              ${editBtn}
            </div>
          </div>
        `;
      })
      .join('');

    container.scrollTop = container.scrollHeight;

    if (this.editingMessageId) {
      const input = document.getElementById(`message-edit-input-${this.editingMessageId}`);
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    }
  },

  startEditMessage(messageId) {
    if (!this.activeSessionId) return;
    this.editingMessageId = messageId;
    this.renderReflection();
  },

  cancelEditMessage() {
    this.editingMessageId = null;
    this.renderReflection();
  },

  saveEditMessage(messageId) {
    if (!this.activeSessionId || !messageId) return;

    const input = document.getElementById(`message-edit-input-${messageId}`);
    const text = input?.value.trim();

    if (!text) {
      this.showToast(I18n.t('reflection.editEmpty'));
      input?.focus();
      return;
    }

    if (this.checkCrisisAndShow(text)) return;

    const result = ReflectionEngine.editUserMessage(this.activeSessionId, messageId, text);
    if (!result) return;

    this.editingMessageId = null;
    this.renderReflection();
    this.renderHomeStats();
    this.showToast(I18n.t('reflection.messageUpdated'));
  },

  sendChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();

    if (!text || !this.activeSessionId) return;

    if (this.checkCrisisAndShow(text)) return;

    this.editingMessageId = null;
    const result = ReflectionEngine.continueSession(this.activeSessionId, text);
    if (!result) return;

    input.value = '';
    this.renderReflection();
    this.renderHomeStats();
  },

  skipReflectionStep() {
    if (!this.activeSessionId) return;
    const result = ReflectionEngine.skipCurrentStep(this.activeSessionId);
    if (!result) return;
    this.renderReflection();
  },

  checkCrisisAndShow(text) {
    if (typeof SafetyEngine === 'undefined') return false;
    const { detected } = SafetyEngine.detectCrisis(text);
    if (!detected) return false;
    this.showCrisisModal();
    return true;
  },

  showCrisisModal() {
    const resources = SafetyEngine.getResources();
    document.getElementById('crisis-modal-title').textContent = resources.title;
    document.getElementById('crisis-modal-body').textContent = resources.body;
    document.getElementById('crisis-modal-footer').textContent = resources.footer;
    document.getElementById('btn-crisis-understood').textContent = resources.understood;

    const hotlinesEl = document.getElementById('crisis-hotlines');
    hotlinesEl.innerHTML = resources.hotlines
      .map(
        (h) => `
          <li>
            <a href="tel:${this.escapeAttr(h.tel)}" class="crisis-hotline-link">
              <strong>${this.escapeHtml(h.label)}</strong>
              <span>${this.escapeHtml(h.tel)}</span>
            </a>
          </li>
        `
      )
      .join('');

    document.getElementById('crisis-modal').showModal();
  },

  // ─── FOREST ───

  renderForest() {
    if (this.selectedForestTree) {
      this.renderForestDetail(this.selectedForestTree);
      return;
    }
    this.showForestGrid();
  },

  showForestGrid() {
    this.selectedForestTree = null;
    document.getElementById('forest-grid').hidden = false;
    document.getElementById('forest-detail').hidden = true;
    this.renderForestAiBanner();

    const grid = document.getElementById('forest-grid');
    const trees = CognitiveLibrary.FOREST_TREES;

    grid.innerHTML = trees
      .map((tree) => {
        const nodes = CognitiveTree.getNodesByForest(tree.id);
        const growth = CognitiveTree.getTreeGrowth(tree.id);
        const status = CognitiveTree.getTreeStatus(tree.id);
        return `
          <div class="tree-card glass" data-tree="${tree.id}" role="button" tabindex="0">
            <span class="tree-icon">${tree.icon}</span>
            <div class="tree-name">${I18n.forestLabel(tree.id)}</div>
            <div class="tree-meta">${I18n.t('forest.entries', { n: nodes.length })}</div>
            <div class="tree-growth">
              <div class="tree-growth-bar" style="width:${growth}%"></div>
            </div>
            <span class="tree-status status-${status}">${I18n.treeStatusLabel(status)}</span>
          </div>
        `;
      })
      .join('');

    grid.querySelectorAll('.tree-card').forEach((card) => {
      card.addEventListener('click', () => {
        this.selectedForestTree = card.dataset.tree;
        this.nodeFilter = 'all';
        this.renderForestDetail(this.selectedForestTree);
      });
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') card.click();
      });
    });
  },

  renderForestDetail(treeId) {
    document.getElementById('forest-grid').hidden = true;
    document.getElementById('forest-detail').hidden = false;
    const banner = document.getElementById('forest-ai-banner');
    if (banner) banner.hidden = true;

    const tree = CognitiveLibrary.FOREST_TREES.find((t) => t.id === treeId);
    document.getElementById('forest-detail-title').textContent = `${tree.icon} ${I18n.forestLabel(treeId)}`;

    this.renderNodeFilters();
    this.renderNodeGrid(treeId);
  },

  renderNodeFilters() {
    const types = ['all', ...CognitiveLibrary.REFLECTION_FLOW];
    const container = document.getElementById('node-filters');

    container.innerHTML = types
      .map(
        (t) => `
        <button class="filter-chip ${t === this.nodeFilter ? 'active' : ''}" data-filter="${t}">
          ${t === 'all' ? I18n.t('forest.filterAll') : CognitiveLibrary.getFrameworkLabel(t)}
        </button>
      `
      )
      .join('');

    container.querySelectorAll('.filter-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        this.nodeFilter = chip.dataset.filter;
        this.renderNodeFilters();
        this.renderNodeGrid(this.selectedForestTree);
      });
    });
  },

  renderNodeGrid(treeId) {
    let nodes = CognitiveTree.getNodesByForest(treeId);

    if (this.nodeFilter !== 'all') {
      nodes = nodes.filter((n) => n.type === this.nodeFilter);
    }

    nodes.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));

    const grid = document.getElementById('node-grid');

    if (nodes.length === 0) {
      grid.innerHTML = `<div class="insight-empty">${I18n.t('forest.empty')}</div>`;
      return;
    }

    grid.innerHTML = nodes.map((node) => this.renderNodeCard(node)).join('');

    grid.querySelectorAll('.node-card').forEach((card) => {
      card.addEventListener('click', () => {
        this.openNodeModal(card.dataset.nodeId);
      });
    });
  },

  renderNodeCard(node) {
    const colors = CognitiveLibrary.NODE_TYPE_COLORS[node.type] || {};
    const statusLabel = CognitiveLibrary.getNodeStatusLabel(node.status);

    return `
      <div class="node-card glass" data-node-id="${node.id}"
           style="background:${colors.bg};border-left-color:${colors.border}">
        <div class="node-type" style="color:${colors.text}">${CognitiveLibrary.getFrameworkLabel(node.type)}</div>
        <div class="node-label">${this.escapeHtml(node.label)}</div>
        <div class="node-footer">
          <span class="node-status status-${node.status}">${statusLabel}</span>
          <div class="confidence-bar" title="${this.escapeAttr(I18n.t('forest.confidence'))}: ${node.confidence}">
            <div class="confidence-fill" style="width:${node.confidence * 100}%"></div>
          </div>
        </div>
      </div>
    `;
  },

  openNodeModal(nodeId) {
    const node = CognitiveTree.getNodeById(nodeId);
    if (!node) return;

    const colors = CognitiveLibrary.NODE_TYPE_COLORS[node.type] || {};
    const relations = CognitiveTree.getNodeRelations(nodeId);

    const modal = document.getElementById('node-modal');
    document.getElementById('modal-body').innerHTML = `
      <span class="modal-type-badge" style="background:${colors.bg};color:${colors.text};border:1px solid ${colors.border}">
        ${CognitiveLibrary.getFrameworkLabel(node.type)}
      </span>
      <div class="modal-label">${this.escapeHtml(node.label)}</div>
      <div class="modal-detail-row"><span>${I18n.t('forest.status')}</span><span>${CognitiveLibrary.getNodeStatusLabel(node.status)}</span></div>
      <div class="modal-detail-row"><span>${I18n.t('forest.confidence')}</span><span>${Math.round(node.confidence * 100)}%</span></div>
      <div class="modal-detail-row"><span>${I18n.t('forest.occurrences')}</span><span>${I18n.t('forest.occurrencesTimes', { n: node.occurrences })}</span></div>
      <div class="modal-detail-row"><span>${I18n.t('forest.domain')}</span><span>${this.getForestLabel(node.category)}</span></div>
      <div class="modal-detail-row"><span>${I18n.t('forest.created')}</span><span>${this.formatDate(node.createdAt)}</span></div>
      <div class="modal-detail-row"><span>${I18n.t('forest.updated')}</span><span>${this.formatDate(node.updatedAt)}</span></div>
      ${
        relations.length > 0
          ? `<div style="margin-top:1rem;font-size:0.85rem;color:var(--text-secondary)">
              ${I18n.t('forest.relations', { n: relations.length })}
            </div>`
          : ''
      }
      ${
        node.aiNote
          ? `<div class="modal-ai-note" style="margin-top:1rem;padding:0.75rem;border-radius:8px;background:rgba(16,185,129,0.08);font-size:0.85rem">
              <strong>${this.escapeHtml(I18n.t('aiScreen.nodeNote'))}</strong><br>${this.escapeHtml(node.aiNote)}
            </div>`
          : ''
      }
    `;

    modal.showModal();
  },

  getForestLabel(id) {
    return I18n.forestLabel(id);
  },

  // ─── INSIGHTS ───

  renderInsights() {
    const insights = InsightEngine.analyze();
    DataStore.setInsights(insights);

    const grid = document.getElementById('insights-grid');

    const aiBadge = `<span class="ai-from-badge">${this.escapeHtml(I18n.t('aiScreen.fromChatGpt'))}</span>`;

    grid.innerHTML = `
      ${
        insights.aiSummary
          ? this.renderInsightSection(
              I18n.t('aiScreen.bannerInsights'),
              `<p class="ai-summary-text">${this.escapeHtml(insights.aiSummary)}</p>`,
              'exploration'
            )
          : ''
      }
      ${
        insights.aiPatterns?.length
          ? this.renderInsightSection(
              I18n.t('aiScreen.patterns'),
              insights.aiPatterns
                .map(
                  (p) => `
                <div class="insight-item">
                  <strong>${this.escapeHtml(p.label)}</strong>
                  <div style="font-size:0.85rem;color:var(--text-secondary);margin-top:0.25rem">${this.escapeHtml(p.detail || '')}</div>
                </div>`
                )
                .join(''),
              'exploration'
            )
          : ''
      }
      ${this.renderInsightSection(
        I18n.t('insights.today'),
        insights.todayDiscoveries.length > 0
          ? insights.todayDiscoveries
              .map(
                (d) => `
              <div class="insight-item">
                <span class="insight-rank">${d.isNew ? I18n.t('insights.new') : '↑'}</span>
                <strong>${CognitiveLibrary.getFrameworkLabel(d.type)}</strong>: ${this.escapeHtml(d.label)}
                <span class="occurrence-badge">${CognitiveLibrary.getNodeStatusLabel(d.status)}</span>
              </div>
            `
              )
              .join('')
          : `<div class="insight-empty">${I18n.t('insights.todayEmpty')}</div>`
      )}

      ${this.renderInsightSection(
        I18n.t('insights.topBeliefs'),
        insights.topBeliefs.length > 0
          ? insights.topBeliefs
              .map(
                (n, i) => `
              <div class="top-node-item">
                <span><span class="insight-rank">#${i + 1}</span>${this.escapeHtml(n.label)}</span>
                <span class="occurrence-badge">${n.occurrences}x</span>
              </div>
            `
              )
              .join('')
          : `<div class="insight-empty">${I18n.t('insights.beliefsEmpty')}</div>`
      )}

      ${this.renderInsightSection(
        I18n.t('insights.topValues'),
        insights.topValues.length > 0
          ? insights.topValues
              .map(
                (n, i) => `
              <div class="top-node-item">
                <span><span class="insight-rank">#${i + 1}</span>${this.escapeHtml(n.label)}</span>
                <span class="occurrence-badge">${n.occurrences}x</span>
              </div>
            `
              )
              .join('')
          : `<div class="insight-empty">${I18n.t('insights.valuesEmpty')}</div>`
      )}

      ${this.renderInsightSection(
        I18n.t('insights.contradictions'),
        insights.contradictions.length > 0
          ? insights.contradictions
              .map(
                (c) => `
              <div class="insight-item ${c.severity === 'high' ? 'danger' : 'warning'}">
                ${c.type === 'ai' ? aiBadge : ''}
                ${this.escapeHtml(I18n.formatContradiction(c.message))}
              </div>
            `
              )
              .join('')
          : `<div class="insight-empty">${I18n.t('insights.contradictionsEmpty')}</div>`,
        insights.contradictions.length > 0 ? 'warning' : ''
      )}

      ${this.renderInsightSection(
        I18n.t('insights.exploration'),
        insights.explorationPrompts.length > 0
          ? insights.explorationPrompts
              .map(
                (p) => `
              <div class="exploration-prompt-card">
                <span class="exploration-prompt-source">${this.escapeHtml(p.source)}${p.fromAi ? ` ${aiBadge}` : ''}</span>
                <p class="exploration-prompt-text">${this.escapeHtml(p.prompt)}</p>
                <button
                  type="button"
                  class="btn btn-ghost btn-sm exploration-prompt-btn"
                  data-exploration-seed="${this.escapeAttr(p.seedThought)}"
                >
                  ${I18n.t('insights.explorationCta')}
                </button>
              </div>
            `
              )
              .join('')
          : `<div class="insight-empty">${I18n.t('insights.explorationEmpty')}</div>`,
        insights.explorationPrompts.length > 0 ? 'exploration' : ''
      )}

      ${this.renderInsightSection(
        I18n.t('insights.biases'),
        insights.biases.length > 0
          ? insights.biases
              .map(
                (b) => `
              <div class="insight-item">
                ${b.fromAi ? aiBadge : ''}
                <strong>${this.escapeHtml(b.label)}</strong>
                <div style="font-size:0.85rem;color:var(--text-secondary);margin-top:0.25rem">
                  ${this.escapeHtml(b.description)}
                </div>
              </div>
            `
              )
              .join('')
          : `<div class="insight-empty">${I18n.t('insights.biasesEmpty')}</div>`
      )}
    `;
  },

  renderInsightSection(title, content, extraClass = '') {
    return `
      <div class="insight-section glass ${extraClass}">
        <h3>${title}</h3>
        <div class="insight-list">${content}</div>
      </div>
    `;
  },

  // ─── TIMELINE ───

  renderTimeline() {
    const { grouped, narrative } = TimelineEngine.getFormattedTimeline();
    const container = document.getElementById('timeline-container');

    if (grouped.length === 0 && narrative.length === 0) {
      container.innerHTML = `
        <div class="insight-empty" style="padding:2rem;text-align:center">
          ${I18n.t('timeline.empty')}
        </div>
      `;
      return;
    }

    let html = '';
    const tlOverlay = DataStore.getAiOverlay('timeline');
    if (tlOverlay?.narrativeArc || tlOverlay?.reflectionPrompt) {
      html += `<div class="timeline-ai-block glass">
        <h3 class="timeline-year">${this.escapeHtml(I18n.t('aiScreen.bannerTimeline'))}</h3>`;
      if (tlOverlay.narrativeArc) {
        html += `<p class="ai-summary-text">${this.escapeHtml(tlOverlay.narrativeArc)}</p>`;
      }
      if (tlOverlay.reflectionPrompt) {
        html += `<p class="timeline-ai-prompt"><em>${this.escapeHtml(tlOverlay.reflectionPrompt)}</em></p>`;
      }
      html += '</div>';
    }

    // Narrative shifts (Value/Belief theo năm)
    if (narrative.length > 0) {
      html += `<div class="timeline-year-group"><h3 class="timeline-year">${I18n.t('timeline.journey')}</h3>`;
      for (const entry of narrative) {
        if (entry.value) {
          html += `
            <div class="timeline-event glass">
              <div class="timeline-event-title">${entry.year} — ${I18n.t('timeline.valueLabel')}: ${this.escapeHtml(entry.value.label)}</div>
              <div class="timeline-event-desc">${I18n.t('timeline.appears', { n: entry.value.occurrences })} · ${CognitiveLibrary.getNodeStatusLabel(entry.value.status)}</div>
            </div>
          `;
        }
        if (entry.transition) {
          html += `
            <div class="timeline-shift glass">
              <span class="shift-value">${this.escapeHtml(entry.transition.from)}</span>
              <span class="shift-arrow">↓</span>
              <span class="shift-value">${this.escapeHtml(entry.transition.to)}</span>
            </div>
          `;
        }
      }
      html += '</div>';
    }

    // Events theo năm
    for (const group of grouped) {
      html += `<div class="timeline-year-group">`;
      html += `<h3 class="timeline-year">${group.year}</h3>`;

      for (const event of group.events.slice(0, 20)) {
        html += `
          <div class="timeline-event glass">
            <div class="timeline-event-title">${this.escapeHtml(event.title)}</div>
            <div class="timeline-event-desc">${this.escapeHtml(event.description || '')}</div>
          </div>
        `;
      }

      html += `</div>`;
    }

    container.innerHTML = html;
  },

  // ─── TEST MODE ───

  renderTestMode() {
    const scenarios = TestMode.getScenarios();
    const listEl = document.getElementById('test-scenario-list');

    if (!TestMode.selectedScenarioId && scenarios.length > 0) {
      TestMode.selectScenario(scenarios[0].id);
    }

    listEl.innerHTML = `
      <div class="test-sidebar-title">${I18n.t('test.scenarios', { n: scenarios.length })}</div>
      ${scenarios
        .map((s) => {
          const active = s.id === TestMode.selectedScenarioId ? 'active' : '';
          return `
            <button
              type="button"
              class="test-scenario-card glass ${active}"
              data-scenario-id="${s.id}"
            >
              <span class="test-scenario-cat">${this.escapeHtml(TestMode.getCategoryLabel(s.category))}</span>
              <span class="test-scenario-title">${this.escapeHtml(s.title)}</span>
              <span class="test-scenario-tags">${s.tags.map((t) => `#${this.escapeHtml(t)}`).join(' ')}</span>
            </button>
          `;
        })
        .join('')}
    `;

    const scenario = TestMode.getScenario(TestMode.selectedScenarioId);
    const detailEl = document.getElementById('test-scenario-detail');

    if (!scenario) {
      detailEl.innerHTML =
        `<div class="insight-empty test-empty">${I18n.t('test.noScenarios')}</div>`;
      return;
    }

    detailEl.innerHTML = this.renderTestScenarioDetail(scenario);
  },

  renderTestScenarioDetail(scenario) {
    const restoreBtn = TestMode.hasSnapshot()
      ? `<button type="button" class="btn btn-ghost" data-test-action="restore">${I18n.t('test.restore')}</button>`
      : '';

    return `
      <div class="test-detail-header glass">
        <div>
          <span class="test-badge">${this.escapeHtml(TestMode.getCategoryLabel(scenario.category))}</span>
          <h3 class="test-detail-title">${this.escapeHtml(scenario.title)}</h3>
          <p class="test-detail-summary">${this.escapeHtml(scenario.summary)}</p>
        </div>
        <div class="test-actions">
          <button type="button" class="btn btn-ghost" data-test-action="apply-home" data-scenario-id="${scenario.id}">
            ${I18n.t('test.fillHome')}
          </button>
          <button type="button" class="btn btn-primary" data-test-action="simulate" data-scenario-id="${scenario.id}">
            ${I18n.t('test.simulate')}
          </button>
          <button type="button" class="btn btn-ghost" data-test-action="simulate-fast" data-scenario-id="${scenario.id}">
            ${I18n.t('test.simulateFast')}
          </button>
          ${restoreBtn}
        </div>
      </div>

      <div class="test-section glass">
        <h4>${I18n.t('test.persona')}</h4>
        <p><strong>${this.escapeHtml(scenario.persona.name)}</strong>, ${I18n.t('test.personaAge', { age: scenario.persona.age })} — ${this.escapeHtml(scenario.persona.role)}</p>
        <p class="test-muted">${this.escapeHtml(scenario.persona.context)}</p>
      </div>

      <div class="test-section glass">
        <h4>${I18n.t('test.situation')}</h4>
        <p>${this.escapeHtml(scenario.situation)}</p>
      </div>

      <div class="test-section glass">
        <h4>${I18n.t('test.initialThought')}</h4>
        <blockquote class="test-quote">${this.escapeHtml(scenario.initialThought)}</blockquote>
      </div>

      <div class="test-section glass">
        <div class="test-dialogue-header">
          <h4>${I18n.t('test.dialogue')}</h4>
          <div class="test-dialogue-toolbar">
            ${
              TestMode.hasDialogueEdits(scenario.id)
                ? `<span class="test-dialogue-badge">${I18n.t('test.dialogueEdited')}</span>`
                : ''
            }
            <button type="button" class="btn btn-ghost btn-sm" data-test-action="reset-dialogue" data-scenario-id="${scenario.id}">
              ${I18n.t('test.resetDialogue')}
            </button>
            <button type="button" class="btn btn-ghost btn-sm" data-test-action="simulate-rerun" data-scenario-id="${scenario.id}">
              ${I18n.t('test.rerunNoReset')}
            </button>
          </div>
        </div>
        <p class="test-muted">${I18n.t('test.dialogueHint')}</p>
        <ol class="test-dialogue-list" id="test-dialogue-list">
          ${TestMode.getEffectiveDialogue(scenario.id)
            .map(
              (turn, i) => `
            <li class="test-dialogue-item${turn.content !== scenario.dialogue[i]?.content ? ' test-dialogue-item--edited' : ''}">
              <div class="test-dialogue-step">
                <span class="test-step-num">${i + 1}</span>
                <span class="test-step-label">${this.escapeHtml(CognitiveLibrary.getFrameworkLabel(turn.step) || turn.step)}</span>
              </div>
              <textarea
                class="test-dialogue-input"
                data-dialogue-index="${i}"
                rows="3"
                aria-label="${this.escapeAttr(CognitiveLibrary.getFrameworkLabel(turn.step) || turn.step)}"
              >${this.escapeHtml(turn.content)}</textarea>
              ${turn.note ? `<p class="test-dialogue-note">💡 ${this.escapeHtml(turn.note)}</p>` : ''}
            </li>
          `
            )
            .join('')}
        </ol>
      </div>

      <div class="test-grid-2">
        <div class="test-section glass">
          <h4>${I18n.t('test.expected')}</h4>
          <ul class="test-list">
            <li><strong>${I18n.t('test.domain')}:</strong> ${this.escapeHtml(TestMode.getCategoryLabel(scenario.expectedOutcomes.forestTree))}</li>
            ${scenario.expectedOutcomes.highlights.map((h) => `<li>${this.escapeHtml(h)}</li>`).join('')}
          </ul>
          ${
            scenario.expectedOutcomes.contradictions?.length
              ? `<h5 class="test-subheading">${I18n.t('test.contradictionsMay')}</h5>
                 <ul class="test-list test-list-warn">
                   ${scenario.expectedOutcomes.contradictions.map((c) => `<li>${this.escapeHtml(c)}</li>`).join('')}
                 </ul>`
              : ''
          }
        </div>

        <div class="test-section glass">
          <h4>${I18n.t('test.learning')}</h4>
          <ul class="test-list">
            ${scenario.learningPoints.map((p) => `<li>${this.escapeHtml(p)}</li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  },

  collectTestDialogueEdits(scenarioId) {
    const scenario = TestMode.getScenario(scenarioId);
    if (!scenario) return null;

    const dialogue = scenario.dialogue.map((turn, i) => {
      const input = document.querySelector(
        `#test-scenario-detail .test-dialogue-input[data-dialogue-index="${i}"]`
      );
      const content = input ? input.value.trim() : turn.content;
      return { ...turn, content };
    });

    TestMode.setDialogueEdits(scenarioId, dialogue);
    return dialogue;
  },

  initTestSimSteps(dialogue) {
    const stepsEl = document.getElementById('test-sim-steps');
    if (!stepsEl) return;

    stepsEl.innerHTML = dialogue
      .map((turn, i) => {
        const label = CognitiveLibrary.getFrameworkLabel(turn.step) || turn.step;
        return `<span class="test-sim-step-pill" data-sim-step="${i}" title="${this.escapeAttr(label)}">${i + 1}. ${this.escapeHtml(label)}</span>`;
      })
      .join('');
  },

  updateTestSimProgress(progress) {
    const statusEl = document.getElementById('test-sim-status');
    const progressEl = document.getElementById('test-sim-progress');
    if (!statusEl || !progressEl) return;

    const pct = Math.round((progress.completedSteps / progress.totalSteps) * 100);
    progressEl.style.width = `${pct}%`;

    const stepLabel =
      CognitiveLibrary.getFrameworkLabel(progress.currentTurn?.step) ||
      progress.currentTurn?.step ||
      '';
    statusEl.textContent = I18n.t('test.stepProgress', {
      current: progress.completedSteps,
      total: progress.totalSteps,
      step: stepLabel,
    });

    document.querySelectorAll('.test-sim-step-pill').forEach((pill, idx) => {
      pill.classList.remove('active', 'done');
      if (idx < progress.completedSteps) pill.classList.add('done');
      if (idx === progress.completedSteps - 1) pill.classList.add('active');
    });

    document.querySelectorAll('#test-dialogue-list .test-dialogue-item').forEach((item, idx) => {
      item.classList.remove('test-dialogue-item--active', 'test-dialogue-item--done');
      if (idx < progress.completedSteps) item.classList.add('test-dialogue-item--done');
      if (idx === progress.completedSteps - 1) {
        item.classList.add('test-dialogue-item--active');
        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  },

  clearTestSimUI() {
    const bar = document.getElementById('test-sim-bar');
    const column = document.getElementById('test-main-column');
    const progressEl = document.getElementById('test-sim-progress');
    const stepsEl = document.getElementById('test-sim-steps');

    if (bar) {
      bar.hidden = true;
      bar.classList.remove('test-sim-bar--done');
    }
    column?.classList.remove('is-simulating');
    if (progressEl) progressEl.style.width = '0%';
    if (stepsEl) stepsEl.replaceChildren();

    document.querySelectorAll('#test-dialogue-list .test-dialogue-item').forEach((item) => {
      item.classList.remove('test-dialogue-item--active', 'test-dialogue-item--done');
    });
  },

  showTestSimDone(result) {
    const bar = document.getElementById('test-sim-bar');
    const statusEl = document.getElementById('test-sim-status');
    const progressEl = document.getElementById('test-sim-progress');
    const column = document.getElementById('test-main-column');

    column?.classList.remove('is-simulating');
    bar?.classList.add('test-sim-bar--done');
    if (progressEl) progressEl.style.width = '100%';

    document.querySelectorAll('.test-sim-step-pill').forEach((pill) => {
      pill.classList.remove('active');
      pill.classList.add('done');
    });
    document.querySelectorAll('#test-dialogue-list .test-dialogue-item').forEach((item) => {
      item.classList.remove('test-dialogue-item--active');
      item.classList.add('test-dialogue-item--done');
    });

    if (statusEl) {
      statusEl.textContent = I18n.t('test.simDone', {
        entries: result.stats.total,
        contradictions: result.insights.contradictions.length,
      });
    }
  },

  async runTestSimulation(scenarioId, options = {}) {
    if (TestMode.isSimulating) return;

    this.collectTestDialogueEdits(scenarioId);
    const dialogue = TestMode.getEffectiveDialogue(scenarioId);

    const bar = document.getElementById('test-sim-bar');
    const column = document.getElementById('test-main-column');
    const statusEl = document.getElementById('test-sim-status');
    const progressEl = document.getElementById('test-sim-progress');

    this.initTestSimSteps(dialogue);
    bar.hidden = false;
    bar.classList.remove('test-sim-bar--done');
    column?.classList.add('is-simulating');
    statusEl.textContent = I18n.t('test.simulating');
    progressEl.style.width = '0%';
    bar.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    try {
      const result = await TestMode.runSimulation(scenarioId, {
        reset: options.reset !== false,
        delayMs: options.delayMs ?? 500,
        backup: options.backup !== false,
        dialogue,
        onProgress: (p) => this.updateTestSimProgress(p),
      });

      if (result.aborted) {
        this.clearTestSimUI();
        this.showToast(I18n.t('test.simStopped'));
        return;
      }

      this.showTestSimDone(result);
      this.activeSessionId = result.sessionId;
      this.showToast(
        I18n.t('test.simDone', {
          entries: result.stats.total,
          contradictions: result.insights.contradictions.length,
        })
      );
      this.renderHomeStats();
      await new Promise((resolve) => setTimeout(resolve, 1400));
      this.clearTestSimUI();
      this.navigate('reflection');
    } catch (err) {
      this.clearTestSimUI();
      this.showToast(err.message || I18n.t('test.simFailed'));
    }
  },

  // ─── Utilities ───

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  },

  escapeAttr(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  },

  formatDate(iso) {
    return I18n.localeDate(iso);
  },
};

// Khởi chạy khi DOM ready
document.addEventListener('DOMContentLoaded', () => App.init());

// Export cho debug / mở rộng
if (typeof window !== 'undefined') {
  window.App = App;
}
