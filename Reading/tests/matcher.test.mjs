import {
  tokenizeSentence,
  normalizeWord,
  wordsFromTranscript,
  matchAccumulating,
  isSentenceComplete,
} from '../js/matcher.js';
import { wordsMatch } from '../js/numberWords.js';

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

// normalize
assert(normalizeWord("six.") === 'six', 'strip trailing punct');
assert(normalizeWord("'clock") === "'clock", 'keep apostrophe word');

// tokenize
const tokens = tokenizeSentence("I wake up at six.");
assert(tokens.length === 5, 'five tokens');
assert(tokens[0].normalized === 'i', 'first word');

// accumulate out of order
const matched = new Set();
const spoken1 = wordsFromTranscript('wake I up');
matchAccumulating(spoken1, tokens, matched);
assert(matched.size === 3, 'three words matched out of order');
assert(!matched.has(3), 'at not yet');

const spoken2 = wordsFromTranscript('at six');
matchAccumulating(spoken2, tokens, matched);
assert(isSentenceComplete(matched, tokens.length), 'sentence complete');

// ignore wrong words
const t2 = tokenizeSentence('hello world');
const m2 = new Set();
matchAccumulating(wordsFromTranscript('foo hello bar world baz'), t2, m2);
assert(m2.size === 2, 'only correct words matched');

// each slot once
const t3 = tokenizeSentence('I I wake');
const m3 = new Set();
matchAccumulating(wordsFromTranscript('I I I wake'), t3, m3);
assert(m3.size === 3, 'two I slots + wake');

// number words: ASR often returns digits
assert(wordsMatch('20', 'twenty'), 'twenty matches 20');
assert(wordsMatch('6', 'six'), 'six matches 6');
const t4 = tokenizeSentence('I am twenty years old.');
const m4 = new Set();
matchAccumulating(wordsFromTranscript('I am 20 years old'), t4, m4);
assert(m4.size === 5, 'digit 20 matches word twenty');

console.log('matcher tests: ok');
