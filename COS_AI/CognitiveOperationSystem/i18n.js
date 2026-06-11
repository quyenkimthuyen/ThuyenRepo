/**
 * i18n — Song ngữ Tiếng Việt / English
 */

const I18N_MESSAGES = {
  vi: {
    appName: 'Nhìn lại suy nghĩ',
    metaDescription: 'Hệ thống nhìn lại suy nghĩ — ghi nhận và hiểu rõ hơn về bản thân',
    nav: {
      main: 'Điều hướng chính',
      home: 'Trang chủ',
      reflection: 'Suy ngẫm',
      forest: 'Bản đồ',
      insights: 'Khám phá',
      timeline: 'Dòng thời gian',
      test: 'Thử nghiệm',
    },
    home: {
      aria: 'Trang chủ',
      badge: '7 bước nhìn lại suy nghĩ',
      title: 'Hôm nay bạn đang suy nghĩ điều gì?',
      subtitle:
        'Chia sẻ suy nghĩ — hệ thống sẽ ghi nhận và sắp xếp theo 7 bước: việc xảy ra, cảm xúc, cách hiểu, niềm tin, giá trị, vai trò bản thân và hành động.',
      placeholder: 'Ví dụ: Con tôi không chịu học, tôi lo lắng về tương lai của con...',
      inputAria: 'Suy nghĩ của bạn',
      startBtn: 'Bắt đầu suy ngẫm',
      statEntries: 'Ghi nhận',
      statVerified: 'Đã vững chắc',
      statSessions: 'Phiên suy ngẫm',
      resetText: 'Muốn bắt đầu lại từ đầu? Toàn bộ ghi nhận, phiên suy ngẫm và dòng thời gian sẽ bị xóa.',
      resetBtn: 'Xóa dữ liệu và bắt đầu lại',
      shareFirst: 'Hãy chia sẻ suy nghĩ của bạn trước.',
      sessionStarted: 'Đã bắt đầu phiên suy ngẫm',
      dataReset: 'Đã xóa dữ liệu. Bạn có thể bắt đầu lại từ đầu.',
      disclaimer:
        'Đây là công cụ tự suy ngẫm — không thay tư vấn tâm lý hay điều trị y khoa. Nếu bạn đang gặp khủng hoảng, hãy tìm người hỗ trợ chuyên môn.',
      privacy: 'Dữ liệu chỉ lưu trên thiết bị của bạn — không ai khác đọc được.',
    },
    ai: {
      title: 'Chế độ phản hồi',
      desc: 'Mặc định dùng rule engine (offline). Bật Cursor AI để người dẫn suy ngẫm trả lời tự nhiên hơn — cần chạy proxy local.',
      modeAria: 'Chế độ phản hồi',
      modeRule: 'Rule engine (offline)',
      modeCursor: 'Cursor AI',
      proxyLabel: 'Proxy URL',
      testBtn: 'Kiểm tra kết nối',
      helpTitle: 'Cách chạy proxy Cursor',
      help1: 'Tạo API key tại Cursor Dashboard → Integrations',
      help2: 'Trong terminal: cd server && npm install && export CURSOR_API_KEY="..." && npm start',
      help3: 'Chọn Cursor AI, bấm Kiểm tra kết nối, rồi bắt đầu suy ngẫm',
      statusUnknown: 'Chưa kiểm tra',
      statusOk: 'Proxy sẵn sàng',
      statusNoKey: 'Thiếu CURSOR_API_KEY trên server',
      statusError: 'Không kết nối được',
      statusChecking: 'Đang kiểm tra...',
      testOk: 'Kết nối Cursor proxy thành công',
      testFail: 'Không kết nối được proxy',
      badgeRule: 'Rule engine',
      badgeCursor: 'Cursor AI',
      thinking: 'Đang suy ngẫm cùng bạn...',
      fallbackRule: 'AI tạm thời không phản hồi — đã dùng rule engine',
    },
    safety: {
      title: 'Bạn không cần đối mặt một mình',
      body: 'Chúng tôi nhận thấy nội dung bạn chia sẻ có thể rất nặng nề. Nếu bạn đang có ý nghĩ làm hại bản thân, hãy liên hệ ngay:',
      hotline1: 'Đường dây nóng quốc gia',
      hotline1Tel: '111',
      hotline2: 'Tổng đài tâm lý',
      hotline2Tel: '18001929',
      footer: 'Ứng dụng này không thay thế chuyên gia. Bạn xứng đáng được lắng nghe và được giúp đỡ.',
      understood: 'Tôi đã hiểu',
    },
    reflection: {
      aria: 'Phiên suy ngẫm',
      title: 'Phiên suy ngẫm',
      progressAria: 'Tiến trình hội thoại',
      progress: 'Tiến trình',
      suggestions: 'Gợi ý trả lời',
      suggestionsAria: 'Mẫu trả lời gợi ý',
      suggestionTitle: 'Chọn câu trả lời này',
      chatPlaceholder: 'Chia sẻ suy nghĩ của bạn...',
      chatAria: 'Tin nhắn',
      send: 'Gửi',
      sendAria: 'Gửi',
      empty: 'Chưa có phiên suy ngẫm nào.',
      emptyHint: 'Hãy bắt đầu từ Trang chủ.',
      you: 'Bạn',
      guide: 'Người dẫn suy ngẫm',
      shareMore: 'Bạn muốn chia sẻ thêm điều gì?',
      openingDefault: 'Nghe có vẻ điều đó đang chạm vào bạn. Bạn cảm thấy thế nào?',
      openingWithThought:
        'Tôi nghe thấy bạn đang nói về "{thought}". Nghe có vẻ điều đó đang chạm vào bạn — bạn cảm thấy thế nào?',
      emotionWithEvent: 'Khi nghĩ về "{event}", cảm xúc nào nổi bật nhất với bạn?',
      interpretationWithEmotion: 'Khi cảm thấy {emotion}, bạn lo điều gì có thể xảy ra?',
      beliefPrompt: 'Điều gì khiến bạn tin như vậy — bạn có thể kể thêm không?',
      sessionEnd:
        'Cảm ơn bạn đã chia sẻ. Tôi đã ghi nhận vào bản đồ suy nghĩ. Khi sẵn sàng, bạn có thể xem thêm ở Góc khám phá.',
      sessionEndMarker: 'Góc khám phá',
      emotionSuggestion: 'Khi nghĩ về việc đó, tôi cảm thấy lo lắng và căng thẳng',
      fallbackReflection: 'Suy ngẫm',
      skipStep: 'Bỏ qua bước này',
      skippedStep: '(Đã bỏ qua bước này)',
      skipNote: 'Không sao — bạn có thể quay lại chủ đề này khi muốn.',
      shortSuggestions: 'Chọn nhanh',
      summaryTitle: 'Tóm tắt',
      summaryTemplate:
        'Bạn đang nghĩ về: {event}. Cảm xúc nổi bật: {emotion}. Cách hiểu: {interpretation}. Niềm tin: {belief}. Điều quan trọng: {value}.',
      reframeQuestion: 'Nếu nhìn nhẹ hơn một chút, bạn có thể hiểu tình huống này theo cách nào khác?',
      smallStepQuestion: 'Một bước nhỏ, trong khả năng của bạn hôm nay, bạn có thể thử làm gì?',
      contextQuestion: 'Phần nào trong tình huống này đến từ hoàn cảnh, áp lực bên ngoài — không chỉ do bạn?',
      powerQuestion: 'Trong tình huống này, ai có thể thay đổi điều gì — kể cả chính bạn?',
      expandEmotion: 'Ngoài cảm xúc đó, còn điều gì nữa trong bạn không?',
    },
    forest: {
      aria: 'Bản đồ suy nghĩ',
      title: 'Bản đồ suy nghĩ',
      desc: 'Mỗi nhánh là một lĩnh vực trong cuộc sống — gia đình, công việc, sức khỏe...',
      back: '← Quay lại',
      entries: '{n} ghi nhận',
      empty: 'Chưa có ghi nhận nào trong nhánh này. Hãy bắt đầu suy ngẫm!',
      filterAll: 'Tất cả',
      confidence: 'Độ chắc chắn',
      status: 'Trạng thái',
      occurrences: 'Xuất hiện',
      occurrencesTimes: '{n} lần',
      domain: 'Lĩnh vực',
      created: 'Tạo lúc',
      updated: 'Cập nhật',
      relations: '{n} quan hệ liên kết',
      treeSeed: 'Hạt giống',
      treeSprouting: 'Nảy mầm',
      treeGrowing: 'Đang lớn',
      treeFlourishing: 'Thịnh vượng',
    },
    insights: {
      aria: 'Góc khám phá',
      title: 'Góc khám phá',
      desc: 'Nhìn thấy kiểu suy nghĩ lặp lại và những điểm mâu thuẫn trong lòng bạn',
      today: '🔍 Khám phá hôm nay',
      todayEmpty: 'Chưa có khám phá hôm nay. Hãy bắt đầu suy ngẫm!',
      new: 'MỚI',
      topBeliefs: '💡 Niềm tin nổi bật',
      beliefsEmpty: 'Chưa có niềm tin được ghi nhận.',
      topValues: '🌟 Giá trị nổi bật',
      valuesEmpty: 'Chưa có giá trị được ghi nhận.',
      contradictions: '⚡ Mâu thuẫn trong suy nghĩ',
      contradictionsEmpty: 'Chưa phát hiện mâu thuẫn. Tiếp tục suy ngẫm để nhìn thấy rõ hơn.',
      biases: '🧩 Kiểu suy nghĩ lệch',
      biasesEmpty: 'Chưa phát hiện kiểu suy nghĩ lệch. Hệ thống sẽ phân tích khi bạn chia sẻ thêm.',
      biasDefault: 'Kiểu suy nghĩ này có thể ảnh hưởng cách bạn hiểu sự việc.',
      disclaimer: 'Các gợi ý dưới đây chỉ để suy ngẫm thêm — không phải kết luận hay chẩn đoán.',
      contradictionPrefix: 'Có thể bạn đang',
      contradictionSuffix: 'Điều này có thể một phần do hoàn cảnh, không chỉ do lựa chọn cá nhân.',
    },
    timeline: {
      aria: 'Dòng thời gian suy nghĩ',
      title: 'Dòng thời gian',
      desc: 'Theo dõi suy nghĩ và giá trị của bạn thay đổi theo thời gian',
      empty: 'Dòng thời gian sẽ hiển thị khi bạn bắt đầu suy ngẫm và có thêm ghi nhận.',
      journey: 'Hành trình suy nghĩ',
      valueLabel: 'Giá trị',
      appears: 'Xuất hiện {n} lần',
      sessionStart: 'Bắt đầu suy ngẫm',
      valueShift: 'Thay đổi giá trị',
      valueShiftDesc: 'Từ "{from}" sang "{to}"',
      nodeDesc: '{status} · xuất hiện {n} lần',
    },
    test: {
      aria: 'Chế độ thử nghiệm',
      title: 'Thử nghiệm',
      desc: 'Kịch bản mẫu để tham khảo và mô phỏng hội thoại',
      listAria: 'Danh sách kịch bản',
      selectHint: 'Chọn một kịch bản bên trái để xem chi tiết.',
      simulating: 'Đang mô phỏng...',
      stop: 'Dừng',
      scenarios: 'Kịch bản ({n})',
      noScenarios: 'Chưa có kịch bản. Thêm vào test-scenarios.js',
      fillHome: 'Điền vào Trang chủ',
      simulate: 'Mô phỏng',
      simulateFast: 'Mô phỏng nhanh',
      restore: '↩ Khôi phục dữ liệu cũ',
      persona: 'Nhân vật',
      personaAge: '{age} tuổi',
      situation: 'Tình huống',
      initialThought: 'Suy nghĩ ban đầu',
      dialogue: 'Kịch bản hội thoại (7 bước)',
      dialogueHint: 'Tham khảo từng lượt trả lời — hoặc dùng Mô phỏng để app tự chạy.',
      expected: 'Kết quả kỳ vọng',
      domain: 'Lĩnh vực',
      contradictionsMay: 'Mâu thuẫn có thể phát hiện',
      learning: 'Điểm cần chú ý',
      filledHome: 'Đã điền kịch bản vào Trang chủ',
      restored: 'Đã khôi phục dữ liệu trước mô phỏng',
      noBackup: 'Không có bản sao lưu để khôi phục',
      simStopped: 'Đã dừng mô phỏng',
      simDone: 'Mô phỏng xong — {entries} ghi nhận, {contradictions} mâu thuẫn',
      simFailed: 'Mô phỏng thất bại',
      stepProgress: 'Bước {current}/{total}: {step}',
    },
    reset: {
      title: 'Xóa toàn bộ dữ liệu?',
      desc: 'Hành động này sẽ xóa vĩnh viễn mọi ghi nhận, phiên suy ngẫm, bản đồ suy nghĩ và dòng thời gian trên thiết bị này. Bạn không thể hoàn tác.',
      cancel: 'Hủy',
      confirm: 'Xóa và bắt đầu lại',
    },
    common: {
      close: 'Đóng',
      langVi: 'VI',
      langEn: 'EN',
      langSwitch: 'Ngôn ngữ',
    },
  },
  en: {
    appName: 'Thought Reflection',
    metaDescription: 'Reflect on your thoughts — record and understand yourself more clearly',
    nav: {
      main: 'Main navigation',
      home: 'Home',
      reflection: 'Reflect',
      forest: 'Map',
      insights: 'Explore',
      timeline: 'Timeline',
      test: 'Test',
    },
    home: {
      aria: 'Home',
      badge: '7-step reflection framework',
      title: 'What are you thinking about today?',
      subtitle:
        'Share your thoughts — the system records and organizes them in 7 steps: event, emotion, interpretation, belief, value, identity, and action.',
      placeholder: 'e.g. My child refuses to study and I worry about their future...',
      inputAria: 'Your thought',
      startBtn: 'Start reflection',
      statEntries: 'Entries',
      statVerified: 'Established',
      statSessions: 'Sessions',
      resetText: 'Want to start fresh? All entries, sessions, and timeline will be deleted.',
      resetBtn: 'Clear data and start over',
      shareFirst: 'Please share your thought first.',
      sessionStarted: 'Reflection session started',
      dataReset: 'Data cleared. You can start fresh.',
      disclaimer:
        'This is a self-reflection tool — not a substitute for therapy or medical care. If you are in crisis, please seek professional support.',
      privacy: 'Your data stays on this device only — no one else can read it.',
    },
    ai: {
      title: 'Response mode',
      desc: 'Default is the offline rule engine. Enable Cursor AI for more natural reflection prompts — requires a local proxy.',
      modeAria: 'Response mode',
      modeRule: 'Rule engine (offline)',
      modeCursor: 'Cursor AI',
      proxyLabel: 'Proxy URL',
      testBtn: 'Test connection',
      helpTitle: 'How to run the Cursor proxy',
      help1: 'Create an API key at Cursor Dashboard → Integrations',
      help2: 'In terminal: cd server && npm install && export CURSOR_API_KEY="..." && npm start',
      help3: 'Select Cursor AI, test connection, then start reflecting',
      statusUnknown: 'Not checked',
      statusOk: 'Proxy ready',
      statusNoKey: 'CURSOR_API_KEY missing on server',
      statusError: 'Cannot connect',
      statusChecking: 'Checking...',
      testOk: 'Cursor proxy connected',
      testFail: 'Cannot reach proxy',
      badgeRule: 'Rule engine',
      badgeCursor: 'Cursor AI',
      thinking: 'Reflecting with you...',
      fallbackRule: 'AI unavailable — used rule engine instead',
    },
    safety: {
      title: 'You don\'t have to face this alone',
      body: 'What you shared may be very heavy. If you are having thoughts of harming yourself, please reach out now:',
      hotline1: 'National crisis line (Vietnam)',
      hotline1Tel: '111',
      hotline2: 'Mental health helpline',
      hotline2Tel: '18001929',
      footer: 'This app is not a substitute for a professional. You deserve to be heard and supported.',
      understood: 'I understand',
    },
    reflection: {
      aria: 'Reflection session',
      title: 'Reflection session',
      progressAria: 'Conversation progress',
      progress: 'Progress',
      suggestions: 'Suggested answers',
      suggestionsAria: 'Suggested answer options',
      suggestionTitle: 'Select this answer',
      chatPlaceholder: 'Share your thoughts...',
      chatAria: 'Message',
      send: 'Send',
      sendAria: 'Send',
      empty: 'No reflection session yet.',
      emptyHint: 'Start from Home.',
      you: 'You',
      guide: 'Reflection guide',
      shareMore: 'What else would you like to share?',
      openingDefault: 'It sounds like this is touching something in you. How do you feel?',
      openingWithThought:
        'I hear you talking about "{thought}". It sounds like this matters to you — how do you feel?',
      emotionWithEvent: 'When you think about "{event}", which feeling stands out most?',
      interpretationWithEmotion: 'When you feel {emotion}, what do you worry might happen?',
      beliefPrompt: 'What makes you believe that — can you say a bit more?',
      sessionEnd:
        'Thank you for sharing. I\'ve added this to your thought map. When you\'re ready, you can explore more in Explore.',
      sessionEndMarker: 'Explore',
      emotionSuggestion: 'When I think about it, I feel anxious and tense',
      fallbackReflection: 'Reflection',
      skipStep: 'Skip this step',
      skippedStep: '(Skipped this step)',
      skipNote: 'That\'s okay — you can return to this topic whenever you want.',
      shortSuggestions: 'Quick picks',
      summaryTitle: 'Summary',
      summaryTemplate:
        'You\'re thinking about: {event}. Main feeling: {emotion}. How you understand it: {interpretation}. Belief: {belief}. What matters: {value}.',
      reframeQuestion: 'If you looked at this a little more gently, how else might you understand it?',
      smallStepQuestion: 'What is one small step, within your reach today, that you might try?',
      contextQuestion: 'What part of this situation comes from circumstances or outside pressure — not just from you?',
      powerQuestion: 'In this situation, who might be able to change something — including you?',
      expandEmotion: 'Besides that feeling, is there anything else inside you?',
    },
    forest: {
      aria: 'Thought map',
      title: 'Thought map',
      desc: 'Each branch is a life area — family, work, health...',
      back: '← Back',
      entries: '{n} entries',
      empty: 'No entries in this branch yet. Start reflecting!',
      filterAll: 'All',
      confidence: 'Confidence',
      status: 'Status',
      occurrences: 'Occurrences',
      occurrencesTimes: '{n} times',
      domain: 'Life area',
      created: 'Created',
      updated: 'Updated',
      relations: '{n} linked relations',
      treeSeed: 'Seed',
      treeSprouting: 'Sprouting',
      treeGrowing: 'Growing',
      treeFlourishing: 'Flourishing',
    },
    insights: {
      aria: 'Explore',
      title: 'Explore',
      desc: 'See recurring thought patterns and inner contradictions',
      today: '🔍 Today\'s discoveries',
      todayEmpty: 'No discoveries today. Start reflecting!',
      new: 'NEW',
      topBeliefs: '💡 Top beliefs',
      beliefsEmpty: 'No beliefs recorded yet.',
      topValues: '🌟 Top values',
      valuesEmpty: 'No values recorded yet.',
      contradictions: '⚡ Thought contradictions',
      contradictionsEmpty: 'No contradictions found yet. Keep reflecting to see more clearly.',
      biases: '🧩 Thinking patterns',
      biasesEmpty: 'No thinking patterns detected yet. Share more for analysis.',
      biasDefault: 'This thinking pattern may affect how you interpret events.',
      disclaimer: 'The notes below are for reflection only — not conclusions or diagnoses.',
      contradictionPrefix: 'You might be',
      contradictionSuffix: 'This may partly come from circumstances, not only personal choice.',
    },
    timeline: {
      aria: 'Thought timeline',
      title: 'Timeline',
      desc: 'Track how your thoughts and values change over time',
      empty: 'Timeline appears once you start reflecting and have entries.',
      journey: 'Thought journey',
      valueLabel: 'Value',
      appears: 'Appeared {n} times',
      sessionStart: 'Reflection started',
      valueShift: 'Value shift',
      valueShiftDesc: 'From "{from}" to "{to}"',
      nodeDesc: '{status} · appeared {n} times',
    },
    test: {
      aria: 'Test mode',
      title: 'Test',
      desc: 'Sample scenarios to explore and simulate conversations',
      listAria: 'Scenario list',
      selectHint: 'Select a scenario on the left to view details.',
      simulating: 'Simulating...',
      stop: 'Stop',
      scenarios: 'Scenarios ({n})',
      noScenarios: 'No scenarios. Add to test-scenarios.js',
      fillHome: 'Fill Home',
      simulate: 'Simulate',
      simulateFast: 'Fast simulate',
      restore: '↩ Restore previous data',
      persona: 'Persona',
      personaAge: '{age} years old',
      situation: 'Situation',
      initialThought: 'Initial thought',
      dialogue: 'Dialogue script (7 steps)',
      dialogueHint: 'Reference each reply — or use Simulate to run automatically.',
      expected: 'Expected outcomes',
      domain: 'Life area',
      contradictionsMay: 'Possible contradictions',
      learning: 'Points to notice',
      filledHome: 'Scenario filled into Home',
      restored: 'Restored data from before simulation',
      noBackup: 'No backup to restore',
      simStopped: 'Simulation stopped',
      simDone: 'Done — {entries} entries, {contradictions} contradictions',
      simFailed: 'Simulation failed',
      stepProgress: 'Step {current}/{total}: {step}',
    },
    reset: {
      title: 'Delete all data?',
      desc: 'This permanently deletes all entries, sessions, thought map, and timeline on this device. This cannot be undone.',
      cancel: 'Cancel',
      confirm: 'Delete and start over',
    },
    common: {
      close: 'Close',
      langVi: 'VI',
      langEn: 'EN',
      langSwitch: 'Language',
    },
  },
};

const I18N_FRAMEWORK = {
  vi: {
    Event: 'Việc xảy ra',
    Emotion: 'Cảm xúc',
    Interpretation: 'Cách hiểu',
    Belief: 'Niềm tin',
    Value: 'Giá trị',
    Identity: 'Vai trò bản thân',
    Action: 'Hành động',
  },
  en: {
    Event: 'Event',
    Emotion: 'Emotion',
    Interpretation: 'Interpretation',
    Belief: 'Belief',
    Value: 'Value',
    Identity: 'Identity',
    Action: 'Action',
  },
};

const I18N_NODE_STATUS = {
  vi: { draft: 'Mới ghi nhận', candidate: 'Lặp lại nhiều lần', verified: 'Đã vững chắc' },
  en: { draft: 'New', candidate: 'Repeating', verified: 'Established' },
};

const I18N_FOREST = {
  vi: {
    family: 'Gia đình',
    work: 'Công việc',
    finance: 'Tài chính',
    learning: 'Học tập',
    health: 'Sức khỏe',
    self: 'Bản thân',
  },
  en: {
    family: 'Family',
    work: 'Work',
    finance: 'Finance',
    learning: 'Learning',
    health: 'Health',
    self: 'Self',
  },
};

const I18N_REFLECTION_QUESTIONS = {
  vi: {
    Event: [
      'Bạn có thể kể thêm về tình huống đó không?',
      'Điều gì đã xảy ra cụ thể?',
      'Khi nào và ở đâu điều đó diễn ra?',
    ],
    Emotion: [
      'Điều đó khiến bạn cảm thấy thế nào?',
      'Cảm xúc nào nổi bật nhất — buồn, lo, tức, hay điều khác?',
      'Trong cơ thể, bạn cảm nhận điều gì khi nghĩ về việc này?',
    ],
    Interpretation: [
      'Bạn đang lo điều gì có thể xảy ra?',
      'Bạn hiểu sự việc đó theo cách nào?',
      'Điều gì ý nghĩa nhất với bạn trong tình huống này?',
    ],
    Belief: [
      'Điều gì khiến bạn tin như vậy?',
      'Niềm tin nào đang dẫn dắt suy nghĩ của bạn?',
      'Bạn đã từng nghĩ điều tương tự trước đây chưa?',
    ],
    Value: [
      'Điều gì quan trọng nhất với bạn trong việc này?',
      'Phần nào trong tình huống này đến từ hoàn cảnh, áp lực bên ngoài?',
      'Giá trị nào đang bị đe dọa hoặc được khẳng định?',
    ],
    Identity: [
      'Trong tình huống này, bạn thấy mình là ai?',
      'Ai trong tình huống này có thể thay đổi điều gì — kể cả bạn?',
      'Vai trò nào của bạn đang được đặt lên bàn cân?',
    ],
    Action: [
      'Một bước nhỏ, trong khả năng hôm nay, bạn có thể thử làm gì?',
      'Bạn muốn làm gì tiếp theo?',
      'Nếu không có rào cản, bạn sẽ làm gì?',
    ],
  },
  en: {
    Event: [
      'Can you tell me more about that situation?',
      'What exactly happened?',
      'When and where did it take place?',
    ],
    Emotion: [
      'How did that make you feel?',
      'Which feeling stands out most — sad, anxious, angry, or something else?',
      'What do you notice in your body when you think about this?',
    ],
    Interpretation: [
      'What are you afraid might happen?',
      'How do you understand what happened?',
      'What matters most to you in this situation?',
    ],
    Belief: [
      'What makes you believe that?',
      'Which belief is guiding your thinking?',
      'Have you thought this way before?',
    ],
    Value: [
      'What matters most to you here?',
      'What part of this comes from circumstances or outside pressure?',
      'Which value feels threatened or affirmed?',
    ],
    Identity: [
      'In this situation, who do you see yourself as?',
      'Who in this situation might be able to change something — including you?',
      'Which role of yours is being activated?',
    ],
    Action: [
      'What is one small step, within your reach today, that you might try?',
      'What do you want to do next?',
      'If nothing held you back, what would you do?',
    ],
  },
};

const I18N_SHORT_CHIPS = {
  vi: {
    Emotion: ['Buồn', 'Lo', 'Tức', 'Mệt', 'Không biết', 'Căng thẳng'],
    default: ['Không biết', 'Khó nói', 'Cần suy nghĩ thêm'],
  },
  en: {
    Emotion: ['Sad', 'Anxious', 'Angry', 'Tired', "I don't know", 'Tense'],
    default: ["I don't know", 'Hard to say', 'Need more time'],
  },
};

const I18N_REFLECTION_SUGGESTIONS = {
  vi: {
    Event: [
      'Hôm nay tôi bị sếp mắng trước mặt đồng nghiệp',
      'Con tôi không nghe lời và bỏ học bài',
      'Tôi làm việc 14 giờ mỗi ngày và mệt mỏi',
      'Vợ/chồng và tôi cãi nhau về việc nuôi dạy con',
      'Tôi không đạt KPI tháng này dù đã cố gắng',
    ],
    Emotion: [
      'Tôi cảm thấy lo lắng và bực bội',
      'Tôi buồn, thất vọng và mệt mỏi',
      'Tôi căng thẳng, áp lực trong ngực',
      'Tôi tức giận nhưng cũng cảm thấy tội lỗi',
      'Tôi cô đơn và không biết nói với ai',
    ],
    Interpretation: [
      'Tôi nghĩ mình đang làm cha mẹ tồi',
      'Có lẽ sếp không coi trọng tôi',
      'Tôi lo con sẽ không thành công trong tương lai',
      'Tôi sợ mọi thứ sẽ trở nên tệ hơn',
      'Có vẻ như dù cố gắng cũng không đủ',
    ],
    Belief: [
      'Tôi tin rằng con phải nghe lời cha mẹ',
      'Tôi nghĩ mình phải hoàn hảo mới được yêu',
      'Tôi tin làm việc chăm chỉ sẽ được đền đáp',
      'Tôi nghĩ thất bại là đáng xấu hổ',
      'Tôi tin gia đình phải là ưu tiên số một',
    ],
    Value: [
      'Gia đình là quan trọng nhất với tôi',
      'Tôi coi trọng trách nhiệm và kỷ luật',
      'Tôi trân trọng sự cân bằng giữa công việc và cuộc sống',
      'Tôi đánh giá cao sự trung thực và tôn trọng',
      'Phát triển bản thân và học hỏi rất quan trọng với tôi',
    ],
    Identity: [
      'Tôi thấy mình là người cha/mẹ đang thất bại',
      'Tôi là người luôn cố hy sinh vì gia đình',
      'Tôi là người làm việc không ngừng nghỉ',
      'Tôi là người phải gánh vác mọi thứ một mình',
      'Tôi là người luôn cố làm hài lòng người khác',
    ],
    Action: [
      'Tôi muốn nói chuyện với con một cách bình tĩnh hơn',
      'Tôi đang cân nhắc giảm giờ làm việc',
      'Tôi sẽ dành thời gian cho gia đình cuối tuần này',
      'Tôi muốn tìm người tư vấn hoặc chia sẻ',
      'Tôi sẽ thử nghỉ ngơi và chăm sóc sức khỏe trước',
    ],
  },
  en: {
    Event: [
      'My boss criticized me in front of colleagues today',
      'My child won\'t listen and skipped homework',
      'I work 14 hours a day and feel exhausted',
      'My spouse and I argued about parenting',
      'I missed my KPI this month despite trying hard',
    ],
    Emotion: [
      'I feel anxious and frustrated',
      'I feel sad, disappointed, and tired',
      'I feel tense pressure in my chest',
      'I feel angry but also guilty',
      'I feel lonely and don\'t know who to talk to',
    ],
    Interpretation: [
      'I think I\'m failing as a parent',
      'Maybe my boss doesn\'t respect me',
      'I worry my child won\'t succeed in the future',
      'I fear things will get worse',
      'It seems like no matter how hard I try, it\'s not enough',
    ],
    Belief: [
      'I believe children must obey their parents',
      'I think I must be perfect to be loved',
      'I believe hard work will be rewarded',
      'I think failure is shameful',
      'I believe family must come first',
    ],
    Value: [
      'Family is most important to me',
      'I value responsibility and discipline',
      'I cherish work-life balance',
      'I value honesty and respect',
      'Personal growth and learning matter deeply to me',
    ],
    Identity: [
      'I see myself as a failing parent',
      'I am someone who always sacrifices for family',
      'I am someone who never stops working',
      'I am someone who must carry everything alone',
      'I am someone who tries to please everyone',
    ],
    Action: [
      'I want to talk to my child more calmly',
      'I\'m considering reducing my work hours',
      'I will spend time with family this weekend',
      'I want to find someone to talk to or get advice',
      'I will try to rest and take care of my health first',
    ],
  },
};

const I18N_BIAS_DESCRIPTIONS = {
  vi: {
    'Confirmation Bias': 'Bạn có thể chỉ chú ý điều củng cố niềm tin sẵn có.',
    Overgeneralization: 'Dùng "luôn luôn", "không bao giờ" có thể làm sự việc trông tệ hơn thực tế.',
    'Black and White Thinking': 'Nhìn mọi thứ chỉ theo đúng hoặc sai, bỏ qua phần ở giữa.',
    Catastrophizing: 'Dễ nghĩ đến kết quả tồi tệ nhất.',
    'Mind Reading': 'Dễ đoán người khác đang nghĩ gì mà chưa hỏi.',
    'Should Statements': 'Quy tắc "phải/nên" quá cứng có thể tạo áp lực lớn.',
    Personalization: 'Dễ đổ hết trách nhiệm về bản thân.',
  },
  en: {
    'Confirmation Bias': 'You may only notice information that confirms existing beliefs.',
    Overgeneralization: 'Words like "always" or "never" can make reality seem worse than it is.',
    'Black and White Thinking': 'Seeing only right or wrong, ignoring the middle ground.',
    Catastrophizing: 'Tending to imagine the worst outcome.',
    'Mind Reading': 'Assuming you know what others think without asking.',
    'Should Statements': 'Rigid "must/should" rules can create heavy pressure.',
    Personalization: 'Taking too much responsibility onto yourself.',
  },
};

const I18n = {
  locale: 'vi',
  _listeners: [],

  init() {
    DataStore.load();
    const saved = DataStore.load().settings?.locale;
    this.locale = saved === 'en' ? 'en' : 'vi';
    this.applyDocumentLang();
  },

  getLocale() {
    return this.locale;
  },

  setLocale(locale) {
    const next = locale === 'en' ? 'en' : 'vi';
    if (next === this.locale) return;
    this.locale = next;
    DataStore.save({
      settings: { ...DataStore.load().settings, locale: next },
    });
    this.applyDocumentLang();
    this._listeners.forEach((fn) => fn(next));
  },

  onChange(fn) {
    this._listeners.push(fn);
  },

  applyDocumentLang() {
    document.documentElement.lang = this.locale === 'en' ? 'en' : 'vi';
    document.title = this.t('appName');
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.content = this.t('metaDescription');
  },

  t(key, vars = {}) {
    const parts = key.split('.');
    let value = I18N_MESSAGES[this.locale];
    for (const part of parts) {
      value = value?.[part];
    }
    if (value == null) return key;
    if (typeof value !== 'string') return key;
    return value.replace(/\{(\w+)\}/g, (_, k) => (vars[k] != null ? vars[k] : `{${k}}`));
  },

  frameworkLabel(step) {
    return I18N_FRAMEWORK[this.locale]?.[step] || step;
  },

  nodeStatusLabel(status) {
    return I18N_NODE_STATUS[this.locale]?.[status] || status;
  },

  forestLabel(id) {
    return I18N_FOREST[this.locale]?.[id] || id;
  },

  treeStatusLabel(status) {
    const map = {
      seed: this.t('forest.treeSeed'),
      sprouting: this.t('forest.treeSprouting'),
      growing: this.t('forest.treeGrowing'),
      flourishing: this.t('forest.treeFlourishing'),
    };
    return map[status] || status;
  },

  reflectionQuestions(flowStep) {
    return I18N_REFLECTION_QUESTIONS[this.locale]?.[flowStep] || [];
  },

  reflectionSuggestions(flowStep) {
    return I18N_REFLECTION_SUGGESTIONS[this.locale]?.[flowStep] || [];
  },

  biasDescription(biasName) {
    return (
      I18N_BIAS_DESCRIPTIONS[this.locale]?.[biasName] ||
      this.t('insights.biasDefault')
    );
  },

  biasLabel(item) {
    return this.locale === 'vi' ? item.labelVi || item.label : item.label;
  },

  localeDate(iso) {
    if (!iso) return '—';
    const loc = this.locale === 'en' ? 'en-US' : 'vi-VN';
    return new Date(iso).toLocaleString(loc, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  },

  localeTime(iso) {
    const loc = this.locale === 'en' ? 'en-US' : 'vi-VN';
    return new Date(iso).toLocaleTimeString(loc, {
      hour: '2-digit',
      minute: '2-digit',
    });
  },

  isSessionEndContent(content) {
    if (!content) return false;
    return (
      content.includes(I18N_MESSAGES.vi.reflection.sessionEndMarker) ||
      content.includes(I18N_MESSAGES.en.reflection.sessionEndMarker)
    );
  },

  shortChips(flowStep) {
    const pool = I18N_SHORT_CHIPS[this.locale];
    return pool?.[flowStep] || pool?.default || [];
  },

  getCrisisResources() {
    return {
      title: this.t('safety.title'),
      body: this.t('safety.body'),
      hotlines: [
        { label: this.t('safety.hotline1'), tel: this.t('safety.hotline1Tel') },
        { label: this.t('safety.hotline2'), tel: this.t('safety.hotline2Tel') },
      ],
      footer: this.t('safety.footer'),
      understood: this.t('safety.understood'),
    };
  },

  formatContradiction(message) {
    if (!message) return '';
    const trimmed = message.replace(/\s+/g, ' ').trim();
    const lower = trimmed.charAt(0).toLowerCase() + trimmed.slice(1);
    return `${this.t('insights.contradictionPrefix')} ${lower}. ${this.t('insights.contradictionSuffix')}`;
  },

  applyStatic() {
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      el.textContent = this.t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.placeholder = this.t(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll('[data-i18n-aria]').forEach((el) => {
      el.setAttribute('aria-label', this.t(el.dataset.i18nAria));
    });
    document.querySelectorAll('.nav-link').forEach((btn) => {
      const screen = btn.dataset.screen;
      const label = btn.querySelector('.nav-label');
      if (label && screen) label.textContent = this.t(`nav.${screen}`);
    });
    document.querySelectorAll('[data-lang]').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.lang === this.locale);
      btn.setAttribute('aria-pressed', btn.dataset.lang === this.locale ? 'true' : 'false');
    });
    const brand = document.querySelector('.nav-title');
    if (brand) brand.textContent = this.t('appName');
  },
};

if (typeof window !== 'undefined') {
  window.I18n = I18n;
}
