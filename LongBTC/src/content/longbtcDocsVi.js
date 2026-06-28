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
    subtitle: 'N?n t?ng nghi�n c?u ??u t? BTC d�i h?n',
    icon: '??',
    viewIds: ['dashboard'],
    blocks: [
      {
        type: 'p',
        text: `${Config.APP_NAME} gi�p nghi�n c?u chu k? Bitcoin theo pipeline: Chu k? halving 4 n?m ② Xu h??ng t?ng/gi?m/?i ngang ? S�ng Elliott ① Chu k? t�m l� th? tr??ng.`,
      },
      {
        type: 'callout',
        variant: 'warn',
        text: '?�y l� c�ng c? nghi�n c?u, KH�NG ph?i l?i khuy�n ??u t?. Qu� kh? kh�ng ??m b?o t??ng lai.',
      },
      {
        type: 'h3',
        text: 'Quy tr�nh ph�n t�ch',
      },
      {
        type: 'ol',
        items: [
          'X�c ??nh v? tr� trong chu k? halving 4 n?m',
          'Ph�n t�ch xu h??ng qua c?u tr�c swing (HH/HL, LH/LL)',
          '??m s�ng Elliott tr�n c�c ?o?n xu h??ng',
          '�nh x? sang giai ?o?n t�m l� th? tr??ng',
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
        text: 'Bi?u ?? n?n BTC v?i overlay ph�n t�ch: swing pivot, ?o?n xu h??ng, ??nh/?�y chu k?. Khuy?n ngh? d�ng khung W (tu?n) ho?c D1 (ng�y) cho ph�n t�ch d�i h?n.',
      },
      {
        type: 'ul',
        items: [
          'B?t/t?t overlay Swing, Xu h??ng, Chu k? tr�n toolbar',
          'EMA 200 h? tr? x�c nh?n xu h??ng d�i h?n',
          'Replay: ph�n t�ch t?ng giai ?o?n l?ch s?',
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
        text: 'Bitcoin halving x?y ra kho?ng 4 n?m/l?n, gi?m m?t n?a ph?n th??ng kh?i. Chu k? th??ng c� 4 giai ?o?n: T�ch l?y ? T?ng tr??ng ? Ph�n ph?i ? Gi?m gi�.',
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
        text: 'Xu h??ng ???c x�c ??nh qua swing pivot (zigzag) v� quy t?c HH/HL (t?ng) ho?c LH/LL (gi?m).',
      },
    ],
  },
  {
    id: 'elliott',
    title: 'S�ng Elliott',
    icon: '??',
    viewIds: ['elliott'],
    blocks: [
      {
        type: 'p',
        text: 'Thu?t to�n heuristic g�n nh�n s�ng xung (1-5) ho?c ?i?u ch?nh (ABC) d?a tr�n c�c ?o?n xu h??ng. N�n x�c nh?n th? c�ng tr�n bi?u ??.',
      },
    ],
  },
  {
    id: 'psychology',
    title: 'Chu k? t�m l�',
    icon: '??',
    viewIds: ['psychology'],
    blocks: [
      {
        type: 'p',
        text: 'K?t h?p v? tr� chu k? halving, xu h??ng hi?n t?i v� s�ng Elliott ?? ??c l??ng giai ?o?n t�m l�: L?c quan, S? h�i, H?ng ph?n c?c ??, Hy v?ng, v.v.',
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
        text: 'Ch? h? tr? BTCUSD (W, D1, H4). T?i d? li?u t? data/defaults ho?c import CSV/JSON. D? li?u EUR/GBP c? s? t? x�a khi kh?i ??ng app.',
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
    title: 'Ph�m t?t',
    icon: '??',
    blocks: [
      {
        type: 'ul',
        items: [
          'Ctrl+1: Bi?u ?? BTC',
          'Ctrl+2: T?ng quan',
          'Ctrl+3: Chu k? 4 n?m',
          'Ctrl+4: Xu h??ng',
          'Ctrl+5: S�ng Elliott',
          'Ctrl+6: T�m l� th? tr??ng',
          'Ctrl+7: Data Manager',
          'Ctrl+0 / F1: T�i li?u',
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
