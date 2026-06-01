export const rarityColors = {
  Common: "#62bf6e",
  Rare: "#43a8ff",
  Epic: "#9471ff",
  Legendary: "#ffb13d",
  Mythic: "#ff65ad"
};

export function buildWordmons(vocabulary) {
  const spawnPoints = [
    [5, 4], [9, 6], [14, 4], [21, 5], [25, 8],
    [6, 11], [11, 12], [17, 11], [23, 13], [28, 14],
    [4, 17], [9, 19], [15, 17], [20, 19], [26, 18],
    [31, 6], [33, 11], [35, 16], [13, 21], [29, 22]
  ];

  return vocabulary.map((entry, index) => ({
    ...entry,
    monsterId: `${entry.id}-mon`,
    x: spawnPoints[index][0],
    y: spawnPoints[index][1],
    captured: false,
    visible: true,
    bob: Math.random() * Math.PI * 2
  }));
}

export function getCaptureReward(wordmon, streak) {
  const rarityBonus = {
    Common: 0,
    Rare: 8,
    Epic: 18,
    Legendary: 35,
    Mythic: 60
  }[wordmon.rarity] || 0;

  return {
    xp: 22 + wordmon.difficulty * 8 + rarityBonus + Math.min(streak, 5) * 4,
    coins: 6 + wordmon.difficulty * 2 + Math.floor(rarityBonus / 4),
    stars: wordmon.rarity === "Legendary" || wordmon.rarity === "Mythic" ? 1 : 0
  };
}

export function categorySummary(vocabulary, capturedIds) {
  const captured = new Set(capturedIds);
  return vocabulary.reduce((summary, entry) => {
    if (!summary[entry.category]) summary[entry.category] = { total: 0, captured: 0 };
    summary[entry.category].total += 1;
    if (captured.has(entry.id)) summary[entry.category].captured += 1;
    return summary;
  }, {});
}
