const PersonalityAnalyzer = {
  record(state, choice) {
    const tags = choice.tags || [];
    const p = state.personality;
    p.total += 1;

    if (tags.includes('short_term')) p.shortTerm += 1;
    if (tags.includes('long_term')) p.longTerm += 1;
    if (tags.includes('risk_high')) p.riskHigh += 1;
    if (tags.includes('risk_low')) p.riskLow += 1;
    if (tags.includes('learning')) p.learning += 1;
    if (tags.includes('avoidance')) p.avoidance += 1;
    if (tags.includes('relationship')) p.relationship += 1;
  },

  shouldGenerateReport(state) {
    const sinceLast = state.decisions.length - (state.lastReportDay || 0);
    return sinceLast >= 20;
  },

  generateReport(state) {
    state.lastReportDay = state.decisions.length;
    const p = state.personality;
    const total = p.total || 1;
    const lines = [];

    const pct = (n) => Math.round((n / total) * 100);

    if (pct(p.shortTerm) > pct(p.longTerm) + 10) {
      lines.push('Ưu tiên phần thưởng ngắn hạn');
    } else if (pct(p.longTerm) > pct(p.shortTerm) + 10) {
      lines.push('Thường nghĩ đến lợi ích dài hạn');
    }

    if (pct(p.riskLow) > pct(p.riskHigh) + 15) {
      lines.push('Tránh rủi ro');
    } else if (pct(p.riskHigh) > pct(p.riskLow) + 15) {
      lines.push('Sẵn sàng chấp nhận rủi ro');
    }

    if (pct(p.learning) < 20) {
      lines.push('Đầu tư ít vào học tập');
    } else if (pct(p.learning) > 35) {
      lines.push('Thường xuyên đầu tư vào học tập');
    }

    if (pct(p.avoidance) > 25) {
      lines.push('Có xu hướng né tránh khó khăn');
    }

    if (pct(p.relationship) > 30) {
      lines.push('Quan tâm mạnh tới các mối quan hệ');
    }

    if (lines.length === 0) {
      lines.push('Hành vi quyết định khá cân bằng giữa các hướng');
    }

    return {
      title: `Báo cáo sau ${state.decisions.length} quyết định`,
      lines,
      stats: {
        shortTerm: pct(p.shortTerm),
        longTerm: pct(p.longTerm),
        riskHigh: pct(p.riskHigh),
        riskLow: pct(p.riskLow),
        learning: pct(p.learning),
        avoidance: pct(p.avoidance),
        relationship: pct(p.relationship)
      }
    };
  },

  getInsights(state) {
    const p = state.personality;
    const total = p.total || 1;
    return [
      { label: 'Ngắn hạn', value: Math.round((p.shortTerm / total) * 100) },
      { label: 'Dài hạn', value: Math.round((p.longTerm / total) * 100) },
      { label: 'Chấp nhận rủi ro', value: Math.round((p.riskHigh / total) * 100) },
      { label: 'Học tập', value: Math.round((p.learning / total) * 100) },
      { label: 'Né tránh', value: Math.round((p.avoidance / total) * 100) },
      { label: 'Quan hệ', value: Math.round((p.relationship / total) * 100) }
    ];
  }
};
