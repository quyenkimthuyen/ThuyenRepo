
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
    title: 'Tổng quan LongBTC',
    subtitle: 'Nền tảng nghiên cứu đầu tư BTC dài hạn',
    icon: '₿',
    viewIds: ['dashboard'],
    blocks: [
      {
        type: 'p',
        text: `${Config.APP_NAME} giúp nghiên cứu chu kỳ Bitcoin theo pipeline: Chu kỳ halving 4 năm → Xu hướng tăng/giảm/đi ngang → Sóng Elliott → Chu kỳ tâm lý thị trường.`,
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Đây là công cụ nghiên cứu, KHÔNG phải lời khuyên đầu tư. Quá khứ không đảm bảo tương lai.',
      },
      {
        type: 'h3',
        text: 'Quy trình phân tích',
      },
      {
        type: 'ol',
        items: [
          'Xác định vị trí trong chu kỳ halving 4 năm',
          'Phân tích xu hướng qua cấu trúc swing (HH/HL, LH/LL)',
          'Đếm sóng Elliott trên các đoạn xu hướng',
          'Ánh xạ sang giai đoạn tâm lý thị trường',
        ],
      },
    ],
  },
  {
    id: 'chart',
    title: 'Biểu đồ BTC',
    icon: '📈',
    viewIds: ['chart'],
    blocks: [
      {
        type: 'p',
        text: 'Biểu đồ nến BTC với overlay phân tích: swing pivot, đoạn xu hướng, đỉnh/đáy chu kỳ. Khuyến nghị dùng khung W (tuần) hoặc D1 (ngày) cho phân tích dài hạn.',
      },
      {
        type: 'ul',
        items: [
          'Bật/tắt overlay Swing, Xu hướng, Chu kỳ trên toolbar',
          'EMA 200 hỗ trợ xác nhận xu hướng dài hạn',
          'Replay: phân tích từng giai đoạn lịch sử',
        ],
      },
    ],
  },
  {
    id: 'cycle',
    title: 'Chu kỳ 4 năm',
    icon: '⏱',
    viewIds: ['cycle'],
    blocks: [
      {
        type: 'p',
        text: 'Bitcoin halving xảy ra khoảng 4 năm/lần, giảm một nửa phần thưởng khối. Chu kỳ thường có 4 giai đoạn: Tích lũy → Tăng trưởng → Phân phối → Giảm giá.',
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
    title: 'Xu hướng',
    icon: '📊',
    viewIds: ['trend'],
    blocks: [
      {
        type: 'p',
        text: 'Xu hướng được xác định qua swing pivot (zigzag) và quy tắc HH/HL (tăng) hoặc LH/LL (giảm).',
      },
    ],
  },
  {
    id: 'elliott',
    title: 'Sóng Elliott',
    icon: '🌊',
    viewIds: ['elliott'],
    blocks: [
      {
        type: 'p',
        text: 'Thuật toán heuristic gán nhãn sóng xung (1-5) hoặc điều chỉnh (ABC) dựa trên các đoạn xu hướng. Nên xác nhận thủ công trên biểu đồ.',
      },
    ],
  },
  {
    id: 'psychology',
    title: 'Chu kỳ tâm lý',
    icon: '🧠',
    viewIds: ['psychology'],
    blocks: [
      {
        type: 'p',
        text: 'Kết hợp vị trí chu kỳ halving, xu hướng hiện tại và sóng Elliott để ước lượng giai đoạn tâm lý: Lạc quan, Sợ hãi, Hưng phấn cực độ, Hy vọng, v.v.',
      },
    ],
  },
  {
    id: 'data',
    title: 'Data Manager',
    icon: '💾',
    viewIds: ['data'],
    blocks: [
      {
        type: 'p',
        text: 'Chỉ hỗ trợ BTCUSD (W, D1, H4). Tải dữ liệu từ data/defaults hoặc import CSV/JSON. Dữ liệu EUR/GBP cũ sẽ tự xóa khi khởi động app.',
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Chạy qua HTTP server: cd LongBTC && python3 -m http.server 8080',
      },
    ],
  },
  {
    id: 'shortcuts',
    title: 'Phím tắt',
    icon: '⌨',
    blocks: [
      {
        type: 'ul',
        items: [
          'Ctrl+1: Biểu đồ BTC',
          'Ctrl+2: Tổng quan',
          'Ctrl+3: Chu kỳ 4 năm',
          'Ctrl+4: Xu hướng',
          'Ctrl+5: Sóng Elliott',
          'Ctrl+6: Tâm lý thị trường',
          'Ctrl+7: Data Manager',
          'Ctrl+0 / F1: Tài liệu',
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
