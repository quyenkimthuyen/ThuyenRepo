/**
 * Pure logic — dùng chung app + unit tests
 */

export const PRACTICE_MODE = { TEXT: 'text', SCORE: 'score' };

export const MIC_STATE = {
  OFF: 'off',
  READY: 'ready',
  HEARING: 'hearing',
  PROCESSING: 'processing',
  BUSY: 'busy',
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

/** Nhóm chính tả tương đương (Anh–Mỹ, SR hay nhầm) */
const SPELLING_VARIANT_GROUPS = [
  ['liveable', 'livable'],
  ['colour', 'color'],
  ['favourite', 'favorite'],
  ['behaviour', 'behavior'],
  ['honour', 'honor'],
  ['labour', 'labor'],
  ['neighbour', 'neighbor'],
  ['theatre', 'theater'],
  ['centre', 'center'],
  ['metre', 'meter'],
  ['organise', 'organize'],
  ['organised', 'organized'],
  ['recognise', 'recognize'],
  ['realise', 'realize'],
];

const SPELLING_VARIANT_LOOKUP = new Map();
for (const group of SPELLING_VARIANT_GROUPS) {
  for (const form of group) {
    if (!SPELLING_VARIANT_LOOKUP.has(form)) {
      SPELLING_VARIANT_LOOKUP.set(form, new Set(group));
    } else {
      for (const alt of group) SPELLING_VARIANT_LOOKUP.get(form).add(alt);
    }
  }
}

/** Sinh các biến thể chính tả chấp nhận được của một token */
export function expandTokenSpellingVariants(token) {
  const variants = new Set([token]);
  const mapped = SPELLING_VARIANT_LOOKUP.get(token);
  if (mapped) mapped.forEach((v) => variants.add(v));

  // liveable ↔ livable (e trước -able)
  if (token.endsWith('eable') && token.length > 5) {
    variants.add(`${token.slice(0, -5)}able`);
  }
  if (token.endsWith('able') && !token.endsWith('eable')) {
    const stem = token.slice(0, -4);
    if (stem.length >= 2) variants.add(`${stem}eable`);
  }

  // -ise ↔ -ize, -isation ↔ -ization
  if (token.endsWith('isation')) {
    variants.add(`${token.slice(0, -7)}ization`);
  } else if (token.endsWith('ization')) {
    variants.add(`${token.slice(0, -7)}isation`);
  } else if (token.endsWith('ise')) {
    variants.add(`${token.slice(0, -3)}ize`);
  } else if (token.endsWith('ize')) {
    variants.add(`${token.slice(0, -3)}ise`);
  } else if (token.endsWith('ised')) {
    variants.add(`${token.slice(0, -4)}ized`);
  } else if (token.endsWith('ized')) {
    variants.add(`${token.slice(0, -4)}ised`);
  }

  return variants;
}

export function tokensSpellingMatch(spokenToken, targetToken) {
  if (spokenToken === targetToken) return true;
  const spokenVars = expandTokenSpellingVariants(spokenToken);
  const targetVars = expandTokenSpellingVariants(targetToken);
  for (const s of spokenVars) {
    if (targetVars.has(s)) return true;
  }
  return false;
}

/** Động từ / mở đầu SR hay thêm — không coi là khớp nếu đứng trước từ mục tiêu */
const TEXT_PREFIX_BLOCK = new Set([
  'say', 'repeat', 'read', 'spell', 'pronounce', 'define', 'what', 'is', 'its', "it's",
]);

/** Gom token lặp liên tiếp: "timetable timetable" → "timetable" */
export function collapseConsecutiveTokens(tokens) {
  const out = [];
  for (const t of tokens) {
    if (!t) continue;
    if (out[out.length - 1] !== t) out.push(t);
  }
  return out;
}

/** Cụm mục tiêu không khoảng trắng: "viet nam" → "vietnam" */
export function compactPhrase(tokens) {
  return tokens.filter(Boolean).join('');
}

/** SR gộp cả cụm thành một token */
export function singleTokenMatchesPhrase(token, targetTokens) {
  if (!token || !targetTokens.length) return false;
  return tokensSpellingMatch(token, compactPhrase(targetTokens));
}

/** Chỉ xét đuôi transcript — tránh SR tích lũy cả câu dài */
export function tailTokensForMatch(spokenTokens, targetTokenCount, margin = 5) {
  const keep = Math.max(targetTokenCount + margin, 8);
  if (spokenTokens.length <= keep) return spokenTokens;
  return spokenTokens.slice(-keep);
}

function phrasePrefixAllowed(prefix, targetTokens) {
  if (prefix.length === 0) return true;
  if (prefix.some((t) => TEXT_PREFIX_BLOCK.has(t))) return false;
  return prefix.every(
    (t) => t.length <= 4 && !tokensSpellingMatch(t, targetTokens[0]),
  );
}

/**
 * Tìm cửa sổ khớp cụm mục tiêu (token rời hoặc SR gộp "vietnam" cho "Viet Nam").
 * @returns {{ start: number, end: number } | null}
 */
export function findPhraseMatchSpan(spokenTokens, targetTokens) {
  if (!spokenTokens.length || !targetTokens.length) return null;

  const n = targetTokens.length;
  const compact = compactPhrase(targetTokens);

  for (let i = 0; i < spokenTokens.length; i += 1) {
    if (singleTokenMatchesPhrase(spokenTokens[i], targetTokens)) {
      if (phrasePrefixAllowed(spokenTokens.slice(0, i), targetTokens)) {
        return { start: i, end: i + 1 };
      }
    }
  }

  for (let i = 0; i <= spokenTokens.length - n; i += 1) {
    const window = spokenTokens.slice(i, i + n);
    if (window.every((tok, j) => tokensSpellingMatch(tok, targetTokens[j]))) {
      if (phrasePrefixAllowed(spokenTokens.slice(0, i), targetTokens)) {
        return { start: i, end: i + n };
      }
    }
  }

  for (let i = 0; i < spokenTokens.length; i += 1) {
    let acc = '';
    for (let j = i; j < spokenTokens.length; j += 1) {
      acc += spokenTokens[j];
      if (acc.length > compact.length) break;
      if (tokensSpellingMatch(acc, compact)) {
        if (phrasePrefixAllowed(spokenTokens.slice(0, i), targetTokens)) {
          return { start: i, end: j + 1 };
        }
      }
    }
  }

  return null;
}

export function findPhraseWindowMatch(spokenTokens, targetTokens) {
  return findPhraseMatchSpan(spokenTokens, targetTokens) != null;
}

export function prepareSpokenTokensForMatch(spoken, target) {
  const targetTokens = normalizeTextForMatch(target).split(' ').filter(Boolean);
  let spokenTokens = collapseConsecutiveTokens(
    normalizeTextForMatch(spoken).split(' ').filter(Boolean),
  );
  spokenTokens = stripLeadingArticles(spokenTokens);
  spokenTokens = tailTokensForMatch(spokenTokens, targetTokens.length);
  return { spokenTokens, targetTokens };
}

/** Đoạn transcript đáng hiển thị / chấm — không cả câu SR lặp vô hạn */
export function extractPracticeMatchSnippet(spoken, target) {
  const { spokenTokens, targetTokens } = prepareSpokenTokensForMatch(spoken, target);
  if (!spokenTokens.length) return '';
  const span = findPhraseMatchSpan(spokenTokens, targetTokens);
  if (span) return spokenTokens.slice(span.start, span.end).join(' ');
  return spokenTokens.slice(-Math.max(targetTokens.length, 3)).join(' ');
}

/** Bỏ mạo từ đầu câu do SR thêm: "the living room" */
export function stripLeadingArticles(tokens) {
  const articles = new Set(['the', 'a', 'an']);
  let i = 0;
  while (i < tokens.length && articles.has(tokens[i])) i += 1;
  return tokens.slice(i);
}

/** Chế độ text: khớp 100% — cụm từ/câu + biến thể chính tả (liveable/livable) */
export function textMatchExact(spoken, target) {
  const s = normalizeTextForMatch(spoken);
  const t = normalizeTextForMatch(target);
  if (!s || !t) return false;
  if (s === t) return true;

  const spokenTokens = s.split(' ');
  const targetTokens = t.split(' ');
  if (spokenTokens.length !== targetTokens.length) return false;

  return spokenTokens.every((tok, i) => tokensSpellingMatch(tok, targetTokens[i]));
}

/**
 * Chế độ text khi luyện tập — strict trước, sau đó chịu SR nhiễu/lặp:
 * dedupe, bỏ mạo từ, khớp cụm mục tiêu ở cuối nếu tiền tố là rác ngắn.
 */
export function textMatchPractice(spoken, target) {
  if (textMatchExact(spoken, target)) return true;

  const { spokenTokens, targetTokens } = prepareSpokenTokensForMatch(spoken, target);
  if (!targetTokens.length || !spokenTokens.length) return false;

  if (textMatchExact(spokenTokens.join(' '), target)) return true;
  if (findPhraseWindowMatch(spokenTokens, targetTokens)) return true;

  if (spokenTokens.length < targetTokens.length) return false;

  const suffix = spokenTokens.slice(-targetTokens.length);
  if (!suffix.every((tok, i) => tokensSpellingMatch(tok, targetTokens[i]))) {
    return false;
  }

  const prefix = spokenTokens.slice(0, -targetTokens.length);
  return phrasePrefixAllowed(prefix, targetTokens);
}

function levenshteinDistance(a, b) {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 0; i < a.length; i += 1) {
    const curr = [i + 1];
    for (let j = 0; j < b.length; j += 1) {
      const cost = a[i] === b[j] ? 0 : 1;
      curr[j + 1] = Math.min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost);
    }
    prev = curr;
  }
  return prev[b.length];
}

/** Độ giống chuỗi 0–100 (Levenshtein) */
export function similarityPercent(a, b) {
  const x = normalizeTextForMatch(a);
  const y = normalizeTextForMatch(b);
  if (!x || !y) return 0;
  if (x === y) return 100;
  const dist = levenshteinDistance(x, y);
  const maxLen = Math.max(x.length, y.length);
  return Math.round((1 - dist / maxLen) * 100);
}

/**
 * % khớp text — ưu tiên khớp practice, sau đó so suffix SR (nhiễu đầu câu).
 */
export function textSimilarityPercent(spoken, target) {
  if (textMatchPractice(spoken, target)) return 100;

  const { spokenTokens, targetTokens } = prepareSpokenTokensForMatch(spoken, target);
  const targetNorm = normalizeTextForMatch(target);
  if (!targetNorm) return 0;

  let best = similarityPercent(spoken, target);

  const snippet = extractPracticeMatchSnippet(spoken, target);
  if (snippet) best = Math.max(best, similarityPercent(snippet, targetNorm));

  const compact = compactPhrase(targetTokens);
  for (const tok of spokenTokens) {
    if (singleTokenMatchesPhrase(tok, targetTokens)) {
      best = Math.max(best, similarityPercent(tok, compact));
    }
  }

  if (spokenTokens.length >= targetTokens.length) {
    const suffix = spokenTokens.slice(-targetTokens.length).join(' ');
    best = Math.max(best, similarityPercent(suffix, targetNorm));
  }

  return best;
}

/** Chế độ text: practice strict trước, sau đó % tương đồng ≥ ngưỡng (từ trùng âm / SR gần đúng) */
export function textMatchWithThreshold(spoken, target, threshold = 100) {
  if (textMatchPractice(spoken, target)) return true;
  if (threshold >= 100) return false;
  return textSimilarityPercent(spoken, target) >= threshold;
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
