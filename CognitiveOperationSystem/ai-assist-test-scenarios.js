/**
 * Kịch bản test — ChatGPT gián tiếp (reflection import)
 *
 * Mỗi kịch bản mô phỏng:
 * 1. User suy ngẫm với ChatGPT (userDialogue)
 * 2. ChatGPT xuất JSON (chatgptExport) — phải bám sát lời user
 * 3. App import → kiểm tra node / bằng chứng / không suy diễn thêm
 *
 * @typedef {Object} AiAssistTestScenario
 * @property {string} id
 * @property {string} title
 * @property {string} category
 * @property {string[]} tags
 * @property {string} summary
 * @property {'vi'|'en'} locale
 * @property {string} initialThought
 * @property {Array<{step: string, content: string, note?: string}>} userDialogue
 * @property {Object} chatgptExport — JSON mô phỏng ChatGPT trả về
 * @property {Array<{type: string, labelContains?: string, quoteContains?: string}>} expectPresent
 * @property {string[]} expectAbsent — nhãn KHÔNG được xuất hiện sau import
 * @property {Object} [expectPrompt]
 * @property {string[]} [expectPrompt.reflectionContains]
 * @property {string[]} [expectPrompt.exportContains]
 */

const AI_ASSIST_TEST_SCENARIOS = [
  {
    id: 'time-management-no-false-beliefs',
    title: 'Thiếu thời gian — không suy diễn sức khỏe',
    category: 'work',
    tags: ['thời gian', 'công việc', 'regression'],
    summary:
      'Regression: user không nói về hy sinh sức khỏe — app không được thêm niềm tin từ rule engine.',
    locale: 'vi',
    initialThought: 'Tôi không có thời gian rảnh.',
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
    chatgptExport: {
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
          label: 'Học thêm kỹ năng, bớt việc không cần',
          quote: 'học thêm kỹ năng và giảm bớt những công việc không cần thiết',
        },
      ],
      summary:
        'Bạn cảm thấy mệt vì thiếu thời gian rảnh, cho rằng mình quản lý thời gian chưa tốt, và muốn cân bằng công việc với phát triển bản thân.',
      reframe: 'Thiếu thời gian có thể là tín hiệu cần ưu tiên lại, không hẳn là thất bại cá nhân.',
      smallStep: 'Liệt kê 3 việc có thể giảm hoặc ủy quyền trong tuần này.',
    },
    expectPresent: [
      { type: 'Event', quoteContains: 'không có thời gian' },
      { type: 'Emotion', quoteContains: 'mệt' },
      { type: 'Belief', quoteContains: 'kỹ năng' },
      { type: 'Value', quoteContains: 'cân bằng' },
      { type: 'Identity', quoteContains: 'cầu toàn' },
      { type: 'Action', quoteContains: 'học thêm' },
    ],
    expectAbsent: [
      'Sức khỏe có thể hy sinh vì công việc',
      'Tôi không có thời gian cho bản thân',
      'Người có kỹ năng sẽ làm việc hiệu quả',
    ],
    expectPrompt: {
      reflectionContains: ['EEIBVIA', 'Tôi không có thời gian rảnh', 'tiếng Việt'],
      exportContains: ['JSON', 'tiếng Việt'],
    },
  },

  {
    id: 'parent-education-chatgpt',
    title: 'Cha lo con không học — import ChatGPT',
    category: 'family',
    tags: ['gia đình', 'giáo dục', 'ChatGPT'],
    summary: 'Hội thoại đầy đủ EEIBVIA — JSON ChatGPT phải khớp lời user, không thêm niềm tin lạ.',
    locale: 'vi',
    initialThought:
      'Con tôi không chịu học, tôi lo lắng về tương lai của con. Mỗi tối tôi làm việc 14 giờ rồi về nhà thấy con còn chơi game thì rất tức.',
    userDialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy lo lắng, căng thẳng và tức giận. Cũng có chút tội lỗi vì đã quát con to tiếng.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi lo con sẽ thất bại trong cuộc sống, không vào được trường tốt, sau này không có việc làm.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin rằng học giỏi mới thành công. Con cái phải nghe lời cha mẹ. Làm việc chăm chỉ sẽ thành công.',
      },
      {
        step: 'Value',
        content:
          'Gia đình là ưu tiên số một với tôi. Giáo dục con đúng cách rất quan trọng.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người cha, có trách nhiệm bảo vệ và hướng dẫn con. Tôi thấy mình là người hy sinh vì gia đình.',
      },
      {
        step: 'Action',
        content:
          'Tôi thường la mắng con, bắt con học mỗi tối. Tôi làm việc 14 giờ mỗi ngày. Tôi chưa dành thời gian ngồi cạnh con học.',
      },
    ],
    chatgptExport: {
      initialThought:
        'Con tôi không chịu học, tôi lo lắng về tương lai của con. Mỗi tối tôi làm việc 14 giờ rồi về nhà thấy con còn chơi game thì rất tức.',
      event: {
        label: 'Con không chịu học, cha làm việc nhiều',
        detail:
          'Con tôi không chịu học, tôi lo lắng về tương lai của con. Mỗi tối tôi làm việc 14 giờ rồi về nhà thấy con còn chơi game thì rất tức.',
      },
      emotions: [
        {
          label: 'Lo lắng và tức giận',
          quote:
            'Tôi cảm thấy lo lắng, căng thẳng và tức giận. Cũng có chút tội lỗi vì đã quát con to tiếng.',
        },
      ],
      interpretation: {
        label: 'Lo con thất bại tương lai',
        detail:
          'Tôi lo con sẽ thất bại trong cuộc sống, không vào được trường tốt, sau này không có việc làm.',
      },
      beliefs: [
        { label: 'Học giỏi mới thành công', quote: 'học giỏi mới thành công' },
        { label: 'Con phải nghe lời cha mẹ', quote: 'Con cái phải nghe lời cha mẹ' },
        { label: 'Làm việc chăm chỉ sẽ thành công', quote: 'Làm việc chăm chỉ sẽ thành công' },
      ],
      values: [
        { label: 'Gia đình ưu tiên', quote: 'Gia đình là ưu tiên số một với tôi' },
        { label: 'Giáo dục con', quote: 'Giáo dục con đúng cách rất quan trọng' },
      ],
      identity: [
        {
          label: 'Người cha hy sinh',
          quote:
            'Tôi là người cha, có trách nhiệm bảo vệ và hướng dẫn con. Tôi thấy mình là người hy sinh vì gia đình.',
        },
      ],
      actions: [
        { label: 'La mắng và bắt con học', quote: 'Tôi thường la mắng con, bắt con học mỗi tối' },
        { label: 'Làm việc 14 giờ', quote: 'Tôi làm việc 14 giờ mỗi ngày' },
      ],
      summary:
        'Bạn lo cho tương lai con, tin vào học hành và kỷ luật, đồng thời đang làm việc rất nhiều giờ.',
      reframe: 'Lo lắng cho con có thể là tình yêu thương — cách thể hiện mới là chỗ cần nhìn lại.',
      smallStep: 'Thử một buổi tối ngồi cạnh con 15 phút trước khi nhắc bài.',
    },
    expectPresent: [
      { type: 'Belief', quoteContains: 'học giỏi' },
      { type: 'Value', quoteContains: 'Gia đình' },
      { type: 'Action', quoteContains: '14 giờ' },
    ],
    expectAbsent: ['Sức khỏe có thể hy sinh vì công việc', 'Giàu mới được hạnh phúc'],
    expectPrompt: {
      reflectionContains: ['người dẫn suy ngẫm', 'EEIBVIA', 'tiếng Việt'],
      exportContains: ['JSON', 'tiếng Việt'],
    },
  },

  {
    id: 'work-burnout-en',
    title: 'Work burnout — English locale',
    category: 'health',
    tags: ['english', 'work', 'locale'],
    summary: 'Prompts and import in English; no cross-locale pollution.',
    locale: 'en',
    initialThought: 'I feel burned out from work and cannot rest properly.',
    userDialogue: [
      { step: 'Emotion', content: 'exhausted and anxious' },
      { step: 'Interpretation', content: 'I think I am failing at work-life balance' },
      { step: 'Belief', content: 'I must always be productive to be valuable' },
      { step: 'Value', content: 'health and family time matter to me' },
      { step: 'Identity', content: 'I see myself as a responsible provider' },
      { step: 'Action', content: 'I keep checking email at night instead of resting' },
    ],
    chatgptExport: {
      initialThought: 'I feel burned out from work and cannot rest properly.',
      event: {
        label: 'Burnout from work',
        detail: 'I feel burned out from work and cannot rest properly.',
      },
      emotions: [{ label: 'Exhausted', quote: 'exhausted and anxious' }],
      interpretation: {
        label: 'Failing at balance',
        detail: 'I think I am failing at work-life balance',
      },
      beliefs: [
        {
          label: 'Must be productive to be valuable',
          quote: 'I must always be productive to be valuable',
        },
      ],
      values: [{ label: 'Health and family', quote: 'health and family time matter to me' }],
      identity: [
        { label: 'Responsible provider', quote: 'I see myself as a responsible provider' },
      ],
      actions: [
        {
          label: 'Checking email at night',
          quote: 'I keep checking email at night instead of resting',
        },
      ],
      summary: 'You feel burned out, tie worth to productivity, and value health while working late.',
      reframe: 'Rest can be part of responsibility, not the opposite of it.',
      smallStep: 'Try one evening without work email for 30 minutes.',
    },
    expectPresent: [
      { type: 'Belief', quoteContains: 'productive' },
      { type: 'Value', quoteContains: 'health' },
    ],
    expectAbsent: ['Sức khỏe có thể hy sinh vì công việc'],
    expectPrompt: {
      reflectionContains: ['Reply in English', 'burned out'],
      exportContains: ['English', 'JSON'],
    },
  },

  {
    id: 'sparse-minimal-export',
    title: 'JSON thưa — chỉ Event + Emotion',
    category: 'self',
    tags: ['sparse', 'minimal'],
    summary: 'ChatGPT chỉ trả một phần EEIBVIA — app không bịa thêm bước từ rule engine.',
    locale: 'vi',
    initialThought: 'Hôm nay tôi cảm thấy trống rỗng, không biết mình muốn gì.',
    userDialogue: [
      { step: 'Emotion', content: 'trống rỗng, buồn nhẹ' },
    ],
    chatgptExport: {
      initialThought: 'Hôm nay tôi cảm thấy trống rỗng, không biết mình muốn gì.',
      event: {
        label: 'Cảm giác trống rỗng',
        detail: 'Hôm nay tôi cảm thấy trống rỗng, không biết mình muốn gì.',
      },
      emotions: [{ label: 'Trống rỗng', quote: 'trống rỗng, buồn nhẹ' }],
      interpretation: null,
      beliefs: [],
      values: [],
      identity: [],
      actions: [],
      summary: 'Bạn mô tả cảm giác trống rỗng và buồn nhẹ, chưa rõ thêm bước sau.',
      reframe: null,
      smallStep: null,
    },
    expectPresent: [
      { type: 'Event', quoteContains: 'trống rỗng' },
      { type: 'Emotion', quoteContains: 'trống rỗng' },
    ],
    expectAbsent: [
      'Sức khỏe có thể hy sinh vì công việc',
      'Tôi không xứng đáng',
      'Cuộc sống phải công bằng',
    ],
    expectPrompt: {
      reflectionContains: ['trống rỗng'],
      exportContains: ['JSON'],
    },
  },

  {
    id: 'finance-saving-conflict',
    title: 'Tiết kiệm vs chi tiêu — không thêm niềm tin tiền',
    category: 'finance',
    tags: ['tài chính', 'gia đình'],
    summary: 'Có từ "tiền" và "gia đình" nhưng không suy ra niềm tin "giàu mới hạnh phúc".',
    locale: 'vi',
    initialThought: 'Vợ tôi muốn tiết kiệm nhưng tôi muốn chi cho con học thêm.',
    userDialogue: [
      { step: 'Emotion', content: 'căng thẳng và tội lỗi' },
      {
        step: 'Interpretation',
        content: 'tôi sợ tranh cãi tiền bạc làm hỏng không khí gia đình',
      },
      {
        step: 'Belief',
        content: 'đầu tư cho con học là đúng dù tốn kém',
      },
      { step: 'Value', content: 'tương lai con và hòa khí gia đình' },
      { step: 'Identity', content: 'tôi là người cha lo cho con' },
      { step: 'Action', content: 'tôi giấu vợ khoản chi học thêm' },
    ],
    chatgptExport: {
      initialThought: 'Vợ tôi muốn tiết kiệm nhưng tôi muốn chi cho con học thêm.',
      event: {
        label: 'Bất đồng tiết kiệm vs chi cho con',
        detail: 'Vợ tôi muốn tiết kiệm nhưng tôi muốn chi cho con học thêm.',
      },
      emotions: [{ label: 'Căng thẳng', quote: 'căng thẳng và tội lỗi' }],
      interpretation: {
        label: 'Sợ tranh cãi tiền',
        detail: 'tôi sợ tranh cãi tiền bạc làm hỏng không khí gia đình',
      },
      beliefs: [
        {
          label: 'Đầu tư học cho con là đúng',
          quote: 'đầu tư cho con học là đúng dù tốn kém',
        },
      ],
      values: [
        { label: 'Tương lai con', quote: 'tương lai con và hòa khí gia đình' },
      ],
      identity: [{ label: 'Người cha lo cho con', quote: 'tôi là người cha lo cho con' }],
      actions: [
        { label: 'Giấu vợ khoản chi', quote: 'tôi giấu vợ khoản chi học thêm' },
      ],
      summary: 'Bạn đang giữa mong muốn đầu tư cho con và sợ xung đột tài chính trong gia đình.',
      reframe: 'Hai giá trị có thể cùng tồn tại — cách nói chuyện mới là điểm cần nhìn.',
      smallStep: 'Chia sẻ với vợ một khoản chi cụ thể cho con, không cần quyết ngay.',
    },
    expectPresent: [
      { type: 'Belief', quoteContains: 'đầu tư' },
      { type: 'Action', quoteContains: 'giấu vợ' },
    ],
    expectAbsent: ['Giàu mới được hạnh phúc', 'Tiền mang lại hạnh phúc'],
      expectPrompt: {
      reflectionContains: ['tiết kiệm', 'EEIBVIA'],
      exportContains: ['JSON'],
    },
  },

  {
    id: 'chatgpt-hallucination-quarantine',
    title: 'ChatGPT bịa niềm tin — cách ly suy diễn',
    category: 'work',
    tags: ['hallucination', 'anchoring', 'regression'],
    summary:
      'JSON có niềm tin user không hề nói → preview cảnh báo, node lưu inferred, không vào Khám phá.',
    locale: 'vi',
    initialThought: 'Tôi không có thời gian rảnh.',
    userDialogue: [
      { step: 'Emotion', content: 'mệt' },
      { step: 'Interpretation', content: 'tôi quản lý thời gian chưa tốt' },
    ],
    chatgptExport: {
      initialThought: 'Tôi không có thời gian rảnh.',
      event: { label: 'Không có thời gian rảnh', detail: 'Tôi không có thời gian rảnh.' },
      emotions: [{ label: 'Mệt', quote: 'mệt' }],
      interpretation: {
        label: 'Quản lý thời gian chưa tốt',
        detail: 'tôi quản lý thời gian chưa tốt',
      },
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
      reframe: null,
      smallStep: null,
    },
    expectPresent: [
      { type: 'Event', quoteContains: 'thời gian' },
      { type: 'Emotion', quoteContains: 'mệt' },
    ],
    expectAbsent: [],
    expectUnanchored: ['Sức khỏe có thể hy sinh vì công việc'],
    expectNotInInsights: ['Sức khỏe có thể hy sinh vì công việc'],
    expectPrompt: {
      reflectionContains: ['thời gian rảnh'],
      exportContains: ['JSON'],
    },
  },
];

if (typeof window !== 'undefined') {
  window.AI_ASSIST_TEST_SCENARIOS = AI_ASSIST_TEST_SCENARIOS;
}
