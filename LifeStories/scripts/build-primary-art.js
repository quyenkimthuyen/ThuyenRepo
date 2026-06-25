#!/usr/bin/env node
/**
 * Generates primary-school illustration JS modules (UTF-8 safe).
 * Run: node scripts/build-primary-art.js
 */
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, '../js/comic');
const FONT = "Be Vietnam Pro, Segoe UI, Tahoma, sans-serif";

function esc(s) {
  return s.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

function wrapModule(storyId, constName, style, illustrations, sceneMap) {
  const svgObj = {};
  const metaObj = {};
  for (const [k, v] of Object.entries(illustrations)) {
    svgObj[k] = v.svg;
    metaObj[k] = { mood: v.mood, caption: v.caption };
  }
  return `/* Auto-generated — ${storyId} (${style}) */
const ${constName}_SVG = ${JSON.stringify(svgObj, null, 2)};

const ${constName}_META = ${JSON.stringify(metaObj, null, 2)};

const ${constName}_SCENES = ${JSON.stringify(sceneMap, null, 2)};

function get${constName}Art(sceneId) {
  const key = ${constName}_SCENES[sceneId];
  if (!key) return null;
  return { key, style: '${style}', ...${constName}_META[key], svg: ${constName}_SVG[key] };
}
`;
}

// ─── ps-02 watercolor ───
const PS02 = {
  test: {
    mood: 'calm',
    caption: { vi: 'Giờ kiểm tra Toán — Linh cho mượn bút', en: 'Math test — Linh lends her pencil' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs>
    <radialGradient id="w1" cx="50%" cy="30%"><stop offset="0%" stop-color="#E8F4FC"/><stop offset="100%" stop-color="#C5DFF5"/></radialGradient>
    <filter id="soft"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <rect width="800" height="450" fill="url(#w1)"/>
  <ellipse cx="400" cy="380" rx="420" ry="80" fill="#D4E8C8" opacity="0.6" filter="url(#soft)"/>
  <rect x="120" y="100" width="560" height="280" rx="24" fill="#FFF8F0" opacity="0.85" filter="url(#soft)"/>
  <ellipse cx="200" cy="200" rx="35" ry="40" fill="#F5D0C5" filter="url(#soft)"/>
  <path d="M175 245 Q200 270 225 245" fill="#A8C8E8" opacity="0.8"/>
  <ellipse cx="320" cy="210" rx="30" ry="35" fill="#F5D0C5" filter="url(#soft)"/>
  <path d="M300 250 Q320 270 340 250" fill="#E8B8C8" opacity="0.8"/>
  <rect x="350" y="230" width="120" height="8" rx="4" fill="#F4C4A0" transform="rotate(-5 410 234)"/>
  <rect x="280" y="260" width="90" height="6" rx="3" fill="#FFD4A8" transform="rotate(8 325 263)"/>
  <text x="400" y="90" font-family="${FONT}" font-size="20" fill="#7A9AB8" text-anchor="middle">Kiểm tra Toán</text>
</svg>`,
  },
  broken: {
    mood: 'tense',
    caption: { vi: 'Cây bút gãy — Không ai thấy', en: 'The pencil snaps — Nobody saw' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs>
    <radialGradient id="w2" cx="50%" cy="40%"><stop offset="0%" stop-color="#F0E0F0"/><stop offset="100%" stop-color="#D8C0E0"/></radialGradient>
    <filter id="soft2"><feGaussianBlur stdDeviation="3"/></filter>
  </defs>
  <rect width="800" height="450" fill="url(#w2)"/>
  <ellipse cx="400" cy="250" rx="200" ry="120" fill="#FFF5EE" opacity="0.7" filter="url(#soft2)"/>
  <rect x="280" y="200" width="100" height="10" rx="5" fill="#E8C090" transform="rotate(-12 330 205)"/>
  <rect x="420" y="215" width="80" height="10" rx="5" fill="#E8C090" transform="rotate(15 460 220)"/>
  <circle cx="400" cy="210" r="18" fill="#F5D0C5" filter="url(#soft2)"/>
  <ellipse cx="400" cy="195" rx="22" ry="14" fill="#8B7355" opacity="0.6"/>
  <text x="400" y="340" font-family="${FONT}" font-size="18" fill="#9A7AB0" text-anchor="middle">...gãy rồi</text>
</svg>`,
  },
  confess: {
    mood: 'warm',
    caption: { vi: 'Nói thật với Linh', en: 'Telling Linh the truth' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs>
    <linearGradient id="w3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#FFE8D0"/><stop offset="100%" stop-color="#F5D8E8"/></linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <rect width="800" height="450" fill="url(#w3)"/>
  <ellipse cx="280" cy="240" rx="50" ry="55" fill="#F5D0C5" filter="url(#glow)"/>
  <path d="M250 300 Q280 330 310 300" fill="#A8C8E8" opacity="0.75"/>
  <ellipse cx="520" cy="235" rx="48" ry="52" fill="#F5D0C5" filter="url(#glow)"/>
  <path d="M490 295 Q520 325 550 295" fill="#E8B8C8" opacity="0.75"/>
  <ellipse cx="400" cy="180" rx="100" ry="40" fill="#FFF" opacity="0.9" filter="url(#glow)"/>
  <text x="330" y="175" font-family="${FONT}" font-size="15" fill="#806080">Mình xin lỗi...</text>
  <text x="330" y="195" font-family="${FONT}" font-size="15" fill="#806080">bút của cậu gãy rồi</text>
</svg>`,
  },
  ending: {
    mood: 'sunset',
    caption: { vi: 'Sự thật nhẹ như lông chim', en: 'Truth light as a feather' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs>
    <linearGradient id="w4" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#FFB8A0"/><stop offset="60%" stop-color="#FFD8C0"/><stop offset="100%" stop-color="#C8E8C0"/></linearGradient>
  </defs>
  <rect width="800" height="450" fill="url(#w4)"/>
  <ellipse cx="300" cy="280" rx="45" ry="50" fill="#F5D0C5" opacity="0.9"/>
  <ellipse cx="500" cy="275" rx="45" ry="50" fill="#F5D0C5" opacity="0.9"/>
  <path d="M350 270 Q400 240 450 270" stroke="#E8A0B0" stroke-width="3" fill="none" opacity="0.6"/>
  <ellipse cx="400" cy="150" rx="30" ry="8" fill="#FFF" opacity="0.5" transform="rotate(-20 400 150)"/>
  <text x="400" y="380" font-family="${FONT}" font-size="22" fill="#C07080" text-anchor="middle">Cảm ơn vì đã nói thật</text>
</svg>`,
  },
};

const PS02_SCENES = {
  'ps02-01': 'test', 'ps02-02': 'test',
  'ps02-03a': 'broken', 'ps02-03b': 'broken', 'ps02-03c': 'broken',
  'ps02-04': 'broken', 'ps02-04b': 'broken',
  'ps02-05': 'confess', 'ps02-06': 'confess',
  'ps02-07': 'ending', 'ps02-08': 'ending',
};

// ─── ps-03 flat ───
const PS03 = {
  cafeteria: {
    mood: 'morning',
    caption: { vi: 'Căng tin trưa — Hộp cơm của mình', en: 'Lunch cafeteria — Your lunch box' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#4ECDC4"/>
  <rect x="0" y="300" width="800" height="150" fill="#45B7AA"/>
  <rect x="80" y="120" width="280" height="200" fill="#FFE66D"/>
  <rect x="440" y="120" width="280" height="200" fill="#FF6B6B"/>
  <rect x="150" y="200" width="140" height="90" rx="8" fill="#FFF"/>
  <rect x="510" y="200" width="140" height="90" rx="8" fill="#FFF"/>
  <rect x="170" y="215" width="50" height="35" fill="#FF6B6B"/>
  <rect x="230" y="220" width="40" height="30" fill="#4ECDC4"/>
  <circle cx="200" cy="160" r="28" fill="#FDDCB5"/>
  <rect x="175" y="188" width="50" height="40" fill="#5B8DEF"/>
  <circle cx="580" cy="165" r="26" fill="#FDDCB5"/>
  <rect x="558" y="191" width="44" height="38" fill="#E879A0"/>
  <text x="400" y="80" font-family="${FONT}" font-size="24" fill="#FFF" text-anchor="middle" font-weight="600">Giờ ăn trưa</text>
</svg>`,
  },
  sharing: {
    mood: 'warm',
    caption: { vi: 'Chia nửa hộp cơm', en: 'Sharing half the lunch' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#FF6B6B"/>
  <rect x="0" y="320" width="800" height="130" fill="#E85555"/>
  <rect x="200" y="140" width="400" height="180" rx="12" fill="#FFF"/>
  <line x1="400" y1="140" x2="400" y2="320" stroke="#DDD" stroke-width="4"/>
  <rect x="220" y="180" width="160" height="100" fill="#FFE66D"/>
  <rect x="420" y="180" width="160" height="100" fill="#4ECDC4"/>
  <circle cx="300" cy="120" r="30" fill="#FDDCB5"/>
  <rect x="275" y="150" width="50" height="35" fill="#5B8DEF"/>
  <circle cx="500" cy="125" r="28" fill="#FDDCB5"/>
  <rect x="478" y="153" width="44" height="33" fill="#E879A0"/>
  <polygon points="380,230 400,210 420,230 400,250" fill="#FF6B6B"/>
  <text x="400" y="380" font-family="${FONT}" font-size="20" fill="#FFF" text-anchor="middle">Chia cho nhau</text>
</svg>`,
  },
  friends: {
    mood: 'playful',
    caption: { vi: 'Ngày mai mang thêm — cùng ăn', en: 'Tomorrow bring extra — eat together' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#5B8DEF"/>
  <rect x="100" y="250" width="600" height="120" fill="#4A7AD0"/>
  <circle cx="280" cy="200" r="35" fill="#FDDCB5"/>
  <rect x="250" y="235" width="60" height="45" fill="#FFE66D"/>
  <circle cx="400" cy="195" r="35" fill="#FDDCB5"/>
  <rect x="370" y="230" width="60" height="45" fill="#4ECDC4"/>
  <circle cx="520" cy="200" r="35" fill="#FDDCB5"/>
  <rect x="490" y="235" width="60" height="45" fill="#FF6B6B"/>
  <rect x="260" y="310" width="80" height="50" rx="6" fill="#FFF"/>
  <rect x="360" y="310" width="80" height="50" rx="6" fill="#FFF"/>
  <rect x="460" y="310" width="80" height="50" rx="6" fill="#FFF"/>
  <text x="400" y="100" font-family="${FONT}" font-size="22" fill="#FFF" text-anchor="middle">Ba hộp cơm — một bàn</text>
</svg>`,
  },
  ending: {
    mood: 'sunset',
    caption: { vi: 'Chia sẻ làm bữa trưa ngon hơn', en: 'Sharing makes lunch sweeter' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#FFB347"/>
  <rect x="0" y="350" width="800" height="100" fill="#E89B3A"/>
  <circle cx="400" cy="220" r="80" fill="#FFE66D"/>
  <circle cx="320" cy="280" r="40" fill="#FDDCB5"/>
  <circle cx="400" cy="270" r="42" fill="#FDDCB5"/>
  <circle cx="480" cy="280" r="40" fill="#FDDCB5"/>
  <text x="400" y="400" font-family="${FONT}" font-size="20" fill="#FFF" text-anchor="middle">♥ Cảm ơn nhé</text>
</svg>`,
  },
};

const PS03_SCENES = {
  'ps03-01': 'cafeteria', 'ps03-02': 'cafeteria',
  'ps03-03a': 'sharing', 'ps03-03b': 'sharing', 'ps03-04': 'sharing',
  'ps03-05': 'friends', 'ps03-06': 'friends',
  'ps03-07': 'ending', 'ps03-08': 'ending',
};

// ─── ps-04 crayon ───
const PS04 = {
  alley: {
    mood: 'tense',
    caption: { vi: 'Cuối ngõ — Tiếng sủa xa xa', en: 'End of the alley — A distant bark' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#FFF8E7"/>
  <path d="M0 350 L200 200 L400 350 L600 180 L800 350 L800 450 L0 450 Z" fill="#98D8C8" stroke="#5BA898" stroke-width="5" stroke-linejoin="round"/>
  <path d="M50 100 L80 250 L120 100" fill="none" stroke="#8B6914" stroke-width="6" stroke-linecap="round"/>
  <path d="M700 80 L730 280 L770 90" fill="none" stroke="#8B6914" stroke-width="6" stroke-linecap="round"/>
  <rect x="300" y="120" width="200" height="150" fill="#E8D4B8" stroke="#A08060" stroke-width="5" stroke-linejoin="round"/>
  <path d="M350 270 L400 320 L450 270" fill="none" stroke="#A08060" stroke-width="5"/>
  <circle cx="400" cy="300" r="25" fill="#FDDCB5" stroke="#C08060" stroke-width="4"/>
  <text x="400" y="60" font-family="${FONT}" font-size="18" fill="#806040" text-anchor="middle">Cuối ngõ</text>
</svg>`,
  },
  dog: {
    mood: 'playful',
    caption: { vi: 'Chú chó nhỏ — Đuôi vẫy', en: 'A small dog — Wagging tail' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#87CEEB"/>
  <ellipse cx="400" cy="380" rx="350" ry="60" fill="#7EC850" stroke="#5A9E38" stroke-width="5"/>
  <ellipse cx="450" cy="280" rx="70" ry="50" fill="#D4A574" stroke="#8B6914" stroke-width="5"/>
  <circle cx="500" cy="240" r="40" fill="#D4A574" stroke="#8B6914" stroke-width="5"/>
  <circle cx="515" cy="230" r="8" fill="#333"/>
  <circle cx="535" cy="235" r="6" fill="#333"/>
  <ellipse cx="545" cy="245" rx="12" ry="8" fill="#E879A0"/>
  <path d="M460 250 Q420 200 400 230" fill="none" stroke="#D4A574" stroke-width="8" stroke-linecap="round"/>
  <path d="M520 320 Q580 280 600 320 Q580 360 520 330" fill="#C49464" stroke="#8B6914" stroke-width="4"/>
  <circle cx="300" cy="260" r="22" fill="#FDDCB5" stroke="#C08060" stroke-width="4"/>
  <path d="M278 285 Q300 305 322 285" fill="#70C090" stroke="#408060" stroke-width="3"/>
</svg>`,
  },
  brave: {
    mood: 'warm',
    caption: { vi: 'Bước lại gần — Không chạy', en: 'Step closer — Don\'t run' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#FFDAB9"/>
  <ellipse cx="400" cy="350" rx="300" ry="50" fill="#C8E8A0" stroke="#8AB860" stroke-width="5"/>
  <ellipse cx="480" cy="260" rx="55" ry="40" fill="#D4A574" stroke="#8B6914" stroke-width="5"/>
  <circle cx="520" cy="225" r="32" fill="#D4A574" stroke="#8B6914" stroke-width="5"/>
  <circle cx="350" cy="270" r="28" fill="#FDDCB5" stroke="#C08060" stroke-width="4"/>
  <path d="M325 300 Q350 325 375 300" fill="#5B8DEF" stroke="#3060A0" stroke-width="3"/>
  <path d="M378 275 L420 250" stroke="#FDDCB5" stroke-width="6" stroke-linecap="round"/>
  <text x="400" y="100" font-family="${FONT}" font-size="20" fill="#A06040" text-anchor="middle">Gần hơn một chút...</text>
</svg>`,
  },
  ending: {
    mood: 'sunset',
    caption: { vi: 'Dũng cảm không phải không sợ', en: 'Courage isn\'t having no fear' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#FF9A6C"/>
  <ellipse cx="400" cy="400" rx="380" ry="55" fill="#5A9E38" stroke="#3A7E18" stroke-width="5"/>
  <ellipse cx="420" cy="270" rx="50" ry="38" fill="#D4A574" stroke="#8B6914" stroke-width="5"/>
  <circle cx="455" cy="240" r="30" fill="#D4A574" stroke="#8B6914" stroke-width="5"/>
  <circle cx="340" cy="255" r="30" fill="#FDDCB5" stroke="#C08060" stroke-width="4"/>
  <path d="M310 290 Q340 320 370 290" fill="#70C090" stroke="#408060" stroke-width="3"/>
  <path d="M365 265 L400 250 L390 280" fill="none" stroke="#FDDCB5" stroke-width="5" stroke-linecap="round"/>
  <text x="400" y="120" font-family="${FONT}" font-size="22" fill="#FFF" text-anchor="middle">Bạn của nhau rồi</text>
</svg>`,
  },
};

const PS04_SCENES = {
  'ps04-01': 'alley', 'ps04-02': 'alley',
  'ps04-03a': 'dog', 'ps04-03b': 'dog', 'ps04-03c': 'dog', 'ps04-04': 'dog',
  'ps04-05': 'brave', 'ps04-06': 'brave',
  'ps04-07': 'ending', 'ps04-08': 'ending',
};

// ─── ps-05 papercut ───
const PS05 = {
  classroom: {
    mood: 'morning',
    caption: { vi: 'Lớp học — Cô giao nhiệm vụ', en: 'Classroom — Teacher assigns a task' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs><filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="4" dy="6" stdDeviation="3" flood-opacity="0.25"/></filter></defs>
  <rect width="800" height="450" fill="#F5F0E8"/>
  <rect x="80" y="60" width="640" height="320" fill="#FFF9F0" filter="url(#shadow)"/>
  <rect x="120" y="100" width="200" height="140" fill="#7EC8A0" transform="rotate(-3 220 170)" filter="url(#shadow)"/>
  <rect x="500" y="90" width="180" height="160" fill="#FFB8A0" transform="rotate(2 590 170)" filter="url(#shadow)"/>
  <ellipse cx="400" cy="280" rx="60" ry="70" fill="#FDDCB5" filter="url(#shadow)"/>
  <rect x="360" y="350" width="80" height="50" fill="#5B8DEF" filter="url(#shadow)"/>
  <rect x="300" y="80" width="200" height="50" fill="#E8D4F0" transform="rotate(-1 400 105)" filter="url(#shadow)"/>
  <text x="320" y="115" font-family="${FONT}" font-size="16" fill="#604080">Tưới cây mỗi ngày nhé</text>
</svg>`,
  },
  plant: {
    mood: 'warm',
    caption: { vi: 'Chậu cây trên bàn cô', en: 'The plant on teacher\'s desk' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs><filter id="sh2"><feDropShadow dx="3" dy="5" stdDeviation="2" flood-opacity="0.3"/></filter></defs>
  <rect width="800" height="450" fill="#E8F4E8"/>
  <rect x="250" y="200" width="300" height="180" fill="#C49A6C" filter="url(#sh2)"/>
  <rect x="270" y="180" width="260" height="40" fill="#A08050" filter="url(#sh2)"/>
  <ellipse cx="400" cy="160" rx="80" ry="60" fill="#5CB87A" filter="url(#sh2)"/>
  <ellipse cx="360" cy="130" rx="40" ry="30" fill="#7EC850" transform="rotate(-15 360 130)" filter="url(#sh2)"/>
  <ellipse cx="440" cy="125" rx="35" ry="28" fill="#6AB868" transform="rotate(20 440 125)" filter="url(#sh2)"/>
  <ellipse cx="400" cy="110" rx="30" ry="22" fill="#8AD870" filter="url(#sh2)"/>
  <circle cx="180" cy="300" r="8" fill="#87CEEB" filter="url(#sh2)"/>
  <circle cx="200" cy="280" r="6" fill="#87CEEB" filter="url(#sh2)"/>
  <circle cx="220" cy="310" r="7" fill="#87CEEB" filter="url(#sh2)"/>
  <text x="400" y="420" font-family="${FONT}" font-size="18" fill="#408050" text-anchor="middle">Cần được tưới</text>
</svg>`,
  },
  care: {
    mood: 'playful',
    caption: { vi: 'Mỗi sáng — Một ít nước', en: 'Each morning — A little water' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs><filter id="sh3"><feDropShadow dx="4" dy="5" stdDeviation="2" flood-opacity="0.25"/></filter></defs>
  <rect width="800" height="450" fill="#FFF5E6"/>
  <rect x="350" y="180" width="100" height="120" fill="#87CEEB" transform="rotate(-10 400 240)" filter="url(#sh3)"/>
  <polygon points="380,160 420,160 400,120" fill="#5BA8D0" filter="url(#sh3)"/>
  <rect x="300" y="280" width="200" height="100" fill="#C49A6C" filter="url(#sh3)"/>
  <ellipse cx="400" cy="260" rx="70" ry="50" fill="#5CB87A" filter="url(#sh3)"/>
  <circle cx="150" cy="250" r="35" fill="#FDDCB5" filter="url(#sh3)"/>
  <rect x="125" y="285" width="50" height="40" fill="#E879A0" filter="url(#sh3)"/>
  <path d="M380 200 Q400 230 420 200" fill="#B8E0F8" opacity="0.8"/>
</svg>`,
  },
  ending: {
    mood: 'sunset',
    caption: { vi: 'Cây xanh — Lời cảm ơn của cô', en: 'Green plant — Teacher\'s thanks' },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <defs><filter id="sh4"><feDropShadow dx="5" dy="6" stdDeviation="3" flood-opacity="0.3"/></filter></defs>
  <rect width="800" height="450" fill="#FFE4C4"/>
  <rect x="0" y="350" width="800" height="100" fill="#7EC850" filter="url(#sh4)"/>
  <rect x="320" y="220" width="160" height="130" fill="#C49A6C" filter="url(#sh4)"/>
  <ellipse cx="400" cy="180" rx="90" ry="70" fill="#4CAF50" filter="url(#sh4)"/>
  <ellipse cx="350" cy="150" rx="45" ry="35" fill="#66BB6A" transform="rotate(-20 350 150)" filter="url(#sh4)"/>
  <ellipse cx="450" cy="145" rx="40" ry="32" fill="#5CB87A" transform="rotate(15 450 145)" filter="url(#sh4)"/>
  <rect x="200" y="100" width="180" height="60" fill="#FFF" filter="url(#sh4)"/>
  <text x="220" y="138" font-family="${FONT}" font-size="17" fill="#C05070">Cảm ơn con nhé!</text>
  <circle cx="600" cy="280" r="30" fill="#FDDCB5" filter="url(#sh4)"/>
</svg>`,
  },
};

const PS05_SCENES = {
  'ps05-01': 'classroom', 'ps05-02': 'classroom', 'ps05-03': 'classroom',
  'ps05-04a': 'plant', 'ps05-04b': 'plant', 'ps05-05': 'plant',
  'ps05-06': 'care', 'ps05-07': 'care',
  'ps05-08': 'ending', 'ps05-09': 'ending', 'ps05-10': 'ending', 'ps05-11': 'ending',
};

const modules = [
  ['ps-02-art.js', 'PS02', 'watercolor', PS02, PS02_SCENES],
  ['ps-03-art.js', 'PS03', 'flat', PS03, PS03_SCENES],
  ['ps-04-art.js', 'PS04', 'crayon', PS04, PS04_SCENES],
  ['ps-05-art.js', 'PS05', 'papercut', PS05, PS05_SCENES],
];

for (const [file, name, style, illus, scenes] of modules) {
  const storyId = 'ps-' + name.slice(3);
  fs.writeFileSync(path.join(OUT, file), wrapModule(storyId, name, style, illus, scenes), 'utf8');
  console.log('Wrote', file);
}

// Registry
const registry = `/* Primary school illustration registry */
const ILLUSTRATED_STYLES = ['comic', 'watercolor', 'flat', 'crayon', 'papercut'];

const ILLUSTRATION_STYLE_LABELS = {
  comic: { vi: 'Truyện Tranh', en: 'Comic' },
  watercolor: { vi: 'Màu Nước', en: 'Watercolor' },
  flat: { vi: 'Phẳng Màu', en: 'Flat Design' },
  crayon: { vi: 'Sáp Màu', en: 'Crayon' },
  papercut: { vi: 'Cắt Giấy', en: 'Paper Cut' },
};

function getStoryArtForScene(storyId, sceneId) {
  let art = null;
  if (storyId === 'ps-01' && typeof getPS01Art === 'function') art = getPS01Art(sceneId);
  else if (storyId === 'ps-02' && typeof getPS02Art === 'function') art = getPS02Art(sceneId);
  else if (storyId === 'ps-03' && typeof getPS03Art === 'function') art = getPS03Art(sceneId);
  else if (storyId === 'ps-04' && typeof getPS04Art === 'function') art = getPS04Art(sceneId);
  else if (storyId === 'ps-05' && typeof getPS05Art === 'function') art = getPS05Art(sceneId);
  return art;
}

function getComicArtForScene(storyId, sceneId) {
  return getStoryArtForScene(storyId, sceneId);
}

function isIllustratedStyle(style) {
  return ILLUSTRATED_STYLES.includes(style);
}
`;

fs.writeFileSync(path.join(OUT, 'story-art.js'), registry, 'utf8');
console.log('Wrote story-art.js');
