/**
 * Event selection and consequence generation engine.
 */
const EventEngine = (() => {
  let eventsData = null;

  const DECISION_OUTCOMES = {
    talk: {
      en: {
        immediate: [
          'Opening up brought some relief, though the conversation did not solve everything.',
          'Someone listened, and you felt slightly less alone with the situation.',
          'Sharing your view clarified what you actually want — even if others disagreed.',
        ],
        later: [
          'This conversation became a reference point when similar tensions appeared.',
          'Trust in that relationship shifted — sometimes closer, sometimes more cautious.',
          'You noticed you reach for dialogue more often after this experience.',
        ],
      },
      vi: {
        immediate: [
          'Chia sẻ giúp bạn nhẹ bớt phần nào, dù chưa giải quyết hết vấn đề.',
          'Có người lắng nghe khiến bạn bớt cô đơn với tình huống này.',
          'Nói ra suy nghĩ giúp bạn hiểu rõ hơn điều mình muốn — dù người khác có thể không đồng ý.',
        ],
        later: [
          'Cuộc trò chuyện này trở thành điểm tham chiếu khi căng thẳng tương tự xuất hiện.',
          'Niềm tin vào mối quan hệ đó thay đổi — đôi khi gần hơn, đôi khi thận trọng hơn.',
          'Bạn nhận ra mình thường tìm đến đối thoại hơn sau trải nghiệm này.',
        ],
      },
    },
    wait: {
      en: {
        immediate: [
          'Pausing gave you space, but uncertainty lingered in the background.',
          'Nothing dramatic happened — the situation stayed unresolved for now.',
          'Observation revealed details you had missed in the first reaction.',
        ],
        later: [
          'Waiting too long sometimes cost you a window of opportunity.',
          'Patience helped you respond more thoughtfully when you finally acted.',
          'A similar situation later showed whether waiting is your default pattern.',
        ],
      },
      vi: {
        immediate: [
          'Tạm dừng cho bạn không gian, nhưng sự không chắc chắn vẫn còn đó.',
          'Không có gì kịch tính xảy ra — tình huống vẫn chưa được giải quyết.',
          'Quan sát cho thấy những chi tiết bạn bỏ lỡ trong phản ứng ban đầu.',
        ],
        later: [
          'Chờ đợi quá lâu đôi khi khiến bạn lỡ mất cơ hội.',
          'Kiên nhẫn giúp bạn phản ứng chu đáo hơn khi cuối cùng hành động.',
          'Tình huống tương tự sau này cho thấy chờ đợi có phải khuôn mẫu mặc định của bạn không.',
        ],
      },
    },
    act: {
      en: {
        immediate: [
          'Taking action shifted the dynamic — not always in the direction you expected.',
          'You felt a mix of relief and doubt right after moving forward.',
          'Your decision had visible effects, and others reacted in different ways.',
        ],
        later: [
          'The outcome of this action influenced how confident you feel about future risks.',
          'Some consequences only became clear weeks later.',
          'You learned whether acting quickly fits this type of situation for you.',
        ],
      },
      vi: {
        immediate: [
          'Hành động thay đổi động thái tình huống — không phải lúc nào cũng như bạn mong đợi.',
          'Bạn cảm thấy vừa nhẹ nhõm vừa nghi ngờ ngay sau khi bước tiếp.',
          'Quyết định có tác động rõ ràng, và mọi người phản ứng khác nhau.',
        ],
        later: [
          'Kết quả của hành động này ảnh hưởng đến sự tự tin khi đối mặt rủi ro sau này.',
          'Một số hệ quả chỉ rõ ràng vài tuần sau.',
          'Bạn học được liệu hành động nhanh có phù hợp với kiểu tình huống này không.',
        ],
      },
    },
    reflect: {
      en: {
        immediate: [
          'Time alone helped you sort feelings from facts — partially.',
          'Reflection softened the intensity of your first reaction.',
          'You wrote or thought through options without committing yet.',
        ],
        later: [
          'Insights from this reflection appeared in how you handled the next challenge.',
          'Sometimes reflection became a way to delay uncomfortable action.',
          'You recognized a recurring theme in what keeps bothering you.',
        ],
      },
      vi: {
        immediate: [
          'Thời gian một mình giúp bạn tách cảm xúc khỏi sự thật — một phần.',
          'Suy ngẫm làm dịu bớt cường độ phản ứng ban đầu.',
          'Bạn cân nhắc các lựa chọn mà chưa cam kết điều gì.',
        ],
        later: [
          'Hiểu biết từ lần suy ngẫm này xuất hiện khi bạn đối mặt thử thách tiếp theo.',
          'Đôi khi suy ngẫm trở thành cách trì hoãn hành động khó chịu.',
          'Bạn nhận ra chủ đề lặp lại trong những gì vẫn làm bạn băn khoăn.',
        ],
      },
    },
    avoid: {
      en: {
        immediate: [
          'Avoiding brought short-term comfort and a subtle sense of unfinished business.',
          'The situation did not escalate — but it also did not improve.',
          'You felt temporary relief, with a quiet question about what you left behind.',
        ],
        later: [
          'Avoidance reduced immediate stress but the underlying issue resurfaced.',
          'You noticed a pattern of stepping back when conflict feels likely.',
          'A future event tested whether avoidance still feels like the safest option.',
        ],
      },
      vi: {
        immediate: [
          'Tránh né mang lại thoải mái tạm thời và cảm giác việc chưa trọn vẹn.',
          'Tình huống không leo thang — nhưng cũng không cải thiện.',
          'Bạn thấy nhẹ nhõm trong chốc lát, kèm câu hỏi về điều mình bỏ lại phía sau.',
        ],
        later: [
          'Tránh né giảm căng thẳng trước mắt nhưng vấn đề gốc tái diện.',
          'Bạn nhận ra khuôn mẫu lùi lại khi cảm thấy xung đột có thể xảy ra.',
          'Sự kiện sau này kiểm tra xem tránh né vẫn có vẻ là lựa chọn an toàn nhất không.',
        ],
      },
    },
    custom: {
      en: {
        immediate: [
          'Your chosen path had mixed results — some expected, some surprising.',
          'The situation evolved in ways that reflected your unique approach.',
          'Others responded to your decision in ways you had not fully anticipated.',
        ],
        later: [
          'This custom choice revealed something about your values under pressure.',
          'You compared this outcome with what preset options might have brought.',
          'The experience added nuance to how you define a "good" decision.',
        ],
      },
      vi: {
        immediate: [
          'Con đường bạn chọn có kết quả hỗn hợp — vừa đoán được, vừa bất ngờ.',
          'Tình huống thay đổi theo cách phản ánh cách tiếp cận riêng của bạn.',
          'Người khác phản ứng theo cách bạn chưa hoàn toàn lường trước.',
        ],
        later: [
          'Lựa chọn riêng này bộc lộ điều gì đó về giá trị của bạn khi chịu áp lực.',
          'Bạn so sánh kết quả với những gì các lựa chọn có sẵn có thể mang lại.',
          'Trải nghiệm làm phong phú thêm cách bạn định nghĩa quyết định "tốt".',
        ],
      },
    },
  };

  async function loadEvents() {
    if (eventsData) return eventsData;
    const res = await fetch('./data/events.json');
    if (!res.ok) throw new Error(`Failed to load events: ${res.status}`);
    eventsData = await res.json();
    return eventsData;
  }

  function getStages() {
    return eventsData?.stages || [];
  }

  function getEventsForStage(stageId) {
    if (!eventsData) return [];
    return eventsData.events.filter((e) => e.stage === stageId);
  }

  function pickEvent(stageId, usedEventIds = []) {
    const pool = getEventsForStage(stageId);
    if (pool.length === 0) return null;

    const unused = pool.filter((e) => !usedEventIds.includes(e.id));
    const source = unused.length > 0 ? unused : pool;
    const idx = Math.floor(Math.random() * source.length);
    return source[idx];
  }

  function pickFrom(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  function generateConsequences(event, lang, decisionId = 'wait') {
    const decisionOutcomes = DECISION_OUTCOMES[decisionId] || DECISION_OUTCOMES.wait;
    const localized = decisionOutcomes[lang] || decisionOutcomes.en;

    const eventImmediate = event.immediateOutcomes[lang] || event.immediateOutcomes.en;
    const eventLater = event.laterOutcomes[lang] || event.laterOutcomes.en;

    const blendImmediate = Math.random() > 0.4;
    return {
      immediate: blendImmediate ? pickFrom(localized.immediate) : pickFrom(eventImmediate),
      later: pickFrom(localized.later.length ? localized.later : eventLater),
      decisionId,
    };
  }

  function getDecisionOptions(lang) {
    if (lang === 'vi') {
      return [
        { id: 'talk', label: 'Tìm người để trò chuyện' },
        { id: 'wait', label: 'Chờ và quan sát thêm' },
        { id: 'act', label: 'Hành động ngay' },
        { id: 'reflect', label: 'Dành thời gian suy ngẫm một mình' },
        { id: 'avoid', label: 'Tránh né tình huống' },
        { id: 'custom', label: 'Tự viết quyết định của bạn' },
      ];
    }
    return [
      { id: 'talk', label: 'Find someone to talk to' },
      { id: 'wait', label: 'Wait and observe more' },
      { id: 'act', label: 'Take action immediately' },
      { id: 'reflect', label: 'Spend time reflecting alone' },
      { id: 'avoid', label: 'Avoid the situation' },
      { id: 'custom', label: 'Write your own decision' },
    ];
  }

  function getEmotions(lang) {
    if (lang === 'vi') {
      return [
        { id: 'angry', label: 'Tức giận' },
        { id: 'sad', label: 'Buồn' },
        { id: 'frustrated', label: 'Bực bội' },
        { id: 'curious', label: 'Tò mò' },
        { id: 'calm', label: 'Bình tĩnh' },
        { id: 'hopeful', label: 'Hy vọng' },
      ];
    }
    return [
      { id: 'angry', label: 'Angry' },
      { id: 'sad', label: 'Sad' },
      { id: 'frustrated', label: 'Frustrated' },
      { id: 'curious', label: 'Curious' },
      { id: 'calm', label: 'Calm' },
      { id: 'hopeful', label: 'Hopeful' },
    ];
  }

  function getEmotionLabel(emotionId, lang, custom = '') {
    if (custom?.trim()) return custom.trim();
    const found = getEmotions(lang).find((e) => e.id === emotionId);
    return found?.label || emotionId || '—';
  }

  function getStageProgress(usedEventIds, stageId) {
    const total = getEventsForStage(stageId).length;
    const used = usedEventIds.filter((id) => id.startsWith(`stage${stageId}-`)).length;
    return { total, used, remaining: Math.max(0, total - used) };
  }

  return {
    loadEvents,
    getStages,
    getEventsForStage,
    pickEvent,
    generateConsequences,
    getDecisionOptions,
    getEmotions,
    getEmotionLabel,
    getStageProgress,
  };
})();
