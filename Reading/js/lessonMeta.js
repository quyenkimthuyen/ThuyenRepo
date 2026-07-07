/** @type {{ id: string, label: string }[]} */
export const LEVELS = [
  { id: 'a1', label: 'A1 — Sơ cấp' },
  { id: 'a2', label: 'A2 — Cơ bản' },
  { id: 'b1', label: 'B1 — Trung cấp' },
  { id: 'b2', label: 'B2 — Khá' },
  { id: 'c1', label: 'C1 — Nâng cao' },
];

/** @type {{ id: string, label: string }[]} */
export const TOPICS = [
  { id: 'daily', label: 'Đời sống' },
  { id: 'travel', label: 'Du lịch' },
  { id: 'work', label: 'Công việc' },
  { id: 'study', label: 'Học tập' },
  { id: 'ielts', label: 'IELTS Speaking' },
  { id: 'health', label: 'Sức khỏe' },
  { id: 'tech', label: 'Công nghệ' },
  { id: 'society', label: 'Xã hội' },
  { id: 'food', label: 'Ẩm thực' },
  { id: 'sports', label: 'Thể thao' },
  { id: 'communication', label: 'Giao tiếp thực tế' },
  { id: 'custom', label: 'Của tôi' },
];

/** Default topic preloaded for fast first paint (common lessons + tests). */
export const DEFAULT_PRELOAD_TOPIC = 'daily';
