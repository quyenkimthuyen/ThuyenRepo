/**
 * Pure logic — dùng chung app + unit tests
 */

export const PRACTICE_MODE = { TEXT: 'text', SCORE: 'score' };

export const MIC_STATE = {
  OFF: 'off',
  READY: 'ready',
  HEARING: 'hearing',
  PROCESSING: 'processing',
  SAMPLE: 'sample',
};

export const TEXT_FAST_MS = 280;
export const SCORE_FAST_MS = 450;
export const DEFAULT_BLOCK_SEC = 2;
export const MIN_BLOCK_SEC = 0.5;
export const MAX_BLOCK_SEC = 10;
export const MAX_LATENCY_MS = 5000;
export const MAX_TEXT_RESPONSE_MS = 800;
export const MAX_SCORE_RESPONSE_MS = 3500;

export function normalizeWord(s) {
  return String(s || '').toLowerCase().replace(/[^a-z']/g, '').trim();
}

export function wordsMatch(spoken, target) {
  const s = normalizeWord(spoken);
  const t = normalizeWord(target);
  if (!s || !t) return false;
  if (s === t || s.includes(t) || t.includes(s)) return true;
  if (Math.abs(s.length - t.length) <= 2) {
    let diff = 0;
    const maxLen = Math.max(s.length, t.length);
    for (let i = 0; i < maxLen; i++) {
      if (s[i] !== t[i]) diff++;
    }
    return diff <= 2;
  }
  return false;
}

export function extractSpokenWord(finalText, interimText) {
  const combined = (`${finalText || ''} ${interimText || ''}`).trim();
  if (!combined) return '';
  return combined.split(/\s+/).pop() || combined;
}

export function getSilenceMsFromSetting(silenceSec) {
  const sec = parseFloat(silenceSec);
  return Math.round((Number.isFinite(sec) ? sec : 0.5) * 1000);
}

export function getSilenceMsForMode(silenceSec, isTextMode) {
  const base = getSilenceMsFromSetting(silenceSec);
  return isTextMode ? Math.min(base, 500) : Math.min(base, 700);
}

export function getFastProcessDelay(isTextMode, isFinal, silenceSec) {
  if (isTextMode) {
    return isFinal ? TEXT_FAST_MS : TEXT_FAST_MS + 120;
  }
  return isFinal ? SCORE_FAST_MS : getSilenceMsForMode(silenceSec, false);
}

export function getBlockMsFromSetting(blockSec) {
  const sec = parseFloat(blockSec);
  if (!Number.isFinite(sec)) return Math.round(DEFAULT_BLOCK_SEC * 1000);
  const clamped = Math.min(MAX_BLOCK_SEC, Math.max(MIN_BLOCK_SEC, sec));
  return Math.round(clamped * 1000);
}

/** Còn bao nhiêu ms tới lần xử lý block tiếp theo */
export function msUntilNextBlock(nowMs, blockStartedAt, blockMs) {
  if (!blockStartedAt || !blockMs) return 0;
  return Math.max(0, blockMs - (nowMs - blockStartedAt));
}

/** Block hiện tại có đủ tín hiệu để xử lý không */
export function shouldProcessBlock({ hadSpeech, hasText, hasAudio }) {
  return !!(hadSpeech || hasText || hasAudio);
}

/** RMS từ byte time-domain (AnalyserNode) */
export function computeRms(timeDomainBytes) {
  if (!timeDomainBytes?.length) return 0;
  let sum = 0;
  for (let i = 0; i < timeDomainBytes.length; i++) {
    const v = (timeDomainBytes[i] - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / timeDomainBytes.length);
}

export function isSpeaking(rms, threshold = 0.010) {
  return rms > threshold;
}

export function validateWordsJson(data) {
  const errors = [];
  if (!data || typeof data !== 'object') {
    return ['Root must be object'];
  }
  if (!Array.isArray(data.words)) {
    return ['Missing words array'];
  }
  data.words.forEach((w, i) => {
    if (!w.word) errors.push(`words[${i}]: missing word`);
    if (!w.ipa) errors.push(`words[${i}]: missing ipa`);
    if (!Array.isArray(w.phonemes) || !w.phonemes.length) {
      errors.push(`words[${i}]: phonemes must be non-empty array`);
    }
  });
  return errors;
}
