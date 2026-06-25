/**
 * Event selection and consequence generation engine.
 */
const EventEngine = (() => {
  let eventsData = null;

  async function loadEvents() {
    if (eventsData) return eventsData;
    const res = await fetch('./data/events.json');
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

  function generateConsequences(event, lang) {
    const immediate = event.immediateOutcomes[lang] || event.immediateOutcomes.en;
    const later = event.laterOutcomes[lang] || event.laterOutcomes.en;

    const immIdx = Math.floor(Math.random() * immediate.length);
    let latIdx = Math.floor(Math.random() * later.length);
    while (later.length > 1 && latIdx === immIdx) {
      latIdx = Math.floor(Math.random() * later.length);
    }

    return {
      immediate: immediate[immIdx],
      later: later[latIdx],
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

  return {
    loadEvents,
    getStages,
    getEventsForStage,
    pickEvent,
    generateConsequences,
    getDecisionOptions,
    getEmotions,
  };
})();
