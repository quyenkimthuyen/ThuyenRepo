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
        text: 'Gặp từ khó như Overfit, Walk Forward, Monte Carlo, Ruin Rate…? Mở mục **Từ điển thuật ngữ** trong tài liệu (Ctrl+0) — giải thích bằng tiếng đời thường, kèm tên tiếng Anh trên app.',
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Run Strategies vs Simulation — có cần quét Strategies trước không? Xem mục **Run Strategies vs Simulation** (Ctrl+0).',
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
          { title: 'Chỉnh & (tuỳ chọn) quét', body: 'Strategies — Save tham số; Run nếu muốn lọc signal / xem Chart trước (không bắt buộc trước Simulation).' },
          { title: 'Mô phỏng lệnh', body: 'Simulation — tự quét + spread/SL/TP; kết quả cho Statistics & Reports.' },
          { title: 'Lọc & kiểm chứng', body: 'AI Signals — Min score → bấm signal → Chart xem setup.' },
          { title: 'Tối ưu & kiểm định', body: 'Optimizer — Grid Search → Sensitivity → Walk Forward → Monte Carlo.' },
          { title: 'Đánh giá', body: 'Ưu tiên Expectancy + đủ lệnh; WF OOS ổn định quan trọng hơn Net in-sample.' },
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
          'Chiến lược: Break & Retest, EMA Pullback, Liquidity Grab, Session Liquidity Sweep, Inside Bar, Pin Bar, Wyckoff Spring/UTAD, Wyckoff Range Test',
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
        text: 'PARL chạy hoàn toàn trên trình duyệt. Nến + kết quả nghiên cứu lớn lưu IndexedDB; cài đặt nhẹ lưu LocalStorage — không gửi lên server.',
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
          ['Replay', 'Space=Play, mũi tên= từng nến, Jump= nhảy ngày (UTC)'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Sau scan: mở Chart cùng Symbol/TF, Jump to date (UTC) tại thời điểm signal từ AI Signals hoặc bấm dòng lệnh trong Simulation.',
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
    subtitle: 'Năm setup Price Action: engine duyệt từng nến, không nhìn trước tương lai.',
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
      {
        type: 'h3',
        text: 'Run Strategies vs Run Simulation',
      },
      {
        type: 'p',
        text: 'Run ở Strategies chỉ quét tín hiệu (Entry/SL/TP). Run Simulation quét lại rồi giả lập lệnh có spread, trailing… — không nhất thiết phải Run Strategies trước nếu bạn chỉ cần số liệu lãi/lỗ.',
      },
      {
        type: 'table',
        headers: ['', 'Strategies — Run', 'Simulation — Run'],
        rows: [
          ['Làm gì', 'Quét tín hiệu trên lịch sử nến', 'Quét lại + mô phỏng từng lệnh'],
          ['Spread / phí', 'Không', 'Có (cấu hình Simulation)'],
          ['Statistics / Reports', 'Không', 'Có'],
          ['AI Signals chấm điểm', 'Có', 'Có (sau bước quét lại)'],
          ['Min score', 'Chỉ lọc danh sách AI Signals', 'Không lọc — mô phỏng hết signal'],
          ['Số strategy/lần', 'Run All = nhiều strategy', 'Một strategy chọn trên màn hình'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Không bắt buộc Run Strategies trước Simulation. Nên Run Strategies khi: chỉnh tham số + Save, lọc signal / xem Chart trước, Export JSON, hoặc quét nhiều strategy (Run All). Chi tiết: Ctrl+0 → mục 「Run Strategies vs Simulation」.',
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

      { type: 'h2', text: '4. Inside Bar Breakout (inside-bar-breakout)' },
      {
        type: 'p',
        text: 'Ý tưởng: sau sóng trend, giá nén trong nến mẹ (inside bar) rồi break theo hướng trend. Phù hợp EUR/GBP trên 4H và 1D khi thị trường pause trước continuation.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'inside-bar-breakout-long',
        alt: 'Sơ đồ Inside Bar Breakout Long',
        caption: 'Nến mẹ (vàng) → inside bar (xám) → close phá mother high khi giá trên EMA → LONG. SL dưới mother low.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'inside-bar-breakout-short',
        alt: 'Sơ đồ Inside Bar Breakout Short',
        caption: 'Đối xứng: trend giảm, inside bar trong nến mẹ, close phá mother low dưới EMA → SHORT.',
      },
      { type: 'h3', text: 'LONG' },
      {
        type: 'ol',
        items: [
          'Nến mẹ đủ rộng (motherMinRangePips).',
          'Nến kế là inside bar (high/low nằm trong nến mẹ).',
          'Close phá mother high + buffer, đồng thời close > EMA trend.',
          'SL dưới mother low; TP theo RR.',
        ],
      },
      { type: 'h3', text: 'SHORT — đối xứng' },
      {
        type: 'p',
        text: 'Close phá mother low, close < EMA trend, SL trên mother high.',
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Gợi ý 4H / 1D'],
        rows: [
          ['trendEma', '50', '50 (4H), 50–200 (1D)'],
          ['motherMinRangePips', '10', '15–25 (4H), 30–50 (1D)'],
          ['breakoutBufferPips', '1', '1–2 pip'],
          ['maxWaitBars', '3', '2–5 nến chờ break'],
          ['rr', '2', '2–3'],
        ],
      },

      { type: 'h2', text: '5. Pin Bar Rejection (pin-bar-rejection)' },
      {
        type: 'p',
        text: 'Ý tưởng: giá chạm swing high/low (không cần quét vượt như Liquidity Grab), nến pin rejection (râu dài, thân nhỏ) + nến xác nhận → vào theo hướng bounce/fade.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'pin-bar-rejection-short',
        alt: 'Sơ đồ Pin Bar Rejection Short',
        caption: 'Giá chạm swing high → pin bar râu trên dài + nến giảm → SHORT tại close. Không cần quét vượt level.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'pin-bar-rejection-long',
        alt: 'Sơ đồ Pin Bar Rejection Long',
        caption: 'Chạm swing low → hammer/pin râu dưới + nến tăng → LONG tại close.',
      },
      { type: 'h3', text: 'Khác Liquidity Grab' },
      {
        type: 'table',
        headers: ['', 'Pin Bar Rejection', 'Liquidity Grab'],
        rows: [
          ['Chạm level', 'Chạm vùng swing là đủ', 'Phải quét qua swing + grabPips'],
          ['Pattern', 'Pin bar (wick + body nhỏ)', 'Sweep + đóng lại trong range'],
        ],
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Tác dụng'],
        rows: [
          ['swingLookback', '7', 'Độ rộng swing S/R — lớn hơn trên 1D'],
          ['retestTolerancePips', '2', 'Vùng chạm level'],
          ['minWickRatio', '0.55', 'Râu rejection tối thiểu'],
          ['maxBodyRatio', '0.35', 'Thân nến phải nhỏ'],
          ['rr', '2', 'TP theo R'],
        ],
      },

      { type: 'h2', text: '6. Wyckoff Spring / UTAD (wyckoff-spring-utad)' },
      {
        type: 'p',
        text: 'Ý tưởng Wyckoff: sau giai đoạn tích lũy/phân phối trong trading range, giá quét qua biên range (spring ở đáy, UTAD ở đỉnh) rồi đóng cửa quay lại trong range — vào lệnh NGAY tại nến spring/UTAD. Khác Liquidity Grab: bắt buộc có range consolidation trước đó.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'wyckoff-spring-utad-long',
        alt: 'So do Wyckoff Spring Long',
        caption: 'Gia sideway trong range (vang) → nen spring quet duoi range low nhung dong cua tren bien → LONG ngay tai close. SL duoi day spring.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'wyckoff-spring-utad-short',
        alt: 'So do Wyckoff UTAD Short',
        caption: 'Doi xung: UTAD quet tren range high, dong cua quay lai trong range → SHORT tai close. Bat buoc co phase tich luy truoc.',
      },
      { type: 'h3', text: 'LONG — Spring' },
      {
        type: 'ol',
        items: [
          'Trading range: max(high) / min(low) của rangeLookback nến trước, chiều cao ≥ minRangePips.',
          '≥ minInsideRatio số close nằm trong range (sideway thật, không trend).',
          'low quét dưới rangeLow − sweepPips, close > rangeLow (false break).',
          'Râu dưới ≥ wickRatio + nến xác nhận tăng → LONG tại close.',
        ],
      },
      { type: 'h3', text: 'SHORT — UTAD' },
      {
        type: 'p',
        text: 'Đối xứng: high quét trên rangeHigh + sweepPips, close < rangeHigh, râu trên rejection + nến giảm.',
      },
      {
        type: 'table',
        headers: ['', 'Wyckoff Spring/UTAD', 'Liquidity Grab'],
        rows: [
          ['Level', 'Biên trading range (dài hơn)', 'Swing high/low ngắn'],
          ['Bối cảnh', 'Bắt buộc consolidation trong range', 'Không cần range'],
          ['Entry', 'Tại nến spring/UTAD', 'Tại nến quét swing'],
        ],
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Gợi ý 4H / 1D'],
        rows: [
          ['rangeLookback', '20', '20–30 (4H), 30–50 (1D)'],
          ['minRangePips', '15', '15–25 (4H), 30–60 (1D)'],
          ['minInsideRatio', '0.65', '0.6–0.75'],
          ['sweepPips', '2', '2–4'],
          ['wickRatio', '0.55', '0.5–0.65'],
          ['rr', '2', '2–3'],
        ],
      },

      { type: 'h2', text: '7. Wyckoff Range Test (wyckoff-range-test)' },
      {
        type: 'p',
        text: 'Ý tưởng Wyckoff cổ điển: sau spring/UTAD, giá rally rồi quay lại test biên range lần hai (higher low / lower high) — entry tại nến test, không vào ngay tại spring/UTAD. Conservative hơn strategy §6.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'wyckoff-range-test-long',
        alt: 'So do Wyckoff Range Test Long',
        caption: '① Spring (chua vao) → ② Rally roi bien → ③ Test higher low tai range low + nen xanh = LONG tai nen test.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'wyckoff-range-test-short',
        alt: 'So do Wyckoff Range Test Short',
        caption: 'Doi xung: UTAD → giam manh → test lower high tai range high → SHORT. An toan hon vao ngay tai UTAD.',
      },
      { type: 'h3', text: 'Luồng LONG' },
      {
        type: 'ol',
        items: [
          'Nến spring hợp lệ (giống §6) → ghi nhận setup, chưa vào lệnh.',
          'Trong testMaxBars nến: giá rally ≥ rallyMinPips phía trên rangeLow.',
          'Nến test chạm vùng rangeLow ± testTolerancePips, low > đáy spring (không phá spring).',
          'Nến xác nhận tăng → LONG tại close test.',
        ],
      },
      { type: 'h3', text: 'Luồng SHORT — đối xứng UTAD test' },
      {
        type: 'p',
        text: 'UTAD → giá giảm ≥ rallyMinPips → test lại rangeHigh với high thấp hơn đỉnh UTAD → SHORT.',
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Tác dụng'],
        rows: [
          ['testMaxBars', '8', 'Thời gian chờ test sau spring/UTAD'],
          ['rallyMinPips', '5', 'Phải có sóng rời biên trước khi test hợp lệ'],
          ['testTolerancePips', '3', 'Vùng chạm biên range khi test'],
          ['eventWickRatio', '0.5', 'Wick tối thiểu trên nến spring/UTAD (arm setup)'],
          ['testWickRatio', '0.45', 'Wick tối thiểu trên nến test entry'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Dùng §6 khi muốn vào sớm tại spring/UTAD; dùng §7 khi muốn xác nhận test lần hai theo Wyckoff. Có thể bật cả hai strategy và so sánh trên Simulation.',
      },

      { type: 'h2', text: '8. Session Liquidity Sweep (session-liquidity-sweep)' },
      {
        type: 'p',
        text: 'Ý tưởng: quét thanh khoản tại biên phiên giao dịch (Asian range, London morning, swing) trong khung giờ London/NY — **chờ nến xác nhận** rồi fade false breakout. Thiết kế cho EURUSD H1 nhưng chạy được mọi symbol/TF. Khác Liquidity Grab: nhiều nguồn level + entry 2 pha + lọc phiên & volatility.',
      },
      {
        type: 'image',
        layout: 'portrait',
        diagramId: 'session-liquidity-sweep-short',
        alt: 'So do Session Liquidity Sweep Short',
        caption: 'Nen 1: quet Asian high (sweep) → Nen 2: nen do xac nhan, dong duoi level = SHORT. SL tren dinh sweep.',
      },
      { type: 'h3', text: 'Luồng 2 pha (state machine)' },
      {
        type: 'ol',
        items: [
          'Pha 1 — Sweep (bar s): high/low vuot level + grabPips, close quay lai trong vung, rau rejection du lon → ghi pending, CHUA vao lenh.',
          'Pha 2 — Confirm (bar c, trong confirmMaxBars): nen xac nhan huong fade, khong pha dinh/day sweep, close dung phia level → ENTRY tai close.',
        ],
      },
      { type: 'h3', text: 'Nguồn liquidity (kiểm tra đồng thời)' },
      {
        type: 'table',
        headers: ['Nguồn', 'Khi nào', 'Ví dụ EURUSD H1'],
        rows: [
          ['Asian (hôm nay)', 'Sau 07 UTC cùng ngày', 'Đỉnh/đáy nến 00–06 UTC'],
          ['Prev Asian', 'London sớm (nếu bật)', 'Biên phiên Á hôm qua'],
          ['London morning', 'Sau 12 UTC cùng ngày', 'Đỉnh/đáy nến 07–11 UTC'],
          ['Swing', 'Tùy chọn (useSwingLevels)', 'Swing high/low — mặc định tắt (grid: lãi tốt hơn)'],
        ],
      },
      { type: 'h3', text: 'SHORT — đủ điều kiện' },
      {
        type: 'ol',
        items: [
          'Trong session 06–20 UTC (mặc định) và volOk (biến động ≥ ngưỡng).',
          'Sweep: high ≥ level_high + grabPips, close < level_high, râu trên ≥ wickRatio.',
          'Confirm: high không vượt đỉnh sweep, close < level, nến giảm xác nhận.',
          'SL = trên high nến sweep + buffer; TP theo rr (mặc định 1.5).',
        ],
      },
      { type: 'h3', text: 'LONG — đối xứng' },
      {
        type: 'p',
        text: 'Sweep đáy (Asian low / London low / swing low) → confirm tăng, close trên level, SL dưới đáy sweep.',
      },
      { type: 'h3', text: 'Khi nào KHÔNG có tín hiệu?' },
      {
        type: 'ul',
        items: [
          'Ngoài khung sessionStartHour–sessionEndHour.',
          'Thị trường “chết” — avg range 14 nến < minVolatilityRatio × median.',
          'Sweep nhưng không có nến confirm trong confirmMaxBars.',
          'Nến confirm phá lại đỉnh/đáy sweep (invalidation).',
          'Đã có signal cùng hướng từ cùng level gần đây.',
        ],
      },
      {
        type: 'table',
        headers: ['', 'Session Liquidity Sweep', 'Liquidity Grab'],
        rows: [
          ['Entry', 'Nến confirm (1–2 bar sau sweep)', 'Ngay nến sweep'],
          ['Level', 'Asian + London (swing tùy chọn)', 'Chỉ swing'],
          ['Phiên', '06–20 UTC (mặc định)', 'Mọi giờ'],
          ['Volatility', 'Bắt buộc volOk (min 1.1)', 'Không lọc'],
          ['RR mặc định', '1.5', '2'],
        ],
      },
      {
        type: 'table',
        headers: ['Tham số', 'Mặc định', 'Tác dụng'],
        rows: [
          ['asianEndHour', '7', 'Asian range = nến UTC 00–06 trên H1'],
          ['londonEndHour', '12', 'London morning = 07–11 UTC'],
          ['sessionStartHour / sessionEndHour', '6 / 20', 'Chỉ trade trong khung này'],
          ['grabPips', '5', 'Quét level thêm X pip — lọc touch nhẹ'],
          ['wickRatio', '0.6', 'Râu rejection trên nến sweep'],
          ['confirmMaxBars', '1', 'Chờ tối đa bao nhiêu nến sau sweep'],
          ['minVolatilityRatio', '1.1', 'Chỉ trade khi biến động đủ lớn'],
          ['usePrevAsian', 'true', 'Dùng biên Á hôm trước lúc London mở'],
          ['useSwingLevels', 'false', 'Swing fallback — grid tắt = Net tốt hơn'],
          ['minSessionRangePips', '0', 'Bỏ range phiên quá hẹp (0 = tắt)'],
          ['maxVolatilityRatio', '0', 'Cap biến động cực đoan (0 = tắt)'],
          ['confirmClosePips', '0', 'Close confirm vượt level thêm X pip (0 = tắt)'],
          ['tradeCooldownBars', '0', 'Nến tối thiểu giữa hai entry'],
          ['swingLookback', '10', 'Khi useSwingLevels=true'],
          ['rr', '1.5', 'TP theo R — RR thấp hơn LG để tăng WR'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Gợi ý workflow: EURUSD H1 → Suggest from data (Optimizer) → Grid grabPips / wickRatio / minVol / sessionEndHour → Sensitivity → Walk Forward. Backtest mặc định v1.2 ~23 lệnh/3 năm, WR ~65%, Net ~$388 (in-sample) — không phải lời khuyên đầu tư.',
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Chiến lược selective — kỳ vọng vài chục lệnh/năm trên H1, không phải scalping. Luôn kiểm tra OOS trước khi áp param vào live.',
      },

      { type: 'h3', text: 'Nến xác nhận (dùng chung các strategy)' },
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
    id: 'compare',
    title: 'Compare — So sánh strategy',
    subtitle: 'Xếp hạng nhiều setup trên cùng Symbol/TF theo expectancy.',
    icon: '⚖️',
    viewIds: ['compare'],
    blocks: [
      { type: 'h3', text: 'Mục đích' },
      {
        type: 'p',
        text: 'Trả lời nhanh: trên cùng bộ nến, strategy nào cho expectancy tốt nhất sau spread — trước khi tối ưu tham số sâu hoặc chọn một setup “chính”.',
      },
      {
        type: 'table',
        headers: ['Bước', 'Thao tác'],
        rows: [
          ['1', 'Chọn Symbol + TF (cùng data đang nghiên cứu)'],
          ['2', 'Tick/bỏ tick từng strategy trong danh sách'],
          ['3', 'Bấm Compare — app scan + mô phỏng lệnh từng setup'],
          ['4', 'Đọc bảng: Signals, Trades, WR, Net, Exp, PF, Max DD — hàng #1 highlight'],
        ],
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Dùng spread/lot từ Simulation (Ctrl+5). Chỉnh Simulation trước nếu muốn số liệu sát điều kiện trade thật. Kết quả lưu IndexedDB — mở lại Compare vẫn thấy lần chạy gần nhất.',
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Workflow: Compare (Ctrl+4) → chọn setup tốt → Strategies Save tham số → Simulation backtest chi tiết → Optimizer nếu cần tinh chỉnh.',
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
        text: 'Điểm tổng = trung bình có trọng số của 8 yếu tố dưới đây. Chấm ngay tại nến signal, dùng spread từ cấu hình Simulation (Ctrl+5).',
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
          ['AI Signals (Ctrl+9)', 'Có — lọc danh sách xem trên màn này'],
          ['Simulation (Ctrl+5)', 'Có — bật AI score filter + Min score; tuỳ chọn Compare vs all signals'],
          ['Statistics / Reports', 'Theo kết quả Simulation gần nhất (đã lọc nếu bật filter)'],
        ],
      },
      {
        type: 'p',
        text: 'Muốn backtest chỉ signal điểm cao: Simulation → tick AI score filter, đặt Min score, (tuỳ chọn) Compare vs all signals để xem lọc có cải thiện Net/Exp không.',
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
          ['Đối chiếu Simulation', 'Sau Ctrl+5 — win rate theo nhóm điểm, yếu tố thắng/thua, gợi ý trọng số'],
        ],
      },
      {
        type: 'h3',
        text: 'Đối chiếu Simulation (tab 2)',
      },
      {
        type: 'p',
        text: 'Sau khi chạy Simulation (Ctrl+5) cùng Strategy / Symbol / TF với lần scan gần nhất, panel 「Điểm AI vs kết quả thực tế」 hiện ở AI Signals: win rate theo nhóm điểm (A/B/C…), yếu tố nào khác biệt giữa lệnh thắng/thua, tương quan điểm–lãi.',
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
          { title: '1. (Tuỳ chọn) Strategies', body: 'Ctrl+3 — Save tham số, Run nếu muốn lọc / xem Chart trước. Không bắt buộc trước Simulation.' },
          { title: '2. Simulation', body: 'Ctrl+5 — Run; bật AI filter nếu muốn chỉ trade signal điểm cao.' },
          { title: '3. Lọc & Chart', body: 'AI Signals tab Danh sách — Min score → bấm signal.' },
          { title: '4. Đối chiếu', body: 'AI Signals tab Đối chiếu Simulation — WR theo nhóm điểm.' },
          { title: '5. Tinh chỉnh (tuỳ chọn)', body: 'Gợi ý trọng số — kiểm tra lại trên period khác.' },
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
        type: 'callout',
        variant: 'info',
        text: 'Run Simulation tự quét lại strategy (giống Strategies) rồi mô phỏng lệnh — không cần Run Strategies trước nếu tham số đã Save và bạn chỉ cần xem lãi/lỗ. Mỗi lần bấm Run vẫn quét lại để khớp cài đặt hiện tại.',
      },
      {
        type: 'h3',
        text: 'Khác gì Run Strategies?',
      },
      {
        type: 'table',
        headers: ['Chỉ Strategies', 'Thêm khi Simulation'],
        rows: [
          ['Danh sách signal + chấm điểm AI', 'Bảng lệnh win/loss + lãi $'],
          ['Xem Chart từng setup', 'Statistics, Reports, Monte Carlo'],
          ['Không trừ spread', 'Spread, slippage, trailing, BE, partial'],
        ],
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
          ['AI score filter', 'Bật → chỉ mô phỏng signal có điểm AI ≥ Min score'],
          ['Min score', 'Ngưỡng 0–100 (mặc định 65 khi bật filter)'],
          ['Compare vs all signals', 'So song song: toàn bộ signal vs đã lọc (WR, Net, Exp)'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Chạy Strategies (Ctrl+3) trước nếu muốn xem signal trước; Simulation tự quét lại khi Run. Sau đó Statistics/Reports; Monte Carlo cần danh sách lệnh từ Simulation. Bấm một dòng lệnh → Chart nhảy tới nến entry.',
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
        text: 'Đường equity đi lên đều + mức sụt tài khoản thấp = setup ổn hơn. Màn hình trống → chạy Simulation (Ctrl+5) trước.',
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
        type: 'callout',
        variant: 'info',
        text: 'Cập nhật 28/06/2025: tab Sensitivity riêng; Suggest from data / Restore defaults / Apply best to Strategy; grid search parallel (≥4 combo); form giữ khi đổi tab; chart WR/Exp/Net theo param đã grid.',
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
          ['Rank by', 'Tiêu chí xếp hạng combo: Exp, Net, PF, WR…', 'Chọn Expectancy nếu muốn so chất lượng mỗi lệnh'],
          ['Parallel', 'Grid ≥4 combo chạy song song Web Workers', '4 luồng cùng lúc — nhanh hơn chạy tuần tự'],
          ['Sensitivity', 'Biểu đồ WR / Expectancy / Net theo từng giá trị param đã chạy grid', 'RR=2 lãi hơn RR=3 không — nhìn đường trên chart'],
          ['Suggest from data', 'Gợi ý lưới giá trị từ biến động nến hiện tại', 'App đọc avg range 14 nến rồi điền breakoutPips, rr…'],
          ['Restore defaults', 'Khôi phục lưới mặc định (default ± 1 bước)', 'Xóa gợi ý Suggest, về tick rr + 3 giá trị quanh default'],
          ['Apply best to Strategy', 'Lưu combo xếp hạng #1 vào Strategies', 'Không cần copy tay từ bảng Params'],
          ['Walk Forward (WF)', 'Kiểm tra theo thời gian — lãi ở đoạn cũ có còn ở đoạn mới ngay sau không', 'Học bài tuần 1–4, thi tuần 5 — không được xem đáp án tuần 5 khi học'],
          ['Monte Carlo (MC)', 'Xáo thứ tự các lệnh đã có — xem tài khoản có thể tệ đến mức nào', 'Cùng 100 lệnh thắng/thua, chỉ đổi thứ tự → đợt lỗ dài có thể sâu hơn'],
          ['WR / Exp / PF / Net', 'Win Rate / Expectancy / Profit Factor / Net Profit — cột trong Top Results', 'WR=% thắng; Exp=$/lệnh; PF=thắng÷thua; Net=tổng $'],
          ['Overfit (học vẹt)', 'Chỉnh cài đặt khớp quá khít quá khứ → sang giai đoạn mới lại lỗ', 'Thuộc lòng đề cũ nhưng đề mới thì trượt'],
          ['IS / In-sample', 'Đoạn “học” — đoạn dùng để tin setup tốt', 'Phần lịch sử bạn đã nhìn khi chọn cài đặt'],
          ['OOS / Out-of-sample', 'Đoạn “thử” — đoạn ngay sau, quan trọng hơn IS', 'Giai đoạn bạn chưa “tối ưu” cho nó'],
          ['Combo', 'Một bộ cài đặt cụ thể (ví dụ RR=2, lookback=20)', 'Một “công thức” tham số'],
          ['Fold', 'Một lượt chia đoạn cũ/mới trong Walk Forward', 'Một lần học + một lần thi'],
          ['Iterations', 'Số lần xáo thứ tự lệnh trong Monte Carlo', 'Xáo bài 1000 lần'],
          ['Ruin Rate', '% lần mô phỏng mà tài khoản gần như cháy', 'Bao nhiêu % lần “đi xuống gần hết tiền”'],
          ['P5 / P50 / P95', 'Kịch bản xấu / trung bình / đẹp trong hàng nghìn lần thử', 'P5 = 95% trường hợp còn tệ hơn; P95 = chỉ 5% may hơn'],
          ['optimizedParamKeys', 'Danh sách param đã tick trong grid gần nhất — dùng cho tab Sensitivity', 'Chỉ param đã grid mới có chart'],
        ],
      },
      {
        type: 'h3',
        text: 'Bốn tab — khi nào dùng?',
      },
      {
        type: 'table',
        headers: ['Tab trên app', 'Làm gì', 'Khi nào bấm'],
        rows: [
          ['Grid Search', 'Thử nhiều combo cài đặt, xếp hạng theo chỉ số bạn chọn', 'Đã có nến, muốn tìm RR, lookback… tốt hơn mặc định'],
          ['Sensitivity', 'Biểu đồ trung bình WR, Expectancy, Net Profit theo từng giá trị param', 'Sau Grid Search — xem param nào ổn, có bị “nhọn” overfit không'],
          ['Walk Forward', 'Chia lịch sử thành nhiều đoạn — phát hiện học vẹt quá khứ', 'Sau Grid Search, đã Save / Apply best vào Strategies'],
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
          ['Strategy', 'Chiến lược cần thử — 8 setup'],
          ['Symbol / TF', 'Chỉ hiện cặp đã có nến — phải khớp data bạn đang nghiên cứu'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Grid Search và Walk Forward dùng cấu hình lệnh từ Simulation (spread, trượt giá, lot, số dư…). Chỉnh ở Simulation (Ctrl+5) trước nếu muốn số liệu sát trade thật.',
      },
      {
        type: 'h3',
        text: 'Quy trình khuyến nghị (5 bước)',
      },
      {
        type: 'steps',
        steps: [
          { title: '1. Grid Search', body: 'Suggest from data (tuỳ chọn) → tick param → Run → Top Results. Có Apply best to Strategy và auto walk-forward nếu bật.' },
          { title: '2. Sensitivity', body: 'Tab Sensitivity → chọn param đã grid → xem WR / Exp / Net. Chỉ param từ lần grid gần nhất.' },
          { title: '3. Áp cài đặt', body: 'Apply best to Strategy hoặc copy combo tốt → Strategies → Save Parameters.' },
          { title: '4. Walk Forward', body: 'Tab Walk Forward → Run — so IS vs OOS.' },
          { title: '5. Simulation + Monte Carlo', body: 'Ctrl+5 mô phỏng lệnh → Monte Carlo xáo thứ tự.' },
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
          ['Suggest from data', 'Gợi ý lưới từ biến động nến — message hiện dưới danh sách param.'],
          ['Restore defaults', 'Về lưới mặc định cho strategy hiện tại.'],
          ['Rank by', 'Xếp hạng combo theo chỉ số — mặc định Expectancy (lãi trung bình/lệnh).'],
          ['Run Grid Search', 'Bắt đầu — progress X/tổng; ≥4 combo chạy song song (parallel) nếu có Web Workers.'],
          ['Auto walk-forward on best combo', 'Sau grid, tự WF combo #1 — tóm tắt dưới Top Results'],
          ['Apply best to Strategy', 'Lưu combo #1 vào Strategies — mở Ctrl+3 để xem.'],
          ['Top Results', '20 combo đầu: Params, Trades, WR, Net, Exp, PF. Export JSON.'],
          ['Giữ form khi đổi tab', 'Input grid được nhớ theo strategy trong phiên — reload trang thì mất.'],
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
          ['Session Liquidity Sweep', 'Asian / London End Hour', 'Biên phiên Á và London (UTC)'],
          ['Session Liquidity Sweep', 'Confirm Max Bars', 'Số nến chờ xác nhận sau sweep'],
          ['Session Liquidity Sweep', 'Min Volatility Ratio', 'Lọc thị trường biến động thấp (mặc định 1.1)'],
          ['Session Liquidity Sweep', 'Use Prev Asian / Use Swing Levels', 'Prev Asian: true; Swing: false (grid)'],
          ['Session Liquidity Sweep', 'Session End Hour', 'Giờ UTC cuối — grid gợi ý tick trong Optimizer'],
        ],
      },
      { type: 'h3', text: 'Tab 2 — Sensitivity (biểu đồ theo param grid)' },
      {
        type: 'p',
        text: 'Dùng kết quả Grid Search gần nhất. Chỉ hiện các param đã tick trong lưới đó. Mỗi điểm = trung bình WR, Expectancy, Net Profit của mọi combo có cùng giá trị param (các param khác có thể khác).',
      },
      {
        type: 'table',
        headers: ['Thành phần', 'Cách dùng'],
        rows: [
          ['Parameter', 'Chọn param đã nằm trong grid (vd. rr, breakoutPips).'],
          ['WR / Exp / Net', 'Bật/tắt từng đường — WR % trục trái, $ trục phải.'],
          ['Grid da chay', 'Dòng tóm tắt lưới giá trị từ lần Run (vd. rr: 1.5, 2, 2.5).'],
          ['Ẩn điểm', 'Bucket có trung bình < 5 lệnh/combo bị ẩn — tránh WR ảo.'],
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Net Profit phụ thuộc số lệnh — so sánh kèm cột Trades ở Top Results. Expectancy phù hợp hơn để so chất lượng setup. Dữ liệu là in-sample — đọc kèm Walk Forward.',
      },
      { type: 'h3', text: 'Tab 3 — Walk Forward (kiểm tra theo thời gian)' },
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
      { type: 'h3', text: 'Tab 4 — Monte Carlo (xáo thứ tự lệnh)' },
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
        text: 'Bắt buộc chạy Simulation (Ctrl+5) trước — Monte Carlo không tạo lệnh mới, chỉ xáo lại lệnh đã có. Đổi cài đặt → Simulation lại → Monte Carlo lại.',
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
          'Sensitivity trống — chạy Grid Search trước; cần ≥2 giá trị khác nhau cho một param đã tick.',
          'Mất input grid khi reload trang — form chỉ giữ trong phiên; dùng Restore defaults để reset.',
        ],
      },
    ],
  },
  {
    id: 'glossary',
    title: 'Từ điển thuật ngữ',
    subtitle: 'Tên tiếng Anh trên app + viết tắt — giải thích bằng tiếng đời thường.',
    icon: '📖',
    viewIds: ['docs'],
    blocks: [
      {
        type: 'p',
        text: 'App giữ tên nút/tab tiếng Anh để khớp giao diện. Bảng dưới gom theo nhóm — tìm nhanh bằng Ctrl+F trong trang tài liệu (Ctrl+0).',
      },
      { type: 'h3', text: '1. Viết tắt thường gặp' },
      {
        type: 'table',
        headers: ['Viết tắt', 'Đầy đủ / trên app', 'Hiểu đơn giản'],
        rows: [
          ['WR', 'Win Rate', '% lệnh thắng'],
          ['RR', 'Risk Reward', 'Chốt lời xa gấp mấy lần cắt lỗ'],
          ['R', 'Risk (1R)', 'Một lần cắt lỗ — lãi +2R = thắng gấp đôi rủi ro'],
          ['SL', 'Stop Loss', 'Giá cắt lỗ'],
          ['TP', 'Take Profit', 'Giá chốt lời'],
          ['PF', 'Profit Factor', 'Tổng tiền thắng ÷ tổng tiền thua'],
          ['Exp', 'Expectancy', 'Lãi/lỗ trung bình mỗi lệnh ($)'],
          ['Net', 'Net Profit', 'Tổng lãi/lỗ cả giai đoạn'],
          ['DD', 'Drawdown', 'Mức sụt từ đỉnh tài khoản'],
          ['IS', 'In-sample', 'Đoạn “học” / đã dùng để tối ưu'],
          ['OOS', 'Out-of-sample', 'Đoạn “thử” ngay sau — quan trọng hơn IS'],
          ['WF', 'Walk Forward', 'Kiểm tra IS vs OOS theo thời gian'],
          ['MC', 'Monte Carlo', 'Xáo thứ tự lệnh để xem rủi ro'],
          ['TF', 'Timeframe', 'Khung thời gian nến: H1, H4, D1, W'],
          ['UTC', 'Coordinated Universal Time', 'Giờ chuẩn trên chart/data — không đổi theo mùa địa phương'],
          ['PA', 'Price Action', 'Đọc nến, level, cấu trúc — không chỉ indicator'],
          ['EMA', 'Exponential Moving Average', 'Đường trung bình cân nặng gần hơn'],
          ['B&R', 'Break & Retest', 'Phá level → hồi test → tiếp tục'],
          ['LG', 'Liquidity Grab', 'Quét swing rồi đóng lại — stop hunt'],
          ['SLS', 'Session Liquidity Sweep', 'Quét biên phiên (Asian/London) — entry 2 pha'],
          ['IB', 'Inside Bar', 'Nến nằm gọn trong nến trước (nén)'],
          ['PB', 'Pin Bar', 'Nến râu dài, thân nhỏ — rejection'],
          ['UTAD', 'Upthrust After Distribution', 'Wyckoff: quét đỉnh range rồi rớt lại'],
          ['NY', 'New York session', 'Phiên Mỹ (~13–22 UTC)'],
          ['London (LDN)', 'London session', 'Phiên London (~07–12 UTC) — hay quét biên Asian range'],
          ['OHLCV', 'Open High Low Close Volume', 'Dữ liệu một nến'],
          ['BE', 'Break-even', 'SL về hòa vốn'],
          ['P5/P50/P95', 'Percentile 5/50/95', 'Kịch bản xấu / trung bình / đẹp (Monte Carlo)'],
          ['AI', 'AI Score (rule-based)', 'Điểm 0–100 theo quy tắc — không phải AI dự đoán giá'],
        ],
      },
      { type: 'h3', text: '2. Chỉ số & thống kê (Statistics / Optimizer)' },
      {
        type: 'table',
        headers: ['Thuật ngữ', 'Hiểu đơn giản'],
        rows: [
          ['Backtest / Simulation', 'Mô phỏng lệnh trên quá khứ — không tiền thật'],
          ['Expectancy', 'Trung bình $ mỗi lệnh — metric chính để so setup'],
          ['Profit Factor (PF)', 'Tổng thắng ÷ tổng thua — >1 còn sống, >1.2 thường ổn'],
          ['Net Profit', 'Tổng $ lãi/lỗ — phụ thuộc số lệnh, dễ bị “lừa” nếu ít trade'],
          ['Win Rate (WR)', '% lệnh thắng — WR thấp OK nếu RR cao'],
          ['Max Drawdown', 'Từ đỉnh equity rớt sâu nhất — đo “đau” tâm lý'],
          ['Sharpe Ratio', 'Lãi có ổn so với biến động không — >1 thường ổn'],
          ['Recovery Factor', 'Net profit ÷ max drawdown — phục hồi sau đợt lỗ'],
          ['Equity curve', 'Đường số dư tài khoản theo thời gian'],
          ['Streak', 'Chuỗi thắng/thua liên tiếp'],
          ['Trades', 'Số lệnh — quá ít = kết quả không đáng tin'],
          ['Rank by', 'Tiêu chí xếp hạng combo Grid Search (Exp, Net, PF…)'],
        ],
      },
      { type: 'h3', text: '3. Lệnh, phí & Simulation' },
      {
        type: 'table',
        headers: ['Thuật ngữ', 'Hiểu đơn giản'],
        rows: [
          ['Signal / Tín hiệu', 'Strategy báo setup tại một nến (Entry, SL, TP)'],
          ['Entry', 'Giá vào lệnh (thường = close nến xác nhận)'],
          ['Spread', 'Chênh mua/bán — mỗi lệnh trừ thêm (mặc định 1.5 pip EURUSD)'],
          ['Slippage', 'Trượt giá khi khớp — mô phỏng thêm phí'],
          ['Pip', 'Đơn vị nhỏ nhất cặp FX (EURUSD: 0.0001)'],
          ['Lot size', 'Khối lượng lệnh mô phỏng'],
          ['Long / Short', 'Mua / Bán'],
          ['Break-even (BE)', 'Dời SL về hòa vốn sau khi lãi'],
          ['Trailing stop', 'SL tự kéo theo giá khi lãi'],
          ['Partial close', 'Chốt một phần lệnh tại mức R nhất định'],
          ['AI score filter', 'Simulation chỉ mô phỏng signal có điểm ≥ Min score'],
          ['Compare vs all signals', 'So sánh backtest: toàn bộ vs đã lọc AI'],
        ],
      },
      { type: 'h3', text: '4. Tám chiến lược (Strategies)' },
      {
        type: 'table',
        headers: ['ID / Tên', 'Hiểu đơn giản'],
        rows: [
          ['break-retest — Break & Retest', 'Phá swing → chờ retest level → entry (2 pha)'],
          ['ema-pullback — EMA Pullback', 'Trend EMA20/50 → hồi chạm EMA → entry cùng nến'],
          ['liquidity-grab — Liquidity Grab', 'Quét swing high/low + rejection — entry ngay 1 nến'],
          ['session-liquidity-sweep — Session Liquidity Sweep', 'Quét biên phiên Á/London — chờ nến confirm (2 pha)'],
          ['inside-bar-breakout — Inside Bar Breakout', 'Nến mẹ + inside bar → break theo trend EMA'],
          ['pin-bar-rejection — Pin Bar Rejection', 'Pin bar chạm swing — không cần quét vượt level'],
          ['wyckoff-spring-utad — Wyckoff Spring/UTAD', 'Quét biên range tích lũy → đóng lại trong range'],
          ['wyckoff-range-test — Wyckoff Range Test', 'Sau spring/UTAD → rally → test lần 2 mới entry'],
        ],
      },
      { type: 'h3', text: '5. Price Action & Wyckoff' },
      {
        type: 'table',
        headers: ['Thuật ngữ', 'Hiểu đơn giản'],
        rows: [
          ['Swing high / low', 'Đỉnh/đáy cục bộ trong N nến lookback'],
          ['Breakout', 'Giá đóng cửa vượt level đủ pip'],
          ['Retest', 'Giá quay lại chạm level vừa phá'],
          ['Liquidity / Stop hunt', 'Vùng stop loss tập trung — giá hay quét rồi quay đầu'],
          ['False breakout', 'Phá level nhưng đóng lại phía trong — setup fade'],
          ['Wick / Râu', 'Bóng trên/dưới thân nến — rejection'],
          ['Confirmation candle', 'Nến xác nhận: close mạnh theo hướng trade'],
          ['Doji', 'Nến range quá nhỏ — không coi là xác nhận'],
          ['Asian range', 'Biên đỉnh/đáy phiên Á (thường 00–06 UTC trên H1)'],
          ['London open', 'Mở cửa London (~07 UTC) — hay quét biên Á'],
          ['Overlap', 'London + NY chồng (~13–17 UTC) — biến động cao'],
          ['Trading range', 'Sideway có biên rõ — nền Wyckoff'],
          ['Spring', 'Wyckoff: quét dưới đáy range rồi bật lại trong range'],
          ['UTAD', 'Quét trên đỉnh range rồi rớt lại trong range'],
          ['Higher low / Lower high', 'Đáy cao dần / đỉnh thấp dần — cấu trúc test'],
          ['Overfit (học vẹt)', 'Tối ưu khớp quá khít quá khứ — OOS thường tệ'],
          ['Edge', 'Lợi thế thật sau spread/phí — không phải may mắn ngắn hạn'],
          ['grabPips / grab', 'Số pip vượt level để coi là quét liquidity'],
          ['wickRatio', 'Tỷ lệ râu/thân nến — rejection mạnh hay yếu'],
          ['confirmMaxBars', 'Tối đa bao nhiêu nến chờ xác nhận sau sweep (2 pha)'],
          ['lookback', 'Số nến quét ngược để tìm swing high/low'],
          ['retestTolerancePips', 'Vùng pip chấp nhận khi giá “chạm” level retest'],
          ['breakoutPips', 'Pip đóng cửa vượt level mới coi là breakout'],
          ['minVolatilityRatio', 'Lọc nến quá “chết” — avg range vs median'],
          ['volOk', 'Nến đạt ngưỡng biến động tối thiểu (filter)'],
          ['Pending / 2-phase', 'Pha 1: phát hiện sweep; pha 2: chờ nến confirm mới entry'],
          ['Session filter', 'Chỉ trade trong khung giờ UTC (vd. 06–20)'],
        ],
      },
      { type: 'h3', text: '6. Optimizer (Ctrl+8)' },
      {
        type: 'table',
        headers: ['Thuật ngữ', 'Hiểu đơn giản'],
        rows: [
          ['Grid Search', 'Thử mọi combo tham số đã tick — xếp hạng kết quả'],
          ['Combo', 'Một bộ param (vd. rr=2, grabPips=5)'],
          ['Parallel', 'Grid ≥4 combo chạy song song Web Workers'],
          ['Sensitivity', 'Chart WR / Exp / Net theo từng giá trị param đã grid'],
          ['Suggest from data', 'Gợi ý lưới giá trị từ biến động nến hiện tại'],
          ['Restore defaults', 'Reset lưới param về mặc định ±1 bước'],
          ['Apply best to Strategy', 'Lưu combo #1 vào Strategies (Ctrl+3)'],
          ['Walk Forward', 'Chia timeline IS/OOS nhiều fold — phát hiện overfit'],
          ['Fold', 'Một lượt IS + OOS trong Walk Forward'],
          ['In-sample % / OOS %', 'Tỷ lệ đoạn học vs đoạn thử mỗi fold'],
          ['Monte Carlo', 'Xáo thứ tự lệnh Simulation — phân phối balance'],
          ['Iterations', 'Số lần xáo trong Monte Carlo (mặc định 1000)'],
          ['Ruin Rate', '% lần MC mà tài khoản gần cháy'],
          ['Auto walk-forward on best combo', 'Sau grid tự WF combo #1'],
          ['optimizedParamKeys', 'Danh sách param đã đưa vào grid (dùng cho Sensitivity)'],
        ],
      },
      { type: 'h3', text: '7. AI Signals & Compare' },
      {
        type: 'table',
        headers: ['Thuật ngữ', 'Hiểu đơn giản'],
        rows: [
          ['AI Score', 'Điểm 0–100 sau scan — trend, momentum, RR, session…'],
          ['Min score', 'Ngưỡng lọc danh sách AI Signals (không lọc Simulation mặc định)'],
          ['Grade A/B/C/D/F', 'A≥80, B≥65, C≥50, D≥35 — nhãn điểm, không đảm bảo WIN'],
          ['Factor breakdown', 'Chi tiết điểm từng yếu tố trên signal'],
          ['Compare (Ctrl+4)', 'Xếp hạng nhiều strategy cùng Symbol+TF theo expectancy'],
        ],
      },
      { type: 'h3', text: '8. Data, chart & app' },
      {
        type: 'table',
        headers: ['Thuật ngữ', 'Hiểu đơn giản'],
        rows: [
          ['Symbol / Pair', 'Cặp tiền: EURUSD, GBPUSD, BTCUSD'],
          ['OHLCV', 'Open, High, Low, Close, Volume — dữ liệu nến'],
          ['IndexedDB', 'Nơi lưu nến + kết quả lớn trên trình duyệt'],
          ['LocalStorage', 'Cài đặt UI, param strategy, kích thước panel'],
          ['Warmup bars', 'Số nến đầu strategy bỏ qua (chờ đủ dữ liệu indicator)'],
          ['Replay', 'Chart chạy từng nến — Space play/pause'],
          ['Jump (UTC)', 'Nhảy tới ngày/giờ trên chart — dùng giờ UTC'],
          ['Heatmap', 'Bản đồ màu P/L theo giờ/tháng/session/strategy…'],
          ['PARL', 'Price Action Research Lab — tên app'],
          ['Plugin / Strategy ID', 'Mã chiến lược trong code (vd. break-retest)'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Optimizer (Ctrl+8) có bảng từ ngữ ngắn gắn với 4 tab. Strategies (Ctrl+0) có mô tả chi tiết từng setup kèm sơ đồ. Spec kỹ thuật: docs/STRATEGY_SPECIFICATION.md.',
      },
    ],
  },
  {
    id: 'run-guide',
    title: 'Run Strategies vs Simulation',
    subtitle: 'Khi nào Run ở đâu — có bắt buộc quét Strategies trước không?',
    icon: '▶️',
    viewIds: ['docs'],
    blocks: [
      {
        type: 'callout',
        variant: 'info',
        text: 'Tóm tắt: Run Simulation đủ để có signal + điểm AI + lãi/lỗ. Run Strategies thêm khi bạn muốn xem/lọc signal trên Chart trước, Export JSON, hoặc quét nhiều strategy (Run All).',
      },
      {
        type: 'h3',
        text: 'Strategies (Ctrl+3) — Run Selected / Run All',
      },
      {
        type: 'p',
        text: 'Chỉ bước quét: duyệt từng nến, tìm setup, sinh signal (Entry, SL, TP). Không giả lập khớp lệnh, không trừ spread, không ra bảng win/loss.',
      },
      {
        type: 'ul',
        items: [
          'Tự chấm điểm AI → cập nhật AI Signals.',
          'Lưu Last Scan, Export JSON signal.',
          'Run All Enabled: chạy lần lượt mọi strategy ON — AI Signals chỉ giữ strategy scan cuối.',
        ],
      },
      {
        type: 'h3',
        text: 'Simulation (Ctrl+5) — Run Simulation',
      },
      {
        type: 'p',
        text: 'Hai bước nối tiếp: (1) quét lại strategy với tham số đã Save — giống Strategies; (2) mô phỏng từng lệnh với spread, slippage, lot, trailing, break-even, chốt một phần.',
      },
      {
        type: 'ul',
        items: [
          'Ra bảng lệnh + win rate, net profit, profit factor…',
          'Cập nhật Statistics, Reports, nguồn Monte Carlo.',
          'Chấm lại AI Signals (do có quét lại).',
          'Một strategy mỗi lần Run (chọn trên màn Simulation).',
        ],
      },
      {
        type: 'h3',
        text: 'Bảng so sánh',
      },
      {
        type: 'table',
        headers: ['', 'Strategies Run', 'Simulation Run'],
        rows: [
          ['Quét tín hiệu', 'Có', 'Có (tự động trước khi mô phỏng)'],
          ['Mô phỏng lệnh + spread', 'Không', 'Có'],
          ['Statistics / Reports', 'Không', 'Có'],
          ['AI Signals', 'Có', 'Có'],
          ['Min score lọc lệnh mô phỏng', 'Không', 'Không — mô phỏng toàn bộ signal'],
          ['Bắt buộc chạy trước?', 'Không', 'Không (nếu chỉ cần số liệu lãi/lỗ)'],
        ],
      },
      {
        type: 'h3',
        text: 'Có nhất thiết Run Strategies trước?',
      },
      {
        type: 'p',
        text: 'Không. Bạn có thể: Data → Simulation (Run) → Statistics. Simulation tự quét và chấm điểm.',
      },
      {
        type: 'table',
        headers: ['Bạn muốn', 'Gợi ý'],
        rows: [
          ['Chỉ biết setup có lãi sau spread', 'Simulation đủ — không cần Strategies trước'],
          ['Lọc signal đẹp, xem Chart trước', 'Strategies Run (hoặc Simulation Run rồi AI Signals)'],
          ['Đối chiếu điểm AI vs lệnh', 'Simulation cùng Strategy/Symbol/TF → AI Signals tab Đối chiếu'],
          ['So sánh nhiều strategy', 'Strategies Run All từng cái; Simulation từng strategy riêng'],
        ],
      },
      {
        type: 'h3',
        text: 'Workflow gợi ý',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Lần đầu setup', body: 'Strategies → chỉnh tham số → Save Parameters.' },
          { title: 'Tuỳ chọn', body: 'Strategies Run → AI Signals lọc → Chart kiểm tra mắt.' },
          { title: 'Chạy số', body: 'Simulation Run (cùng Symbol/TF).' },
          { title: 'Đánh giá', body: 'Statistics / Reports + AI Signals tab Đối chiếu.' },
        ],
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'Mỗi lần Run Simulation đều quét lại — hơi trùng với Strategies nhưng đảm bảo khớp tham số hiện tại. Min score chỉ ẩn signal trên AI Signals, không giảm số lệnh trong Simulation.',
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
          ['Ctrl+4', 'Compare'],
          ['Ctrl+5', 'Simulation'],
          ['Ctrl+6', 'Statistics'],
          ['Ctrl+7', 'Reports'],
          ['Ctrl+8', 'Optimizer'],
          ['Ctrl+9', 'AI Signals'],
          ['Ctrl+0 / F1', 'Tài liệu đầy đủ'],
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
      { type: 'p', text: 'Chạy Simulation (Ctrl+5) trước. Hai mục này đọc kết quả simulation gần nhất.' },
      { type: 'h3', text: 'Monte Carlo báo không có lệnh?' },
      { type: 'p', text: 'Monte Carlo chỉ xáo lại lệnh từ Simulation — không tạo lệnh mới. Chạy Simulation (Ctrl+5) trước.' },
      { type: 'h3', text: 'Grid search quá chậm / quá nhiều combo?' },
      { type: 'p', text: `Giảm số combo (tối đa ${Config.OPTIMIZER.MAX_COMBINATIONS}): bỏ tick bớt tham số hoặc rút dải giá trị. Từ ≥4 combo, grid chạy song song trên Web Workers (4 luồng) nếu trình duyệt hỗ trợ.` },
      { type: 'h3', text: 'Tab Sensitivity trống?' },
      { type: 'p', text: 'Chạy Grid Search trước. Chart chỉ hiện param đã tick trong lưới đó và cần ≥2 giá trị khác nhau cho ít nhất một param.' },
      { type: 'h3', text: 'Mất input Grid Search khi đổi tab?' },
      { type: 'p', text: 'Bản hiện tại giữ form theo từng strategy trong phiên. Reload trang sẽ mất — dùng Restore defaults để về lưới mặc định.' },
      { type: 'h3', text: 'Walk Forward tệ dù Grid Search đẹp?' },
      { type: 'p', text: 'Dấu hiệu “học vẹt” quá khứ (overfit) — thử ít tham số hơn, chọn combo có nhiều lệnh, hoặc kiểm tra giai đoạn/cặp khác.' },
      { type: 'h3', text: 'AI score cao mà lệnh vẫn LOSS?' },
      { type: 'p', text: 'Bình thường. Điểm AI đánh giá setup lúc vào lệnh (trend, nến, RR, phiên…), không dự đoán giá sau đó. Muốn backtest chỉ signal điểm cao → bật AI score filter ở Simulation (Ctrl+5).' },
      { type: 'h3', text: 'Có bắt buộc Run Strategies trước Simulation?' },
      { type: 'p', text: 'Không. Simulation tự quét lại strategy rồi mô phỏng lệnh. Chỉ cần Strategies trước khi bạn muốn lọc signal / Chart trước, Export JSON, hoặc Run All nhiều strategy. Xem Ctrl+0 → Run Strategies vs Simulation.' },
      { type: 'h3', text: 'Run Strategies và Run Simulation khác gì?' },
      { type: 'p', text: 'Strategies chỉ sinh signal + chấm điểm AI. Simulation quét lại + giả lập lệnh (spread, trailing…) → Statistics/Reports. Chi tiết: Ctrl+0 → Run Strategies vs Simulation.' },
      { type: 'h3', text: 'Reset app làm gì?' },
      { type: 'p', text: 'Data Manager → Reset app: xóa IndexedDB (nến + kết quả lớn), mọi key parl_* (settings, tham số strategy), rồi tải lại trang. Giống cài mới — boot sẽ tự seed EURUSD H1 nếu trống. Không hoàn tác — export trước nếu cần.' },
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
