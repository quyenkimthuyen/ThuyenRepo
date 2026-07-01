/** @type {SpeechSynthesisUtterance | null} */
let currentUtterance = null;
let speaking = false;

/**
 * @returns {boolean}
 */
export function isTtsSupported() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

/**
 * @returns {boolean}
 */
export function isSpeaking() {
  return speaking;
}

export function stopSpeaking() {
  if (!isTtsSupported()) return;
  window.speechSynthesis.cancel();
  currentUtterance = null;
  speaking = false;
}

/**
 * @param {string} text
 * @param {{ rate?: number }=} options
 * @returns {Promise<boolean>}
 */
export function speakText(text, options = {}) {
  return new Promise((resolve) => {
    if (!isTtsSupported() || !text.trim()) {
      resolve(false);
      return;
    }

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

    const finish = (ok) => {
      speaking = false;
      currentUtterance = null;
      resolve(ok);
    };

    utterance.onend = () => finish(true);
    utterance.onerror = () => finish(false);

    currentUtterance = utterance;
    speaking = true;
    window.speechSynthesis.speak(utterance);
  });
}

if (isTtsSupported() && window.speechSynthesis.onvoiceschanged !== undefined) {
  window.speechSynthesis.onvoiceschanged = () => {
    /* preload voices */
  };
}
