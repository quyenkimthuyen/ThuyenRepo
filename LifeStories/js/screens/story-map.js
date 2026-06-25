function renderStoryMap(container, state) {
  const stories = getStoriesForStage('high_school');

  let html = `
    <div class="screen-header">
      <h1 data-i18n="storyMap">${t('storyMap')}</h1>
    </div>
    <div class="map-grid">
  `;

  if (stories.length === 0) {
    html += '<div class="empty-state" data-i18n="noInsights">' + t('noInsights') + '</div>';
  }

  stories.forEach(story => {
    const isCompleted = state.completedStories.includes(story.id);
    const branches = state.exploredBranches[story.id] || [];
    const progress = getStoryProgress(state, story.id);
    const statusIcon = isCompleted ? '✓' : progress ? '◐' : '○';

    html += `
      <div class="map-story-item">
        <h4>${statusIcon} ${tl(story.title)}</h4>
        <span class="story-category" data-i18n="category_${story.category}">${t('category_' + story.category)}</span>
        <p class="story-desc" style="margin-top:0.5rem">${isCompleted ? t('completed') : progress ? t('inProgress') : t('locked')}</p>
        ${branches.length > 0 ? `
          <div class="map-branches">
            <span style="font-size:0.75rem;color:var(--text-muted)">${t('branchesExplored')}: ${branches.length}</span>
          </div>
        ` : ''}
        ${!isCompleted && !progress ? '' : `
          <button class="btn btn-secondary" style="margin-top:0.75rem" data-play="${story.id}">
            ${isCompleted ? t('replayStory') : t('continueStory')}
          </button>
        `}
      </div>
    `;
  });

  html += '</div>';
  container.innerHTML = html;

  container.querySelectorAll('[data-play]').forEach(btn => {
    btn.addEventListener('click', () => {
      const storyId = btn.getAttribute('data-play');
      const replay = state.completedStories.includes(storyId);
      navigateTo('story', { storyId, replay });
    });
  });

  applyI18n(container);
}
