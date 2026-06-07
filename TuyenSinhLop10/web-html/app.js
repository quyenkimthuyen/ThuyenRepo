const FALLBACK_QUESTIONS = [
  {
    id: "demo-math-001",
    monHoc: "Toan",
    chuyenDe: "HamSoBacHai",
    mucDo: "ThongHieu",
    deBai: "Cho hàm số y = 2x^2. Tính y khi x = 3.",
    luaChon: [],
    dapAn: "18",
    loiGiai: "Thay x = 3 vào y = 2x^2, ta được y = 2 . 3^2 = 18.",
    meoLamBai: "Với hàm bậc hai, thay đúng giá trị x rồi bình phương trước khi nhân hệ số.",
    tags: ["TPHCM", "GDPT2018"],
    estimatedTimeSeconds: 120,
  },
  {
    id: "demo-literature-001",
    monHoc: "NguVan",
    chuyenDe: "NghiLuanXaHoi",
    mucDo: "VanDung",
    deBai: "Lập dàn ý ngắn cho bài nghị luận xã hội về sự tử tế trong đời sống.",
    luaChon: [],
    dapAn: "Mở bài nêu vấn đề; thân bài giải thích, biểu hiện, ý nghĩa, phản biện; kết bài rút bài học.",
    loiGiai: "Dàn ý cần có luận điểm rõ, dẫn chứng gần gũi và bài học hành động cụ thể.",
    meoLamBai: "Không kể chuyện lan man; mỗi luận điểm nên có một dẫn chứng và một câu bình luận.",
    tags: ["TPHCM", "GDPT2018"],
    estimatedTimeSeconds: 300,
  },
  {
    id: "demo-english-001",
    monHoc: "TiengAnh",
    chuyenDe: "Tenses",
    mucDo: "NhanBiet",
    deBai: "Choose the best answer: She _____ English for three years.",
    luaChon: ["learns", "has learned", "learned", "is learning"],
    dapAn: "has learned",
    loiGiai: "'For three years' diễn tả hành động kéo dài đến hiện tại nên dùng hiện tại hoàn thành.",
    meoLamBai: "Thấy for/since với mốc kéo dài đến hiện tại, nghĩ đến present perfect.",
    tags: ["TPHCM", "GDPT2018"],
    estimatedTimeSeconds: 60,
  },
];

const subjectNames = {
  Toan: "Toán",
  NguVan: "Ngữ văn",
  TiengAnh: "Tiếng Anh",
};

const levelNames = {
  NhanBiet: "Nhận biết",
  ThongHieu: "Thông hiểu",
  VanDung: "Vận dụng",
  VanDungCao: "Vận dụng cao",
};

const topicNames = {
  BatPhuongTrinh: "Bất phương trình",
  BienDoiBieuThuc: "Biến đổi biểu thức",
  CanBacHai: "Căn bậc hai",
  DoThi: "Đồ thị",
  DuongTron: "Đường tròn",
  HamSoBacHai: "Hàm số bậc hai",
  HePhuongTrinh: "Hệ phương trình",
  HinhHocPhang: "Hình học phẳng",
  HinhKhongGian: "Hình không gian",
  PhuongTrinhBacHai: "Phương trình bậc hai",
  TamGiacDongDang: "Tam giác đồng dạng",
  ToanThucTe: "Toán thực tế",
  ToanUngDung: "Toán ứng dụng",
  VanDungCao: "Vận dụng cao",
  XacSuatThongKe: "Xác suất - thống kê",
  BienPhapTuTu: "Biện pháp tu từ",
  DanChungXaHoi: "Dẫn chứng xã hội",
  DocHieuVanBanThongTin: "Đọc hiểu văn bản thông tin",
  DocHieuVanBanVanHoc: "Đọc hiểu văn bản văn học",
  GiaTriNgheThuat: "Giá trị nghệ thuật",
  GiaTriNoiDung: "Giá trị nội dung",
  LapDanY: "Lập dàn ý",
  LienHeBanThan: "Liên hệ bản thân",
  MoBaiKetBai: "Mở bài - kết bài",
  NghiLuanVanHoc: "Nghị luận văn học",
  NghiLuanXaHoi: "Nghị luận xã hội",
  PhanTichNhanVat: "Phân tích nhân vật",
  SuaLoiDienDat: "Sửa lỗi diễn đạt",
  ThongDiepVanBan: "Thông điệp văn bản",
  VietDoanVan: "Viết đoạn văn",
  ClozeTest: "Điền từ vào đoạn văn",
  Comparisons: "So sánh",
  Conditionals: "Câu điều kiện",
  DialogueCompletion: "Hoàn thành hội thoại",
  ErrorIdentification: "Tìm lỗi sai",
  PassiveVoice: "Câu bị động",
  Prepositions: "Giới từ",
  Pronunciation: "Phát âm",
  ReadingComprehension: "Đọc hiểu",
  RelativeClauses: "Mệnh đề quan hệ",
  ReportedSpeech: "Câu tường thuật",
  SentenceTransformation: "Viết lại câu",
  Stress: "Trọng âm",
  Tenses: "Thì",
  WordForms: "Từ loại",
};

const examTemplates = {
  Toan: [
    "Bài 1: Parabol y = ax², tọa độ điểm, đồ thị và giao điểm cơ bản.",
    "Bài 2: Phương trình bậc hai, điều kiện nghiệm và hệ thức Viète.",
    "Bài 3: Xác suất - thống kê, bảng số liệu, tỉ lệ hoặc đọc dữ liệu thực tế.",
    "Bài 4-5: Toán thực tế: chi phí, khuyến mãi, chuyển động, năng suất, điều kiện tối ưu.",
    "Bài 6: Hình học thực tế/đo lường: diện tích, thể tích, đổi đơn vị, làm tròn.",
    "Bài 7: Hình học phẳng phân loại: đường tròn, nội tiếp, đồng dạng, tiếp tuyến, hệ thức.",
  ],
  NguVan: [
    "Phần đọc hiểu: ngữ liệu ngoài SGK, chi tiết tiêu biểu, thông điệp, tiếng Việt trong ngữ cảnh.",
    "Phần viết ngắn: đoạn/bài theo vấn đề rút từ ngữ liệu, có câu chủ đề, luận điểm, dẫn chứng.",
    "Phần nghị luận xã hội: quan điểm cá nhân, phản biện nhẹ, giải pháp và liên hệ hành động.",
    "Phần văn học/đề mở: phân tích chi tiết nghệ thuật, liên hệ tác phẩm hoặc trải nghiệm đọc.",
  ],
  TiengAnh: [
    "Câu 1-4: Ngữ âm và trọng âm.",
    "Câu 5-16: Từ vựng, ngữ pháp, giới từ/cụm từ, biển báo/thông báo và giao tiếp.",
    "Câu 17-22: Cloze test theo đoạn văn, kiểm tra ngữ pháp, từ vựng và liên kết câu.",
    "Câu 23-28: Reading comprehension, True/False, main idea, detail, inference/reference.",
    "Câu 29-34: Word forms và từ loại.",
    "Câu 35-40: Guided writing, sentence transformation, rearrangement/rewriting.",
  ],
};

const mathExamBlueprint = [
  { topic: "HamSoBacHai", count: 1 },
  { topic: "PhuongTrinhBacHai", count: 1 },
  { topic: "XacSuatThongKe", count: 1 },
  { topic: "ToanThucTe", count: 2 },
  { topic: "HinhKhongGian", count: 1 },
  { topic: "HinhHocPhang", count: 1 },
];

const literatureExamBlueprint = [
  { topic: "DocHieuVanBanThongTin", count: 1 },
  { topic: "DocHieuVanBanVanHoc", count: 1 },
  { topic: "ThongDiepVanBan", count: 1 },
  { topic: "BienPhapTuTu", count: 1 },
  { topic: "VietDoanVan", count: 1 },
  { topic: "NghiLuanXaHoi", count: 2 },
  { topic: "DanChungXaHoi", count: 1 },
  { topic: "NghiLuanVanHoc", count: 1 },
];

const englishExamBlueprint = [
  { topic: "Pronunciation", count: 2 },
  { topic: "Stress", count: 2 },
  { topic: "Tenses", count: 3 },
  { topic: "PassiveVoice", count: 2 },
  { topic: "ReportedSpeech", count: 2 },
  { topic: "RelativeClauses", count: 2 },
  { topic: "Conditionals", count: 2 },
  { topic: "WordForms", count: 3 },
  { topic: "Prepositions", count: 2 },
  { topic: "Comparisons", count: 2 },
  { topic: "ErrorIdentification", count: 2 },
  { topic: "DialogueCompletion", count: 2 },
  { topic: "ClozeTest", count: 6 },
  { topic: "ReadingComprehension", count: 5 },
  { topic: "SentenceTransformation", count: 3 },
];

const examStats = [
  {
    subject: "Toán",
    focus: "Hình học phẳng - đường tròn, nội tiếp, đồng dạng",
    weight: 98,
    frequency: "Rất cao",
    difficulty: "Cao",
    note: "Năm nào cũng là phần phân loại lớn; 2022 có đường cao, tứ giác nội tiếp, hệ thức MB.MC = ME.MF.",
  },
  {
    subject: "Toán",
    focus: "Toán thực tế - lập biểu thức/phương trình",
    weight: 95,
    frequency: "Rất cao",
    difficulty: "Trung bình - cao",
    note: "Xuất hiện dày ở bài giữa đề: khuyến mãi, nhiệt độ, BMI, SEA Games, chi phí, điều kiện ít nhất/nhiều nhất.",
  },
  {
    subject: "Toán",
    focus: "Phương trình bậc hai và Viète",
    weight: 90,
    frequency: "Rất cao",
    difficulty: "Trung bình - cao",
    note: "Mạch ổn định nhiều năm: điều kiện nghiệm, nghiệm kép, tổng - tích nghiệm, biểu thức đối xứng.",
  },
  {
    subject: "Toán",
    focus: "Parabol, đồ thị và tọa độ điểm",
    weight: 86,
    frequency: "Rất cao",
    difficulty: "Trung bình",
    note: "Bài nền đầu đề: y = ax², xét điểm thuộc đồ thị, giao điểm với đường thẳng, tìm hệ số a.",
  },
  {
    subject: "Toán",
    focus: "Hình học thực tế và đo lường",
    weight: 82,
    frequency: "Cao",
    difficulty: "Trung bình - cao",
    note: "Gắn hình tròn, hình trụ, hình nón, hình hộp; dễ mất điểm vì đổi đơn vị, bán kính/đường kính, làm tròn.",
  },
  {
    subject: "Toán",
    focus: "Xác suất - thống kê và đọc dữ liệu",
    weight: 78,
    frequency: "Cao",
    difficulty: "Trung bình",
    note: "Tăng rõ trong đề 2025-2026; cần đọc bảng, tính tỉ lệ, trung bình cộng và xác suất đơn giản.",
  },
  {
    subject: "Ngữ văn",
    focus: "Đọc hiểu ngữ liệu ngoài SGK",
    weight: 98,
    frequency: "Rất cao",
    difficulty: "Trung bình",
    note: "Trục cố định 2022-2026: văn bản mới, thông tin chính, thông điệp, thái độ, căn cứ từ văn bản.",
  },
  {
    subject: "Ngữ văn",
    focus: "Nghị luận xã hội và quan điểm cá nhân",
    weight: 96,
    frequency: "Rất cao",
    difficulty: "Trung bình - cao",
    note: "Điểm lớn trong đề: trưởng thành, suy nghĩ tốt đẹp, trách nhiệm, ứng xử, tự học; cần lập luận và dẫn chứng.",
  },
  {
    subject: "Ngữ văn",
    focus: "Viết đoạn/bài theo vấn đề từ ngữ liệu",
    weight: 92,
    frequency: "Rất cao",
    difficulty: "Trung bình - cao",
    note: "Đọc hiểu thường nối sang viết; cần câu chủ đề, luận điểm rõ, dẫn chứng ngắn, bài học hành động.",
  },
  {
    subject: "Ngữ văn",
    focus: "Tiếng Việt trong ngữ cảnh và biện pháp tu từ",
    weight: 86,
    frequency: "Cao",
    difficulty: "Trung bình",
    note: "Thường hỏi phép liên kết, thành phần biệt lập, từ ngữ/hình ảnh, biện pháp tu từ và tác dụng cụ thể.",
  },
  {
    subject: "Ngữ văn",
    focus: "Cảm thụ/nghị luận văn học",
    weight: 78,
    frequency: "Cao",
    difficulty: "Cao",
    note: "Đề vẫn mở cửa cho phân tích thơ/truyện hoặc trải nghiệm đọc; điểm cao cần chi tiết nghệ thuật, không kể lại.",
  },
  {
    subject: "Ngữ văn",
    focus: "Dẫn chứng, phản biện và diễn đạt",
    weight: 74,
    frequency: "Cao",
    difficulty: "Trung bình - cao",
    note: "Yếu tố quyết định điểm viết: dẫn chứng đúng vấn đề, có bình luận, liên kết đoạn và ít lỗi diễn đạt.",
  },
  {
    subject: "Tiếng Anh",
    focus: "Reading Comprehension và Cloze Test",
    weight: 96,
    frequency: "Rất cao",
    difficulty: "Trung bình - cao",
    note: "Chiếm phần điểm lớn trong cấu trúc 40 câu; 2022 có water cycle và cloze tình huống thời tiết.",
  },
  {
    subject: "Tiếng Anh",
    focus: "Word Forms và từ loại",
    weight: 94,
    frequency: "Rất cao",
    difficulty: "Cao",
    note: "Nhóm phân loại rõ ở câu 29-34: xác định noun/verb/adj/adv, tiền tố phủ định, số ít/số nhiều.",
  },
  {
    subject: "Tiếng Anh",
    focus: "Sentence Transformation và guided writing",
    weight: 92,
    frequency: "Rất cao",
    difficulty: "Cao",
    note: "Câu cuối nhiều năm kiểm tra giữ nguyên nghĩa: passive, reported speech, conditionals, because/because of, enough/too.",
  },
  {
    subject: "Tiếng Anh",
    focus: "Tenses, verb forms và cấu trúc câu",
    weight: 88,
    frequency: "Rất cao",
    difficulty: "Trung bình - cao",
    note: "Xuất hiện rải trong ngữ pháp, cloze và viết lại câu; cần chắc thì, V-ing/to V, bị động, điều kiện, quan hệ.",
  },
  {
    subject: "Tiếng Anh",
    focus: "Vocabulary, prepositions, phrasal verbs và dialogue",
    weight: 82,
    frequency: "Cao",
    difficulty: "Trung bình",
    note: "Câu 5-16 luôn có cụm từ, giới từ và giao tiếp; học theo collocation để tránh dịch từng từ.",
  },
  {
    subject: "Tiếng Anh",
    focus: "Pronunciation và Stress",
    weight: 72,
    frequency: "Cao",
    difficulty: "Trung bình",
    note: "Câu 1-4 là nhóm giữ điểm nhanh: -ed, -s/-es, âm dễ nhầm và trọng âm từ 2-4 âm tiết.",
  },
];

const essentialKnowledge = {
  Toan: [
    {
      title: "Bài 1 - Parabol y = ax² và tọa độ điểm",
      knowledge: "Dạng gần như cố định: vẽ/nhận diện parabol, tính giá trị hàm số, xét điểm thuộc đồ thị, tìm hệ số a khi biết điểm.",
      formula: "y = ax²; M(x0; y0) thuộc parabol khi y0 = a.x0²; nếu biết M thì a = y0 / x0² với x0 ≠ 0.",
      steps: ["Lập bảng giá trị đối xứng quanh trục Oy.", "Bình phương x trước rồi nhân hệ số a.", "Khi xét điểm, thay đúng hoành độ vào hàm số.", "Kết luận bằng câu rõ: thuộc/không thuộc đồ thị."],
      commonMistake: "Bình phương sai số âm hoặc vẽ parabol sai chiều khi a < 0.",
    },
    {
      title: "Bài 2 - Phương trình bậc hai và hệ thức Viète",
      knowledge: "Phải chắc điều kiện có nghiệm, nghiệm kép, hai nghiệm phân biệt, tổng-tích nghiệm và biểu thức đối xứng của nghiệm.",
      formula: "Δ = b² - 4ac; Δ' = b'² - ac; x1 + x2 = -b/a; x1x2 = c/a; x1² + x2² = (x1 + x2)² - 2x1x2.",
      steps: ["Đưa phương trình về đúng dạng ax² + bx + c = 0.", "Xét a ≠ 0 và điều kiện của tham số nếu có.", "Tính Δ/Δ' để kết luận số nghiệm.", "Dùng Viète sau khi bảo đảm phương trình có nghiệm.", "Biến đổi biểu thức nghiệm trước khi thay tổng-tích."],
      commonMistake: "Dùng Viète khi chưa xét điều kiện có nghiệm hoặc nhầm dấu tổng nghiệm.",
    },
    {
      title: "Bài 3 - Xác suất, thống kê và đọc dữ liệu",
      knowledge: "Đề mới thường gắn bảng/biểu đồ/tình huống thực tế: tần số, tỉ lệ phần trăm, trung bình cộng, xác suất đơn giản.",
      formula: "P(A) = số kết quả thuận lợi / số kết quả có thể; trung bình = tổng giá trị / số lượng; tỉ lệ % = phần / toàn bộ × 100%.",
      steps: ["Đọc kỹ đơn vị, tổng số mẫu và nhóm cần tính.", "Ghi rõ mẫu số khi tính xác suất/tỉ lệ.", "Rút gọn phân số hoặc đổi ra phần trăm theo yêu cầu.", "Kiểm tra kết quả có nằm trong khoảng hợp lý không."],
      commonMistake: "Lấy sai mẫu số, nhầm tỉ lệ phần trăm với số thập phân hoặc bỏ qua đơn vị.",
    },
    {
      title: "Bài 4 - Lập biểu thức theo biến trong thực tế",
      knowledge: "Dạng TP.HCM hay hỏi chi phí, khuyến mãi, diện tích theo x, số lượng sản phẩm, tiền điện/nước, quãng đường hoặc năng suất.",
      formula: "Tổng tiền = đơn giá × số lượng; sau giảm giá p% còn (100 - p)% giá; diện tích hình chữ nhật = dài × rộng.",
      steps: ["Gọi biến đúng ý nghĩa và đơn vị.", "Biểu diễn từng đại lượng theo biến.", "Lập biểu thức tổng/hiệu/tích theo dữ kiện.", "Rút gọn biểu thức và thay số nếu đề yêu cầu.", "Kết luận theo ngữ cảnh thực tế."],
      commonMistake: "Lập biểu thức đúng đại số nhưng sai ý nghĩa thực tế do hiểu nhầm đơn vị hoặc phần trăm.",
    },
    {
      title: "Bài 5 - Hình học thực tế và đo lường",
      knowledge: "Cần vận dụng diện tích, chu vi, thể tích cho sân, bồn hoa, hộp, ly, bình trụ, mái che, biển quảng cáo.",
      formula: "Tròn: C = 2πr, S = πr²; hộp chữ nhật: V = dài × rộng × cao; trụ: V = πr²h; diện tích xung quanh trụ = 2πrh.",
      steps: ["Nhận diện hình trong tình huống thực tế.", "Đổi đơn vị trước khi thay công thức.", "Phân biệt bán kính và đường kính.", "Ghi công thức, thay số, tính và ghi đơn vị.", "Làm tròn theo yêu cầu đề."],
      commonMistake: "Quên đổi cm/m/lít hoặc lấy đường kính thay cho bán kính.",
    },
    {
      title: "Bài 6 - Phương trình, bất phương trình, hệ phương trình thực tế",
      knowledge: "Phần vận dụng thường gắn chuyển động, năng suất, mua bán, pha trộn, điều kiện tối thiểu/tối đa hoặc so sánh chi phí.",
      formula: "Chuyển động: S = v.t; năng suất: công việc = năng suất × thời gian; bất phương trình dùng khi có ít nhất/nhiều nhất/không vượt quá.",
      steps: ["Chọn ẩn và đặt điều kiện thực tế.", "Lập bảng nếu có nhiều đại lượng.", "Dịch câu chữ thành phương trình/bất phương trình/hệ.", "Giải, đối chiếu điều kiện.", "Trả lời đúng đại lượng đề hỏi."],
      commonMistake: "Giải ra số nhưng không đối chiếu điều kiện nguyên dương, thời gian, số người hoặc số sản phẩm.",
    },
    {
      title: "Bài 7 - Hình học phẳng phân loại",
      knowledge: "Phần 3 điểm thường kiểm tra đường tròn, tứ giác nội tiếp, góc tạo bởi tiếp tuyến/dây, tam giác đồng dạng, hệ thức và cực trị hình học.",
      formula: "Tứ giác nội tiếp: hai góc đối bù hoặc hai góc cùng nhìn một đoạn; đồng dạng: g.g, c.g.c, c.c.c; tiếp tuyến vuông góc bán kính tại tiếp điểm.",
      steps: ["Vẽ hình lớn, ghi giả thiết/kết luận.", "Tìm các góc cùng chắn cung hoặc cùng nhìn một đoạn.", "Chứng minh tứ giác nội tiếp/đồng dạng trước khi suy hệ thức.", "Với câu cuối, tìm quan hệ cố định hoặc dùng bất đẳng thức/cực trị quen thuộc."],
      commonMistake: "Chứng minh theo cảm giác hình vẽ, thiếu căn cứ góc/cung/đồng dạng nên mất điểm nặng.",
    },
    {
      title: "Kỹ năng trình bày bài Toán",
      knowledge: "Muốn giữ điểm chắc phải trình bày đủ điều kiện, công thức, phép biến đổi, đơn vị và câu kết luận. Đây là phần học sinh khá vẫn thường mất điểm.",
      formula: "Khung an toàn: gọi ẩn → điều kiện → lập luận/lập phương trình → giải → đối chiếu → kết luận có đơn vị.",
      steps: ["Không bỏ qua điều kiện của ẩn.", "Ghi công thức trước khi thay số.", "Mỗi phép biến đổi cần hợp lý và không nhảy bước quá xa.", "Kết luận bằng ngôn ngữ của đề bài, không chỉ ghi đáp số."],
      commonMistake: "Làm đúng ý nhưng thiếu điều kiện, thiếu đơn vị hoặc thiếu câu trả lời cuối.",
    },
  ],
  NguVan: [
    {
      title: "Đọc hiểu ngữ liệu ngoài SGK",
      knowledge: "Đề TP.HCM ưu tiên ngữ liệu mới, kiểm tra năng lực đọc thật: nội dung chính, chủ đề, thông điệp, thái độ người viết, chi tiết tiêu biểu.",
      formula: "Câu đọc hiểu đủ ý = trả lời trực tiếp + căn cứ từ văn bản + giải thích ngắn.",
      steps: ["Đọc câu hỏi trước để biết cần tìm gì.", "Gạch từ khóa/câu chủ đề/hình ảnh lặp.", "Trả lời đúng yêu cầu, không lan sang ý khác.", "Dẫn một chi tiết ngắn làm căn cứ.", "Diễn đạt bằng lời của mình nhưng không suy diễn quá xa."],
      commonMistake: "Trả lời theo cảm tính hoặc học thuộc văn mẫu, không bám vào ngữ liệu.",
    },
    {
      title: "Tiếng Việt, liên kết và biện pháp tu từ",
      knowledge: "Cần nhận diện phép liên kết, thành phần câu, từ ngữ biểu cảm và các biện pháp so sánh, ẩn dụ, nhân hóa, điệp, liệt kê, câu hỏi tu từ.",
      formula: "Tác dụng = gọi tên + chỉ dấu hiệu + tác dụng nội dung + tác dụng biểu cảm/nghệ thuật.",
      steps: ["Gọi đúng tên đơn vị tiếng Việt hoặc biện pháp.", "Chỉ ra từ ngữ/hình ảnh làm căn cứ.", "Nêu tác dụng gắn với nội dung cụ thể của ngữ liệu.", "Tránh viết tác dụng chung chung cho mọi đề."],
      commonMistake: "Nêu 'làm câu văn hay hơn' nhưng không nói hay ở điểm nào, nhấn mạnh điều gì.",
    },
    {
      title: "Viết đoạn nghị luận khoảng 200 chữ",
      knowledge: "Dạng lặp nhiều năm: viết đoạn gắn với vấn đề từ ngữ liệu, cần câu chủ đề, luận điểm rõ, dẫn chứng ngắn và bài học hành động.",
      formula: "Đoạn 200 chữ: câu chủ đề → giải thích → 2 luận điểm → dẫn chứng → phản đề nhẹ → bài học.",
      steps: ["Xác định đúng vấn đề cần bàn.", "Viết một câu chủ đề trực tiếp.", "Triển khai 2-3 ý, mỗi ý có giải thích.", "Chọn dẫn chứng gần đời sống học sinh.", "Kết đoạn bằng nhận thức/hành động cụ thể."],
      commonMistake: "Viết nhiều đoạn như bài văn hoặc kể chuyện dài khiến thiếu lập luận.",
    },
    {
      title: "Bài nghị luận xã hội",
      knowledge: "Phần điểm lớn yêu cầu bàn vấn đề đời sống gần học sinh: trách nhiệm, tử tế, vượt khó, đọc sách, môi trường, ứng xử số, tự học.",
      formula: "Dàn ý an toàn: mở vấn đề → giải thích → biểu hiện → ý nghĩa → dẫn chứng → phản biện → giải pháp/bài học → kết.",
      steps: ["Giải thích khái niệm bằng lời rõ ràng.", "Tách luận điểm theo biểu hiện, ý nghĩa, giải pháp.", "Dẫn chứng cụ thể, không bịa quá đà.", "Có một ý phản biện để bài viết sâu hơn.", "Liên hệ bản thân bằng hành động cụ thể."],
      commonMistake: "Viết đạo lý chung chung, thiếu dẫn chứng và thiếu giải pháp thực tế.",
    },
    {
      title: "Cảm thụ và nghị luận văn học",
      knowledge: "Dù tăng ngữ liệu ngoài SGK, học sinh vẫn cần biết phân tích hình ảnh, nhân vật, tình huống, giọng điệu, chủ đề và giá trị nghệ thuật.",
      formula: "Phân tích văn học = chi tiết tiêu biểu + cảm nhận + nhận xét nội dung + nhận xét nghệ thuật.",
      steps: ["Xác định đối tượng cần cảm nhận/phân tích.", "Chọn chi tiết thật tiêu biểu.", "Giải thích chi tiết cho thấy phẩm chất/chủ đề gì.", "Nhận xét nghệ thuật: hình ảnh, giọng điệu, ngôn ngữ, kết cấu.", "Kết nối với thông điệp nhân văn."],
      commonMistake: "Kể lại cốt truyện thay vì phân tích chi tiết và tác dụng nghệ thuật.",
    },
    {
      title: "Dẫn chứng, phản biện và liên hệ bản thân",
      knowledge: "Điểm khá giỏi phụ thuộc nhiều vào khả năng chọn dẫn chứng đúng, phản biện vừa phải và liên hệ không sáo rỗng.",
      formula: "Dẫn chứng tốt = cụ thể + đúng vấn đề + được phân tích; liên hệ tốt = nhận thức + hành động.",
      steps: ["Chuẩn bị nhóm dẫn chứng về học tập, gia đình, cộng đồng, môi trường, công nghệ.", "Sau mỗi dẫn chứng phải có câu phân tích.", "Phản biện một biểu hiện trái ngược nhưng không sa đà.", "Liên hệ bằng việc bản thân sẽ làm, không chỉ hứa chung."],
      commonMistake: "Dẫn chứng nổi tiếng nhưng không liên quan hoặc chỉ nêu tên mà không phân tích.",
    },
    {
      title: "Diễn đạt và sửa lỗi",
      knowledge: "Cần viết đúng chính tả, dùng từ tự nhiên, câu rõ chủ-vị, đoạn có liên kết và tránh lặp từ. Đây là phần dễ mất điểm dù ý đúng.",
      formula: "Câu rõ = chủ ngữ + vị ngữ + ý chính; đoạn rõ = một luận điểm trung tâm + từ nối hợp lý.",
      steps: ["Đọc lại từng câu sau khi viết.", "Cắt câu quá dài hoặc nhiều vế rối.", "Thay từ bị lặp bằng cách diễn đạt khác.", "Kiểm tra dẫn chứng có phục vụ luận điểm không.", "Dành 3-5 phút cuối để sửa lỗi chính tả và dấu câu."],
      commonMistake: "Dùng câu văn hoa mỹ nhưng ý mờ, thiếu liên kết hoặc sai chính tả cơ bản.",
    },
  ],
  TiengAnh: [
    {
      title: "Câu 1-4 - Ngữ âm và trọng âm",
      knowledge: "Cần chắc phát âm đuôi -ed, -s/-es, nguyên âm/phụ âm dễ nhầm và trọng âm từ 2-4 âm tiết.",
      formula: "-ed: /id/ sau /t/, /d/; /t/ sau âm vô thanh; /d/ sau âm còn lại. -s/-es: /s/, /z/, /iz/.",
      steps: ["Đọc thầm từng lựa chọn.", "Xác định âm cuối hoặc số âm tiết.", "Loại các từ có cách đọc/trọng âm giống nhau.", "Chọn từ khác biệt."],
      commonMistake: "Nhìn mặt chữ để đoán mà không xét âm thật của từ.",
    },
    {
      title: "Thì, sự hòa hợp và dạng động từ",
      knowledge: "Các thì hay gặp: hiện tại đơn/tiếp diễn/hoàn thành, quá khứ đơn/tiếp diễn, tương lai; kèm hòa hợp chủ-vị và V-ing/to V/V bare.",
      formula: "Present perfect: have/has + V3; Past continuous: was/were + V-ing; after suggest/enjoy/avoid + V-ing; want/decide/hope + to V.",
      steps: ["Tìm dấu hiệu thời gian.", "Xác định hành động xảy ra khi nào.", "Kiểm tra chủ ngữ số ít/số nhiều.", "Xem động từ trước chỗ trống yêu cầu V-ing, to V hay V nguyên mẫu."],
      commonMistake: "Chỉ nhìn một từ khóa mà bỏ qua ngữ cảnh hoặc quên chia động từ theo chủ ngữ.",
    },
    {
      title: "Cấu trúc câu trọng tâm",
      knowledge: "Đề thường kiểm tra bị động, tường thuật, câu điều kiện, mệnh đề quan hệ, so sánh, so/such...that, enough/too.",
      formula: "Passive: be + V3; Conditional 1: If + present, will + V; Conditional 2: If + past, would/could + V; Relative: who/which/that/whose.",
      steps: ["Nhận diện cấu trúc qua từ khóa.", "Tìm chủ ngữ, động từ, tân ngữ.", "Áp đúng công thức và đổi thì/đại từ nếu cần.", "Đọc lại câu để kiểm tra nghĩa."],
      commonMistake: "Đổi đúng hình thức nhưng sai nghĩa, đặc biệt ở câu điều kiện và tường thuật.",
    },
    {
      title: "Word Forms và từ loại",
      knowledge: "Nhóm phân loại mạnh: xác định danh từ, động từ, tính từ, trạng từ, tiền tố phủ định và danh từ số ít/số nhiều.",
      formula: "a/an/the + N; Adj + N; be/seem/look + Adj; V thường + Adv; preposition + N/V-ing.",
      steps: ["Nhìn vị trí chỗ trống trong câu.", "Xác định từ loại cần điền.", "Biến đổi từ gốc đúng hậu tố/tiền tố.", "Kiểm tra nghĩa tích cực/phủ định.", "Kiểm tra số ít/số nhiều nếu là danh từ."],
      commonMistake: "Dùng đúng từ loại nhưng sai nghĩa phủ định hoặc sai dạng số nhiều.",
    },
    {
      title: "Từ vựng, giới từ, cụm động từ và giao tiếp",
      knowledge: "Cần học từ theo cụm và chủ đề: trường học, môi trường, sức khỏe, công nghệ, cộng đồng; kèm hội thoại cảm ơn, xin lỗi, đề nghị, lời khuyên.",
      formula: "Cụm hay gặp: interested in, good at, proud of, responsible for, take part in, look after, turn off, give up.",
      steps: ["Đọc toàn câu để hiểu tình huống.", "Nhận diện cụm cố định/collocation.", "Loại đáp án không hợp ngữ pháp.", "Với hội thoại, chọn câu đáp tự nhiên theo chức năng giao tiếp."],
      commonMistake: "Dịch từng từ rời rạc, chọn đáp án nghe quen nhưng không hợp ngữ cảnh.",
    },
    {
      title: "Reading Comprehension và Cloze Test",
      knowledge: "Phần nhiều điểm, kiểm tra ý chính, chi tiết, suy luận nhẹ, từ thay thế, liên kết câu, nghĩa của từ trong ngữ cảnh.",
      formula: "Cloze = grammar + word form + collocation + coherence; Reading = main idea + detail + inference + reference.",
      steps: ["Đọc lướt để nắm chủ đề.", "Đọc câu hỏi trước khi tìm đáp án.", "Với cloze, xác định từ loại và ý nghĩa quanh chỗ trống.", "Với reading, quay lại dòng chứa thông tin.", "Không chọn chỉ vì thấy một từ giống trong bài."],
      commonMistake: "Chọn đáp án theo keyword đơn lẻ, không đọc câu trước-sau.",
    },
    {
      title: "Sentence Transformation và guided writing",
      knowledge: "Cần viết lại câu giữ nguyên nghĩa, đúng cấu trúc, đúng thì, đúng từ loại và không thêm ý mới.",
      formula: "because ↔ because of; although ↔ despite/in spite of; so...that ↔ such...that; too ↔ not enough; last ↔ present perfect.",
      steps: ["Xác định cấu trúc gốc và nghĩa chính.", "Chọn cấu trúc tương đương.", "Đổi dạng từ/cụm danh từ nếu cần.", "Giữ đúng thì, chủ ngữ và tân ngữ.", "Đọc lại câu mới để chắc nghĩa không đổi."],
      commonMistake: "Viết đúng mẫu nhưng đổi nghĩa, sai thì hoặc thiếu một thành phần bắt buộc.",
    },
    {
      title: "Chiến thuật làm bài 40 câu",
      knowledge: "Đề Tiếng Anh cần tốc độ và độ chính xác. Học sinh nên giữ điểm chắc ở ngữ âm, giao tiếp, từ loại cơ bản, rồi xử lý đọc hiểu/viết lại câu.",
      formula: "Nhịp làm bài: câu dễ trước → đánh dấu câu phân vân → đọc hiểu sau khi đã giữ điểm ngữ pháp → rà lại word forms và transformation.",
      steps: ["Không dừng quá lâu ở một câu ngữ pháp.", "Làm reading bằng cách đọc câu hỏi trước.", "Ghi chú câu phân vân để quay lại.", "Dành thời gian cuối kiểm tra lỗi nhỏ: -s, -ed, số ít/số nhiều, thì."],
      commonMistake: "Sa vào câu khó quá lâu, thiếu thời gian cho phần đọc hiểu và viết lại câu.",
    },
  ],
};

const essentialRealExamEvidence = {
  Toan: [
    [
      "2022-2026: đều có nhóm hàm số/parabol hoặc đọc tọa độ điểm trên đồ thị.",
      "2022: y = x² và đường thẳng y = -x + 2, tìm giao điểm bằng phương trình hoành độ.",
      "2025-2026: cấu trúc mới vẫn giữ bài nền về hàm số bậc hai để lấy điểm chắc.",
    ],
    [
      "2022-2026: phương trình bậc hai và Viète xuất hiện ổn định ở phần đầu đề.",
      "2022: tính (x1 - x2)² bằng tổng - tích nghiệm, không giải phương trình.",
      "Trong phạm vi 2022-2026: thường hỏi điều kiện nghiệm, nghiệm kép, biểu thức đối xứng của nghiệm.",
    ],
    [
      "2025-2026: xác suất - thống kê được đẩy lên nhóm bắt buộc theo GDPT 2018.",
      "Các đề mô phỏng mới ưu tiên bảng số liệu, tỉ lệ phần trăm, trung bình cộng, xác suất đơn giản.",
      "Dạng này giúp giữ điểm nếu đọc đúng mẫu số và dữ kiện trong bảng/biểu đồ.",
    ],
    [
      "2022: khuyến mãi mua bánh, so sánh cửa hàng A/B.",
      "2022: nhiệt độ khi leo núi theo hàm tuyến tính T = a.h + b.",
      "2023-2026: toán thực tế tiếp tục xuất hiện dày ở bài giữa đề.",
    ],
    [
      "2022: đống cát hình nón, xe cải tiến dạng hộp chữ nhật, yêu cầu đổi đơn vị và tính số chuyến.",
      "2023-2026: hình học thực tế thường gắn diện tích/thể tích, vật dụng đời sống, làm tròn kết quả.",
      "Dạng này dễ mất điểm vì nhầm bán kính - đường kính hoặc quên đổi đơn vị.",
    ],
    [
      "2022: bài SEA Games 31 về bảng đấu, điểm số và số trận hòa.",
      "Trong phạm vi 2022-2026: bài thực tế có thể dẫn tới phương trình, hệ phương trình hoặc bất phương trình.",
      "Dạng câu hỏi 'ít nhất', 'nhiều nhất', 'tiết kiệm bao nhiêu' cần đối chiếu điều kiện nghiệm.",
    ],
    [
      "2022: tam giác nhọn, đường cao, tứ giác nội tiếp, MB.MC = ME.MF, AN vuông góc HN.",
      "2023-2026: hình học phẳng vẫn là phần phân loại 2.5-3 điểm.",
      "Các ý cuối thường cần phối hợp đường tròn, đồng dạng, tiếp tuyến hoặc phương tích.",
    ],
    [
      "Đề thật nhiều năm chấm rất chặt điều kiện, đơn vị và câu kết luận.",
      "Toán thực tế 2022-2026 thường có bối cảnh dài, cần trình bày rõ đại lượng và ý nghĩa đáp số.",
      "Hình học cần căn cứ góc/cung/đồng dạng, không chỉ ghi theo hình vẽ.",
    ],
  ],
  NguVan: [
    [
      "2022: chủ đề 'Bức thông điệp của thời gian', đọc hai văn bản ngoài SGK.",
      "2023: bức thư 'Để những nghĩ suy cất lên thành lời', yêu cầu rút lợi ích/thông điệp.",
      "2024-2026: tiếp tục ưu tiên ngữ liệu mới, yêu cầu hiểu và phản hồi thay vì học thuộc.",
    ],
    [
      "2022: hỏi phép liên kết trong hai câu đầu văn bản 2.",
      "2023-2026: thường yêu cầu chỉ ra thành phần biệt lập, biện pháp tu từ, tác dụng của từ ngữ/hình ảnh.",
      "Điểm nằm ở việc nêu căn cứ cụ thể, không chỉ gọi tên kiến thức tiếng Việt.",
    ],
    [
      "2022: viết về câu hỏi 'Phải chăng chỉ cần thời gian trôi qua, bạn sẽ trưởng thành?'.",
      "2023: bài khoảng 500 chữ với nhan đề 'Nếu những suy nghĩ tốt đẹp không được cất lên thành lời...'.",
      "Các đề mới yêu cầu quan điểm riêng, lập luận rõ và bài học hành động.",
    ],
    [
      "2022-2026: nghị luận xã hội luôn xoay quanh vấn đề gần học sinh: thời gian, trưởng thành, suy nghĩ, trách nhiệm, ứng xử.",
      "Dẫn chứng cần gần đời sống và có phân tích, tránh kể chuyện dài.",
      "Ý phản biện nhẹ giúp bài viết sâu hơn và tránh một chiều.",
    ],
    [
      "2022: cảm nhận hai khổ thơ 'Sang thu' và liên hệ tác phẩm khác.",
      "2023: chọn nghị luận về thơ/tác phẩm gia đình hoặc bài viết cho câu lạc bộ sách.",
      "Đề thường mở nhưng vẫn cần phân tích chi tiết nghệ thuật cụ thể.",
    ],
    [
      "2022-2026: câu liên hệ bản thân hoặc nêu quan điểm xuất hiện thường xuyên trong đọc hiểu/viết.",
      "Dẫn chứng xã hội tốt phải đúng vấn đề, cụ thể và được bình luận.",
      "Liên hệ nên chuyển thành hành động, không chỉ nêu lời hứa chung chung.",
    ],
    [
      "Đề Văn TP.HCM chấm mạnh vào khả năng diễn đạt rõ ý, đúng trọng tâm.",
      "Các bài viết dài dễ mất điểm vì lặp từ, câu quá dài, thiếu liên kết đoạn.",
      "Sửa lỗi diễn đạt giúp nâng điểm thực tế ngay cả khi ý tưởng không quá mới.",
    ],
  ],
  TiengAnh: [
    [
      "2022: lần đầu cấu trúc 40 câu có nhóm ngữ âm rõ ở đầu đề.",
      "2023-2026: câu 1-4 tiếp tục kiểm tra pronunciation/stress.",
      "Đây là nhóm giữ điểm nhanh nếu học quy tắc -ed, -s/-es và trọng âm cơ bản.",
    ],
    [
      "2022-2026: thì và dạng động từ xuất hiện rải trong câu 5-16, cloze và viết lại câu.",
      "Dấu hiệu như since/for, last, when, by the time thường quyết định thì.",
      "Sai hòa hợp chủ-vị hoặc V-ing/to V là lỗi mất điểm phổ biến.",
    ],
    [
      "2022-2026: bị động, tường thuật, câu điều kiện, mệnh đề quan hệ và so sánh lặp lại nhiều năm.",
      "Câu 37-40 thường yêu cầu biến đổi cấu trúc mà vẫn giữ nghĩa.",
      "Cần kiểm tra thì, chủ ngữ, tân ngữ và nghĩa sau khi viết lại.",
    ],
    [
      "2022: word forms gồm advertisement, beneficial, orally, published, disaster, informative.",
      "2023-2026: câu 29-34 tiếp tục là nhóm phân loại mạnh.",
      "Cần xác định từ loại theo vị trí: sau mạo từ, trước danh từ, sau động từ, sau giới từ.",
    ],
    [
      "2022-2026: câu 5-16 luôn có từ vựng, giới từ/cụm cố định và hội thoại.",
      "Câu giao tiếp thường hỏi đề nghị, cảm ơn, chúc mừng, xin lỗi, đồng ý/từ chối.",
      "Học theo cụm giúp tránh dịch từng từ và chọn sai ngữ cảnh.",
    ],
    [
      "2022: reading về water cycle; cloze về cơn bão và tìm chó của hàng xóm.",
      "2023-2026: reading/cloze vẫn chiếm phần điểm lớn và yêu cầu đọc ngữ cảnh.",
      "Câu EXCEPT/True-False cần quay lại bài đọc, không chọn theo từ khóa đơn lẻ.",
    ],
    [
      "2022: rearrange câu về entrance exam/global warming và rewrite câu học tiếng Anh, chờ xe buýt, have something done, suggested that.",
      "2023-2026: sentence transformation vẫn là nhóm câu cuối phân loại.",
      "Chấm tự động chỉ hỗ trợ so sánh đáp án, nhưng khi ôn cần hiểu cấu trúc để tránh đổi nghĩa.",
    ],
    [
      "Đề thật 40 câu cần tốc độ: câu dễ trước, đánh dấu câu phân vân, quay lại cuối giờ.",
      "Word forms và transformation nên được rà chính tả, dạng số ít/số nhiều, thì và dấu câu.",
      "Reading nên đọc câu hỏi trước để tiết kiệm thời gian.",
    ],
  ],
};

const essentialStudyPriorities = {
  Toan: [
    {
      level: "Rất cao",
      target: "Không mất điểm bài nền về hàm số/parabol.",
      drills: ["Luyện thay tọa độ điểm vào parabol.", "Luyện tìm giao điểm parabol - đường thẳng.", "Luyện vẽ nhanh bảng giá trị đối xứng."],
    },
    {
      level: "Rất cao",
      target: "Làm chắc mọi câu Viète và phương trình bậc hai có tham số đơn giản.",
      drills: ["Luyện biến đổi biểu thức nghiệm về tổng - tích.", "Luyện điều kiện có nghiệm trước khi dùng Viète.", "Luyện nhận diện nghiệm kép/hai nghiệm phân biệt."],
    },
    {
      level: "Cao",
      target: "Đọc đúng bảng số liệu và giữ điểm các câu xác suất - thống kê mới.",
      drills: ["Luyện tính tỉ lệ phần trăm từ bảng.", "Luyện xác suất một phép thử.", "Luyện trung bình cộng và nhận xét dữ liệu."],
    },
    {
      level: "Rất cao",
      target: "Dịch được tình huống thực tế thành biểu thức hoặc phương trình.",
      drills: ["Luyện bài giảm giá, chi phí, tiền điện/nước.", "Luyện bài quãng đường - vận tốc - thời gian.", "Luyện lập biểu thức theo biến và thay số."],
    },
    {
      level: "Cao",
      target: "Không sai công thức đo lường và đơn vị trong bài thực tế.",
      drills: ["Luyện hình tròn, hình trụ, hình nón, hình hộp.", "Luyện đổi cm, m, m³, lít.", "Luyện bài làm tròn theo yêu cầu."],
    },
    {
      level: "Cao",
      target: "Giải được bài thực tế nhiều bước có điều kiện nghiệm.",
      drills: ["Luyện lập phương trình/hệ từ bảng dữ kiện.", "Luyện bất phương trình với 'ít nhất', 'không vượt quá'.", "Luyện đối chiếu nghiệm với điều kiện thực tế."],
    },
    {
      level: "Rất cao",
      target: "Ăn điểm các ý đầu hình học và có cơ hội lấy điểm phân loại.",
      drills: ["Luyện tứ giác nội tiếp qua góc.", "Luyện tam giác đồng dạng và hệ thức.", "Luyện góc tạo bởi tiếp tuyến/dây và phương tích cơ bản."],
    },
    {
      level: "Rất cao",
      target: "Giữ điểm trình bày ở tất cả bài, đặc biệt toán thực tế và hình học.",
      drills: ["Luyện viết điều kiện của ẩn.", "Luyện câu kết luận có đơn vị.", "Luyện trình bày hình học theo giả thiết - suy luận - kết luận."],
    },
  ],
  NguVan: [
    {
      level: "Rất cao",
      target: "Đọc văn bản mới và trả lời đúng trọng tâm, có căn cứ.",
      drills: ["Luyện xác định chủ đề/thông điệp.", "Luyện trích chi tiết làm căn cứ.", "Luyện viết câu trả lời 2-3 ý, không lan man."],
    },
    {
      level: "Cao",
      target: "Gọi đúng kiến thức tiếng Việt và nêu được tác dụng cụ thể.",
      drills: ["Luyện phép liên kết và thành phần biệt lập.", "Luyện biện pháp tu từ kèm dấu hiệu.", "Luyện công thức tác dụng gắn nội dung văn bản."],
    },
    {
      level: "Rất cao",
      target: "Viết đoạn/bài ngắn có luận điểm rõ, không lạc đề.",
      drills: ["Luyện câu chủ đề trực tiếp.", "Luyện 2 luận điểm + dẫn chứng ngắn.", "Luyện kết đoạn bằng bài học hành động."],
    },
    {
      level: "Rất cao",
      target: "Xử lý vấn đề đời sống gần học sinh bằng lập luận thuyết phục.",
      drills: ["Luyện giải thích khái niệm.", "Luyện biểu hiện - ý nghĩa - giải pháp.", "Luyện phản biện nhẹ và liên hệ bản thân."],
    },
    {
      level: "Cao",
      target: "Phân tích được chi tiết nghệ thuật thay vì kể lại tác phẩm.",
      drills: ["Luyện phân tích hình ảnh thơ.", "Luyện nhân vật/tình huống truyện.", "Luyện liên hệ tác phẩm khác theo điểm tương đồng."],
    },
    {
      level: "Cao",
      target: "Có dẫn chứng đúng vấn đề và biết bình luận sau dẫn chứng.",
      drills: ["Chuẩn bị dẫn chứng học tập, gia đình, cộng đồng, công nghệ.", "Luyện viết 1 câu phân tích sau dẫn chứng.", "Luyện liên hệ bằng hành động cụ thể."],
    },
    {
      level: "Cao",
      target: "Tăng điểm thực tế bằng diễn đạt rõ, ít lỗi.",
      drills: ["Luyện rút câu quá dài.", "Luyện dùng từ nối đoạn.", "Luyện đọc lại để sửa chính tả, dấu câu và lặp từ."],
    },
  ],
  TiengAnh: [
    {
      level: "Cao",
      target: "Lấy nhanh 3-4 câu đầu bằng quy tắc âm và trọng âm.",
      drills: ["Luyện -ed, -s/-es theo âm cuối.", "Luyện trọng âm danh từ/động từ 2 âm tiết.", "Luyện nhóm nguyên âm dễ nhầm."],
    },
    {
      level: "Rất cao",
      target: "Không mất điểm thì cơ bản, verb forms và hòa hợp chủ-vị.",
      drills: ["Luyện dấu hiệu thì trong câu.", "Luyện V-ing/to V/bare infinitive.", "Luyện subject-verb agreement trong câu dài."],
    },
    {
      level: "Rất cao",
      target: "Làm chắc grammar và câu viết lại giữ nguyên nghĩa.",
      drills: ["Luyện passive, reported speech, conditionals.", "Luyện relative clauses và comparisons.", "Luyện enough/too, so/such...that."],
    },
    {
      level: "Rất cao",
      target: "Ăn điểm nhóm word forms, nhóm phân loại rõ nhất.",
      drills: ["Luyện vị trí danh từ/tính từ/trạng từ.", "Luyện hậu tố và tiền tố phủ định.", "Luyện số ít/số nhiều và nghĩa phù hợp ngữ cảnh."],
    },
    {
      level: "Cao",
      target: "Giảm sai câu từ vựng, giới từ, cụm động từ và giao tiếp.",
      drills: ["Học collocation theo chủ đề.", "Luyện preposition sau tính từ/động từ.", "Luyện hội thoại theo chức năng giao tiếp."],
    },
    {
      level: "Rất cao",
      target: "Giữ điểm reading/cloze, phần nhiều điểm trong đề 40 câu.",
      drills: ["Luyện main idea/detail/inference.", "Luyện cloze theo từ loại và liên kết câu.", "Luyện câu EXCEPT/True-False bằng cách quay lại đoạn văn."],
    },
    {
      level: "Rất cao",
      target: "Tăng điểm câu cuối bằng transformation chính xác.",
      drills: ["Luyện because/because of, although/despite.", "Luyện present perfect với last/since/for.", "Luyện viết lại câu không đổi nghĩa và đúng chính tả."],
    },
    {
      level: "Cao",
      target: "Hoàn thành đề đúng thời gian và hạn chế lỗi nhỏ.",
      drills: ["Luyện đề 40 câu có bấm giờ.", "Luyện bỏ qua câu khó để quay lại.", "Luyện rà -s, -ed, số nhiều, thì và dấu câu cuối giờ."],
    },
  ],
};

const yearlyExamStats = [
  {
    year: "2026",
    subject: "Toán",
    pattern: "7 bài theo GDPT 2018",
    topics: "Parabol, Viète, xác suất-thống kê, toán thực tế, hình học phẳng",
    score: "10 điểm",
    level: "Vận dụng tăng",
    note: "Toán thực tế xuất hiện dày ở bài 3-6; hình học phẳng vẫn là phần phân loại.",
  },
  {
    year: "2026",
    subject: "Ngữ văn",
    pattern: "2 phần tích hợp đọc hiểu và viết",
    topics: "Ngữ liệu ngoài SGK, viết đoạn, nghị luận xã hội",
    score: "10 điểm",
    level: "Đọc hiểu - viết",
    note: "Không thể học tủ văn mẫu; cần đọc hiểu văn bản mới và viết có quan điểm.",
  },
  {
    year: "2026",
    subject: "Tiếng Anh",
    pattern: "40 câu, 4 phần",
    topics: "Ngữ âm, từ vựng-ngữ pháp, đọc hiểu, word forms, viết lại câu",
    score: "10 điểm",
    level: "Trung bình - cao",
    note: "Word forms và sentence transformation là nhóm dễ phân hóa.",
  },
  {
    year: "2025",
    subject: "Toán",
    pattern: "7 bài theo GDPT 2018",
    topics: "Parabol, Viète, thống kê-xác suất, toán thực tế, hình học phẳng",
    score: "10 điểm",
    level: "Vận dụng tăng",
    note: "Bắt đầu thể hiện rõ cấu trúc mới, tăng dữ liệu thực tế và đọc hiểu tình huống.",
  },
  {
    year: "2025",
    subject: "Ngữ văn",
    pattern: "2 phần tích hợp đọc hiểu và viết",
    topics: "Ngữ liệu ngoài SGK, quan điểm cá nhân, nghị luận xã hội",
    score: "10 điểm",
    level: "Đọc hiểu - viết",
    note: "Tiếp tục giảm học thuộc văn mẫu, yêu cầu đọc hiểu văn bản mới và lập luận riêng.",
  },
  {
    year: "2025",
    subject: "Tiếng Anh",
    pattern: "40 câu, 4 phần",
    topics: "Ngữ âm, grammar-vocabulary, reading/cloze, word forms, transformation",
    score: "10 điểm",
    level: "Trung bình - cao",
    note: "Reading/cloze và nhóm câu cuối vẫn là phần phân loại rõ.",
  },
  {
    year: "2024",
    subject: "Toán",
    pattern: "Đề theo cấu trúc quen thuộc",
    topics: "Hàm số, phương trình bậc hai, toán thực tế, hình học",
    score: "10 điểm",
    level: "Nhận biết - vận dụng",
    note: "Giữ lõi đại số và hình học, toán thực tế xuất hiện đều.",
  },
  {
    year: "2024",
    subject: "Ngữ văn",
    pattern: "Đọc hiểu + viết",
    topics: "Ngữ liệu ngoài SGK, tiếng Việt, nghị luận xã hội, văn học",
    score: "10 điểm",
    level: "Thông hiểu - vận dụng",
    note: "Tập trung đọc hiểu văn bản mới, nêu thông điệp và viết có quan điểm.",
  },
  {
    year: "2024",
    subject: "Tiếng Anh",
    pattern: "40 câu, 4 phần",
    topics: "Từ vựng-ngữ pháp, reading, cloze, word forms, viết lại câu",
    score: "10 điểm",
    level: "Trung bình - cao",
    note: "Cần chắc cụm từ, cấu trúc câu và đọc hiểu theo ngữ cảnh.",
  },
  {
    year: "2023",
    subject: "Toán",
    pattern: "Đề theo cấu trúc quen thuộc",
    topics: "Parabol, Viète, toán thực tế, hình học phẳng",
    score: "10 điểm",
    level: "Nhận biết - vận dụng cao",
    note: "Hình học phẳng và toán thực tế tiếp tục giữ vai trò phân hóa.",
  },
  {
    year: "2023",
    subject: "Ngữ văn",
    pattern: "Đọc hiểu + nghị luận",
    topics: "Bức thư/ngữ liệu ngoài SGK, thành phần biệt lập, nghị luận xã hội, lựa chọn văn học",
    score: "10 điểm",
    level: "Thông hiểu - vận dụng",
    note: "Đề mở, yêu cầu học sinh trình bày suy nghĩ và chọn hướng viết phù hợp.",
  },
  {
    year: "2023",
    subject: "Tiếng Anh",
    pattern: "40 câu, 4 phần",
    topics: "Grammar-vocabulary, signs/notices, cloze, reading, word forms, transformation",
    score: "10 điểm",
    level: "Trung bình - cao",
    note: "Câu đọc hiểu và viết lại câu cần bám nghĩa, tránh chọn theo từ khóa đơn lẻ.",
  },
  {
    year: "2022",
    subject: "Toán",
    pattern: "Đề theo cấu trúc quen thuộc",
    topics: "Parabol, Viète, BMI, khuyến mãi, hình nón/hộp, SEA Games, hình học nội tiếp",
    score: "10 điểm",
    level: "Nhận biết - vận dụng cao",
    note: "Nhiều tình huống thực tế cụ thể; hình học vẫn là phần phân loại lớn.",
  },
  {
    year: "2022",
    subject: "Ngữ văn",
    pattern: "Đọc hiểu + viết",
    topics: "Bức thông điệp của thời gian, phép liên kết, nghị luận trưởng thành, Sang thu",
    score: "10 điểm",
    level: "Thông hiểu - vận dụng",
    note: "Yêu cầu đọc hiểu văn bản ngoài SGK và liên hệ quan điểm cá nhân.",
  },
  {
    year: "2022",
    subject: "Tiếng Anh",
    pattern: "40 câu, 4 phần",
    topics: "Pronunciation/stress, grammar-vocabulary, water cycle reading, cloze, word forms, transformation",
    score: "10 điểm",
    level: "Trung bình - cao",
    note: "Cấu trúc 40 câu ổn định; word forms và transformation cần độ chính xác cao.",
  },
];

const repeatedPatterns = {
  Toan: [
    "Parabol/hàm số bậc hai: xét điểm thuộc đồ thị, tìm hệ số, giao điểm parabol - đường thẳng.",
    "Phương trình bậc hai và Viète: điều kiện nghiệm, tổng - tích, biểu thức đối xứng của nghiệm.",
    "Xác suất - thống kê: bảng số liệu, tỉ lệ phần trăm, trung bình cộng, xác suất đơn giản, tăng rõ ở 2025-2026.",
    "Toán thực tế nhiều bước: BMI, khuyến mãi, nhiệt độ, điểm số thi đấu, chi phí, điều kiện ít nhất/nhiều nhất.",
    "Hình học thực tế/đo lường: hình tròn, hình nón, hình trụ, hình hộp; đổi đơn vị và làm tròn.",
    "Hình học phẳng phân loại: tứ giác nội tiếp, đường tròn, đồng dạng, tiếp tuyến, chứng minh hệ thức.",
  ],
  NguVan: [
    "Đọc hiểu ngữ liệu ngoài SGK: văn bản văn học, nghị luận/thông tin, thư, đoạn trích đời sống.",
    "Câu hỏi thông điệp/ý nghĩa/quan điểm: trả lời bằng căn cứ từ văn bản, không học thuộc văn mẫu.",
    "Tiếng Việt trong ngữ cảnh: phép liên kết, thành phần biệt lập, biện pháp tu từ, tác dụng từ ngữ/hình ảnh.",
    "Viết đoạn/bài theo vấn đề từ ngữ liệu: câu chủ đề, luận điểm, dẫn chứng, phản biện nhẹ, hành động.",
    "Nghị luận xã hội gần học sinh: trưởng thành, suy nghĩ tích cực, cảm xúc, trách nhiệm, tự học, ứng xử.",
    "Cảm thụ/nghị luận văn học hoặc đề mở: phân tích chi tiết nghệ thuật, liên hệ tác phẩm/trải nghiệm đọc.",
  ],
  TiengAnh: [
    "Pronunciation/stress đầu đề: -ed, -s/-es, âm dễ nhầm, trọng âm 2-4 âm tiết.",
    "Grammar-vocabulary câu 5-16: thì, dạng động từ, giới từ, cụm từ, biển báo/thông báo, hội thoại.",
    "Cloze test câu 17-22: từ loại, collocation, liên từ, giới từ, mạch nghĩa trong đoạn.",
    "Reading câu 23-28: True/False, main idea, detail, inference, reference, câu EXCEPT/NOT mentioned.",
    "Word forms câu 29-34: noun/verb/adj/adv, tiền tố/hậu tố, nghĩa phủ định, số ít/số nhiều.",
    "Guided writing/transformation câu 35-40: viết lại câu giữ nghĩa, rearrangement, passive, conditional, reported speech, present perfect.",
  ],
};

const scoreTargets = {
  Toan: [
    { level: "Phải biết để qua kỳ thi", detail: "Làm chắc bài 1-3, biết công thức diện tích/thể tích cơ bản, giải được phương trình đơn giản." },
    { level: "Nên chắc để đạt 6.5-7.5", detail: "Làm ổn toán thực tế, Viète, xác suất-thống kê, trình bày đầy đủ điều kiện và kết luận." },
    { level: "Muốn 8+", detail: "Luyện bài 6 và bài 7 hình học phẳng, chứng minh hệ thức, xử lý câu vận dụng cao có nhiều bước." },
  ],
  NguVan: [
    { level: "Phải biết để qua kỳ thi", detail: "Trả lời đúng câu đọc hiểu cơ bản, viết đoạn có câu chủ đề và không lạc đề." },
    { level: "Nên chắc để đạt 6.5-7.5", detail: "Có luận điểm rõ, dẫn chứng phù hợp, biết giải thích và liên hệ vấn đề đời sống." },
    { level: "Muốn 8+", detail: "Diễn đạt sâu, có phản biện, dẫn chứng chọn lọc, phân tích nghệ thuật thay vì kể lại." },
  ],
  TiengAnh: [
    { level: "Phải biết để qua kỳ thi", detail: "Nắm thì cơ bản, từ loại, giới từ phổ biến, đọc hiểu câu hỏi trực tiếp." },
    { level: "Nên chắc để đạt 6.5-7.5", detail: "Làm ổn word forms, cloze test, reading, passive/conditional/reported speech." },
    { level: "Muốn 8+", detail: "Chính xác ở sentence transformation, đọc hiểu suy luận, tránh lỗi nhỏ về dạng từ và thì." },
  ],
};

const commonMistakes = {
  Toan: [
    "Thiếu điều kiện của ẩn hoặc không đối chiếu điều kiện.",
    "Nhầm bán kính với đường kính, quên đổi đơn vị.",
    "Sai dấu trong hệ thức Viète.",
    "Chứng minh hình học thiếu căn cứ, chỉ suy luận theo hình vẽ.",
    "Có đáp số nhưng thiếu câu kết luận theo ngữ cảnh.",
  ],
  NguVan: [
    "Không trả lời đúng trọng tâm câu hỏi đọc hiểu.",
    "Nêu biện pháp tu từ nhưng không phân tích tác dụng.",
    "Viết đoạn lan man, thiếu câu chủ đề.",
    "Dẫn chứng chung chung hoặc không liên quan luận điểm.",
    "Kể lại tác phẩm thay vì phân tích chi tiết.",
  ],
  TiengAnh: [
    "Chia sai thì do bỏ qua dấu hiệu thời gian.",
    "Nhầm tính từ/trạng từ trong word forms.",
    "Viết lại câu đúng cấu trúc nhưng đổi nghĩa.",
    "Chọn đáp án đọc hiểu theo từ khóa đơn lẻ, không xét ngữ cảnh.",
    "Sai giới từ/cụm cố định vì học từ rời rạc.",
  ],
};

const questionWeightRecommendations = [
  { subject: "Toán", current: "600 câu đã tái phân bổ", recommended: "Ưu tiên Hình học phẳng, Toán thực tế, Phương trình bậc hai, Xác suất-thống kê; giữ đủ câu nền cho parabol, đồ thị, hình học thực tế." },
  { subject: "Ngữ văn", current: "600 câu đã tái phân bổ", recommended: "Ưu tiên đọc hiểu ngữ liệu ngoài SGK, nghị luận xã hội, viết đoạn/bài, dẫn chứng và sửa lỗi diễn đạt theo đề thật." },
  { subject: "Tiếng Anh", current: "900 câu đã tái phân bổ", recommended: "Ưu tiên Word Forms, Sentence Transformation, Reading Comprehension, Cloze Test; vẫn giữ nhịp 40 câu với ngữ âm, ngữ pháp và giao tiếp." },
];

const state = {
  questions: [],
  filtered: [],
  current: null,
  answered: 0,
  correct: 0,
  xp: 120,
  favorites: new Set(),
  history: [],
};

const $ = (selector) => document.querySelector(selector);

function topicLabel(topic) {
  return topicNames[topic] || topic;
}

const elements = {
  subjectFilter: $("#subjectFilter"),
  topicFilter: $("#topicFilter"),
  levelFilter: $("#levelFilter"),
  questionSubject: $("#questionSubject"),
  questionLevel: $("#questionLevel"),
  questionTitle: $("#questionTitle"),
  choices: $("#choices"),
  freeAnswerWrap: $("#freeAnswerWrap"),
  freeAnswer: $("#freeAnswer"),
  feedback: $("#feedback"),
  checkAnswer: $("#checkAnswer"),
  nextQuestion: $("#nextQuestion"),
  favoriteQuestion: $("#favoriteQuestion"),
  answeredValue: $("#answeredValue"),
  accuracyValue: $("#accuracyValue"),
  xpValue: $("#xpValue"),
  historyList: $("#historyList"),
  weakList: $("#weakList"),
  subjectBars: $("#subjectBars"),
  examStatsSummary: $("#examStatsSummary"),
  examTrendList: $("#examTrendList"),
  essentialList: $("#essentialList"),
  yearlyStatsBody: $("#yearlyStatsBody"),
  repeatedPatternList: $("#repeatedPatternList"),
  scoreTargetList: $("#scoreTargetList"),
  commonMistakeList: $("#commonMistakeList"),
  questionWeightList: $("#questionWeightList"),
  mockExam: $("#mockExam"),
  realExamSummary: $("#realExamSummary"),
};

function loadQuestions() {
  if (Array.isArray(window.QUESTION_BANK) && window.QUESTION_BANK.length) {
    state.questions = window.QUESTION_BANK;
  } else {
    console.warn("Không tìm thấy QUESTION_BANK, dùng dữ liệu demo.");
    state.questions = FALLBACK_QUESTIONS;
  }

  state.filtered = [...state.questions];
  renderTopicOptions();
  renderQuestion();
  renderSubjectBars();
  renderExamStats("Toán");
  renderEssentialKnowledge("Toan");
  renderYearlyStats();
  renderRepeatedPatterns("Toan");
  renderScoreTargets("Toan");
  renderCommonMistakes("Toan");
  renderQuestionWeightRecommendations();
  initRealExams();
}

function frequencyScore(value) {
  if (value === "Rất cao") return 100;
  if (value === "Cao") return 82;
  if (value === "Trung bình") return 62;
  return 45;
}

function renderExamStats(selectedSubject = "Toán") {
  const subjectCounts = examStats.reduce((acc, item) => {
    acc[item.subject] = (acc[item.subject] || 0) + 1;
    return acc;
  }, {});

  elements.examStatsSummary.innerHTML = [
    { label: "Môn thi bắt buộc", value: "3", note: "Toán, Ngữ văn, Tiếng Anh" },
    { label: "Cấu trúc Toán", value: "7-8 bài", note: "2022-2024 thiên 8 bài; 2025-2026 thiên 7 bài" },
    { label: "Tiếng Anh", value: "40 câu", note: "90 phút, 4 nhóm kỹ năng" },
    { label: "Trọng tâm ôn", value: `${Object.keys(subjectCounts).length} môn`, note: "Học theo ma trận, không học tủ" },
  ]
    .map((item) => `
      <article class="mini-stat">
        <span>${item.label}</span>
        <strong>${item.value}</strong>
        <small>${item.note}</small>
      </article>
    `)
    .join("");

  const trends = examStats.filter((item) => item.subject === selectedSubject);
  elements.examTrendList.innerHTML = trends
    .map((item) => {
      const score = item.weight || frequencyScore(item.frequency);
      return `
        <div class="trend-row">
          <div>
            <strong>${item.subject}: ${item.focus}</strong>
            <p>${item.note}</p>
          </div>
          <div class="trend-meter" aria-label="Mức ưu tiên ${score}/100">
            <span style="width: ${score}%"></span>
          </div>
          <small>${score}/100 · ${item.frequency} · ${item.difficulty}</small>
        </div>
      `;
    })
    .join("");
}

function renderEssentialKnowledge(subject) {
  if (!elements.essentialList) return;
  const items = essentialKnowledge[subject] || [];
  elements.essentialList.innerHTML = items
    .map((item, index) => {
      const evidence = essentialRealExamEvidence[subject]?.[index] || [];
      const priority = essentialStudyPriorities[subject]?.[index];
      return `
        <li class="essential-item">
          <button class="essential-toggle" type="button" data-essential-index="${index}" aria-expanded="false">
            <span>${escapeHtml(item.title)}</span>
            <small>Xem chi tiết</small>
          </button>
          <div class="essential-detail" hidden>
            <div class="essential-memory-grid">
              <section class="memory-card knowledge-card">
                <span>Kiến thức cốt lõi</span>
                <p>${escapeHtml(item.knowledge)}</p>
              </section>
              <section class="memory-card formula-card">
                <span>Công thức / Cấu trúc cần thuộc</span>
                <p>${escapeHtml(item.formula)}</p>
              </section>
            </div>
            ${evidence.length ? `
              <div class="essential-evidence">
                <b>Đề thật đã ra:</b>
                <ul>${evidence.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>
              </div>
            ` : ""}
            ${priority ? `
              <div class="essential-priority">
                <div>
                  <b>Ưu tiên ôn:</b>
                  <span>${escapeHtml(priority.level)}</span>
                </div>
                <p><b>Mục tiêu:</b> ${escapeHtml(priority.target)}</p>
                <div>
                  <b>Nên luyện:</b>
                  <ul>${priority.drills.map((drill) => `<li>${escapeHtml(drill)}</li>`).join("")}</ul>
                </div>
              </div>
            ` : ""}
            <div>
              <b>Cách làm:</b>
              <ol>${item.steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
            </div>
            <p><b>Lỗi thường gặp:</b> ${escapeHtml(item.commonMistake)}</p>
          </div>
        </li>
      `;
    })
    .join("");
  bindEssentialDetailToggles();
}

function renderYearlyStats() {
  elements.yearlyStatsBody.innerHTML = yearlyExamStats
    .map((item) => `
      <tr>
        <td>${escapeHtml(item.year)}</td>
        <td>${escapeHtml(item.subject)}</td>
        <td>${escapeHtml(item.pattern)}</td>
        <td>${escapeHtml(item.topics)}</td>
        <td>${escapeHtml(item.level)}</td>
        <td>${escapeHtml(item.note)}</td>
      </tr>
    `)
    .join("");
}

function renderRepeatedPatterns(subject) {
  const items = repeatedPatterns[subject] || [];
  elements.repeatedPatternList.innerHTML = items
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function renderScoreTargets(subject) {
  const items = scoreTargets[subject] || [];
  elements.scoreTargetList.innerHTML = items
    .map((item) => `
      <div class="score-target-item">
        <strong>${escapeHtml(item.level)}</strong>
        <p>${escapeHtml(item.detail)}</p>
      </div>
    `)
    .join("");
}

function renderCommonMistakes(subject) {
  const items = commonMistakes[subject] || [];
  elements.commonMistakeList.innerHTML = items
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function renderQuestionWeightRecommendations() {
  if (!elements.questionWeightList) return;
  elements.questionWeightList.innerHTML = questionWeightRecommendations
    .map((item) => `
      <div class="recommendation-item">
        <strong>${escapeHtml(item.subject)}</strong>
        <p><b>Hiện tại:</b> ${escapeHtml(item.current)}</p>
        <p><b>Nên chỉnh:</b> ${escapeHtml(item.recommended)}</p>
      </div>
    `)
    .join("");
}

function initRealExams() {
  if (!elements.realExamSummary) return;

  const data = window.REAL_EXAMS;
  if (!data?.exams?.length) {
    elements.realExamSummary.innerHTML = `
      <article class="real-exam-empty">
        Chưa có dữ liệu đề thi thật. Kiểm tra file <code>web-html/real-exams-data.js</code>.
      </article>
    `;
    return;
  }

  renderRealExams();
}

function renderRealExams() {
  const data = window.REAL_EXAMS;
  if (!data?.exams?.length || !elements.realExamSummary) return;

  const yearCount = new Set(data.exams.map((exam) => exam.year)).size;
  const verbatimCount = data.exams.filter((exam) => exam.contentStatus === "verbatim_text_available").length;
  const latestYear = Math.max(...data.exams.map((exam) => exam.year));
  elements.realExamSummary.innerHTML = `
    <article class="mini-stat">
      <span>Năm đã lưu</span>
      <strong>${yearCount}</strong>
      <small>${data.years.join(", ")}</small>
    </article>
    <article class="mini-stat">
      <span>Bản ghi đề</span>
      <strong>${data.exams.length}</strong>
      <small>${data.subjects.length} môn mỗi năm</small>
    </article>
    <article class="mini-stat real-exam-note">
      <span>Đã nhập text</span>
      <strong>${verbatimCount}</strong>
      <small>Mới nhất: ${latestYear}; xem chi tiết ở trang riêng.</small>
    </article>
  `;
}

function bindEssentialDetailToggles() {
  document.querySelectorAll("[data-essential-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const detail = button.nextElementSibling;
      const isOpen = !detail.hidden;
      detail.hidden = isOpen;
      button.setAttribute("aria-expanded", String(!isOpen));
      button.querySelector("small").textContent = isOpen ? "Xem chi tiết" : "Ẩn chi tiết";
    });
  });
}

function renderTopicOptions() {
  const currentSubject = elements.subjectFilter.value;
  if (!currentSubject) {
    elements.topicFilter.innerHTML = `<option value="all">Tất cả chuyên đề</option>`;
    return;
  }

  const topics = [...new Set(
    state.questions
      .filter((question) => question.monHoc === currentSubject)
      .map((question) => question.chuyenDe),
  )].sort((a, b) => topicLabel(a).localeCompare(topicLabel(b), "vi"));

  elements.topicFilter.innerHTML = `<option value="all">Tất cả chuyên đề</option>`;
  topics.forEach((topic) => {
    const option = document.createElement("option");
    option.value = topic;
    option.textContent = topicLabel(topic);
    elements.topicFilter.appendChild(option);
  });
}

function applyFilters() {
  const subject = elements.subjectFilter.value;
  const topic = elements.topicFilter.value;
  const level = elements.levelFilter.value;

  if (!subject) {
    state.filtered = [];
    renderQuestion();
    renderSubjectBars();
    return;
  }

  state.filtered = state.questions.filter((question) => {
    const matchSubject = question.monHoc === subject;
    const matchTopic = topic === "all" || question.chuyenDe === topic;
    const matchLevel = level === "all" || question.mucDo === level;
    return matchSubject && matchTopic && matchLevel;
  });

  renderQuestion();
  renderSubjectBars();
}

function pickQuestion() {
  if (!state.filtered.length) return null;
  const index = Math.floor(Math.random() * state.filtered.length);
  return state.filtered[index];
}

function renderPracticeQuestionPrompt(question) {
  const prompt = String(question?.deBai || "");
  if (question?.monHoc !== "NguVan") return escapeHtml(prompt);

  const match = prompt.match(/^(.+?:)\s*[“"]([\s\S]+)[”"]\s*(Câu hỏi:[\s\S]*)$/);
  if (!match) {
    return `
      <div class="literature-question-prompt">
        <section class="literature-task">
          ${escapeHtml(prompt)}
        </section>
      </div>
    `;
  }

  return `
    <div class="literature-question-prompt">
      <p class="literature-intro">${escapeHtml(match[1])}</p>
      <section class="literature-passage" aria-label="Ngữ liệu">
        <strong>Ngữ liệu</strong>
        <div>${escapeHtml(match[2])}</div>
      </section>
      <section class="literature-task">
        ${escapeHtml(match[3])}
      </section>
    </div>
  `;
}

function renderQuestion() {
  if (!elements.subjectFilter.value) {
    state.current = null;
    elements.feedback.hidden = true;
    elements.feedback.className = "feedback";
    elements.freeAnswer.value = "";
    elements.choices.innerHTML = "";
    elements.freeAnswerWrap.hidden = true;
    elements.questionSubject.textContent = "Chưa chọn môn";
    elements.questionLevel.textContent = "...";
    elements.questionTitle.textContent = "Chọn môn học để bắt đầu luyện tập.";
    elements.checkAnswer.disabled = true;
    elements.nextQuestion.disabled = true;
    elements.favoriteQuestion.disabled = true;
    return;
  }

  const question = pickQuestion();
  state.current = question;
  elements.feedback.hidden = true;
  elements.feedback.className = "feedback";
  elements.freeAnswer.value = "";
  elements.choices.innerHTML = "";
  elements.checkAnswer.disabled = false;
  elements.nextQuestion.disabled = false;
  elements.favoriteQuestion.disabled = false;

  if (!question) {
    elements.questionSubject.textContent = "Không có dữ liệu";
    elements.questionLevel.textContent = "...";
    elements.questionTitle.textContent = "Không tìm thấy câu hỏi phù hợp với bộ lọc.";
    elements.freeAnswerWrap.hidden = true;
    elements.checkAnswer.disabled = true;
    elements.favoriteQuestion.disabled = true;
    return;
  }

  elements.questionSubject.textContent = subjectNames[question.monHoc] || question.monHoc;
  elements.questionLevel.textContent = levelNames[question.mucDo] || question.mucDo;
  elements.questionTitle.innerHTML = renderPracticeQuestionPrompt(question);

  if (question.luaChon?.length) {
    elements.freeAnswerWrap.hidden = true;
    question.luaChon.forEach((choice, index) => {
      const id = `choice-${index}`;
      const label = document.createElement("label");
      label.className = "choice";
      label.innerHTML = `<input type="radio" name="choice" value="${escapeHtml(choice)}" id="${id}" /> <span>${escapeHtml(choice)}</span>`;
      elements.choices.appendChild(label);
    });
  } else {
    elements.freeAnswerWrap.hidden = false;
  }
}

function normalize(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function selectedAnswer() {
  const checked = document.querySelector("input[name='choice']:checked");
  return checked ? checked.value : elements.freeAnswer.value;
}

function checkAnswer() {
  if (!state.current) return;

  const answer = selectedAnswer();
  const expected = state.current.dapAn;
  const hasChoice = state.current.luaChon?.length > 0;
  const isCorrect = hasChoice
    ? normalize(answer) === normalize(expected)
    : normalize(answer) && normalize(expected).includes(normalize(answer));

  state.answered += 1;
  if (isCorrect) {
    state.correct += 1;
    state.xp += 15;
  } else {
    state.xp += 5;
  }

  state.history.unshift({
    id: state.current.id,
    subject: state.current.monHoc,
    topic: state.current.chuyenDe,
    correct: isCorrect,
  });
  state.history = state.history.slice(0, 6);

  elements.feedback.hidden = false;
  elements.feedback.className = `feedback ${isCorrect ? "correct" : "incorrect"}`;
  elements.feedback.innerHTML = `
    <strong>${isCorrect ? "Đúng rồi!" : "Cần xem lại."}</strong>
    <p><b>Đáp án:</b> ${escapeHtml(expected)}</p>
    <p><b>Lời giải:</b> ${escapeHtml(state.current.loiGiai)}</p>
    <p><b>Mẹo:</b> ${escapeHtml(state.current.meoLamBai)}</p>
  `;

  renderProgress();
  renderHistory();
  renderWeakness();
}

function renderProgress() {
  const accuracy = state.answered ? Math.round((state.correct / state.answered) * 100) : 0;
  elements.answeredValue.textContent = state.answered;
  elements.accuracyValue.textContent = `${accuracy}%`;
  elements.xpValue.textContent = state.xp;
}

function renderHistory() {
  elements.historyList.innerHTML = "";
  state.history.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${subjectNames[item.subject]} - ${topicLabel(item.topic)}: ${item.correct ? "đúng" : "sai"}`;
    elements.historyList.appendChild(li);
  });
}

function renderWeakness() {
  const wrongTopics = state.history.filter((item) => !item.correct).map((item) => item.topic);
  const topics = wrongTopics.length ? [...new Set(wrongTopics)] : ["Hình học phẳng", "Viết lại câu", "Nghị luận xã hội"];
  elements.weakList.innerHTML = topics.map((topic) => `<span>${escapeHtml(topicLabel(topic))}</span>`).join("");
}

function renderSubjectBars() {
  if (!elements.subjectBars) return;
  const source = state.filtered.length ? state.filtered : state.questions;
  const counts = source.reduce((acc, question) => {
    acc[question.monHoc] = (acc[question.monHoc] || 0) + 1;
    return acc;
  }, {});
  const max = Math.max(...Object.values(counts), 1);

  elements.subjectBars.innerHTML = Object.entries(subjectNames)
    .map(([key, label]) => {
      const value = counts[key] || 0;
      const width = Math.round((value / max) * 100);
      return `
        <div class="bar-row">
          <strong>${label}</strong>
          <div class="bar-track"><div class="bar-fill" style="width: ${width}%"></div></div>
          <span>${value}</span>
        </div>
      `;
    })
    .join("");
}

function takeQuestionsByTopic(subject, topic, count, usedIds) {
  const available = state.questions.filter((question) => (
    question.monHoc === subject &&
    question.chuyenDe === topic &&
    !usedIds.has(question.id)
  ));

  const selected = available.slice(0, count);
  selected.forEach((question) => usedIds.add(question.id));
  return selected;
}

function buildMockExamQuestions(subject) {
  const usedIds = new Set();
  const blueprintBySubject = {
    Toan: mathExamBlueprint,
    NguVan: literatureExamBlueprint,
    TiengAnh: englishExamBlueprint,
  };
  const targetCountBySubject = {
    Toan: 7,
    NguVan: 9,
    TiengAnh: 40,
  };
  const blueprint = blueprintBySubject[subject] || [];
  const targetCount = targetCountBySubject[subject] || 8;
  const selected = blueprint.flatMap(({ topic, count }) => (
    takeQuestionsByTopic(subject, topic, count, usedIds)
  ));

  if (selected.length < targetCount) {
    const fallback = state.questions
      .filter((question) => question.monHoc === subject && !usedIds.has(question.id))
      .slice(0, targetCount - selected.length);
    fallback.forEach((question) => usedIds.add(question.id));
    selected.push(...fallback);
  }

  return selected.slice(0, targetCount);
}

function renderMockAnswerControl(question, questionIndex, subject) {
  if (subject === "TiengAnh" && question.luaChon?.length) {
    return `
      <div class="mock-answer-control">
        <b>Câu trả lời của bạn</b>
        <div class="mock-checkbox-group" role="group" aria-label="Chọn đáp án câu ${questionIndex + 1}">
          ${question.luaChon.map((choice, choiceIndex) => {
            const id = `mock-${questionIndex}-${choiceIndex}`;
            return `
              <label class="mock-checkbox-choice" for="${id}">
                <input
                  id="${id}"
                  type="checkbox"
                  name="mock-question-${questionIndex}"
                  value="${escapeHtml(choice)}"
                  data-mock-checkbox
                />
                <span>${escapeHtml(choice)}</span>
              </label>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }

  return question.luaChon?.length
    ? `<ul class="mock-choices">${question.luaChon.map((choice) => `<li>${escapeHtml(choice)}</li>`).join("")}</ul>`
    : "";
}

function createMockExam(subject) {
  const questions = buildMockExamQuestions(subject);
  const template = examTemplates[subject] || [];
  elements.mockExam.hidden = false;
  elements.mockExam.innerHTML = `
    <h3>Đề mô phỏng ${subjectNames[subject]}</h3>
    <p><b>Số câu:</b> ${questions.length}${subject === "TiengAnh" ? " / 40 câu theo cấu trúc đề Tiếng Anh TP.HCM" : " câu/bài mẫu chọn theo blueprint đề thật 2022-2026"}</p>
    <p><b>Cấu trúc:</b></p>
    <ul>${template.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <p><b>Câu hỏi từ ngân hàng:</b></p>
    <ol class="mock-question-list">
      ${questions.map((question, index) => `
        <li>
          <article class="mock-question-item">
            <p>${escapeHtml(question.deBai)}</p>
            ${renderMockAnswerControl(question, index, subject)}
            <details>
              <summary>Đáp án và lời giải</summary>
              <p><b>Đáp án:</b> ${escapeHtml(question.dapAn)}</p>
              <p><b>Lời giải:</b> ${escapeHtml(question.loiGiai)}</p>
              <p><b>Mẹo làm bài:</b> ${escapeHtml(question.meoLamBai)}</p>
            </details>
          </article>
        </li>
      `).join("")}
    </ol>
  `;
  elements.mockExam.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindEvents() {
  $("[data-nav-toggle]").addEventListener("click", () => {
    $("[data-nav-links]").classList.toggle("open");
  });

  elements.subjectFilter.addEventListener("change", () => {
    renderTopicOptions();
    applyFilters();
  });
  elements.topicFilter.addEventListener("change", applyFilters);
  elements.levelFilter.addEventListener("change", applyFilters);
  elements.checkAnswer.addEventListener("click", checkAnswer);
  elements.nextQuestion.addEventListener("click", renderQuestion);
  elements.favoriteQuestion.addEventListener("click", () => {
    if (!state.current) return;
    state.favorites.add(state.current.id);
    elements.favoriteQuestion.textContent = `Đã đánh dấu (${state.favorites.size})`;
  });
  document.querySelectorAll("[data-exam]").forEach((button) => {
    button.addEventListener("click", () => createMockExam(button.dataset.exam));
  });
  elements.mockExam.addEventListener("change", (event) => {
    const checkbox = event.target.closest("[data-mock-checkbox]");
    if (!checkbox || !checkbox.checked) return;
    const group = checkbox.closest(".mock-checkbox-group");
    group?.querySelectorAll("[data-mock-checkbox]").forEach((item) => {
      if (item !== checkbox) item.checked = false;
    });
  });
  document.querySelectorAll("[data-essential-subject]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-essential-subject]").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      renderEssentialKnowledge(button.dataset.essentialSubject);
    });
  });
  document.querySelectorAll("[data-heatmap-subject]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-heatmap-subject]").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      renderExamStats(button.dataset.heatmapSubject);
    });
  });
  document.querySelectorAll("[data-pattern-subject]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-pattern-subject]").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      renderRepeatedPatterns(button.dataset.patternSubject);
    });
  });
  document.querySelectorAll("[data-score-subject]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-score-subject]").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      renderScoreTargets(button.dataset.scoreSubject);
    });
  });
  document.querySelectorAll("[data-mistake-subject]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-mistake-subject]").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      renderCommonMistakes(button.dataset.mistakeSubject);
    });
  });
}

bindEvents();
loadQuestions();
