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

  /**
   * Khởi tạo ứng dụng
   */
  init() {
    DataStore.load();
    this.bindEvents();
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
    document.getElementById('suggestions-list').addEventListener('click', (e) => {
      const chip = e.target.closest('.suggestion-chip');
      if (!chip) return;
      const text = chip.dataset.text;
      if (!text) return;
      const input = document.getElementById('chat-input');
      input.value = text;
      input.focus();
      this.sendChatMessage();
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
    if (!el) return;

    el.innerHTML = `
      <div class="stat-item">
        <div class="stat-value">${stats.total}</div>
        <div class="stat-label">Nodes</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${stats.byStatus?.verified || 0}</div>
        <div class="stat-label">Xác nhận</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${DataStore.getSessions().length}</div>
        <div class="stat-label">Phiên suy ngẫm</div>
      </div>
    `;
  },

  startReflection() {
    const input = document.getElementById('home-thought-input');
    const thought = input.value.trim();

    if (!thought) {
      this.showToast('Hãy chia sẻ suy nghĩ của bạn trước.');
      input.focus();
      return;
    }

    const { session } = ReflectionEngine.createSession(thought);
    this.activeSessionId = session.id;
    input.value = '';

    this.showToast('Đã bắt đầu phiên suy ngẫm');
    this.navigate('reflection');
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
    document.getElementById('chat-messages').innerHTML = `
      <div class="insight-empty" style="text-align:center;padding:2rem;">
        Chưa có phiên suy ngẫm nào.<br>
        Hãy bắt đầu từ trang Home.
      </div>
    `;
    document.getElementById('flow-indicator').innerHTML = '';
    document.getElementById('session-timeline-steps').innerHTML = '';
    document.getElementById('chat-suggestions').hidden = true;
    document.getElementById('suggestions-list').innerHTML = '';
  },

  renderReflectionSuggestions(session) {
    const container = document.getElementById('chat-suggestions');
    const list = document.getElementById('suggestions-list');
    const suggestions = ReflectionEngine.getSuggestions(session);

    if (!suggestions.length) {
      container.hidden = true;
      list.innerHTML = '';
      return;
    }

    container.hidden = false;
    list.innerHTML = suggestions
      .map(
        (text) => `
          <button
            type="button"
            class="suggestion-chip"
            data-text="${this.escapeAttr(text)}"
            role="option"
            title="Chọn câu trả lời này"
          >${this.escapeHtml(text)}</button>
        `
      )
      .join('');
  },

  renderFlowIndicator(currentStep) {
    const flow = CognitiveLibrary.REFLECTION_FLOW;
    const currentIdx = flow.indexOf(currentStep);

    const html = flow
      .map((step, idx) => {
        let cls = 'flow-step';
        if (idx === currentIdx) cls += ' active';
        else if (idx < currentIdx) cls += ' done';
        return `<span class="${cls}">${step}</span>`;
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
        return `<div class="${cls}">${icon} ${step}</div>`;
      })
      .join('');

    document.getElementById('session-timeline-steps').innerHTML = html;
  },

  renderChatMessages(session) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = session.messages
      .map((msg) => {
        const isUser = msg.role === 'user';
        const time = new Date(msg.timestamp).toLocaleTimeString('vi-VN', {
          hour: '2-digit',
          minute: '2-digit',
        });
        return `
          <div class="message message-${isUser ? 'user' : 'guide'}">
            ${this.escapeHtml(msg.content)}
            <div class="message-meta">${isUser ? 'Bạn' : 'Reflection Guide'} · ${time}</div>
          </div>
        `;
      })
      .join('');

    container.scrollTop = container.scrollHeight;
  },

  sendChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();

    if (!text || !this.activeSessionId) return;

    const result = ReflectionEngine.continueSession(this.activeSessionId, text);
    if (!result) return;

    input.value = '';
    this.renderReflection();
    this.renderHomeStats();
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
        const statusLabels = {
          seed: 'Hạt giống',
          sprouting: 'Nảy mầm',
          growing: 'Đang lớn',
          flourishing: 'Thịnh vượng',
        };

        return `
          <div class="tree-card glass" data-tree="${tree.id}" role="button" tabindex="0">
            <span class="tree-icon">${tree.icon}</span>
            <div class="tree-name">${tree.label}</div>
            <div class="tree-meta">${nodes.length} nodes</div>
            <div class="tree-growth">
              <div class="tree-growth-bar" style="width:${growth}%"></div>
            </div>
            <span class="tree-status status-${status}">${statusLabels[status]}</span>
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
    document.getElementById('forest-detail-title').textContent = `${tree.icon} ${tree.label}`;

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
          ${t === 'all' ? 'Tất cả' : t}
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
      grid.innerHTML = `<div class="insight-empty">Chưa có node nào trong cây này. Hãy bắt đầu suy ngẫm!</div>`;
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
    const statusLabel = { draft: 'Nháp', candidate: 'Ứng viên', verified: 'Xác nhận' }[node.status];

    return `
      <div class="node-card glass" data-node-id="${node.id}"
           style="background:${colors.bg};border-left-color:${colors.border}">
        <div class="node-type" style="color:${colors.text}">${node.type}</div>
        <div class="node-label">${this.escapeHtml(node.label)}</div>
        <div class="node-footer">
          <span class="node-status status-${node.status}">${statusLabel}</span>
          <div class="confidence-bar" title="Confidence: ${node.confidence}">
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
        ${node.type}
      </span>
      <div class="modal-label">${this.escapeHtml(node.label)}</div>
      <div class="modal-detail-row"><span>Trạng thái</span><span>${node.status}</span></div>
      <div class="modal-detail-row"><span>Confidence</span><span>${Math.round(node.confidence * 100)}%</span></div>
      <div class="modal-detail-row"><span>Xuất hiện</span><span>${node.occurrences} lần</span></div>
      <div class="modal-detail-row"><span>Cây</span><span>${this.getForestLabel(node.category)}</span></div>
      <div class="modal-detail-row"><span>Tạo lúc</span><span>${this.formatDate(node.createdAt)}</span></div>
      <div class="modal-detail-row"><span>Cập nhật</span><span>${this.formatDate(node.updatedAt)}</span></div>
      ${
        relations.length > 0
          ? `<div style="margin-top:1rem;font-size:0.85rem;color:var(--text-secondary)">
              ${relations.length} quan hệ liên kết
            </div>`
          : ''
      }
    `;

    modal.showModal();
  },

  getForestLabel(id) {
    const tree = CognitiveLibrary.FOREST_TREES.find((t) => t.id === id);
    return tree ? tree.label : id;
  },

  // ─── INSIGHTS ───

  renderInsights() {
    const insights = InsightEngine.analyze();
    DataStore.setInsights(insights);

    const grid = document.getElementById('insights-grid');

    grid.innerHTML = `
      ${this.renderInsightSection(
        '🔍 Khám phá hôm nay',
        insights.todayDiscoveries.length > 0
          ? insights.todayDiscoveries
              .map(
                (d) => `
              <div class="insight-item">
                <span class="insight-rank">${d.isNew ? 'MỚI' : '↑'}</span>
                <strong>${d.type}</strong>: ${this.escapeHtml(d.label)}
                <span class="occurrence-badge">${d.status}</span>
              </div>
            `
              )
              .join('')
          : '<div class="insight-empty">Chưa có khám phá hôm nay. Hãy bắt đầu suy ngẫm!</div>'
      )}

      ${this.renderInsightSection(
        '💡 Niềm tin nổi bật',
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
          : '<div class="insight-empty">Chưa có niềm tin được ghi nhận.</div>'
      )}

      ${this.renderInsightSection(
        '🌟 Giá trị nổi bật',
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
          : '<div class="insight-empty">Chưa có giá trị được ghi nhận.</div>'
      )}

      ${this.renderInsightSection(
        '⚡ Mâu thuẫn nhận thức',
        insights.contradictions.length > 0
          ? insights.contradictions
              .map(
                (c) => `
              <div class="insight-item ${c.severity === 'high' ? 'danger' : 'warning'}">
                ${this.escapeHtml(c.message)}
              </div>
            `
              )
              .join('')
          : '<div class="insight-empty">Chưa phát hiện mâu thuẫn. Tiếp tục suy ngẫm để hệ thống học thêm.</div>',
        insights.contradictions.length > 0 ? 'warning' : ''
      )}

      ${this.renderInsightSection(
        '🧩 Thiên kiến nhận thức',
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
          : '<div class="insight-empty">Chưa phát hiện thiên kiến. Hệ thống sẽ phân tích khi có thêm dữ liệu.</div>'
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
          Timeline sẽ hiển thị khi bạn bắt đầu suy ngẫm và xây dựng cây nhận thức.
        </div>
      `;
      return;
    }

    let html = '';

    // Narrative shifts (Value/Belief theo năm)
    if (narrative.length > 0) {
      html += '<div class="timeline-year-group"><h3 class="timeline-year">Hành trình nhận thức</h3>';
      for (const entry of narrative) {
        if (entry.value) {
          html += `
            <div class="timeline-event glass">
              <div class="timeline-event-title">${entry.year} — Value: ${this.escapeHtml(entry.value.label)}</div>
              <div class="timeline-event-desc">Xuất hiện ${entry.value.occurrences} lần · ${entry.value.status}</div>
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
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('vi-VN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  },
};

// Khởi chạy khi DOM ready
document.addEventListener('DOMContentLoaded', () => App.init());

// Export cho debug / mở rộng
if (typeof window !== 'undefined') {
  window.App = App;
}
