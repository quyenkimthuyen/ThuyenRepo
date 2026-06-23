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
    subtitle: 'Ba setup Price Action: engine duyệt từng nến, không nhìn trước tương lai.',
    icon: '⚙️',
    viewIds: ['strategy'],
    blocks: [
      { type: 'h3', text: 'Engine hoạt động thế nào?' },
      {
        type: 'p',
        text: 'Mỗi nến i, engine chỉ dùng dữ liệu candles[0..i]. Tại mỗi bar: calculate() cập nhật state → generateSignal() kiểm tra điều kiện → nếu hợp lệ sinh 1 signal (entry=close nến đó, SL/TP theo RR). Không lookahead.',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Chọn Symbol + TF', body: 'Chỉ hiện khi IndexedDB đã có nến. Phải khớp dữ liệu bạn muốn nghiên cứu.' },
          { title: 'Bật strategy (ON)', body: 'Tick plugin trong danh sách trái. Tắt strategy không cần scan.' },
          { title: 'Chỉnh tham số', body: 'Panel phải — Save Parameters để lưu local. Optimizer có thể ghi đè sau Grid Search.' },
          { title: 'Run Selected / Run All', body: 'Quét toàn bộ lịch sử bar-by-bar. Kết quả → Last Scan + AI scoring tự động.' },
        ],
      },
      {
        type: 'table',
        headers: ['Thành phần UI', 'Ý nghĩa'],
        rows: [
          ['Run Selected', 'Scan một strategy đang chọn'],
          ['Run All Enabled', 'Scan mọi strategy đang ON'],
          ['Save Parameters', 'Lưu tham số vào LocalStorage'],
          ['Last Scan', 'Số signal, thời gian chạy gần nhất'],
          ['Export JSON', 'Xuất signal để phân tích ngoài app'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Simulation dùng TOÀN BỘ signal từ scan — chưa lọc Min score ở AI Signals. Scan xong AI chấm điểm tự động.',
      },

      { type: 'h2', text: '1. Break & Retest (break-retest)' },
      {
        type: 'p',
        text: 'Ý tưởng: giá phá vỡ swing high/low, sau đó retest level cũ (đổi vai support/resistance) rồi tiếp tục theo hướng breakout. Dùng state machine 2 giai đoạn — không phải tín hiệu ngay tại nến breakout.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'break-retest-long',
        alt: 'Sơ đồ Break and Retest Long',
        caption: 'LONG: (1) Swing high = level kháng cự → (2) Breakout close vượt level + breakoutPips → (3) Trong retestMaxBars, nến retest chạm vùng level + nến xác nhận tăng → Entry tại close nến retest.',
      },
      { type: 'h3', text: 'Khi nào có tín hiệu LONG?' },
      {
        type: 'ol',
        items: [
          'Swing high = max(high) của swingLookback nến trước (không tính nến hiện tại).',
          'Nến breakout: close ≥ level + breakoutPips (mặc định 5 pip).',
          'Trong tối đa retestMaxBars nến sau breakout: nến retest chạm vùng level ±2 pip.',
          'Nến retest là nến xác nhận tăng: close > open, close ở 40% trên của range.',
          'Close retest không phá invalidation (đáy nến breakout − buffer).',
        ],
      },
      { type: 'h3', text: 'Khi nào có tín hiệu SHORT?' },
      {
        type: 'p',
        text: 'Đối xứng: swing low, close phá xuống dưới level − breakoutPips, retest vùng level từ dưới, nến xác nhận giảm, SL trên đỉnh retest.',
      },
      { type: 'h3', text: 'Khi nào KHÔNG có tín hiệu?' },
      {
        type: 'ul',
        items: [
          'Breakout không đủ pip (close chưa vượt ngưỡng).',
          'Quá retestMaxBars mà chưa retest → setup hết hạn.',
          'Trước khi retest, close phá invalidation → setup hủy.',
          'Nến retest chạm level nhưng không phải nến xác nhận (doji, body yếu).',
        ],
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Tác dụng'],
        rows: [
          ['breakoutPips', '5', 'Close phải vượt level thêm X pip mới coi là breakout thật'],
          ['retestMaxBars', '10', 'Chờ retest tối đa bao nhiêu nến — ngắn = ít signal, dài = nhiều cơ hội retest'],
          ['swingLookback', '5', 'Độ rộng tìm swing — lớn = level “cứng” hơn, ít signal hơn'],
          ['rr', '2', 'TP = entry ± RR × khoảng cách SL'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Entry = close nến retest. SL = dưới đáy retest (long) hoặc trên đỉnh retest (short) + 1 pip buffer. Signal có reason dạng "Bullish B&R: broke 1.08450, retest bar 3…".',
      },

      { type: 'h2', text: '2. EMA Pullback (ema-pullback)' },
      {
        type: 'p',
        text: 'Ý tưởng: xu hướng xác nhận bởi EMA nhanh/chậm, chờ giá hồi về vùng EMA nhanh, entry khi nến xác nhận hướng trend. Tín hiệu tại CÙNG nến pullback — không chờ nến sau.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'ema-pullback-long',
        alt: 'Sơ đồ EMA Pullback Long',
        caption: 'LONG: EMA20 > EMA50, xu hướng tăng xác nhận → giá hồi chạm vùng EMA20 (± pullbackTolerancePips) → nến tăng xác nhận, close trên EMA20, low vẫn trên EMA50.',
      },
      { type: 'h3', text: 'Xu hướng tăng (đủ điều kiện LONG)' },
      {
        type: 'ul',
        items: [
          'EMA fast > EMA slow và EMA fast đang dốc lên (so với trendBars nến trước).',
          'Close > EMA slow — giá trên xu hướng dài.',
          'Ít nhất 60% số nến trong trendBars có close cao hơn nến trước.',
          'Khoảng cách EMA fast–slow từ 3 đến 50 pip (tránh sideway và overextended).',
        ],
      },
      { type: 'h3', text: 'Khi nào có tín hiệu tại nến i?' },
      {
        type: 'ol',
        items: [
          'LONG: uptrend OK + low chạm vùng EMA fast ± tolerance + nến xác nhận tăng + close > EMA fast + low > EMA slow (không phá slow).',
          'SHORT: downtrend đối xứng + high chạm vùng EMA + nến giảm xác nhận + close < EMA fast + high < EMA slow.',
        ],
      },
      { type: 'h3', text: 'Khi nào KHÔNG có tín hiệu?' },
      {
        type: 'ul',
        items: [
          'EMA20 và EMA50 quá gần (< 3 pip) hoặc quá xa (> 50 pip).',
          'Chạm EMA nhưng close không phục hồi đúng phía (close dưới EMA fast khi muốn long).',
          'Low (long) hoặc high (short) phá qua EMA slow — trend bị nghi ngờ.',
          'Trong trendBars nến sau signal trước (cooldown — tránh trùng lặp).',
        ],
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Tác dụng'],
        rows: [
          ['emaFast / emaSlow', '20 / 50', 'Cặp EMA xác định trend và vùng pullback'],
          ['pullbackTolerancePips', '3', 'Vùng chấp nhận quanh EMA fast — rộng = nhiều signal hơn'],
          ['trendBars', '5', 'Số nến xác nhận xu hướng + cooldown sau mỗi signal'],
          ['rr', '2', 'Hệ số risk:reward cho TP'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Setup đẹp: chỉ râu chạm EMA, thân nến đóng cửa phía trên EMA (wick rejection). Confidence AI cộng thêm điểm cho pattern này.',
      },

      { type: 'h2', text: '3. Liquidity Grab (liquidity-grab)' },
      {
        type: 'p',
        text: 'Ý tưởng: false breakout — giá quét qua swing high/low (lấy liquidity / stop hunt), rồi đóng cửa quay lại trong range. Tín hiệu NGAY tại nến grab (single-bar), không chờ retest.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'liquidity-grab-short',
        alt: 'Sơ đồ Liquidity Grab Short',
        caption: 'SHORT: High quét trên swing high thêm grabPips, nhưng close đóng cửa DƯỚI level + râu trên ≥ wickRatio × range + nến giảm xác nhận.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'liquidity-grab-long',
        alt: 'Sơ đồ Liquidity Grab Long',
        caption: 'LONG: Low quét dưới swing low, close quay lại TRÊN level + râu dưới lớn + nến tăng xác nhận.',
      },
      { type: 'h3', text: 'SHORT — đủ 4 điều kiện cùng lúc' },
      {
        type: 'ol',
        items: [
          'high ≥ swingHigh + grabPips (quét đỉnh đủ xa).',
          'close < swingHigh (đóng cửa quay lại dưới level — false breakout).',
          'Râu trên / range nến ≥ wickRatio (mặc định 0.6 = 60%).',
          'Nến xác nhận giảm. SL = trên high nến grab + buffer.',
        ],
      },
      { type: 'h3', text: 'LONG — đối xứng' },
      {
        type: 'ol',
        items: [
          'low ≤ swingLow − grabPips.',
          'close > swingLow.',
          'Râu dưới / range ≥ wickRatio + nến tăng xác nhận.',
          'SL = dưới low nến grab.',
        ],
      },
      { type: 'h3', text: 'Khi nào KHÔNG có tín hiệu?' },
      {
        type: 'ul',
        items: [
          'Quét swing nhưng close vẫn ngoài level (breakout thật, không phải grab).',
          'Râu rejection quá nhỏ (< wickRatio).',
          'Volume nến grab < 80% trung bình (nếu data có volume).',
          'Đã có signal cùng hướng từ cùng level trong swingLookback×2 nến gần đây.',
        ],
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Tác dụng'],
        rows: [
          ['swingLookback', '7', 'Độ rộng tìm swing bị quét'],
          ['grabPips', '3', 'Phải vượt swing thêm X pip — lọc touch nhẹ'],
          ['wickRatio', '0.6', 'Râu rejection tối thiểu — cao = setup “sạch” hơn, ít signal'],
          ['rr', '2', 'TP theo bội số R'],
        ],
      },

      { type: 'h3', text: 'Nến xác nhận (dùng chung cả 3 strategy)' },
      {
        type: 'table',
        headers: ['Loại', 'Điều kiện'],
        rows: [
          ['Tăng', 'close > open VÀ close nằm ở 40% trên của range nến'],
          ['Giảm', 'close < open VÀ close nằm ở 40% dưới của range nến'],
          ['Doji', 'Range < 0.5 pip → KHÔNG được coi là xác nhận'],
        ],
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Sau scan: mở AI Signals lọc điểm → Chart Jump to date tại timestamp signal để đối chiếu bằng mắt. Reason trên mỗi signal mô tả level giá và bar index.',
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
