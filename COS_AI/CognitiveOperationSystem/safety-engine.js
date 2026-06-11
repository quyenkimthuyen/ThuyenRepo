/**
 * Safety Engine — Phát hiện nội dung khủng hoảng & tài nguyên hỗ trợ
 */

const SafetyEngine = {
  crisisPatterns: [
    { keywords: ['tự tử', 'tự sát', 'muốn chết', 'không muốn sống', 'chết đi', 'kết thúc cuộc đời', 'tự hại', 'tự cắt', 'làm hại mình'] },
    { keywords: ['suicide', 'kill myself', 'want to die', 'end my life', 'self-harm', 'hurt myself', 'no reason to live'] },
    { keywords: ['tuyệt vọng hoàn toàn', 'không còn hy vọng', 'vô vọng tuyệt đối'] },
  ],

  detectCrisis(text) {
    const normalized = (text || '').toLowerCase();
    for (const pattern of this.crisisPatterns) {
      const hit = pattern.keywords.find((kw) => normalized.includes(kw.toLowerCase()));
      if (hit) return { detected: true, keyword: hit };
    }
    return { detected: false };
  },

  getResources() {
    if (typeof I18n === 'undefined') {
      return {
        title: 'Bạn không cần đối mặt một mình',
        body: 'Nếu bạn đang có ý nghĩ làm hại bản thân, hãy liên hệ ngay:',
        hotlines: [
          { label: 'Đường dây nóng quốc gia 111', tel: '111' },
          { label: 'Tổng đài tâm lý 18001929', tel: '18001929' },
        ],
        footer: 'Ứng dụng này không thay thế tư vấn chuyên môn.',
      };
    }
    return I18n.getCrisisResources();
  },
};

if (typeof window !== 'undefined') {
  window.SafetyEngine = SafetyEngine;
}
