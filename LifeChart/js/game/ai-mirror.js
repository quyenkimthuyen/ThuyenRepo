export function analyzePatterns(state) {
  const journal = state.journal.slice(0, 30);
  if (journal.length < 3) return [];

  const insights = [];
  const total = journal.length;

  const shortTermCategories = ['fun'];
  const longTermCategories = ['learning', 'health', 'career'];

  const shortTermCount = journal.filter(j => shortTermCategories.includes(j.category)).length;
  const longTermCount = journal.filter(j => longTermCategories.includes(j.category)).length;

  const shortTermPct = Math.round((shortTermCount / total) * 100);
  if (shortTermPct >= 50) {
    insights.push(`${shortTermPct}% lựa chọn gần đây ưu tiên phần thưởng ngắn hạn (Fun).`);
  } else if (longTermCount / total >= 0.5) {
    insights.push(`${Math.round((longTermCount / total) * 100)}% lựa chọn hướng tới đầu tư dài hạn.`);
  }

  if (state.winStreak >= 3) {
    insights.push(`Bạn đang trong chuỗi thắng ${state.winStreak} — nguy cơ overconfidence tăng (Greed: ${state.emotions.greed}).`);
  }
  if (state.loseStreak >= 3) {
    insights.push(`Bạn đang trong chuỗi thua ${state.loseStreak} — fear đang tăng (${state.emotions.fear}).`);
  }

  const recentLearning = journal.slice(0, 10).filter(j => j.category === 'learning').length;
  if (state.emotions.stress > 60 && recentLearning < 2) {
    insights.push('Bạn giảm đầu tư học tập khi stress tăng.');
  }

  const avgSuccessRate = journal.reduce((s, j) => s + (j.successRate || 0.5), 0) / total;
  if (avgSuccessRate < 0.45) {
    insights.push('Bạn thường chọn các trade có xác suất thấp — tư duy gambler.');
  }

  const fearEmotions = journal.filter(j => j.emotion === 'fearful').length;
  if (fearEmotions / total > 0.4) {
    insights.push(`${Math.round((fearEmotions / total) * 100)}% quyết định được thực hiện khi lo lắng.`);
  }

  const greedyEmotions = journal.filter(j => j.emotion === 'greedy').length;
  if (greedyEmotions / total > 0.3) {
    insights.push('Bạn thường quyết định khi cảm giác tham lam — hãy chú ý FOMO.');
  }

  const healthTrades = journal.filter(j => j.category === 'health').length;
  if (healthTrades / total < 0.1 && state.drawdowns.health) {
    insights.push(`Health Drawdown -${state.drawdowns.health}% nhưng bạn ít đầu tư sức khỏe.`);
  }

  if (state.emotions.discipline > 70) {
    insights.push('Kỷ luật cao — bạn đang kiểm soát impulse tốt.');
  } else if (state.emotions.discipline < 30) {
    insights.push('Kỷ luật thấp — cảm xúc đang dẫn dắt quyết định.');
  }

  const familyTrades = journal.filter(j => j.category === 'family').length;
  if (familyTrades / total < 0.08) {
    insights.push('Bạn đang neglect các mối quan hệ — Relationship risk tăng.');
  }

  if (insights.length === 0) {
    insights.push('Tiếp tục quan sát — cần thêm dữ liệu để phản chiếu pattern.');
  }

  return insights;
}

export function classifyArchetype(state) {
  const journal = state.journal.slice(0, 50);
  if (journal.length < 10) return null;

  const scores = {
    gambler: 0,
    builder: 0,
    protector: 0,
    explorer: 0,
  };

  const avgRate = journal.reduce((s, j) => s + (j.successRate || 0.5), 0) / journal.length;
  if (avgRate < 0.45) scores.gambler += 3;
  if (state.emotions.greed > 60) scores.gambler += 2;
  if (state.winStreak >= 4) scores.gambler += 2;

  const longTerm = journal.filter(j => ['learning', 'health', 'career'].includes(j.category)).length;
  if (longTerm / journal.length > 0.5) scores.builder += 3;
  if (state.emotions.discipline > 60) scores.builder += 2;
  if (Object.keys(state.drawdowns).length <= 1) scores.builder += 1;

  const funCount = journal.filter(j => j.category === 'fun').length;
  if (funCount / journal.length < 0.15 && avgRate > 0.6) scores.protector += 3;
  if (state.emotions.fear > 55) scores.protector += 2;
  if (state.emotions.discipline > 50 && state.emotions.greed < 40) scores.protector += 1;

  const categories = new Set(journal.map(j => j.category));
  if (categories.size >= 4) scores.explorer += 2;
  if (state.loseStreak >= 2 && journal.length > 20) scores.explorer += 1;
  const uniqueTrades = new Set(journal.map(j => j.decision));
  if (uniqueTrades.size / journal.length > 0.7) scores.explorer += 2;

  const top = Object.entries(scores).sort((a, b) => b[1] - a[1])[0][0];

  const archetypes = {
    gambler: {
      name: 'The Gambler',
      traits: 'Rủi ro cao, thiếu kiên nhẫn',
      description: 'Bạn thường chọn trade rủi ro cao và phần thưởng ngắn hạn. Hãy nhớ: expected value quan trọng hơn jackpot.',
    },
    builder: {
      name: 'The Builder',
      traits: 'Tư duy dài hạn, kỷ luật cao',
      description: 'Bạn đầu tư bền vững vào kiến thức, sức khỏe và sự nghiệp. Compound effect đang hoạt động.',
    },
    protector: {
      name: 'The Protector',
      traits: 'An toàn cao, tăng trưởng thấp',
      description: 'Bạn ưu tiên bảo toàn vốn cuộc đời. Cân nhắc thêm trade tăng trưởng có risk được kiểm soát.',
    },
    explorer: {
      name: 'The Explorer',
      traits: 'Thích thử nghiệm, chấp nhận thất bại',
      description: 'Bạn đa dạng hóa trải nghiệm. Hãy đảm bảo thất bại là học phí, không phải lãng phí.',
    },
  };

  return archetypes[top];
}
