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
    title: 'T?ng quan LongBTC',
    subtitle: 'N?n t?ng nghiên c?u ??u t? BTC dài h?n',
    icon: '??',
    viewIds: ['dashboard'],
    blocks: [
      {
        type: 'p',
        text: `${Config.APP_NAME} giúp nghiên c?u chu k? Bitcoin theo pipeline: Chu k? halving 4 n?m ? Xu h??ng t?ng/gi?m/?i ngang ? Sóng Elliott ? Chu k? tâm lý th? tr??ng.`,
      },
      {
        type: 'callout',
        variant: 'warn',
        text: '?ây là công c? nghiên c?u, KHÔNG ph?i l?i khuyên ??u t?. Quá kh? không ??m b?o t??ng lai.',
      },
      {
        type: 'h3',
        text: 'Quy trình phân tích',
      },
      {
        type: 'ol',
        items: [
          'Xác ??nh v? trí trong chu k? halving 4 n?m',
          'Phân tích xu h??ng qua c?u trúc swing (HH/HL, LH/LL)',
          '??m sóng Elliott trên các ?o?n xu h??ng',
          'Ánh x? sang giai ?o?n tâm lý th? tr??ng',
        ],
      },
    ],
  },
  {
    id: 'chart',
    title: 'Bi?u ?? BTC',
    icon: '??',
    viewIds: ['chart'],
    blocks: [
      {
        type: 'p',
        text: 'Bi?u ?? n?n BTC v?i overlay phân tích: swing pivot, ?o?n xu h??ng, ??nh/?áy chu k?. Khuy?n ngh? dùng khung W (tu?n) ho?c D1 (ngày) cho phân tích dài h?n.',
      },
      {
        type: 'ul',
        items: [
          'B?t/t?t overlay Swing, Xu h??ng, Chu k? trên toolbar',
          'EMA 200 h? tr? xác nh?n xu h??ng dài h?n',
          'Replay: phân tích t?ng giai ?o?n l?ch s?',
        ],
      },
    ],
  },
  {
    id: 'cycle',
    title: 'Chu k? 4 n?m',
    icon: '??',
    viewIds: ['cycle'],
    blocks: [
      {
        type: 'p',
        text: 'Bitcoin halving x?y ra kho?ng 4 n?m/l?n, gi?m m?t n?a ph?n th??ng kh?i. Chu k? th??ng có 4 giai ?o?n: Tích l?y ? T?ng tr??ng ? Phân ph?i ? Gi?m giá.',
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
    title: 'Xu h??ng',
    icon: '??',
    viewIds: ['trend'],
    blocks: [
      {
        type: 'p',
        text: 'Xu h??ng ???c xác ??nh qua swing pivot (zigzag) và quy t?c HH/HL (t?ng) ho?c LH/LL (gi?m).',
      },
    ],
  },
  {
    id: 'elliott',
    title: 'Sóng Elliott',
    icon: '??',
    viewIds: ['elliott'],
    blocks: [
      {
        type: 'p',
        text: 'Thu?t toán heuristic gán nhãn sóng xung (1-5) ho?c ?i?u ch?nh (ABC) d?a trên các ?o?n xu h??ng. Nên xác nh?n th? công trên bi?u ??.',
      },
    ],
  },
  {
    id: 'psychology',
    title: 'Chu k? tâm lý',
    icon: '??',
    viewIds: ['psychology'],
    blocks: [
      {
        type: 'p',
        text: 'K?t h?p v? trí chu k? halving, xu h??ng hi?n t?i và sóng Elliott ?? ??c l??ng giai ?o?n tâm lý: L?c quan, S? hãi, H?ng ph?n c?c ??, Hy v?ng, v.v.',
      },
    ],
  },
  {
    id: 'data',
    title: 'Data Manager',
    icon: '??',
    viewIds: ['data'],
    blocks: [
      {
        type: 'p',
        text: 'T?i d? li?u BTCUSD (W, D1, H4) t? data/defaults ho?c import CSV/JSON. D? li?u l?u c?c b? trong IndexedDB.',
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Ch?y qua HTTP server: cd LongBTC && python3 -m http.server 8080',
      },
    ],
  },
  {
    id: 'shortcuts',
    title: 'Phím t?t',
    icon: '??',
    blocks: [
      {
        type: 'ul',
        items: [
          'Ctrl+1: Bi?u ?? BTC',
          'Ctrl+2: T?ng quan',
          'Ctrl+3: Chu k? 4 n?m',
          'Ctrl+4: Xu h??ng',
          'Ctrl+5: Sóng Elliott',
          'Ctrl+6: Tâm lý th? tr??ng',
          'Ctrl+7: Data Manager',
          'Ctrl+0 / F1: Tài li?u',
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
