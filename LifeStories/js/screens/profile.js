let personalityChart = null;
let tagsChart = null;

function renderProfile(container, state) {
  initPersonality(state);
  const traits = getTraitPercentages(state);
  const insights = getInsights(state);
  const completed = state.completedStories.length;
  const totalBranches = Object.values(state.exploredBranches).reduce((s, b) => s + b.length, 0);

  let html = `
    <div class="screen-header">
      <h1 data-i18n="lifeProfile">${t('lifeProfile')}</h1>
    </div>
    <div class="profile-stats">
      <div class="stat-card">
        <div class="stat-value">${completed}</div>
        <div class="stat-label" data-i18n="storiesCompleted">${t('storiesCompleted')}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${state.xp}</div>
        <div class="stat-label" data-i18n="totalXP">${t('totalXP')}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${totalBranches}</div>
        <div class="stat-label" data-i18n="branchesExplored">${t('branchesExplored')}</div>
      </div>
    </div>
    <div class="chart-container">
      <h3 data-i18n="personalityTraits">${t('personalityTraits')}</h3>
      <canvas id="personality-chart" height="200"></canvas>
    </div>
    <div class="chart-container">
      <h3 data-i18n="thinkingPatterns">${t('thinkingPatterns')}</h3>
      ${insights.length > 0 ? '<div class="insights-list" id="insights-list"></div>' : '<div class="empty-state" data-i18n="noInsights">' + t('noInsights') + '</div>'}
      <canvas id="tags-chart" height="180" style="margin-top:1rem"></canvas>
    </div>
    <div class="chart-container">
      <h3 data-i18n="achievements">${t('achievements')}</h3>
      <div class="achievements-grid" id="achievements-grid"></div>
    </div>
    <div class="reset-section">
      <button class="btn-danger" id="btn-reset" data-i18n="resetProgress">${t('resetProgress')}</button>
    </div>
  `;

  container.innerHTML = html;

  if (insights.length > 0) {
    const list = container.querySelector('#insights-list');
    insights.forEach(insight => {
      const item = document.createElement('div');
      item.className = 'insight-item';
      item.innerHTML = t('insightPrefix') + ' <em>' + insight.text + '</em>';
      list.appendChild(item);
    });
  }

  const achGrid = container.querySelector('#achievements-grid');
  const allAchievements = [
    { id: 'milestone_first_story', label: t('milestone_first_story') },
    { id: 'milestone_all_branches', label: t('milestone_all_branches') },
    { id: 'milestone_relationship_master', label: t('milestone_relationship_master') },
  ];

  allAchievements.forEach(ach => {
    const earned = state.achievements.includes(ach.id);
    const badge = document.createElement('span');
    badge.className = 'achievement-badge';
    badge.style.opacity = earned ? '1' : '0.35';
    badge.textContent = (earned ? '★ ' : '○ ') + ach.label;
    achGrid.appendChild(badge);
  });

  renderCharts(traits, state.tagCounts || {});

  container.querySelector('#btn-reset').addEventListener('click', () => {
    if (confirm(t('resetConfirm'))) {
      window.appState = resetState();
      initPersonality(window.appState);
      navigateTo('home');
    }
  });

  applyI18n(container);
}

function renderCharts(traits, tagCounts) {
  if (personalityChart) personalityChart.destroy();
  if (tagsChart) tagsChart.destroy();

  const traitLabels = PERSONALITY_TRAITS.map(tr => t(tr));
  const traitValues = PERSONALITY_TRAITS.map(tr => traits[tr] || 0);

  const ctx1 = document.getElementById('personality-chart');
  if (ctx1) {
    personalityChart = new Chart(ctx1, {
      type: 'radar',
      data: {
        labels: traitLabels,
        datasets: [{
          data: traitValues,
          backgroundColor: 'rgba(212, 168, 83, 0.15)',
          borderColor: 'rgba(212, 168, 83, 0.8)',
          borderWidth: 2,
          pointBackgroundColor: '#d4a853',
        }],
      },
      options: {
        responsive: true,
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: { display: false },
            grid: { color: 'rgba(255,255,255,0.08)' },
            angleLines: { color: 'rgba(255,255,255,0.08)' },
            pointLabels: { color: '#9aa0ab', font: { size: 10 } },
          },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  const tagEntries = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const ctx2 = document.getElementById('tags-chart');
  if (ctx2 && tagEntries.length > 0) {
    tagsChart = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: tagEntries.map(([tag]) => tag.replace(/_/g, ' ')),
        datasets: [{
          data: tagEntries.map(([, count]) => count),
          backgroundColor: 'rgba(155, 114, 207, 0.6)',
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        scales: {
          x: { ticks: { color: '#5c6370' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: { ticks: { color: '#9aa0ab', font: { size: 11 } }, grid: { display: false } },
        },
        plugins: { legend: { display: false } },
      },
    });
  }
}
