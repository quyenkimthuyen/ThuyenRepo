
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
        text: 'Module HalvingCycleAnalyzer. Ti\u1ebfn \u0111\u1ed9 = ng\u00e0y t\u1eeb halving g\u1ea7n nh\u1ea5t / 1460. Halving k\u1ebf ti\u1ebfp \u01b0\u1edbc t\u00ednh = halving hi\u1ec7n t\u1ea1i + 1460 ng\u00e0y (cho \u0111\u1ebfn khi c\u00f3 ng\u00e0y ch\u00ednh th\u1ee9c).',
      },
      {
        type: 'table',
        headers: ['Pha macro', '% chu k\u1ef3', 'ID'],
        rows: [
          ['T\u00edch l\u0169y', '0\u201325%', 'accumulation'],
          ['T\u0103ng tr\u01b0\u1edfng', '25\u201355%', 'markup'],
          ['Ph\u00e2n ph\u1ed1i', '55\u201375%', 'distribution'],
          ['Gi\u1ea3m gi\u00e1', '75\u2013100%', 'markdown'],
        ],
      },
      {
        type: 'h3',
        text: 'M\u1ed1c halving (UTC)',
      },
      {
        type: 'ul',
        items: [
          '#1: 2012-11-28 \u2192 25 BTC',
          '#2: 2016-07-09 \u2192 12.5 BTC',
          '#3: 2020-05-11 \u2192 6.25 BTC',
          '#4: 2024-04-20 \u2192 3.125 BTC',
        ],
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Pha macro d\u00f9ng 1460 ng\u00e0y c\u1ed1 \u0111\u1ecbnh. N\u1ec1n t\u00e2m l\u00fd chart d\u00f9ng kho\u1ea3ng halving N \u2192 N+1 theo ng\u00e0y th\u1ef1c.',
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
        text: 'Swing pivot zigzag (SwingPivotDetector) \u2192 \u0111o\u1ea1n trend (TrendAnalyzer) \u2192 HH/HL ho\u1eb7c LH/LL.',
      },
      {
        type: 'table',
        headers: ['TF', 'reversalPct', 'minBars', 'sideways %'],
        rows: [
          ['W', '18%', '1', '10%'],
          ['D1', '12%', '2', '6%'],
          ['H4', '8%', '4', '3%'],
        ],
      },
      {
        type: 'ul',
        items: [
          'HH + HL \u2192 uptrend (85% tin c\u1eady)',
          'LH + LL \u2192 downtrend (85%)',
          'Ph\u00e2n k\u1ef3 HH/LL ho\u1eb7c LH/HL \u2192 sideways (60%)',
          'Thi\u1ebfu pivot \u2192 sideways (30%)',
        ],
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
        text: 'Heuristic tr\u00ean 8 \u0111o\u1ea1n trend g\u1ea7n nh\u1ea5t: impulse 1\u20135 ho\u1eb7c correction ABC. Kh\u00f4ng thay th\u1ebf \u0111\u1ebfm s\u00f3ng th\u1ee7 c\u00f4ng.',
      },
      {
        type: 'table',
        headers: ['S\u00f3ng', 'G\u1ee3i \u00fd t\u00e2m l\u00fd (chip)'],
        rows: [
          ['1', 'hope, relief, optimism'],
          ['2', 'denial, anxiety'],
          ['3', 'optimism, excitement, thrill'],
          ['4', 'anxiety, denial'],
          ['5', 'euphoria, thrill'],
          ['A', 'anxiety, fear'],
          ['B', 'denial, hope'],
          ['C', 'capitulation, depression, fear'],
        ],
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
          'N\u1ec1n chart: toggle N\u1ec1n giai \u0111o\u1ea1n t\u00e2m l\u00fd \u2014 Mode A/B, \u0111\u1ed3ng b\u1ed9 pan/zoom',
          'Chip context bar: assessPsychology() t\u1ea1i n\u1ebfn \u0111ang xem',
          'M\u00e0n T\u00e2m l\u00fd Ctrl+6: khuy\u1ebfn ngh\u1ecb DCA + timeline CYCLE_PHASE_MAP',
        ],
      },
    ],
  },
  {
    id: 'psychology-rules',
    title: 'Quy t\u1eafc x\u00e1c \u0111\u1ecbnh',
    subtitle: 'Ba l\u1edbp logic \u2014 chi ti\u1ebft trong PSYCHOLOGY_CYCLE.md',
    icon: '\u{1F4D0}',
    viewIds: ['psychology', 'chart'],
    blocks: [
      {
        type: 'callout',
        variant: 'info',
        text: 'App d\u00f9ng 3 b\u1ed9 quy t\u1eafc: (A) n\u1ec1n chart Mode A/B, (B) chip assessPsychology, (C) timeline m\u00e0n T\u00e2m l\u00fd (CYCLE_PHASE_MAP). Ch\u00fang kh\u00f4ng gi\u1ed1ng h\u1ec7t nhau.',
      },
      {
        type: 'h3',
        text: 'N\u1ec1n chart \u2014 khung halving N \u2192 N+1',
      },
      {
        type: 'p',
        text: 'Chu k\u1ef3 \u0111\u00e3 k\u1ebft th\u00fac: ng\u00e0y halving th\u1ef1c. H4\u2192H5: halving #4 + 1460 ng\u00e0y. Ch\u1ecdn Mode:',
      },
      {
        type: 'ul',
        items: [
          'Mode A: <12 n\u1ebfn trong CK ho\u1eb7c close ch\u01b0a h\u1ed3i \u226510% t\u1eeb ATH (high max)',
          'Mode B: \u226512 n\u1ebfn v\u00e0 drawdown \u226510% \u2192 neo \u0111\u1ec9nh chu k\u1ef3 (peakPct 12\u201348%)',
        ],
      },
      {
        type: 'h3',
        text: 'Mode A \u2014 13 c\u1eeda s\u1ed5 % (n\u1ec1n chart)',
      },
      {
        type: 'table',
        headers: ['%', 'Phase'],
        rows: [
          ['0\u201310', 'Hy v\u1ecdng'],
          ['10\u201318', 'Nh\u1eb9 nh\u00f5m'],
          ['18\u201326', 'L\u1ea1c quan'],
          ['26\u201334', 'H\u01b0ng ph\u1ea5n'],
          ['34\u201342', 'Ph\u1ea5n kh\u00edch'],
          ['42\u201352', 'Hoan h\u1ef7'],
          ['52\u201358', 'Lo l\u1eafng'],
          ['58\u201365', 'Ph\u1ee7 nh\u1eadn'],
          ['65\u201372', 'S\u1ee3 h\u00e3i'],
          ['72\u201380', '\u0110\u1ea7u h\u00e0ng'],
          ['80\u201388', 'Ch\u00e1n n\u1ea3n'],
          ['88\u201394', 'Hy v\u1ecdng'],
          ['94\u2013100', 'Nh\u1eb9 nh\u00f5m'],
        ],
      },
      {
        type: 'h3',
        text: 'Mode B \u2014 bull tr\u01b0\u1edbc ATH, bear sau ATH',
      },
      {
        type: 'p',
        text: 'Tr\u01b0\u1edbc \u0111\u1ec9nh: hope\u2192relief\u2192optimism\u2192excitement\u2192thrill\u2192euphoria. Sau \u0111\u1ec9nh: anxiety\u2192denial\u2192fear\u2192capitulation\u2192depression\u2192hope\u2192relief. T\u1ef7 l\u1ec7 co gi\u00e3n theo peakPct (xem docs m\u1ee5c 5.4).',
      },
      {
        type: 'h3',
        text: 'Chip assessPsychology()',
      },
      {
        type: 'p',
        text: 'Ch\u1ea5m \u0111i\u1ec3m t\u1ed5ng 5 y\u1ebfu t\u1ed1; ch\u1ecdn phase cao nh\u1ea5t. confidence = min(95, \u0111i\u1ec3m).',
      },
      {
        type: 'table',
        headers: ['Y\u1ebfu t\u1ed1', 'Tr\u1ecdng s\u01a1 (drawdown \u226525%)'],
        rows: [
          ['L\u1ecbch halving (CYCLE_PHASE_MAP)', '~12%'],
          ['Drawdown t\u1eeb \u0111\u1ec9nh CK', '~38%'],
          ['Xu h\u01b0\u1edbng HH/HL', '~32%'],
          ['S\u00f3ng Elliott', '~12%'],
          ['Bonus pha macro', '~6%'],
        ],
      },
      {
        type: 'ul',
        items: [
          'Drawdown \u226545%: \u01b0u ti\u00ean capitulation, depression, fear; tr\u1eeb bull',
          'Drawdown \u226530%: tr\u1eeb euphoria/thrill; c\u1ed9ng fear/anxiety',
          'Uptrend + phase bull \u2192 +85; downtrend + phase bear \u2192 +85',
          'Drawdown = (close - cycleHigh) / cycleHigh t\u1eeb halving hi\u1ec7n t\u1ea1i',
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
        type: 'h3',
        text: 'X\u1ebfp h\u1ea1ng theo l\u1ecbch s\u1eed (median 26 tu\u1ea7n)',
      },
      {
        type: 'p',
        text: 'Ngu\u1ed3n: PsychologyInvestGuide.js \u2014 BTCUSD W, phase theo Mode A/B, \u0111o forward return 12w/26w.',
      },
      {
        type: 'table',
        headers: ['Giai \u0111o\u1ea1n', 'Med. 26w', '% th\u1eafng', 'Tier'],
        rows: [
          ['\u0110\u1ea7u h\u00e0ng', '+61.1%', '86%', 'R\u1ea5t t\u1ed1t'],
          ['Nh\u1eb9 nh\u00f5m', '+55.4%', '87%', 'R\u1ea5t t\u1ed1t'],
          ['Hy v\u1ecdng', '+50.6%', '80%', 'T\u1ed1t'],
          ['Ch\u00e1n n\u1ea3n', '+37.9%', '60%', 'T\u1ed1t'],
          ['L\u1ea1c quan', '+37.1%', '91%', 'T\u1ed1t'],
          ['S\u1ee3 h\u00e3i', '+32.6%', '58%', 'Trung b\u00ecnh'],
          ['Ph\u1ea5n kh\u00edch', '+22.2%', '63%', 'Th\u1eadn tr\u1ecdng'],
          ['H\u01b0ng ph\u1ea5n', '+15.9%', '81%', 'Th\u1eadn tr\u1ecdng'],
          ['Ph\u1ee7 nh\u1eadn', '-17.9%', '38%', 'Tr\u00e1nh'],
          ['Hoan h\u1ef7', '-39.6%', '25%', 'Tr\u00e1nh'],
          ['Lo l\u1eafng', '-31.7%', '0%', 'Tr\u00e1nh'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'B\u1ea3ng \u0111\u1ea7y \u0111\u1ee7 v\u00e0 khuy\u1ebfn ngh\u1ecb t\u1eebng giai \u0111o\u1ea1n: m\u00e0n T\u00e2m l\u00fd (Ctrl+6) ho\u1eb7c docs/PSYCHOLOGY_CYCLE.md m\u1ee5c 7.',
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
          'ATH, drawdown, Mode A/B \u2014 m\u1ed7i l\u1ea7n ph\u00e2n t\u00edch / n\u1ebfn m\u1edbi',
          'N\u1ec1n chart \u2014 rebuild khi pan, zoom, resize (PsychologyChartOverlay)',
          'Chip \u2014 theo n\u1ebfn hover/replay + cycleExtremes',
        ],
      },
      {
        type: 'h3',
        text: 'C\u1ea7n c\u1eadp nh\u1eadt th\u1ee7 c\u00f4ng',
      },
      {
        type: 'ul',
        items: [
          'Halving m\u1edbi: BTC_HALVING_EVENTS trong BtcCycleConfig.js',
          '% n\u1ec1n chart: buildChartPsychologyTimeline / buildAdaptiveChartPsychologyTimeline',
          'Tr\u1ecdng s\u1ed1 chip: assessPsychology trong PsychologyCycleMapper.js',
          'Stats DCA: HISTORICAL_STATS trong PsychologyInvestGuide.js',
          'D\u1eef li\u1ec7u BTCUSD W/D1 trong Data Manager',
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
