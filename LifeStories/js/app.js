window.appState = loadState();
initPersonality(window.appState);

let currentScreen = 'home';
let screenParams = {};

const SCREENS = {
  home: renderHome,
  story: renderStoryScreen,
  map: renderStoryMap,
  relationships: renderRelationships,
  profile: renderProfile,
};

function navigateTo(screen, params = {}) {
  currentScreen = screen;
  screenParams = params;

  const container = document.getElementById('screen-container');
  const backBtn = document.getElementById('btn-back');

  if (screen === 'story') {
    backBtn.classList.remove('hidden');
  } else {
    backBtn.classList.add('hidden');
  }

  updateBottomNav(screen);

  const renderer = SCREENS[screen];
  if (renderer) {
    renderer(container, window.appState, params);
  }
}

function updateBottomNav(activeScreen) {
  let nav = document.getElementById('bottom-nav');
  if (!nav) {
    nav = document.createElement('nav');
    nav.id = 'bottom-nav';
    nav.className = 'bottom-nav';
    nav.innerHTML = `
      <button data-screen="home"><span class="nav-icon">🏠</span><span data-i18n="navHome">${t('navHome')}</span></button>
      <button data-screen="map"><span class="nav-icon">🗺️</span><span data-i18n="navMap">${t('navMap')}</span></button>
      <button data-screen="relationships"><span class="nav-icon">💫</span><span data-i18n="navRelations">${t('navRelations')}</span></button>
      <button data-screen="profile"><span class="nav-icon">📊</span><span data-i18n="navProfile">${t('navProfile')}</span></button>
    `;
    document.getElementById('app').appendChild(nav);

    nav.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        const screen = btn.getAttribute('data-screen');
        if (screen !== 'story') navigateTo(screen);
      });
    });
  }

  const mapScreen = activeScreen === 'story' ? null : activeScreen;
  nav.querySelectorAll('button').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-screen') === mapScreen);
  });

  nav.style.display = activeScreen === 'story' ? 'none' : 'flex';
}

function initApp() {
  const savedLang = localStorage.getItem('lifechoices_lang');
  if (savedLang) setLang(savedLang);
  updateLangButton();

  document.getElementById('btn-lang').addEventListener('click', () => {
    setLang(currentLang === 'vi' ? 'en' : 'vi');
    updateLangButton();
    navigateTo(currentScreen, screenParams);
  });

  document.getElementById('btn-back').addEventListener('click', () => {
    if (currentScreen === 'story') {
      saveState(window.appState);
      navigateTo('home');
    }
  });

  navigateTo('home');
}

function updateLangButton() {
  document.getElementById('btn-lang').textContent = currentLang === 'vi' ? 'EN' : 'VI';
}

document.addEventListener('DOMContentLoaded', initApp);
