import fs from "node:fs/promises";

const CREATED_AT = 1779703568473;
const OUT_FILE = "toeic-basic-english-premium.json";

const manualIpa = {
  barcode: "/ˈbɑːrkoʊd/",
  helpline: "/ˈhɛlplaɪn/",
  timesheet: "/ˈtaɪmʃiːt/",
  waybill: "/ˈweɪbɪl/",
};

const arpabetToIpa = {
  AA: "ɑ",
  AE: "æ",
  AH: "ʌ",
  AO: "ɔ",
  AW: "aʊ",
  AY: "aɪ",
  B: "b",
  CH: "tʃ",
  D: "d",
  DH: "ð",
  EH: "ɛ",
  ER: "ɝ",
  EY: "eɪ",
  F: "f",
  G: "ɡ",
  HH: "h",
  IH: "ɪ",
  IY: "iː",
  JH: "dʒ",
  K: "k",
  L: "l",
  M: "m",
  N: "n",
  NG: "ŋ",
  OW: "oʊ",
  OY: "ɔɪ",
  P: "p",
  R: "r",
  S: "s",
  SH: "ʃ",
  T: "t",
  TH: "θ",
  UH: "ʊ",
  UW: "uː",
  V: "v",
  W: "w",
  Y: "j",
  Z: "z",
  ZH: "ʒ",
};
const vowelPhones = new Set(["AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"]);

const topics = [
  {
    topic: "business",
    label: "business",
    cefr: "B1",
    difficulty: 2,
    image: "business office meeting",
    words: [
      ["agenda", "chương trình nghị sự"],
      ["agreement", "thỏa thuận"],
      ["approval", "sự chấp thuận"],
      ["arrangement", "sự sắp xếp"],
      ["assessment", "sự đánh giá"],
      ["branch", "chi nhánh"],
      ["partnership", "sự hợp tác"],
      ["budget", "ngân sách"],
      ["client", "khách hàng"],
      ["contract", "hợp đồng"],
      ["deadline", "hạn chót"],
      ["department", "phòng ban"],
      ["director", "giám đốc"],
      ["enterprise", "doanh nghiệp"],
      ["headquarters", "trụ sở chính"],
      ["manager", "quản lý"],
      ["objective", "mục tiêu"],
      ["operation", "hoạt động"],
      ["policy", "chính sách"],
      ["procedure", "quy trình"],
      ["proposal", "đề xuất"],
      ["schedule", "lịch trình"],
      ["strategy", "chiến lược"],
      ["supervisor", "giám sát viên"],
      ["workplace", "nơi làm việc"],
    ],
  },
  {
    topic: "office",
    label: "office administration",
    cefr: "B1",
    difficulty: 2,
    image: "office administration documents",
    words: [
      ["archive", "kho lưu trữ"],
      ["cabinet", "tủ hồ sơ"],
      ["calendar", "lịch"],
      ["clerk", "nhân viên văn phòng"],
      ["copier", "máy photocopy"],
      ["document", "tài liệu"],
      ["drawer", "ngăn kéo"],
      ["envelope", "phong bì"],
      ["extension", "số máy nhánh"],
      ["folder", "thư mục, bìa hồ sơ"],
      ["form", "biểu mẫu"],
      ["memo", "bản ghi nhớ"],
      ["notepad", "sổ ghi chú"],
      ["paperwork", "thủ tục giấy tờ"],
      ["photocopy", "bản sao photocopy"],
      ["printer", "máy in"],
      ["reception", "quầy tiếp tân"],
      ["record", "hồ sơ"],
      ["reminder", "lời nhắc"],
      ["stationery", "văn phòng phẩm"],
      ["storage", "sự lưu trữ"],
      ["supply", "nguồn cung, vật dụng"],
      ["timesheet", "bảng chấm công"],
      ["workspace", "không gian làm việc"],
      ["workstation", "bàn làm việc"],
    ],
  },
  {
    topic: "meetings",
    label: "meetings and events",
    cefr: "B1",
    difficulty: 2,
    image: "business meeting conference",
    words: [
      ["attendee", "người tham dự"],
      ["auditorium", "hội trường"],
      ["banquet", "tiệc chiêu đãi"],
      ["briefing", "buổi báo cáo ngắn"],
      ["conference", "hội nghị"],
      ["convention", "hội nghị lớn"],
      ["discussion", "cuộc thảo luận"],
      ["event", "sự kiện"],
      ["exhibition", "triển lãm"],
      ["forum", "diễn đàn"],
      ["handout", "tài liệu phát tay"],
      ["host", "người chủ trì"],
      ["itinerary", "lịch trình chuyến đi"],
      ["lecture", "bài giảng"],
      ["minutes", "biên bản cuộc họp"],
      ["participant", "người tham gia"],
      ["podium", "bục phát biểu"],
      ["presentation", "bài thuyết trình"],
      ["attendance", "sự tham dự"],
      ["seminar", "hội thảo"],
      ["session", "phiên họp"],
      ["speaker", "diễn giả"],
      ["symposium", "hội nghị chuyên đề"],
      ["venue", "địa điểm tổ chức"],
      ["workshop", "buổi hội thảo thực hành"],
    ],
  },
  {
    topic: "employment",
    label: "employment",
    cefr: "B1",
    difficulty: 2,
    image: "job interview hiring",
    words: [
      ["applicant", "ứng viên"],
      ["application", "đơn ứng tuyển"],
      ["benefit", "phúc lợi"],
      ["candidate", "ứng viên"],
      ["career", "sự nghiệp"],
      ["commute", "việc đi làm hằng ngày"],
      ["employee", "nhân viên"],
      ["employer", "nhà tuyển dụng"],
      ["employment", "việc làm"],
      ["experience", "kinh nghiệm"],
      ["interview", "buổi phỏng vấn"],
      ["internship", "kỳ thực tập"],
      ["occupation", "nghề nghiệp"],
      ["overtime", "giờ làm thêm"],
      ["payroll", "bảng lương"],
      ["position", "vị trí công việc"],
      ["raise", "sự tăng lương"],
      ["qualification", "bằng cấp, năng lực"],
      ["recruiter", "nhà tuyển dụng"],
      ["reference", "người giới thiệu"],
      ["resignation", "sự từ chức"],
      ["resume", "sơ yếu lý lịch"],
      ["salary", "lương"],
      ["trainee", "thực tập sinh"],
      ["opening", "vị trí còn trống"],
    ],
  },
  {
    topic: "finance",
    label: "finance and banking",
    cefr: "B1",
    difficulty: 3,
    image: "finance banking money",
    words: [
      ["account", "tài khoản"],
      ["balance", "số dư"],
      ["bankruptcy", "sự phá sản"],
      ["capital", "vốn"],
      ["cashier", "thu ngân"],
      ["deposit", "tiền gửi"],
      ["dividend", "cổ tức"],
      ["expense", "chi phí"],
      ["fee", "phí"],
      ["fund", "quỹ"],
      ["income", "thu nhập"],
      ["interest", "lãi suất"],
      ["investment", "khoản đầu tư"],
      ["invoice", "hóa đơn"],
      ["loan", "khoản vay"],
      ["mortgage", "khoản vay thế chấp"],
      ["payment", "khoản thanh toán"],
      ["profit", "lợi nhuận"],
      ["receipt", "biên lai"],
      ["revenue", "doanh thu"],
      ["savings", "tiền tiết kiệm"],
      ["statement", "bảng sao kê"],
      ["tax", "thuế"],
      ["transaction", "giao dịch"],
      ["withdrawal", "việc rút tiền"],
    ],
  },
  {
    topic: "marketing",
    label: "marketing and sales",
    cefr: "B1",
    difficulty: 3,
    image: "marketing sales campaign",
    words: [
      ["advertisement", "quảng cáo"],
      ["audience", "đối tượng khán giả"],
      ["brand", "thương hiệu"],
      ["campaign", "chiến dịch"],
      ["catalog", "danh mục sản phẩm"],
      ["consumer", "người tiêu dùng"],
      ["coupon", "phiếu giảm giá"],
      ["customer", "khách hàng"],
      ["demand", "nhu cầu"],
      ["discount", "giảm giá"],
      ["display", "khu trưng bày"],
      ["flyer", "tờ rơi"],
      ["guarantee", "sự bảo đảm"],
      ["launch", "lễ ra mắt"],
      ["logo", "biểu trưng"],
      ["market", "thị trường"],
      ["merchandise", "hàng hóa"],
      ["promotion", "chương trình khuyến mãi"],
      ["prospect", "khách hàng tiềm năng"],
      ["publicity", "sự quảng bá"],
      ["purchase", "việc mua hàng"],
      ["retailer", "nhà bán lẻ"],
      ["sale", "đợt bán hàng"],
      ["sample", "mẫu thử"],
      ["survey", "khảo sát"],
    ],
  },
  {
    topic: "customer-service",
    label: "customer service",
    cefr: "B1",
    difficulty: 2,
    image: "customer service support",
    words: [
      ["assistance", "sự hỗ trợ"],
      ["complaint", "lời phàn nàn"],
      ["confirmation", "sự xác nhận"],
      ["contact", "liên hệ"],
      ["courtesy", "sự lịch sự"],
      ["exchange", "sự đổi hàng"],
      ["feedback", "phản hồi"],
      ["helpline", "đường dây hỗ trợ"],
      ["inquiry", "câu hỏi, yêu cầu thông tin"],
      ["instruction", "hướng dẫn"],
      ["issue", "vấn đề"],
      ["membership", "tư cách thành viên"],
      ["operator", "tổng đài viên"],
      ["option", "lựa chọn"],
      ["policyholder", "người mua bảo hiểm"],
      ["questionnaire", "bảng câu hỏi"],
      ["refund", "khoản hoàn tiền"],
      ["replacement", "sự thay thế"],
      ["representative", "đại diện"],
      ["request", "yêu cầu"],
      ["response", "phản hồi"],
      ["satisfaction", "sự hài lòng"],
      ["service", "dịch vụ"],
      ["subscriber", "người đăng ký"],
      ["warranty", "bảo hành"],
    ],
  },
  {
    topic: "shopping",
    label: "shopping and retail",
    cefr: "B1",
    difficulty: 2,
    image: "shopping retail store",
    words: [
      ["aisle", "lối đi giữa các kệ"],
      ["barcode", "mã vạch"],
      ["basket", "giỏ mua hàng"],
      ["cash", "tiền mặt"],
      ["checkout", "quầy thanh toán"],
      ["counter", "quầy"],
      ["delivery", "sự giao hàng"],
      ["fitting", "việc thử đồ"],
      ["inventory", "hàng tồn kho"],
      ["item", "mặt hàng"],
      ["label", "nhãn"],
      ["mall", "trung tâm mua sắm"],
      ["outlet", "cửa hàng đại lý"],
      ["package", "gói hàng"],
      ["price", "giá"],
      ["product", "sản phẩm"],
      ["quantity", "số lượng"],
      ["register", "máy tính tiền"],
      ["shopper", "người mua sắm"],
      ["stock", "hàng trong kho"],
      ["store", "cửa hàng"],
      ["tag", "thẻ giá"],
      ["vendor", "người bán hàng"],
      ["voucher", "phiếu mua hàng"],
      ["wholesale", "bán buôn"],
    ],
  },
  {
    topic: "travel",
    label: "travel and tourism",
    cefr: "B1",
    difficulty: 2,
    image: "travel airport tourism",
    words: [
      ["agency", "đại lý"],
      ["arrival", "sự đến"],
      ["baggage", "hành lý"],
      ["boarding", "việc lên máy bay"],
      ["booking", "sự đặt chỗ"],
      ["landmark", "địa danh nổi tiếng"],
      ["currency", "tiền tệ"],
      ["immigration", "nhập cảnh"],
      ["departure", "sự khởi hành"],
      ["destination", "điểm đến"],
      ["excursion", "chuyến tham quan"],
      ["airfare", "giá vé máy bay"],
      ["flight", "chuyến bay"],
      ["guide", "hướng dẫn viên"],
      ["luggage", "hành lý"],
      ["passport", "hộ chiếu"],
      ["sightseeing", "việc tham quan"],
      ["souvenir", "quà lưu niệm"],
      ["terminal", "nhà ga"],
      ["ticket", "vé"],
      ["tour", "chuyến du lịch"],
      ["traveler", "du khách"],
      ["trip", "chuyến đi"],
      ["visa", "thị thực"],
      ["voyage", "chuyến hành trình"],
    ],
  },
  {
    topic: "hotels",
    label: "hotels and accommodation",
    cefr: "B1",
    difficulty: 2,
    image: "hotel accommodation room",
    words: [
      ["accommodation", "chỗ ở"],
      ["amenity", "tiện nghi"],
      ["bellhop", "nhân viên khuân hành lý"],
      ["porter", "nhân viên khuân hành lý"],
      ["lodging", "chỗ lưu trú"],
      ["concierge", "nhân viên hỗ trợ khách"],
      ["prepayment", "khoản trả trước"],
      ["guest", "khách"],
      ["housekeeping", "dịch vụ dọn phòng"],
      ["key", "chìa khóa"],
      ["laundry", "dịch vụ giặt ủi"],
      ["lobby", "sảnh"],
      ["maid", "nhân viên dọn phòng"],
      ["occupancy", "tình trạng lấp đầy phòng"],
      ["rate", "mức giá"],
      ["receptionist", "nhân viên lễ tân"],
      ["renovation", "sự cải tạo"],
      ["availability", "tình trạng còn phòng"],
      ["resort", "khu nghỉ dưỡng"],
      ["room", "phòng"],
      ["suite", "phòng cao cấp"],
      ["doorman", "nhân viên gác cửa"],
      ["valet", "nhân viên giữ xe"],
      ["view", "quang cảnh"],
      ["wake-up", "cuộc gọi đánh thức"],
    ],
  },
  {
    topic: "restaurants",
    label: "restaurants and food service",
    cefr: "B1",
    difficulty: 2,
    image: "restaurant food service",
    words: [
      ["appetizer", "món khai vị"],
      ["beverage", "đồ uống"],
      ["bill", "hóa đơn"],
      ["buffet", "tiệc tự chọn"],
      ["cafeteria", "nhà ăn"],
      ["caterer", "nhà cung cấp tiệc"],
      ["chef", "đầu bếp"],
      ["cuisine", "ẩm thực"],
      ["dessert", "món tráng miệng"],
      ["dish", "món ăn"],
      ["ingredient", "nguyên liệu"],
      ["kitchen", "nhà bếp"],
      ["menu", "thực đơn"],
      ["napkin", "khăn ăn"],
      ["portion", "khẩu phần"],
      ["recipe", "công thức nấu ăn"],
      ["server", "nhân viên phục vụ"],
      ["special", "món đặc biệt"],
      ["table", "bàn"],
      ["takeout", "đồ ăn mang đi"],
      ["taste", "hương vị"],
      ["tray", "khay"],
      ["utensil", "dụng cụ ăn uống"],
      ["waiter", "bồi bàn nam"],
      ["waitress", "bồi bàn nữ"],
    ],
  },
  {
    topic: "transportation",
    label: "transportation",
    cefr: "B1",
    difficulty: 2,
    image: "transportation bus train traffic",
    words: [
      ["automobile", "ô tô"],
      ["bicycle", "xe đạp"],
      ["bus", "xe buýt"],
      ["cab", "xe taxi"],
      ["commuter", "người đi làm xa"],
      ["delay", "sự chậm trễ"],
      ["driver", "tài xế"],
      ["toll", "phí đường bộ"],
      ["ferry", "phà"],
      ["freeway", "đường cao tốc"],
      ["garage", "nhà để xe"],
      ["intersection", "giao lộ"],
      ["license", "giấy phép"],
      ["passenger", "hành khách"],
      ["platform", "sân ga"],
      ["railway", "đường sắt"],
      ["route", "tuyến đường"],
      ["shuttle", "xe đưa đón"],
      ["station", "nhà ga"],
      ["subway", "tàu điện ngầm"],
      ["taxi", "xe taxi"],
      ["traffic", "giao thông"],
      ["transfer", "sự chuyển tuyến"],
      ["vehicle", "phương tiện"],
      ["wheelchair", "xe lăn"],
    ],
  },
  {
    topic: "shipping",
    label: "shipping and logistics",
    cefr: "B1",
    difficulty: 3,
    image: "shipping logistics warehouse",
    words: [
      ["cargo", "hàng hóa vận chuyển"],
      ["carrier", "hãng vận chuyển"],
      ["carton", "thùng carton"],
      ["container", "công-ten-nơ"],
      ["courier", "người chuyển phát"],
      ["clearance", "thủ tục thông quan"],
      ["dispatch", "việc gửi hàng"],
      ["freight", "hàng vận tải"],
      ["handling", "việc xử lý hàng"],
      ["import", "hàng nhập khẩu"],
      ["loading", "việc bốc hàng"],
      ["manifest", "bảng kê hàng hóa"],
      ["pallet", "kệ hàng"],
      ["parcel", "bưu kiện"],
      ["pickup", "việc lấy hàng"],
      ["port", "cảng"],
      ["postage", "bưu phí"],
      ["shipment", "lô hàng"],
      ["supplier", "nhà cung cấp"],
      ["tracking", "sự theo dõi đơn hàng"],
      ["truck", "xe tải"],
      ["unloading", "việc dỡ hàng"],
      ["warehouse", "nhà kho"],
      ["waybill", "vận đơn"],
      ["weight", "trọng lượng"],
    ],
  },
  {
    topic: "manufacturing",
    label: "manufacturing and production",
    cefr: "B1",
    difficulty: 3,
    image: "manufacturing factory production",
    words: [
      ["assembly", "sự lắp ráp"],
      ["component", "linh kiện"],
      ["defect", "lỗi sản phẩm"],
      ["equipment", "thiết bị"],
      ["factory", "nhà máy"],
      ["inspection", "sự kiểm tra"],
      ["machinery", "máy móc"],
      ["maintenance", "bảo trì"],
      ["manufacturer", "nhà sản xuất"],
      ["material", "vật liệu"],
      ["output", "sản lượng"],
      ["plant", "nhà máy"],
      ["production", "sản xuất"],
      ["prototype", "nguyên mẫu"],
      ["quality", "chất lượng"],
      ["resource", "nguồn lực"],
      ["repair", "sự sửa chữa"],
      ["blueprint", "bản thiết kế"],
      ["shift", "ca làm việc"],
      ["specification", "thông số kỹ thuật"],
      ["supervision", "sự giám sát"],
      ["tool", "công cụ"],
      ["upgrade", "sự nâng cấp"],
      ["calibration", "sự hiệu chuẩn"],
      ["workbench", "bàn làm việc"],
    ],
  },
  {
    topic: "technology",
    label: "technology and communication",
    cefr: "B1",
    difficulty: 3,
    image: "technology communication computer",
    words: [
      ["access", "quyền truy cập"],
      ["attachment", "tệp đính kèm"],
      ["browser", "trình duyệt"],
      ["database", "cơ sở dữ liệu"],
      ["device", "thiết bị"],
      ["email", "thư điện tử"],
      ["plugin", "tiện ích mở rộng"],
      ["hardware", "phần cứng"],
      ["inbox", "hộp thư đến"],
      ["installation", "việc cài đặt"],
      ["keyboard", "bàn phím"],
      ["laptop", "máy tính xách tay"],
      ["login", "thông tin đăng nhập"],
      ["monitor", "màn hình"],
      ["network", "mạng"],
      ["password", "mật khẩu"],
      ["program", "chương trình"],
      ["software", "phần mềm"],
      ["spreadsheet", "bảng tính"],
      ["memory", "bộ nhớ"],
      ["support", "hỗ trợ kỹ thuật"],
      ["system", "hệ thống"],
      ["update", "bản cập nhật"],
      ["username", "tên người dùng"],
      ["website", "trang web"],
    ],
  },
  {
    topic: "real-estate",
    label: "real estate and facilities",
    cefr: "B1",
    difficulty: 3,
    image: "real estate building facility",
    words: [
      ["address", "địa chỉ"],
      ["apartment", "căn hộ"],
      ["building", "tòa nhà"],
      ["ceiling", "trần nhà"],
      ["construction", "sự xây dựng"],
      ["elevator", "thang máy"],
      ["entrance", "lối vào"],
      ["facility", "cơ sở vật chất"],
      ["floor", "tầng, sàn"],
      ["hallway", "hành lang"],
      ["heating", "hệ thống sưởi"],
      ["landlord", "chủ nhà"],
      ["lease", "hợp đồng thuê"],
      ["location", "vị trí"],
      ["janitor", "nhân viên bảo trì"],
      ["neighborhood", "khu dân cư"],
      ["occupant", "người cư trú"],
      ["property", "bất động sản"],
      ["remodeling", "sự sửa sang"],
      ["rent", "tiền thuê"],
      ["resident", "cư dân"],
      ["security", "an ninh"],
      ["tenant", "người thuê nhà"],
      ["utility", "tiện ích"],
      ["window", "cửa sổ"],
    ],
  },
  {
    topic: "healthcare",
    label: "healthcare and benefits",
    cefr: "B1",
    difficulty: 3,
    image: "healthcare clinic benefits",
    words: [
      ["appointment", "cuộc hẹn"],
      ["beneficiary", "người thụ hưởng"],
      ["clinic", "phòng khám"],
      ["coverage", "phạm vi bảo hiểm"],
      ["dentist", "nha sĩ"],
      ["diagnosis", "chẩn đoán"],
      ["examination", "cuộc kiểm tra"],
      ["healthcare", "chăm sóc sức khỏe"],
      ["insurance", "bảo hiểm"],
      ["medicine", "thuốc"],
      ["patient", "bệnh nhân"],
      ["pharmacy", "nhà thuốc"],
      ["physician", "bác sĩ"],
      ["plan", "gói bảo hiểm"],
      ["prescription", "đơn thuốc"],
      ["surgery", "ca phẫu thuật"],
      ["provider", "nhà cung cấp dịch vụ"],
      ["reimbursement", "sự hoàn trả chi phí"],
      ["treatment", "điều trị"],
      ["vaccination", "tiêm chủng"],
      ["wellness", "sức khỏe tổng thể"],
      ["claim", "yêu cầu bồi thường"],
      ["copayment", "khoản đồng chi trả"],
      ["emergency", "trường hợp khẩn cấp"],
      ["therapy", "liệu pháp"],
    ],
  },
  {
    topic: "training",
    label: "education and training",
    cefr: "B1",
    difficulty: 2,
    image: "training education class",
    words: [
      ["assignment", "bài tập"],
      ["certificate", "chứng chỉ"],
      ["classroom", "phòng học"],
      ["course", "khóa học"],
      ["curriculum", "chương trình học"],
      ["degree", "bằng cấp"],
      ["enrollment", "sự ghi danh"],
      ["exercise", "bài luyện tập"],
      ["faculty", "khoa, đội ngũ giảng viên"],
      ["grade", "điểm số"],
      ["instructor", "giảng viên"],
      ["lesson", "bài học"],
      ["manual", "sổ tay hướng dẫn"],
      ["orientation", "buổi định hướng"],
      ["practice", "sự luyện tập"],
      ["quiz", "bài kiểm tra ngắn"],
      ["registration", "sự đăng ký"],
      ["scholarship", "học bổng"],
      ["skill", "kỹ năng"],
      ["student", "học viên"],
      ["textbook", "sách giáo khoa"],
      ["trainer", "người đào tạo"],
      ["tuition", "học phí"],
      ["tutorial", "bài hướng dẫn"],
      ["webinar", "hội thảo trực tuyến"],
    ],
  },
  {
    topic: "legal",
    label: "legal and compliance",
    cefr: "B2",
    difficulty: 4,
    image: "legal compliance contract",
    words: [
      ["authorization", "sự ủy quyền"],
      ["clause", "điều khoản"],
      ["compliance", "sự tuân thủ"],
      ["confidentiality", "tính bảo mật"],
      ["consent", "sự đồng ý"],
      ["copyright", "bản quyền"],
      ["disclosure", "sự tiết lộ"],
      ["evidence", "bằng chứng"],
      ["fine", "tiền phạt"],
      ["guideline", "hướng dẫn"],
      ["liability", "trách nhiệm pháp lý"],
      ["certification", "chứng nhận"],
      ["notice", "thông báo"],
      ["obligation", "nghĩa vụ"],
      ["permit", "giấy phép"],
      ["privacy", "quyền riêng tư"],
      ["regulation", "quy định"],
      ["requirement", "yêu cầu"],
      ["signature", "chữ ký"],
      ["statute", "đạo luật"],
      ["term", "điều khoản"],
      ["violation", "sự vi phạm"],
      ["witness", "nhân chứng"],
      ["lawsuit", "vụ kiện"],
      ["settlement", "sự dàn xếp"],
    ],
  },
  {
    topic: "safety",
    label: "environment and safety",
    cefr: "B1",
    difficulty: 3,
    image: "workplace safety environment",
    words: [
      ["accident", "tai nạn"],
      ["alarm", "chuông báo động"],
      ["caution", "sự thận trọng"],
      ["conservation", "sự bảo tồn"],
      ["disposal", "việc thải bỏ"],
      ["drill", "buổi diễn tập"],
      ["emission", "khí thải"],
      ["environment", "môi trường"],
      ["evacuation", "sự sơ tán"],
      ["fire", "hỏa hoạn"],
      ["hazard", "mối nguy"],
      ["helmet", "mũ bảo hộ"],
      ["audit", "cuộc kiểm tra"],
      ["mask", "khẩu trang"],
      ["pollution", "sự ô nhiễm"],
      ["precaution", "biện pháp phòng ngừa"],
      ["recycling", "việc tái chế"],
      ["rule", "quy tắc"],
      ["risk", "rủi ro"],
      ["safety", "sự an toàn"],
      ["shelter", "nơi trú ẩn"],
      ["spill", "sự tràn đổ"],
      ["coordinator", "điều phối viên"],
      ["training", "đào tạo"],
      ["warning", "cảnh báo"],
    ],
  },
];

function normalizeWord(word) {
  return word.toLowerCase();
}

function makeExample(word, label) {
  return `The ${word} was important in the ${label} context.`;
}

function fallbackAudio(word) {
  return `https://api.dictionaryapi.dev/media/pronunciations/en/${encodeURIComponent(word)}-us.mp3`;
}

function normalizeIpa(text) {
  if (!text) return "";
  const trimmed = text.trim();
  if (!trimmed) return "";
  return trimmed.startsWith("/") ? trimmed : `/${trimmed.replace(/^[/\\[]|[/\\]]$/g, "")}/`;
}

async function loadCmuDictionary() {
  const url = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict";
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Unable to load CMU dictionary: HTTP ${response.status}`);
  const text = await response.text();
  const dictionary = new Map();
  for (const line of text.split(/\r?\n/)) {
    if (!line || line.startsWith(";")) continue;
    const [word, ...phones] = line.trim().split(/\s+/);
    const normalized = word.replace(/\(\d+\)$/, "");
    if (!dictionary.has(normalized)) dictionary.set(normalized, phones);
  }
  return dictionary;
}

function phonesToIpa(phones) {
  const parts = [];
  for (const phone of phones) {
    const match = phone.match(/^([A-Z]+)([012])?$/);
    if (!match) continue;
    const [, base, stress] = match;
    const ipa = arpabetToIpa[base];
    if (!ipa) continue;
    if (stress === "1" || stress === "2") {
      let insertAt = parts.length;
      while (insertAt > 0 && !parts[insertAt - 1].isVowel) insertAt -= 1;
      parts.splice(insertAt, 0, { ipa: stress === "1" ? "ˈ" : "ˌ", isVowel: false });
    }
    const vowel = vowelPhones.has(base);
    if (base === "AH" && stress === "0") parts.push({ ipa: "ə", isVowel: vowel });
    else if (base === "ER" && stress === "0") parts.push({ ipa: "ɚ", isVowel: vowel });
    else parts.push({ ipa, isVowel: vowel });
  }
  return parts.length > 0 ? `/${parts.map((part) => part.ipa).join("")}/` : "";
}

function getCmuIpa(cmuDictionary, word) {
  const normalized = word.toLowerCase().replace(/-/g, "");
  if (manualIpa[normalized]) return manualIpa[normalized];
  const phones = cmuDictionary.get(normalized);
  return phones ? phonesToIpa(phones) : "";
}

async function getPronunciation(word) {
  const apiWord = word.replace("-", "");
  const url = `https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(apiWord)}`;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const entries = await response.json();
    const phonetics = entries.flatMap((entry) => entry.phonetics || []);
    const usAudio = phonetics.find((p) => p.audio && /-us\.mp3|\/us\//i.test(p.audio));
    const withTextAndUsAudio = phonetics.find((p) => p.text && p.audio && /-us\.mp3|\/us\//i.test(p.audio));
    const withText = phonetics.find((p) => p.text);
    const topLevelText = entries.find((entry) => entry.phonetic)?.phonetic;
    const withAudio = phonetics.find((p) => p.audio);
    return {
      ipa_us: normalizeIpa((withTextAndUsAudio || usAudio || withText || {}).text || topLevelText),
      audio_us: (withTextAndUsAudio || usAudio || withAudio || {}).audio || fallbackAudio(apiWord),
    };
  } catch {
    return {
      ipa_us: "",
      audio_us: fallbackAudio(apiWord),
    };
  }
}

const seen = new Set();
const duplicated = [];
const rawEntries = [];

for (const topic of topics) {
  for (const [word, meaning_vi] of topic.words) {
    const normalized = normalizeWord(word);
    if (seen.has(normalized)) {
      duplicated.push(word);
      continue;
    }
    seen.add(normalized);
    rawEntries.push({ word, meaning_vi, topic });
  }
}

if (duplicated.length > 0) {
  throw new Error(`Duplicate words in source data: ${duplicated.join(", ")}`);
}

const entries = [];
const missingIpa = [];
const cmuDictionary = await loadCmuDictionary();

for (const raw of rawEntries) {
  const number = entries.length + 1;
  const pronunciation = await getPronunciation(raw.word);
  if (!pronunciation.ipa_us) pronunciation.ipa_us = getCmuIpa(cmuDictionary, raw.word);
  if (!pronunciation.ipa_us) missingIpa.push(raw.word);
  entries.push({
    id: `toeic-${String(number).padStart(4, "0")}`,
    word: raw.word,
    ipa_us: pronunciation.ipa_us,
    meaning_vi: raw.meaning_vi,
    example: makeExample(raw.word, raw.topic.label),
    status: "new",
    reviewLevel: 0,
    reviewCount: 0,
    createdAt: CREATED_AT,
    audio_us: pronunciation.audio_us,
    topic: raw.topic.topic,
    cefr_level: raw.topic.cefr,
    difficulty: raw.topic.difficulty,
    image_keyword: `${raw.word} ${raw.topic.image}`,
  });
}

const output = { "toeic-basic-english-premium": entries };
await fs.writeFile(OUT_FILE, `${JSON.stringify(output, null, 2)}\n`, "utf8");

const missingFields = entries.filter((entry) =>
  ["id", "word", "ipa_us", "meaning_vi", "example", "audio_us", "topic", "cefr_level", "difficulty", "image_keyword"].some((field) => !entry[field])
);

console.log(JSON.stringify({
  file: OUT_FILE,
  total: entries.length,
  topics: topics.map((topic) => ({ topic: topic.topic, count: topic.words.length })),
  duplicateWords: duplicated,
  missingIpa,
  missingRequiredFieldCount: missingFields.length,
}, null, 2));
