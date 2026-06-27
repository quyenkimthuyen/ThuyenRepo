/**
 * Chế độ đọc đoạn văn — tách câu, theo dõi tiến độ từng từ, render highlight
 */

import {
  splitIntoSentences,
  tokenizeSentenceDisplay,
  countMatchedPrefixTokens,
  normalizeTextForMatch,
} from './core.js';

export const PASSAGE_SESSION_KEY = 'pronouncelab_passage_session';

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function createPassageSession(rawText) {
  const trimmed = String(rawText || '').trim();
  const sentences = splitIntoSentences(trimmed).map((text, index) => ({
    index,
    text,
    tokens: tokenizeSentenceDisplay(text),
    completed: false,
    matchedWordCount: 0,
  }));

  return {
    rawText: trimmed,
    sentences,
    currentIndex: 0,
  };
}

export function getSentenceWordCount(sentence) {
  return sentence?.tokens?.filter((t) => t.isWord).length ?? 0;
}

export function getCurrentSentence(session) {
  if (!session?.sentences?.length) return null;
  return session.sentences[session.currentIndex] ?? null;
}

export function updateSessionWordProgress(session, spoken) {
  const sentence = getCurrentSentence(session);
  if (!sentence || sentence.completed) return session;

  const matched = countMatchedPrefixTokens(spoken, sentence.text);
  sentence.matchedWordCount = Math.min(matched, getSentenceWordCount(sentence));
  return session;
}

export function markCurrentSentenceComplete(session) {
  const sentence = getCurrentSentence(session);
  if (sentence) {
    sentence.completed = true;
    sentence.matchedWordCount = getSentenceWordCount(sentence);
  }
  return session;
}

export function advancePassageIndex(session) {
  if (!session?.sentences?.length) return session;
  if (session.currentIndex < session.sentences.length - 1) {
    session.currentIndex += 1;
  }
  return session;
}

export function isPassageComplete(session) {
  if (!session?.sentences?.length) return false;
  return session.sentences.every((s) => s.completed);
}

export function renderPassageDisplay(session) {
  if (!session?.sentences?.length) {
    return '<p class="passage-empty">Chưa có đoạn văn.</p>';
  }

  return session.sentences.map((sentence, si) => {
    const isActive = si === session.currentIndex && !sentence.completed;
    const classes = ['passage-sentence'];
    if (sentence.completed) classes.push('passage-sentence--done');
    if (isActive) classes.push('passage-sentence--active');

    let wordIdx = 0;
    const wordHtml = sentence.tokens.map((token) => {
      if (!token.isWord) {
        return `<span class="passage-punct">${escapeHtml(token.display)}</span>`;
      }
      const classes = ['passage-word'];
      if (sentence.completed || wordIdx < sentence.matchedWordCount) {
        classes.push('passage-word--matched');
      } else if (isActive && wordIdx === sentence.matchedWordCount) {
        classes.push('passage-word--current');
      }
      wordIdx += 1;
      return `<span class="${classes.join(' ')}">${escapeHtml(token.display)}</span>`;
    }).join(' ');

    return `<p class="${classes.join(' ')}" data-sentence-index="${si}">${wordHtml}</p>`;
  }).join('');
}

export function serializePassageSession(session) {
  if (!session?.rawText) return null;
  return {
    rawText: session.rawText,
    currentIndex: session.currentIndex,
    sentences: session.sentences.map((s) => ({
      text: s.text,
      completed: s.completed,
      matchedWordCount: s.matchedWordCount,
    })),
  };
}

export function deserializePassageSession(data) {
  if (!data?.rawText) return null;
  const session = createPassageSession(data.rawText);
  data.sentences?.forEach((saved, i) => {
    const sentence = session.sentences[i];
    if (!sentence || sentence.text !== saved.text) return;
    sentence.completed = Boolean(saved.completed);
    sentence.matchedWordCount = Number(saved.matchedWordCount) || 0;
  });
  session.currentIndex = Math.min(
    Math.max(0, Number(data.currentIndex) || 0),
    Math.max(0, session.sentences.length - 1),
  );
  return session;
}
