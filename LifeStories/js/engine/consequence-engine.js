function createConsequenceQueue() {
  return [];
}

function scheduleConsequences(queue, choice, currentSceneIndex) {
  if (!choice.delayedConsequences) return;
  choice.delayedConsequences.forEach(dc => {
    queue.push({
      triggerAtScene: currentSceneIndex + dc.triggerAfterScenes,
      effects: dc.effects,
      message: dc.message || null,
      fired: false,
    });
  });
}

function checkDelayedConsequences(queue, currentSceneIndex, state) {
  const triggered = [];
  queue.forEach(item => {
    if (!item.fired && currentSceneIndex >= item.triggerAtScene) {
      item.fired = true;
      const relChanges = applyRelationshipEffects(state, item.effects?.relationships);
      if (item.effects?.personality) {
        applyPersonalityEffects(state, item.effects.personality);
      }
      triggered.push({
        message: item.message,
        relationshipChanges: relChanges,
      });
    }
  });
  return triggered;
}

function applyImmediateEffects(state, choice) {
  const relChanges = applyRelationshipEffects(state, choice.effects?.relationships);
  if (choice.effects?.personality) {
    applyPersonalityEffects(state, choice.effects.personality);
  }
  if (choice.tags) {
    applyTags(state, choice.tags);
  }
  return relChanges;
}
