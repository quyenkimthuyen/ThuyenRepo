export const MARKET_EVENTS = [
  {
    id: 'ai_boom',
    name: 'AI Boom',
    description: 'Công nghệ AI bùng nổ — trade Learning và Career có lợi thế.',
    duration: 6,
    modifiers: { learning: 1.3, career: 1.2 },
  },
  {
    id: 'recession',
    name: 'Recession',
    description: 'Suy thoái kinh tế — trade Career rủi ro cao hơn, cần thận trọng.',
    duration: 8,
    modifiers: { career: 0.7, fun: 0.9 },
  },
  {
    id: 'health_crisis',
    name: 'Health Crisis',
    description: 'Dịch bệnh lan rộng — Health trades quan trọng hơn bao giờ hết.',
    duration: 5,
    modifiers: { health: 1.5, fun: 0.6 },
  },
  {
    id: 'economic_growth',
    name: 'Economic Growth',
    description: 'Kinh tế tăng trưởng — cơ hội Wealth tăng cho mọi trade.',
    duration: 6,
    modifiers: { career: 1.15, learning: 1.1 },
    wealthBonus: 1.2,
  },
  {
    id: 'family_emergency',
    name: 'Family Emergency',
    description: 'Gia đình cần bạn — Family trades có giá trị gấp đôi.',
    duration: 3,
    modifiers: { family: 1.8 },
  },
  {
    id: 'social_media_trend',
    name: 'Social Media Trend',
    description: 'Xu hướng mạng xã hội — Fun trades hấp dẫn nhưng phân tâm.',
    duration: 4,
    modifiers: { fun: 1.4, learning: 0.85 },
  },
  {
    id: 'burnout_wave',
    name: 'Burnout Wave',
    description: 'Làn sóng kiệt sức — Energy cost tăng cho mọi trade.',
    duration: 5,
    energyCostMultiplier: 1.3,
    modifiers: { health: 1.2 },
  },
  {
    id: 'knowledge_revolution',
    name: 'Knowledge Revolution',
    description: 'Cách mạng tri thức — học tập mang lại reward cao hơn.',
    duration: 7,
    modifiers: { learning: 1.5 },
  },
  {
    id: 'relationship_season',
    name: 'Relationship Season',
    description: 'Mùa kết nối — các mối quan hệ dễ phát triển hơn.',
    duration: 5,
    modifiers: { family: 1.3 },
  },
  {
    id: 'market_volatility',
    name: 'Market Volatility',
    description: 'Thị trường biến động — success rate giảm 10% cho mọi trade.',
    duration: 4,
    successRatePenalty: 0.1,
  },
];

export function pickRandomEvent(excludeIds = []) {
  const available = MARKET_EVENTS.filter(e => !excludeIds.includes(e.id));
  if (available.length === 0) return MARKET_EVENTS[Math.floor(Math.random() * MARKET_EVENTS.length)];
  return available[Math.floor(Math.random() * available.length)];
}
