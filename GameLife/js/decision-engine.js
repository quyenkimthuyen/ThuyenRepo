const DecisionEngine = {
  makeDecision(state, event, choice) {
    const decision = {
      day: state.day,
      eventId: event.id,
      eventText: event.text,
      choiceId: choice.id,
      choiceText: choice.text,
      tags: choice.tags || [],
      reflection: null
    };

    GameState.applyEffects(state.character, choice.immediate);

    ConsequenceEngine.schedule(state, choice.delayed, {
      text: choice.text,
      eventId: event.id
    });

    ConsequenceEngine.setFlags(state, choice.flags);

    state.decisions.push(decision);
    state.usedEventIds.push(event.id);

    GameState.addTimelineEntry(state, {
      type: 'decision',
      message: `Quyết định: "${choice.text}"`,
      eventText: event.text,
      effects: choice.immediate,
      choiceId: choice.id
    });

    if (choice.immediate) {
      const effectParts = Object.entries(choice.immediate)
        .filter(([, v]) => v !== 0)
        .map(([k, v]) => `${k} ${v > 0 ? '+' : ''}${v}`);
      if (effectParts.length) {
        GameState.addTimelineEntry(state, {
          type: 'immediate',
          message: `Tác động ngay: ${effectParts.join(', ')}`,
          effects: choice.immediate
        });
      }
    }

    PersonalityAnalyzer.record(state, choice);
    state.day += 1;

    if (state.day % 365 === 0) {
      state.character.age += 1;
    }

    ConsequenceEngine.processDay(state);

    return decision;
  },

  setReflection(state, decisionIndex, reflection) {
    if (state.decisions[decisionIndex]) {
      state.decisions[decisionIndex].reflection = reflection;
      state.reflections.push({
        day: state.decisions[decisionIndex].day,
        reflection,
        choiceText: state.decisions[decisionIndex].choiceText
      });
    }
  }
};
