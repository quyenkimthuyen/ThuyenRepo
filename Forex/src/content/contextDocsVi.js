/**
 * Vietnamese context-aware documentation — one section per app view.
 * @module content/contextDocsVi
 */

import { Config } from '../core/Config.js';

/** @typedef {Object} DocBlock */
/** @typedef {Object} DocSection */

/** @type {DocSection[]} */
export const CONTEXT_DOC_SECTIONS = [
  {
    id: 'overview',
    title: 'Tổng quan PARL',
    subtitle: 'Price Action Research Lab — nền tảng nghiên cứu, không phải bot trade.',
    icon: '🏠',
    viewIds: ['docs'],
    blocks: [
      {
        type: 'callout',
        variant: 'info',
        text: 'PARL giúp bạn trả lời: setup nào, cặp nào, khung thời gian nào, tham số nào cho kết quả tốt nhất — trên dữ liệu quá khứ. Không tự đặt lệnh thật.',
      },
      {
        type: 'h3',
        text: 'Quy trình nghiên cứu khuyến nghị',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Dữ liệu nến', body: 'Data Manager — import hoặc load mặc định EURUSD/GBPUSD.' },
          { title: 'Scan chiến lược', body: 'Strategies — sinh danh sách signal (điểm vào, SL, TP).' },
          { title: 'Lọc signal', body: 'AI Signals — chấm điểm 0–100, lọc Min score.' },
          { title: 'Backtest lệnh', body: 'Simulation — mô phỏng spread, slippage, trailing.' },
          { title: 'Đánh giá', body: 'Statistics + Reports — expectancy, drawdown, heatmap.' },
          { title: 'Tối ưu & kiểm định', body: 'Optimizer — Grid Search, Walk Forward, Monte Carlo.' },
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Mở app qua http:// (Live Server hoặc python -m http.server). Không mở file:// trực tiếp.',
      },
      {
        type: 'h3',
        text: 'Cặp & khung thời gian hỗ trợ',
      },
      {
        type: 'ul',
        items: [
          `Cặp: ${Config.SYMBOLS.join(', ')}`,
          `Khung: ${Config.TIMEFRAMES.join(', ')}`,
          'Chiến lược: Break & Retest, EMA Pullback, Liquidity Grab',
        ],
      },
    ],
  },
  {
    id: 'install',
    title: 'Cài đặt & chạy',
    subtitle: 'App tĩnh — chỉ cần HTTP server, không cần Node hay database.',
    icon: '⚡',
    viewIds: ['docs'],
    blocks: [
      {
        type: 'p',
        text: 'PARL chạy hoàn toàn trên trình duyệt. Dữ liệu lưu IndexedDB + LocalStorage — không gửi lên server.',
      },
      {
        type: 'code',
        text: `cd Forex\npython3 -m http.server 8080\n# Mở http://localhost:8080\n# Hoặc VS Code Live Server → http://127.0.0.1:5500`,
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Lần đầu: vào Data Manager (Ctrl+2) → Reload Default Data hoặc Generate Sample.',
      },
    ],
  },
  {
    id: 'chart',
    title: 'Chart & Replay',
    subtitle: 'Quan sát nến và replay bar-by-bar — không nhìn trước tương lai.',
    icon: '📈',
    viewIds: ['chart'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Xác nhận bằng mắt setup mà Strategies đã báo. Replay mô phỏng trader chỉ thấy nến đã đóng.',
      },
      {
        type: 'table',
        headers: ['Thành phần', 'Ý nghĩa'],
        rows: [
          ['Symbol / TF', 'Cặp tiền và khung nến đang xem'],
          ['Reload', 'Tải lại dữ liệu từ IndexedDB'],
          ['EMA 20/50', 'Đối chiếu xu hướng với signal'],
          ['Watchlist', 'Click đổi cặp nhanh — chỉ hiện ở Chart và Data Manager'],
          ['Replay', 'Space=Play, mũi tên= từng nến, Jump= nhảy ngày'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Sau scan: mở Chart cùng Symbol/TF, Jump to date tại thời điểm signal từ AI Signals.',
      },
      { type: 'h3', text: 'Phím tắt Replay (khi đang ở Chart)' },
      {
        type: 'table',
        headers: ['Phím', 'Hành động'],
        rows: [
          ['Space', 'Play / Pause'],
          ['→ / ←', 'Nến tiếp / trước'],
          ['Home', 'Reset replay'],
          ['End', 'Xem hết (live)'],
        ],
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Dataset lớn: chart chỉ render ~50.000 nến cuối để mượt — replay vẫn chạy trên full data.',
      },
    ],
  },
  {
    id: 'data',
    title: 'Data Manager',
    subtitle: 'Nguồn dữ liệu cho mọi bước — không có nến thì không scan được.',
    icon: '💾',
    viewIds: ['data'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Import, lưu, export OHLCV trong trình duyệt. Lần đầu tự load EURUSD/GBPUSD (H1, H4, D1, W).',
      },
      {
        type: 'table',
        headers: ['Nút / thành phần', 'Cách dùng'],
        rows: [
          ['Import File', 'Chọn Symbol + TF, rồi chọn CSV/JSON/.gz'],
          ['Reload Default Data', 'Tải data/defaults/ (~3 năm). Đợi 1–2 phút full history'],
          ['Generate Sample', 'Nến giả lập nhanh để test'],
          ['Health bar', 'Data OK = sẵn sàng scan'],
        ],
      },
      { type: 'code', text: 'timestamp,datetime,open,high,low,close,volume' },
      { type: 'h3', text: 'Bảng dataset' },
      {
        type: 'table',
        headers: ['Cột', 'Ý nghĩa'],
        rows: [
          ['Candles', 'Số nến đã lưu — phải > 0 mới scan được'],
          ['Gaps', 'Khoảng trống thời gian — gap lớn có thể làm signal sai'],
          ['Export', 'Backup CSV trước khi xóa cache trình duyệt'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Health bar báo "Chưa có dữ liệu" → bấm Reload Default Data và đợi. Nếu dùng file:// sẽ không load được — cần http://.',
      },
    ],
  },
  {
    id: 'strategy',
    title: 'Strategies — Scan chiến lược',
    subtitle: 'Sinh signal Price Action bar-by-bar, không lookahead.',
    icon: '⚙️',
    viewIds: ['strategy'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Chạy plugin trên dữ liệu đã lưu → signal (entry, SL, TP, R:R). Input cho Simulation và AI scoring.',
      },
      {
        type: 'table',
        headers: ['Thành phần', 'Ý nghĩa'],
        rows: [
          ['Symbol / TF', 'Chỉ hiện khi đã có nến'],
          ['Run Selected', 'Scan một strategy'],
          ['Run All Enabled', 'Scan mọi strategy ON'],
          ['Save Parameters', 'Lưu tham số local'],
          ['Last Scan', 'Kết quả lần chạy gần nhất'],
        ],
      },
      { type: 'h3', text: 'Break & Retest' },
      {
        type: 'table',
        headers: ['Tham số', 'Ý nghĩa'],
        rows: [
          ['Breakout (pips)', 'Vượt swing tối thiểu bao nhiêu pip'],
          ['Retest Max Bars', 'Chờ retest tối đa bao nến'],
          ['Risk Reward', 'Hệ số TP/SL'],
          ['Swing Lookback', 'Độ rộng tìm swing'],
        ],
      },
      { type: 'h3', text: 'EMA Pullback' },
      {
        type: 'table',
        headers: ['Tham số', 'Ý nghĩa'],
        rows: [
          ['EMA Fast/Slow', 'Xác định xu hướng (20/50)'],
          ['Pullback Tolerance', 'Khoảng chạm EMA cho phép (pip)'],
          ['Min Trend Bars', 'Nến xác nhận xu hướng'],
          ['Risk Reward', 'Hệ số R:R'],
        ],
      },
      { type: 'h3', text: 'Liquidity Grab' },
      {
        type: 'table',
        headers: ['Tham số', 'Ý nghĩa'],
        rows: [
          ['Swing Lookback', 'Vùng swing / liquidity'],
          ['Grab Pips', 'Vượt swing thêm bao nhiêu pip'],
          ['Wick Ratio', 'Râu rejection tối thiểu'],
          ['Risk Reward', 'Hệ số R:R'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Scan xong tự chấm AI. Simulation dùng toàn bộ signal — chưa lọc Min score.',
      },
    ],
  },
  {
    id: 'signals',
    title: 'AI Signals — Lọc signal',
    subtitle: 'Chấm 0–100 sau mỗi scan.',
    icon: '🎯',
    viewIds: ['signals'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Sau mỗi lần scan Strategies, engine tự chấm từng signal 0–100. Dùng slider Min score để lọc setup đẹp trước khi xem Chart hoặc quyết định backtest thủ công.',
      },
      { type: 'h3', text: 'Min score — chọn ngưỡng' },
      {
        type: 'table',
        headers: ['Ngưỡng', 'Grade', 'Gợi ý'],
        rows: [
          ['50', 'C+', 'Bỏ signal rất yếu'],
          ['65', 'B+', 'Cân bằng số lượng/chất lượng'],
          ['80', 'A', 'Chỉ setup rất đẹp'],
        ],
      },
      {
        type: 'table',
        headers: ['Yếu tố', 'Đo gì'],
        rows: [
          ['trend', 'EMA & hướng lệnh'],
          ['momentum', 'Sức nến xác nhận'],
          ['location', 'SL gần entry'],
          ['volatility', 'Biến động vừa phải'],
          ['priceActionQuality', 'Râu rejection'],
          ['rr', 'Risk:Reward'],
          ['session', 'London/NY tốt hơn'],
          ['spread', 'Spread từ Simulation config'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Lọc Min score chỉ ảnh hưởng danh sách hiển thị ở đây. Simulation vẫn dùng TOÀN BỘ signal từ scan — muốn backtest ít signal hơn thì scan với tham số chặt hơn hoặc tắt strategy yếu.',
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Workflow: Scan (Ctrl+3) → kéo Min score 65–80 → mở Chart kiểm tra top signal → Simulation với cùng Symbol/TF.',
      },
    ],
  },
  {
    id: 'simulation',
    title: 'Simulation — Backtest',
    subtitle: 'Signal → lệnh giả lập với spread/SL/TP/trailing.',
    icon: '🔬',
    viewIds: ['simulation'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Biến signal thành lệnh giả lập: khớp entry, chạm SL/TP, trailing, break-even, partial close. Kết quả là nguồn cho Statistics, Reports và Monte Carlo.',
      },
      {
        type: 'table',
        headers: ['Tham số', 'Ý nghĩa & cách dùng'],
        rows: [
          ['Spread', 'Chi phí spread (pip) — EURUSD ~1–1.5'],
          ['Slippage', 'Trượt giá khi khớp'],
          ['Lot size', 'Khối lượng — giữ cố định khi so sánh'],
          ['Trailing', 'Kéo SL theo giá (0=tắt)'],
          ['Break-even at R', 'Dời SL về entry tại X R'],
          ['Partial at R / %', 'Chốt một phần tại X R'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Kết quả feed Statistics, Reports, Monte Carlo. Chạy Strategies trước hoặc Simulation sẽ scan lại.',
      },
    ],
  },
  {
    id: 'statistics',
    title: 'Statistics',
    subtitle: 'Số liệu từ Simulation gần nhất.',
    icon: '📊',
    viewIds: ['statistics'],
    blocks: [
      { type: 'h3', text: 'Đọc chỉ số' },
      {
        type: 'table',
        headers: ['Chỉ số', 'Ý nghĩa tốt'],
        rows: [
          ['Expectancy', '> 0 $/lệnh — lợi nhuận kỳ vọng mỗi trade'],
          ['Profit Factor', '> 1.2 — tổng thắng / tổng thua'],
          ['Max Drawdown', 'Càng thấp càng tốt — mức sụt tài khoản'],
          ['Win Rate', 'Xem cùng RR — win rate thấp vẫn OK nếu RR cao'],
          ['Sharpe Ratio', '> 1 ổn — risk-adjusted return'],
          ['Recovery Factor', 'Net profit / max DD — khả năng phục hồi'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Equity curve đi lên đều + drawdown thấp = setup ổn định. Nếu trống → chạy Simulation (Ctrl+4) trước.',
      },
    ],
  },
  {
    id: 'reports',
    title: 'Reports & Heatmap',
    subtitle: 'Setup mạnh khi nào / ở đâu.',
    icon: '📋',
    viewIds: ['reports'],
    blocks: [
      { type: 'h3', text: 'Các tab' },
      {
        type: 'ul',
        items: [
          'Dashboard — tóm tắt P/L, win rate, equity curve.',
          'Heatmaps — theo tháng, ngày, giờ, session, strategy, cặp, TF.',
          'Export — CSV trades, JSON report, PNG dashboard, in PDF.',
        ],
      },
      { type: 'h3', text: 'Đọc heatmap hiệu quả' },
      {
        type: 'ul',
        items: [
          'Session — ưu tiên London/NY nếu setup mạnh ở đó.',
          'Month/day — tránh giao dịch mùa yếu.',
          'Export CSV/PNG trước khi xóa cache trình duyệt.',
        ],
      },
    ],
  },
  {
    id: 'optimizer',
    title: 'Optimizer',
    subtitle: 'Grid Search · Walk Forward · Monte Carlo.',
    icon: '🧪',
    viewIds: ['optimizer'],
    blocks: [
      { type: 'h3', text: 'Quy trình khuyến nghị' },
      {
        type: 'steps',
        steps: [
          { title: 'Grid Search', body: 'Tìm combo tham số tốt trên toàn bộ lịch sử.' },
          { title: 'Save params', body: 'Chọn combo → áp vào Strategies → Save Parameters.' },
          { title: 'Walk Forward', body: 'Kiểm tra OOS — tránh overfit.' },
          { title: 'Simulation', body: 'Backtest với params đã chọn.' },
          { title: 'Monte Carlo', body: 'Đánh giá rủi ro chuỗi thua.' },
        ],
      },
      { type: 'h3', text: 'Grid Search' },
      {
        type: 'ul',
        items: [
          'Tick tham số + nhập giá trị: 3,5,7 hoặc 5:20:5.',
          `Tối đa ${Config.OPTIMIZER.MAX_COMBINATIONS} combo.`,
          'Rank: Expectancy. Chọn combo có ≥30 trades.',
        ],
      },
      { type: 'h3', text: 'Walk Forward' },
      {
        type: 'ul',
        items: [
          'Dùng params đã Save trong Strategies.',
          'OOS gần IS = bền; IS cao OOS âm = overfit.',
        ],
      },
      { type: 'h3', text: 'Monte Carlo' },
      {
        type: 'ul',
        items: [
          'Cần Simulation trước.',
          'Xem P5 (xấu nhất) và Ruin Rate.',
        ],
      },
    ],
  },
  {
    id: 'shortcuts',
    title: 'Phím tắt',
    icon: '⌨️',
    viewIds: ['docs'],
    blocks: [
      {
        type: 'table',
        headers: ['Phím', 'Chức năng'],
        rows: [
          ['Ctrl+B', 'Ẩn/hiện sidebar'],
          ['Ctrl+1', 'Chart'],
          ['Ctrl+2', 'Data Manager'],
          ['Ctrl+3', 'Strategies'],
          ['Ctrl+4', 'Simulation'],
          ['Ctrl+5', 'Statistics'],
          ['Ctrl+6', 'Reports'],
          ['Ctrl+7', 'Optimizer'],
          ['Ctrl+8', 'AI Signals'],
          ['Ctrl+9 / F1', 'Tài liệu đầy đủ'],
          ['📖 (top bar)', 'Hướng dẫn theo mục đang mở'],
          ['📖 Hướng dẫn', 'Nút trên từng màn hình'],
        ],
      },
      { type: 'h3', text: 'Chart replay' },
      {
        type: 'table',
        headers: ['Phím', 'Chức năng'],
        rows: [
          ['Space', 'Play / Pause'],
          ['→', 'Nến tiếp'],
          ['←', 'Nến trước'],
          ['Home', 'Reset'],
          ['End', 'Live'],
        ],
      },
    ],
  },
  {
    id: 'faq',
    title: 'FAQ',
    icon: '❓',
    viewIds: ['docs'],
    blocks: [
      { type: 'h3', text: 'Không có Symbol/TF ở Strategies?' },
      { type: 'p', text: 'Chưa có nến trong IndexedDB. Vào Data Manager → Reload Default Data hoặc Import. Phải chạy qua http://.' },
      { type: 'h3', text: 'Statistics / Reports trống?' },
      { type: 'p', text: 'Chạy Simulation (Ctrl+4) trước. Hai mục này đọc kết quả simulation gần nhất.' },
      { type: 'h3', text: 'Monte Carlo báo không có trade?' },
      { type: 'p', text: 'Monte Carlo dùng danh sách lệnh từ Simulation. Chạy Simulation trước khi vào tab Monte Carlo.' },
      { type: 'h3', text: 'Grid search quá chậm?' },
      { type: 'p', text: `Giảm số combo (tối đa ${Config.OPTIMIZER.MAX_COMBINATIONS}). Dataset lớn tự dùng Web Workers.` },
      { type: 'h3', text: 'Watchlist biến mất?' },
      { type: 'p', text: 'Watchlist chỉ hiện ở Chart và Data Manager — các mục khác ẩn để tập trung workspace.' },
    ],
  },
];

/**
 * @param {string} id
 * @returns {DocSection|undefined}
 */
export function getContextDoc(id) {
  return CONTEXT_DOC_SECTIONS.find((s) => s.id === id);
}

/**
 * @param {string} viewId
 * @returns {string}
 */
export function docSectionForView(viewId) {
  const direct = CONTEXT_DOC_SECTIONS.find((s) => s.viewIds?.includes(viewId));
  if (direct) return direct.id;
  return 'overview';
}

export const DOC_SECTIONS = CONTEXT_DOC_SECTIONS;
