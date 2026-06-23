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
        text: 'PARL giúp bạn trả lời: “Setup này, trên cặp/khung nào, với cài đặt nào — có thật sự kiếm được tiền sau khi trừ spread không?” — bằng cách mô phỏng trên dữ liệu quá khứ. Không tự đặt lệnh thật.',
      },
      {
        type: 'h3',
        text: 'Vấn đề trader thường gặp',
      },
      {
        type: 'ul',
        items: [
          'Không biết setup nào thực sự có lợi trên dữ liệu thật.',
          'Xem lại chart kiểu “đã biết kết quả” — dễ tự lừa mình.',
          'Chỉ đếm tín hiệu, không tính phí spread, cắt lỗ/chốt lời.',
          'Quá nhiều tín hiệu — không biết cái nào đáng mở chart xem.',
          'Chỉnh cài đặt cho khớp quá khít quá khứ (học vẹt) mà không kiểm tra lại.',
          'Dữ liệu, chart, Excel, mô phỏng nằm rải rác nhiều chỗ.',
        ],
      },
      {
        type: 'h3',
        text: 'PARL giải quyết thế nào',
      },
      {
        type: 'table',
        headers: ['Nỗi đau', 'Module trong app'],
        rows: [
          ['Setup nào tốt?', 'Strategies quét tín hiệu → Simulation mô phỏng lệnh có spread/SL/TP'],
          ['Tránh tự lừa', 'Chart + Replay — chỉ thấy nến đã đóng; bấm signal từ AI Signals để kiểm tra'],
          ['Lọc tín hiệu', 'AI Signals — chấm 0–100 theo 8 yếu tố, lọc Min score (không dự đoán thắng/thua)'],
          ['Tìm cài đặt tốt', 'Optimizer: thử lưới tham số, kiểm tra theo thời gian, xáo thứ tự lệnh'],
          ['Đánh giá kết quả', 'Statistics + Reports — lãi/lỗ, mức sụt tài khoản, biểu đồ theo giờ/tháng'],
          ['Quản lý data', 'Data Manager — nến lưu trên máy bạn, không gửi server'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Gặp từ khó như Overfit, Walk Forward, Monte Carlo, Ruin Rate…? Mở mục **Từ điển thuật ngữ** trong tài liệu (Ctrl+9) — giải thích bằng tiếng đời thường, kèm tên tiếng Anh trên app.',
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'PARL KHÔNG: kết nối broker, đặt lệnh live, thay journal/tâm lý, hay “dự đoán chắc thắng”. AI Signals chỉ lọc chất lượng setup — Simulation vẫn dùng toàn bộ signal từ scan (chưa theo Min score).',
      },
      {
        type: 'h3',
        text: 'Quy trình nghiên cứu khuyến nghị',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Dữ liệu nến', body: 'Data Manager — import, Reload Default, Cập nhật/Xóa theo Symbol+TF.' },
          { title: 'Scan chiến lược', body: 'Strategies — sinh signal (entry, SL, TP); chọn Symbol/TF có data.' },
          { title: 'Lọc & kiểm chứng', body: 'AI Signals — Min score → bấm signal → Chart vẽ setup (Entry/SL/TP, chú thích màu).' },
          { title: 'Mô phỏng lệnh', body: 'Simulation — tính spread, trượt giá, trailing, chốt một phần.' },
          { title: 'Đánh giá', body: 'Statistics + Reports — lãi trung bình/lệnh, mức sụt tài khoản, biểu đồ.' },
          { title: 'Tối ưu & kiểm định', body: 'Optimizer — thử nhiều cài đặt, kiểm tra theo thời gian, xáo thứ tự lệnh.' },
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
        text: 'Lần đầu: vào Data Manager (Ctrl+2) → Reload Default Data hoặc Import file.',
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
          ['Symbol / TF', 'Chỉ liệt kê cặp đã có nến trong IndexedDB'],
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
          ['Cập nhật', 'Chọn Symbol + TF → tải lại dataset đó từ data/defaults/'],
          ['Xóa', 'Chọn Symbol + TF → xóa dataset đó khỏi IndexedDB'],
          ['Reload Default Data', 'Tải toàn bộ data/defaults/ (~3 năm). Đợi 1–2 phút full history'],
          ['Reset app', 'Xóa TOÀN BỘ dữ liệu app + tải lại như mới cài (nến, settings, kết quả…)'],
          ['Health bar', 'Data OK = có ít nhất một dataset sẵn sàng scan'],
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
        text: 'Health bar báo "Chưa có dữ liệu" → bấm Reload Default Data và đợi. Nếu dùng file:// sẽ không load được — cần http://. Muốn xóa sạch mọi thứ (như cài mới) → Reset app ở cuối màn hình — export trước nếu cần giữ kết quả.',
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
        alt: 'So do Break and Retest Long',
        caption: 'Trên chart: ① giá lắng dưới swing high → ② breakout (chờ, chưa vào) → ③ retest chạm level + nến xanh = LONG. Entry/SL/TP như trên sơ đồ.',
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
        alt: 'So do EMA Pullback Long',
        caption: 'Giá tăng theo EMA20/50 → hồi chạm vùng xanh (EMA20) → nến bật lên cùng bar = LONG. Khác B&R: không chờ nến sau pullback.',
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
        alt: 'So do Liquidity Grab Short',
        caption: 'Nến quét trên swing high (vùng đỏ) nhưng đóng cửa dưới level = stop hunt → SHORT ngay tại close nến đó.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'liquidity-grab-long',
        alt: 'So do Liquidity Grab Long',
        caption: 'Nến quét dưới swing low (vùng xanh) nhưng đóng cửa trên level → LONG ngay. Đối xứng với SHORT ở đỉnh.',
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
    title: 'AI Signals — Chấm & lọc tín hiệu',
    subtitle: 'Điểm 0–100 theo quy tắc — ưu tiên setup đẹp, không dự đoán thắng/thua.',
    icon: '🎯',
    viewIds: ['signals'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Sau mỗi lần scan Strategies, app tự chấm từng tín hiệu 0–100. Dùng thanh Min score để xem trước những setup “trông đẹp” trên chart — tiết kiệm thời gian khi có hàng trăm signal.',
      },
      {
        type: 'callout',
        variant: 'info',
        text: '「AI」ở đây là chấm điểm theo quy tắc (rule-based), không phải mô hình học máy dự đoán giá. Điểm cao = setup lúc vào lệnh nhìn có vẻ chất lượng (trend, nến, RR, phiên…), không phải cam kết lệnh sẽ WIN.',
      },
      {
        type: 'h3',
        text: '8 yếu tố chấm điểm (mỗi yếu tố 0–100)',
      },
      {
        type: 'p',
        text: 'Điểm tổng = trung bình có trọng số của 8 yếu tố dưới đây. Chấm ngay tại nến signal, dùng spread từ cấu hình Simulation (Ctrl+4).',
      },
      {
        type: 'table',
        headers: ['Yếu tố (trên card)', 'Trọng số', 'Đo cái gì', 'Điểm cao khi…'],
        rows: [
          ['trend', `${Config.SCORING.WEIGHTS.trend * 100}%`, 'Xu hướng EMA20/EMA50', 'Giá và EMA cùng hướng với lệnh (long: giá > EMA20 > EMA50)'],
          ['momentum', `${Config.SCORING.WEIGHTS.momentum * 100}%`, 'Sức nến xác nhận', 'Thân nến dài, nến bullish/bearish rõ'],
          ['location', `${Config.SCORING.WEIGHTS.location * 100}%`, 'Vị trí SL so entry', 'SL gần entry (≤5 pip → điểm cao nhất)'],
          ['volatility', `${Config.SCORING.WEIGHTS.volatility * 100}%`, 'Biến động 14 nến', 'Biên độ vừa phải — không quá flat, không quá loạn'],
          ['priceActionQuality', `${Config.SCORING.WEIGHTS.priceActionQuality * 100}%`, 'Râu rejection', 'Long: râu dưới dài; Short: râu trên dài'],
          ['rr', `${Config.SCORING.WEIGHTS.rr * 100}%`, 'Risk:Reward', 'RR càng cao càng tốt (≥2 ~80+, ≥3 → 100)'],
          ['session', `${Config.SCORING.WEIGHTS.session * 100}%`, 'Phiên giao dịch', 'London / New York cao nhất; Asian thấp hơn'],
          ['spread', `${Config.SCORING.WEIGHTS.spread * 100}%`, 'Spread (pip)', 'Spread thấp (từ Simulation config) → điểm cao hơn'],
        ],
      },
      {
        type: 'h3',
        text: 'Grade & Min score',
      },
      {
        type: 'table',
        headers: ['Điểm', 'Grade', 'Gợi ý Min score'],
        rows: [
          ['≥ 80', 'A', 'Chỉ xem setup rất đẹp'],
          ['65–79', 'B', 'Cân bằng số lượng / chất lượng'],
          ['50–64', 'C', 'Bỏ signal rất yếu'],
          ['35–49', 'D', 'Thường không đáng xem'],
          ['< 35', 'F', 'Setup yếu trên hầu hết yếu tố'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Điểm A (80+) vẫn có thể LOSS trong Simulation — giá có thể chạm SL sau khi vào. Điểm chỉ đánh giá lúc signal xuất hiện, không biết tương lai. Muốn biết setup có lãi thật → Run Simulation + Statistics + Walk Forward.',
      },
      {
        type: 'h3',
        text: 'Min score ảnh hưởng gì?',
      },
      {
        type: 'table',
        headers: ['Màn hình', 'Có lọc theo Min score?'],
        rows: [
          ['AI Signals (Ctrl+8)', 'Có — chỉ ẩn/bớt signal dưới ngưỡng'],
          ['Simulation (Ctrl+4)', 'Không — mô phỏng TOÀN BỘ signal từ scan'],
          ['Statistics / Reports', 'Không — đọc kết quả simulation gần nhất'],
        ],
      },
      {
        type: 'p',
        text: 'Muốn simulation ít lệnh hơn: chỉnh tham số strategy chặt hơn hoặc tắt strategy yếu. Min score hiện chỉ dùng để ưu tiên xem chart.',
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Mỗi signal gắn strategy (Break & Retest, EMA Pullback, …). Thanh meta hiện Strategy / Symbol / TF của lần scan gần nhất. Run All Enabled: chỉ giữ kết quả strategy scan cuối — muốn từng strategy thì Run Selected từng cái.',
      },
      {
        type: 'h3',
        text: 'Hai tab trên màn hình',
      },
      {
        type: 'table',
        headers: ['Tab', 'Dùng khi'],
        rows: [
          ['Danh sách', 'Lọc Min score, bấm signal → Chart kiểm tra setup (mặc định)'],
          ['Đối chiếu Simulation', 'Sau Ctrl+4 — win rate theo nhóm điểm, yếu tố thắng/thua, gợi ý trọng số'],
        ],
      },
      {
        type: 'h3',
        text: 'Đối chiếu Simulation (tab 2)',
      },
      {
        type: 'p',
        text: 'Sau khi chạy Simulation (Ctrl+4) cùng Strategy / Symbol / TF với lần scan gần nhất, panel 「Điểm AI vs kết quả thực tế」 hiện ở AI Signals: win rate theo nhóm điểm (A/B/C…), yếu tố nào khác biệt giữa lệnh thắng/thua, tương quan điểm–lãi.',
      },
      {
        type: 'table',
        headers: ['Nút', 'Làm gì'],
        rows: [
          ['Gợi ý trọng số', 'Tối ưu trọng số 8 yếu tố trên các lệnh đã mô phỏng — để điểm cao gắn với lệnh tốt hơn'],
          ['Áp dụng gợi ý', 'Lưu trọng số mới + chấm lại toàn bộ signal'],
          ['Về mặc định', 'Khôi phục trọng số ban đầu trong Config'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Tối ưu trọng số trên cùng bộ lệnh quá khứ có thể học vẹt — cần ≥10 lệnh, nên kiểm tra lại bằng Simulation / Walk Forward trên period khác trước khi tin Min score.',
      },
      {
        type: 'h3',
        text: 'Workflow gợi ý',
      },
      {
        type: 'steps',
        steps: [
          { title: '1. Scan', body: 'Strategies (Ctrl+3) — app tự chấm điểm sau scan.' },
          { title: '2. Lọc', body: 'AI Signals — kéo Min score (ví dụ 65–80).' },
          { title: '3. Kiểm tra mắt', body: 'Bấm signal → Chart nhảy tới nến, vẽ Entry (xanh dương) / SL (đỏ) / TP (xanh).' },
          { title: '4. Chạy số', body: 'Simulation → xem calibration AI vs lệnh + Statistics tổng thể.' },
          { title: '5. Tinh chỉnh (tùy chọn)', body: 'Gợi ý trọng số → áp dụng nếu điểm cao thật sự gắn lệnh tốt hơn trên sample khác.' },
        ],
      },
    ],
  },
  {
    id: 'simulation',
    title: 'Simulation — Mô phỏng lệnh',
    subtitle: 'Từ tín hiệu → lệnh giả (có spread, cắt lỗ, chốt lời).',
    icon: '🔬',
    viewIds: ['simulation'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Giả lập việc vào lệnh trên quá khứ: khớp giá vào, chạm cắt lỗ/chốt lời, kéo SL, chốt một phần… như trade thật nhưng không dùng tiền thật. Kết quả dùng cho Statistics, Reports và tab “xáo thứ tự lệnh” (Monte Carlo) trong Optimizer.',
      },
      {
        type: 'table',
        headers: ['Tham số trên màn hình', 'Nói đơn giản là'],
        rows: [
          ['Spread', 'Phí chênh lệch mua/bán (pip) — mỗi lệnh trừ thêm chi phí này'],
          ['Slippage', 'Giá khớp lệch so với giá mong muốn'],
          ['Lot size', 'Khối lượng giao dịch — giữ cố định khi so sánh'],
          ['Trailing', 'Tự kéo cắt lỗ theo giá khi lệnh đang lãi (0 = tắt)'],
          ['Break-even at R', 'Khi lãi đủ X lần rủi ro → dời SL về điểm vào (hòa vốn)'],
          ['Partial at R / %', 'Chốt một phần lệnh khi đạt X lần rủi ro'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Chạy Strategies (Ctrl+3) trước để có tín hiệu, hoặc Simulation sẽ quét lại. Sau đó xem Statistics / Reports; nếu cần đánh giá rủi ro chuỗi thua → Optimizer tab Monte Carlo. Bấm một dòng lệnh trong bảng kết quả → Chart nhảy tới nến vào lệnh (giống AI Signals).',
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
      { type: 'h3', text: 'Đọc các con số (tên tiếng Anh trên màn hình)' },
      {
        type: 'table',
        headers: ['Trên app', 'Hiểu đơn giản', 'Gợi ý'],
        rows: [
          ['Expectancy', 'Trung bình mỗi lệnh lãi/lỗ bao nhiêu $', 'Dương = về lâu dài có lợi'],
          ['Profit Factor (PF)', 'Tổng tiền thắng ÷ tổng tiền thua', 'Trên 1.2 thường coi là ổn'],
          ['Max Drawdown', 'Từ đỉnh tài khoản rớt sâu nhất bao nhiêu', 'Càng thấp càng dễ chịu tâm lý'],
          ['Win Rate', '% lệnh thắng', 'Thấp vẫn OK nếu lệnh thắng ăn xa (RR cao)'],
          ['Sharpe Ratio', 'Lãi có “êm” không so với độ lên xuống', 'Trên 1 thường ổn'],
          ['Recovery Factor', 'Lãi tổng so với mức sụt sâu nhất', 'Cao = phục hồi tốt sau đợt lỗ'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Đường equity đi lên đều + mức sụt tài khoản thấp = setup ổn hơn. Màn hình trống → chạy Simulation (Ctrl+4) trước.',
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
    title: 'Optimizer — Tối ưu & kiểm định',
    subtitle: 'Tìm cài đặt tốt, tránh “học vẹt” quá khứ, xem chuỗi thua có thể làm tài khoản tệ cỡ nào.',
    icon: '🧪',
    viewIds: ['optimizer'],
    blocks: [
      {
        type: 'callout',
        variant: 'info',
        text: 'Ba câu hỏi màn hình này trả lời: (1) Cài đặt nào cho lãi tốt nhất? (2) Lãi đó có giữ được ở đoạn thời gian “chưa tối ưu” không? (3) Nếu thắng/thua xảy ra theo thứ tự xấu, tài khoản có gần cháy không? Không đặt lệnh thật.',
      },
      {
        type: 'h3',
        text: 'Từ ngữ trên màn hình — nói đơn giản',
      },
      {
        type: 'table',
        headers: ['Tên trên app', 'Hiểu là gì', 'Ví dụ đời thường'],
        rows: [
          ['Grid Search', 'Thử lưới cài đặt — chạy từng combo xem combo nào tốt nhất', 'Thử 3 độ dài EMA khác nhau, xem độ nào lãi nhất'],
          ['Walk Forward', 'Kiểm tra theo thời gian — lãi ở đoạn cũ có còn ở đoạn mới ngay sau không', 'Học bài tuần 1–4, thi tuần 5 — không được xem đáp án tuần 5 khi học'],
          ['Monte Carlo', 'Xáo thứ tự các lệnh đã có — xem tài khoản có thể tệ đến mức nào', 'Cùng 100 lệnh thắng/thua, chỉ đổi thứ tự → đợt lỗ dài có thể sâu hơn'],
          ['Overfit (học vẹt)', 'Chỉnh cài đặt khớp quá khít quá khứ → sang giai đoạn mới lại lỗ', 'Thuộc lòng đề cũ nhưng đề mới thì trượt'],
          ['IS / In-sample', 'Đoạn “học” — đoạn dùng để tin setup tốt', 'Phần lịch sử bạn đã nhìn khi chọn cài đặt'],
          ['OOS / Out-of-sample', 'Đoạn “thử” — đoạn ngay sau, quan trọng hơn IS', 'Giai đoạn bạn chưa “tối ưu” cho nó'],
          ['Combo', 'Một bộ cài đặt cụ thể (ví dụ RR=2, lookback=20)', 'Một “công thức” tham số'],
          ['Fold', 'Một lượt chia đoạn cũ/mới trong Walk Forward', 'Một lần học + một lần thi'],
          ['Iterations', 'Số lần xáo thứ tự lệnh trong Monte Carlo', 'Xáo bài 1000 lần'],
          ['Ruin Rate', '% lần mô phỏng mà tài khoản gần như cháy', 'Bao nhiêu % lần “đi xuống gần hết tiền”'],
          ['P5 / P50 / P95', 'Kịch bản xấu / trung bình / đẹp trong hàng nghìn lần thử', 'P5 = 95% trường hợp còn tệ hơn; P95 = chỉ 5% may hơn'],
        ],
      },
      {
        type: 'h3',
        text: 'Ba tab — khi nào dùng?',
      },
      {
        type: 'table',
        headers: ['Tab trên app', 'Làm gì', 'Khi nào bấm'],
        rows: [
          ['Grid Search', 'Thử nhiều combo cài đặt, xếp hạng theo chỉ số bạn chọn', 'Đã có nến, muốn tìm RR, lookback… tốt hơn mặc định'],
          ['Walk Forward', 'Chia lịch sử thành nhiều đoạn — phát hiện học vẹt quá khứ', 'Sau Grid Search, đã Save cài đặt vào Strategies'],
          ['Monte Carlo', 'Xáo thứ tự lệnh đã mô phỏng — xem balance & tỷ lệ gần cháy', 'Sau Simulation — phải có danh sách lệnh thật'],
        ],
      },
      {
        type: 'h3',
        text: 'Thanh chọn chung (đầu màn hình)',
      },
      {
        type: 'table',
        headers: ['Thành phần', 'Ý nghĩa'],
        rows: [
          ['Strategy', 'Chiến lược cần thử (Break & Retest, EMA Pullback, Liquidity Grab)'],
          ['Symbol / TF', 'Chỉ hiện cặp đã có nến — phải khớp data bạn đang nghiên cứu'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Grid Search và Walk Forward dùng cấu hình lệnh từ Simulation (spread, trượt giá, lot, số dư…). Chỉnh ở Simulation (Ctrl+4) trước nếu muốn số liệu sát trade thật.',
      },
      {
        type: 'h3',
        text: 'Quy trình khuyến nghị (5 bước)',
      },
      {
        type: 'steps',
        steps: [
          { title: '1. Grid Search', body: 'Chọn Strategy + Symbol + TF → tick tham số muốn thử → Run → xem bảng Top Results.' },
          { title: '2. Áp cài đặt', body: 'Copy combo tốt (cột Params) → Strategies → dán/chỉnh → Save Parameters.' },
          { title: '3. Walk Forward', body: 'Tab Walk Forward → Run — so sánh lãi đoạn “học” (IS) vs đoạn “thử” (OOS).' },
          { title: '4. Simulation', body: 'Ctrl+4 mô phỏng lệnh với cài đặt đã chọn — tạo danh sách lệnh.' },
          { title: '5. Monte Carlo', body: 'Tab Monte Carlo → Run — đọc Ruin Rate và P5 (kịch bản xấu).' },
        ],
      },
      { type: 'h3', text: 'Tab 1 — Grid Search (thử lưới cài đặt)' },
      {
        type: 'p',
        text: 'Chạy mô phỏng cho mọi tổ hợp cài đặt bạn chọn, trên toàn bộ lịch sử nến. Mỗi combo = quét tín hiệu + giả lập lệnh (giống Simulation) → ra các con số thống kê.',
      },
      {
        type: 'table',
        headers: ['Thành phần', 'Cách dùng'],
        rows: [
          ['Checkbox tham số', 'Tick để đưa vào lưới thử. Ít tick = ít combo = nhanh hơn, ít học vẹt hơn.'],
          ['Ô giá trị', 'Danh sách: 2,3,4,5 hoặc dải: 10:50:10 (bắt đầu:kết thúc:bước).'],
          ['Rank by', 'Xếp hạng combo theo chỉ số — mặc định Expectancy (lãi trung bình/lệnh).'],
          ['Run Grid Search', 'Bắt đầu — thanh progress hiện X / tổng combo.'],
          ['Top Results', '20 combo đầu: Params, Trades, WR, Net, Exp, PF. Export JSON để lưu.'],
        ],
      },
      {
        type: 'table',
        headers: ['Rank by', 'Nói đơn giản', 'Khi nào chọn'],
        rows: [
          ['Expectancy', 'Trung bình mỗi lệnh lãi/lỗ bao nhiêu $', 'Mặc định — cân bằng chất lượng setup'],
          ['Net Profit', 'Tổng tiền lãi cả giai đoạn', 'Muốn tối đa hóa lãi tuyệt đối'],
          ['Profit Factor', 'Tổng thắng ÷ tổng thua', 'Ưu tiên tỷ lệ tiền thắng/thua'],
          ['Sharpe Ratio', 'Lãi có ổn so với độ lên xuống không', 'So combo có mức sụt tài khoản khác nhau'],
          ['Win Rate', '% lệnh thắng', 'Chỉ khi chấp nhận ít lệnh nhưng tỷ lệ thắng cao'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: `Tối đa ${Config.OPTIMIZER.MAX_COMBINATIONS} combo/lần. Ưu tiên combo có ≥30 lệnh. Đừng tick quá nhiều tham số — dễ “học vẹt” quá khứ (overfit).`,
      },
      {
        type: 'h3',
        text: 'Tham số strategy trong Grid (theo từng setup)',
      },
      {
        type: 'table',
        headers: ['Strategy', 'Tham số', 'Ý nghĩa'],
        rows: [
          ['Break & Retest', 'Breakout (pips)', 'Giá phải vượt level tối thiểu bao nhiêu pip mới tính breakout'],
          ['Break & Retest', 'Retest Max Bars', 'Tối đa bao nhiêu nến chờ retest sau breakout'],
          ['Break & Retest', 'Risk Reward', 'Chốt lời xa gấp mấy lần cắt lỗ (RR)'],
          ['Break & Retest', 'Swing Lookback', 'Số nến tìm đỉnh/đáy làm level'],
          ['EMA Pullback', 'EMA Fast / Slow', 'Chu kỳ EMA xác định xu hướng và vùng pullback'],
          ['EMA Pullback', 'Pullback Tolerance (pips)', 'Độ rộng vùng chạm EMA nhanh'],
          ['EMA Pullback', 'Trend Confirmation Bars', 'Số nến xác nhận xu hướng'],
          ['EMA Pullback', 'Risk Reward', 'Tỷ lệ chốt lời / cắt lỗ'],
          ['Liquidity Grab', 'Grab (pips)', 'Quét thanh khoản vượt level bao nhiêu pip'],
          ['Liquidity Grab', 'Min Wick Ratio', 'Râu nến từ chối tối thiểu so với biên độ nến'],
          ['Liquidity Grab', 'Swing Lookback', 'Tìm đỉnh/đáy thanh khoản'],
          ['Liquidity Grab', 'Risk Reward', 'Tỷ lệ chốt lời / cắt lỗ'],
        ],
      },
      { type: 'h3', text: 'Tab 2 — Walk Forward (kiểm tra theo thời gian)' },
      {
        type: 'p',
        text: 'Chia chuỗi nến thành nhiều “fold” (lượt). Mỗi fold: mô phỏng trên đoạn A (in-sample — đoạn “học”) → kiểm tra trên đoạn B ngay sau (out-of-sample — đoạn “thử”), dùng cùng cài đặt đã lưu trong Strategies (không tối ưu lại từng fold).',
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Nói đơn giản'],
        rows: [
          ['In-sample %', `${Config.OPTIMIZER.IN_SAMPLE_RATIO * 100}%`, 'Phần lịch sử dùng để tin setup tốt trong mỗi fold'],
          ['OOS %', `${Config.OPTIMIZER.OOS_RATIO * 100}%`, 'Phần ngay sau — giống giai đoạn bạn chưa tối ưu cho nó'],
          ['Folds', String(Config.OPTIMIZER.WALK_FORWARD_FOLDS), 'Số lần lặp “học rồi thi” trên timeline'],
        ],
      },
      {
        type: 'table',
        headers: ['Kết quả', 'Nói đơn giản'],
        rows: [
          ['Avg IS Profit', 'Lãi trung bình trên các đoạn “học”'],
          ['Avg OOS Profit', 'Lãi trung bình đoạn “thử” — quan trọng hơn IS'],
          ['OOS Profitable %', '% lượt mà đoạn thử vẫn có lãi'],
          ['Bảng từng Fold', 'Chi tiết từng lượt: thời gian, số lệnh, lãi IS vs OOS'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'IS lãi nhiều mà OOS lỗ = học vẹt quá khứ (overfit). IS và OOS đều lãi, OOS Profitable % cao = setup bền hơn. Walk Forward dùng cài đặt hiện tại trong Strategies — nhớ Save Parameters sau Grid Search.',
      },
      { type: 'h3', text: 'Tab 3 — Monte Carlo (xáo thứ tự lệnh)' },
      {
        type: 'p',
        text: 'Lấy danh sách lệnh từ Simulation gần nhất, xáo ngẫu nhiên thứ tự N lần (mặc định 1000). Cùng bộ lệnh, khác thứ tự thắng/thua → đợt lỗ dài có thể sâu hơn — đây là cách xem “nếu may rủi xấu thì tài khoản tệ cỡ nào”.',
      },
      {
        type: 'table',
        headers: ['Tham số / Kết quả', 'Nói đơn giản'],
        rows: [
          ['Iterations', `Số lần xáo (mặc định ${Config.OPTIMIZER.MONTE_CARLO_ITERATIONS}, chọn 100–10000)`],
          ['Ruin Rate', '% lần mà số dư gần như cháy (dưới ngưỡng phá sản)'],
          ['P5 (worst)', 'Kịch bản xấu — 95% lần thử còn tệ hơn mức này'],
          ['P50 (median)', 'Giữa đường — kết quả “thường gặp”'],
          ['P95 (best)', 'Kịch bản đẹp — chỉ 5% lần may hơn'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Bắt buộc chạy Simulation (Ctrl+4) trước — Monte Carlo không tạo lệnh mới, chỉ xáo lại lệnh đã có. Đổi cài đặt → Simulation lại → Monte Carlo lại.',
      },
      {
        type: 'h3',
        text: 'Lỗi thường gặp',
      },
      {
        type: 'ul',
        items: [
          '「Chưa có dữ liệu」— Data Manager → Reload Default hoặc Import.',
          '「Select at least one parameter」— Grid Search: tick ít nhất một tham số có giá trị.',
          `Quá ${Config.OPTIMIZER.MAX_COMBINATIONS} combo — bỏ tick bớt tham số hoặc rút ngắn dải giá trị.`,
          'Monte Carlo không có lệnh — chạy Simulation trước.',
          'Walk Forward tệ dù Grid Search đẹp — dấu hiệu học vẹt; thử ít tham số hơn hoặc period/cặp khác.',
        ],
      },
    ],
  },
  {
    id: 'glossary',
    title: 'Từ điển thuật ngữ',
    subtitle: 'Tên tiếng Anh trên app — giải thích bằng tiếng đời thường.',
    icon: '📖',
    viewIds: ['docs'],
    blocks: [
      {
        type: 'p',
        text: 'App giữ tên nút/tab tiếng Anh (Grid Search, Walk Forward…) để khớp giao diện. Bảng dưới giúp bạn đọc tài liệu và kết quả mà không cần học thuật ngữ quant.',
      },
      {
        type: 'table',
        headers: ['Thuật ngữ (trên app)', 'Hiểu đơn giản'],
        rows: [
          ['Backtest / Simulation', 'Mô phỏng lệnh trên quá khứ — không dùng tiền thật'],
          ['Signal / Tín hiệu', 'Setup strategy báo “có thể vào lệnh” tại một nến'],
          ['Spread', 'Phí chênh lệch mua/bán — mỗi lệnh trừ thêm'],
          ['SL / TP', 'Cắt lỗ / Chốt lời'],
          ['RR (Risk Reward)', 'Chốt lời xa gấp mấy lần cắt lỗ'],
          ['Expectancy', 'Trung bình mỗi lệnh lãi/lỗ bao nhiêu $'],
          ['Profit Factor (PF)', 'Tổng tiền thắng ÷ tổng tiền thua — trên 1 là còn sống'],
          ['Drawdown', 'Từ đỉnh tài khoản rớt sâu nhất bao nhiêu'],
          ['Win Rate (WR)', '% lệnh thắng'],
          ['Sharpe Ratio', 'Lãi có “êm” không so với độ lên xuống'],
          ['Grid Search', 'Thử nhiều combo cài đặt, xếp hạng kết quả'],
          ['Combo', 'Một bộ tham số cụ thể (ví dụ RR=2, lookback=20)'],
          ['Walk Forward', 'Chia quá khứ: lãi đoạn cũ có còn ở đoạn mới ngay sau không'],
          ['Overfit', 'Học vẹt quá khứ — chỉnh khớp quá khít, live dễ tệ'],
          ['In-sample (IS)', 'Đoạn “học” — đoạn dùng để tin setup tốt'],
          ['Out-of-sample (OOS)', 'Đoạn “thử” — quan trọng hơn IS'],
          ['Fold', 'Một lượt chia IS/OOS trong Walk Forward'],
          ['Monte Carlo', 'Xáo thứ tự lệnh đã có — xem rủi ro chuỗi thua'],
          ['Iterations', 'Số lần xáo trong Monte Carlo'],
          ['Ruin Rate', '% lần mô phỏng tài khoản gần như cháy'],
          ['P5 / P50 / P95', 'Kịch bản xấu / trung bình / đẹp trong nhiều lần thử'],
          ['Edge', 'Lợi thế thật — setup kiếm tiền sau phí, không phải may mắn ngắn hạn'],
          ['AI Score / Min score', 'Điểm chất lượng setup 0–100; Min score chỉ lọc danh sách AI Signals'],
          ['Grade (A/B/C…)', 'Nhãn điểm: A ≥80, B ≥65, C ≥50 — không đảm bảo lệnh WIN'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Mở Optimizer (Ctrl+7) — phần đầu cũng có bảng từ ngữ tương tự, gắn trực tiếp với 3 tab Grid Search, Walk Forward, Monte Carlo.',
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
      { type: 'h3', text: 'Monte Carlo báo không có lệnh?' },
      { type: 'p', text: 'Monte Carlo chỉ xáo lại lệnh từ Simulation — không tạo lệnh mới. Chạy Simulation (Ctrl+4) trước.' },
      { type: 'h3', text: 'Grid search quá chậm / quá nhiều combo?' },
      { type: 'p', text: `Giảm số combo (tối đa ${Config.OPTIMIZER.MAX_COMBINATIONS}): bỏ tick bớt tham số hoặc rút dải giá trị. Dataset lớn tự dùng Web Workers.` },
      { type: 'h3', text: 'Walk Forward tệ dù Grid Search đẹp?' },
      { type: 'p', text: 'Dấu hiệu “học vẹt” quá khứ (overfit) — thử ít tham số hơn, chọn combo có nhiều lệnh, hoặc kiểm tra giai đoạn/cặp khác.' },
      { type: 'h3', text: 'AI score cao mà lệnh vẫn LOSS?' },
      { type: 'p', text: 'Bình thường. Điểm AI đánh giá setup lúc vào lệnh (trend, nến, RR, phiên…), không dự đoán giá sau đó. Simulation không lọc theo Min score — xem Statistics / Walk Forward để đánh giá setup có lãi về lâu dài.' },
      { type: 'h3', text: 'Reset app làm gì?' },
      { type: 'p', text: 'Data Manager → Reset app: xóa IndexedDB (nến), mọi key parl_* (settings, strategy params, simulation/statistics/reports, AI scores), rồi tải lại trang. Giống cài mới — boot sẽ tự seed EURUSD H1 nếu trống. Không hoàn tác — export trước nếu cần.' },
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
