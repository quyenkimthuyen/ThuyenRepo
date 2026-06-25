/**
 * Cognitive Mirror: Life Journey — Main Application
 */
const App = (() => {
  const I18N = {
    vi: {
      appTitle: 'Cognitive Mirror',
      appSubtitle: 'Hành trình Cuộc đời',
      loading: 'Đang tải hành trình...',
      loadError: 'Không thể tải dữ liệu. Hãy chạy qua local server.',
      navJourney: 'Hành trình',
      navDashboard: 'Bảng điều khiển',
      navTimeline: 'Dòng thời gian',
      navSimulation: 'Mô phỏng tương lai',
      footer: 'Gương nhận thức — giúp bạn nhìn thấy khuôn mẫu tư duy của chính mình.',
      welcomeTitle: 'Chào mừng đến với Gương Nhận Thức',
      welcomeDesc: 'Ứng dụng này không phải game, không phải self-help. Đây là một gương giúp bạn nhìn thấy cách bạn nghĩ, phản ứng và diễn giải sự kiện.',
      welcomeNot: 'Không phải công cụ năng suất. Không phải therapy. Không phán xét đúng/sai.',
      welcomePhilosophy: ['Giai đoạn đời', 'Sự kiện', 'Diễn giải', 'Cảm xúc', 'Quyết định', 'Kết quả', 'Suy ngẫm', 'Nhận diện khuôn mẫu'],
      selectStage: 'Chọn giai đoạn cuộc đời hiện tại của bạn',
      stageFocus: 'Trọng tâm',
      eventsAvailable: 'sự kiện',
      eventsRemaining: 'sự kiện chưa khám phá',
      changeStage: 'Đổi giai đoạn',
      startEvent: 'Bắt đầu sự kiện mới',
      stepEvent: 'Sự kiện',
      stepThought: 'Suy nghĩ',
      stepEmotion: 'Cảm xúc',
      stepDecision: 'Quyết định',
      stepOutcome: 'Kết quả',
      stepThoughtQ: 'Suy nghĩ đầu tiên của bạn là gì?',
      stepThoughtHint: 'Viết tự do — không có đúng hay sai. Điều quan trọng nhất là cách bạn diễn giải sự kiện.',
      liveHints: 'Gợi ý ngôn ngữ phát hiện',
      stepEmotionQ: 'Bạn cảm thấy thế nào?',
      stepEmotionCustom: 'Hoặc mô tả cảm xúc khác:',
      stepDecisionQ: 'Bạn sẽ làm gì tiếp theo?',
      stepDecisionCustom: 'Mô tả quyết định của bạn:',
      stepConsequence: 'Hệ quả',
      immediate: 'Ngay lập tức',
      later: 'Sau đó',
      stepReflection: 'Suy ngẫm',
      reflectLearned: 'Bạn học được gì?',
      reflectDifferent: 'Bạn có làm khác đi không?',
      reflectSurprised: 'Điều gì khiến bạn ngạc nhiên?',
      finish: 'Hoàn thành',
      next: 'Tiếp theo',
      back: 'Quay lại',
      completeTitle: 'Đã ghi nhận hành trình',
      completeDesc: 'Dữ liệu quan trọng nhất là cách bạn diễn giải — không phải quyết định.',
      viewDashboard: 'Xem bảng điều khiển',
      continueJourney: 'Tiếp tục hành trình',
      profileChanged: 'Thay đổi hồ sơ tư duy',
      dashRadar: 'Biểu đồ tư duy',
      dashProfile: 'Hồ sơ tư duy',
      dashEmotion: 'Phân bố cảm xúc',
      dashEmotionTrend: 'Xu hướng cảm xúc theo thời gian',
      dashPatterns: 'Phân tích khuôn mẫu ngôn ngữ',
      dashPhrases: 'Cụm từ thường gặp',
      dashMirror: 'Gương nhận thức',
      dashMap: 'Bản đồ hành trình',
      mirrorDisclaimer: 'Gương này không phải huấn luyện viên. Không đưa lời khuyên. Không phán xét. Chỉ phản chiếu khuôn mẫu.',
      timelineTitle: 'Dòng thời gian cuộc đời',
      timelineEmpty: 'Chưa có sự kiện nào. Bắt đầu hành trình để xây dựng dòng thời gian.',
      filterAll: 'Tất cả giai đoạn',
      simTitle: 'Mô phỏng tương lai',
      simDesc: 'Khám phá các giai đoạn cuộc đời khác để hiểu trách nhiệm và thử thách trong tương lai — không cần đúng tuổi thực tế.',
      simStart: 'Mô phỏng giai đoạn này',
      simActive: 'Đang mô phỏng',
      simExit: 'Thoát mô phỏng',
      simulation: 'Mô phỏng',
      currentStage: 'Giai đoạn hiện tại',
      noPatterns: 'Chưa đủ dữ liệu để phân tích.',
      chainStage: 'Giai đoạn',
      chainEvent: 'Sự kiện',
      chainThought: 'Suy nghĩ',
      chainEmotion: 'Cảm xúc',
      chainDecision: 'Quyết định',
      chainOutcome: 'Kết quả',
      chainReflection: 'Suy ngẫm',
      chainPatterns: 'Khuôn mẫu nhận diện',
      ownership: 'Chủ động',
      growth: 'Phát triển',
      victim: 'Nạn nhân',
      resilience: 'Kiên cường',
      optimism: 'Lạc quan',
      emotional_stability: 'Ổn định cảm xúc',
      self_awareness: 'Tự nhận thức',
      pattern_ownership: 'Tư duy chủ động',
      pattern_growth: 'Tư duy phát triển',
      pattern_victim: 'Tư duy nạn nhân',
      pattern_fixed: 'Tư duy cố định',
      pattern_catastrophic: 'Suy nghĩ thảm họa',
      pattern_opportunity: 'Tư duy cơ hội',
      pattern_fear: 'Ngôn ngữ sợ hãi',
      entries: 'mục',
      statEntries: 'Sự kiện đã ghi',
      statDays: 'Ngày hoạt động',
      statExplored: 'Sự kiện đã khám phá',
      statSimulated: 'Mô phỏng',
      settingsTitle: 'Cài đặt & Dữ liệu',
      settingsAbout: 'Dữ liệu được lưu cục bộ trên thiết bị của bạn. Ứng dụng hoạt động offline. Gương nhận thức chỉ phản chiếu — không thay thế tư vấn chuyên nghiệp.',
      exportData: 'Xuất dữ liệu (JSON)',
      importData: 'Nhập dữ liệu',
      resetData: 'Xóa toàn bộ dữ liệu',
      resetConfirm: 'Bạn có chắc muốn xóa toàn bộ hành trình?',
      close: 'Đóng',
      importSuccess: 'Nhập dữ liệu thành công!',
      importError: 'File không hợp lệ.',
    },
    en: {
      appTitle: 'Cognitive Mirror',
      appSubtitle: 'Life Journey',
      loading: 'Loading your journey...',
      loadError: 'Could not load data. Please run via a local server.',
      navJourney: 'Journey',
      navDashboard: 'Dashboard',
      navTimeline: 'Timeline',
      navSimulation: 'Future Simulation',
      footer: 'A cognitive mirror — helping you see your own thinking patterns.',
      welcomeTitle: 'Welcome to Cognitive Mirror',
      welcomeDesc: 'This is not a game, not self-help. It is a mirror that helps you see how you think, react, and interpret events.',
      welcomeNot: 'Not a productivity tool. Not therapy. No right/wrong judgments.',
      welcomePhilosophy: ['Life Stage', 'Event', 'Interpretation', 'Emotion', 'Decision', 'Outcome', 'Reflection', 'Pattern Recognition'],
      selectStage: 'Select your current life stage',
      stageFocus: 'Focus',
      eventsAvailable: 'events',
      eventsRemaining: 'events not yet explored',
      changeStage: 'Change stage',
      startEvent: 'Start new event',
      stepEvent: 'Event',
      stepThought: 'Thought',
      stepEmotion: 'Emotion',
      stepDecision: 'Decision',
      stepOutcome: 'Outcome',
      stepThoughtQ: 'What is your first thought?',
      stepThoughtHint: 'Write freely — there is no right or wrong. Your interpretation matters most.',
      liveHints: 'Language patterns detected',
      stepEmotionQ: 'How do you feel?',
      stepEmotionCustom: 'Or describe another emotion:',
      stepDecisionQ: 'What would you do next?',
      stepDecisionCustom: 'Describe your decision:',
      stepConsequence: 'Consequences',
      immediate: 'Immediate',
      later: 'Later',
      stepReflection: 'Reflection',
      reflectLearned: 'What did you learn?',
      reflectDifferent: 'Would you do anything differently?',
      reflectSurprised: 'What surprised you?',
      finish: 'Finish',
      next: 'Next',
      back: 'Back',
      completeTitle: 'Journey recorded',
      completeDesc: 'The most important data is your interpretation — not the decision itself.',
      viewDashboard: 'View dashboard',
      continueJourney: 'Continue journey',
      profileChanged: 'Thinking profile changes',
      dashRadar: 'Thinking Radar',
      dashProfile: 'Thinking Profile',
      dashEmotion: 'Emotion Distribution',
      dashEmotionTrend: 'Emotion Trends Over Time',
      dashPatterns: 'Language Pattern Analysis',
      dashPhrases: 'Most Frequent Phrases',
      dashMirror: 'AI Mirror',
      dashMap: 'Life Journey Map',
      mirrorDisclaimer: 'This mirror is not a coach. It does not give advice. It does not judge. It only reflects patterns.',
      timelineTitle: 'Life Timeline',
      timelineEmpty: 'No events yet. Start your journey to build a timeline.',
      filterAll: 'All stages',
      simTitle: 'Future Simulation',
      simDesc: 'Explore other life stages to understand future responsibilities and challenges — no need to match your actual age.',
      simStart: 'Simulate this stage',
      simActive: 'Simulating',
      simExit: 'Exit simulation',
      simulation: 'Simulation',
      currentStage: 'Current stage',
      noPatterns: 'Not enough data to analyze yet.',
      chainStage: 'Life Stage',
      chainEvent: 'Event',
      chainThought: 'Thought',
      chainEmotion: 'Emotion',
      chainDecision: 'Decision',
      chainOutcome: 'Outcome',
      chainReflection: 'Reflection',
      chainPatterns: 'Patterns detected',
      ownership: 'Ownership',
      growth: 'Growth',
      victim: 'Victim',
      resilience: 'Resilience',
      optimism: 'Optimism',
      emotional_stability: 'Emotional Stability',
      self_awareness: 'Self Awareness',
      pattern_ownership: 'Ownership thinking',
      pattern_growth: 'Growth mindset',
      pattern_victim: 'Victim mindset',
      pattern_fixed: 'Fixed mindset',
      pattern_catastrophic: 'Catastrophic thinking',
      pattern_opportunity: 'Opportunity thinking',
      pattern_fear: 'Fear language',
      entries: 'entries',
      statEntries: 'Events recorded',
      statDays: 'Active days',
      statExplored: 'Events explored',
      statSimulated: 'Simulated',
      settingsTitle: 'Settings & Data',
      settingsAbout: 'Data is stored locally on your device. The app works offline. The cognitive mirror reflects only — it does not replace professional guidance.',
      exportData: 'Export data (JSON)',
      importData: 'Import data',
      resetData: 'Delete all data',
      resetConfirm: 'Are you sure you want to delete your entire journey?',
      close: 'Close',
      importSuccess: 'Data imported successfully!',
      importError: 'Invalid file.',
    },
  };

  const STAGE_FOCUS = {
    vi: {
      1: 'Trách nhiệm, Trung thực, Đồng cảm',
      2: 'Bản sắc, Áp lực bạn bè, Lòng tự trọng',
      3: 'Kế hoạch tương lai, Xử lý thất bại, Động lực',
      4: 'Độc lập, Quản lý thời gian, Nhận thức tài chính',
      5: 'Phát triển sự nghiệp, Quyết định tài chính, Tự phát triển',
      6: 'Cân bằng, Nuôi dạy con, Trách nhiệm dài hạn',
      7: 'Ý nghĩa, Lãnh đạo, Thích nghi',
      8: 'Di sản, Suy ngẫm, Viên mãn',
    },
    en: {
      1: 'Responsibility, Honesty, Empathy',
      2: 'Identity, Peer pressure, Self-esteem',
      3: 'Future planning, Failure handling, Motivation',
      4: 'Independence, Time management, Financial awareness',
      5: 'Career growth, Financial decisions, Self-development',
      6: 'Balance, Parenting, Long-term responsibility',
      7: 'Meaning, Leadership, Adaptation',
      8: 'Legacy, Reflection, Fulfillment',
    },
  };

  const STEP_KEYS = ['stepEvent', 'stepThought', 'stepEmotion', 'stepDecision', 'stepOutcome'];

  let state = null;
  let journey = null;
  let completion = null;
  let radarChart = null;
  let emotionChart = null;
  let emotionTrendChart = null;
  let patternChart = null;
  let timelineFilter = 'all';

  function t(key) {
    const lang = state?.language || 'vi';
    return I18N[lang][key] || I18N.en[key] || key;
  }

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  async function init() {
    state = Storage.load();
    $('#loading-text').textContent = t('loading');
    try {
      await EventEngine.loadEvents();
      hideLoading();
      bindGlobalEvents();
      applyLanguage();
      showView('journey');
      renderJourney();
    } catch (err) {
      $('#loading-screen').innerHTML = `<div class="error-screen"><p>${t('loadError')}</p><p style="font-size:0.85rem;margin-top:0.5rem">${err.message}</p></div>`;
    }
  }

  function hideLoading() {
    $('#loading-screen')?.classList.add('hidden');
    $('#app')?.classList.remove('hidden');
  }

  function bindGlobalEvents() {
    $$('.nav-btn').forEach((btn) => {
      btn.addEventListener('click', () => showView(btn.dataset.view));
    });

    $$('.lang-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        state = Storage.setLanguage(state, btn.dataset.lang);
        applyLanguage();
        renderCurrentView();
      });
    });

    $('#btn-settings')?.addEventListener('click', openSettings);
    $('#settings-backdrop')?.addEventListener('click', closeSettings);
    $('#btn-close-settings')?.addEventListener('click', closeSettings);
    $('#btn-export')?.addEventListener('click', exportData);
    $('#btn-reset')?.addEventListener('click', resetData);
    $('#import-file')?.addEventListener('change', importData);
    $('#timeline-filter')?.addEventListener('change', (e) => {
      timelineFilter = e.target.value;
      renderTimeline();
    });
  }

  function openSettings() {
    $('#settings-modal')?.classList.remove('hidden');
  }

  function closeSettings() {
    $('#settings-modal')?.classList.add('hidden');
  }

  function exportData() {
    const blob = new Blob([Storage.exportData(state)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `life-journey-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function importData(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        state = Storage.importData(reader.result);
        journey = null;
        completion = null;
        closeSettings();
        applyLanguage();
        renderCurrentView();
        alert(t('importSuccess'));
      } catch {
        alert(t('importError'));
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  }

  function resetData() {
    if (!confirm(t('resetConfirm'))) return;
    state = Storage.reset();
    journey = null;
    completion = null;
    closeSettings();
    applyLanguage();
    showView('journey');
  }

  function applyLanguage() {
    const lang = state.language;
    document.documentElement.lang = lang;
    const textIds = {
      'app-title': 'appTitle', 'app-subtitle': 'appSubtitle',
      'nav-journey': 'navJourney', 'nav-dashboard': 'navDashboard',
      'nav-timeline': 'navTimeline', 'nav-simulation': 'navSimulation',
      'footer-text': 'footer',
      'dash-radar-title': 'dashRadar', 'dash-profile-title': 'dashProfile',
      'dash-emotion-title': 'dashEmotion', 'dash-emotion-trend-title': 'dashEmotionTrend',
      'dash-patterns-title': 'dashPatterns', 'dash-phrases-title': 'dashPhrases',
      'dash-mirror-title': 'dashMirror', 'dash-map-title': 'dashMap',
      'mirror-disclaimer': 'mirrorDisclaimer',
      'timeline-title': 'timelineTitle',
      'sim-title': 'simTitle', 'sim-desc': 'simDesc',
      'settings-title': 'settingsTitle', 'settings-about': 'settingsAbout',
      'btn-export': 'exportData', 'btn-import-label': 'importData',
      'btn-reset': 'resetData', 'btn-close-settings': 'close',
    };
    for (const [id, key] of Object.entries(textIds)) {
      const el = $(`#${id}`);
      if (el) el.textContent = t(key);
    }
    $$('.lang-btn').forEach((b) => b.classList.toggle('active', b.dataset.lang === lang));
    populateTimelineFilter();
  }

  function populateTimelineFilter() {
    const sel = $('#timeline-filter');
    if (!sel) return;
    const stages = EventEngine.getStages();
    const lang = state.language;
    sel.innerHTML = `<option value="all">${t('filterAll')}</option>` +
      stages.map((s) => `<option value="${s.id}">${s.name[lang]}</option>`).join('');
    sel.value = timelineFilter;
  }

  function showView(name) {
    $$('.view').forEach((v) => v.classList.remove('active'));
    $$('.nav-btn').forEach((b) => b.classList.remove('active'));
    $(`#view-${name}`)?.classList.add('active');
    $(`.nav-btn[data-view="${name}"]`)?.classList.add('active');
    renderCurrentView();
  }

  function renderCurrentView() {
    const active = $('.view.active');
    if (!active) return;
    const id = active.id.replace('view-', '');
    if (id === 'journey') renderJourney();
    else if (id === 'dashboard') renderDashboard();
    else if (id === 'timeline') renderTimeline();
    else if (id === 'simulation') renderSimulation();
  }

  function getActiveStageId() {
    return state.simulationStage || state.currentStage;
  }

  function hasActiveStage() {
    return !!(state.currentStage || state.simulationStage);
  }

  // ─── Journey ───────────────────────────────────────────────

  function renderJourney() {
    const container = $('#journey-content');
    if (!container) return;

    if (completion) {
      renderCompletion(container);
      return;
    }

    if (journey?.step) {
      renderJourneyStep(container);
      return;
    }

    if (!hasActiveStage()) {
      container.innerHTML = renderWelcome() + renderStageSelection(false);
      bindStageCards(container, false);
      return;
    }

    const stageId = getActiveStageId();
    const stages = EventEngine.getStages();
    const stage = stages.find((s) => s.id === stageId);
    const progress = EventEngine.getStageProgress(state.usedEventIds, stageId);
    const stats = Storage.getStats(state);
    const simBadge = state.simulationStage ? `<span class="sim-badge">${t('simulation')}</span>` : '';

    container.innerHTML = `
      <div class="journey-step">
        <div class="hub-stats">
          <div class="stat-card"><div class="stat-value">${stats.realEntries}</div><div class="stat-label">${t('statEntries')}</div></div>
          <div class="stat-card"><div class="stat-value">${stats.daysActive}</div><div class="stat-label">${t('statDays')}</div></div>
          <div class="stat-card"><div class="stat-value">${progress.remaining}</div><div class="stat-label">${t('eventsRemaining')}</div></div>
          <div class="stat-card"><div class="stat-value">${stats.simulatedEntries}</div><div class="stat-label">${t('statSimulated')}</div></div>
        </div>
        <div class="event-card" style="border-left-color: var(--accent)">
          <div class="category">${t('currentStage')}${simBadge}</div>
          <p><strong>${stage?.name[state.language] || ''}</strong> (${stage?.age || ''})</p>
          <p style="font-size:0.85rem;color:var(--text-muted);margin-top:0.5rem">${t('stageFocus')}: ${STAGE_FOCUS[state.language][stageId]}</p>
        </div>
        <div class="btn-group">
          <button class="btn" id="btn-start-event">${t('startEvent')}</button>
          <button class="btn btn-secondary" id="btn-change-stage">${t('changeStage')}</button>
          ${state.simulationStage ? `<button class="btn btn-secondary" id="btn-exit-sim">${t('simExit')}</button>` : ''}
        </div>
      </div>
    `;

    $('#btn-start-event')?.addEventListener('click', startJourneyEvent);
    $('#btn-change-stage')?.addEventListener('click', () => {
      container.innerHTML = renderWelcome() + renderStageSelection(false);
      bindStageCards(container, false);
    });
    $('#btn-exit-sim')?.addEventListener('click', () => {
      state = Storage.clearSimulation(state);
      renderJourney();
    });
  }

  function renderCompletion(container) {
    const { delta, patterns, entrySnapshot } = completion;
    const insight = entrySnapshot
      ? MirrorEngine.getEntryReflection(entrySnapshot, state.language)
      : null;
    const deltaHtml = Object.entries(delta)
      .filter(([, v]) => Math.abs(v) >= 1)
      .map(([k, v]) => {
        const cls = v > 0 ? 'up' : 'down';
        const sign = v > 0 ? '+' : '';
        return `<span class="delta-tag ${cls}">${t(k)} ${sign}${v}</span>`;
      }).join('');

    const patternHtml = (patterns?.detected || []).slice(0, 3)
      .map((d) => `<span class="pattern-tag">${t('pattern_' + d.pattern)}</span>`).join('');

    container.innerHTML = `
      <div class="completion-card">
        <h2>${t('completeTitle')}</h2>
        <p style="color:var(--text-muted)">${t('completeDesc')}</p>
        ${insight ? `<div class="completion-insight">${insight}</div>` : ''}
        ${patternHtml ? `<div style="margin:1rem 0">${patternHtml}</div>` : ''}
        ${deltaHtml ? `<p style="font-size:0.85rem;color:var(--text-muted)">${t('profileChanged')}</p><div class="profile-delta">${deltaHtml}</div>` : ''}
        <div class="btn-group" style="justify-content:center">
          <button class="btn" id="btn-go-dashboard">${t('viewDashboard')}</button>
          <button class="btn btn-secondary" id="btn-continue">${t('continueJourney')}</button>
        </div>
      </div>
    `;

    $('#btn-go-dashboard')?.addEventListener('click', () => { completion = null; showView('dashboard'); });
    $('#btn-continue')?.addEventListener('click', () => { completion = null; renderJourney(); });
  }

  function renderWelcome() {
    const chain = t('welcomePhilosophy');
    return `
      <div class="welcome-hero">
        <h2>${t('welcomeTitle')}</h2>
        <p>${t('welcomeDesc')}</p>
        <p style="font-size:0.9rem">${t('welcomeNot')}</p>
        <div class="philosophy-chain">${chain.map((s) => `<span>${s}</span>`).join('')}</div>
      </div>
    `;
  }

  function renderStageSelection() {
    const stages = EventEngine.getStages();
    const lang = state.language;
    return `
      <h2 style="text-align:center;margin-bottom:1rem">${t('selectStage')}</h2>
      <div class="stage-grid" id="stage-grid">
        ${stages.map((s) => `
          <div class="stage-card" data-stage="${s.id}">
            <h3>${s.name[lang]}</h3>
            <div class="age">${s.age}</div>
            <div class="focus">${t('stageFocus')}: ${STAGE_FOCUS[lang][s.id]}</div>
            <div class="count">${s.eventCount} ${t('eventsAvailable')}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function bindStageCards(container, isSimulation) {
    container.querySelectorAll('.stage-card').forEach((card) => {
      card.addEventListener('click', () => {
        const stageId = parseInt(card.dataset.stage, 10);
        if (isSimulation) {
          state = Storage.setSimulationStage(state, stageId);
          showView('journey');
          startJourneyEvent();
        } else {
          state = Storage.setStage(state, stageId);
          journey = null;
          completion = null;
          renderJourney();
        }
      });
    });
  }

  function startJourneyEvent() {
    const stageId = getActiveStageId();
    if (!stageId) return;
    const event = EventEngine.pickEvent(stageId, state.usedEventIds);
    if (!event) return;

    journey = {
      step: 1,
      event,
      stageId,
      thought: '',
      emotion: '',
      emotionCustom: '',
      decision: '',
      decisionCustom: '',
      consequences: null,
      reflection: { learned: '', differently: '', surprised: '' },
      simulation: !!state.simulationStage,
    };
    renderJourney();
  }

  function renderJourneyStep(container) {
    const stepLabels = STEP_KEYS.map((key, i) => {
      const n = i + 1;
      let cls = n === journey.step ? 'active' : n < journey.step ? 'done' : '';
      return `<span class="${cls}">${t(key)}</span>`;
    }).join('');

    const dots = STEP_KEYS.map((_, i) => {
      const n = i + 1;
      let cls = 'step-dot';
      if (n === journey.step) cls += ' active';
      else if (n < journey.step) cls += ' done';
      return `<div class="${cls}"></div>`;
    }).join('');

    const lang = state.language;
    const eventDesc = journey.event.description[lang] || journey.event.description.en;
    const catLabel = journey.event.categoryLabel?.[lang] || journey.event.category;

    let body = '';
    if (journey.step === 1) {
      const hints = MirrorEngine.getLiveHints(journey.thought, lang);
      body = `
        <div class="event-card">
          <div class="category">${catLabel}</div>
          <p>${eventDesc}</p>
        </div>
        <div class="question-block">
          <label>${t('stepThoughtQ')}</label>
          <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.5rem">${t('stepThoughtHint')}</p>
          <textarea id="input-thought" placeholder="...">${journey.thought}</textarea>
          <div id="live-hints" class="live-hints ${hints.length ? '' : 'hidden'}">
            <strong>${t('liveHints')}:</strong> <span id="hints-text">${hints.join(', ')}</span>
          </div>
        </div>
        <div class="btn-group">
          <button class="btn" id="btn-next" ${!journey.thought.trim() ? 'disabled' : ''}>${t('next')}</button>
        </div>
      `;
    } else if (journey.step === 2) {
      const emotions = EventEngine.getEmotions(lang);
      body = `
        <div class="event-card"><p>${eventDesc}</p></div>
        <div class="question-block">
          <label>${t('stepEmotionQ')}</label>
          <div class="emotion-grid" id="emotion-grid">
            ${emotions.map((e) => `
              <button type="button" class="emotion-btn ${journey.emotion === e.id ? 'selected' : ''}" data-emotion="${e.id}">${e.label}</button>
            `).join('')}
          </div>
          <label style="margin-top:1rem">${t('stepEmotionCustom')}</label>
          <input type="text" id="input-emotion-custom" value="${journey.emotionCustom}" placeholder="...">
        </div>
        <div class="btn-group">
          <button type="button" class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button type="button" class="btn" id="btn-next">${t('next')}</button>
        </div>
      `;
    } else if (journey.step === 3) {
      const options = EventEngine.getDecisionOptions(lang);
      body = `
        <div class="event-card"><p>${eventDesc}</p></div>
        <div class="question-block">
          <label>${t('stepDecisionQ')}</label>
          <div class="emotion-grid" id="decision-grid">
            ${options.map((o) => `
              <button type="button" class="decision-btn ${journey.decision === o.id ? 'selected' : ''}" data-decision="${o.id}">${o.label}</button>
            `).join('')}
          </div>
          <div id="custom-decision-wrap" class="${journey.decision === 'custom' ? '' : 'hidden'}" style="margin-top:1rem">
            <label>${t('stepDecisionCustom')}</label>
            <textarea id="input-decision-custom">${journey.decisionCustom}</textarea>
          </div>
        </div>
        <div class="btn-group">
          <button type="button" class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button type="button" class="btn" id="btn-next">${t('next')}</button>
        </div>
      `;
    } else if (journey.step === 4) {
      const decisionId = journey.decision === 'custom' ? 'custom' : journey.decision;
      journey.consequences = EventEngine.generateConsequences(journey.event, lang, decisionId);
      body = `
        <div class="event-card"><p>${eventDesc}</p></div>
        <h3 style="margin-bottom:1rem">${t('stepConsequence')}</h3>
        <div class="outcome-block">
          <div class="label">${t('immediate')}</div>
          <p>${journey.consequences.immediate}</p>
        </div>
        <div class="outcome-block">
          <div class="label">${t('later')}</div>
          <p>${journey.consequences.later}</p>
        </div>
        <div class="btn-group">
          <button type="button" class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button type="button" class="btn" id="btn-next">${t('next')}</button>
        </div>
      `;
    } else if (journey.step === 5) {
      body = `
        <div class="event-card"><p>${eventDesc}</p></div>
        <h3 style="margin-bottom:1rem">${t('stepReflection')}</h3>
        <div class="question-block">
          <label>${t('reflectLearned')}</label>
          <textarea id="input-learned">${journey.reflection.learned}</textarea>
        </div>
        <div class="question-block">
          <label>${t('reflectDifferent')}</label>
          <textarea id="input-differently">${journey.reflection.differently}</textarea>
        </div>
        <div class="question-block">
          <label>${t('reflectSurprised')}</label>
          <textarea id="input-surprised">${journey.reflection.surprised}</textarea>
        </div>
        <div class="btn-group">
          <button type="button" class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button type="button" class="btn" id="btn-finish">${t('finish')}</button>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="journey-step">
        <div class="step-labels">${stepLabels}</div>
        <div class="step-indicator">${dots}</div>
        ${body}
      </div>
    `;
    bindStepEvents();
  }

  function bindStepEvents() {
    const thoughtInput = $('#input-thought');
    if (thoughtInput) {
      thoughtInput.addEventListener('input', (e) => {
        journey.thought = e.target.value;
        $('#btn-next').disabled = !journey.thought.trim();
        const hints = MirrorEngine.getLiveHints(journey.thought, state.language);
        const wrap = $('#live-hints');
        const text = $('#hints-text');
        if (wrap && text) {
          wrap.classList.toggle('hidden', hints.length === 0);
          text.textContent = hints.join(', ');
        }
      });
      $('#btn-next')?.addEventListener('click', () => { journey.step = 2; renderJourney(); });
    }

    $('#emotion-grid')?.querySelectorAll('.emotion-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        journey.emotion = btn.dataset.emotion;
        $('#emotion-grid').querySelectorAll('.emotion-btn').forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');
      });
    });
    $('#input-emotion-custom')?.addEventListener('input', (e) => { journey.emotionCustom = e.target.value; });
    if (journey.step === 2) {
      $('#btn-back')?.addEventListener('click', () => { journey.step = 1; renderJourney(); });
      $('#btn-next')?.addEventListener('click', () => {
        if (!journey.emotion && !journey.emotionCustom.trim()) return;
        journey.step = 3;
        renderJourney();
      });
    }

    $('#decision-grid')?.querySelectorAll('.decision-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        journey.decision = btn.dataset.decision;
        journey.consequences = null;
        $('#decision-grid').querySelectorAll('.decision-btn').forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');
        $('#custom-decision-wrap')?.classList.toggle('hidden', journey.decision !== 'custom');
      });
    });
    $('#input-decision-custom')?.addEventListener('input', (e) => { journey.decisionCustom = e.target.value; });
    if (journey.step === 3) {
      $('#btn-back')?.addEventListener('click', () => { journey.step = 2; renderJourney(); });
      $('#btn-next')?.addEventListener('click', () => {
        if (!journey.decision) return;
        if (journey.decision === 'custom' && !journey.decisionCustom.trim()) return;
        journey.step = 4;
        renderJourney();
      });
    }

    if (journey.step === 4) {
      $('#btn-back')?.addEventListener('click', () => { journey.step = 3; journey.consequences = null; renderJourney(); });
      $('#btn-next')?.addEventListener('click', () => { journey.step = 5; renderJourney(); });
    }

    if (journey.step === 5) {
      $('#input-learned')?.addEventListener('input', (e) => { journey.reflection.learned = e.target.value; });
      $('#input-differently')?.addEventListener('input', (e) => { journey.reflection.differently = e.target.value; });
      $('#input-surprised')?.addEventListener('input', (e) => { journey.reflection.surprised = e.target.value; });
      $('#btn-back')?.addEventListener('click', () => { journey.step = 4; renderJourney(); });
      $('#btn-finish')?.addEventListener('click', finishJourney);
    }
  }

  function finishJourney() {
    const lang = state.language;
    const decisionText = journey.decision === 'custom'
      ? journey.decisionCustom
      : EventEngine.getDecisionOptions(lang).find((o) => o.id === journey.decision)?.label || journey.decision;

    const emotionLabel = EventEngine.getEmotionLabel(journey.emotion, lang, journey.emotionCustom);
    const patterns = MirrorEngine.analyzeEntry({
      thought: journey.thought,
      decision: decisionText,
      reflection: journey.reflection,
    });

    const profileBefore = { ...state.thinkingProfile };

    const entry = TimelineEngine.createEntry({
      event: journey.event,
      stageId: journey.stageId,
      thought: journey.thought,
      emotion: journey.emotion,
      emotionCustom: journey.emotionCustom,
      emotionLabel,
      decision: decisionText,
      consequences: journey.consequences,
      reflection: journey.reflection,
      patterns,
      simulation: journey.simulation,
    });

    state = Storage.addTimelineEntry(state, entry);
    state.thinkingProfile = ProfileEngine.evolveProfile(state.thinkingProfile, entry, patterns.scores);
    state = Storage.markEventUsed(state, journey.event.id);
    state = Storage.updateProfile(state, state.thinkingProfile);

    completion = {
      entrySnapshot: {
        thought: journey.thought,
        decision: decisionText,
        reflection: journey.reflection,
      },
      delta: ProfileEngine.getProfileDelta(profileBefore, state.thinkingProfile),
      patterns,
    };
    journey = null;
    renderJourney();
  }

  // ─── Dashboard ─────────────────────────────────────────────

  function renderDashboard() {
    if (state.timeline.length === 0) {
      $('#profile-scores').innerHTML = `<p class="empty-state">${t('noPatterns')}</p>`;
    } else {
      renderProfileScores(state.thinkingProfile);
      renderRadarChart(state.thinkingProfile);
      renderEmotionChart();
      renderEmotionTrendChart();
      renderPatternChart();
      renderPatternTags();
      renderFrequentPhrases();
      renderMirror();
      renderJourneyMap();
    }
  }

  function renderProfileScores(profile) {
    const keys = ['ownership', 'growth', 'victim', 'resilience', 'optimism', 'emotional_stability', 'self_awareness'];
    const container = $('#profile-scores');
    if (!container) return;
    container.innerHTML = keys.map((k) => `
      <div class="score-row">
        <span class="score-label">${t(k)}</span>
        <div class="score-bar"><div class="score-fill" style="width:${profile[k]}%"></div></div>
        <span class="score-value">${profile[k]}</span>
      </div>
    `).join('');
  }

  function destroyChart(chart) { if (chart) { chart.destroy(); return null; } return null; }

  function renderRadarChart(profile) {
    const canvas = $('#radar-chart');
    if (!canvas || typeof Chart === 'undefined') return;
    radarChart = destroyChart(radarChart);
    const data = ProfileEngine.getRadarData(profile);
    radarChart = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: data.labels.map((k) => t(k)),
        datasets: [{
          data: data.values,
          backgroundColor: 'rgba(91, 159, 212, 0.2)',
          borderColor: 'rgba(91, 159, 212, 0.8)',
          pointBackgroundColor: 'rgba(91, 159, 212, 1)',
        }],
      },
      options: {
        scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, color: '#8b9cb3', backdropColor: 'transparent' }, grid: { color: '#2d3a4f' }, pointLabels: { color: '#e8edf4', font: { size: 11 } } } },
        plugins: { legend: { display: false } },
      },
    });
  }

  function ensureCanvas(wrapId, canvasId) {
    const wrap = $(wrapId);
    if (!wrap) return null;
    if (!wrap.querySelector('canvas')) {
      wrap.innerHTML = `<canvas id="${canvasId}"></canvas>`;
    }
    return $(`#${canvasId}`);
  }

  function renderEmotionChart() {
    const trends = ProfileEngine.getEmotionTrends(state.timeline);
    const rawLabels = Object.keys(trends);
    const labels = rawLabels;
    const values = rawLabels.map((k) => trends[k].count);

    emotionChart = destroyChart(emotionChart);
    const wrap = $('#emotion-chart-wrap');
    if (rawLabels.length === 0) {
      if (wrap) wrap.innerHTML = `<p class="empty-state">${t('noPatterns')}</p>`;
      return;
    }

    const canvas = ensureCanvas('#emotion-chart-wrap', 'emotion-chart');
    if (!canvas) return;

    emotionChart = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: ['#d45b5b', '#5b9fd4', '#d4a55b', '#5bd491', '#8b9cb3', '#b57bd4'],
        }],
      },
      options: { plugins: { legend: { position: 'bottom', labels: { color: '#e8edf4', boxWidth: 12 } } } },
    });
  }

  function renderEmotionTrendChart() {
    const data = ProfileEngine.getEmotionTimelineData(state.timeline);
    emotionTrendChart = destroyChart(emotionTrendChart);

    const wrap = $('#emotion-trend-wrap');
    if (data.labels.length < 2) {
      if (wrap) wrap.innerHTML = `<p class="empty-state">${t('noPatterns')}</p>`;
      return;
    }

    const canvas = ensureCanvas('#emotion-trend-wrap', 'emotion-trend-chart');
    if (!canvas) return;

    emotionTrendChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          label: t('dashEmotionTrend'),
          data: data.values,
          borderColor: 'rgba(212, 165, 91, 1)',
          backgroundColor: 'rgba(212, 165, 91, 0.1)',
          fill: true,
          tension: 0.3,
        }],
      },
      options: {
        scales: {
          y: { min: 1, max: 6, ticks: { color: '#8b9cb3', stepSize: 1 }, grid: { color: '#2d3a4f' } },
          x: { ticks: { color: '#e8edf4' }, grid: { display: false } },
        },
        plugins: { legend: { display: false }, tooltip: { callbacks: { afterLabel: (ctx) => data.emotions[ctx.dataIndex] || '' } } },
      },
    });
  }

  function renderPatternChart() {
    const { totals, count } = MirrorEngine.aggregatePatterns(state.timeline);
    patternChart = destroyChart(patternChart);
    const wrap = $('#pattern-chart-wrap');
    if (count === 0) return;

    const sorted = Object.entries(totals).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
    if (sorted.length === 0) return;

    const canvas = ensureCanvas('#pattern-chart-wrap', 'pattern-chart');
    if (!canvas) return;

    patternChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: sorted.map(([k]) => t('pattern_' + k)),
        datasets: [{
          data: sorted.map(([, v]) => v),
          backgroundColor: 'rgba(91, 159, 212, 0.6)',
          borderColor: 'rgba(91, 159, 212, 1)',
          borderWidth: 1,
        }],
      },
      options: {
        indexAxis: 'y',
        scales: {
          x: { beginAtZero: true, ticks: { color: '#8b9cb3' }, grid: { color: '#2d3a4f' } },
          y: { ticks: { color: '#e8edf4', font: { size: 10 } }, grid: { display: false } },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderPatternTags() {
    const container = $('#pattern-analysis');
    if (!container) return;
    const { totals, count } = MirrorEngine.aggregatePatterns(state.timeline);
    if (count === 0) {
      container.innerHTML = '';
      return;
    }
    const sorted = Object.entries(totals).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
    container.innerHTML = sorted.map(([k, v]) => `<span class="pattern-tag">${t('pattern_' + k)}: ${v.toFixed(1)}</span>`).join('');
  }

  function renderFrequentPhrases() {
    const container = $('#frequent-phrases');
    if (!container) return;
    const phrases = MirrorEngine.getFrequentPhrases(state.timeline, state.language);
    container.innerHTML = phrases.length === 0
      ? `<p class="empty-state">${t('noPatterns')}</p>`
      : phrases.map((p) => `<div class="phrase-item"><span>${p.word}</span><span>${p.count}</span></div>`).join('');
  }

  function renderMirror() {
    const container = $('#ai-mirror');
    if (!container) return;
    const reflections = MirrorEngine.generateReflections(state.timeline, state.language);
    container.innerHTML = reflections.map((r) => `<div class="mirror-item">${r}</div>`).join('');
  }

  function renderJourneyMap() {
    const container = $('#life-journey-map');
    if (!container) return;
    const stages = EventEngine.getStages();
    const progress = TimelineEngine.getStageProgress(state.timeline, stages);
    const lang = state.language;
    const activeId = getActiveStageId();

    container.innerHTML = stages.map((s) => {
      const p = progress[s.id] || { total: 0, real: 0 };
      const pct = Math.min(100, p.total * 10);
      const active = s.id === activeId ? 'active' : '';
      return `
        <div class="map-stage ${active}">
          <div class="map-count">${p.total}</div>
          <div class="map-label">${s.name[lang]}</div>
          <div class="map-label">${p.real} ${t('entries')}</div>
          <div class="map-bar"><div class="map-bar-fill" style="width:${pct}%"></div></div>
        </div>
      `;
    }).join('');
  }

  // ─── Timeline ──────────────────────────────────────────────

  function renderTimeline() {
    const list = $('#timeline-list');
    const detail = $('#timeline-detail');
    if (!list) return;

    let entries = TimelineEngine.sortByDate(state.timeline);
    if (timelineFilter !== 'all') {
      entries = entries.filter((e) => e.stage === parseInt(timelineFilter, 10));
    }

    if (entries.length === 0) {
      list.innerHTML = `<p class="empty-state">${t('timelineEmpty')}</p>`;
      detail?.classList.add('hidden');
      return;
    }

    const lang = state.language;
    const stages = EventEngine.getStages();

    list.innerHTML = entries.map((entry) => {
      const summary = TimelineEngine.formatEntrySummary(entry, lang);
      const stage = stages.find((s) => s.id === entry.stage);
      const emotionDisplay = entry.emotionLabel || EventEngine.getEmotionLabel(entry.emotion, lang, entry.emotionCustom);
      const sim = entry.simulation ? `<span class="sim-badge">${t('simulation')}</span>` : '';
      return `
        <div class="timeline-item" data-entry="${entry.id}">
          <div class="meta">
            <span>${summary.date}</span>
            <span>${stage?.name[lang] || ''}</span>
            <span>${emotionDisplay}</span>
            ${sim}
          </div>
          <div class="desc">${summary.desc}</div>
        </div>
      `;
    }).join('');

    list.querySelectorAll('.timeline-item').forEach((item) => {
      item.addEventListener('click', () => {
        const entry = TimelineEngine.getEntry(state.timeline, item.dataset.entry);
        if (entry) renderTimelineDetail(entry);
      });
    });
  }

  function renderTimelineDetail(entry) {
    const detail = $('#timeline-detail');
    if (!detail) return;
    detail.classList.remove('hidden');

    const lang = state.language;
    const stages = EventEngine.getStages();
    const stage = stages.find((s) => s.id === entry.stage);
    const emotionDisplay = entry.emotionLabel || EventEngine.getEmotionLabel(entry.emotion, lang, entry.emotionCustom);
    const patternTags = (entry.patterns?.detected || [])
      .map((d) => t('pattern_' + d.pattern)).join(', ');

    const chain = [
      { label: t('chainStage'), value: stage?.name[lang] },
      { label: t('chainEvent'), value: entry.eventDescription?.[lang] },
      { label: t('chainThought'), value: entry.thought },
      { label: t('chainEmotion'), value: emotionDisplay },
      { label: t('chainDecision'), value: entry.decision },
      { label: t('chainOutcome'), value: `${entry.consequences?.immediate || ''} → ${entry.consequences?.later || ''}` },
      { label: t('chainReflection'), value: [entry.reflection?.learned, entry.reflection?.differently, entry.reflection?.surprised].filter(Boolean).join(' | ') },
      { label: t('chainPatterns'), value: patternTags },
    ];

    detail.innerHTML = `
      <h3>${new Date(entry.timestamp).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}</h3>
      <div class="detail-chain">
        ${chain.map((c) => `
          <div class="chain-step">
            <span class="chain-label">${c.label}</span>
            <span>${c.value || '—'}</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  // ─── Simulation ────────────────────────────────────────────

  function renderSimulation() {
    const container = $('#sim-stages');
    if (!container) return;
    container.innerHTML = renderStageSelection();
    bindStageCards(container, true);

    container.querySelectorAll('.stage-card').forEach((card) => {
      const stageId = parseInt(card.dataset.stage, 10);
      if (state.simulationStage === stageId) {
        card.classList.add('selected');
        const badge = document.createElement('div');
        badge.className = 'count';
        badge.style.color = 'var(--accent-warm)';
        badge.textContent = t('simActive');
        card.appendChild(badge);
      }
    });
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
