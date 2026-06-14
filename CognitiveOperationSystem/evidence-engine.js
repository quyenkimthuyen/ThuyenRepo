/**
 * Evidence Engine — Phân biệt điều user nói vs suy luận hệ thống
 *
 * Node chỉ được dùng cho insight / mâu thuẫn / prompt ChatGPT khi có bằng chứng đủ.
 */

const EvidenceEngine = {
  TYPES: {
    DIRECT_QUOTE: 'direct_quote',
    PARAPHRASE: 'paraphrase',
    IMPORTED: 'imported',
    RULE_MATCH: 'rule_match',
    INFERRED: 'inferred',
    LEGACY: 'legacy',
  },

  /** Ngưỡng confidence tối thiểu cho rule_match (nếu sau này bật lại) */
  RULE_MATCH_MIN_CONFIDENCE: 0.65,

  getType(node) {
    return node?.evidenceType || this.TYPES.LEGACY;
  },

  /**
   * Node đủ tin cậy để đưa vào insight, mâu thuẫn, topBeliefs, prompt ChatGPT
   */
  isInsightEligible(node) {
    if (!node) return false;
    if (node.userConfirmed === false) return false;
    if (node.userConfirmed === true) return true;

    const type = this.getType(node);
    if (type === this.TYPES.DIRECT_QUOTE || type === this.TYPES.PARAPHRASE || type === this.TYPES.IMPORTED) {
      return (node.evidence || []).length > 0 || Boolean(node.sourceText);
    }
    if (type === this.TYPES.RULE_MATCH || type === this.TYPES.INFERRED) {
      return false;
    }
    if (type === this.TYPES.LEGACY) {
      return node.status === 'verified';
    }
    return false;
  },

  filterInsightEligible(nodes) {
    return (nodes || []).filter((n) => this.isInsightEligible(n));
  },

  /**
   * Metadata khi tạo/cập nhật node
   */
  metaForUpsert({
    evidenceType,
    quote,
    sourceText,
    sourceSessionId,
    fromLibrary = false,
    matchScore = 0,
    keywordHits = 0,
  }) {
    const text = (quote || sourceText || '').trim();
    let type = evidenceType;
    if (!type) {
      if (fromLibrary) {
        type = this.TYPES.RULE_MATCH;
      } else if (text) {
        type = this.TYPES.DIRECT_QUOTE;
      } else {
        type = this.TYPES.INFERRED;
      }
    }

    let evidenceConfidence = 0.5;
    if (type === this.TYPES.DIRECT_QUOTE) evidenceConfidence = 0.95;
    else if (type === this.TYPES.PARAPHRASE) evidenceConfidence = 0.85;
    else if (type === this.TYPES.IMPORTED) evidenceConfidence = 0.9;
    else if (type === this.TYPES.RULE_MATCH) {
      evidenceConfidence = Math.min(0.55, 0.25 + keywordHits * 0.12 + matchScore * 0.002);
    } else if (type === this.TYPES.INFERRED) evidenceConfidence = 0.2;
    else if (type === this.TYPES.LEGACY) evidenceConfidence = 0.5;

    return {
      evidenceType: type,
      evidence: text ? [text] : [],
      sourceText: text,
      evidenceConfidence,
      sourceSessionIds: sourceSessionId ? [sourceSessionId] : [],
    };
  },

  mergeOnUpdate(existing, patch) {
    const merged = { ...patch };
    if (patch.sourceSessionId) {
      const prev = existing.sourceSessionIds || [];
      if (!prev.includes(patch.sourceSessionId)) {
        merged.sourceSessionIds = [...prev, patch.sourceSessionId];
      }
      delete merged.sourceSessionId;
    }
    if (patch.evidence?.length) {
      const prevEv = existing.evidence || [];
      merged.evidence = [...new Set([...prevEv, ...patch.evidence])];
    }
    return merged;
  },
};

if (typeof window !== 'undefined') {
  window.EvidenceEngine = EvidenceEngine;
}
