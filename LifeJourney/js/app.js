/**
 * Cognitive Mirror: Life Journey — Main Application
 */
const App = (() => {
  const I18N = {
    vi: {
      appTitle: 'Cognitive Mirror',
      appSubtitle: 'Hành trình Cuộc đời',
      navJourney: 'Hành trình',
      navDashboard: 'Bảng điều khiển',
      navTimeline: 'Dòng thời gian',
      navSimulation: 'Mô phỏng tương lai',
      footer: 'Gương nhận thức — giúp bạn nhìn thấy khuôn mẫu tư duy của chính mình.',
      welcomeTitle: 'Chào mừng đến với Gương Nhận Thức',
      welcomeDesc: 'Ứng dụng này không phải game, không phải self-help. Đây là một gương giúp bạn nhìn thấy cách bạn nghĩ, phản ứng và diễn giải sự kiện.',
      welcomePhilosophy: ['Giai đoạn đời', 'Sự kiện', 'Diễn giải', 'Cảm xúc', 'Quyết định', 'Kết quả', 'Suy ngẫm', 'Nhận diện khuôn mẫu'],
      selectStage: 'Chọn giai đoạn cuộc đời hiện tại của bạn',
      stageFocus: 'Trọng tâm',
      eventsAvailable: 'sự kiện',
      changeStage: 'Đổi giai đoạn',
      startEvent: 'Bắt đầu sự kiện mới',
      stepThought: 'Suy nghĩ đầu tiên của bạn là gì?',
      stepThoughtHint: 'Viết tự do — không có đúng hay sai.',
      stepEmotion: 'Bạn cảm thấy thế nào?',
      stepEmotionCustom: 'Hoặc mô tả cảm xúc khác:',
      stepDecision: 'Bạn sẽ làm gì tiếp theo?',
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
      dashRadar: 'Biểu đồ tư duy',
      dashProfile: 'Hồ sơ tư duy',
      dashEmotion: 'Xu hướng cảm xúc',
      dashPatterns: 'Phân tích khuôn mẫu ngôn ngữ',
      dashPhrases: 'Cụm từ thường gặp',
      dashMirror: 'Gương nhận thức',
      dashMap: 'Bản đồ hành trình',
      timelineTitle: 'Dòng thời gian cuộc đời',
      timelineEmpty: 'Chưa có sự kiện nào. Bắt đầu hành trình để xây dựng dòng thời gian.',
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
    },
    en: {
      appTitle: 'Cognitive Mirror',
      appSubtitle: 'Life Journey',
      navJourney: 'Journey',
      navDashboard: 'Dashboard',
      navTimeline: 'Timeline',
      navSimulation: 'Future Simulation',
      footer: 'A cognitive mirror — helping you see your own thinking patterns.',
      welcomeTitle: 'Welcome to Cognitive Mirror',
      welcomeDesc: 'This is not a game, not self-help. It is a mirror that helps you see how you think, react, and interpret events.',
      welcomePhilosophy: ['Life Stage', 'Event', 'Interpretation', 'Emotion', 'Decision', 'Outcome', 'Reflection', 'Pattern Recognition'],
      selectStage: 'Select your current life stage',
      stageFocus: 'Focus',
      eventsAvailable: 'events',
      changeStage: 'Change stage',
      startEvent: 'Start new event',
      stepThought: 'What is your first thought?',
      stepThoughtHint: 'Write freely — there is no right or wrong.',
      stepEmotion: 'How do you feel?',
      stepEmotionCustom: 'Or describe another emotion:',
      stepDecision: 'What would you do next?',
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
      dashRadar: 'Thinking Radar',
      dashProfile: 'Thinking Profile',
      dashEmotion: 'Emotion Trends',
      dashPatterns: 'Language Pattern Analysis',
      dashPhrases: 'Most Frequent Phrases',
      dashMirror: 'AI Mirror',
      dashMap: 'Life Journey Map',
      timelineTitle: 'Life Timeline',
      timelineEmpty: 'No events yet. Start your journey to build a timeline.',
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

  let state = null;
  let journey = null;
  let radarChart = null;
  let emotionChart = null;

  function t(key) {
    const lang = state?.language || 'vi';
    return I18N[lang][key] || I18N.en[key] || key;
  }

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  function wrapHasCanvas(wrap) {
    return wrap && wrap.querySelector('canvas');
  }

  async function init() {
    state = Storage.load();
    await EventEngine.loadEvents();
    bindGlobalEvents();
    applyLanguage();
    showView('journey');
    renderJourney();
  }

  function bindGlobalEvents() {
    $$('.nav-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const view = btn.dataset.view;
        showView(view);
      });
    });

    $$('.lang-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        state = Storage.setLanguage(state, btn.dataset.lang);
        applyLanguage();
        renderCurrentView();
      });
    });
  }

  function applyLanguage() {
    const lang = state.language;
    document.documentElement.lang = lang;
    $('#app-title').textContent = t('appTitle');
    $('#app-subtitle').textContent = t('appSubtitle');
    $('#nav-journey').textContent = t('navJourney');
    $('#nav-dashboard').textContent = t('navDashboard');
    $('#nav-timeline').textContent = t('navTimeline');
    $('#nav-simulation').textContent = t('navSimulation');
    $('#footer-text').textContent = t('footer');
    $('#dash-radar-title').textContent = t('dashRadar');
    $('#dash-profile-title').textContent = t('dashProfile');
    $('#dash-emotion-title').textContent = t('dashEmotion');
    $('#dash-patterns-title').textContent = t('dashPatterns');
    $('#dash-phrases-title').textContent = t('dashPhrases');
    $('#dash-mirror-title').textContent = t('dashMirror');
    $('#dash-map-title').textContent = t('dashMap');
    $('#timeline-title').textContent = t('timelineTitle');
    $('#sim-title').textContent = t('simTitle');
    $('#sim-desc').textContent = t('simDesc');
    $$('.lang-btn').forEach((b) => b.classList.toggle('active', b.dataset.lang === lang));
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

  // ─── Journey ───────────────────────────────────────────────

  function renderJourney() {
    const container = $('#journey-content');
    if (!container) return;

    if (journey?.step) {
      renderJourneyStep(container);
      return;
    }

    if (!state.currentStage) {
      container.innerHTML = renderWelcome() + renderStageSelection(false);
      bindStageCards(container, false);
      return;
    }

    const stageId = getActiveStageId();
    const stages = EventEngine.getStages();
    const stage = stages.find((s) => s.id === stageId);
    const simBadge = state.simulationStage
      ? `<span class="sim-badge">${t('simulation')}</span>`
      : '';

    container.innerHTML = `
      <div class="journey-step">
        <div class="event-card" style="border-left-color: var(--accent)">
          <div class="category">${t('currentStage')}${simBadge}</div>
          <p><strong>${stage?.name[state.language] || ''}</strong> (${stage?.age || ''})</p>
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
      container.innerHTML = renderStageSelection(false);
      bindStageCards(container, false);
    });
    $('#btn-exit-sim')?.addEventListener('click', () => {
      state = Storage.clearSimulation(state);
      renderJourney();
    });
  }

  function renderWelcome() {
    const chain = t('welcomePhilosophy');
    return `
      <div class="welcome-hero">
        <h2>${t('welcomeTitle')}</h2>
        <p>${t('welcomeDesc')}</p>
        <div class="philosophy-chain">
          ${chain.map((s) => `<span>${s}</span>`).join('')}
        </div>
      </div>
    `;
  }

  function renderStageSelection(isSimulation) {
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
          renderJourney();
        }
      });
    });
  }

  function startJourneyEvent() {
    const stageId = getActiveStageId();
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
    const steps = 5;
    const dots = Array.from({ length: steps }, (_, i) => {
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
      body = `
        <div class="event-card">
          <div class="category">${catLabel}</div>
          <p>${eventDesc}</p>
        </div>
        <div class="question-block">
          <label>${t('stepThought')}</label>
          <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.5rem">${t('stepThoughtHint')}</p>
          <textarea id="input-thought" placeholder="...">${journey.thought}</textarea>
        </div>
        <div class="btn-group">
          <button class="btn" id="btn-next" ${!journey.thought ? 'disabled' : ''}>${t('next')}</button>
        </div>
      `;
    } else if (journey.step === 2) {
      const emotions = EventEngine.getEmotions(lang);
      body = `
        <div class="event-card"><p>${eventDesc}</p></div>
        <div class="question-block">
          <label>${t('stepEmotion')}</label>
          <div class="emotion-grid" id="emotion-grid">
            ${emotions.map((e) => `
              <button class="emotion-btn ${journey.emotion === e.id ? 'selected' : ''}" data-emotion="${e.id}">${e.label}</button>
            `).join('')}
          </div>
          <label style="margin-top:1rem">${t('stepEmotionCustom')}</label>
          <input type="text" id="input-emotion-custom" value="${journey.emotionCustom}" placeholder="...">
        </div>
        <div class="btn-group">
          <button class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button class="btn" id="btn-next">${t('next')}</button>
        </div>
      `;
    } else if (journey.step === 3) {
      const options = EventEngine.getDecisionOptions(lang);
      body = `
        <div class="event-card"><p>${eventDesc}</p></div>
        <div class="question-block">
          <label>${t('stepDecision')}</label>
          <div class="emotion-grid" id="decision-grid">
            ${options.map((o) => `
              <button class="decision-btn ${journey.decision === o.id ? 'selected' : ''}" data-decision="${o.id}">${o.label}</button>
            `).join('')}
          </div>
          <div id="custom-decision-wrap" class="${journey.decision === 'custom' ? '' : 'hidden'}" style="margin-top:1rem">
            <label>${t('stepDecisionCustom')}</label>
            <textarea id="input-decision-custom">${journey.decisionCustom}</textarea>
          </div>
        </div>
        <div class="btn-group">
          <button class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button class="btn" id="btn-next">${t('next')}</button>
        </div>
      `;
    } else if (journey.step === 4) {
      if (!journey.consequences) {
        journey.consequences = EventEngine.generateConsequences(journey.event, lang);
      }
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
          <button class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button class="btn" id="btn-next">${t('next')}</button>
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
          <button class="btn btn-secondary" id="btn-back">${t('back')}</button>
          <button class="btn" id="btn-finish">${t('finish')}</button>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="journey-step">
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
        $('#decision-grid').querySelectorAll('.decision-btn').forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');
        const wrap = $('#custom-decision-wrap');
        if (wrap) wrap.classList.toggle('hidden', journey.decision !== 'custom');
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
      $('#btn-back')?.addEventListener('click', () => { journey.step = 3; renderJourney(); });
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

    const patterns = MirrorEngine.analyzeEntry({
      thought: journey.thought,
      decision: decisionText,
      reflection: journey.reflection,
    });

    const entry = TimelineEngine.createEntry({
      event: journey.event,
      stageId: journey.stageId,
      thought: journey.thought,
      emotion: journey.emotion,
      emotionCustom: journey.emotionCustom,
      decision: decisionText,
      consequences: journey.consequences,
      reflection: journey.reflection,
      patterns,
      simulation: journey.simulation,
    });

    state = Storage.addTimelineEntry(state, entry);
    state = Storage.markEventUsed(state, journey.event.id);
    state.thinkingProfile = ProfileEngine.evolveProfile(state.thinkingProfile, entry, patterns.scores);
    Storage.updateProfile(state, state.thinkingProfile);

    journey = null;
    renderJourney();
  }

  // ─── Dashboard ─────────────────────────────────────────────

  function renderDashboard() {
    const profile = state.thinkingProfile;
    renderProfileScores(profile);
    renderRadarChart(profile);
    renderEmotionChart();
    renderPatternAnalysis();
    renderFrequentPhrases();
    renderMirror();
    renderJourneyMap();
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

  function renderRadarChart(profile) {
    const canvas = $('#radar-chart');
    if (!canvas) return;
    const data = ProfileEngine.getRadarData(profile);
    const labels = data.labels.map((k) => t(k));

    if (radarChart) radarChart.destroy();
    radarChart = new Chart(canvas, {
      type: 'radar',
      data: {
        labels,
        datasets: [{
          label: t('dashProfile'),
          data: data.values,
          backgroundColor: 'rgba(91, 159, 212, 0.2)',
          borderColor: 'rgba(91, 159, 212, 0.8)',
          pointBackgroundColor: 'rgba(91, 159, 212, 1)',
        }],
      },
      options: {
        scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, color: '#8b9cb3' }, grid: { color: '#2d3a4f' }, pointLabels: { color: '#e8edf4' } } },
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderEmotionChart() {
    let canvas = $('#emotion-chart');
    if (!canvas) return;
    const trends = ProfileEngine.getEmotionTrends(state.timeline);
    const labels = Object.keys(trends);
    const values = labels.map((k) => trends[k].count);

    if (emotionChart) emotionChart.destroy();
    if (labels.length === 0) {
      const wrap = canvas.parentElement;
      if (!wrap.querySelector('.empty-state')) {
        wrap.innerHTML = `<p class="empty-state">${t('noPatterns')}</p>`;
      }
      return;
    }

    if (!wrapHasCanvas(canvas.parentElement)) {
      canvas.parentElement.innerHTML = '<canvas id="emotion-chart"></canvas>';
      canvas = $('#emotion-chart');
    }

    emotionChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: t('dashEmotion'),
          data: values,
          backgroundColor: 'rgba(212, 165, 91, 0.6)',
          borderColor: 'rgba(212, 165, 91, 1)',
          borderWidth: 1,
        }],
      },
      options: {
        scales: {
          y: { beginAtZero: true, ticks: { color: '#8b9cb3', stepSize: 1 }, grid: { color: '#2d3a4f' } },
          x: { ticks: { color: '#e8edf4' }, grid: { display: false } },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderPatternAnalysis() {
    const container = $('#pattern-analysis');
    if (!container) return;
    const { totals, count } = MirrorEngine.aggregatePatterns(state.timeline);
    if (count === 0) {
      container.innerHTML = `<p class="empty-state">${t('noPatterns')}</p>`;
      return;
    }
    const sorted = Object.entries(totals).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
    container.innerHTML = sorted.map(([k, v]) => `
      <span class="pattern-tag">${t('pattern_' + k)}: ${v.toFixed(1)}</span>
    `).join('') || `<p class="empty-state">${t('noPatterns')}</p>`;
  }

  function renderFrequentPhrases() {
    const container = $('#frequent-phrases');
    if (!container) return;
    const phrases = MirrorEngine.getFrequentPhrases(state.timeline, state.language);
    if (phrases.length === 0) {
      container.innerHTML = `<p class="empty-state">${t('noPatterns')}</p>`;
      return;
    }
    container.innerHTML = phrases.map((p) => `
      <div class="phrase-item"><span>${p.word}</span><span>${p.count}</span></div>
    `).join('');
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
      const active = s.id === activeId ? 'active' : '';
      return `
        <div class="map-stage ${active}">
          <div class="map-count">${p.total}</div>
          <div class="map-label">${s.name[lang]}</div>
          <div class="map-label">${p.real} ${t('entries')}</div>
        </div>
      `;
    }).join('');
  }

  // ─── Timeline ──────────────────────────────────────────────

  function renderTimeline() {
    const list = $('#timeline-list');
    const detail = $('#timeline-detail');
    if (!list) return;

    const sorted = TimelineEngine.sortByDate(state.timeline);
    if (sorted.length === 0) {
      list.innerHTML = `<p class="empty-state">${t('timelineEmpty')}</p>`;
      detail?.classList.add('hidden');
      return;
    }

    const lang = state.language;
    const stages = EventEngine.getStages();

    list.innerHTML = sorted.map((entry) => {
      const summary = TimelineEngine.formatEntrySummary(entry, lang);
      const stage = stages.find((s) => s.id === entry.stage);
      const sim = entry.simulation ? `<span class="sim-badge">${t('simulation')}</span>` : '';
      return `
        <div class="timeline-item" data-entry="${entry.id}">
          <div class="meta">
            <span>${summary.date}</span>
            <span>${stage?.name[lang] || ''}</span>
            <span>${summary.emotion}</span>
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

    const chain = [
      { label: t('chainStage'), value: stage?.name[lang] },
      { label: t('chainEvent'), value: entry.eventDescription?.[lang] },
      { label: t('chainThought'), value: entry.thought },
      { label: t('chainEmotion'), value: entry.emotion },
      { label: t('chainDecision'), value: entry.decision },
      { label: t('chainOutcome'), value: `${entry.consequences?.immediate || ''} / ${entry.consequences?.later || ''}` },
      { label: t('chainReflection'), value: [entry.reflection?.learned, entry.reflection?.differently, entry.reflection?.surprised].filter(Boolean).join(' | ') },
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
    container.innerHTML = renderStageSelection(true);
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
