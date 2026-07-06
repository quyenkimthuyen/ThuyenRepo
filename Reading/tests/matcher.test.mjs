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

// hyphenated words: tokenization and matching
const t5 = tokenizeSentence('I learn food-related words.');
assert(t5.length === 5, 'splits food-related into food- and related (5 tokens total)');
assert(t5[2].display === 'food-', 'hyphenated first part display');
assert(t5[2].normalized === 'food', 'hyphenated first part normalized');
assert(t5[2].hasSpaceAfter === false, 'hyphenated first part hasSpaceAfter false');
assert(t5[3].display === 'related', 'hyphenated second part display');
assert(t5[3].normalized === 'related', 'hyphenated second part normalized');
assert(t5[3].hasSpaceAfter === true, 'hyphenated second part hasSpaceAfter true');

const m5 = new Set();
matchAccumulating(wordsFromTranscript('I learn food related words'), t5, m5);
assert(isSentenceComplete(m5, t5.length), 'matches split words');

const m6 = new Set();
matchAccumulating(wordsFromTranscript('I learn food-related words'), t5, m6);
assert(isSentenceComplete(m6, t5.length), 'matches hyphenated spoken words');

const t6 = tokenizeSentence('I learn food related words.');
const m7 = new Set();
matchAccumulating(wordsFromTranscript('I learn food-related words'), t6, m7);
assert(isSentenceComplete(m7, t6.length), 'matches hyphenated spoken words to split sentence tokens');

// spelling variations (US vs UK English)
assert(wordsMatch('travelling', 'traveling'), 'travelling matches traveling');
assert(wordsMatch('cancelled', 'canceled'), 'cancelled matches canceled');
assert(wordsMatch('colour', 'color'), 'colour matches color');
assert(wordsMatch('centre', 'center'), 'centre matches center');
assert(wordsMatch('realise', 'realize'), 'realise matches realize');
assert(wordsMatch('organisation', 'organization'), 'organisation matches organization');
assert(wordsMatch('analyse', 'analyze'), 'analyse matches analyze');
assert(wordsMatch('defence', 'defense'), 'defence matches defense');
assert(wordsMatch('dialogue', 'dialog'), 'dialogue matches dialog');

// spelling variations edge cases / preservation of numbers and short words
assert(wordsMatch('four', 'four'), 'four matches four');
assert(!wordsMatch('four', 'for'), 'four does not match for');
assert(wordsMatch('four', '4'), 'four matches 4');
assert(wordsMatch('hour', 'hour'), 'hour matches hour');
assert(!wordsMatch('hour', 'hor'), 'hour does not match hor');
assert(wordsMatch('sour', 'sour'), 'sour matches sour');
assert(!wordsMatch('sour', 'sor'), 'sour does not match sor');

console.log('matcher tests: ok');
