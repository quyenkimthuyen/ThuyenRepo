let selectedStageId = null;

const ILLUSTRATION_ICONS = {
  comic: '📖',
  watercolor: '🎨',
  flat: '◼',
  crayon: '🖍',
  papercut: '✂️',
};

function getIllustrationBadgeHtml(story) {
  if (!story.visualStyle || typeof isIllustratedStyle !== 'function' || !isIllustratedStyle(story.visualStyle)) {
    return '';
  }
  const label = ILLUSTRATION_STYLE_LABELS?.[story.visualStyle];
  const icon = ILLUSTRATION_ICONS[story.visualStyle] || '🖼';
  const text = label ? tl(label) : t('comicBadge');
  return '<span class="story-card-badge-illus story-card-badge--' + story.visualStyle + '">' + icon + ' ' + text + '</span>';
}

function renderHome(container, state) {
  const unlockedStages = LIFE_STAGES.filter(s => s.unlocked);
  if (!selectedStageId || !unlockedStages.find(s => s.id === selectedStageId)) {
    selectedStageId = unlockedStages[0]?.id || 'high_school';
  }

  container.innerHTML = `
    <div class="screen-header">
      <h1 data-i18n="selectStage">${t('selectStage')}</h1>
      <p data-i18n="yourChoices">${t('yourChoices')}</p>
    </div>
    <div class="stage-grid" id="stage-grid"></div>
    <div id="story-list-container"></div>
  `;

  const grid = container.querySelector('#stage-grid');

  LIFE_STAGES.forEach(s => {
    const isActive = s.id === selectedStageId;
    const stageDescKey = 'stageDesc_' + s.id;
    const hasDesc = I18N[currentLang][stageDescKey] || I18N.en[stageDescKey];
    const card = document.createElement('div');
    card.className = `stage-card${s.unlocked ? '' : ' locked'}${isActive && s.unlocked ? ' active' : ''}`;
    card.innerHTML = `
      ${s.unlocked ? '<span class="stage-badge" data-i18n="unlocked">' + t('unlocked') + '</span>' : ''}
      <h3 data-i18n="${s.id}">${t(s.id)}</h3>
      <p class="stage-meta">${s.unlocked ? s.storyCount + ' ' + t('stories') : t('stageLocked')}</p>
      ${isActive && s.unlocked && hasDesc ? '<p class="stage-meta" style="margin-top:0.5rem" data-i18n="' + stageDescKey + '">' + t(stageDescKey) + '</p>' : ''}
    `;
    if (s.unlocked) {
      card.addEventListener('click', () => {
        selectedStageId = s.id;
        showStoryList(container, state, s.id);
        grid.querySelectorAll('.stage-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        const descKey = 'stageDesc_' + s.id;
        const desc = I18N[currentLang][descKey] || I18N.en[descKey];
        const existingDesc = card.querySelector('.stage-desc');
        if (existingDesc) existingDesc.remove();
        if (desc) {
          const p = document.createElement('p');
          p.className = 'stage-meta stage-desc';
          p.style.marginTop = '0.5rem';
          p.textContent = desc;
          card.appendChild(p);
        }
      });
    }
    grid.appendChild(card);
  });

  showStoryList(container, state, selectedStageId);
  applyI18n(container);
}

function showStoryList(container, state, stageId) {
  const listContainer = container.querySelector('#story-list-container');
  const stories = getStoriesForStage(stageId);

  let html = `<div class="screen-header" style="margin-top:2rem">
    <h2 data-i18n="${stageId}">${t(stageId)}</h2>
  </div><div class="story-list">`;

  if (stories.length === 0) {
    html += '<div class="empty-state">' + t('stageLocked') + '</div>';
  }

  stories.forEach(story => {
    const progress = getStoryProgress(state, story.id);
    const isCompleted = state.completedStories.includes(story.id);
    const isInProgress = progress && !isCompleted;
    const statusClass = isCompleted ? 'completed' : isInProgress ? 'in-progress' : '';
    const statusText = isCompleted ? t('completed') : isInProgress ? t('inProgress') : '';
    const progressPct = progress ? Math.round((progress.visitedScenes?.length || 0) / story.totalScenes * 100) : 0;

    const illusClass = story.visualStyle && isIllustratedStyle?.(story.visualStyle)
      ? ' story-card--illustrated story-card--' + story.visualStyle
      : '';

    html += `
      <div class="story-card ${statusClass}${illusClass}" data-story-id="${story.id}">
        <div class="story-card-header">
          <div>
            <span class="story-category" data-i18n="category_${story.category}">${t('category_' + story.category)}</span>
            ${getIllustrationBadgeHtml(story)}
            <h3>${tl(story.title)}</h3>
          </div>
          ${statusText ? '<span class="story-status ' + statusClass + '">' + statusText + '</span>' : ''}
        </div>
        <p class="story-desc">${tl(story.description)}</p>
        ${isInProgress ? '<div class="progress-bar"><div class="progress-bar-fill" style="width:' + progressPct + '%"></div></div>' : ''}
        <button class="btn btn-primary" data-action="play" data-story="${story.id}">
          ${isInProgress ? t('continueStory') : isCompleted ? t('replayStory') : t('startStory')}
        </button>
      </div>
    `;
  });

  html += '</div>';
  listContainer.innerHTML = html;

  listContainer.querySelectorAll('[data-action="play"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const storyId = btn.getAttribute('data-story');
      navigateTo('story', { storyId, replay: state.completedStories.includes(storyId) });
    });
  });

  applyI18n(listContainer);
}
