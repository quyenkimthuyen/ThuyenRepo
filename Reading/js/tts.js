/** @type {SpeechSynthesisUtterance | null} */
let currentUtterance = null;
let speaking = false;
let speakGeneration = 0;
/** @type {{ gen: number, resolve: (ok: boolean) => void } | null} */
let activeSpeak = null;
/** @type {string | null} */
let selectedVoiceUri = null;
/** @type {Set<() => void>} */
const voiceListeners = new Set();

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

/**
 * @returns {SpeechSynthesisVoice[]}
 */
export function getEnglishVoices() {
  if (!isTtsSupported()) return [];
  return window.speechSynthesis
    .getVoices()
    .filter((v) => /^en(-|$)/i.test(v.lang))
    .sort((a, b) => {
      const rank = (/** @type {SpeechSynthesisVoice} */ v) => {
        if (v.lang.toLowerCase().startsWith('en-us')) return 0;
        if (v.lang.toLowerCase().startsWith('en-gb')) return 1;
        if (v.lang.toLowerCase().startsWith('en')) return 2;
        return 3;
      };
      const dr = rank(a) - rank(b);
      if (dr !== 0) return dr;
      return a.name.localeCompare(b.name);
    });
}

/**
 * @param {() => void} callback
 */
export function onVoicesReady(callback) {
  if (getEnglishVoices().length) callback();
  voiceListeners.add(callback);
}

function notifyVoiceListeners() {
  if (!getEnglishVoices().length) return;
  voiceListeners.forEach((cb) => cb());
}

/**
 * @param {string | null} uri
 */
export function setSelectedVoiceUri(uri) {
  selectedVoiceUri = uri || null;
}

/**
 * @returns {string | null}
 */
export function getSelectedVoiceUri() {
  return selectedVoiceUri;
}

/**
 * @param {SpeechSynthesisVoice[]} voices
 * @returns {SpeechSynthesisVoice | undefined}
 */
function resolveVoice(voices) {
  if (!voices.length) return undefined;

  if (selectedVoiceUri) {
    const saved = voices.find((v) => v.voiceURI === selectedVoiceUri);
    if (saved) return saved;
  }

  return (
    voices.find((v) => v.lang.toLowerCase().startsWith('en-us') && v.localService) ||
    voices.find((v) => v.lang.toLowerCase().startsWith('en-us')) ||
    voices.find((v) => v.lang.toLowerCase().startsWith('en-gb')) ||
    voices[0]
  );
}

/**
 * @param {SpeechSynthesisVoice} voice
 * @returns {string}
 */
export function formatVoiceLabel(voice) {
  const lang = voice.lang.replace('_', '-');
  return `${voice.name} (${lang})`;
}

function settleActiveSpeak(ok) {
  if (!activeSpeak) return;
  const { resolve } = activeSpeak;
  activeSpeak = null;
  speaking = false;
  currentUtterance = null;
  resolve(ok);
}

function abortSpeaking() {
  speakGeneration += 1;
  if (isTtsSupported()) {
    window.speechSynthesis.cancel();
  }
  settleActiveSpeak(false);
}

export function stopSpeaking() {
  abortSpeaking();
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

    abortSpeaking();

    const gen = speakGeneration;
    activeSpeak = { gen, resolve };

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = options.rate ?? 0.92;

    const voice = resolveVoice(getEnglishVoices());
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }

    const finish = (ok) => {
      if (!activeSpeak || activeSpeak.gen !== gen) return;
      settleActiveSpeak(ok);
    };

    utterance.onend = () => finish(true);
    utterance.onerror = () => finish(false);

    currentUtterance = utterance;
    speaking = true;
    window.speechSynthesis.speak(utterance);
  });
}

if (isTtsSupported()) {
  window.speechSynthesis.onvoiceschanged = notifyVoiceListeners;
  notifyVoiceListeners();
  setTimeout(notifyVoiceListeners, 250);
}
