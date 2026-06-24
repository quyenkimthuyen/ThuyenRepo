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

export const PROCESS_COOLDOWN_MS = 350;
export const MIN_SPEECH_MS = 180;
export const MAX_UTTERANCE_MS = 5000;
export const DEFAULT_SILENCE_SEC = 0.35;
export const MIN_SILENCE_SEC = 0.2;
export const MAX_SILENCE_SEC = 1.2;
export const MAX_LATENCY_MS = 5000;
export const TEXT_MATCH_DELAY_MS = 200;
export const MAX_TEXT_RESPONSE_MS = 750;
export const MAX_SCORE_RESPONSE_MS = 3000;
export const MIN_BLOB_BYTES = 500;
export const MIN_UPLOAD_BYTES = 800;

export function isScoreMode(practiceMode) {
  return practiceMode === PRACTICE_MODE.SCORE;
}

/** Chế độ chấm điểm: có tự gọi API sau khi kết thúc câu không */
export function shouldAutoScoreOnUtteranceEnd({ practiceMode, autoEvaluate }) {
  return isScoreMode(practiceMode) && autoEvaluate !== false;
}

export function isAudioReadyForScore(blobSize, minBytes = MIN_BLOB_BYTES) {
  return Number(blobSize) >= minBytes;
}

/** Tiêu chí đạt từ (giống renderEvaluation trong app) */
export function isEvaluationPassed(data, passScore = 80) {
  if (!data?.phonemes?.length) return false;
  const allOk = data.phonemes.every((p) => p.label === 'ok');
  return data.passed ?? (allOk || data.overall_score >= passScore);
}

export function uploadFilenameForMime(mimeType) {
  if (mimeType?.includes('mp4')) return 'recording.mp4';
  if (mimeType?.includes('ogg')) return 'recording.ogg';
  if (mimeType?.includes('wav')) return 'recording.wav';
  return 'recording.webm';
}

/** Kiểm tra JSON evaluate đủ field cho UI chấm điểm */
export function validateEvaluateResponse(data) {
  const errors = [];
  if (!data || typeof data !== 'object') return ['root must be object'];
  if (!data.word) errors.push('missing word');
  if (typeof data.overall_score !== 'number') errors.push('missing overall_score');
  if (typeof data.passed !== 'boolean' && data.passed !== undefined) {
    errors.push('passed must be boolean if set');
  }
  if (!Array.isArray(data.phonemes)) {
    errors.push('missing phonemes array');
  } else {
    data.phonemes.forEach((p, i) => {
      if (!p.ipa) errors.push(`phonemes[${i}].ipa`);
      if (typeof p.score !== 'number') errors.push(`phonemes[${i}].score`);
      if (!['ok', 'warn', 'mis'].includes(p.label)) errors.push(`phonemes[${i}].label`);
      if (!('start' in p) || !('end' in p)) errors.push(`phonemes[${i}].timing`);
    });
  }
  return errors;
}

export function normalizeWord(s) {
  return String(s || '').toLowerCase().replace(/[^a-z']/g, '').trim();
}

/** Chuẩn hóa câu/cụm từ — giữ khoảng trắng giữa các từ */
export function normalizeTextForMatch(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/[^a-z0-9'\s-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
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

/** Chế độ text: khớp chính xác 100% — hỗ trợ cụm từ và câu (mở rộng sau) */
export function textMatchExact(spoken, target) {
  const s = normalizeTextForMatch(spoken);
  const t = normalizeTextForMatch(target);
  return s.length > 0 && s === t;
}

/** @deprecated Dùng textMatchExact — giữ cho tương thích test cũ */
export function wordsMatchExact(spoken, target) {
  return textMatchExact(spoken, target);
}

/** Ghép final + interim thành câu đang nói (không chỉ lấy từ cuối) */
export function extractSpokenText(finalText, interimText) {
  const final = normalizeTextForMatch(finalText);
  const interim = normalizeTextForMatch(interimText);
  if (!final) return interim;
  if (!interim) return final;
  if (interim.startsWith(final)) return interim;
  if (final.startsWith(interim)) return final;
  if (final.endsWith(interim) || interim.endsWith(final)) {
    return final.length >= interim.length ? final : interim;
  }
  return normalizeTextForMatch(`${final} ${interim}`);
}

/** Lấy token cuối — dùng khi cần gợi ý nhanh (score mode) */
export function extractSpokenWord(finalText, interimText) {
  const combined = extractSpokenText(finalText, interimText);
  if (!combined) return '';
  return combined.split(/\s+/).pop() || combined;
}

export function getSilenceMsFromSetting(silenceSec) {
  const sec = parseFloat(silenceSec);
  if (!Number.isFinite(sec)) return Math.round(DEFAULT_SILENCE_SEC * 1000);
  const clamped = Math.min(MAX_SILENCE_SEC, Math.max(MIN_SILENCE_SEC, sec));
  return Math.round(clamped * 1000);
}

/** Hangover VAD — text nhanh hơn score một chút */
export function getHangoverMs(silenceSec, isTextMode) {
  const base = getSilenceMsFromSetting(silenceSec);
  return isTextMode ? Math.min(base, 400) : Math.min(base, 550);
}

export function canStartProcessing(lastProcessAt, nowMs, cooldownMs = PROCESS_COOLDOWN_MS) {
  if (!lastProcessAt) return true;
  return nowMs - lastProcessAt >= cooldownMs;
}

export function createVadState() {
  return {
    noiseFloor: 0.008,
    speaking: false,
    speechStartAt: 0,
    lastSpeechAt: 0,
  };
}

/**
 * VAD năng lượng thích ứng — ngưỡng tự calibrate theo noise floor
 * @returns {{ noiseFloor, speaking, speechStartAt, lastSpeechAt, isSpeech, threshold, speechStarted, speechEnded, silentFor }}
 */
export function updateEnergyVad(state, rms, nowMs, options = {}) {
  const {
    hangoverMs = 350,
    thresholdMul = 2.4,
    minThreshold = 0.011,
    noiseAlpha = 0.08,
  } = options;

  const next = { ...state };

  if (!next.speaking && rms < next.noiseFloor * 1.6) {
    next.noiseFloor = next.noiseFloor * (1 - noiseAlpha) + rms * noiseAlpha;
  }

  const threshold = Math.max(minThreshold, next.noiseFloor * thresholdMul);
  const isSpeech = rms > threshold;

  let speechStarted = false;
  let speechEnded = false;
  let silentFor = 0;

  if (isSpeech) {
    if (!next.speaking) {
      next.speaking = true;
      next.speechStartAt = nowMs;
      speechStarted = true;
    }
    next.lastSpeechAt = nowMs;
  } else if (next.speaking) {
    silentFor = nowMs - next.lastSpeechAt;
    if (silentFor >= hangoverMs) {
      const duration = next.lastSpeechAt - next.speechStartAt;
      if (duration >= MIN_SPEECH_MS) {
        speechEnded = true;
      }
      next.speaking = false;
    }
  }

  return {
    ...next,
    isSpeech,
    threshold,
    speechStarted,
    speechEnded,
    silentFor,
  };
}

export function buildUtteranceBlob(chunks, mimeType = 'audio/webm') {
  const valid = (chunks || []).filter((c) => c?.size > 0);
  if (!valid.length) return null;
  return new Blob(valid.slice(-12), { type: mimeType });
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
