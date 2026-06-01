const SAVE_KEY = "englishMonsterQuest.save.v1";

const defaultAchievements = {
  firstCapture: false,
  tenWords: false,
  perfectQuiz: false,
  animalMaster: false,
  foodCollector: false,
  pronunciationExpert: false
};

export function createDefaultState() {
  return {
    level: 1,
    xp: 0,
    coins: 0,
    stars: 0,
    hearts: 3,
    captured: [],
    escaped: [],
    treasureOpened: [],
    explored: [],
    correctAnswers: 0,
    totalAnswers: 0,
    bestStreak: 0,
    currentStreak: 0,
    perfectQuizStreak: 0,
    pronunciationPlays: 0,
    timeStarted: Date.now(),
    activeSeconds: 0,
    lastSeen: Date.now(),
    learningStreak: 1,
    achievements: { ...defaultAchievements },
    settings: {
      speech: true,
      sfx: true
    },
    daily: createDailyState()
  };
}

export function createDailyState() {
  const today = new Date().toISOString().slice(0, 10);
  return {
    date: today,
    missions: [
      { id: "learn5", title: "Learn 5 new words", goal: 5, progress: 0, reward: { xp: 25, coins: 10 }, claimed: false },
      { id: "capture3", title: "Capture 3 Wordmons", goal: 3, progress: 0, reward: { xp: 35, stars: 1 }, claimed: false },
      { id: "answer10", title: "Answer 10 questions correctly", goal: 10, progress: 0, reward: { xp: 30, coins: 15 }, claimed: false }
    ]
  };
}

export function loadState() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    const saved = raw ? JSON.parse(raw) : {};
    const state = mergeState(createDefaultState(), saved);
    return refreshDaily(state);
  } catch (error) {
    console.warn("Could not load save file", error);
    return createDefaultState();
  }
}

export function saveState(state) {
  state.lastSeen = Date.now();
  localStorage.setItem(SAVE_KEY, JSON.stringify(state));
}

export function resetState() {
  localStorage.removeItem(SAVE_KEY);
  return createDefaultState();
}

export function addRewards(state, reward) {
  state.xp += reward.xp || 0;
  state.coins += reward.coins || 0;
  state.stars += reward.stars || 0;
  while (state.xp >= xpForLevel(state.level) && state.level < 100) {
    state.xp -= xpForLevel(state.level);
    state.level += 1;
    state.hearts = 3;
  }
}

export function xpForLevel(level) {
  return 80 + level * 25;
}

export function markDailyProgress(state, missionId, amount = 1) {
  const mission = state.daily.missions.find((item) => item.id === missionId);
  if (!mission || mission.claimed) return null;
  mission.progress = Math.min(mission.goal, mission.progress + amount);
  if (mission.progress >= mission.goal) {
    mission.claimed = true;
    addRewards(state, mission.reward);
    return mission;
  }
  return null;
}

export function unlockAchievements(state, vocabulary) {
  const captured = new Set(state.captured);
  const capturedWords = vocabulary.filter((entry) => captured.has(entry.id));
  const unlocked = [];
  const unlock = (id) => {
    if (!state.achievements[id]) {
      state.achievements[id] = true;
      unlocked.push(id);
    }
  };

  if (capturedWords.length >= 1) unlock("firstCapture");
  if (capturedWords.length >= 10) unlock("tenWords");
  if (state.perfectQuizStreak >= 5) unlock("perfectQuiz");
  if (state.pronunciationPlays >= 10) unlock("pronunciationExpert");
  if (capturedWords.filter((entry) => entry.category === "Animals").length >= 5) unlock("animalMaster");
  if (capturedWords.filter((entry) => entry.category === "Food").length >= 3) unlock("foodCollector");

  return unlocked;
}

function refreshDaily(state) {
  const today = new Date().toISOString().slice(0, 10);
  if (!state.daily || state.daily.date !== today) {
    state.daily = createDailyState();
    state.learningStreak = sameYesterday(state.lastSeen) ? state.learningStreak + 1 : 1;
  }
  return state;
}

function sameYesterday(timestamp) {
  const previous = new Date(timestamp || 0);
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return previous.toISOString().slice(0, 10) === yesterday.toISOString().slice(0, 10);
}

function mergeState(base, saved) {
  return {
    ...base,
    ...saved,
    achievements: { ...base.achievements, ...(saved.achievements || {}) },
    settings: { ...base.settings, ...(saved.settings || {}) },
    daily: saved.daily || base.daily
  };
}
