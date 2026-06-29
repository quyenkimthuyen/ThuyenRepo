
/**
 * LongBTC in-app documentation (Vietnamese).
 * @module content/longbtcDocsVi
 */

import { Config } from '../core/Config.js';

/**
 * @typedef {Object} DocBlock
 * @property {'h2'|'h3'|'p'|'ul'|'ol'|'callout'|'table'} type
 * @property {string} [text]
 * @property {string[]} [items]
 * @property {string[]} [headers]
 * @property {string[][]} [rows]
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
        text: `${Config.APP_NAME} gi\u00fap nghi\u00ean c\u1ee9u chu k\u1ef3 Bitcoin theo pipeline: Chu k\u1ef3 halving 4 n\u0103m \u2192 Xu h\u01b0\u1edbng \u2192 S\u00f3ng Elliott \u2192 Chu k\u1ef3 t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng.`,
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
          'Ph\u00e2n t\u00edch xu h\u01b0\u1edbng qua swing (HH/HL, LH/LL)',
          '\u0110\u1ebfm s\u00f3ng Elliott tr\u00ean c\u00e1c \u0111o\u1ea1n xu h\u01b0\u1edbng',
          '\u00c1nh x\u1ea1 sang 11 giai \u0111o\u1ea1n t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
        ],
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'T\u00e0i li\u1ec7u t\u00e2m l\u00fd c\u1ea5p 1: docs/PSYCHOLOGY_CYCLE.md',
      },
    ],
  },
  {
    id: 'chart',
    title: 'Bi\u1ec3u \u0111\u1ed3 BTC',
    icon: '\u{1F4C8}',
    viewIds: ['chart'],
    blocks: [
      {
        type: 'p',
        text: 'Bi\u1ec3u \u0111\u1ed3 n\u1ebfn BTC v\u1edbi overlay ph\u00e2n t\u00edch. Khuy\u1ebfn ngh\u1ecb khung W (tu\u1ea7n) ho\u1eb7c D1 cho ph\u00e2n t\u00edch d\u00e0i h\u1ea1n.',
      },
      {
        type: 'ul',
        items: [
          'B\u1eadt/t\u1eaft overlay Swing, Xu h\u01b0\u1edbng, Chu k\u1ef3, Halving, T\u00e2m l\u00fd',
          'L\u1edbp ph\u1ee7 \u2192 N\u1ec1n giai \u0111o\u1ea1n t\u00e2m l\u00fd: v\u00f9ng m\u00e0u theo chu k\u1ef3 halving',
          'Preset S\u1ea1ch / +Xu h\u01b0\u1edfng / \u0110\u1ea7y \u0111\u1ee7',
          'Replay bar-by-bar; context bar khi di chu\u1ed9t',
        ],
      },
    ],
  },
  {
    id: 'cycle',
    title: 'Chu k\u1ef3 4 n\u0103m',
    icon: '\u23F1',
    viewIds: ['cycle'],
    blocks: [
      {
        type: 'p',
        text: 'Bitcoin halving ~4 n\u0103m/l\u1ea7n. 4 giai \u0111o\u1ea1n macro: T\u00edch l\u0169y \u2192 T\u0103ng tr\u01b0\u1edfng \u2192 Ph\u00e2n ph\u1ed1i \u2192 Gi\u1ea3m gi\u00e1.',
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
    icon: '\u{1F4CA}',
    viewIds: ['trend'],
    blocks: [
      {
        type: 'p',
        text: 'Xu h\u01b0\u1edbng qua swing pivot v\u00e0 quy t\u1eafc HH/HL (t\u0103ng) ho\u1eb7c LH/LL (gi\u1ea3m).',
      },
    ],
  },
  {
    id: 'elliott',
    title: 'S\u00f3ng Elliott',
    icon: '\u{1F30A}',
    viewIds: ['elliott'],
    blocks: [
      {
        type: 'p',
        text: 'Heuristic g\u00e1n nh\u00e3n s\u00f3ng 1-5 ho\u1eb7c ABC. N\u00ean x\u00e1c nh\u1eadn th\u1ee7 c\u00f4ng tr\u00ean bi\u1ec3u \u0111\u1ed3.',
      },
    ],
  },
  {
    id: 'psychology',
    title: 'Chu k\u1ef3 t\u00e2m l\u00fd',
    subtitle: 'Wall Street Cheat Sheet \u00d7 halving BTC',
    icon: '\u{1F9E0}',
    viewIds: ['psychology'],
    blocks: [
      {
        type: 'p',
        text: '11 giai \u0111o\u1ea1n t\u00e2m l\u00fd g\u1eafn chu k\u1ef3 halving. T\u00e0i li\u1ec7u \u0111\u1ea7y \u0111\u1ee7: docs/PSYCHOLOGY_CYCLE.md',
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'C\u00f4ng c\u1ee5 nghi\u00ean c\u1ee9u \u2014 kh\u00f4ng ph\u1ea3i l\u1eddi khuy\u00ean \u0111\u1ea7u t\u01b0.',
      },
      {
        type: 'h3',
        text: '11 giai \u0111o\u1ea1n',
      },
      {
        type: 'table',
        headers: ['Ti\u1ebfng Vi\u1ec7t', 'English', 'V\u1ecb tr\u00ed'],
        rows: [
          ['Hy v\u1ecdng', 'Hope', 'Sau \u0111\u00e1y / halving'],
          ['Nh\u1eb9 nh\u00f5m', 'Relief', 'Sau stress'],
          ['L\u1ea1c quan', 'Optimism', 'Uptrend'],
          ['H\u01b0ng ph\u1ea5n', 'Excitement', 'FOMO'],
          ['Ph\u1ea5n kh\u00edch', 'Thrill', 'G\u1ea7n \u0111\u1ec9nh'],
          ['Hoan h\u1ef7', 'Euphoria', '\u0110\u1ec9nh'],
          ['Lo l\u1eafng', 'Anxiety', 'Pullback \u0111\u1ea7u'],
          ['Ph\u1ee7 nh\u1eadn', 'Denial', 'Gi\u1ea3m s\u00e2u'],
          ['S\u1ee3 h\u00e3i', 'Fear', 'B\u00e1n th\u00e1o'],
          ['\u0110\u1ea7u h\u00e0ng', 'Capitulation', '\u0110\u00e1y'],
          ['Ch\u00e1n n\u1ea3n', 'Depression', 'Sideways'],
        ],
      },
      {
        type: 'ul',
        items: [
          'N\u1ec1n chart: L\u1edbp ph\u1ee7 \u2192 N\u1ec1n giai \u0111o\u1ea1n t\u00e2m l\u00fd',
          'Chip context bar: giai \u0111o\u1ea1n t\u1ea1i n\u1ebfn \u0111ang xem',
        ],
      },
    ],
  },
  {
    id: 'psychology-rules',
    title: 'Quy t\u1eafc x\u00e1c \u0111\u1ecbnh',
    subtitle: 'L\u1ecbch halving + neo ATH',
    icon: '\u{1F4D0}',
    viewIds: ['psychology', 'chart'],
    blocks: [
      {
        type: 'p',
        text: 'Chu k\u1ef3 = Halving N \u2192 N+1 (ng\u00e0y th\u1ef1c). H4\u2192H5: \u01b0\u1edbc t\u00ednh +1460 ng\u00e0y cho \u0111\u1ebfn halving #5.',
      },
      {
        type: 'h3',
        text: 'Ch\u1ebf \u0111\u1ed9 A \u2014 L\u1ecbch c\u1ed1 \u0111\u1ecbnh',
      },
      {
        type: 'p',
        text: '13 c\u1eeda s\u1ed5 % chu k\u1ef3 (Hy v\u1ecdng 0\u201310%, H\u01b0ng ph\u1ea5n 26\u201334%, Hoan h\u1ef7 42\u201352%, \u2026). Khi <12 n\u1ebfn ho\u1eb7c gi\u00e1 trong 10% ATH.',
      },
      {
        type: 'h3',
        text: 'Ch\u1ebf \u0111\u1ed9 B \u2014 Neo ATH',
      },
      {
        type: 'p',
        text: 'Khi \u0111\u00f3ng c\u1eeda h\u1ed3i \u226510% t\u1eeb high max chu k\u1ef3: bull tr\u01b0\u1edbc ATH, bear sau ATH.',
      },
      {
        type: 'h3',
        text: 'Chip context bar',
      },
      {
        type: 'ul',
        items: [
          'Ch\u1ea5m \u0111i\u1ec3m: l\u1ecbch + drawdown + xu h\u01b0\u1edbng + Elliott + pha macro',
          'Drawdown \u226525%: \u01b0u ti\u00ean giai \u0111o\u1ea1n bear',
        ],
      },
    ],
  },
  {
    id: 'psychology-invest',
    title: 'Khuy\u1ebfn ngh\u1ecb nghi\u00ean c\u1ee9u',
    subtitle: 'Khung DCA d\u00e0i h\u1ea1n',
    icon: '\u{1F4A1}',
    viewIds: ['psychology', 'dashboard'],
    blocks: [
      {
        type: 'callout',
        variant: 'warn',
        text: 'Kh\u00f4ng ph\u1ea3i l\u1eddi khuy\u00ean mua b\u00e1n. Ch\u1ec9 khung suy ngh\u0129 cho hodl/DCA c\u00f3 k\u1ef7 lu\u1eadt.',
      },
      {
        type: 'table',
        headers: ['Giai \u0111o\u1ea1n', 'DCA', 'V\u1ecb th\u1ebf', 'Tr\u00e1nh'],
        rows: [
          ['Hy v\u1ecdng \u2192 L\u1ea1c quan', 'DCA \u0111\u1ec1u', 'X\u00e2y core', 'All-in'],
          ['H\u01b0ng ph\u1ea5n \u2192 Hoan h\u1ef7', 'Gi\u1ea3m/d\u1eebng', 'Ch\u1ed1t l\u1eebng ph\u1ea7n', 'FOMO, \u0111\u00f2n b\u1ea9y'],
          ['Lo l\u1eafng \u2192 S\u1ee3 h\u00e3i', 'Ch\u1eadm', 'B\u1ea3o to\u00e0n', 'Panic sell'],
          ['\u0110\u1ea7u h\u00e0ng \u2192 Ch\u00e1n n\u1ea3n', 'DCA v\u1ed1n d\u01b0', 'T\u00edch l\u0169y', 'B\u00e1n c\u00f9ng \u0111\u00e1m'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Chi ti\u1ebft 11 giai \u0111o\u1ea1n: docs/PSYCHOLOGY_CYCLE.md m\u1ee5c 7.',
      },
    ],
  },
  {
    id: 'psychology-maintain',
    title: 'B\u1ea3o tr\u00ec m\u00f4 h\u00ecnh',
    icon: '\u{1F527}',
    viewIds: ['psychology'],
    blocks: [
      {
        type: 'h3',
        text: 'T\u1ef1 c\u1eadp nh\u1eadt',
      },
      {
        type: 'ul',
        items: [
          'ATH chu k\u1ef3, drawdown, n\u1ebfn m\u1edbi',
          'V\u00f9ng m\u00e0u chart khi pan/zoom',
          'Chip t\u00e2m l\u00fd theo gi\u00e1',
        ],
      },
      {
        type: 'h3',
        text: 'C\u1ea7n c\u1eadp nh\u1eadt th\u1ee7 c\u00f4ng',
      },
      {
        type: 'ul',
        items: [
          'Halving m\u1edbi (~4 n\u0103m): th\u00eam ng\u00e0y v\u00e0o BTC_HALVING_EVENTS',
          'H\u00e0ng n\u0103m: so\u00e1t m\u1ed1c 2020/2021/2022 tr\u00ean W',
          'C\u1eadp nh\u1eadt d\u1eef li\u1ec7u BTCUSD trong Data Manager',
        ],
      },
    ],
  },
  {
    id: 'data',
    title: 'Data Manager',
    icon: '\u{1F4BE}',
    viewIds: ['data'],
    blocks: [
      {
        type: 'p',
        text: 'Ch\u1ec9 BTCUSD (W, D1, H4). T\u1ea3i data/defaults ho\u1eb7c import CSV/JSON.',
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'cd LongBTC && python3 -m http.server 8080',
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
