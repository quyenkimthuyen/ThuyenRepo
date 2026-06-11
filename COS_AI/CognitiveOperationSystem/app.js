/**
 * Cognitive OS — Main Application
 *
 * Điều phối 5 màn hình: Home, Reflection, Forest, Insights, Timeline
 * Mở rộng: thay ReflectionEngine bằng API client (OpenAI/Cursor)
 */

const App = {
  currentScreen: 'home',
  activeSessionId: null,
  selectedForestTree: null,
  nodeFilter: 'all',
  isReflecting: false,

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
      this.renderAiSettings();
      this.navigate(this.currentScreen);
    });
    this.renderHomeStats();
    this.renderAiSettings();
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

    document.querySelectorAll('input[name="reflection-mode"]').forEach((input) => {
      input.addEventListener('change', () => {
        if (!input.checked) return;
        AiClient.setMode(input.value);
        this.renderAiSettings();
        this.renderReflectionModeBadge();
      });
    });

    document.getElementById('ai-proxy-url').addEventListener('change', (e) => {
      AiClient.setProxyUrl(e.target.value);
      this.setAiStatus('unknown');
    });

    document.getElementById('btn-ai-test').addEventListener('click', () => {
      this.testAiConnection();
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

    document.getElementById('btn-crisis-understood').addEventListener('click', () => {
      document.getElementById('crisis-modal').close();
    });

    // Test mode — chọn kịch bản & hành động
    document.getElementById('test-scenario-list').addEventListener('click', (e) => {
      const card = e.target.closest('.test-scenario-card');
      if (card) {
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
        this.renderAiSettings();
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

  async startReflection() {
    const input = document.getElementById('home-thought-input');
    const thought = input.value.trim();

    if (!thought) {
      this.showToast(I18n.t('home.shareFirst'));
      input.focus();
      return;
    }

    if (this.checkCrisisAndShow(thought)) return;
    if (this.isReflecting) return;

    this.setReflecting(true);
    try {
      const { session } = await ReflectionEngine.createSession(thought);
      this.activeSessionId = session.id;
      input.value = '';
      this.showToast(I18n.t('home.sessionStarted'));
      this.navigate('reflection');
    } catch (err) {
      this.showToast(err.message || I18n.t('ai.testFail'));
    } finally {
      this.setReflecting(false);
    }
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
    this.renderReflectionModeBadge();
  },

  renderEmptyReflection() {
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
        return `
          <div class="message message-${isUser ? 'user' : 'guide'}">
            ${this.escapeHtml(msg.content)}
            <div class="message-meta">${isUser ? I18n.t('reflection.you') : I18n.t('reflection.guide')} · ${time}</div>
          </div>
        `;
      })
      .join('');

    container.scrollTop = container.scrollHeight;
  },

  async sendChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();

    if (!text || !this.activeSessionId || this.isReflecting) return;

    if (this.checkCrisisAndShow(text)) return;

    this.setReflecting(true);
    try {
      const result = await ReflectionEngine.continueSession(this.activeSessionId, text);
      if (!result) return;

      if (result.aiFallback) {
        this.showToast(I18n.t('ai.fallbackRule'));
      }

      input.value = '';
      this.renderReflection();
      this.renderHomeStats();
    } catch (err) {
      this.showToast(err.message || I18n.t('ai.testFail'));
    } finally {
      this.setReflecting(false);
    }
  },

  setReflecting(active) {
    this.isReflecting = active;
    const form = document.getElementById('chat-form');
    const sendBtn = form?.querySelector('.btn-send');
    const skipBtn = document.getElementById('btn-skip-step');
    const chatInput = document.getElementById('chat-input');
    if (sendBtn) sendBtn.disabled = active;
    if (skipBtn) skipBtn.disabled = active;
    if (chatInput) chatInput.disabled = active;
    form?.classList.toggle('is-loading', active);
  },

  renderAiSettings() {
    const settings = AiClient.getSettings();
    const mode = settings.reflectionMode;

    document.querySelectorAll('input[name="reflection-mode"]').forEach((input) => {
      input.checked = input.value === mode;
    });

    const proxyRow = document.getElementById('ai-proxy-row');
    const proxyInput = document.getElementById('ai-proxy-url');
    if (proxyRow) proxyRow.hidden = mode !== 'cursor';
    if (proxyInput) proxyInput.value = settings.cursorProxyUrl;

    this.setAiStatus('unknown', I18n.t('ai.statusUnknown'));
    this.renderReflectionModeBadge();
  },

  renderReflectionModeBadge() {
    const el = document.getElementById('reflection-mode-badge');
    if (!el) return;

    if (!AiClient.isEnabled()) {
      el.hidden = true;
      return;
    }

    el.hidden = false;
    el.textContent = I18n.t('ai.badgeCursor');
    el.className = 'reflection-mode-badge mode-cursor';
  },

  setAiStatus(status, label) {
    const pill = document.getElementById('ai-status-pill');
    if (!pill) return;
    pill.dataset.status = status;
    pill.textContent = label || I18n.t(`ai.status${status.charAt(0).toUpperCase()}${status.slice(1)}`);
  },

  async testAiConnection() {
    this.setAiStatus('checking', I18n.t('ai.statusChecking'));
    try {
      const health = await AiClient.checkHealth();
      if (health.hasKey) {
        this.setAiStatus('ok', I18n.t('ai.statusOk'));
        this.showToast(I18n.t('ai.testOk'));
      } else {
        this.setAiStatus('noKey', I18n.t('ai.statusNoKey'));
        this.showToast(I18n.t('ai.statusNoKey'));
      }
    } catch {
      this.setAiStatus('error', I18n.t('ai.statusError'));
      this.showToast(I18n.t('ai.testFail'));
    }
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

    grid.innerHTML = `
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
                ${this.escapeHtml(I18n.formatContradiction(c.message))}
              </div>
            `
              )
              .join('')
          : `<div class="insight-empty">${I18n.t('insights.contradictionsEmpty')}</div>`,
        insights.contradictions.length > 0 ? 'warning' : ''
      )}

      ${this.renderInsightSection(
        I18n.t('insights.biases'),
        insights.biases.length > 0
          ? insights.biases
              .map(
                (b) => `
              <div class="insight-item">
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
        <h4>${I18n.t('test.dialogue')}</h4>
        <p class="test-muted">${I18n.t('test.dialogueHint')}</p>
        <ol class="test-dialogue-list">
          ${scenario.dialogue
            .map(
              (turn, i) => `
            <li class="test-dialogue-item">
              <div class="test-dialogue-step">
                <span class="test-step-num">${i + 1}</span>
                <span class="test-step-label">${this.escapeHtml(CognitiveLibrary.getFrameworkLabel(turn.step) || turn.step)}</span>
              </div>
              <p class="test-dialogue-content">${this.escapeHtml(turn.content)}</p>
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

  async runTestSimulation(scenarioId, options = {}) {
    if (TestMode.isSimulating) return;

    const bar = document.getElementById('test-sim-bar');
    const statusEl = document.getElementById('test-sim-status');
    const progressEl = document.getElementById('test-sim-progress');

    bar.hidden = false;
    statusEl.textContent = I18n.t('test.simulating');
    progressEl.style.width = '0%';

    try {
      const result = await TestMode.runSimulation(scenarioId, {
        reset: true,
        delayMs: options.delayMs ?? 500,
        backup: true,
        onProgress: (p) => {
          const pct = Math.round((p.completedSteps / p.totalSteps) * 100);
          progressEl.style.width = `${pct}%`;
          const stepLabel = CognitiveLibrary.getFrameworkLabel(p.currentTurn?.step) || p.currentTurn?.step || '';
          statusEl.textContent = I18n.t('test.stepProgress', {
            current: p.completedSteps,
            total: p.totalSteps,
            step: stepLabel,
          });
        },
      });

      bar.hidden = true;

      if (result.aborted) {
        this.showToast(I18n.t('test.simStopped'));
        return;
      }

      this.activeSessionId = result.sessionId;
      this.showToast(
        I18n.t('test.simDone', {
          entries: result.stats.total,
          contradictions: result.insights.contradictions.length,
        })
      );
      this.renderHomeStats();
      this.navigate('reflection');
    } catch (err) {
      bar.hidden = true;
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
