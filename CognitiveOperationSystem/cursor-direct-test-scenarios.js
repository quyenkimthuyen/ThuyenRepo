/**
 * Kịch bản test — Cursor trực tiếp (mock bridge + live)
 *
 * Mock: mô phỏng phản hồi bridge → export JSON → import (pipeline finish)
 * Live: gọi bridge thật (--live trong CLI)
 */

const CURSOR_DIRECT_TEST_SCENARIOS = [
  {
    id: 'cursor-mock-time-no-false-beliefs',
    title: 'Mock — thiếu thời gian, không niềm tin sức khỏe',
    category: 'work',
    tags: ['mock', 'cursor', 'regression'],
    summary: 'Mô phỏng phiên Cursor → export → import; không được thêm niềm tin hy sinh sức khỏe.',
    locale: 'vi',
    initialThought: 'Tôi không có thời gian rảnh.',
    openingReply: 'Tôi nghe bạn nói về việc không có thời gian rảnh. Cảm xúc nào nổi bật nhất?',
    userDialogue: [
      { step: 'Emotion', content: 'mệt' },
      { step: 'Interpretation', content: 'tôi quản lý thời gian chưa tốt' },
      {
        step: 'Belief',
        content:
          'người có kỹ năng sẽ có khả năng giải quyết vấn đề nhanh chóng và biết sắp xếp thời gian hợp lý',
      },
      {
        step: 'Value',
        content: 'cân bằng công việc gia đình và phát triển bản thân',
      },
      { step: 'Identity', content: 'tôi là người cầu toàn' },
      {
        step: 'Action',
        content: 'học thêm kỹ năng và giảm bớt những công việc không cần thiết',
      },
    ],
    cursorExport: {
      initialThought: 'Tôi không có thời gian rảnh.',
      event: {
        label: 'Không có thời gian rảnh',
        detail: 'Tôi không có thời gian rảnh.',
      },
      emotions: [{ label: 'Mệt mỏi', quote: 'mệt' }],
      interpretation: {
        label: 'Quản lý thời gian chưa tốt',
        detail: 'tôi quản lý thời gian chưa tốt',
      },
      beliefs: [
        {
          label: 'Kỹ năng giúp giải quyết vấn đề nhanh',
          quote:
            'người có kỹ năng sẽ có khả năng giải quyết vấn đề nhanh chóng và biết sắp xếp thời gian hợp lý',
        },
      ],
      values: [
        {
          label: 'Cân bằng công việc và phát triển bản thân',
          quote: 'cân bằng công việc gia đình và phát triển bản thân',
        },
      ],
      identity: [{ label: 'Người cầu toàn', quote: 'tôi là người cầu toàn' }],
      actions: [
        {
          label: 'Học kỹ năng, bớt việc không cần',
          quote: 'học thêm kỹ năng và giảm bớt những công việc không cần thiết',
        },
      ],
      summary: 'User thiếu thời gian, mệt, muốn cải thiện quản lý thời gian.',
      reframe: 'Thiếu thời gian có thể là tín hiệu cần ưu tiên lại, không hẳn là thất bại.',
      smallStep: 'Liệt kê một việc có thể hoãn tuần này.',
    },
    expectPresent: [
      { type: 'Emotion', quoteContains: 'mệt' },
      { type: 'Belief', quoteContains: 'kỹ năng' },
    ],
    expectAbsent: ['Sức khỏe có thể hy sinh', 'hy sinh sức khỏe'],
    expectPrompt: {
      reflectionContains: ['EEIBVIA', 'Event'],
      exportContains: ['JSON'],
    },
  },
  {
    id: 'cursor-mock-hallucination-quarantine',
    title: 'Mock — quote bịa → inferred, không insight',
    category: 'regression',
    tags: ['mock', 'cursor', 'hallucination'],
    summary: 'Export có niềm tin user không nói → quarantine inferred.',
    locale: 'vi',
    initialThought: 'Tôi không có thời gian rảnh.',
    openingReply: 'Cảm ơn bạn đã chia sẻ. Bạn cảm thấy thế nào?',
    userDialogue: [{ step: 'Emotion', content: 'mệt' }],
    cursorExport: {
      initialThought: 'Tôi không có thời gian rảnh.',
      event: { label: 'Thiếu thời gian', detail: 'Tôi không có thời gian rảnh.' },
      emotions: [{ label: 'Mệt', quote: 'mệt' }],
      interpretation: { label: 'Quản lý thời gian', detail: 'tôi quản lý thời gian chưa tốt' },
      beliefs: [
        {
          label: 'Sức khỏe có thể hy sinh vì công việc',
          quote: 'Sức khỏe có thể hy sinh vì công việc',
        },
      ],
      values: [],
      identity: [],
      actions: [],
      summary: '...',
      reframe: '...',
      smallStep: '...',
    },
    expectUnanchored: ['Sức khỏe có thể hy sinh'],
    expectNotInInsights: ['Sức khỏe có thể hy sinh'],
    expectAbsent: [],
    expectPresent: [{ type: 'Emotion', quoteContains: 'mệt' }],
  },
  {
    id: 'cursor-mock-sparse-minimal',
    title: 'Mock — JSON thưa (Event + Emotion)',
    category: 'minimal',
    tags: ['mock', 'cursor'],
    summary: 'Phiên ngắn, export tối thiểu vẫn import được.',
    locale: 'vi',
    initialThought: 'Hôm nay trời đẹp.',
    openingReply: 'Trời đẹp — điều gì đang chạm vào bạn?',
    userDialogue: [{ step: 'Emotion', content: 'vui và nhẹ nhõm' }],
    cursorExport: {
      initialThought: 'Hôm nay trời đẹp.',
      event: { label: 'Trời đẹp', detail: 'Hôm nay trời đẹp.' },
      emotions: [{ label: 'Vui', quote: 'vui và nhẹ nhõm' }],
      interpretation: null,
      beliefs: [],
      values: [],
      identity: [],
      actions: [],
      summary: 'Một ngày trời đẹp, cảm giác vui.',
      reframe: null,
      smallStep: null,
    },
    expectPresent: [
      { type: 'Event', labelContains: 'trời' },
      { type: 'Emotion', quoteContains: 'vui' },
    ],
    expectAbsent: [],
  },
  {
    id: 'cursor-mock-live-sync-insights',
    title: 'Mock — đồng bộ Khám phá/Timeline khi chat Cursor',
    category: 'integration',
    tags: ['mock', 'cursor', 'insights', 'timeline', 'live-sync'],
    summary:
      'Mô phỏng syncSessionData từng lượt user (như app) — node, timeline, insights cập nhật trước khi finish.',
    locale: 'vi',
    testLiveSync: true,
    initialThought: 'Tôi căng thẳng vì deadline tuần này.',
    openingReply: 'Nghe bạn nói về deadline — cảm xúc nào nổi bật nhất?',
    userDialogue: [
      { step: 'Emotion', content: 'lo lắng và mệt vì áp lực công việc' },
      { step: 'Interpretation', content: 'tôi lo sẽ không kịp hoàn thành đúng hạn' },
    ],
    expectDuringChat: {
      sessionNodeMin: 2,
      nodesPresent: [
        { type: 'Event', quoteContains: 'deadline' },
        { type: 'Emotion', quoteContains: 'lo lắng' },
      ],
      timelineSessionStart: true,
      timelineMinCount: 1,
      insightsUpdated: true,
      todayDiscoveriesMin: 1,
      topEmotionsContains: 'lo',
    },
    expectAfterFinish: {
      noOrphanSessionNodes: true,
    },
    cursorExport: {
      initialThought: 'Tôi căng thẳng vì deadline tuần này.',
      event: {
        label: 'Áp lực deadline tuần này',
        detail: 'Tôi căng thẳng vì deadline tuần này.',
      },
      emotions: [{ label: 'Lo lắng', quote: 'lo lắng và mệt vì áp lực công việc' }],
      interpretation: {
        label: 'Lo không kịp hạn',
        detail: 'tôi lo sẽ không kịp hoàn thành đúng hạn',
      },
      beliefs: [],
      values: [],
      identity: [],
      actions: [],
      summary: 'Căng thẳng deadline, lo lắng và mệt.',
      reframe: 'Deadline là áp lực thời gian, không nhất thiết đánh giá năng lực.',
      smallStep: 'Chọn một việc ưu tiên nhất trong tuần.',
    },
    expectPresent: [
      { type: 'Event', quoteContains: 'deadline' },
      { type: 'Emotion', quoteContains: 'lo lắng' },
    ],
    expectAbsent: [],
  },
  {
    id: 'cursor-live-minimal-vi',
    title: 'Live — một lượt qua bridge thật',
    category: 'live',
    tags: ['live', 'cursor', 'integration'],
    summary: 'Gọi Cursor bridge + API key; kiểm tra reply và export JSON hợp lệ.',
    locale: 'vi',
    liveOnly: true,
    initialThought: 'Hôm nay tôi cảm thấy căng thẳng vì deadline tuần này.',
    userDialogue: [{ step: 'Emotion', content: 'lo lắng và hơi choáng ngợp' }],
    liveMaxTurns: 1,
    expectExportFields: ['initialThought', 'event', 'emotions'],
  },
];

if (typeof window !== 'undefined') {
  window.CURSOR_DIRECT_TEST_SCENARIOS = CURSOR_DIRECT_TEST_SCENARIOS;
}
