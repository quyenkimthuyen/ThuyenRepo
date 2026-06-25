/* Auto-generated — ps-3 (flat) */
const PS03_SVG = {
  "cafeteria": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 800 450\">\n  <rect width=\"800\" height=\"450\" fill=\"#4ECDC4\"/>\n  <rect x=\"0\" y=\"300\" width=\"800\" height=\"150\" fill=\"#45B7AA\"/>\n  <rect x=\"80\" y=\"120\" width=\"280\" height=\"200\" fill=\"#FFE66D\"/>\n  <rect x=\"440\" y=\"120\" width=\"280\" height=\"200\" fill=\"#FF6B6B\"/>\n  <rect x=\"150\" y=\"200\" width=\"140\" height=\"90\" rx=\"8\" fill=\"#FFF\"/>\n  <rect x=\"510\" y=\"200\" width=\"140\" height=\"90\" rx=\"8\" fill=\"#FFF\"/>\n  <rect x=\"170\" y=\"215\" width=\"50\" height=\"35\" fill=\"#FF6B6B\"/>\n  <rect x=\"230\" y=\"220\" width=\"40\" height=\"30\" fill=\"#4ECDC4\"/>\n  <circle cx=\"200\" cy=\"160\" r=\"28\" fill=\"#FDDCB5\"/>\n  <rect x=\"175\" y=\"188\" width=\"50\" height=\"40\" fill=\"#5B8DEF\"/>\n  <circle cx=\"580\" cy=\"165\" r=\"26\" fill=\"#FDDCB5\"/>\n  <rect x=\"558\" y=\"191\" width=\"44\" height=\"38\" fill=\"#E879A0\"/>\n  <text x=\"400\" y=\"80\" font-family=\"Be Vietnam Pro, Segoe UI, Tahoma, sans-serif\" font-size=\"24\" fill=\"#FFF\" text-anchor=\"middle\" font-weight=\"600\">Giờ ăn trưa</text>\n</svg>",
  "sharing": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 800 450\">\n  <rect width=\"800\" height=\"450\" fill=\"#FF6B6B\"/>\n  <rect x=\"0\" y=\"320\" width=\"800\" height=\"130\" fill=\"#E85555\"/>\n  <rect x=\"200\" y=\"140\" width=\"400\" height=\"180\" rx=\"12\" fill=\"#FFF\"/>\n  <line x1=\"400\" y1=\"140\" x2=\"400\" y2=\"320\" stroke=\"#DDD\" stroke-width=\"4\"/>\n  <rect x=\"220\" y=\"180\" width=\"160\" height=\"100\" fill=\"#FFE66D\"/>\n  <rect x=\"420\" y=\"180\" width=\"160\" height=\"100\" fill=\"#4ECDC4\"/>\n  <circle cx=\"300\" cy=\"120\" r=\"30\" fill=\"#FDDCB5\"/>\n  <rect x=\"275\" y=\"150\" width=\"50\" height=\"35\" fill=\"#5B8DEF\"/>\n  <circle cx=\"500\" cy=\"125\" r=\"28\" fill=\"#FDDCB5\"/>\n  <rect x=\"478\" y=\"153\" width=\"44\" height=\"33\" fill=\"#E879A0\"/>\n  <polygon points=\"380,230 400,210 420,230 400,250\" fill=\"#FF6B6B\"/>\n  <text x=\"400\" y=\"380\" font-family=\"Be Vietnam Pro, Segoe UI, Tahoma, sans-serif\" font-size=\"20\" fill=\"#FFF\" text-anchor=\"middle\">Chia cho nhau</text>\n</svg>",
  "friends": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 800 450\">\n  <rect width=\"800\" height=\"450\" fill=\"#5B8DEF\"/>\n  <rect x=\"100\" y=\"250\" width=\"600\" height=\"120\" fill=\"#4A7AD0\"/>\n  <circle cx=\"280\" cy=\"200\" r=\"35\" fill=\"#FDDCB5\"/>\n  <rect x=\"250\" y=\"235\" width=\"60\" height=\"45\" fill=\"#FFE66D\"/>\n  <circle cx=\"400\" cy=\"195\" r=\"35\" fill=\"#FDDCB5\"/>\n  <rect x=\"370\" y=\"230\" width=\"60\" height=\"45\" fill=\"#4ECDC4\"/>\n  <circle cx=\"520\" cy=\"200\" r=\"35\" fill=\"#FDDCB5\"/>\n  <rect x=\"490\" y=\"235\" width=\"60\" height=\"45\" fill=\"#FF6B6B\"/>\n  <rect x=\"260\" y=\"310\" width=\"80\" height=\"50\" rx=\"6\" fill=\"#FFF\"/>\n  <rect x=\"360\" y=\"310\" width=\"80\" height=\"50\" rx=\"6\" fill=\"#FFF\"/>\n  <rect x=\"460\" y=\"310\" width=\"80\" height=\"50\" rx=\"6\" fill=\"#FFF\"/>\n  <text x=\"400\" y=\"100\" font-family=\"Be Vietnam Pro, Segoe UI, Tahoma, sans-serif\" font-size=\"22\" fill=\"#FFF\" text-anchor=\"middle\">Ba hộp cơm — một bàn</text>\n</svg>",
  "ending": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 800 450\">\n  <rect width=\"800\" height=\"450\" fill=\"#FFB347\"/>\n  <rect x=\"0\" y=\"350\" width=\"800\" height=\"100\" fill=\"#E89B3A\"/>\n  <circle cx=\"400\" cy=\"220\" r=\"80\" fill=\"#FFE66D\"/>\n  <circle cx=\"320\" cy=\"280\" r=\"40\" fill=\"#FDDCB5\"/>\n  <circle cx=\"400\" cy=\"270\" r=\"42\" fill=\"#FDDCB5\"/>\n  <circle cx=\"480\" cy=\"280\" r=\"40\" fill=\"#FDDCB5\"/>\n  <text x=\"400\" y=\"400\" font-family=\"Be Vietnam Pro, Segoe UI, Tahoma, sans-serif\" font-size=\"20\" fill=\"#FFF\" text-anchor=\"middle\">♥ Cảm ơn nhé</text>\n</svg>"
};

const PS03_META = {
  "cafeteria": {
    "mood": "morning",
    "caption": {
      "vi": "Căng tin trưa — Hộp cơm của mình",
      "en": "Lunch cafeteria — Your lunch box"
    }
  },
  "sharing": {
    "mood": "warm",
    "caption": {
      "vi": "Chia nửa hộp cơm",
      "en": "Sharing half the lunch"
    }
  },
  "friends": {
    "mood": "playful",
    "caption": {
      "vi": "Ngày mai mang thêm — cùng ăn",
      "en": "Tomorrow bring extra — eat together"
    }
  },
  "ending": {
    "mood": "sunset",
    "caption": {
      "vi": "Chia sẻ làm bữa trưa ngon hơn",
      "en": "Sharing makes lunch sweeter"
    }
  }
};

const PS03_SCENES = {
  "ps03-01": "cafeteria",
  "ps03-02": "cafeteria",
  "ps03-03a": "sharing",
  "ps03-03b": "sharing",
  "ps03-04": "sharing",
  "ps03-05": "friends",
  "ps03-06": "friends",
  "ps03-07": "ending",
  "ps03-08": "ending"
};

function getPS03Art(sceneId) {
  const key = PS03_SCENES[sceneId];
  if (!key) return null;
  return { key, style: 'flat', ...PS03_META[key], svg: PS03_SVG[key] };
}
