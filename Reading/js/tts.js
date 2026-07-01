/** @type {SpeechSynthesisUtterance | null} */
let currentUtterance = null;

/**
 * @returns {boolean}
 */
export function isTtsSupported() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

export function stopSpeaking() {
  if (!isTtsSupported()) return;
  window.speechSynthesis.cancel();
  currentUtterance = null;
}

/**
 * @param {string} text
 * @param {{ rate?: number }=} options
 * @returns {boolean}
 */
export function speakText(text, options = {}) {
  if (!isTtsSupported() || !text.trim()) return false;

  stopSpeaking();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-US';
  utterance.rate = options.rate ?? 0.92;

  const voices = window.speechSynthesis.getVoices();
  const enVoice =
    voices.find((v) => v.lang.startsWith('en-US') && v.localService) ||
    voices.find((v) => v.lang.startsWith('en-US')) ||
    voices.find((v) => v.lang.startsWith('en'));
  if (enVoice) utterance.voice = enVoice;

  currentUtterance = utterance;
  window.speechSynthesis.speak(utterance);
  return true;
}

if (isTtsSupported() && window.speechSynthesis.onvoiceschanged !== undefined) {
  window.speechSynthesis.onvoiceschanged = () => {
    /* preload voices */
  };
}
