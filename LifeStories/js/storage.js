const STORAGE_KEY = 'lifechoices_save_v1';

const DEFAULT_STATE = {
  lang: 'vi',
  xp: 0,
  achievements: [],
  completedStories: [],
  storyProgress: {},
  relationships: {},
  personality: {},
  tagCounts: {},
  choiceHistory: [],
  exploredBranches: {},
  milestones: [],
  currentStory: null,
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return structuredClone(DEFAULT_STATE);
    return { ...structuredClone(DEFAULT_STATE), ...JSON.parse(raw) };
  } catch {
    return structuredClone(DEFAULT_STATE);
  }
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function resetState() {
  localStorage.removeItem(STORAGE_KEY);
  return structuredClone(DEFAULT_STATE);
}

function getStoryProgress(state, storyId) {
  return state.storyProgress[storyId] || null;
}

function setStoryProgress(state, storyId, progress) {
  state.storyProgress[storyId] = progress;
  saveState(state);
}

function markStoryCompleted(state, storyId) {
  if (!state.completedStories.includes(storyId)) {
    state.completedStories.push(storyId);
  }
  saveState(state);
}

function addXP(state, amount) {
  state.xp += amount;
  saveState(state);
}

function unlockAchievement(state, id) {
  if (!state.achievements.includes(id)) {
    state.achievements.push(id);
    saveState(state);
  }
}

function recordBranch(state, storyId, branchPath) {
  if (!state.exploredBranches[storyId]) {
    state.exploredBranches[storyId] = [];
  }
  const key = branchPath.join('>');
  if (!state.exploredBranches[storyId].includes(key)) {
    state.exploredBranches[storyId].push(key);
    saveState(state);
  }
}
