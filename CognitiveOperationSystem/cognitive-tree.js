/**
 * Cognitive Tree — Quản lý đồ thị nhận thức (nodes + relations)
 *
 * Quy tắc trạng thái:
 * - draft: xuất hiện 1 lần
 * - candidate: xuất hiện 2 lần
 * - verified: xuất hiện >= 3 lần
 *
 * Mở rộng: thay upsertNode bằng embedding similarity từ AI API.
 */

const CognitiveTree = {
  /**
   * Tính confidence dựa trên occurrences và status
   * @param {number} occurrences
   * @param {string} status
   */
  computeConfidence(occurrences, status) {
    const base = Math.min(occurrences / 5, 1);
    const statusBoost = { draft: 0.2, candidate: 0.5, verified: 0.8 };
    return Math.round((base * 0.4 + (statusBoost[status] || 0.2) * 0.6) * 100) / 100;
  },

  /**
   * Xác định status từ số lần xuất hiện
   */
  statusFromOccurrences(occurrences) {
    if (occurrences >= 3) return 'verified';
    if (occurrences === 2) return 'candidate';
    return 'draft';
  },

  /**
   * Phân loại node vào cây trong Cognitive Forest
   */
  categorizeToForest(text, label) {
    const combined = `${text} ${label}`.toLowerCase();
    const { FOREST_TREES } = window.CognitiveLibrary;

    for (const tree of FOREST_TREES) {
      if (tree.keywords.some((kw) => combined.includes(kw))) {
        return tree.id;
      }
    }
    return 'self';
  },

  /**
   * Upsert node — tăng occurrences hoặc tạo mới
   * @returns {{ node: object, isNew: boolean }}
   */
  upsertNode({ type, label, category, sourceText = '', evidenceType, evidence, sourceSessionId, userConfirmed, fromLibrary, matchScore, keywordHits }) {
    const existing = DataStore.findNode(type, label);

    const evidenceMeta =
      typeof EvidenceEngine !== 'undefined'
        ? EvidenceEngine.metaForUpsert({
            evidenceType,
            quote: evidence?.[0],
            sourceText,
            sourceSessionId,
            fromLibrary,
            matchScore,
            keywordHits,
          })
        : { evidence: sourceText ? [sourceText] : [], sourceText };

    if (existing) {
      const occurrences = (existing.occurrences || 0) + 1;
      const status = this.statusFromOccurrences(occurrences);
      const confidence = this.computeConfidence(occurrences, status);

      const patch = {
        occurrences,
        status,
        confidence,
        category: category || existing.category,
      };

      if (typeof EvidenceEngine !== 'undefined') {
        const stronger =
          (evidenceMeta.evidenceConfidence || 0) >= (existing.evidenceConfidence || 0);
        if (stronger) {
          Object.assign(patch, {
            evidenceType: evidenceMeta.evidenceType,
            evidenceConfidence: evidenceMeta.evidenceConfidence,
          });
        }
        if (evidenceMeta.evidence?.length) {
          patch.evidence = [...new Set([...(existing.evidence || []), ...evidenceMeta.evidence])];
        }
        if (sourceSessionId) {
          const prev = existing.sourceSessionIds || [];
          if (!prev.includes(sourceSessionId)) {
            patch.sourceSessionIds = [...prev, sourceSessionId];
          }
        }
        if (userConfirmed !== undefined) patch.userConfirmed = userConfirmed;
      }

      const updated = DataStore.updateNode(existing.id, patch);
      return { node: updated, isNew: false };
    }

    const forestCategory = category || this.categorizeToForest(sourceText, label);

    const node = {
      id: generateId('node'),
      type,
      label,
      category: forestCategory,
      confidence: this.computeConfidence(1, 'draft'),
      occurrences: 1,
      status: 'draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...(typeof EvidenceEngine !== 'undefined'
        ? {
            evidenceType: evidenceMeta.evidenceType,
            evidence: evidenceMeta.evidence,
            evidenceConfidence: evidenceMeta.evidenceConfidence,
            sourceSessionIds: evidenceMeta.sourceSessionIds,
            userConfirmed: userConfirmed ?? null,
          }
        : {}),
    };

    DataStore.addNode(node);
    return { node, isNew: true };
  },

  /**
   * Tạo quan hệ giữa hai node
   */
  linkNodes(sourceId, targetId, type = 'related') {
    if (!sourceId || !targetId || sourceId === targetId) return null;

    const relation = {
      id: generateId('rel'),
      source: sourceId,
      target: targetId,
      type,
    };

    return DataStore.addRelation(relation);
  },

  /**
   * Liên kết các node trong một session theo luồng EEIBVIA
   */
  linkSessionChain(nodeIds) {
    const types = ['causes', 'supports', 'related'];
    for (let i = 0; i < nodeIds.length - 1; i++) {
      const relType = i === 0 ? 'causes' : 'supports';
      this.linkNodes(nodeIds[i], nodeIds[i + 1], relType);
    }
  },

  /**
   * Lấy nodes theo cây (forest category)
   */
  getNodesByForest(treeId) {
    return DataStore.getNodes().filter((n) => n.category === treeId);
  },

  /**
   * Tính độ phát triển cây (0-100)
   */
  getTreeGrowth(treeId) {
    const nodes = this.getNodesByForest(treeId);
    if (nodes.length === 0) return 0;

    const verified = nodes.filter((n) => n.status === 'verified').length;
    const candidate = nodes.filter((n) => n.status === 'candidate').length;
    const score = verified * 3 + candidate * 2 + nodes.length;
    return Math.min(Math.round((score / (nodes.length * 3)) * 100), 100);
  },

  /**
   * Trạng thái tổng thể của cây
   */
  getTreeStatus(treeId) {
    const growth = this.getTreeGrowth(treeId);
    if (growth >= 70) return 'flourishing';
    if (growth >= 40) return 'growing';
    if (growth >= 15) return 'sprouting';
    return 'seed';
  },

  /**
   * Lấy node theo type
   */
  getNodesByType(type) {
    return DataStore.getNodes().filter((n) => n.type === type);
  },

  /**
   * Lấy node theo id
   */
  getNodeById(id) {
    return DataStore.getNodes().find((n) => n.id === id);
  },

  /**
   * Lấy relations của node
   */
  getNodeRelations(nodeId) {
    const relations = DataStore.getRelations();
    return relations.filter((r) => r.source === nodeId || r.target === nodeId);
  },

  /**
   * Thống kê tổng quan
   */
  getStats() {
    const nodes = DataStore.getNodes();
    return {
      total: nodes.length,
      byType: nodes.reduce((acc, n) => {
        acc[n.type] = (acc[n.type] || 0) + 1;
        return acc;
      }, {}),
      byStatus: nodes.reduce((acc, n) => {
        acc[n.status] = (acc[n.status] || 0) + 1;
        return acc;
      }, {}),
    };
  },
};

if (typeof window !== 'undefined') {
  window.CognitiveTree = CognitiveTree;
}
