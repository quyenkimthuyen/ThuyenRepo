const ConsequenceEngine = {
  schedule(state, delayedList, choiceMeta) {
    if (!delayedList) return;
    delayedList.forEach((item) => {
      state.pendingConsequences.push({
        triggerDay: state.day + item.days,
        effects: item.effects,
        message: item.message,
        traceChoice: item.traceChoice || choiceMeta.text,
        traceDay: state.day,
        eventId: choiceMeta.eventId
      });
    });
  },

  setFlags(state, flags) {
    if (!flags) return;
    flags.forEach((flag) => {
      state.flags[flag] = (state.flags[flag] || 0) + 1;
      state.flags[`${flag}_day`] = state.day;
    });
  },

  processDay(state) {
    const triggered = [];
    const remaining = [];

    state.pendingConsequences.forEach((consequence) => {
      if (consequence.triggerDay <= state.day) {
        triggered.push(consequence);
      } else {
        remaining.push(consequence);
      }
    });

    state.pendingConsequences = remaining;

    triggered.forEach((consequence) => {
      GameState.applyEffects(state.character, consequence.effects);
      const message = consequence.message ||
        `Một quyết định trước đây đã góp phần tạo nên kết quả này. (Ngày ${consequence.traceDay}: "${consequence.traceChoice}")`;

      GameState.addTimelineEntry(state, {
        type: 'delayed',
        message,
        effects: consequence.effects,
        traceDay: consequence.traceDay,
        traceChoice: consequence.traceChoice
      });
    });

    this.processFlagConsequences(state);

    return triggered;
  },

  processFlagConsequences(state) {
    const flagRules = [
      {
        flag: 'skipped_exercise',
        thresholds: [
          { count: 3, dayOffset: 25, effects: { health: -8 }, message: 'Bạn đã bỏ tập thể dục nhiều lần. Sức khỏe bắt đầu giảm.' },
          { count: 5, dayOffset: 55, effects: { energy: -10 }, message: 'Thiếu vận động kéo dài khiến năng lượng giảm.' },
          { count: 8, dayOffset: 85, effects: { health: -12, energy: -8 }, message: 'Lối sống ít vận động ảnh hưởng đến khả năng làm việc.' }
        ]
      },
      {
        flag: 'poor_sleep',
        thresholds: [
          { count: 2, dayOffset: 15, effects: { energy: -10, health: -5 }, message: 'Thiếu ngủ tích lũy khiến bạn mệt mỏi.' },
          { count: 4, dayOffset: 40, effects: { happiness: -8, knowledge: -5 }, message: 'Giấc ngủ kém ảnh hưởng đến tâm trạng và khả năng tập trung.' }
        ]
      },
      {
        flag: 'avoided_learning',
        thresholds: [
          { count: 3, dayOffset: 30, effects: { knowledge: -10 }, message: 'Bạn đã né tránh học tập nhiều lần. Kiến thức tụt lại.' },
          { count: 5, dayOffset: 60, effects: { wealth: -8 }, message: 'Thiếu kỹ năng mới hạn chế cơ hội thu nhập.' }
        ]
      },
      {
        flag: 'impulse_spending',
        thresholds: [
          { count: 3, dayOffset: 20, effects: { wealth: -15 }, message: 'Chi tiêu bốc đồng tích lũy gây áp lực tài chính.' },
          { count: 5, dayOffset: 50, effects: { happiness: -5, wealth: -10 }, message: 'Tài chính căng thẳng ảnh hưởng đến hạnh phúc.' }
        ]
      }
    ];

    flagRules.forEach((rule) => {
      const count = state.flags[rule.flag] || 0;
      rule.thresholds.forEach((threshold) => {
        const key = `${rule.flag}_${threshold.count}`;
        if (count >= threshold.count && !state.flags[key]) {
          const flagDay = state.flags[`${rule.flag}_day`] || state.day;
          if (state.day >= flagDay + threshold.dayOffset) {
            state.flags[key] = true;
            GameState.applyEffects(state.character, threshold.effects);
            GameState.addTimelineEntry(state, {
              type: 'pattern',
              message: threshold.message,
              effects: threshold.effects,
              flag: rule.flag
            });
          }
        }
      });
    });
  }
};
