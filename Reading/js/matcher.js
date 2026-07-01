import { wordsMatch } from './numberWords.js';

/**
 * Tokenize a sentence into display tokens (word + trailing punctuation).
 * @param {string} sentence
 * @returns {{ display: string, normalized: string }[]}
 */
export function tokenizeSentence(sentence) {
  const re = /\S+/g;
  const tokens = [];
  let m;
  while ((m = re.exec(sentence)) !== null) {
    const display = m[0];
    tokens.push({
      display,
      normalized: normalizeWord(display),
    });
  }
  return tokens;
}

/**
 * @param {string} raw
 * @returns {string}
 */
export function normalizeWord(raw) {
  return raw
    .toLowerCase()
    .replace(/^[^a-z0-9']+/i, '')
    .replace(/[^a-z0-9']+$/i, '');
}

/**
 * Split transcript into normalized words, skipping empties.
 * @param {string} transcript
 * @returns {string[]}
 */
export function wordsFromTranscript(transcript) {
  return transcript
    .split(/\s+/)
    .map(normalizeWord)
    .filter(Boolean);
}

/**
 * Try to match spoken words against unmatched tokens in the current sentence.
 * Returns indices newly matched this call.
 *
 * @param {string[]} spokenWords - words from ASR chunk
 * @param {{ normalized: string }[]} sentenceTokens
 * @param {Set<number>} matchedIndices - already matched token indices
 * @returns {number[]} newly matched indices
 */
export function matchAccumulating(spokenWords, sentenceTokens, matchedIndices) {
  const newlyMatched = [];

  for (const spoken of spokenWords) {
    if (!spoken) continue;

    for (let i = 0; i < sentenceTokens.length; i++) {
      if (matchedIndices.has(i)) continue;
      if (wordsMatch(spoken, sentenceTokens[i].normalized)) {
        matchedIndices.add(i);
        newlyMatched.push(i);
        break;
      }
    }
  }

  return newlyMatched;
}

/**
 * @param {Set<number>} matchedIndices
 * @param {number} tokenCount
 * @returns {boolean}
 */
export function isSentenceComplete(matchedIndices, tokenCount) {
  return tokenCount > 0 && matchedIndices.size >= tokenCount;
}
