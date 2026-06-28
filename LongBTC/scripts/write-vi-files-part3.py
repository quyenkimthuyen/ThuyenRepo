from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def w(rel, s):
    text = s.encode("utf-8").decode("unicode_escape")
    (ROOT / rel).write_text(text, encoding="utf-8")
    print(rel, "OK" if "\ufffd" not in text and "??" not in text else "CHECK")


w(
    "src/content/longbtcDocsVi.js",
    r"""
/**
 * LongBTC in-app documentation (Vietnamese).
 * @module content/longbtcDocsVi
 */

import { Config } from '../core/Config.js';

/**
 * @typedef {Object} DocBlock
 * @property {'h2'|'h3'|'p'|'ul'|'ol'|'callout'} type
 * @property {string} [text]
 * @property {string[]} [items]
 * @property {'info'|'warn'|'tip'} [variant]
 */

/**
 * @typedef {Object} DocSection
 * @property {string} id
 * @property {string} title
 * @property {string} [subtitle]
 * @property {string} [icon]
 * @property {string[]} [viewIds]
 * @property {DocBlock[]} blocks
 */

/** @type {DocSection[]} */
export const LONG_BTC_DOC_SECTIONS = [
  {
    id: 'overview',
    title: 'T\u1ed5ng quan LongBTC',
    subtitle: 'N\u1ec1n t\u1ea3ng nghi\u00ean c\u1ee9u \u0111\u1ea7u t\u01b0 BTC d\u00e0i h\u1ea1n',
    icon: '\u20bf',
    viewIds: ['dashboard'],
    blocks: [
      {
        type: 'p',
        text: `${Config.APP_NAME} gi\u00fap nghi\u00ean c\u1ee9u chu k\u1ef3 Bitcoin theo pipeline: Chu k\u1ef3 halving 4 n\u0103m \u2192 Xu h\u01b0\u1edbng t\u0103ng/gi\u1ea3m/\u0111i ngang \u2192 S\u00f3ng Elliott \u2192 Chu k\u1ef3 t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng.`,
      },
      {
        type: 'callout',
        variant: 'warn',
        text: '\u0110\u00e2y l\u00e0 c\u00f4ng c\u1ee5 nghi\u00ean c\u1ee9u, KH\u00d4NG ph\u1ea3i l\u1eddi khuy\u00ean \u0111\u1ea7u t\u01b0. Qu\u00e1 kh\u1ee9 kh\u00f4ng \u0111\u1ea3m b\u1ea3o t\u01b0\u01a1ng lai.',
      },
      {
        type: 'h3',
        text: 'Quy tr\u00ecnh ph\u00e2n t\u00edch',
      },
      {
        type: 'ol',
        items: [
          'X\u00e1c \u0111\u1ecbnh v\u1ecb tr\u00ed trong chu k\u1ef3 halving 4 n\u0103m',
          'Ph\u00e2n t\u00edch xu h\u01b0\u1edbng qua c\u1ea5u tr\u00fac swing (HH/HL, LH/LL)',
          '\u0110\u1ebfm s\u00f3ng Elliott tr\u00ean c\u00e1c \u0111o\u1ea1n xu h\u01b0\u1edbng',
          '\u00c1nh x\u1ea1 sang giai \u0111o\u1ea1n t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
        ],
      },
    ],
  },
  {
    id: 'chart',
    title: 'Bi\u1ec3u \u0111\u1ed3 BTC',
    icon: '\U0001f4c8',
    viewIds: ['chart'],
    blocks: [
      {
        type: 'p',
        text: 'Bi\u1ec3u \u0111\u1ed3 n\u1ebfn BTC v\u1edbi overlay ph\u00e2n t\u00edch: swing pivot, \u0111o\u1ea1n xu h\u01b0\u1edbng, \u0111\u1ec9nh/\u0111\u00e1y chu k\u1ef3. Khuy\u1ebfn ngh\u1ecb d\u00f9ng khung W (tu\u1ea7n) ho\u1eb7c D1 (ng\u00e0y) cho ph\u00e2n t\u00edch d\u00e0i h\u1ea1n.',
      },
      {
        type: 'ul',
        items: [
          'B\u1eadt/t\u1eaft overlay Swing, Xu h\u01b0\u1edbng, Chu k\u1ef3 tr\u00ean toolbar',
          'EMA 200 h\u1ed7 tr\u1ee3 x\u00e1c nh\u1eadn xu h\u01b0\u1edbng d\u00e0i h\u1ea1n',
          'Replay: ph\u00e2n t\u00edch t\u1eebng giai \u0111o\u1ea1n l\u1ecbch s\u1eed',
        ],
      },
    ],
  },
  {
    id: 'cycle',
    title: 'Chu k\u1ef3 4 n\u0103m',
    icon: '\u23f1',
    viewIds: ['cycle'],
    blocks: [
      {
        type: 'p',
        text: 'Bitcoin halving x\u1ea3y ra kho\u1ea3ng 4 n\u0103m/l\u1ea7n, gi\u1ea3m m\u1ed9t n\u1eeda ph\u1ea7n th\u01b0\u1edfng kh\u1ed1i. Chu k\u1ef3 th\u01b0\u1eddng c\u00f3 4 giai \u0111o\u1ea1n: T\u00edch l\u0169y \u2192 T\u0103ng tr\u01b0\u1edfng \u2192 Ph\u00e2n ph\u1ed1i \u2192 Gi\u1ea3m gi\u00e1.',
      },
      {
        type: 'ul',
        items: [
          'Halving #1: 28/11/2012',
          'Halving #2: 09/07/2016',
          'Halving #3: 11/05/2020',
          'Halving #4: 20/04/2024',
        ],
      },
    ],
  },
  {
    id: 'trend',
    title: 'Xu h\u01b0\u1edbng',
    icon: '\U0001f4ca',
    viewIds: ['trend'],
    blocks: [
      {
        type: 'p',
        text: 'Xu h\u01b0\u1edbng \u0111\u01b0\u1ee3c x\u00e1c \u0111\u1ecbnh qua swing pivot (zigzag) v\u00e0 quy t\u1eafc HH/HL (t\u0103ng) ho\u1eb7c LH/LL (gi\u1ea3m).',
      },
    ],
  },
  {
    id: 'elliott',
    title: 'S\u00f3ng Elliott',
    icon: '\U0001f30a',
    viewIds: ['elliott'],
    blocks: [
      {
        type: 'p',
        text: 'Thu\u1eadt to\u00e1n heuristic g\u00e1n nh\u00e3n s\u00f3ng xung (1-5) ho\u1eb7c \u0111i\u1ec1u ch\u1ec9nh (ABC) d\u1ef1a tr\u00ean c\u00e1c \u0111o\u1ea1n xu h\u01b0\u1edbng. N\u00ean x\u00e1c nh\u1eadn th\u1ee7 c\u00f4ng tr\u00ean bi\u1ec3u \u0111\u1ed3.',
      },
    ],
  },
  {
    id: 'psychology',
    title: 'Chu k\u1ef3 t\u00e2m l\u00fd',
    icon: '\U0001f9e0',
    viewIds: ['psychology'],
    blocks: [
      {
        type: 'p',
        text: 'K\u1ebft h\u1ee3p v\u1ecb tr\u00ed chu k\u1ef3 halving, xu h\u01b0\u1edbng hi\u1ec7n t\u1ea1i v\u00e0 s\u00f3ng Elliott \u0111\u1ec3 \u01b0\u1edbc l\u01b0\u1ee3ng giai \u0111o\u1ea1n t\u00e2m l\u00fd: L\u1ea1c quan, S\u1ee3 h\u00e3i, H\u01b0ng ph\u1ea5n c\u1ef1c \u0111\u1ed9, Hy v\u1ecdng, v.v.',
      },
    ],
  },
  {
    id: 'data',
    title: 'Data Manager',
    icon: '\U0001f4be',
    viewIds: ['data'],
    blocks: [
      {
        type: 'p',
        text: 'Ch\u1ec9 h\u1ed7 tr\u1ee3 BTCUSD (W, D1, H4). T\u1ea3i d\u1eef li\u1ec7u t\u1eeb data/defaults ho\u1eb7c import CSV/JSON. D\u1eef li\u1ec7u EUR/GBP c\u0169 s\u1ebd t\u1ef1 x\u00f3a khi kh\u1edfi \u0111\u1ed9ng app.',
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Ch\u1ea1y qua HTTP server: cd LongBTC && python3 -m http.server 8080',
      },
    ],
  },
  {
    id: 'shortcuts',
    title: 'Ph\u00edm t\u1eaft',
    icon: '\u2328',
    blocks: [
      {
        type: 'ul',
        items: [
          'Ctrl+1: Bi\u1ec3u \u0111\u1ed3 BTC',
          'Ctrl+2: T\u1ed5ng quan',
          'Ctrl+3: Chu k\u1ef3 4 n\u0103m',
          'Ctrl+4: Xu h\u01b0\u1edbng',
          'Ctrl+5: S\u00f3ng Elliott',
          'Ctrl+6: T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
          'Ctrl+7: Data Manager',
          'Ctrl+0 / F1: T\u00e0i li\u1ec7u',
        ],
      },
    ],
  },
];

/**
 * @param {string} id
 * @returns {DocSection|undefined}
 */
export function getLongBtcDoc(id) {
  return LONG_BTC_DOC_SECTIONS.find((s) => s.id === id);
}

/**
 * @param {string} viewId
 * @returns {string}
 */
export function docSectionForView(viewId) {
  const direct = LONG_BTC_DOC_SECTIONS.find((s) => s.viewIds?.includes(viewId));
  if (direct) return direct.id;
  return 'overview';
}
""",
)
