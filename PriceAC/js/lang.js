const i18n = (() => {
  const translations = {
    en: {
      eyebrow_market: "Market Awareness Tool",
      title_app: "Market Psychology Map",
      zen_btn: "🧘 Zen Mode",
      zen_btn_active: "🧘 Zen Active",
      status_pill: "Educational",
      
      // Nav
      nav_market: "Market",
      nav_psychology: "Psychology",
      nav_journal: "Journal",
      nav_bias: "Bias",
      nav_settings: "Settings",

      // Dashboard
      dashboard_sentiment: "Market Sentiment",
      dashboard_sentiment_sub: "Probabilistic context, not advice",
      dashboard_emotion: "User Emotion",
      dashboard_emotion_sub: "Based on saved notes",
      dashboard_bias: "Bias Summary",
      dashboard_bias_sub: "Educational reflection",
      dashboard_notes: "Recent Notes",
      dashboard_notes_sub: "Journal entries",
      no_journal: "No journal yet",
      learning_mode: "Learning mode",

      // Zen panel
      zen_title: "Price-Unbiased Reflection Active",
      zen_desc: '"The market is a voting machine in the short run, but a weighing machine in the long run. Master your mind before you master your trades."',
      zen_shortcut_btn: "Write Unbiased Reflection",

      // Price panel
      price_eyebrow: "Market",
      price_title: "Price Observation",
      chart_note: "Use drag and pinch/scroll to pan or zoom. Crosshair is enabled when Lightweight Charts loads.",

      // Map panel
      map_eyebrow: "Map",
      map_title: "Market Psychology Map",

      // Cycle
      cycle_eyebrow: "Cycle",
      cycle_title: "Psychology Progress Path",
      cycle_desc: "The app shows possible zones and supporting signals. It does not identify a definite market phase.",
      possible_zone: "Possible Zone",

      // Engine
      engine_eyebrow: "Engine",
      engine_title: "Probability View",

      // Socratic Form
      journal_eyebrow: "Journal",
      journal_title: "Socratic Decision Reflection",
      form_date: "Date",
      form_asset: "Asset",
      form_action: "Intended Action",
      form_emotion: "Current Emotion",
      form_confidence: "Confidence Level",
      form_belief_lbl: "1. Core Belief / Thesis",
      form_belief_help: "What makes you believe this?",
      form_belief_placeholder: "e.g. I believe BTC will surge because of steady ETF inflows.",
      form_reasoning_lbl: "2. Reasoning & Logical Rationale",
      form_reasoning_help: "Specific arguments or analysis supporting your belief.",
      form_reasoning_placeholder: "e.g. Declining exchange reserves combined with falling interest rates...",
      form_evidence_lbl: "3. Supporting Evidence",
      form_evidence_help: "What factual evidence supports your view?",
      form_evidence_placeholder: "e.g. On-chain data shows whale accumulation, upcoming FED meeting support.",
      form_counter_lbl: "4. Counter-Evidence (Mandatory check)",
      form_counter_help: "What evidence is against your belief? (Helps combat Confirmation Bias)",
      form_counter_placeholder: "e.g. Higher than expected inflation index or ETF outflows. Do not leave empty.",
      form_fail_lbl: "5. Pre-Mortem: What if you are wrong?",
      form_fail_help: "If you are wrong, what is the likely reason?",
      form_fail_placeholder: "e.g. Stop loss trigger at $90,000 support level...",
      form_save_btn: "Save Socratic Reflection",

      // History
      history_eyebrow: "Reflection",
      history_title: "Awareness History",
      history_search_placeholder: "Search beliefs, assets, emotions, actions...",
      empty_state: "No journal entries yet. Save a reflection to begin.",

      // Bias Screen
      bias_eyebrow: "Cognitive Bias",
      bias_title: "Bias Reflection Radar",
      bias_desc: "Bias analysis is educational and based on your Socratic inputs and confidence ratios.",
      
      // Insights
      insights_eyebrow: "Behavioral Insights",
      insights_title: "Long-term Cognitive Patterns",
      insight_fear_title: "Fear Sensitivity",
      insight_fear_empty: "No data yet. Log fear/panic entries to map price correlation.",
      insight_greed_title: "Greed Sensitivity",
      insight_greed_empty: "No data yet. Log greed/hope entries to map price correlation.",
      insight_buy_title: "Buy Motivations",
      insight_buy_empty: "Your primary reasons for buying will appear here.",
      insight_sell_title: "Sell Motivations",
      insight_sell_empty: "Your primary reasons for selling will appear here.",
      insight_score_title: "Socratic Rationale Score",
      insight_score_desc: "Balance Score (Counter-evidence logging frequency vs Overconfidence)",

      // Settings
      settings_eyebrow: "Settings",
      settings_title: "Application Notes",
      settings_purpose_lbl: "Purpose",
      settings_purpose_val: "Observe market psychology, personal emotion, and cognitive bias.",
      settings_advice_lbl: "Not Trading Advice",
      settings_advice_val: "No buy, sell, profit, or signal language is used.",
      settings_storage_lbl: "Storage",
      settings_storage_val: "Journal entries are stored locally in this browser with LocalStorage.",
      settings_clear_btn: "Clear Journal",

      // Impulsivity Shield
      shield_title: "Impulsivity Shield Active",
      shield_desc: "We detected high emotional intensity (FOMO/Panic) in your entry. Before saving, take a moment to calibrate your nervous system.",
      shield_prompt_inhale: "Inhale slowly...",
      shield_prompt_hold: "Hold breath...",
      shield_prompt_exhale: "Exhale slowly...",
      shield_abort: "Abort & Re-evaluate",
      shield_confirm: "Proceed to Save",
      shield_confirm_ready: "Confirm & Save Reflection",

      // Dynamic tags
      action_buy: "Buy",
      action_sell: "Sell",
      action_hold: "Hold",
      action_observe: "Observe",
      emotion_neutral: "Neutral",
      emotion_fear: "Fear",
      emotion_greed: "Greed",
      emotion_hope: "Hope",
      emotion_confidence: "Confidence",
      emotion_anxiety: "Anxiety",
      emotion_panic: "Panic",
      bias_warning_confirm: "Confirmation Bias Risk (No counter-evidence logged)",
      zen_mode_reflection: "🧘 Zen Mode Reflection",
      edit_btn: "Edit",
      delete_btn: "Delete",
      belief_line: "Belief",
      reasoning_line: "Reasoning",
      support_ev: "Supporting Evidence",
      against_ev: "Counter-Evidence",
      wrong_why: "If wrong, why",
      risk_low: "low risk",
      risk_medium: "medium risk",
      risk_high: "high risk",
      identified_logs: "Identified logs",
      bias_confirmation: "Confirmation Bias",
      bias_fomo: "FOMO",
      bias_loss_aversion: "Loss Aversion",
      bias_anchoring: "Anchoring Bias",
      bias_herd: "Herd Mentality",
      bias_recency: "Recency Bias",
      bias_overconfidence: "Overconfidence"
    },
    vi: {
      eyebrow_market: "Công cụ nhận thức thị trường",
      title_app: "Bản đồ tâm lý thị trường",
      zen_btn: "🧘 Chế độ Thiền",
      zen_btn_active: "🧘 Đang Thiền",
      status_pill: "Giáo dục",
      
      // Nav
      nav_market: "Thị trường",
      nav_psychology: "Tâm lý",
      nav_journal: "Nhật ký",
      nav_bias: "Thiên kiến",
      nav_settings: "Cài đặt",

      // Dashboard
      dashboard_sentiment: "Tâm lý thị trường",
      dashboard_sentiment_sub: "Bối cảnh xác suất, không phải lời khuyên",
      dashboard_emotion: "Cảm xúc cá nhân",
      dashboard_emotion_sub: "Dựa trên nhật ký đã lưu",
      dashboard_bias: "Thiên kiến nổi bật",
      dashboard_bias_sub: "Suy ngẫm giáo dục",
      dashboard_notes: "Ghi chép gần đây",
      dashboard_notes_sub: "Bản ghi nhật ký",
      no_journal: "Chưa có nhật ký",
      learning_mode: "Đang học hỏi",

      // Zen panel
      zen_title: "Đang kích hoạt Suy ngẫm phi giá cả",
      zen_desc: '"Thị trường trong ngắn hạn là một chiếc máy bỏ phiếu, nhưng trong dài hạn là một chiếc cân đo. Hãy làm chủ tâm trí trước khi làm chủ giao dịch của bạn."',
      zen_shortcut_btn: "Viết suy ngẫm phi giá cả",

      // Price panel
      price_eyebrow: "Thị trường",
      price_title: "Quan sát giá cả",
      chart_note: "Kéo hoặc cuộn bằng hai ngón tay để zoom/pan đồ thị. Hồng tâm tự động bật khi Lightweight Charts tải xong.",

      // Map panel
      map_eyebrow: "Bản đồ",
      map_title: "Bản đồ tâm lý thị trường",

      // Cycle
      cycle_eyebrow: "Chu kỳ",
      cycle_title: "Tiến trình tâm lý chu kỳ",
      cycle_desc: "Ứng dụng hiển thị các vùng có thể xảy ra và tín hiệu hỗ trợ. Nó không xác định một pha thị trường chắc chắn.",
      possible_zone: "Vùng khả thi",

      // Engine
      engine_eyebrow: "Động cơ",
      engine_title: "Xác suất tâm lý",

      // Socratic Form
      journal_eyebrow: "Nhật ký",
      journal_title: "Suy ngẫm quyết định Socratic",
      form_date: "Ngày",
      form_asset: "Tài sản",
      form_action: "Hành động dự kiến",
      form_emotion: "Cảm xúc hiện tại",
      form_confidence: "Mức độ tự tin",
      form_belief_lbl: "1. Niềm tin cốt lõi / Giả thuyết",
      form_belief_help: "Điều gì khiến bạn tin điều này?",
      form_belief_placeholder: "VD: Tôi tin BTC sẽ tăng mạnh vì dòng vốn ETF ròng ổn định.",
      form_reasoning_lbl: "2. Lập luận & Cơ sở Logic",
      form_reasoning_help: "Lập luận hay phân tích cụ thể hỗ trợ niềm tin của bạn.",
      form_reasoning_placeholder: "VD: Sự suy giảm nguồn cung trên sàn kết hợp với lãi suất giảm kích thích thanh khoản...",
      form_evidence_lbl: "3. Bằng chứng ủng hộ",
      form_evidence_help: "Bằng chứng thực tế nào ủng hộ nhận định của bạn?",
      form_evidence_placeholder: "VD: Dữ liệu on-chain cho thấy tích lũy của cá voi, tin tức hỗ trợ từ cuộc họp FED sắp tới.",
      form_counter_lbl: "4. Bằng chứng phản biện (Quan trọng)",
      form_counter_help: "Bằng chứng nào đang chống lại nhận định của bạn? (Giúp tránh Thiên kiến xác nhận)",
      form_counter_placeholder: "VD: Chỉ số lạm phát cao hơn dự kiến hoặc tháo chạy khỏi ETF. Đừng để trống.",
      form_fail_lbl: "5. Kịch bản thất bại: Nếu bạn sai, vì sao?",
      form_fail_help: "If you are wrong, what is the likely reason?",
      form_fail_placeholder: "VD: Điểm kích hoạt cắt lỗ ở mức hỗ trợ kỹ thuật $90,000...",
      form_save_btn: "Lưu suy ngẫm Socratic",

      // History
      history_eyebrow: "Suy ngẫm",
      history_title: "Lịch sử nhận thức",
      history_search_placeholder: "Tìm kiếm niềm tin, tài sản, cảm xúc, hành động...",
      empty_state: "Chưa có ghi chép nhật ký nào. Hãy lưu một suy ngẫm để bắt đầu.",

      // Bias Screen
      bias_eyebrow: "Thiên kiến nhận thức",
      bias_title: "Radar thiên kiến nhận thức",
      bias_desc: "Phân tích thiên kiến mang tính giáo dục, dựa trên các trường nhập Socratic và tỷ lệ tự tin của bạn.",
      
      // Insights
      insights_eyebrow: "Mô thức hành vi",
      insights_title: "Mô thức hành vi dài hạn",
      insight_fear_title: "Độ nhạy cảm với nỗi sợ",
      insight_fear_empty: "Chưa có dữ liệu. Hãy ghi chép cảm xúc sợ hãi/hoảng loạn để lập bản đồ tương quan giá cả.",
      insight_greed_title: "Độ nhạy cảm với lòng tham",
      insight_greed_empty: "Chưa có dữ liệu. Hãy ghi chép cảm xúc tham lam/hy vọng để lập bản đồ tương quan giá cả.",
      insight_buy_title: "Động cơ mua",
      insight_buy_empty: "Các lý do mua chủ yếu của bạn sẽ xuất hiện ở đây.",
      insight_sell_title: "Động cơ bán",
      insight_sell_empty: "Các lý do bán chủ yếu của bạn sẽ xuất hiện ở đây.",
      insight_score_title: "Điểm tư duy Socratic",
      insight_score_desc: "Điểm cân bằng lý thuyết (Tần suất ghi chép bằng chứng phản biện so với Sự tự tin quá mức)",

      // Settings
      settings_eyebrow: "Cài đặt",
      settings_title: "Ghi chú ứng dụng",
      settings_purpose_lbl: "Mục đích",
      settings_purpose_val: "Quan sát tâm lý thị trường, cảm xúc cá nhân và thiên kiến nhận thức.",
      settings_advice_lbl: "Không phải lời khuyên giao dịch",
      settings_advice_val: "Không sử dụng ngôn từ mua, bán, lợi nhuận hoặc tín hiệu.",
      settings_storage_lbl: "Lưu trữ",
      settings_storage_val: "Nhật ký được lưu trữ cục bộ trong trình duyệt này bằng LocalStorage.",
      settings_clear_btn: "Xóa tất cả nhật ký",

      // Impulsivity Shield
      shield_title: "Đang bật Khiên chắn bốc đồng",
      shield_desc: "Chúng tôi phát hiện cường độ cảm xúc cao (FOMO/Hoảng loạn) trong suy ngẫm của bạn. Trước khi lưu, hãy dành chút thời gian điều hòa hệ thần kinh của bạn.",
      shield_prompt_inhale: "Hít vào thật chậm...",
      shield_prompt_hold: "Nín thở...",
      shield_prompt_exhale: "Thở ra thật chậm...",
      shield_abort: "Hủy & Đánh giá lại",
      shield_confirm: "Tiếp tục Lưu",
      shield_confirm_ready: "Xác nhận & Lưu suy ngẫm",

      // Dynamic tags
      action_buy: "Mua",
      action_sell: "Bán",
      action_hold: "Nắm giữ",
      action_observe: "Quan sát",
      emotion_neutral: "Bình thường",
      emotion_fear: "Sợ hãi",
      emotion_greed: "Tham lam",
      emotion_hope: "Hy vọng",
      emotion_confidence: "Tự tin",
      emotion_anxiety: "Lo âu",
      emotion_panic: "Hoảng loạn",
      bias_warning_confirm: "Nguy cơ Thiên kiến xác nhận (Chưa ghi chép bằng chứng phản biện)",
      zen_mode_reflection: "🧘 Suy ngẫm phi giá cả (Thiền)",
      edit_btn: "Sửa",
      delete_btn: "Xóa",
      belief_line: "Niềm tin",
      reasoning_line: "Lập luận",
      support_ev: "Bằng chứng ủng hộ",
      against_ev: "Bằng chứng phản biện",
      wrong_why: "Nếu sai, lý do là",
      risk_low: "nguy cơ thấp",
      risk_medium: "nguy cơ trung bình",
      risk_high: "nguy cơ cao",
      identified_logs: "Số lần phát hiện",
      bias_confirmation: "Thiên kiến xác nhận",
      bias_fomo: "FOMO (Sợ bỏ lỡ)",
      bias_loss_aversion: "Sợ thua lỗ (Loss Aversion)",
      bias_anchoring: "Thiên kiến neo giữ (Anchoring)",
      bias_herd: "Tâm lý bầy đàn (Herd Mentality)",
      bias_recency: "Thiên kiến xu hướng gần đây (Recency)",
      bias_overconfidence: "Tự tin thái quá"
    }
  };

  let currentLang = localStorage.getItem("app-lang") || "en";

  const get = (key) => {
    return translations[currentLang][key] || key;
  };

  const setLang = (lang) => {
    if (translations[lang]) {
      currentLang = lang;
      localStorage.setItem("app-lang", lang);
      translatePage();
    }
  };

  const toggle = () => {
    const nextLang = currentLang === "en" ? "vi" : "en";
    setLang(nextLang);
    return nextLang;
  };

  const translatePage = () => {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      const text = get(key);
      if (text) {
        if (el.tagName === "INPUT" && el.placeholder !== undefined) {
          el.placeholder = text;
        } else if (el.tagName === "TEXTAREA" && el.placeholder !== undefined) {
          el.placeholder = text;
        } else {
          el.textContent = text;
        }
      }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.dataset.i18nPlaceholder;
      const text = get(key);
      if (text) {
        el.placeholder = text;
      }
    });

    const langBtn = document.querySelector("#lang-toggle");
    if (langBtn) {
      langBtn.textContent = currentLang === "en" ? "VI" : "EN";
    }

    if (window.JournalUI && typeof window.JournalUI.refresh === "function") {
      window.JournalUI.refresh();
    }
  };

  const getCurrentLang = () => currentLang;

  return {
    get,
    setLang,
    toggle,
    translatePage,
    getCurrentLang
  };
})();
