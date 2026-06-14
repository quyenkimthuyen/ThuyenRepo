/**
 * i18n — Song ngữ Tiếng Việt / English
 */

const I18N_MESSAGES = {
  vi: {
    appName: 'Nhìn lại suy nghĩ',
    metaDescription: 'Ghi nhận suy nghĩ và nhìn lại bản thân qua 7 bước — dữ liệu chỉ ở trên thiết bị của bạn',
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
        'Viết điều đang bận trong đầu — app sẽ cùng bạn nhìn lại qua 7 bước: chuyện gì xảy ra, bạn cảm thấy sao, hiểu thế nào, tin điều gì, điều gì quan trọng, bạn là ai trong đó, và bước tiếp theo.',
      placeholder: 'Ví dụ: Con tôi không chịu học, tôi lo lắng về tương lai của con...',
      inputAria: 'Suy nghĩ của bạn',
      startBtn: 'Bắt đầu suy ngẫm',
      aiAssistBtn: 'Suy ngẫm với ChatGPT',
      modePickerAria: 'Chọn cách suy ngẫm',
      modeInApp: 'Suy ngẫm trong app',
      modeInAppDesc: 'Từng câu hỏi nhẹ nhàng, ngay trong app',
      modeChatGpt: 'Cùng ChatGPT',
      modeChatGptDesc: 'Trò chuyện bên ngoài, mang kết quả về đây',
      statEntries: 'Ghi nhận',
      statVerified: 'Đã vững chắc',
      statSessions: 'Phiên suy ngẫm',
      resetText: 'Muốn xóa hết và bắt đầu lại? Mọi ghi nhận và phiên suy ngẫm trên máy này sẽ mất.',
      resetBtn: 'Xóa và bắt đầu lại',
      shareFirst: 'Hãy viết vài dòng suy nghĩ trước nhé.',
      sessionStarted: 'Bắt đầu phiên suy ngẫm',
      dataReset: 'Đã xóa dữ liệu. Bạn có thể bắt đầu lại.',
      disclaimer:
        'Đây là không gian tự suy ngẫm, không thay tư vấn chuyên môn. Nếu bạn đang rất khó khăn, hãy tìm người hỗ trợ.',
      privacy: 'Mọi thứ chỉ lưu trên máy bạn.',
    },
    aiAssist: {
      badge: 'Qua ChatGPT',
      title: 'Suy ngẫm với ChatGPT',
      intro:
        'Bạn trò chuyện trên ChatGPT, rồi mang kết quả về đây — app không tự gửi dữ liệu đi đâu.',
      flowApp: 'App',
      flowChat: 'ChatGPT',
      flowBack: 'App',
      stepper1: 'Sao chép',
      stepper2: 'Trò chuyện',
      stepper3: 'Dán về',
      privacyBanner: 'App không tự gửi dữ liệu — chỉ khi bạn tự sao chép sang ChatGPT.',
      thoughtLabel: 'Điều đang bận trong đầu',
      promptPreview: 'Lời mở đầu cho ChatGPT',
      step1Title: 'Bước 1 — Sao chép lời mở đầu',
      step1Desc: 'Chỉnh lại nếu cần, rồi sao chép đoạn bên dưới vào ChatGPT.',
      step1Next: 'Đã sao chép',
      step2Title: 'Bước 2 — Trò chuyện',
      step2Desc: 'Trả lời từng câu hỏi, không cần vội. Khi thấy đủ, sang bước tiếp theo.',
      step2Next: 'Đã trò chuyện xong',
      step3Title: 'Bước 3 — Mang kết quả về',
      step3Desc: 'Sao chép lời kết thúc vào chat, lấy kết quả ChatGPT trả về và dán vào ô bên dưới.',
      stepBack: 'Quay lại',
      openChatGpt: 'Mở ChatGPT ↗',
      exportPromptToggle: 'Lời kết thúc (để lấy kết quả)',
      pasteHint: 'Dán vào đây, rồi bấm Xem trước',
      copy: 'Sao chép',
      copyExport: 'Sao chép lời kết thúc',
      copyDone: 'Đã sao chép',
      importLabel: 'Kết quả từ ChatGPT',
      importPlaceholder: 'Dán kết quả ChatGPT trả về (thường là dạng JSON)...',
      importBtn: 'Lưu vào app',
      previewBtn: 'Xem trước',
      previewTitle: 'Trước khi lưu',
      previewDesc: 'Xem lại 7 bước. Mục màu xanh lá là gợi ý thêm từ app.',
      previewBack: 'Sửa lại',
      confirmImport: 'Lưu',
      previewFromAi: 'Từ ChatGPT',
      previewFromRule: 'App gợi ý thêm',
      previewBiases: 'Kiểu suy nghĩ',
      previewEmptyStep: '—',
      previewInvalid: 'Chưa đọc được kết quả — kiểm tra lại phần bạn vừa dán.',
      previewInvalidHint: 'Gợi ý: {hint}',
      previewStats: '{ai} từ ChatGPT · {rule} gợi ý thêm · {steps}/7 bước',
      previewStatsTranscript: 'Sẽ lưu {n} lượt trò chuyện',
      previewWarnManyEmpty: 'Khá nhiều bước còn trống — có thể trò chuyện thêm trên ChatGPT.',
      previewWarnNoInterpretation: 'Thiếu phần “cách bạn hiểu việc đó”.',
      previewWarnNoEmotions: 'Thiếu phần cảm xúc.',
      transcriptToggle: 'Nhật ký trò chuyện (không bắt buộc)',
      transcriptDesc:
        'Dán log chat (User: / ChatGPT:) nếu muốn giữ nguyên giọng hội thoại. Bỏ trống thì app chỉ lưu phần tóm tắt.',
      transcriptPlaceholder: 'User: ...\nChatGPT: ...',
      contextRefreshed: 'Đã lấy dữ liệu mới nhất',
      contextNote: 'Dữ liệu trong prompt cập nhật lúc {time}',
      matchApply: 'Sẽ lưu',
      matchFuzzy: 'Gần khớp',
      matchMiss: 'Chưa tìm thấy',
      previewForestStats: 'Liên kết: {apply}/{total} · Cập nhật: {updates}/{totalUpdates}',
      previewInsightsStats: '{n} mâu thuẫn · {e} gợi ý · {new} điểm mới',
      previewTimelineStats: '{m} mốc · {v} chuyển giá trị',
      warnForestMiss: '{n} liên kết chưa khớp — sửa tên bên dưới hoặc bỏ qua khi lưu.',
      warnForestFuzzy: '{n} mục chỉ khớp gần đúng — xem lại trước khi lưu.',
      warnInsightsOverlap: '{n} mâu thuẫn trùng ý với phần app đã nhận ra.',
      matchResolvedAs: '→ khớp với “{label}”',
      editLabelHint: 'Sửa tên nếu cần, rồi Xem trước lại',
      jsonHintNoObject: 'Không thấy dữ liệu dạng JSON',
      jsonHintInvalidShape: 'Cấu trúc không đúng với màn hình này',
      importedNote: '(Từ phiên ChatGPT)',
      eeibviaSummaryTitle: 'Tóm tắt 7 bước',
      recordedInMap: 'Đã ghi vào bản đồ suy nghĩ. Khi sẵn sàng, mở {marker}.',
      sessionEndPlain: 'Cảm ơn bạn đã chia sẻ. Đã ghi vào bản đồ suy nghĩ.',
      reframeLabel: 'Góc nhìn khác',
      smallStepLabel: 'Bước nhỏ',
      copied: 'Đã sao chép',
      copyFailed: 'Không sao chép được — hãy chọn và copy thủ công',
      importEmpty: 'Hãy dán kết quả từ ChatGPT trước.',
      importInvalid: 'Chưa đọc được kết quả. Thử dán lại sau khi dùng lời kết thúc.',
      importMissingEvent: 'Thiếu phần việc xảy ra — trò chuyện đủ các bước rồi xuất lại.',
      importSuccess: 'Đã lưu — mở Suy ngẫm hoặc Khám phá',
      needThought: 'Viết vài dòng suy nghĩ trước khi sao chép.',
    },
    aiScreen: {
      triggerForest: 'ChatGPT',
      triggerInsights: 'ChatGPT',
      triggerTimeline: 'ChatGPT',
      title_insights: 'Khám phá sâu hơn',
      title_forest: 'Nhìn lại bản đồ',
      title_timeline: 'Kể lại hành trình',
      desc_insights:
        'Sao chép đoạn bên dưới — kèm những gì bạn đã ghi nhận — để ChatGPT gợi ý mâu thuẫn, kiểu lặp lại và câu hỏi tiếp theo.',
      desc_forest:
        'Sao chép đoạn kèm bản đồ hiện tại để ChatGPT gợi ý liên kết và chủ đề theo từng lĩnh vực.',
      desc_timeline:
        'Sao chép đoạn kèm dòng thời gian để ChatGPT giúp bạn thấy bước ngoặt và sự thay đổi giá trị.',
      stepper1: 'Sao chép',
      stepper3: 'Dán về',
      step1Next: 'Đã sao chép',
      step2Desc: 'Trao đổi thoải mái trên ChatGPT. Xong thì sang bước cuối.',
      step2Next: 'Sang bước cuối',
      analysisPrompt: 'Đoạn phân tích (kèm dữ liệu của bạn)',
      exportPrompt: 'Lời kết thúc (để lấy kết quả)',
      needData: 'Cần có vài ghi nhận trước — hãy suy ngẫm hoặc nhập từ ChatGPT.',
      previewEmpty: 'Không có gì để lưu.',
      fromChatGpt: 'ChatGPT',
      nodeNote: 'Ghi chú từ ChatGPT',
      bannerInsights: 'Lời ChatGPT',
      bannerForest: 'Nhận xét về bản đồ',
      bannerTimeline: 'Câu chuyện hành trình',
      patterns: 'Kiểu lặp lại',
      preview_summary: 'Tóm tắt',
      preview_contradictions: 'Mâu thuẫn',
      preview_exploration: 'Câu hỏi gợi mở',
      preview_biases: 'Kiểu suy nghĩ',
      preview_patterns: 'Kiểu lặp lại',
      preview_relations: 'Liên kết',
      preview_nodeUpdates: 'Cập nhật ghi nhận',
      preview_treeInsights: 'Theo từng nhánh',
      preview_narrative: 'Hành trình',
      preview_milestones: 'Mốc',
      preview_valueShifts: 'Chuyển giá trị',
      preview_reflection: 'Câu hỏi suy ngẫm',
      importSuccess_insights: 'Đã cập nhật Khám phá',
      importSuccess_forest: 'Đã cập nhật Bản đồ',
      importSuccess_timeline: 'Đã bổ sung Dòng thời gian',
    },
    safety: {
      title: 'Bạn không cần một mình',
      body: 'Những gì bạn vừa chia sẻ nghe rất nặng. Nếu bạn đang nghĩ đến việc làm hại bản thân, hãy liên hệ ngay:',
      hotline1: 'Đường dây nóng quốc gia',
      hotline1Tel: '111',
      hotline2: 'Tổng đài tâm lý',
      hotline2Tel: '18001929',
      footer: 'App này không thay chuyên gia. Bạn xứng đáng được lắng nghe và được giúp.',
      understood: 'Tôi hiểu',
    },
    reflection: {
      aria: 'Phiên suy ngẫm',
      title: 'Suy ngẫm',
      progressAria: 'Tiến trình',
      progress: 'Tiến trình',
      suggestions: 'Gợi ý câu trả lời',
      suggestionsAria: 'Gợi ý câu trả lời',
      suggestionTitle: 'Chọn câu này',
      chatPlaceholder: 'Viết ở đây...',
      chatAria: 'Tin nhắn',
      send: 'Gửi',
      sendAria: 'Gửi',
      empty: 'Chưa có phiên nào.',
      emptyHint: 'Bắt đầu từ Trang chủ nhé.',
      you: 'Bạn',
      guide: 'Người dẫn',
      shareMore: 'Bạn muốn nói thêm điều gì?',
      openingDefault: 'Nghe có vẻ điều đó đang chạm vào bạn. Bạn cảm thấy thế nào?',
      openingWithThought:
        'Bạn đang nói về “{thought}”. Điều đó đang chạm vào bạn thế nào?',
      emotionWithEvent: 'Khi nghĩ về “{event}”, cảm xúc nào nổi lên rõ nhất?',
      interpretationWithEmotion: 'Khi cảm thấy {emotion}, bạn lo điều gì có thể xảy ra?',
      beliefPrompt: 'Điều gì khiến bạn tin như vậy?',
      sessionEnd:
        'Cảm ơn bạn đã chia sẻ. Đã ghi vào bản đồ suy nghĩ — khi muốn, mở Khám phá để nhìn thêm.',
      sessionEndMarker: 'Khám phá',
      emotionSuggestion: 'Khi nghĩ về việc đó, tôi cảm thấy lo lắng và căng thẳng',
      fallbackReflection: 'Suy ngẫm',
      skipStep: 'Bỏ qua bước này',
      skippedStep: '(Đã bỏ qua bước này)',
      skipNote: 'Không sao — bạn có thể quay lại sau.',
      shortSuggestions: 'Chọn nhanh',
      summaryTitle: 'Tóm tắt',
      summaryTemplate:
        'Bạn đang nghĩ về: {event}. Cảm xúc: {emotion}. Cách hiểu: {interpretation}. Niềm tin: {belief}. Điều quan trọng: {value}.',
      reframeQuestion: 'Nếu nhìn nhẹ hơn một chút, bạn có thể hiểu khác đi không?',
      smallStepQuestion: 'Hôm nay, một việc nhỏ trong tầm tay bạn là gì?',
      contextQuestion: 'Phần nào đến từ hoàn cảnh bên ngoài — không chỉ từ bạn?',
      powerQuestion: 'Ai có thể thay đổi điều gì — kể cả bạn?',
      expandEmotion: 'Ngoài cảm xúc đó, còn gì nữa trong bạn?',
      editMessage: 'Sửa',
      saveEdit: 'Lưu',
      cancelEdit: 'Hủy',
      editedLabel: 'đã sửa',
      messageUpdated: 'Đã cập nhật theo nội dung bạn sửa',
      editEmpty: 'Không được để trống',
    },
    forest: {
      aria: 'Bản đồ suy nghĩ',
      title: 'Bản đồ suy nghĩ',
      desc: 'Mỗi nhánh là một mảng trong đời — gia đình, công việc, sức khỏe...',
      back: '← Quay lại',
      entries: '{n} ghi nhận',
      empty: 'Nhánh này còn trống. Bắt đầu suy ngẫm là sẽ có.',
      filterAll: 'Tất cả',
      confidence: 'Độ chắc',
      status: 'Trạng thái',
      occurrences: 'Lặp lại',
      occurrencesTimes: '{n} lần',
      domain: 'Lĩnh vực',
      created: 'Tạo',
      updated: 'Cập nhật',
      relations: '{n} liên kết',
      treeSeed: 'Hạt giống',
      treeSprouting: 'Nảy mầm',
      treeGrowing: 'Đang lớn',
      treeFlourishing: 'Thịnh vượng',
    },
    insights: {
      aria: 'Khám phá',
      title: 'Khám phá',
      desc: 'Những kiểu suy nghĩ lặp lại và chỗ trong lòng bạn đang kéo hai hướng',
      today: '🔍 Hôm nay',
      todayEmpty: 'Chưa có gì mới hôm nay. Một phiên suy ngẫm sẽ giúp.',
      new: 'MỚI',
      topBeliefs: '💡 Niềm tin nổi bật',
      beliefsEmpty: 'Chưa có niềm tin nào được ghi.',
      topValues: '🌟 Giá trị nổi bật',
      valuesEmpty: 'Chưa có giá trị nào được ghi.',
      contradictions: '⚡ Chỗ đang kéo hai hướng',
      contradictionsEmpty: 'Chưa thấy mâu thuẫn rõ. Cứ suy ngẫm thêm — sẽ dần lộ ra.',
      biases: '🧩 Kiểu suy nghĩ lệch',
      biasesEmpty: 'Chưa thấy kiểu lệch rõ. Chia sẻ thêm sẽ giúp nhìn rõ hơn.',
      biasDefault: 'Kiểu này có thể ảnh hưởng cách bạn hiểu sự việc.',
      disclaimer: 'Chỉ để suy ngẫm thêm — không phải kết luận hay chẩn đoán.',
      contradictionPrefix: 'Có thể bạn đang',
      contradictionsNote: 'Điều này có thể một phần do hoàn cảnh — không chỉ do bạn.',
      exploration: '💭 Câu hỏi gợi mở',
      explorationEmpty: 'Suy ngẫm thêm để nhận câu hỏi phù hợp với những gì bạn vừa ghi.',
      explorationCta: 'Suy ngẫm tiếp',
      explorationFilled: 'Đã đưa gợi ý lên Trang chủ — sửa nếu muốn rồi bắt đầu',
    },
    timeline: {
      aria: 'Dòng thời gian',
      title: 'Dòng thời gian',
      desc: 'Xem suy nghĩ và giá trị của bạn thay đổi ra sao theo thời gian',
      empty: 'Sẽ có nội dung khi bạn bắt đầu suy ngẫm và ghi nhận thêm.',
      journey: 'Hành trình suy nghĩ',
      valueLabel: 'Giá trị',
      appears: 'Xuất hiện {n} lần',
      sessionStart: 'Bắt đầu suy ngẫm',
      valueShift: 'Thay đổi giá trị',
      valueShiftDesc: 'Từ "{from}" sang "{to}"',
      nodeDesc: '{status} · xuất hiện {n} lần',
    },
    test: {
      aria: 'Thử nghiệm',
      title: 'Thử nghiệm',
      desc: 'Kịch bản mẫu để xem app hoạt động thế nào',
      listAria: 'Danh sách kịch bản',
      selectHint: 'Chọn một kịch bản bên trái.',
      simulating: 'Đang chạy thử',
      stop: 'Dừng',
      scenarios: 'Kịch bản ({n})',
      noScenarios: 'Chưa có kịch bản',
      fillHome: 'Đưa lên Trang chủ',
      simulate: 'Chạy thử',
      simulateFast: 'Chạy nhanh',
      restore: '↩ Khôi phục dữ liệu',
      persona: 'Nhân vật',
      personaAge: '{age} tuổi',
      situation: 'Tình huống',
      initialThought: 'Suy nghĩ ban đầu',
      dialogue: 'Hội thoại mẫu (7 bước)',
      dialogueHint:
        'Sửa từng câu trả lời, rồi Chạy thử để xem ghi nhận thay đổi.',
      resetDialogue: 'Khôi phục gốc',
      rerunNoReset: 'Chạy lại',
      dialogueEdited: 'Đã sửa',
      dialogueRestored: 'Đã khôi phục hội thoại gốc',
      expected: 'Kỳ vọng',
      domain: 'Lĩnh vực',
      contradictionsMay: 'Có thể thấy mâu thuẫn',
      learning: 'Điểm đáng chú ý',
      filledHome: 'Đã đưa lên Trang chủ',
      restored: 'Đã khôi phục dữ liệu cũ',
      noBackup: 'Không có bản sao để khôi phục',
      simStopped: 'Đã dừng',
      simDone: 'Xong — {entries} ghi nhận, {contradictions} mâu thuẫn',
      simFailed: 'Chạy thử không thành công',
      stepProgress: 'Bước {current}/{total}: {step}',
    },
    reset: {
      title: 'Xóa hết dữ liệu?',
      desc: 'Mọi ghi nhận, phiên suy ngẫm, bản đồ và dòng thời gian trên máy này sẽ mất vĩnh viễn.',
      cancel: 'Hủy',
      confirm: 'Xóa và bắt đầu lại',
    },
    common: {
      close: 'Đóng',
      langVi: 'VI',
      langEn: 'EN',
      langSwitch: 'Ngôn ngữ',
    },
    screenView: {
      app: 'Từ app',
      chatgpt: 'ChatGPT',
      forestAria: 'Chọn nguồn bản đồ',
      insightsAria: 'Chọn nguồn khám phá',
      chatgptImported: 'Nhập lúc {time}',
      insightsChatgptEmpty:
        'Chưa có phân tích ChatGPT. Bấm ChatGPT ở góc phải để sao chép prompt và nhập kết quả.',
      forestChatgptEmpty:
        'Chưa có phân tích ChatGPT cho bản đồ. Bấm ChatGPT ở góc phải để thêm.',
      forestAiRelations: 'Liên kết gợi ý',
      forestAiUpdates: 'Ghi chú trên ghi nhận',
      forestAiApplied: 'Đã lưu {relations} liên kết · {updates} cập nhật khi nhập',
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
        'Write what’s on your mind — we’ll walk through 7 steps together: what happened, how you feel, what it means to you, what you believe, what matters, who you are in this, and what might come next.',
      placeholder: 'e.g. My child refuses to study and I worry about their future...',
      inputAria: 'Your thought',
      startBtn: 'Start reflection',
      aiAssistBtn: 'Reflect with ChatGPT',
      modePickerAria: 'Choose reflection mode',
      modeInApp: 'Reflect in app',
      modeInAppDesc: 'Gentle questions, right here in the app',
      modeChatGpt: 'With ChatGPT',
      modeChatGptDesc: 'Chat elsewhere, bring the result back',
      statEntries: 'Entries',
      statVerified: 'Established',
      statSessions: 'Sessions',
      resetText: 'Start completely fresh? Everything on this device will be deleted.',
      resetBtn: 'Clear and start over',
      shareFirst: 'Write a few lines first.',
      sessionStarted: 'Reflection started',
      dataReset: 'Data cleared. You can start fresh.',
      disclaimer:
        'A space for self-reflection — not professional care. If things feel overwhelming, please reach out for support.',
      privacy: 'Everything stays on your device.',
    },
    aiAssist: {
      badge: 'Via ChatGPT',
      title: 'Reflect with ChatGPT',
      intro:
        'Chat on ChatGPT, then bring the result back here — the app never sends your data on its own.',
      flowApp: 'App',
      flowChat: 'ChatGPT',
      flowBack: 'App',
      stepper1: 'Copy',
      stepper2: 'Chat',
      stepper3: 'Paste back',
      privacyBanner: 'Nothing leaves your device unless you copy it to ChatGPT yourself.',
      thoughtLabel: 'What’s on your mind',
      promptPreview: 'Opening message for ChatGPT',
      step1Title: 'Step 1 — Copy the opening',
      step1Desc: 'Edit if you like, then copy the text below into ChatGPT.',
      step1Next: 'Copied',
      step2Title: 'Step 2 — Chat',
      step2Desc: 'Answer one question at a time. When it feels enough, move on.',
      step2Next: 'Done chatting',
      step3Title: 'Step 3 — Bring it back',
      step3Desc: 'Copy the closing message into the chat, then paste what ChatGPT returns below.',
      stepBack: 'Back',
      openChatGpt: 'Open ChatGPT ↗',
      exportPromptToggle: 'Closing message (to get the result)',
      pasteHint: 'Paste here, then tap Preview',
      copy: 'Copy',
      copyExport: 'Copy closing message',
      copyDone: 'Copied',
      importLabel: 'Result from ChatGPT',
      importPlaceholder: 'Paste what ChatGPT returned (usually JSON)...',
      importBtn: 'Save to app',
      previewBtn: 'Preview',
      previewTitle: 'Before saving',
      previewDesc: 'Review the 7 steps. Green tags are extra suggestions from the app.',
      previewBack: 'Edit',
      confirmImport: 'Save',
      previewFromAi: 'From ChatGPT',
      previewFromRule: 'App suggests',
      previewBiases: 'Thinking patterns',
      previewEmptyStep: '—',
      previewInvalid: 'Couldn’t read that — check what you pasted.',
      previewInvalidHint: 'Hint: {hint}',
      previewStats: '{ai} from ChatGPT · {rule} app suggestions · {steps}/7 steps',
      previewStatsTranscript: 'Will save {n} chat turns',
      previewWarnManyEmpty: 'Quite a few steps are empty — you may want to chat a bit more.',
      previewWarnNoInterpretation: 'Missing how you understand the situation.',
      previewWarnNoEmotions: 'Missing emotions.',
      transcriptToggle: 'Chat log (optional)',
      transcriptDesc:
        'Paste User: / ChatGPT: lines to keep the real conversation. Leave blank to save only the summary.',
      transcriptPlaceholder: 'User: ...\nChatGPT: ...',
      contextRefreshed: 'Updated with your latest data',
      contextNote: 'Prompt data refreshed at {time}',
      matchApply: 'Will save',
      matchFuzzy: 'Close match',
      matchMiss: 'Not found',
      previewForestStats: 'Links: {apply}/{total} · Updates: {updates}/{totalUpdates}',
      previewInsightsStats: '{n} tensions · {e} prompts · {new} new insights',
      previewTimelineStats: '{m} milestones · {v} value shifts',
      warnForestMiss: '{n} links didn’t match — fix names below or skip on save.',
      warnForestFuzzy: '{n} items are close matches — review before saving.',
      warnInsightsOverlap: '{n} tensions overlap with what the app already noticed.',
      matchResolvedAs: '→ matches “{label}”',
      editLabelHint: 'Edit names if needed, then Preview again',
      jsonHintNoObject: 'No JSON data found',
      jsonHintInvalidShape: 'Structure doesn’t match this screen',
      importedNote: '(From ChatGPT session)',
      eeibviaSummaryTitle: '7-step summary',
      recordedInMap: 'Saved to your thought map. When ready, open {marker}.',
      sessionEndPlain: 'Thank you for sharing. Saved to your thought map.',
      reframeLabel: 'Another view',
      smallStepLabel: 'Small step',
      copied: 'Copied',
      copyFailed: 'Couldn’t copy — please select and copy manually',
      importEmpty: 'Paste the result from ChatGPT first.',
      importInvalid: 'Couldn’t read the result. Try pasting again after the closing message.',
      importMissingEvent: 'Missing what happened — finish the steps and export again.',
      importSuccess: 'Saved — open Reflect or Explore',
      needThought: 'Write a few lines before copying.',
    },
    aiScreen: {
      triggerForest: 'ChatGPT',
      triggerInsights: 'ChatGPT',
      triggerTimeline: 'ChatGPT',
      title_insights: 'Go deeper',
      title_forest: 'Read your map',
      title_timeline: 'Your journey',
      desc_insights:
        'Copy the text below — with your entries — so ChatGPT can suggest tensions, patterns, and questions to sit with.',
      desc_forest:
        'Copy with your current map so ChatGPT can suggest links and themes by life area.',
      desc_timeline:
        'Copy with your timeline so ChatGPT can help you see turning points and shifting values.',
      stepper1: 'Copy',
      stepper3: 'Paste back',
      step1Next: 'Copied',
      step2Desc: 'Talk it through on ChatGPT. When ready, go to the last step.',
      step2Next: 'Last step',
      analysisPrompt: 'Analysis text (includes your data)',
      exportPrompt: 'Closing message (to get the result)',
      needData: 'Add a few entries first — reflect or import from ChatGPT.',
      previewEmpty: 'Nothing to save.',
      fromChatGpt: 'ChatGPT',
      nodeNote: 'Note from ChatGPT',
      bannerInsights: 'From ChatGPT',
      bannerForest: 'Map notes',
      bannerTimeline: 'Journey story',
      patterns: 'Recurring patterns',
      preview_summary: 'Summary',
      preview_contradictions: 'Tensions',
      preview_exploration: 'Questions to sit with',
      preview_biases: 'Thinking patterns',
      preview_patterns: 'Patterns',
      preview_relations: 'Links',
      preview_nodeUpdates: 'Entry updates',
      preview_treeInsights: 'By branch',
      preview_narrative: 'Journey',
      preview_milestones: 'Milestones',
      preview_valueShifts: 'Value shifts',
      preview_reflection: 'Reflection question',
      importSuccess_insights: 'Explore updated',
      importSuccess_forest: 'Map updated',
      importSuccess_timeline: 'Timeline updated',
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
      empty: 'No session yet.',
      emptyHint: 'Start from Home.',
      you: 'You',
      guide: 'Guide',
      shareMore: 'Anything else on your mind?',
      openingDefault: 'Sounds like this touches something in you. How do you feel?',
      openingWithThought:
        'You’re talking about “{thought}”. How is that landing for you?',
      emotionWithEvent: 'When you think about "{event}", which feeling stands out most?',
      interpretationWithEmotion: 'When you feel {emotion}, what do you worry might happen?',
      beliefPrompt: 'What makes you believe that — can you say a bit more?',
      sessionEnd:
        'Thank you for sharing. Saved to your thought map — open Explore when you want to look deeper.',
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
      editMessage: 'Edit message',
      saveEdit: 'Save',
      cancelEdit: 'Cancel',
      editedLabel: 'edited',
      messageUpdated: 'Updated to match your edit',
      editEmpty: 'Can’t be empty',
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
      desc: 'Recurring patterns and places where your thoughts pull in two directions',
      today: '🔍 Today',
      todayEmpty: 'Nothing new today yet. One reflection session helps.',
      new: 'NEW',
      topBeliefs: '💡 Top beliefs',
      beliefsEmpty: 'No beliefs recorded yet.',
      topValues: '🌟 Top values',
      valuesEmpty: 'No values recorded yet.',
      contradictions: '⚡ Pulling two ways',
      contradictionsEmpty: 'No clear tension yet. Keep reflecting — it often shows up over time.',
      biases: '🧩 Skewed thinking patterns',
      biasesEmpty: 'Nothing clear yet. Sharing more helps you see sharper.',
      biasDefault: 'This pattern may shape how you read what happens.',
      disclaimer: 'For reflection only — not a conclusion or diagnosis.',
      contradictionPrefix: 'You might be',
      contradictionsNote: 'This may partly come from circumstances — not only from you.',
      exploration: '💭 Questions to sit with',
      explorationEmpty: 'Reflect more to get questions matched to what you’ve written.',
      explorationCta: 'Reflect more',
      explorationFilled: 'Added to Home — edit if you like, then start',
    },
    timeline: {
      aria: 'Timeline',
      title: 'Timeline',
      desc: 'How your thoughts and values shift over time',
      empty: 'Shows up once you start reflecting and recording more.',
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
      simulating: 'Simulating',
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
      dialogueHint:
        'Edit replies below, then Simulate or Re-run to see how entries change (e.g. add “ask the team for help” in Action).',
      resetDialogue: 'Restore original',
      rerunNoReset: 'Re-run (no reset)',
      dialogueEdited: 'Edited',
      dialogueRestored: 'Dialogue restored to original',
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
    screenView: {
      app: 'From app',
      chatgpt: 'ChatGPT',
      forestAria: 'Choose map source',
      insightsAria: 'Choose explore source',
      chatgptImported: 'Imported at {time}',
      insightsChatgptEmpty:
        'No ChatGPT analysis yet. Tap ChatGPT (top right) to copy a prompt and import results.',
      forestChatgptEmpty:
        'No ChatGPT map analysis yet. Tap ChatGPT (top right) to add one.',
      forestAiRelations: 'Suggested links',
      forestAiUpdates: 'Notes on entries',
      forestAiApplied: 'Saved {relations} links · {updates} updates on import',
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

const I18N_EXPLORATION_PROMPTS = {
  vi: {
    family_work: {
      source: 'Giá trị & hành động',
      prompt:
        'Giá trị và hành động đang lệch nhau — một việc nhỏ tuần này bạn có thể làm để thể hiện điều quan trọng với bạn là gì, dù chỉ 15 phút?',
      seedThought:
        'Tôi coi trọng gia đình nhưng thời gian làm việc vẫn chiếm rất nhiều. Tuần này tôi có thể làm gì nhỏ để dành thêm cho người thân?',
    },
    health_burnout: {
      source: 'Sức khỏe & nhịp sống',
      prompt:
        'Nếu sức khỏe thực sự quan trọng, một thay đổi nhỏ trong 24 giờ tới bạn có thể thử là gì — ngủ sớm hơn, nghỉ giữa giờ, hay nói không một việc?',
      seedThought:
        'Tôi biết sức khỏe quan trọng nhưng nhịp sống hiện tại đang làm tôi mệt. Trong 24 giờ tới, một việc nhỏ tôi có thể làm để chăm sóc bản thân là gì?',
    },
    work_life_balance: {
      source: 'Cân bằng cuộc sống',
      prompt:
        'Điều gì khiến bạn chưa dám đặt ranh giới với công việc? Thử viết một câu bạn có thể nói với sếp hoặc đồng nghiệp.',
      seedThought:
        'Tôi mong có sự cân bằng nhưng vẫn làm rất nhiều giờ. Điều gì khiến tôi chưa dám đặt ranh giới — và tôi có thể nói gì với sếp hoặc team?',
    },
    development_pressure: {
      source: 'Phát triển & áp lực',
      prompt:
        'Nếu mục tiêu là giúp người khác phát triển, cách nào vừa đặt kỳ vọng vừa giữ được kết nối — thay vì chỉ gây áp lực?',
      seedThought:
        'Tôi muốn người thân phát triển tốt nhưng đôi khi phản ứng của tôi có vẻ tạo áp lực. Tôi có thể thử cách nào vừa quan tâm vừa không ép buộc?',
    },
    control_freedom: {
      source: 'Tự do & kiểm soát',
      prompt:
        'Ở đâu ranh giới giữa “bảo vệ” và “kiểm soát”? Bạn có thể tin tưởng thêm một chút vào ai — kể cả bản thân?',
      seedThought:
        'Tôi coi trọng tự do nhưng đôi khi muốn kiểm soát mọi thứ. Trong tình huống gần đây, tôi đang bảo vệ hay đang kiểm soát?',
    },
    belief_obedience: {
      source: 'Niềm tin về con cái',
      prompt:
        '“Nghe lời” và “tự lập” có thể cùng tồn tại không? Một quy tắc mới trong nhà bạn muốn thử là gì?',
      seedThought:
        'Tôi tin con cần nghe lời nhưng cũng muốn con tự lập. Làm sao để vừa dạy con kỷ luật vừa tôn trọng tiếng nói của con?',
    },
    money_family: {
      source: 'Tiền bạc & quan hệ',
      prompt:
        'Nếu không chỉ đo bằng tiền, “đủ” với bạn trông như thế nào trong quan hệ gia đình tuần này?',
      seedThought:
        'Tôi thường gắn an toàn với tiền bạc, nhưng quan hệ gia đình cũng rất quan trọng. Tuần này tôi có thể đầu tư thời gian thay vì chỉ lo kiếm tiền không?',
    },
    bias_catastrophizing: {
      source: 'Kiểu suy nghĩ: tồi tệ nhất',
      prompt:
        'Ngoài kịch bản tồi nhất, còn hai kịch bản khác có thể xảy ra là gì — một trung bình và một khả quan hơn?',
      seedThought:
        'Tôi hay nghĩ đến chuyện tồi tệ nhất. Nếu nhìn lại tình huống gần đây, còn cách hiểu nào khác ngoài kết quả xấu nhất?',
    },
    bias_should: {
      source: 'Quy tắc “phải/nên”',
      prompt:
        'Câu “tôi phải…” nào đang áp lực nhất? Thử đổi thành “tôi muốn…” hoặc “tôi chọn…” — cảm giác có khác không?',
      seedThought:
        'Tôi có nhiều quy tắc “phải” và “nên” trong đầu. Quy tắc nào đang tạo áp lực lớn nhất — và nếu coi đó là lựa chọn thì sao?',
    },
    bias_overgeneralization: {
      source: 'Kết luận cho mọi trường hợp',
      prompt:
        'Có ngoại lệ nào — dù nhỏ — cho câu “luôn luôn / không bao giờ” bạn vừa nghĩ không?',
      seedThought:
        'Tôi hay dùng “luôn” hoặc “không bao giờ” khi nghĩ về mình hoặc người khác. Có lần nào điều đó không đúng hoàn toàn?',
    },
    bias_mind_reading: {
      source: 'Đoán ý người khác',
      prompt:
        'Bạn chưa hỏi trực tiếp điều gì mà đang tự đoán? Một câu hỏi bạn có thể hỏi thay vì đoán là gì?',
      seedThought:
        'Tôi thường đoán người khác đang nghĩ gì mà chưa hỏi. Trong tình huống gần đây, tôi có thể hỏi thẳng điều gì?',
    },
    general_belief: {
      source: 'Niềm tin nổi bật',
      prompt:
        'Niềm tin “{belief}” đang giúp hay cản bạn? Nếu nới lỏng một chút, điều gì có thể thay đổi?',
      seedThought:
        'Tôi thường tin rằng {belief}. Niềm tin này đang ảnh hưởng đến cách tôi hành động thế nào — và tôi có muốn giữ nguyên không?',
    },
  },
  en: {
    family_work: {
      source: 'Values & actions',
      prompt:
        'Your values and actions seem misaligned — what is one small thing this week, even 15 minutes, that could show what matters to you?',
      seedThought:
        'Family matters to me but work still takes most of my time. What is one small thing I could do this week for someone I love?',
    },
    health_burnout: {
      source: 'Health & pace of life',
      prompt:
        'If health truly matters, what tiny change in the next 24 hours could you try — sleep earlier, a break, or saying no to one task?',
      seedThought:
        'I know health matters but my current pace exhausts me. What is one small thing I can do in the next 24 hours to care for myself?',
    },
    work_life_balance: {
      source: 'Work–life balance',
      prompt:
        'What makes it hard to set boundaries at work? Try writing one sentence you could say to your manager or team.',
      seedThought:
        'I want balance but still work very long hours. What stops me from setting boundaries — and what could I say to my manager or team?',
    },
    development_pressure: {
      source: 'Growth & pressure',
      prompt:
        'If the goal is to help someone grow, how can you hold expectations and stay connected — instead of only applying pressure?',
      seedThought:
        'I want my loved ones to grow but my reactions sometimes feel pressuring. How can I care without forcing?',
    },
    control_freedom: {
      source: 'Freedom & control',
      prompt:
        'Where is the line between protecting and controlling? Could you trust someone a little more — including yourself?',
      seedThought:
        'I value freedom but sometimes want to control everything. In a recent situation, was I protecting or controlling?',
    },
    belief_obedience: {
      source: 'Beliefs about children',
      prompt:
        'Can “obedience” and “independence” coexist? What is one new household rule you might try?',
      seedThought:
        'I believe children should listen but I also want them independent. How can I teach discipline while respecting their voice?',
    },
    money_family: {
      source: 'Money & relationships',
      prompt:
        'If “enough” is not only measured in money, what would it look like in your family relationships this week?',
      seedThought:
        'I often tie safety to money, but family relationships matter too. Can I invest time this week, not only effort at work?',
    },
    bias_catastrophizing: {
      source: 'Pattern: worst-case thinking',
      prompt:
        'Besides the worst case, what are two other outcomes — one middling and one more hopeful?',
      seedThought:
        'I often imagine the worst outcome. Looking at a recent situation, what other interpretations are possible?',
    },
    bias_should: {
      source: 'Rigid “must/should” rules',
      prompt:
        'Which “I must…” sentence feels heaviest? Try rewriting it as “I want…” or “I choose…” — does it feel different?',
      seedThought:
        'I carry many “must” and “should” rules. Which one pressures me most — and what if I treated it as a choice?',
    },
    bias_overgeneralization: {
      source: 'All-or-every-time conclusions',
      prompt:
        'Is there any exception — however small — to the “always / never” thought you just had?',
      seedThought:
        'I often use “always” or “never” about myself or others. When was that not completely true?',
    },
    bias_mind_reading: {
      source: 'Assuming others’ thoughts',
      prompt:
        'What are you assuming without asking? What is one direct question you could ask instead?',
      seedThought:
        'I often guess what others think without asking. In a recent situation, what could I ask directly?',
    },
    general_belief: {
      source: 'Top belief',
      prompt:
        'Is the belief “{belief}” helping or limiting you? If you loosened it slightly, what might change?',
      seedThought:
        'I often believe that {belief}. How does this shape my actions — and do I want to keep it as is?',
    },
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

  explorationPrompt(id, vars = {}) {
    const raw = I18N_EXPLORATION_PROMPTS[this.locale]?.[id];
    if (!raw) return null;
    const sub = (text) =>
      String(text || '').replace(/\{(\w+)\}/g, (_, k) =>
        vars[k] != null ? vars[k] : `{${k}}`
      );
    return {
      id,
      source: sub(raw.source),
      prompt: sub(raw.prompt),
      seedThought: sub(raw.seedThought),
    };
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
    const legacy = ['Góc khám phá', 'Explore'];
    return (
      content.includes(I18N_MESSAGES.vi.reflection.sessionEndMarker) ||
      content.includes(I18N_MESSAGES.en.reflection.sessionEndMarker) ||
      legacy.some((m) => content.includes(m))
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
    if (/^["「]/.test(trimmed) || /mâu thuẫn với/i.test(trimmed) || /^Niềm tin đối lập/i.test(trimmed)) {
      return trimmed.endsWith('.') ? trimmed : `${trimmed}.`;
    }
    const lower = trimmed.charAt(0).toLowerCase() + trimmed.slice(1);
    const body = lower.replace(/\.$/, '');
    return `${this.t('insights.contradictionPrefix')} ${body}.`;
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
