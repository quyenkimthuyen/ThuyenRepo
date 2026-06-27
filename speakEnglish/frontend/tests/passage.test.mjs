import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  splitIntoSentences,
  tokenizeSentenceDisplay,
  countMatchedPrefixTokens,
} from '../js/core.js';
import {
  createPassageSession,
  renderPassageDisplay,
  updateSessionWordProgress,
  markCurrentSentenceComplete,
  advancePassageIndex,
  isPassageComplete,
} from '../js/passage.js';

describe('splitIntoSentences', () => {
  it('splits on sentence-ending punctuation', () => {
    const text = 'Hello world. How are you? I am fine!';
    assert.deepEqual(splitIntoSentences(text), [
      'Hello world.',
      'How are you?',
      'I am fine!',
    ]);
  });

  it('normalizes newlines to spaces', () => {
    assert.deepEqual(
      splitIntoSentences('First line.\nSecond line.'),
      ['First line.', 'Second line.'],
    );
  });

  it('returns empty for blank input', () => {
    assert.deepEqual(splitIntoSentences('   '), []);
  });
});

describe('countMatchedPrefixTokens', () => {
  it('counts progressive prefix matches', () => {
    const target = 'The quick brown fox';
    assert.equal(countMatchedPrefixTokens('the', target), 1);
    assert.equal(countMatchedPrefixTokens('the quick', target), 2);
    assert.equal(countMatchedPrefixTokens('the quick brown', target), 3);
    assert.equal(countMatchedPrefixTokens('the quick brown fox', target), 4);
  });

  it('uses suffix when SR accumulates transcript', () => {
    const target = 'Birds sing in the morning.';
    assert.equal(
      countMatchedPrefixTokens('noise birds sing in the morning birds sing in the morning', target),
      5,
    );
  });
});

describe('passage session', () => {
  it('renders matched words with highlight class', () => {
    let session = createPassageSession('Hello world. Goodbye.');
    session = updateSessionWordProgress(session, 'hello');
    const html = renderPassageDisplay(session);
    assert.match(html, /passage-word--matched/);
    assert.match(html, /passage-sentence--active/);
  });

  it('marks passage complete after all sentences', () => {
    let session = createPassageSession('One. Two.');
    markCurrentSentenceComplete(session);
    advancePassageIndex(session);
    markCurrentSentenceComplete(session);
    assert.equal(isPassageComplete(session), true);
  });
});

describe('tokenizeSentenceDisplay', () => {
  it('keeps punctuation on display tokens', () => {
    const tokens = tokenizeSentenceDisplay('Hello, world!');
    assert.equal(tokens[0].display, 'Hello,');
    assert.equal(tokens[0].normalized, 'hello');
    assert.equal(tokens[1].display, 'world!');
  });
});
