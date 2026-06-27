import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseIpaWithStress,
  groupPhonemesIntoSyllables,
  ipaToViSyllables,
  getWordViSpelling,
} from '../js/vi-spelling.js';

describe('parseIpaWithStress', () => {
  it('marks primary stress syllable index', () => {
    const parsed = parseIpaWithStress('/həˈloʊ/');
    assert.equal(parsed.primaryStressSyllable, 1);
    assert.deepEqual(parsed.phonemes, ['h', 'ə', 'l', 'oʊ']);
  });

  it('defaults stress to first syllable when no marker', () => {
    const parsed = parseIpaWithStress('/wɜːld/');
    assert.equal(parsed.primaryStressSyllable, 0);
  });
});

describe('ipaToViSyllables', () => {
  it('hello — nhấn âm âm tiết thứ hai', () => {
    const syllables = ipaToViSyllables('/həˈloʊ/', ['h', 'ə', 'l', 'oʊ']);
    assert.equal(syllables.length, 2);
    assert.equal(syllables[0].body, 'hơ');
    assert.equal(syllables[1].body, 'lÔ');
    assert.equal(syllables[1].stress, 'primary');
  });

  it('think — phụ âm cuối -C', () => {
    const syllables = ipaToViSyllables('/θɪŋk/', ['θ', 'ɪ', 'ŋ', 'k']);
    assert.equal(syllables.length, 1);
    assert.equal(syllables[0].body, 'thi');
    assert.equal(syllables[0].coda, '-NGC');
  });

  it('world — phụ âm cuối -LĐ', () => {
    const syllables = ipaToViSyllables('/wɜːld/', ['w', 'ɜː', 'l', 'd']);
    assert.equal(syllables.length, 1);
    assert.match(syllables[0].coda, /Đ/);
  });

  it('station — nhấn âm âm tiết đầu', () => {
    const syllables = ipaToViSyllables('/ˈsteɪʃən/', ['s', 't', 'eɪ', 'ʃ', 'ə', 'n']);
    assert.equal(syllables[0].stress, 'primary');
    assert.match(syllables[0].body, /ÂY|Ây/i);
  });
});

describe('getWordViSpelling', () => {
  it('prefers vi_spell when provided', () => {
    const result = getWordViSpelling({ ipa: '/həˈloʊ/', vi_spell: 'hê-LÔ' });
    assert.equal(result.text, 'hê-LÔ');
  });

  it('prefers vi_syllables when provided', () => {
    const result = getWordViSpelling({
      vi_syllables: [
        { body: 'hê', stress: null },
        { body: 'LÔ', stress: 'primary' },
      ],
    });
    assert.equal(result.text, 'hê-LÔ');
    assert.equal(result.syllables.length, 2);
  });
});
