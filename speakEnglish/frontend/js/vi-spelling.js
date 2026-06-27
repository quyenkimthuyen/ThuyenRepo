/**
 * Đánh vần tiếng Việt từ IPA — nhấn âm (in hoa nguyên âm) và phụ âm cuối (hậu tố -X).
 */

const IPA_TOKEN_RE = /ˈ|ˌ|tʃ|dʒ|aʊ|aɪ|eɪ|oʊ|ɔɪ|ɜː|iː|uː|ɔː|./gu;

const VOWEL_PHONEMES = new Set([
  'iː', 'ɪ', 'eɪ', 'ɛ', 'æ', 'ɑ', 'ɒ', 'ɔː', 'ɔ', 'ʌ', 'ʊ', 'uː',
  'ə', 'ɜː', 'aɪ', 'aʊ', 'ɔɪ', 'oʊ', 'a', 'e', 'i', 'o', 'u',
]);

/** @type {Record<string, string>} */
const PHONEME_TO_VI = {
  p: 'p', b: 'b', t: 't', d: 'd', k: 'c', g: 'g',
  tʃ: 'ch', dʒ: 'j', f: 'ph', v: 'v', θ: 'th', ð: 'th',
  s: 's', z: 'z', ʃ: 'sh', ʒ: 'zh', h: 'h',
  m: 'm', n: 'n', ŋ: 'ng', l: 'l', r: 'r', w: 'w', j: 'y',
  iː: 'i', ɪ: 'i', eɪ: 'ây', ɛ: 'e', æ: 'a',
  ɑ: 'a', ɒ: 'o', ɔː: 'o', ɔ: 'o', ʌ: 'ă', ʊ: 'u', uː: 'u',
  ə: 'ơ', ɜː: 'ơ', aɪ: 'ai', aʊ: 'ao', ɔɪ: 'oi', oʊ: 'ô',
  a: 'a', e: 'e', i: 'i', o: 'o', u: 'u',
};

/** Phụ âm cuối — viết hoa để nổi bật */
const CODA_DISPLAY = {
  p: 'P', b: 'B', t: 'T', d: 'Đ', k: 'C', g: 'G',
  tʃ: 'CH', dʒ: 'J', f: 'PH', v: 'V', θ: 'TH', ð: 'TH',
  s: 'S', z: 'Z', ʃ: 'SH', ʒ: 'ZH', h: 'H',
  m: 'M', n: 'N', ŋ: 'NG', l: 'L', r: 'R',
};

function isVowel(phoneme) {
  return VOWEL_PHONEMES.has(phoneme);
}

/**
 * @param {string} ipa
 * @returns {{ phonemes: string[], primaryStressSyllable: number, secondaryStressSyllables: Set<number> }}
 */
export function parseIpaWithStress(ipa) {
  const clean = String(ipa || '').replace(/^\/+|\/+$/g, '').trim();
  const phonemes = [];
  let primaryStressSyllable = -1;
  const secondaryStressSyllables = new Set();
  let syllableIdx = -1;
  let pendingPrimary = false;
  let pendingSecondary = false;

  IPA_TOKEN_RE.lastIndex = 0;
  let match;
  while ((match = IPA_TOKEN_RE.exec(clean)) !== null) {
    const token = match[0];
    if (token === 'ˈ') {
      pendingPrimary = true;
      continue;
    }
    if (token === 'ˌ') {
      pendingSecondary = true;
      continue;
    }
    if (!token.trim()) continue;

    if (isVowel(token)) {
      syllableIdx += 1;
      if (pendingPrimary) {
        primaryStressSyllable = syllableIdx;
        pendingPrimary = false;
        pendingSecondary = false;
      } else if (pendingSecondary) {
        secondaryStressSyllables.add(syllableIdx);
        pendingSecondary = false;
      }
    }
    phonemes.push(token);
  }

  if (primaryStressSyllable < 0 && syllableIdx >= 0) {
    primaryStressSyllable = 0;
  }

  return { phonemes, primaryStressSyllable, secondaryStressSyllables };
}

/**
 * @param {string[]} phonemes
 * @param {number} primaryStressSyllable
 * @param {Set<number>} secondaryStressSyllables
 */
export function groupPhonemesIntoSyllables(phonemes, primaryStressSyllable, secondaryStressSyllables = new Set()) {
  const vowelIndices = phonemes
    .map((phoneme, index) => (isVowel(phoneme) ? index : -1))
    .filter((index) => index >= 0);

  if (!vowelIndices.length) return [];

  /** @type {Array<{ onset: string[], nucleus: string[], coda: string[], stress: 'primary'|'secondary'|null }>} */
  const syllables = [];

  for (let v = 0; v < vowelIndices.length; v += 1) {
    const vowelIndex = vowelIndices[v];
    const isLast = v === vowelIndices.length - 1;
    const onsetStart = v === 0 ? 0 : vowelIndices[v - 1] + 1;
    const onset = phonemes.slice(onsetStart, vowelIndex);
    const nucleus = [phonemes[vowelIndex]];
    const coda = isLast ? phonemes.slice(vowelIndex + 1) : [];

    let stress = null;
    if (v === primaryStressSyllable) stress = 'primary';
    else if (secondaryStressSyllables.has(v)) stress = 'secondary';

    syllables.push({ onset, nucleus, coda, stress });
  }

  return syllables;
}

function romanizePhoneme(phoneme) {
  return PHONEME_TO_VI[phoneme] || phoneme;
}

function capitalizeVowels(text) {
  return text.replace(/[aeiouăâêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/gi, (ch) => ch.toUpperCase());
}

function formatCoda(coda) {
  if (!coda.length) return '';
  const parts = coda.map((p) => CODA_DISPLAY[p] || romanizePhoneme(p).toUpperCase());
  return `-${parts.join('')}`;
}

/**
 * @param {{ onset: string[], nucleus: string[], coda: string[], stress: string|null }} syllable
 */
export function romanizeSyllable(syllable) {
  const onsetStr = syllable.onset.map(romanizePhoneme).join('');
  let nucleusStr = syllable.nucleus.map(romanizePhoneme).join('');
  const emphasizeVowel = syllable.stress && !syllable.coda.length;
  if (emphasizeVowel) {
    nucleusStr = capitalizeVowels(nucleusStr);
  }
  const body = onsetStr + nucleusStr;
  const coda = formatCoda(syllable.coda);
  return { body, coda, stress: syllable.stress };
}

/**
 * @param {string} ipa
 * @param {string[]|null} [phonemes]
 * @returns {Array<{ body: string, coda: string, stress: string|null, display: string }>}
 */
export function ipaToViSyllables(ipa, phonemes = null) {
  const parsed = parseIpaWithStress(ipa);
  const phones = phonemes?.length ? phonemes : parsed.phonemes;
  const syllables = groupPhonemesIntoSyllables(
    phones,
    parsed.primaryStressSyllable,
    parsed.secondaryStressSyllables,
  );
  return syllables.map((syllable) => {
    const { body, coda, stress } = romanizeSyllable(syllable);
    return { body, coda, stress, display: `${body}${coda}` };
  });
}

/**
 * @param {{ ipa?: string, phonemes?: string[], vi_spell?: string, vi_syllables?: Array<{body?:string,coda?:string,stress?:string}> }} word
 */
export function getWordViSpelling(word) {
  if (!word) return { syllables: [], text: '—' };

  if (word.vi_syllables?.length) {
    const syllables = word.vi_syllables.map((s) => ({
      body: s.body || '',
      coda: s.coda || '',
      stress: s.stress || null,
      display: `${s.body || ''}${s.coda || ''}`,
    }));
    return { syllables, text: syllables.map((s) => s.display).join('-') };
  }

  if (word.vi_spell) {
    return { syllables: [], text: word.vi_spell };
  }

  const syllables = ipaToViSyllables(word.ipa || '', word.phonemes || null);
  return {
    syllables,
    text: syllables.map((s) => s.display).join('-') || '—',
  };
}

/**
 * @param {HTMLElement|null} container
 * @param {{ ipa?: string, phonemes?: string[], vi_spell?: string, vi_syllables?: Array }} word
 */
export function renderViSpellingStrip(container, word) {
  if (!container) return;
  const { syllables, text } = getWordViSpelling(word);
  container.replaceChildren();

  if (!syllables.length) {
    const pill = document.createElement('p');
    pill.className = 'vi-spell-pill';
    pill.textContent = text;
    pill.title = 'Đánh vần tiếng Việt';
    container.appendChild(pill);
    return;
  }

  const strip = document.createElement('div');
  strip.className = 'vi-syllable-strip';
  strip.setAttribute('role', 'list');
  strip.setAttribute('aria-label', 'Đánh vần tiếng Việt');

  syllables.forEach((syllable, index) => {
    const chip = document.createElement('span');
    chip.className = 'vi-syllable-chip';
    chip.setAttribute('role', 'listitem');
    if (syllable.stress === 'primary') chip.classList.add('vi-syllable-stress');
    if (syllable.stress === 'secondary') chip.classList.add('vi-syllable-stress-secondary');

    const body = document.createElement('span');
    body.className = 'vi-syllable-body';
    body.textContent = syllable.body;
    chip.appendChild(body);

    if (syllable.coda) {
      const coda = document.createElement('span');
      coda.className = 'vi-syllable-coda';
      coda.textContent = syllable.coda;
      coda.title = 'Phụ âm cuối';
      chip.appendChild(coda);
    }

    strip.appendChild(chip);

    if (index < syllables.length - 1) {
      const sep = document.createElement('span');
      sep.className = 'vi-syllable-sep';
      sep.setAttribute('aria-hidden', 'true');
      sep.textContent = '-';
      strip.appendChild(sep);
    }
  });

  container.appendChild(strip);
}
