const STORAGE_KEY = "be-vui-hoc-chu-progress";

const defaultState = {
  learned: [],
  xp: 0,
  stars: 0,
  badges: [],
  streak: 0,
  sound: true
};

function loadState() {
  try {
    return { ...defaultState, ...JSON.parse(localStorage.getItem(STORAGE_KEY)) };
  } catch (error) {
    return { ...defaultState };
  }
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function addReward(state, xp = 5, stars = 1) {
  state.xp += xp;
  state.stars += stars;
  saveState(state);
}

function completeLetter(state, letter, alphabet, badges) {
  if (!state.learned.includes(letter)) {
    state.learned.push(letter);
    state.streak += 1;
    addReward(state, 10, 1);
  }

  const learnedLetters = new Set(state.learned);
  const allVowels = alphabet.filter((item) => item.type === "vowel").every((item) => learnedLetters.has(item.letter));
  const badgeChecks = [
    ["first-letter", state.learned.length >= 1],
    ["five-streak", state.streak >= 5],
    ["vowels", allVowels],
    ["alphabet", state.learned.length >= alphabet.length],
    ["game-star", state.xp >= 100]
  ];

  badgeChecks.forEach(([id, passed]) => {
    if (passed && !state.badges.includes(id)) state.badges.push(id);
  });

  saveState(state);
  return badges.filter((badge) => state.badges.includes(badge.id));
}

window.LearnStore = {
  loadState,
  saveState,
  addReward,
  completeLetter
};
