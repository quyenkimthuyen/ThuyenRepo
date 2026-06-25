const App = {
  state: null,
  currentEvent: null,
  pendingChoice: null,
  awaitingReflection: false,

  init() {
    this.bindEvents();
    if (SaveLoad.hasSave()) {
      document.getElementById('btn-continue').style.display = 'block';
    }
  },

  bindEvents() {
    document.getElementById('btn-start').addEventListener('click', () => this.startNew());
    document.getElementById('btn-continue').addEventListener('click', () => this.continueGame());
    document.getElementById('btn-save').addEventListener('click', () => this.saveGame());
    document.getElementById('btn-new').addEventListener('click', () => {
      if (confirm('Bắt đầu game mới? Tiến trình hiện tại sẽ bị xóa.')) {
        SaveLoad.clear();
        this.startNew();
      }
    });
    document.getElementById('btn-reflect').addEventListener('click', () => this.submitReflection());
  },

  startNew() {
    this.state = GameState.createNew();
    this.showGame();
    this.nextEvent();
    SaveLoad.save(this.state);
  },

  continueGame() {
    const loaded = SaveLoad.load();
    if (loaded) {
      this.state = loaded;
      this.showGame();
      this.renderAll();
      this.nextEvent();
    }
  },

  showGame() {
    document.getElementById('welcome-screen').style.display = 'none';
    document.getElementById('game-screen').style.display = 'block';
  },

  nextEvent() {
    this.awaitingReflection = false;
    document.getElementById('reflection-panel').style.display = 'none';
    this.currentEvent = EventEngine.getRandomEvent(this.state);
    this.renderEvent();
    this.enableChoices(true);
  },

  renderEvent() {
    const event = this.currentEvent;
    document.getElementById('event-category').textContent =
      EventEngine.getCategoryLabel(event.category);
    document.getElementById('event-text').textContent = event.text;

    const choicesEl = document.getElementById('choices');
    choicesEl.innerHTML = event.choices.map((choice) => `
      <button class="choice-btn" data-choice-id="${choice.id}">
        <span class="choice-id">${choice.id}</span>
        <span>${choice.text}</span>
      </button>
    `).join('');

    choicesEl.querySelectorAll('.choice-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const choiceId = btn.dataset.choiceId;
        const choice = event.choices.find((c) => c.id === choiceId);
        this.onChoiceSelected(choice);
      });
    });
  },

  onChoiceSelected(choice) {
    this.enableChoices(false);
    this.pendingChoice = choice;

    DecisionEngine.makeDecision(this.state, this.currentEvent, choice);

    this.renderAll();
    this.showReflection(choice);
    SaveLoad.save(this.state);
  },

  showReflection(choice) {
    this.awaitingReflection = true;
    const panel = document.getElementById('reflection-panel');
    panel.style.display = 'block';

    const question = AICoach.getQuestion(this.state, choice);
    document.getElementById('coach-question').textContent = question;
    document.getElementById('reflection-input').value = '';
    document.getElementById('reflection-input').focus();
  },

  submitReflection() {
    const reflection = document.getElementById('reflection-input').value.trim();
    const lastIdx = this.state.decisions.length - 1;

    if (reflection) {
      DecisionEngine.setReflection(this.state, lastIdx, reflection);
      const followUp = AICoach.getFollowUp(reflection);
      this.showToast(followUp);
    }

    if (PersonalityAnalyzer.shouldGenerateReport(this.state)) {
      this.showReport();
    }

    SaveLoad.save(this.state);
    this.nextEvent();
  },

  showReport() {
    const report = PersonalityAnalyzer.generateReport(this.state);
    const panel = document.getElementById('report-panel');
    panel.style.display = 'block';

    document.getElementById('report-content').innerHTML = `
      <div class="report-title">${report.title}</div>
      <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.5rem">Bạn thường:</p>
      <ul class="report-list">
        ${report.lines.map((line) => `<li>${line}</li>`).join('')}
      </ul>
    `;

    GameState.addTimelineEntry(this.state, {
      type: 'report',
      message: `Báo cáo phản tỉnh: ${report.lines.join('; ')}`
    });

    this.showToast('Báo cáo phản tỉnh mới đã sẵn sàng');
  },

  enableChoices(enabled) {
    document.querySelectorAll('.choice-btn').forEach((btn) => {
      btn.disabled = !enabled;
    });
  },

  renderAll() {
    this.renderDashboard();
    TimelineModule.render(
      document.getElementById('timeline'),
      this.state.timeline
    );
    this.renderInsights();
    document.getElementById('day-display').textContent = `Ngày ${this.state.day}`;
  },

  renderDashboard() {
    const c = this.state.character;
    const stats = ['health', 'wealth', 'happiness', 'knowledge', 'relationships'];

    stats.forEach((stat) => {
      const val = c[stat];
      document.getElementById(`val-${stat}`).textContent = val;
      const bar = document.getElementById(`bar-${stat}`);
      bar.style.width = `${Math.min(100, val)}%`;
    });

    document.getElementById('val-energy').textContent = c.energy;
    document.getElementById('val-age').textContent = c.age;
  },

  renderInsights() {
    const insights = PersonalityAnalyzer.getInsights(this.state);
    const container = document.getElementById('insights');

    if (this.state.personality.total === 0) {
      container.innerHTML = '<p class="empty-state">Đưa ra quyết định để xem xu hướng hành vi.</p>';
      return;
    }

    container.innerHTML = insights.map((item) => `
      <div class="insight-bar">
        <div class="insight-label">
          <span>${item.label}</span>
          <span>${item.value}%</span>
        </div>
        <div class="insight-track">
          <div class="insight-fill" style="width:${item.value}%"></div>
        </div>
      </div>
    `).join('');
  },

  saveGame() {
    if (SaveLoad.save(this.state)) {
      this.showToast('Đã lưu tiến trình');
    }
  },

  showToast(message) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
