const STORAGE_KEY = 'btc_wallet_v1';

export function saveWallet(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function loadWallet() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearWallet() {
  localStorage.removeItem(STORAGE_KEY);
}

export function hasWallet() {
  return Boolean(loadWallet()?.mnemonic);
}
