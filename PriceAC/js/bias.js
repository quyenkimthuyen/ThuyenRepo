/* Bias module: derives educational cognitive-bias hints from journal history. */
const BiasAnalyzer = (() => {
  const biasKeywords = {
    "Confirmation Bias": ["sure", "always", "obvious", "certain", "knew", "\u0111\u00fang", "ch\u1eafc ch\u1eafn"],
    FOMO: ["miss", "late", "everyone", "moon", "fomo", "b\u1ecf l\u1ee1", "\u0111u \u0111\u1ec9nh"],
    "Anchoring Bias": ["price", "target", "old high", "ath", "neo", "m\u1ed1c"],
    "Loss Aversion": ["loss", "s\u1eadp", "crash", "fear", "panic", "m\u1ea5t", "l\u1ed7"],
    "Herd Mentality": ["crowd", "twitter", "news", "people", "market says", "\u0111\u00e1m \u0111\u00f4ng"]
  };

  const countByEmotion = (entries) => entries.reduce((stats, entry) => {
    stats[entry.emotion] = (stats[entry.emotion] || 0) + 1;
    return stats;
  }, {});

  const detectBiasCounts = (entries) => {
    const counts = Object.fromEntries(Object.keys(biasKeywords).map((name) => [name, 0]));

    entries.forEach((entry) => {
      const text = `${entry.emotion} ${entry.note}`.toLowerCase();
      Object.entries(biasKeywords).forEach(([bias, keywords]) => {
        if (keywords.some((keyword) => text.includes(keyword.toLowerCase()))) {
          counts[bias] += 1;
        }
      });

      if (entry.emotion === "Greed" || entry.emotion === "Hope") {
        counts.FOMO += 1;
      }

      if (entry.emotion === "Fear" || entry.emotion === "Panic" || entry.emotion === "Anxiety") {
        counts["Loss Aversion"] += 1;
      }
    });

    return counts;
  };

  const summarize = (entries) => {
    const emotionCounts = countByEmotion(entries);
    const biasCounts = detectBiasCounts(entries);
    const mostCommonBias = Object.entries(biasCounts).sort((a, b) => b[1] - a[1])[0] || ["Learning", 0];

    return {
      emotionCounts,
      biasCounts,
      fearEntries: emotionCounts.Fear || 0,
      greedEntries: emotionCounts.Greed || 0,
      fomoSignals: biasCounts.FOMO || 0,
      mostCommonBias: mostCommonBias[1] > 0 ? mostCommonBias[0] : "Not enough data"
    };
  };

  const render = (container, entries) => {
    const summary = summarize(entries);
    const cards = [
      ["Fear entries", summary.fearEntries],
      ["Greed entries", summary.greedEntries],
      ["FOMO signals", summary.fomoSignals],
      ["Most common bias", summary.mostCommonBias]
    ];

    container.innerHTML = cards.map(([label, value]) => `
      <article class="bias-card">
        <h3>${label}</h3>
        <strong>${value}</strong>
        <div class="asset-meta">Educational reflection only</div>
      </article>
    `).join("");

    return summary;
  };

  return {
    summarize,
    render
  };
})();
