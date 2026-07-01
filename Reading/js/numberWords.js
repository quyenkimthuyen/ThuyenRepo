/** @type {Record<string, number>} */
const WORD_TO_NUM = {
  zero: 0,
  one: 1,
  two: 2,
  three: 3,
  four: 4,
  five: 5,
  six: 6,
  seven: 7,
  eight: 8,
  nine: 9,
  ten: 10,
  eleven: 11,
  twelve: 12,
  thirteen: 13,
  fourteen: 14,
  fifteen: 15,
  sixteen: 16,
  seventeen: 17,
  eighteen: 18,
  nineteen: 19,
  twenty: 20,
  thirty: 30,
  forty: 40,
  fifty: 50,
  sixty: 60,
  seventy: 70,
  eighty: 80,
  ninety: 90,
};

/**
 * Canonical key for matching: "twenty" and "20" both become "n:20".
 * @param {string} word - normalized word
 * @returns {string}
 */
export function matchKey(word) {
  if (/^\d+$/.test(word)) {
    return `n:${parseInt(word, 10)}`;
  }
  const n = WORD_TO_NUM[word];
  if (n !== undefined) {
    return `n:${n}`;
  }
  return word;
}

/**
 * @param {string} a - normalized spoken word
 * @param {string} b - normalized token word
 * @returns {boolean}
 */
export function wordsMatch(a, b) {
  return matchKey(a) === matchKey(b);
}
