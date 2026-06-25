/**
 * Rule-based cognitive pattern analysis.
 * Abstraction layer: AI providers can be plugged in later via analyzeWithProvider().
 */
const MirrorEngine = (() => {
  const PATTERNS = {
    ownership: {
      en: ['what can i do', 'my responsibility', 'i will', 'i can change', 'my part', 'i should', 'i need to', 'up to me', 'my choice', 'i take', 'i own', 'i could have', 'my fault', 'i control'],
      vi: ['tôi có thể làm gì', 'trách nhiệm của tôi', 'tôi sẽ', 'tôi có thể thay đổi', 'phần của tôi', 'tôi nên', 'tôi cần', 'tùy tôi', 'lựa chọn của tôi', 'tôi chịu', 'do tôi', 'lỗi của tôi', 'tôi kiểm soát', 'mình phải'],
      weight: 1,
    },
    growth: {
      en: ['i can improve', 'i learned', 'lesson', 'grow', 'practice', 'try again', 'develop', 'progress', 'better next', 'feedback', 'opportunity to learn', 'next time', 'get better'],
      vi: ['tôi có thể cải thiện', 'tôi học được', 'bài học', 'phát triển', 'luyện tập', 'thử lại', 'tiến bộ', 'lần sau tốt hơn', 'phản hồi', 'cơ hội học', 'lần tới', 'tốt hơn'],
      weight: 1,
    },
    victim: {
      en: ["it's unfair", 'their fault', 'not my fault', 'they always', 'blame', 'why me', 'unfair', 'against me', 'nobody cares', 'they did', 'because of them', 'picked on me', 'singled out'],
      vi: ['bất công', 'lỗi của họ', 'không phải lỗi tôi', 'họ luôn', 'đổ lỗi', 'tại sao lại tôi', 'chống lại tôi', 'không ai quan tâm', 'do họ', 'vì họ', 'bắt nạt', 'oán trách'],
      weight: 1,
    },
    fixed: {
      en: ["i can't", 'i always fail', 'never works', 'no point', 'hopeless', 'stuck', 'impossible', 'i am bad at', 'always mess up', 'nothing changes'],
      vi: ['tôi không thể', 'tôi luôn thất bại', 'không bao giờ được', 'vô ích', 'vô vọng', 'mắc kẹt', 'không thể', 'tôi kém', 'luôn làm hỏng', 'không thay đổi gì'],
      weight: 0.8,
    },
    catastrophic: {
      en: ['never', 'always', 'everything is ruined', 'disaster', 'worst', 'end of', 'totally', 'completely destroyed', 'all over', 'ruined forever'],
      vi: ['không bao giờ', 'luôn luôn', 'mọi thứ hỏng hết', 'thảm họa', 'tệ nhất', 'kết thúc', 'hoàn toàn', 'hủy hoại', 'tan nát', 'mãi mãi'],
      weight: 0.9,
    },
    opportunity: {
      en: ['maybe', 'possibility', 'opportunity', 'could work', 'worth trying', 'another way', 'explore', 'potential', 'might', 'chance'],
      vi: ['có lẽ', 'khả năng', 'cơ hội', 'có thể được', 'đáng thử', 'cách khác', 'khám phá', 'tiềm năng', 'có thể', 'cơ hội'],
      weight: 1,
    },
    fear: {
      en: ['risk', 'afraid', 'lose', 'scared', 'worry', 'anxious', 'fear', 'what if', 'might fail', 'danger'],
      vi: ['rủi ro', 'sợ', 'mất', 'lo lắng', 'băn khoăn', 'sợ hãi', 'nếu như', 'có thể thất bại', 'nguy hiểm', 'hoảng'],
      weight: 0.7,
    },
  };

  function normalize(text) {
    return (text || '').toLowerCase().trim();
  }

  function countMatches(text, phrases) {
    let count = 0;
    for (const phrase of phrases) {
      if (text.includes(phrase)) count++;
    }
    return count;
  }

  function analyzeText(text) {
    const normalized = normalize(text);
    const scores = {};
    const detected = [];

    for (const [key, config] of Object.entries(PATTERNS)) {
      const enMatches = countMatches(normalized, config.en);
      const viMatches = countMatches(normalized, config.vi);
      const total = (enMatches + viMatches) * config.weight;
      scores[key] = total;
      if (total > 0) detected.push({ pattern: key, strength: total });
    }

    return { scores, detected: detected.sort((a, b) => b.strength - a.strength) };
  }

  function analyzeEntry(entry) {
    const combined = [entry.thought, entry.decision, entry.reflection?.learned, entry.reflection?.differently, entry.reflection?.surprised]
      .filter(Boolean)
      .join(' ');

    return analyzeText(combined);
  }

  function aggregatePatterns(timeline, limit = 30) {
    const recent = timeline.slice(-limit);
    const totals = { ownership: 0, growth: 0, victim: 0, fixed: 0, catastrophic: 0, opportunity: 0, fear: 0 };
    const phrases = {};

    for (const entry of recent) {
      const { scores, detected } = analyzeEntry(entry);
      for (const [k, v] of Object.entries(scores)) totals[k] += v;
      for (const d of detected) {
        phrases[d.pattern] = (phrases[d.pattern] || 0) + 1;
      }
    }

    return { totals, count: recent.length, phrases };
  }

  /**
   * AI provider abstraction — plug OpenAI/Gemini/Claude here later.
   * @param {object} provider - { name, analyze(timeline, lang) => Promise<reflections[]> }
   */
  async function analyzeWithProvider(provider, timeline, lang) {
    if (provider && typeof provider.analyze === 'function') {
      return provider.analyze(timeline, lang);
    }
    return generateReflections(timeline, lang);
  }

  function generateReflections(timeline, lang) {
    const isVi = lang === 'vi';
    const { totals, count } = aggregatePatterns(timeline);
    if (count === 0) return [];

    const reflections = [];
    const n = Math.min(count, 30);

    if (totals.victim > totals.ownership && totals.victim >= 2) {
      reflections.push(
        isVi
          ? `Trong ${n} phản hồi gần đây, bạn thường tập trung vào những gì người khác đã làm sai.`
          : `In your last ${n} responses, you often focused on what others did wrong.`
      );
    }

    if (totals.growth >= 2 && totals.growth > totals.fixed) {
      reflections.push(
        isVi
          ? `Bạn thường phục hồi sau khó khăn bằng cách tìm kiếm bài học.`
          : `You frequently recover from setbacks by looking for lessons.`
      );
    }

    if (totals.fear >= 2 && totals.opportunity < totals.fear) {
      reflections.push(
        isVi
          ? `Bạn có xu hướng phản ứng với lo lắng trước khi khám phá các lựa chọn khác.`
          : `You tend to react with worry before exploring alternatives.`
      );
    }

    if (totals.opportunity >= 2 && totals.catastrophic < 1) {
      reflections.push(
        isVi
          ? `Bạn thường nhìn thấy khả năng ngay cả trong tình huống khó.`
          : `You often see possibility even in difficult situations.`
      );
    }

    if (totals.ownership >= 2 && totals.ownership > totals.victim) {
      reflections.push(
        isVi
          ? `Bạn thường đặt câu hỏi về phần việc mình có thể làm trong các tình huống.`
          : `You often ask what part you can play in situations.`
      );
    }

    if (totals.catastrophic >= 2) {
      reflections.push(
        isVi
          ? `Ngôn ngữ của bạn đôi khi phóng đại mức độ nghiêm trọng của sự kiện.`
          : `Your language sometimes amplifies how catastrophic events feel.`
      );
    }

    if (totals.fixed >= 2 && totals.growth < totals.fixed) {
      reflections.push(
        isVi
          ? `Bạn đôi khi dùng những từ ngữ cho thấy niềm tin rằng mọi thứ khó thay đổi.`
          : `You sometimes use language that suggests things are hard to change.`
      );
    }

    if (reflections.length === 0) {
      reflections.push(
        isVi
          ? `Tiếp tục ghi lại phản hồi để nhận diện khuôn mẫu tư duy rõ hơn.`
          : `Keep recording responses to reveal clearer thinking patterns.`
      );
    }

    return reflections;
  }

  function getLiveHints(text, lang) {
    const { detected } = analyzeText(text);
    if (detected.length === 0) return [];
    const labels = {
      vi: {
        ownership: 'Chủ động',
        growth: 'Phát triển',
        victim: 'Nạn nhân',
        fixed: 'Cố định',
        catastrophic: 'Thảm họa',
        opportunity: 'Cơ hội',
        fear: 'Lo lắng',
      },
      en: {
        ownership: 'Ownership',
        growth: 'Growth',
        victim: 'Victim',
        fixed: 'Fixed',
        catastrophic: 'Catastrophic',
        opportunity: 'Opportunity',
        fear: 'Fear',
      },
    };
    const L = labels[lang] || labels.en;
    return detected.slice(0, 3).map((d) => L[d.pattern] || d.pattern);
  }

  function getEntryReflection(entry, lang) {
    const { detected } = analyzeEntry(entry);
    if (detected.length === 0) return null;
    const isVi = lang === 'vi';
    const top = detected[0].pattern;
    const map = {
      ownership: isVi ? 'Ngôn ngữ của bạn cho thấy tư duy chủ động.' : 'Your language shows ownership thinking.',
      growth: isVi ? 'Bạn đang dùng ngôn ngữ phát triển.' : 'You are using growth-oriented language.',
      victim: isVi ? 'Bạn đang tập trung vào điều ngoài tầm kiểm soát.' : 'You are focusing on what is outside your control.',
      fixed: isVi ? 'Bạn đang dùng ngôn ngữ cho thấy niềm tin cố định.' : 'You are using language that suggests fixed beliefs.',
      catastrophic: isVi ? 'Bạn đang phóng đại mức độ nghiêm trọng.' : 'You are amplifying how severe this feels.',
      opportunity: isVi ? 'Bạn đang nhìn thấy khả năng trong tình huống.' : 'You are seeing possibility in the situation.',
      fear: isVi ? 'Ngôn ngữ của bạn mang sắc thái lo lắng.' : 'Your language carries worry.',
    };
    return map[top] || null;
  }

  function getFrequentPhrases(timeline, lang, limit = 10) {
    const words = {};
    const stopWords = new Set(
      lang === 'vi'
        ? ['và', 'là', 'của', 'tôi', 'một', 'có', 'không', 'đã', 'được', 'trong', 'với', 'cho', 'này', 'đó', 'rằng', 'nhưng', 'khi', 'thì', 'cũng', 'rất', 'để', 'bạn', 'họ', 'nó', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'it', 'that', 'this', 'i', 'my', 'me']
        : ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'it', 'that', 'this', 'i', 'my', 'me', 'and', 'or', 'but', 'not', 'so', 'if', 'as', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should']
    );

    for (const entry of timeline) {
      const text = [entry.thought, entry.decision].filter(Boolean).join(' ');
      const tokens = text.toLowerCase().split(/[\s,.!?;:'"()\-–—]+/).filter((w) => w.length > 2 && !stopWords.has(w));
      for (const t of tokens) {
        words[t] = (words[t] || 0) + 1;
      }
    }

    return Object.entries(words)
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit)
      .map(([word, count]) => ({ word, count }));
  }

  return {
    analyzeText,
    analyzeEntry,
    aggregatePatterns,
    analyzeWithProvider,
    generateReflections,
    getLiveHints,
    getEntryReflection,
    getFrequentPhrases,
    PATTERNS,
  };
})();
