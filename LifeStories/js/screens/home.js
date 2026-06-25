function renderHome(container, state) {
  const stage = LIFE_STAGES.find(s => s.id === 'high_school');
  const stories = getStoriesForStage('high_school');

  container.innerHTML = `
    <div class="screen-header">
      <h1 data-i18n="selectStage">${t('selectStage')}</h1>
      <p data-i18n="yourChoices">${t('yourChoices')}</p>
    </div>
    <div class="stage-grid" id="stage-grid"></div>
    <div id="story-list-container" class="hidden"></div>
  `;

  const grid = container.querySelector('#stage-grid');

  LIFE_STAGES.forEach(s => {
    const isActive = s.id === 'high_school';
    const card = document.createElement('div');
    card.className = `stage-card${s.unlocked ? '' : ' locked'}${isActive ? ' active' : ''}`;
    card.innerHTML = `
      ${s.unlocked ? '<span class="stage-badge" data-i18n="unlocked">' + t('unlocked') + '</span>' : ''}
      <h3 data-i18n="${s.id}">${t(s.id)}</h3>
      <p class="stage-meta">${s.unlocked ? s.storyCount + ' ' + t('stories') : t('stageLocked')}</p>
      ${isActive ? '<p class="stage-meta" style="margin-top:0.5rem" data-i18n="stageDesc_high_school">' + t('stageDesc_high_school') + '</p>' : ''}
    `;
    if (s.unlocked) {
      card.addEventListener('click', () => showStoryList(container, state, s.id));
    }
    grid.appendChild(card);
  });

  if (stage.unlocked) {
    showStoryList(container, state, 'high_school');
  }

  applyI18n(container);
}

function showStoryList(container, state, stageId) {
  const listContainer = container.querySelector('#story-list-container');
  listContainer.classList.remove('hidden');
  const stories = getStoriesForStage(stageId);

  let html = `<div class="screen-header" style="margin-top:2rem">
    <h2 data-i18n="${stageId}">${t(stageId)}</h2>
  </div><div class="story-list">`;

  stories.forEach(story => {
    const progress = getStoryProgress(state, story.id);
    const isCompleted = state.completedStories.includes(story.id);
    const isInProgress = progress && !isCompleted;
    const statusClass = isCompleted ? 'completed' : isInProgress ? 'in-progress' : '';
    const statusText = isCompleted ? t('completed') : isInProgress ? t('inProgress') : '';
    const progressPct = progress ? Math.round((progress.visitedScenes?.length || 0) / story.totalScenes * 100) : 0;

    html += `
      <div class="story-card ${statusClass}" data-story-id="${story.id}">
        <div class="story-card-header">
          <div>
            <span class="story-category" data-i18n="category_${story.category}">${t('category_' + story.category)}</span>
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
