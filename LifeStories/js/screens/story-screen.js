let currentEngine = null;

function isIllustratedStory(story) {
  return typeof isIllustratedStyle === 'function' && isIllustratedStyle(story?.visualStyle);
}

function getStoryVisualStyle(story) {
  return story?.visualStyle || 'comic';
}

function renderStoryScreen(container, state, params) {
  const story = getStoryById(params.storyId);
  if (!story) { navigateTo('home'); return; }

  const savedProgress = params.replay ? null : getStoryProgress(state, story.id);
  currentEngine = new StoryEngine(story, savedProgress);
  const illustrated = isIllustratedStory(story);
  const vStyle = getStoryVisualStyle(story);

  container.innerHTML = `
    <div class="story-screen${illustrated ? ' story-screen--illustrated story-screen--' + vStyle : ''}" id="story-ui">
      <div class="story-bg${illustrated ? ' illus-panel' : ''}" id="story-bg">
        <div class="story-progress-top">
          <div class="story-progress-label">
            <span>${tl(story.title)}</span>
            <span id="progress-pct">0%</span>
          </div>
          <div class="progress-bar"><div class="progress-bar-fill" id="progress-fill" style="width:0%"></div></div>
        </div>
        ${illustrated ? `
          <div class="illus-frame illus-frame--${vStyle}" id="illus-frame">
            <div class="illus-frame__border"></div>
            <div class="illus-art" id="illus-art" role="img" aria-live="polite"></div>
            <div class="illus-caption" id="illus-caption"></div>
            <div class="illus-character-badge" id="illus-badge">
              <span class="illus-character-badge__emoji" id="char-avatar"></span>
            </div>
          </div>
        ` : '<div class="character-avatar" id="char-avatar"></div>'}
      </div>
      <div class="dialogue-panel${illustrated ? ' dialogue-panel--illustrated dialogue-panel--' + vStyle : ''}">
        <div class="dialogue-bubble" id="dialogue-bubble">
          <div class="character-name" id="char-name"></div>
          <div class="dialogue-text" id="dialogue-text"></div>
        </div>
      </div>
      <div id="choices-area"></div>
      <div id="consequence-area"></div>
    </div>
  `;

  document.getElementById('btn-back').classList.remove('hidden');
  renderCurrentScene(state, story);
}

function updateStoryIllustration(story, scene) {
  const art = typeof getStoryArtForScene === 'function'
    ? getStoryArtForScene(story.id, scene.id)
    : null;
  const artEl = document.getElementById('illus-art');
  const caption = document.getElementById('illus-caption');
  const bg = document.getElementById('story-bg');

  if (!artEl) return;

  if (art && art.svg) {
    if (artEl.dataset.artKey !== art.key) {
      artEl.innerHTML = art.svg;
      artEl.dataset.artKey = art.key;
      artEl.classList.remove('illus-art--hidden');
      artEl.classList.add('illus-art--show');
    }
    artEl.setAttribute('aria-label', tl(art.caption));
    if (caption) caption.textContent = tl(art.caption);
    if (bg) bg.dataset.mood = art.mood || '';
  } else {
    artEl.innerHTML = '';
    artEl.dataset.artKey = '';
    artEl.classList.add('illus-art--hidden');
    artEl.classList.remove('illus-art--show');
    if (caption) caption.textContent = '';
    if (bg) bg.dataset.mood = 'neutral';
  }
}

function renderCurrentScene(state, story) {
  const engine = currentEngine;
  const scene = engine.getCurrentScene();
  if (!scene) { showStoryComplete(state, story); return; }

  const char = engine.getCharacter(scene.character) || { name: { en: '...', vi: '...' }, emoji: '', color: '#888' };
  const illustrated = isIllustratedStory(story);
  const vStyle = getStoryVisualStyle(story);

  const avatarEl = document.getElementById('char-avatar');
  if (illustrated) {
    avatarEl.textContent = char.emoji || '💬';
    updateStoryIllustration(story, scene);
  } else {
    avatarEl.textContent = char.emoji || '💬';
  }

  document.getElementById('char-name').textContent = tl(char.name);
  document.getElementById('char-name').style.color = char.color;
  document.getElementById('dialogue-text').textContent = tl(scene.dialogue);

  const pct = engine.getProgress();
  document.getElementById('progress-pct').textContent = pct + '%';
  document.getElementById('progress-fill').style.width = pct + '%';

  const choicesArea = document.getElementById('choices-area');
  const consequenceArea = document.getElementById('consequence-area');
  const dialogueBubble = document.getElementById('dialogue-bubble');
  consequenceArea.innerHTML = '';

  if (dialogueBubble) {
    dialogueBubble.classList.remove('dialogue-bubble--enter');
    void dialogueBubble.offsetWidth;
    dialogueBubble.classList.add('dialogue-bubble--enter');
  }

  if (engine.lastConsequenceMessages?.length) {
    engine.lastConsequenceMessages.forEach(msg => {
      if (msg.message) {
        const toast = document.createElement('div');
        toast.className = 'consequence-toast';
        toast.textContent = '◈ ' + tl(msg.message);
        consequenceArea.appendChild(toast);
      }
    });
    engine.lastConsequenceMessages = [];
  }

  if (scene.choices && scene.choices.length > 0) {
    choicesArea.innerHTML = '<div class="choices-panel' + (illustrated ? ' choices-panel--illustrated choices-panel--' + vStyle : '') + '"><p class="choices-label" data-i18n="choose">' + t('choose') + '</p></div>';
    const panel = choicesArea.querySelector('.choices-panel');

    scene.choices.forEach((choice, idx) => {
      const btn = document.createElement('button');
      btn.className = 'btn-choice' + (illustrated ? ' btn-choice--illustrated btn-choice--' + vStyle : '');
      btn.textContent = tl(choice.text);
      btn.style.animationDelay = (idx * 0.08) + 's';
      btn.addEventListener('click', () => onChoiceMade(state, story, idx));
      panel.appendChild(btn);
    });
  } else if (scene.endStory) {
    choicesArea.innerHTML = '<div class="choices-panel"><button class="btn btn-primary" id="btn-finish">' + t('next') + '</button></div>';
    document.getElementById('btn-finish').addEventListener('click', () => showStoryComplete(state, story));
  } else if (engine.isComplete) {
    showStoryComplete(state, story);
  } else {
    choicesArea.innerHTML = '<div class="choices-panel"><button class="btn btn-primary" id="btn-next">' + t('next') + '</button></div>';
    document.getElementById('btn-next').addEventListener('click', () => {
      engine.advanceNarrative();
      saveEngineProgress(state, story);
      if (engine.isComplete) {
        showStoryComplete(state, story);
      } else {
        renderCurrentScene(state, story);
      }
    });
  }
}

function onChoiceMade(state, story, choiceIndex) {
  const engine = currentEngine;
  engine.makeChoice(choiceIndex);
  saveEngineProgress(state, story);
  recordBranch(state, story.id, engine.choicePath);

  if (engine.isComplete) {
    showStoryComplete(state, story);
  } else {
    renderCurrentScene(state, story);
  }
}

function saveEngineProgress(state, story) {
  setStoryProgress(state, story.id, currentEngine.getSaveData());
  saveState(state);
}

function showStoryComplete(state, story) {
  const isFirstComplete = !state.completedStories.includes(story.id);
  if (isFirstComplete) {
    markStoryCompleted(state, story.id);
    addXP(state, story.xpReward);
    unlockAchievement(state, 'milestone_first_story');
  }
  recordBranch(state, story.id, currentEngine.choicePath);

  const choicesArea = document.getElementById('choices-area');
  choicesArea.innerHTML = `
    <div class="story-complete-panel">
      <h2 data-i18n="storyComplete">${t('storyComplete')}</h2>
      ${isFirstComplete ? '<div class="xp-badge">' + tFormat('xpBadge', { n: story.xpReward }) + '</div>' : ''}
      <div class="complete-actions">
        <button class="btn btn-primary" id="btn-home" data-i18n="backToHome">${t('backToHome')}</button>
        <button class="btn btn-secondary" id="btn-profile" data-i18n="viewProfile">${t('viewProfile')}</button>
      </div>
    </div>
  `;

  document.getElementById('btn-home').addEventListener('click', () => navigateTo('home'));
  document.getElementById('btn-profile').addEventListener('click', () => navigateTo('profile'));
}
