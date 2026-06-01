(() => {
const ALPHABET = [
  { letter: "a", uppercase: "A", type: "vowel", imageConcept: "quả cam", imageFile: "assets/images/a.svg", visual: "🍊", shapeNote: "Quả cam tròn, trong từ cam có chữ a để bé vừa nhìn hình vừa đọc a.", phonics: "a", exampleWord: "cam", spelling: "cờ a cam", audio: "a, cam" },
  { letter: "ă", uppercase: "Ă", type: "vowel", imageConcept: "quả măng", imageFile: "assets/images/aw.svg", visual: "🎍", shapeNote: "Búp măng có chóp nhỏ như dấu ngắn, trong từ măng có chữ ă.", phonics: "á", exampleWord: "măng", spelling: "mờ ă măng", audio: "á, măng" },
  { letter: "â", uppercase: "Â", type: "vowel", imageConcept: "cái cân", imageFile: "assets/images/aa.svg", visual: "⚖️", shapeNote: "Hai đĩa cân tạo dáng nhô lên như mũ của â, trong từ cân có chữ â.", phonics: "ớ", exampleWord: "cân", spelling: "cờ â cân", audio: "ớ, cân" },
  { letter: "b", uppercase: "B", type: "consonant", imageConcept: "bóng bay", imageFile: "assets/images/b.svg", visual: "🎈", shapeNote: "Bóng bay có phần tròn như bụng chữ b, trong từ bóng bay có chữ b.", phonics: "bờ", exampleWord: "bé", spelling: "bờ e be sắc bé", audio: "bờ, bé" },
  { letter: "c", uppercase: "C", type: "consonant", imageConcept: "cánh cung", imageFile: "assets/images/c.svg", visual: "🌙", shapeNote: "Cánh cung cong mở ra giống chữ c, trong từ cung có chữ c.", phonics: "cờ", exampleWord: "cá", spelling: "cờ a ca sắc cá", audio: "cờ, cá" },
  { letter: "d", uppercase: "D", type: "consonant", imageConcept: "dây diều", imageFile: "assets/images/d.svg", visual: "🪁", shapeNote: "Cánh diều có bụng tròn và dây dài như chữ d, trong từ diều có chữ d.", phonics: "dờ", exampleWord: "dê", spelling: "dờ ê dê", audio: "dờ, dê" },
  { letter: "đ", uppercase: "Đ", type: "consonant", imageConcept: "cây đàn", imageFile: "assets/images/dd.svg", visual: "🎸", shapeNote: "Cần đàn có thanh ngang giúp bé nhớ chữ đ, trong từ đàn có chữ đ.", phonics: "đờ", exampleWord: "đàn", spelling: "đờ a đa huyền đàn", audio: "đờ, đàn" },
  { letter: "e", uppercase: "E", type: "vowel", imageConcept: "em bé", imageFile: "assets/images/e.svg", visual: "👶", shapeNote: "Miệng em bé mở nhỏ khi đọc e, trong từ em có chữ e.", phonics: "e", exampleWord: "em", spelling: "e mờ em", audio: "e, em" },
  { letter: "ê", uppercase: "Ê", type: "vowel", imageConcept: "con ếch", imageFile: "assets/images/ee.svg", visual: "🐸", shapeNote: "Đầu ếch tròn có hai mắt như dấu mũ, trong từ ếch có chữ ê.", phonics: "ê", exampleWord: "ếch", spelling: "ê chờ êch sắc ếch", audio: "ê, ếch" },
  { letter: "g", uppercase: "G", type: "consonant", imageConcept: "con gà", imageFile: "assets/images/g.svg", visual: "🐔", shapeNote: "Cổ gà cong giúp bé nhớ chữ g, trong từ gà có chữ g.", phonics: "gờ", exampleWord: "gà", spelling: "gờ a ga huyền gà", audio: "gờ, gà" },
  { letter: "h", uppercase: "H", type: "consonant", imageConcept: "hàng rào", imageFile: "assets/images/h.svg", visual: "🪜", shapeNote: "Hai thanh đứng nối nhau giống chữ h, trong từ hàng có chữ h.", phonics: "hờ", exampleWord: "hoa", spelling: "hờ oa hoa", audio: "hờ, hoa" },
  { letter: "i", uppercase: "I", type: "vowel", imageConcept: "cây kim", imageFile: "assets/images/i.svg", visual: "🪡", shapeNote: "Cây kim thẳng và nhỏ giống chữ i, trong từ kim có chữ i.", phonics: "i", exampleWord: "in", spelling: "i nờ in", audio: "i, in" },
  { letter: "k", uppercase: "K", type: "consonant", imageConcept: "cái kèn", imageFile: "assets/images/k.svg", visual: "🎺", shapeNote: "Ống kèn có thân thẳng và miệng xòe như nét chữ k, trong từ kèn có chữ k.", phonics: "ca", exampleWord: "kẹo", spelling: "ca eo keo nặng kẹo", audio: "ca, kẹo" },
  { letter: "l", uppercase: "L", type: "consonant", imageConcept: "chiếc lá", imageFile: "assets/images/l.svg", visual: "🍃", shapeNote: "Cuống lá dài giống nét chữ l, trong từ lá có chữ l.", phonics: "lờ", exampleWord: "lá", spelling: "lờ a la sắc lá", audio: "lờ, lá" },
  { letter: "m", uppercase: "M", type: "consonant", imageConcept: "mỏm núi", imageFile: "assets/images/m.svg", visual: "⛰️", shapeNote: "Hai mỏm núi giống chữ m, trong từ mỏm có chữ m.", phonics: "mờ", exampleWord: "mẹ", spelling: "mờ e me nặng mẹ", audio: "mờ, mẹ" },
  { letter: "n", uppercase: "N", type: "consonant", imageConcept: "nấm nâu", imageFile: "assets/images/n.svg", visual: "🍄", shapeNote: "Mũ nấm cong như nét chữ n, trong từ nấm có chữ n.", phonics: "nờ", exampleWord: "nơ", spelling: "nờ ơ nơ", audio: "nờ, nơ" },
  { letter: "o", uppercase: "O", type: "vowel", imageConcept: "con ong", imageFile: "assets/images/o.svg", visual: "🐝", shapeNote: "Thân ong tròn giúp bé nhớ chữ o, trong từ ong có chữ o.", phonics: "o", exampleWord: "ong", spelling: "o ngờ ong", audio: "o, ong" },
  { letter: "ô", uppercase: "Ô", type: "vowel", imageConcept: "chiếc ô", imageFile: "assets/images/oo.svg", visual: "☂️", shapeNote: "Chiếc ô có mái như dấu mũ trên chữ ô, trong từ ô có chữ ô.", phonics: "ô", exampleWord: "ô", spelling: "ô", audio: "ô" },
  { letter: "ơ", uppercase: "Ơ", type: "vowel", imageConcept: "cái nơ", imageFile: "assets/images/ow.svg", visual: "🎀", shapeNote: "Vòng nơ có nét móc mềm giúp bé nhớ chữ ơ, trong từ nơ có chữ ơ.", phonics: "ơ", exampleWord: "nơ", spelling: "nờ ơ nơ", audio: "ơ, nơ" },
  { letter: "p", uppercase: "P", type: "consonant", imageConcept: "viên pin", imageFile: "assets/images/p.svg", visual: "🔋", shapeNote: "Viên pin có thân thẳng và đầu tròn gợi nét chữ p, trong từ pin có chữ p.", phonics: "pờ", exampleWord: "pin", spelling: "pờ i nờ pin", audio: "pờ, pin" },
  { letter: "q", uppercase: "Q", type: "consonant", imageConcept: "quả bóng", imageFile: "assets/images/q.svg", visual: "🎯", shapeNote: "Quả bóng tròn có đuôi nhỏ giống chữ q, trong từ quả có chữ q.", phonics: "quờ", exampleWord: "quà", spelling: "quờ a qua huyền quà", audio: "quờ, quà" },
  { letter: "r", uppercase: "R", type: "consonant", imageConcept: "rễ cây", imageFile: "assets/images/r.svg", visual: "🌱", shapeNote: "Rễ cây tỏa xuống như nét móc của r, trong từ rễ có chữ r.", phonics: "rờ", exampleWord: "rổ", spelling: "rờ ô rô hỏi rổ", audio: "rờ, rổ" },
  { letter: "s", uppercase: "S", type: "consonant", imageConcept: "con sâu", imageFile: "assets/images/s.svg", visual: "🐛", shapeNote: "Con sâu uốn cong giống chữ s, trong từ sâu có chữ s.", phonics: "sờ", exampleWord: "sữa", spelling: "sờ ưa sưa ngã sữa", audio: "sờ, sữa" },
  { letter: "t", uppercase: "T", type: "consonant", imageConcept: "thập tự", imageFile: "assets/images/t.svg", visual: "✝️", shapeNote: "Thập tự có một nét đứng và một nét ngang giống chữ t, trong từ tự có chữ t.", phonics: "tờ", exampleWord: "tô", spelling: "tờ ô tô", audio: "tờ, tô" },
  { letter: "u", uppercase: "U", type: "vowel", imageConcept: "cốc uống nước", imageFile: "assets/images/u.svg", visual: "🥤", shapeNote: "Miệng cốc mở giống chữ u, trong từ uống có chữ u.", phonics: "u", exampleWord: "ủ", spelling: "u hỏi ủ", audio: "u, ủ" },
  { letter: "ư", uppercase: "Ư", type: "vowel", imageConcept: "cái lư", imageFile: "assets/images/uw.svg", visual: "🏺", shapeNote: "Miệng lư cong như chữ u và có nét râu của ư, trong từ lư có chữ ư.", phonics: "ư", exampleWord: "lư", spelling: "lờ ư lư", audio: "ư, lư" },
  { letter: "v", uppercase: "V", type: "consonant", imageConcept: "váy xòe", imageFile: "assets/images/v.svg", visual: "👗", shapeNote: "Dáng váy xòe xuống tạo hình chữ v, trong từ váy có chữ v.", phonics: "vờ", exampleWord: "vở", spelling: "vờ ơ vơ hỏi vở", audio: "vờ, vở" },
  { letter: "x", uppercase: "X", type: "consonant", imageConcept: "que xếp chéo", imageFile: "assets/images/x.svg", visual: "❌", shapeNote: "Hai que xếp chéo tạo thành chữ x, trong từ xếp có chữ x.", phonics: "xờ", exampleWord: "xe", spelling: "xờ e xe", audio: "xờ, xe" },
  { letter: "y", uppercase: "Y", type: "vowel", imageConcept: "cái yếm", imageFile: "assets/images/y.svg", visual: "🦺", shapeNote: "Dây yếm tách làm hai nhánh giống chữ y, trong từ yếm có chữ y.", phonics: "i dài", exampleWord: "y tá", spelling: "i dài, y tá", audio: "i dài, y tá" }
];

const RHYME_LESSONS = [
  { consonant: "l", vowel: "a", syllable: "la", chant: "lờ a la", word: "lá", spelling: "lờ a la sắc lá" },
  { consonant: "đ", vowel: "a", syllable: "đa", chant: "đờ a đa", word: "đàn", spelling: "đờ a đa huyền đàn" },
  { consonant: "m", vowel: "e", syllable: "me", chant: "mờ e me", word: "mẹ", spelling: "mờ e me nặng mẹ" },
  { consonant: "c", vowel: "a", syllable: "ca", chant: "cờ a ca", word: "cá", spelling: "cờ a ca sắc cá" },
  { consonant: "v", vowel: "ơ", syllable: "vơ", chant: "vờ ơ vơ", word: "vở", spelling: "vờ ơ vơ hỏi vở" },
  { consonant: "s", vowel: "ưa", syllable: "sưa", chant: "sờ ưa sưa", word: "sữa", spelling: "sờ ưa sưa ngã sữa" }
];

const TONE_LESSONS = [
  { base: "la", mark: "sắc", word: "lá", chant: "la sắc lá", symbol: "́" },
  { base: "ga", mark: "huyền", word: "gà", chant: "ga huyền gà", symbol: "̀" },
  { base: "ro", mark: "hỏi", word: "rổ", chant: "rô hỏi rổ", symbol: "̉" },
  { base: "sưa", mark: "ngã", word: "sữa", chant: "sưa ngã sữa", symbol: "̃" },
  { base: "me", mark: "nặng", word: "mẹ", chant: "me nặng mẹ", symbol: "̣" }
];

const BADGES = [
  { id: "first-letter", icon: "🌟", name: "Chữ đầu tiên", condition: "Hoàn thành chữ đầu tiên" },
  { id: "five-streak", icon: "⭐", name: "5 chữ liên tiếp", condition: "Học 5 chữ" },
  { id: "vowels", icon: "🎵", name: "Bạn của nguyên âm", condition: "Hoàn thành nguyên âm" },
  { id: "alphabet", icon: "🏆", name: "Nhà vô địch chữ cái", condition: "Hoàn thành bảng chữ cái" },
  { id: "game-star", icon: "🎖️", name: "Cao thủ trò chơi", condition: "Đạt 100 XP" }
];

window.ALPHABET_DATA = { ALPHABET, RHYME_LESSONS, TONE_LESSONS, BADGES };
})();
