const STORAGE_KEY = 'life_trading_simulator_save';

export function saveGame(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

export function loadGame() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return null;
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function hasSave() {
  return localStorage.getItem(STORAGE_KEY) !== null;
}

export function clearSave() {
  localStorage.removeItem(STORAGE_KEY);
}
