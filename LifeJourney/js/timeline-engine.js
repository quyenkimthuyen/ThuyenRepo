/**
 * Life journey timeline management.
 */
const TimelineEngine = (() => {
  function createEntry({ event, stageId, thought, emotion, emotionCustom, decision, consequences, reflection, patterns, simulation }) {
    return {
      id: `entry-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      eventId: event.id,
      stage: stageId,
      eventDescription: event.description,
      category: event.category,
      thought,
      emotion: emotionCustom || emotion,
      decision,
      consequences,
      reflection,
      patterns,
      simulation: !!simulation,
      timestamp: new Date().toISOString(),
    };
  }

  function sortByDate(timeline, ascending = false) {
    return [...timeline].sort((a, b) => {
      const da = new Date(a.timestamp).getTime();
      const db = new Date(b.timestamp).getTime();
      return ascending ? da - db : db - da;
    });
  }

  function getByStage(timeline, stageId) {
    return timeline.filter((e) => e.stage === stageId);
  }

  function getEntry(timeline, entryId) {
    return timeline.find((e) => e.id === entryId);
  }

  function getStageProgress(timeline, stages) {
    const progress = {};
    for (const stage of stages) {
      const entries = getByStage(timeline, stage.id);
      const realEntries = entries.filter((e) => !e.simulation);
      progress[stage.id] = {
        total: entries.length,
        real: realEntries.length,
        simulated: entries.length - realEntries.length,
      };
    }
    return progress;
  }

  function formatEntrySummary(entry, lang) {
    const desc = entry.eventDescription?.[lang] || entry.eventDescription?.en || '';
    const date = new Date(entry.timestamp).toLocaleDateString(lang === 'vi' ? 'vi-VN' : 'en-US');
    return { desc, date, emotion: entry.emotion, thought: entry.thought };
  }

  return {
    createEntry,
    sortByDate,
    getByStage,
    getEntry,
    getStageProgress,
    formatEntrySummary,
  };
})();
