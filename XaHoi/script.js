const groups = {
  root: { label: "Trung tâm", color: "#20232a" },
  human: { label: "Yếu tố con người", color: "#e25555" },
  relation: { label: "Quan hệ xã hội", color: "#d9862f" },
  wellbeing: { label: "Nhu cầu & đời sống", color: "#36a269" },
  value: { label: "Giá trị & ý nghĩa", color: "#b7791f" },
  power: { label: "Quyền lực & bất bình đẳng", color: "#c05621" },
  lifecycle: { label: "Vòng đời", color: "#805ad5" },
  environment: { label: "Môi trường sống", color: "#2c7a7b" },
  research: { label: "Nghiên cứu xã hội", color: "#4a5568" },
  theory: { label: "Lý thuyết xã hội", color: "#6b46c1" },
  institution: { label: "Thể chế", color: "#5d7cff" },
  culture: { label: "Văn hóa", color: "#e78a3d" },
  economy: { label: "Kinh tế", color: "#2f9d75" },
  technology: { label: "Công nghệ", color: "#9b6ce3" }
};

const concepts = [
  { id: "human", label: "Con người", icon: "☉", group: "root", year: -300000, description: "Chủ thể trung tâm tạo nghĩa, xây quan hệ và chịu tác động của mọi cấu trúc xã hội." },
  { id: "body-mind", label: "Thân thể & tâm trí", icon: "◒", group: "human", parent: "human", year: -300000, description: "Nền tảng sinh học, cảm xúc và nhận thức của trải nghiệm xã hội." },
  { id: "need", label: "Nhu cầu", icon: "◌", group: "wellbeing", parent: "human", year: -300000, description: "Động lực cơ bản về an toàn, thuộc về, được tôn trọng và phát triển." },
  { id: "agency", label: "Năng lực hành động", icon: "↗", group: "human", parent: "human", year: -200000, description: "Khả năng lựa chọn, phản ứng và thay đổi hoàn cảnh sống." },
  { id: "relationship", label: "Quan hệ", icon: "∞", group: "relation", parent: "human", year: -200000, description: "Các liên kết gia đình, bạn bè, nhóm và mạng lưới tạo nên đời sống chung." },
  { id: "society", label: "Xã hội", icon: "◎", group: "root", parent: "human", year: -10000, description: "Không gian chung nơi con người tổ chức đời sống, chuẩn mực và quan hệ." },
  { id: "emotion", label: "Cảm xúc", icon: "♡", group: "human", parent: "body-mind", year: -300000, description: "Tín hiệu nội tâm ảnh hưởng đến gắn bó, xung đột và ra quyết định." },
  { id: "knowledge", label: "Tri thức", icon: "✧", group: "human", parent: "body-mind", year: -70000, description: "Cách con người học, ghi nhớ, diễn giải và truyền lại kinh nghiệm." },
  { id: "safety", label: "An toàn", icon: "□", group: "wellbeing", parent: "need", year: -300000, description: "Điều kiện để con người giảm rủi ro và ổn định đời sống." },
  { id: "belonging", label: "Thuộc về", icon: "⊂", group: "wellbeing", parent: "need", year: -200000, description: "Cảm giác được công nhận là một phần của gia đình, nhóm hoặc cộng đồng." },
  { id: "dignity", label: "Phẩm giá", icon: "◇", group: "wellbeing", parent: "need", year: -5000, description: "Giá trị con người cần được tôn trọng bất kể vị thế hay nguồn lực." },
  { id: "choice", label: "Lựa chọn", icon: "⌁", group: "human", parent: "agency", year: -200000, description: "Không gian quyết định giữa các khả năng cá nhân và ràng buộc xã hội." },
  { id: "responsibility", label: "Trách nhiệm", icon: "✓", group: "human", parent: "agency", year: -12000, description: "Sự gắn kết giữa hành động cá nhân và hệ quả đối với người khác." },
  { id: "family", label: "Gia đình", icon: "⌂", group: "relation", parent: "relationship", year: -200000, description: "Đơn vị gần nhất của chăm sóc, xã hội hóa và truyền giá trị." },
  { id: "community", label: "Cộng đồng", icon: "◉", group: "relation", parent: "relationship", year: -12000, description: "Không gian hợp tác, hỗ trợ và chia sẻ bản sắc giữa nhiều cá nhân." },
  { id: "trust", label: "Niềm tin", icon: "◈", group: "relation", parent: "relationship", year: -12000, description: "Kỳ vọng rằng người khác và thiết chế sẽ hành động có thể dự đoán." },
  { id: "institution", label: "Thể chế", icon: "🏛", group: "institution", parent: "society", year: -3000, description: "Luật lệ, tổ chức và quy trình giữ cho cộng đồng vận hành ổn định." },
  { id: "culture", label: "Văn hóa", icon: "✦", group: "culture", parent: "society", year: -40000, description: "Hệ biểu tượng, giá trị và thực hành tạo nên bản sắc chung." },
  { id: "economy", label: "Kinh tế", icon: "◍", group: "economy", parent: "society", year: -9000, description: "Cách xã hội sản xuất, phân phối và trao đổi nguồn lực." },
  { id: "technology", label: "Công nghệ", icon: "⚙", group: "technology", parent: "society", year: -2500000, description: "Công cụ và tri thức mở rộng năng lực hành động của con người." },
  { id: "law", label: "Pháp luật", icon: "§", group: "institution", parent: "institution", year: -1750, description: "Bộ quy tắc chính thức xác định quyền, nghĩa vụ và chế tài." },
  { id: "rights", label: "Quyền", icon: "◈", group: "institution", parent: "institution", year: -500, description: "Các bảo đảm đạo đức và pháp lý giúp con người được bảo vệ, tham gia và phát triển." },
  { id: "governance", label: "Quản trị", icon: "⬠", group: "institution", parent: "institution", year: -3200, description: "Cách quyền lực được phân bổ, giám sát và ra quyết định." },
  { id: "identity", label: "Bản sắc", icon: "◐", group: "culture", parent: "culture", year: -12000, description: "Cảm nhận về mình và nhóm mình trong một cộng đồng rộng hơn." },
  { id: "norm", label: "Chuẩn mực", icon: "∴", group: "culture", parent: "culture", year: -6000, description: "Kỳ vọng xã hội định hướng hành vi được xem là phù hợp." },
  { id: "market", label: "Thị trường", icon: "↔", group: "economy", parent: "economy", year: -700, description: "Cơ chế trao đổi nơi giá trị được thương lượng qua cung và cầu." },
  { id: "labor", label: "Lao động", icon: "◧", group: "economy", parent: "economy", year: -9000, description: "Hoạt động tạo giá trị, thu nhập và vị thế trong cấu trúc xã hội." },
  { id: "media", label: "Truyền thông", icon: "◌", group: "technology", parent: "technology", year: 1450, description: "Hạ tầng lan truyền thông tin, ký ức và ảnh hưởng tập thể." },
  { id: "digital-network", label: "Mạng số", icon: "#", group: "technology", parent: "technology", year: 1990, description: "Không gian kết nối dữ liệu, cá nhân và thiết chế theo thời gian thực." },
  { id: "life-course", label: "Vòng đời", icon: "◷", group: "lifecycle", parent: "human", year: -300000, description: "Các giai đoạn sống mà con người đi qua, gắn với vai trò, kỳ vọng và nguồn lực khác nhau." },
  { id: "meaning-value", label: "Giá trị & ý nghĩa", icon: "✺", group: "value", parent: "human", year: -70000, description: "Những điều con người xem là đáng sống, đáng theo đuổi và đáng bảo vệ." },
  { id: "power-inequality", label: "Quyền lực & bất bình đẳng", icon: "△", group: "power", parent: "society", year: -12000, description: "Cách nguồn lực, tiếng nói và cơ hội được phân bổ không đồng đều trong xã hội." },
  { id: "environment", label: "Môi trường sống", icon: "◬", group: "environment", parent: "society", year: -300000, description: "Không gian tự nhiên, đô thị và hạ tầng vật chất định hình cách con người sống cùng nhau." },
  { id: "perception", label: "Tri giác", icon: "◔", group: "human", parent: "body-mind", year: -300000, description: "Cách con người cảm nhận thế giới và lựa chọn điều gì là đáng chú ý." },
  { id: "memory", label: "Ký ức", icon: "≋", group: "human", parent: "body-mind", year: -200000, description: "Năng lực lưu giữ trải nghiệm cá nhân và ký ức tập thể để định hướng hiện tại." },
  { id: "stress", label: "Căng thẳng", icon: "!", group: "human", parent: "body-mind", year: -300000, description: "Phản ứng của cơ thể và tâm trí trước áp lực, bất an hoặc thiếu kiểm soát." },
  { id: "mental-health", label: "Sức khỏe tinh thần", icon: "◑", group: "human", parent: "body-mind", year: -300000, description: "Trạng thái cân bằng tâm lý chịu ảnh hưởng bởi quan hệ, lao động, rủi ro và hỗ trợ xã hội." },
  { id: "care", label: "Chăm sóc", icon: "♡", group: "wellbeing", parent: "need", year: -300000, description: "Hoạt động duy trì sự sống, phục hồi tổn thương và nâng đỡ người phụ thuộc." },
  { id: "health", label: "Sức khỏe", icon: "+", group: "wellbeing", parent: "need", year: -300000, description: "Điều kiện thể chất và xã hội cho phép con người sống, học tập và lao động." },
  { id: "education", label: "Giáo dục", icon: "⌘", group: "wellbeing", parent: "need", year: -5000, description: "Quá trình truyền tri thức, kỹ năng, giá trị và khả năng tham gia xã hội." },
  { id: "recognition", label: "Công nhận", icon: "◊", group: "wellbeing", parent: "need", year: -12000, description: "Nhu cầu được nhìn nhận như một chủ thể có giá trị, tiếng nói và phẩm giá." },
  { id: "motivation", label: "Động cơ", icon: "↑", group: "human", parent: "agency", year: -200000, description: "Nguồn năng lượng nội tại hoặc xã hội thúc đẩy con người hành động." },
  { id: "habit", label: "Thói quen", icon: "↻", group: "human", parent: "agency", year: -200000, description: "Mẫu hành vi lặp lại giúp đời sống ổn định nhưng cũng có thể tái tạo bất bình đẳng." },
  { id: "resilience", label: "Khả năng phục hồi", icon: "⤴", group: "human", parent: "agency", year: -200000, description: "Khả năng thích nghi và tái lập đời sống sau mất mát, khủng hoảng hoặc biến động." },
  { id: "participation", label: "Tham gia", icon: "◫", group: "human", parent: "agency", year: -12000, description: "Việc con người góp tiếng nói, hành động và trách nhiệm vào đời sống chung." },
  { id: "communication", label: "Giao tiếp", icon: "↔", group: "relation", parent: "relationship", year: -200000, description: "Trao đổi ý nghĩa bằng ngôn ngữ, biểu cảm, ký hiệu và công nghệ." },
  { id: "empathy", label: "Đồng cảm", icon: "≈", group: "relation", parent: "relationship", year: -200000, description: "Khả năng hiểu và phản hồi trước trải nghiệm của người khác." },
  { id: "conflict", label: "Xung đột", icon: "⚡", group: "relation", parent: "relationship", year: -200000, description: "Va chạm lợi ích, giá trị hoặc quyền lực có thể phá vỡ hoặc tái cấu trúc quan hệ." },
  { id: "reciprocity", label: "Có đi có lại", icon: "⇄", group: "relation", parent: "relationship", year: -200000, description: "Nguyên tắc trao đổi hỗ trợ và nghĩa vụ giúp duy trì niềm tin xã hội." },
  { id: "childhood", label: "Thời thơ ấu", icon: "◡", group: "lifecycle", parent: "life-course", year: -300000, description: "Giai đoạn phụ thuộc và học hỏi mạnh, nơi chăm sóc và xã hội hóa có ảnh hưởng sâu." },
  { id: "adolescence", label: "Thanh thiếu niên", icon: "◗", group: "lifecycle", parent: "life-course", year: -300000, description: "Giai đoạn hình thành bản sắc, thử nghiệm vai trò và mở rộng quan hệ ngoài gia đình." },
  { id: "adulthood", label: "Trưởng thành", icon: "●", group: "lifecycle", parent: "life-course", year: -300000, description: "Giai đoạn gắn với lao động, gia đình, trách nhiệm công dân và tích lũy nguồn lực." },
  { id: "aging", label: "Tuổi già", icon: "◌", group: "lifecycle", parent: "life-course", year: -300000, description: "Giai đoạn đặt ra vấn đề chăm sóc, ký ức, phụ thuộc, phẩm giá và liên thế hệ." },
  { id: "belief", label: "Niềm tin giá trị", icon: "✧", group: "value", parent: "meaning-value", year: -70000, description: "Những xác tín nền tảng giúp con người diễn giải thế giới và hành động." },
  { id: "morality", label: "Đạo đức", icon: "∵", group: "value", parent: "meaning-value", year: -12000, description: "Phân biệt điều nên làm, không nên làm và trách nhiệm với người khác." },
  { id: "purpose", label: "Mục đích sống", icon: "◎", group: "value", parent: "meaning-value", year: -70000, description: "Cảm nhận rằng đời sống có hướng đi, đóng góp và ý nghĩa vượt khỏi nhu cầu tức thời." },
  { id: "freedom", label: "Tự do", icon: "⟡", group: "value", parent: "meaning-value", year: -5000, description: "Khả năng tự quyết trong giới hạn của quan hệ, luật lệ và điều kiện vật chất." },
  { id: "class", label: "Giai tầng", icon: "▤", group: "power", parent: "power-inequality", year: -9000, description: "Vị trí xã hội hình thành từ tài sản, nghề nghiệp, giáo dục và uy tín." },
  { id: "gender", label: "Giới", icon: "⚭", group: "power", parent: "power-inequality", year: -12000, description: "Cấu trúc vai trò và kỳ vọng xã hội gắn với thân thể, bản dạng và quyền lực." },
  { id: "ethnicity", label: "Tộc người", icon: "◍", group: "power", parent: "power-inequality", year: -12000, description: "Cộng đồng bản sắc dựa trên nguồn gốc, ngôn ngữ, ký ức và ranh giới xã hội." },
  { id: "social-mobility", label: "Dịch chuyển xã hội", icon: "⇧", group: "power", parent: "power-inequality", year: -5000, description: "Khả năng thay đổi vị thế xã hội giữa các thế hệ hoặc trong một đời người." },
  { id: "language", label: "Ngôn ngữ", icon: "¶", group: "culture", parent: "culture", year: -70000, description: "Hệ ký hiệu giúp con người chia sẻ ý nghĩa, ký ức và phối hợp hành động." },
  { id: "ritual", label: "Nghi lễ", icon: "✷", group: "culture", parent: "culture", year: -40000, description: "Thực hành biểu tượng tạo cảm giác thuộc về, chuyển tiếp và trật tự." },
  { id: "collective-memory", label: "Ký ức tập thể", icon: "◫", group: "culture", parent: "culture", year: -12000, description: "Cách cộng đồng nhớ, kể lại và tranh luận về quá khứ chung." },
  { id: "citizenship", label: "Công dân", icon: "▣", group: "institution", parent: "institution", year: -500, description: "Tư cách thành viên chính trị gắn với quyền, nghĩa vụ và sự tham gia công cộng." },
  { id: "public-service", label: "Dịch vụ công", icon: "▦", group: "institution", parent: "institution", year: 1800, description: "Hạ tầng y tế, giáo dục, an sinh và hành chính giúp bảo đảm đời sống chung." },
  { id: "livelihood", label: "Sinh kế", icon: "◧", group: "economy", parent: "economy", year: -9000, description: "Cách con người bảo đảm nguồn sống thông qua lao động, tài sản và mạng lưới hỗ trợ." },
  { id: "consumption", label: "Tiêu dùng", icon: "◈", group: "economy", parent: "economy", year: -3000, description: "Hành vi sử dụng hàng hóa và dịch vụ để đáp ứng nhu cầu, biểu đạt vị thế và bản sắc." },
  { id: "algorithm", label: "Thuật toán", icon: "⌗", group: "technology", parent: "technology", year: 1950, description: "Quy tắc xử lý dữ liệu ngày càng ảnh hưởng đến lựa chọn, thông tin và cơ hội xã hội." },
  { id: "privacy", label: "Riêng tư", icon: "◫", group: "technology", parent: "technology", year: 1890, description: "Không gian kiểm soát thông tin cá nhân, ranh giới thân mật và tự chủ." },
  { id: "urban-space", label: "Không gian đô thị", icon: "▥", group: "environment", parent: "environment", year: -3500, description: "Cấu trúc nhà ở, giao thông, công cộng và mật độ tạo nên nhịp sống xã hội." },
  { id: "ecology", label: "Sinh thái", icon: "♧", group: "environment", parent: "environment", year: -300000, description: "Quan hệ giữa con người, tài nguyên, khí hậu và các hệ sống khác." },
  { id: "migration", label: "Di cư", icon: "⇢", group: "environment", parent: "environment", year: -70000, description: "Sự dịch chuyển nơi sống làm thay đổi quan hệ, sinh kế, bản sắc và chính sách." },
  { id: "socialization", label: "Xã hội hóa", icon: "◭", group: "culture", parent: "human", year: -200000, description: "Quá trình con người học ngôn ngữ, chuẩn mực, vai trò và cách trở thành thành viên xã hội." },
  { id: "primary-socialization", label: "Xã hội hóa sơ cấp", icon: "◡", group: "culture", parent: "socialization", year: -200000, description: "Giai đoạn học đầu đời qua gia đình, chăm sóc, bắt chước và gắn bó." },
  { id: "secondary-socialization", label: "Xã hội hóa thứ cấp", icon: "◧", group: "culture", parent: "socialization", year: -12000, description: "Quá trình học vai trò mới qua trường học, nghề nghiệp, cộng đồng và truyền thông." },
  { id: "role-learning", label: "Học vai trò", icon: "▣", group: "culture", parent: "socialization", year: -12000, description: "Việc tiếp nhận kỳ vọng gắn với vị trí như con cái, người lao động, công dân hoặc cha mẹ." },
  { id: "habitus", label: "Tập tính xã hội", icon: "≋", group: "culture", parent: "socialization", year: -12000, description: "Những khuynh hướng cảm nhận và hành động được hình thành qua hoàn cảnh sống lặp lại." },
  { id: "everyday-life", label: "Đời sống thường nhật", icon: "☷", group: "human", parent: "human", year: -300000, description: "Những thực hành hằng ngày nơi xã hội được tái tạo qua ăn ở, đi lại, làm việc và nghỉ ngơi." },
  { id: "routine", label: "Nếp sống", icon: "↺", group: "human", parent: "everyday-life", year: -200000, description: "Trật tự thời gian và hành vi lặp lại giúp con người cảm thấy ổn định và có thể dự đoán." },
  { id: "leisure", label: "Giải trí", icon: "◠", group: "human", parent: "everyday-life", year: -70000, description: "Không gian phục hồi, sáng tạo, tiêu dùng văn hóa và xây dựng quan hệ ngoài lao động." },
  { id: "food-practice", label: "Ăn uống", icon: "◍", group: "human", parent: "everyday-life", year: -300000, description: "Thực hành sinh tồn đồng thời biểu đạt bản sắc, giai tầng, chăm sóc và nghi lễ." },
  { id: "mobility", label: "Di chuyển hằng ngày", icon: "⇆", group: "environment", parent: "everyday-life", year: -300000, description: "Cách con người đi lại giữa nhà, việc làm, dịch vụ và không gian công cộng." },
  { id: "vulnerability", label: "Tổn thương xã hội", icon: "◇", group: "wellbeing", parent: "need", year: -300000, description: "Tình trạng dễ bị ảnh hưởng bởi nghèo đói, bệnh tật, bạo lực, loại trừ hoặc thiếu hỗ trợ." },
  { id: "disability", label: "Khuyết tật", icon: "◐", group: "wellbeing", parent: "vulnerability", year: -300000, description: "Trải nghiệm thân thể và xã hội cần được hiểu qua tiếp cận, hỗ trợ và quyền bình đẳng." },
  { id: "dependency", label: "Phụ thuộc", icon: "⊂", group: "wellbeing", parent: "vulnerability", year: -300000, description: "Tình trạng cần người khác hoặc thiết chế hỗ trợ để duy trì đời sống." },
  { id: "trauma", label: "Sang chấn", icon: "⚬", group: "wellbeing", parent: "vulnerability", year: -300000, description: "Dấu vết tâm lý - xã hội sau bạo lực, mất mát, thiên tai hoặc đứt gãy quan hệ." },
  { id: "social-support", label: "Hỗ trợ xã hội", icon: "✚", group: "wellbeing", parent: "vulnerability", year: -200000, description: "Nguồn lực cảm xúc, vật chất và thông tin từ gia đình, bạn bè, cộng đồng hoặc nhà nước." },
  { id: "fear", label: "Sợ hãi", icon: "!", group: "human", parent: "emotion", year: -300000, description: "Cảm xúc cảnh báo rủi ro, có thể bảo vệ con người nhưng cũng bị quyền lực khai thác." },
  { id: "shame", label: "Xấu hổ", icon: "◌", group: "human", parent: "emotion", year: -200000, description: "Cảm xúc xã hội gắn với ánh nhìn của người khác, danh dự và chuẩn mực." },
  { id: "hope", label: "Hy vọng", icon: "✦", group: "human", parent: "emotion", year: -200000, description: "Năng lực hướng tới tương lai, giúp con người vượt qua bất định và hành động tập thể." },
  { id: "anger", label: "Phẫn nộ", icon: "▲", group: "human", parent: "emotion", year: -200000, description: "Cảm xúc trước bất công, xúc phạm hoặc bị tước quyền, có thể dẫn tới phản kháng." },
  { id: "learning", label: "Học tập", icon: "⌘", group: "human", parent: "knowledge", year: -200000, description: "Quá trình tiếp nhận và biến đổi tri thức qua kinh nghiệm, giáo dục và tương tác." },
  { id: "critical-thinking", label: "Tư duy phản biện", icon: "?", group: "human", parent: "knowledge", year: -2500, description: "Khả năng xem xét bằng chứng, quyền lực và giả định đằng sau một cách hiểu." },
  { id: "bias", label: "Thiên kiến", icon: "◒", group: "human", parent: "knowledge", year: -200000, description: "Khuynh hướng nhận thức giúp quyết định nhanh nhưng có thể tạo định kiến và sai lệch." },
  { id: "worldview", label: "Thế giới quan", icon: "◎", group: "value", parent: "knowledge", year: -70000, description: "Khung hiểu biết tổng quát về con người, tự nhiên, xã hội và điều đáng sống." },
  { id: "kinship", label: "Thân tộc", icon: "⌁", group: "relation", parent: "family", year: -200000, description: "Mạng quan hệ huyết thống, hôn nhân, nhận nuôi và nghĩa vụ chăm sóc." },
  { id: "parenting", label: "Nuôi dạy con", icon: "◡", group: "relation", parent: "family", year: -200000, description: "Thực hành chăm sóc, kỷ luật, yêu thương và truyền vốn văn hóa giữa thế hệ." },
  { id: "intergenerational", label: "Liên thế hệ", icon: "⇅", group: "relation", parent: "family", year: -200000, description: "Quan hệ giữa thế hệ trong truyền ký ức, tài sản, chăm sóc và xung đột giá trị." },
  { id: "domestic-work", label: "Lao động gia đình", icon: "⌂", group: "economy", parent: "family", year: -200000, description: "Công việc chăm sóc, nấu nướng, dọn dẹp và tổ chức đời sống thường bị vô hình hóa." },
  { id: "solidarity", label: "Đoàn kết", icon: "◉", group: "relation", parent: "community", year: -12000, description: "Cảm giác cùng thuộc về và sẵn sàng hỗ trợ nhau trước rủi ro hoặc mục tiêu chung." },
  { id: "collective-action", label: "Hành động tập thể", icon: "▦", group: "relation", parent: "community", year: -12000, description: "Sự phối hợp của nhiều người để giải quyết vấn đề chung hoặc thay đổi trật tự xã hội." },
  { id: "social-capital", label: "Vốn xã hội", icon: "◇", group: "relation", parent: "community", year: -12000, description: "Nguồn lực đến từ mạng lưới, niềm tin và khả năng tiếp cận hỗ trợ." },
  { id: "human-rights", label: "Nhân quyền", icon: "◈", group: "institution", parent: "rights", year: 1948, description: "Bộ chuẩn mực phổ quát khẳng định phẩm giá và quyền cơ bản của mọi người." },
  { id: "civil-rights", label: "Quyền dân sự", icon: "▣", group: "institution", parent: "rights", year: 1789, description: "Quyền tự do cá nhân, bình đẳng trước pháp luật, biểu đạt và bảo vệ khỏi lạm quyền." },
  { id: "social-rights", label: "Quyền xã hội", icon: "▦", group: "institution", parent: "rights", year: 1900, description: "Quyền tiếp cận giáo dục, y tế, an sinh, nhà ở và điều kiện sống tối thiểu." },
  { id: "child-rights", label: "Quyền trẻ em", icon: "◡", group: "institution", parent: "rights", year: 1989, description: "Các bảo đảm để trẻ em được bảo vệ, phát triển, tham gia và được lắng nghe." },
  { id: "discrimination", label: "Phân biệt đối xử", icon: "×", group: "power", parent: "power-inequality", year: -12000, description: "Đối xử bất lợi dựa trên giới, giai tầng, tộc người, khuyết tật, tuổi tác hoặc bản dạng." },
  { id: "privilege", label: "Đặc quyền", icon: "▲", group: "power", parent: "power-inequality", year: -12000, description: "Lợi thế xã hội được hưởng như điều hiển nhiên nhờ vị trí trong cấu trúc quyền lực." },
  { id: "marginalization", label: "Bên lề hóa", icon: "◌", group: "power", parent: "power-inequality", year: -12000, description: "Quá trình đẩy một nhóm ra khỏi nguồn lực, tiếng nói và sự công nhận." },
  { id: "violence", label: "Bạo lực", icon: "⚡", group: "power", parent: "power-inequality", year: -300000, description: "Tổn hại thể chất, tinh thần, biểu tượng hoặc cấu trúc làm giới hạn đời sống con người." },
  { id: "social-control", label: "Kiểm soát xã hội", icon: "⬠", group: "power", parent: "power-inequality", year: -12000, description: "Cơ chế chính thức và phi chính thức điều chỉnh hành vi qua luật, chuẩn mực, giám sát và trừng phạt." },
  { id: "unemployment", label: "Thất nghiệp", icon: "∅", group: "economy", parent: "economy", year: 1800, description: "Tình trạng thiếu việc làm tạo áp lực lên thu nhập, bản sắc, gia đình và sức khỏe tinh thần." },
  { id: "precarity", label: "Bấp bênh", icon: "⌁", group: "economy", parent: "economy", year: 1970, description: "Điều kiện sống và lao động thiếu ổn định, bảo vệ và khả năng dự đoán tương lai." },
  { id: "informal-economy", label: "Kinh tế phi chính thức", icon: "◧", group: "economy", parent: "economy", year: -3000, description: "Hoạt động sinh kế ngoài khung lao động chính thức, vừa linh hoạt vừa dễ thiếu bảo vệ." },
  { id: "digital-identity", label: "Danh tính số", icon: "@", group: "technology", parent: "technology", year: 1990, description: "Cách con người được nhận diện, biểu đạt và đánh giá qua dữ liệu, hồ sơ và nền tảng số." },
  { id: "surveillance", label: "Giám sát", icon: "◉", group: "technology", parent: "technology", year: 1800, description: "Theo dõi hành vi bằng thiết chế hoặc công nghệ, ảnh hưởng đến quyền riêng tư và tự do." },
  { id: "platform-labor", label: "Lao động nền tảng", icon: "▥", group: "technology", parent: "technology", year: 2010, description: "Hình thức lao động qua ứng dụng số, gắn với thuật toán, đánh giá và bấp bênh." },
  { id: "housing", label: "Nhà ở", icon: "⌂", group: "environment", parent: "environment", year: -12000, description: "Không gian cư trú gắn với an toàn, thân mật, tài sản, giai tầng và quyền được ở." },
  { id: "public-space", label: "Không gian công cộng", icon: "□", group: "environment", parent: "environment", year: -3500, description: "Nơi con người gặp gỡ, tranh luận, nghỉ ngơi và thể hiện quyền hiện diện." },
  { id: "climate-risk", label: "Rủi ro khí hậu", icon: "☂", group: "environment", parent: "environment", year: 1850, description: "Tác động của biến đổi khí hậu lên sức khỏe, di cư, sinh kế và bất bình đẳng." },
  { id: "justice", label: "Công lý", icon: "⚖", group: "institution", parent: "institution", year: -3000, description: "Nguyên tắc xử lý xung đột và phân bổ trách nhiệm, quyền lợi, hình phạt một cách chính đáng." },
  { id: "welfare", label: "An sinh xã hội", icon: "▤", group: "institution", parent: "institution", year: 1880, description: "Hệ thống bảo vệ con người trước rủi ro như bệnh tật, thất nghiệp, tuổi già và nghèo đói." },
  { id: "social-structure", label: "Cấu trúc xã hội", icon: "▧", group: "power", parent: "society", year: -12000, description: "Mẫu hình tương đối bền vững của vị thế, vai trò, thiết chế và phân bổ nguồn lực." },
  { id: "status", label: "Vị thế", icon: "▴", group: "power", parent: "social-structure", year: -12000, description: "Vị trí xã hội của một người trong gia đình, cộng đồng, nghề nghiệp hoặc thể chế." },
  { id: "role", label: "Vai trò", icon: "◫", group: "power", parent: "social-structure", year: -12000, description: "Tập hợp kỳ vọng hành vi gắn với một vị thế xã hội cụ thể." },
  { id: "role-conflict", label: "Xung đột vai trò", icon: "⚭", group: "power", parent: "social-structure", year: -12000, description: "Tình huống các vai trò như cha mẹ, người lao động, công dân tạo yêu cầu mâu thuẫn." },
  { id: "institutionalization", label: "Thiết chế hóa", icon: "▣", group: "institution", parent: "institution", year: -3000, description: "Quá trình thực hành lặp lại trở thành quy tắc, tổ chức và trật tự được thừa nhận." },
  { id: "social-order", label: "Trật tự xã hội", icon: "☷", group: "institution", parent: "institution", year: -12000, description: "Mức ổn định của kỳ vọng, luật lệ và phối hợp giúp đời sống chung có thể dự đoán." },
  { id: "legitimacy", label: "Tính chính danh", icon: "◈", group: "institution", parent: "governance", year: -3000, description: "Mức độ một quyền lực hoặc thiết chế được người dân xem là hợp lý và đáng tuân theo." },
  { id: "bureaucracy", label: "Quan liêu", icon: "▦", group: "institution", parent: "governance", year: -3000, description: "Hình thức tổ chức dựa trên quy tắc, hồ sơ, phân cấp và chuyên môn hóa." },
  { id: "social-change", label: "Biến đổi xã hội", icon: "⇢", group: "culture", parent: "society", year: -12000, description: "Sự thay đổi trong quan hệ, giá trị, thiết chế, công nghệ và phân bổ quyền lực." },
  { id: "modernization", label: "Hiện đại hóa", icon: "⬡", group: "culture", parent: "social-change", year: 1750, description: "Quá trình công nghiệp hóa, đô thị hóa, duy lý hóa và mở rộng nhà nước hiện đại." },
  { id: "globalization", label: "Toàn cầu hóa", icon: "◎", group: "culture", parent: "social-change", year: 1500, description: "Sự kết nối xuyên biên giới về hàng hóa, con người, thông tin, văn hóa và rủi ro." },
  { id: "social-movement", label: "Phong trào xã hội", icon: "◬", group: "relation", parent: "social-change", year: 1800, description: "Hành động tập thể có tổ chức nhằm bảo vệ quyền lợi hoặc thay đổi chuẩn mực và thiết chế." },
  { id: "demographic-change", label: "Biến đổi dân số", icon: "◷", group: "lifecycle", parent: "social-change", year: -12000, description: "Thay đổi về sinh, tử, tuổi thọ, di cư và cấu trúc tuổi ảnh hưởng đến xã hội." },
  { id: "interaction", label: "Tương tác xã hội", icon: "⇄", group: "relation", parent: "relationship", year: -200000, description: "Quá trình con người cùng định nghĩa tình huống, phản hồi và điều chỉnh hành vi." },
  { id: "symbolic-interaction", label: "Tương tác biểu tượng", icon: "✦", group: "relation", parent: "interaction", year: 1900, description: "Cách ý nghĩa được tạo ra qua ký hiệu, ngôn ngữ, vai diễn và diễn giải lẫn nhau." },
  { id: "impression-management", label: "Quản trị ấn tượng", icon: "◐", group: "relation", parent: "interaction", year: 1950, description: "Cách con người trình diễn bản thân để được nhìn nhận phù hợp trong từng tình huống." },
  { id: "boundary", label: "Ranh giới xã hội", icon: "║", group: "relation", parent: "interaction", year: -12000, description: "Đường phân biệt giữa trong - ngoài nhóm, thân - lạ, hợp lệ - lệch chuẩn." },
  { id: "stigma", label: "Kỳ thị", icon: "×", group: "power", parent: "interaction", year: -12000, description: "Dấu hiệu xã hội làm một người hoặc nhóm bị giảm giá trị và bị đối xử khác biệt." },
  { id: "social-network", label: "Mạng quan hệ", icon: "✣", group: "relation", parent: "relationship", year: -200000, description: "Cấu trúc các liên kết cá nhân và nhóm qua đó thông tin, hỗ trợ và cơ hội lưu chuyển." },
  { id: "strong-ties", label: "Liên kết mạnh", icon: "●", group: "relation", parent: "social-network", year: -200000, description: "Quan hệ gần gũi, thường xuyên và giàu tin cậy như gia đình, bạn thân." },
  { id: "weak-ties", label: "Liên kết yếu", icon: "○", group: "relation", parent: "social-network", year: -200000, description: "Quan hệ lỏng hơn nhưng quan trọng để tiếp cận thông tin, cơ hội và thế giới ngoài nhóm thân." },
  { id: "bridging-capital", label: "Vốn cầu nối", icon: "⌁", group: "relation", parent: "social-network", year: -12000, description: "Nguồn lực từ các liên kết bắc cầu giữa nhóm khác nhau, giúp mở rộng cơ hội." },
  { id: "bonding-capital", label: "Vốn gắn kết", icon: "⊂", group: "relation", parent: "social-network", year: -12000, description: "Nguồn lực từ liên kết nội nhóm chặt chẽ, tạo hỗ trợ nhưng có thể khép kín." },
  { id: "poverty", label: "Nghèo đói", icon: "∅", group: "power", parent: "power-inequality", year: -12000, description: "Tình trạng thiếu nguồn lực vật chất, dịch vụ, cơ hội và quyền tham gia đầy đủ vào xã hội." },
  { id: "relative-deprivation", label: "Thiếu hụt tương đối", icon: "◒", group: "power", parent: "poverty", year: 1900, description: "Cảm nhận bị thiệt thòi khi so sánh điều kiện sống với nhóm tham chiếu." },
  { id: "social-exclusion", label: "Loại trừ xã hội", icon: "⊘", group: "power", parent: "poverty", year: 1970, description: "Quá trình bị tách khỏi việc làm, dịch vụ, quan hệ, quyền và không gian công cộng." },
  { id: "life-chances", label: "Cơ hội sống", icon: "⇧", group: "power", parent: "poverty", year: 1920, description: "Khả năng tiếp cận giáo dục, sức khỏe, việc làm, an toàn và tuổi thọ do vị trí xã hội định hình." },
  { id: "intersectionality", label: "Giao thoa bất bình đẳng", icon: "✣", group: "power", parent: "power-inequality", year: 1989, description: "Cách giới, giai tầng, tộc người, khuyết tật và tuổi tác chồng lấn để tạo trải nghiệm bất bình đẳng riêng." },
  { id: "care-economy", label: "Kinh tế chăm sóc", icon: "♡", group: "economy", parent: "economy", year: -200000, description: "Hệ hoạt động chăm sóc được trả công và không trả công duy trì con người và xã hội." },
  { id: "emotional-labor", label: "Lao động cảm xúc", icon: "◌", group: "economy", parent: "labor", year: 1980, description: "Việc quản lý cảm xúc trong công việc để đáp ứng kỳ vọng của tổ chức hoặc khách hàng." },
  { id: "work-life-balance", label: "Cân bằng sống - làm", icon: "⚖", group: "economy", parent: "labor", year: 1970, description: "Khả năng điều hòa lao động, chăm sóc, nghỉ ngơi, quan hệ và phát triển cá nhân." },
  { id: "social-epidemiology", label: "Dịch tễ học xã hội", icon: "+", group: "wellbeing", parent: "health", year: 1950, description: "Nghiên cứu cách điều kiện xã hội tạo phân bố bệnh tật, tuổi thọ và sức khỏe." },
  { id: "health-inequality", label: "Bất bình đẳng sức khỏe", icon: "▤", group: "wellbeing", parent: "health", year: 1900, description: "Chênh lệch sức khỏe giữa nhóm xã hội do thu nhập, môi trường, chăm sóc và quyền lực." },
  { id: "institutional-trust", label: "Niềm tin thể chế", icon: "◈", group: "institution", parent: "trust", year: -3000, description: "Mức độ người dân tin rằng nhà nước, luật pháp và tổ chức công hành động công bằng." },
  { id: "civic-engagement", label: "Gắn kết công dân", icon: "▣", group: "institution", parent: "citizenship", year: -500, description: "Sự tham gia vào bầu cử, thảo luận, tổ chức cộng đồng và giám sát quyền lực." },
  { id: "digital-divide", label: "Khoảng cách số", icon: "⌗", group: "technology", parent: "technology", year: 1990, description: "Bất bình đẳng trong tiếp cận thiết bị, kỹ năng, dữ liệu và lợi ích từ công nghệ." },
  { id: "social-theory", label: "Lý thuyết xã hội", icon: "◬", group: "theory", parent: "society", year: 1800, description: "Các khung giải thích cách con người, quan hệ và cấu trúc xã hội tạo nên đời sống chung." },
  { id: "functionalism", label: "Chức năng luận", icon: "▦", group: "theory", parent: "social-theory", year: 1900, description: "Cách nhìn xã hội như hệ thống các bộ phận liên kết để duy trì trật tự và ổn định." },
  { id: "conflict-theory", label: "Lý thuyết xung đột", icon: "⚡", group: "theory", parent: "social-theory", year: 1848, description: "Nhấn mạnh mâu thuẫn lợi ích, quyền lực và bất bình đẳng trong sự vận hành xã hội." },
  { id: "symbolic-interactionism", label: "Tương tác luận biểu tượng", icon: "✦", group: "theory", parent: "social-theory", year: 1900, description: "Phân tích cách ý nghĩa và bản sắc được tạo ra qua tương tác hằng ngày." },
  { id: "feminist-theory", label: "Lý thuyết nữ quyền", icon: "♀", group: "theory", parent: "social-theory", year: 1800, description: "Phân tích quyền lực giới, lao động chăm sóc, thân thể và bất bình đẳng trong đời sống xã hội." },
  { id: "postcolonial-theory", label: "Hậu thuộc địa", icon: "◍", group: "theory", parent: "social-theory", year: 1950, description: "Xem xét di sản thuộc địa trong bản sắc, tri thức, phát triển và quan hệ quyền lực toàn cầu." },
  { id: "research-methods", label: "Phương pháp nghiên cứu", icon: "⌕", group: "research", parent: "society", year: 1800, description: "Công cụ thu thập và diễn giải bằng chứng về đời sống con người trong bối cảnh xã hội." },
  { id: "survey", label: "Khảo sát", icon: "☷", group: "research", parent: "research-methods", year: 1800, description: "Phương pháp thu thập dữ liệu có cấu trúc từ nhiều người để đo thái độ, hành vi và điều kiện sống." },
  { id: "interview", label: "Phỏng vấn sâu", icon: "❝", group: "research", parent: "research-methods", year: 1900, description: "Cách tiếp cận trải nghiệm, ý nghĩa và câu chuyện đời sống qua đối thoại có định hướng." },
  { id: "ethnography", label: "Dân tộc ký", icon: "◉", group: "research", parent: "research-methods", year: 1900, description: "Nghiên cứu đời sống từ bên trong bối cảnh qua quan sát, tham dự và ghi chép dài hạn." },
  { id: "participant-observation", label: "Quan sát tham dự", icon: "◐", group: "research", parent: "research-methods", year: 1900, description: "Phương pháp hiểu thực hành xã hội bằng cách hiện diện và tham gia vào môi trường nghiên cứu." },
  { id: "life-history", label: "Lịch sử đời sống", icon: "◷", group: "research", parent: "research-methods", year: 1920, description: "Cách phân tích tiểu sử cá nhân để thấy cấu trúc xã hội đi qua một đời người." },
  { id: "comparative-method", label: "So sánh xã hội", icon: "⇄", group: "research", parent: "research-methods", year: 1800, description: "Đối chiếu nhóm, quốc gia hoặc thời kỳ để nhận ra khác biệt, tương đồng và cơ chế xã hội." },
  { id: "ethics-research", label: "Đạo đức nghiên cứu", icon: "⚖", group: "research", parent: "research-methods", year: 1945, description: "Nguyên tắc bảo vệ người tham gia, đồng thuận, bảo mật và tránh gây hại trong nghiên cứu." },
  { id: "embodiment", label: "Thân thể xã hội", icon: "◒", group: "human", parent: "body-mind", year: -300000, description: "Cách thân thể vừa là nền tảng sinh học vừa được xã hội định nghĩa, kỷ luật và biểu đạt." },
  { id: "sexuality", label: "Tính dục", icon: "⚭", group: "human", parent: "body-mind", year: -300000, description: "Chiều kích ham muốn, thân mật, chuẩn mực và quyền tự chủ thân thể." },
  { id: "reproduction", label: "Sinh sản", icon: "◡", group: "human", parent: "body-mind", year: -300000, description: "Quá trình sinh học và xã hội liên quan tới gia đình, giới, chăm sóc, quyền và chính sách." },
  { id: "illness-experience", label: "Trải nghiệm bệnh tật", icon: "+", group: "wellbeing", parent: "health", year: -300000, description: "Cách con người sống với bệnh, tìm kiếm chăm sóc và tái định nghĩa bản thân." },
  { id: "intimacy", label: "Thân mật", icon: "♡", group: "relation", parent: "relationship", year: -200000, description: "Quan hệ gần gũi về cảm xúc, thân thể và niềm tin, nơi con người tìm sự công nhận và an toàn." },
  { id: "friendship", label: "Tình bạn", icon: "◈", group: "relation", parent: "intimacy", year: -200000, description: "Quan hệ tự nguyện dựa trên tin cậy, chia sẻ và hỗ trợ ngoài khuôn khổ huyết thống." },
  { id: "love", label: "Tình yêu", icon: "♥", group: "relation", parent: "intimacy", year: -200000, description: "Hình thức gắn bó cảm xúc mạnh, chịu ảnh hưởng bởi văn hóa, kinh tế và chuẩn mực giới." },
  { id: "marriage", label: "Hôn nhân", icon: "◇", group: "institution", parent: "intimacy", year: -12000, description: "Thiết chế hóa quan hệ thân mật, tài sản, sinh sản, chăm sóc và liên minh gia đình." },
  { id: "loneliness", label: "Cô đơn", icon: "○", group: "wellbeing", parent: "intimacy", year: -200000, description: "Trải nghiệm thiếu kết nối có ý nghĩa, liên quan tới sức khỏe, đô thị hóa và mạng xã hội." },
  { id: "deviance", label: "Lệch chuẩn", icon: "∴", group: "power", parent: "social-control", year: -12000, description: "Hành vi hoặc bản dạng bị xem là vi phạm chuẩn mực trong một bối cảnh xã hội cụ thể." },
  { id: "labeling", label: "Gán nhãn", icon: "⌁", group: "power", parent: "deviance", year: 1960, description: "Quá trình xã hội gọi tên một người là lệch chuẩn, qua đó ảnh hưởng đến bản sắc và cơ hội." },
  { id: "punishment", label: "Trừng phạt", icon: "▣", group: "institution", parent: "deviance", year: -3000, description: "Phản ứng chính thức hoặc phi chính thức nhằm răn đe, kiểm soát hoặc tái lập trật tự." },
  { id: "rehabilitation", label: "Tái hòa nhập", icon: "⤴", group: "institution", parent: "deviance", year: 1800, description: "Cách hỗ trợ người từng bị loại trừ hoặc vi phạm chuẩn mực quay lại đời sống xã hội." },
  { id: "public-opinion", label: "Dư luận", icon: "◌", group: "culture", parent: "media", year: 1700, description: "Tập hợp nhận định và cảm xúc công chúng có thể ảnh hưởng đến chính sách và chuẩn mực." },
  { id: "moral-panic", label: "Hoảng loạn đạo đức", icon: "!", group: "culture", parent: "public-opinion", year: 1970, description: "Sự phóng đại mối đe dọa đối với giá trị xã hội, thường nhắm vào một nhóm bị gán nhãn." },
  { id: "misinformation", label: "Thông tin sai lệch", icon: "?", group: "technology", parent: "media", year: 1900, description: "Thông tin sai hoặc gây hiểu lầm làm méo mó nhận thức, niềm tin và hành động tập thể." },
  { id: "social-policy", label: "Chính sách xã hội", icon: "▤", group: "institution", parent: "welfare", year: 1880, description: "Can thiệp công nhằm cải thiện phúc lợi, giảm rủi ro và điều chỉnh bất bình đẳng." },
  { id: "redistribution", label: "Tái phân phối", icon: "⇆", group: "institution", parent: "social-policy", year: 1900, description: "Cơ chế chuyển nguồn lực qua thuế, trợ cấp, dịch vụ công và an sinh." },
  { id: "recognition-policy", label: "Chính sách công nhận", icon: "◊", group: "institution", parent: "social-policy", year: 1960, description: "Chính sách bảo vệ bản sắc, chống kỳ thị và khẳng định phẩm giá của nhóm bị gạt ra bên lề." },
  { id: "capability", label: "Năng lực sống", icon: "↗", group: "wellbeing", parent: "social-policy", year: 1980, description: "Khả năng thực chất để con người sống đời sống mà họ có lý do để coi trọng." },
  { id: "risk-society", label: "Xã hội rủi ro", icon: "☂", group: "theory", parent: "social-theory", year: 1986, description: "Cách hiện đại hóa tạo rủi ro mới như ô nhiễm, khủng hoảng tài chính, công nghệ và khí hậu." }
];

const relationships = [
  ["human", "body-mind"], ["human", "need"], ["human", "agency"], ["human", "relationship"], ["human", "society"],
  ["body-mind", "emotion"], ["body-mind", "knowledge"], ["need", "safety"], ["need", "belonging"], ["need", "dignity"],
  ["agency", "choice"], ["agency", "responsibility"], ["relationship", "family"], ["relationship", "community"], ["relationship", "trust"],
  ["society", "institution"], ["society", "culture"], ["society", "economy"], ["society", "technology"],
  ["institution", "law"], ["institution", "rights"], ["institution", "governance"], ["culture", "identity"], ["culture", "norm"],
  ["economy", "market"], ["economy", "labor"], ["technology", "media"], ["technology", "digital-network"],
  ["dignity", "law"], ["choice", "market"], ["responsibility", "governance"], ["family", "identity"], ["community", "norm"],
  ["trust", "institution"], ["media", "emotion"], ["digital-network", "relationship"], ["labor", "dignity"],
  ["human", "life-course"], ["human", "meaning-value"], ["society", "power-inequality"], ["society", "environment"],
  ["body-mind", "perception"], ["body-mind", "memory"], ["body-mind", "stress"], ["body-mind", "mental-health"],
  ["need", "care"], ["need", "health"], ["need", "education"], ["need", "recognition"],
  ["agency", "motivation"], ["agency", "habit"], ["agency", "resilience"], ["agency", "participation"],
  ["relationship", "communication"], ["relationship", "empathy"], ["relationship", "conflict"], ["relationship", "reciprocity"],
  ["life-course", "childhood"], ["life-course", "adolescence"], ["life-course", "adulthood"], ["life-course", "aging"],
  ["meaning-value", "belief"], ["meaning-value", "morality"], ["meaning-value", "purpose"], ["meaning-value", "freedom"],
  ["power-inequality", "class"], ["power-inequality", "gender"], ["power-inequality", "ethnicity"], ["power-inequality", "social-mobility"],
  ["culture", "language"], ["culture", "ritual"], ["culture", "collective-memory"],
  ["institution", "citizenship"], ["institution", "public-service"],
  ["economy", "livelihood"], ["economy", "consumption"],
  ["technology", "algorithm"], ["technology", "privacy"],
  ["environment", "urban-space"], ["environment", "ecology"], ["environment", "migration"],
  ["care", "health"], ["education", "social-mobility"], ["recognition", "identity"], ["stress", "mental-health"],
  ["communication", "trust"], ["conflict", "governance"], ["morality", "law"], ["freedom", "rights"],
  ["class", "education"], ["gender", "family"], ["migration", "identity"], ["algorithm", "privacy"], ["urban-space", "community"],
  ["human", "socialization"], ["human", "everyday-life"],
  ["socialization", "primary-socialization"], ["socialization", "secondary-socialization"], ["socialization", "role-learning"], ["socialization", "habitus"],
  ["everyday-life", "routine"], ["everyday-life", "leisure"], ["everyday-life", "food-practice"], ["everyday-life", "mobility"],
  ["need", "vulnerability"], ["vulnerability", "disability"], ["vulnerability", "dependency"], ["vulnerability", "trauma"], ["vulnerability", "social-support"],
  ["emotion", "fear"], ["emotion", "shame"], ["emotion", "hope"], ["emotion", "anger"],
  ["knowledge", "learning"], ["knowledge", "critical-thinking"], ["knowledge", "bias"], ["knowledge", "worldview"],
  ["family", "kinship"], ["family", "parenting"], ["family", "intergenerational"], ["family", "domestic-work"],
  ["community", "solidarity"], ["community", "collective-action"], ["community", "social-capital"],
  ["rights", "human-rights"], ["rights", "civil-rights"], ["rights", "social-rights"], ["rights", "child-rights"],
  ["power-inequality", "discrimination"], ["power-inequality", "privilege"], ["power-inequality", "marginalization"], ["power-inequality", "violence"], ["power-inequality", "social-control"],
  ["economy", "unemployment"], ["economy", "precarity"], ["economy", "informal-economy"],
  ["technology", "digital-identity"], ["technology", "surveillance"], ["technology", "platform-labor"],
  ["environment", "housing"], ["environment", "public-space"], ["environment", "climate-risk"],
  ["institution", "justice"], ["institution", "welfare"],
  ["primary-socialization", "family"], ["secondary-socialization", "education"], ["habitus", "class"], ["role-learning", "gender"],
  ["routine", "habit"], ["leisure", "identity"], ["mobility", "urban-space"], ["food-practice", "ritual"],
  ["disability", "rights"], ["dependency", "care"], ["trauma", "mental-health"], ["social-support", "resilience"],
  ["shame", "norm"], ["anger", "collective-action"], ["hope", "resilience"], ["fear", "social-control"],
  ["bias", "discrimination"], ["worldview", "belief"], ["critical-thinking", "education"], ["learning", "social-mobility"],
  ["parenting", "childhood"], ["intergenerational", "collective-memory"], ["domestic-work", "gender"],
  ["solidarity", "social-support"], ["social-capital", "trust"], ["collective-action", "participation"],
  ["social-rights", "welfare"], ["child-rights", "childhood"], ["civil-rights", "citizenship"], ["justice", "law"],
  ["precarity", "stress"], ["unemployment", "mental-health"], ["informal-economy", "livelihood"], ["platform-labor", "algorithm"],
  ["surveillance", "privacy"], ["digital-identity", "identity"], ["housing", "safety"], ["public-space", "citizenship"], ["climate-risk", "migration"],
  ["society", "social-structure"], ["social-structure", "status"], ["social-structure", "role"], ["social-structure", "role-conflict"],
  ["institution", "institutionalization"], ["institution", "social-order"], ["governance", "legitimacy"], ["governance", "bureaucracy"],
  ["society", "social-change"], ["social-change", "modernization"], ["social-change", "globalization"], ["social-change", "social-movement"], ["social-change", "demographic-change"],
  ["relationship", "interaction"], ["interaction", "symbolic-interaction"], ["interaction", "impression-management"], ["interaction", "boundary"], ["interaction", "stigma"],
  ["relationship", "social-network"], ["social-network", "strong-ties"], ["social-network", "weak-ties"], ["social-network", "bridging-capital"], ["social-network", "bonding-capital"],
  ["power-inequality", "poverty"], ["poverty", "relative-deprivation"], ["poverty", "social-exclusion"], ["poverty", "life-chances"],
  ["power-inequality", "intersectionality"], ["economy", "care-economy"], ["labor", "emotional-labor"], ["labor", "work-life-balance"],
  ["health", "social-epidemiology"], ["health", "health-inequality"], ["trust", "institutional-trust"], ["citizenship", "civic-engagement"], ["technology", "digital-divide"],
  ["status", "identity"], ["role", "role-learning"], ["role-conflict", "stress"], ["institutionalization", "norm"], ["social-order", "social-control"],
  ["legitimacy", "institutional-trust"], ["bureaucracy", "public-service"], ["modernization", "urban-space"], ["globalization", "migration"],
  ["social-movement", "collective-action"], ["demographic-change", "aging"], ["symbolic-interaction", "language"], ["impression-management", "shame"],
  ["boundary", "ethnicity"], ["stigma", "discrimination"], ["weak-ties", "social-mobility"], ["strong-ties", "social-support"],
  ["bridging-capital", "weak-ties"], ["bonding-capital", "solidarity"], ["poverty", "vulnerability"], ["relative-deprivation", "anger"],
  ["social-exclusion", "marginalization"], ["life-chances", "class"], ["intersectionality", "gender"], ["intersectionality", "ethnicity"],
  ["care-economy", "domestic-work"], ["care-economy", "welfare"], ["emotional-labor", "mental-health"], ["work-life-balance", "family"],
  ["social-epidemiology", "health-inequality"], ["health-inequality", "class"], ["institutional-trust", "legitimacy"],
  ["civic-engagement", "participation"], ["digital-divide", "education"], ["digital-divide", "social-exclusion"],
  ["society", "social-theory"], ["social-theory", "functionalism"], ["social-theory", "conflict-theory"], ["social-theory", "symbolic-interactionism"], ["social-theory", "feminist-theory"], ["social-theory", "postcolonial-theory"], ["social-theory", "risk-society"],
  ["society", "research-methods"], ["research-methods", "survey"], ["research-methods", "interview"], ["research-methods", "ethnography"], ["research-methods", "participant-observation"], ["research-methods", "life-history"], ["research-methods", "comparative-method"], ["research-methods", "ethics-research"],
  ["body-mind", "embodiment"], ["body-mind", "sexuality"], ["body-mind", "reproduction"], ["health", "illness-experience"],
  ["relationship", "intimacy"], ["intimacy", "friendship"], ["intimacy", "love"], ["intimacy", "marriage"], ["intimacy", "loneliness"],
  ["social-control", "deviance"], ["deviance", "labeling"], ["deviance", "punishment"], ["deviance", "rehabilitation"],
  ["media", "public-opinion"], ["public-opinion", "moral-panic"], ["media", "misinformation"],
  ["welfare", "social-policy"], ["social-policy", "redistribution"], ["social-policy", "recognition-policy"], ["social-policy", "capability"],
  ["functionalism", "social-order"], ["conflict-theory", "power-inequality"], ["symbolic-interactionism", "interaction"], ["feminist-theory", "gender"], ["postcolonial-theory", "ethnicity"], ["risk-society", "climate-risk"],
  ["survey", "public-opinion"], ["interview", "life-history"], ["ethnography", "everyday-life"], ["participant-observation", "interaction"], ["comparative-method", "globalization"],
  ["embodiment", "gender"], ["sexuality", "rights"], ["reproduction", "care"], ["illness-experience", "identity"],
  ["friendship", "social-support"], ["love", "family"], ["marriage", "law"], ["loneliness", "mental-health"],
  ["labeling", "stigma"], ["punishment", "justice"], ["rehabilitation", "social-support"], ["moral-panic", "deviance"], ["misinformation", "public-opinion"],
  ["redistribution", "poverty"], ["recognition-policy", "marginalization"], ["capability", "freedom"]
];

const focusSets = {
  core: ["human", "body-mind", "need", "agency", "relationship", "family", "community", "trust", "communication", "empathy", "conflict", "reciprocity", "intimacy", "interaction", "social-network", "life-course", "childhood", "adolescence", "adulthood", "aging", "meaning-value", "socialization", "everyday-life", "society", "social-structure", "social-change", "social-theory", "research-methods"],
  self: ["human", "body-mind", "emotion", "fear", "shame", "hope", "anger", "knowledge", "learning", "critical-thinking", "bias", "worldview", "perception", "memory", "stress", "mental-health", "embodiment", "sexuality", "reproduction", "need", "safety", "belonging", "dignity", "care", "health", "illness-experience", "social-epidemiology", "health-inequality", "education", "recognition", "vulnerability", "disability", "dependency", "trauma", "social-support", "agency", "choice", "responsibility", "motivation", "habit", "resilience", "participation", "life-course", "childhood", "adolescence", "adulthood", "aging", "meaning-value", "belief", "morality", "purpose", "freedom", "everyday-life", "routine", "leisure", "food-practice", "work-life-balance", "capability"],
  relations: ["human", "relationship", "intimacy", "friendship", "love", "marriage", "loneliness", "interaction", "symbolic-interaction", "impression-management", "boundary", "stigma", "social-network", "strong-ties", "weak-ties", "bridging-capital", "bonding-capital", "family", "kinship", "parenting", "intergenerational", "domestic-work", "community", "solidarity", "collective-action", "social-capital", "trust", "institutional-trust", "communication", "empathy", "conflict", "reciprocity", "socialization", "primary-socialization", "secondary-socialization", "role-learning", "habitus", "society", "social-structure", "status", "role", "role-conflict", "culture", "identity", "norm", "language", "ritual", "collective-memory", "life-course", "childhood", "adolescence", "adulthood", "aging", "symbolic-interactionism"],
  systems: ["human", "society", "social-theory", "functionalism", "conflict-theory", "symbolic-interactionism", "feminist-theory", "postcolonial-theory", "risk-society", "research-methods", "survey", "interview", "ethnography", "participant-observation", "life-history", "comparative-method", "ethics-research", "social-structure", "status", "role", "role-conflict", "institution", "law", "rights", "human-rights", "civil-rights", "social-rights", "child-rights", "governance", "legitimacy", "bureaucracy", "institutionalization", "social-order", "citizenship", "civic-engagement", "public-service", "justice", "welfare", "social-policy", "redistribution", "recognition-policy", "culture", "identity", "norm", "language", "ritual", "collective-memory", "social-change", "modernization", "globalization", "social-movement", "demographic-change", "economy", "market", "labor", "emotional-labor", "work-life-balance", "care-economy", "livelihood", "consumption", "unemployment", "precarity", "informal-economy", "technology", "media", "public-opinion", "moral-panic", "misinformation", "digital-network", "algorithm", "privacy", "digital-identity", "surveillance", "platform-labor", "digital-divide", "power-inequality", "poverty", "relative-deprivation", "social-exclusion", "life-chances", "intersectionality", "class", "gender", "ethnicity", "social-mobility", "discrimination", "privilege", "marginalization", "violence", "social-control", "deviance", "labeling", "punishment", "rehabilitation", "environment", "urban-space", "ecology", "migration", "housing", "public-space", "climate-risk"],
  all: concepts.map((concept) => concept.id)
};

const focusCopy = {
  core: "Tổng quan giữ các trục chính: thân thể, nhu cầu, hành động, quan hệ, xã hội hóa, đời sống thường nhật, lý thuyết và phương pháp nghiên cứu.",
  self: "Tập trung vào đời sống bên trong: thân thể, tính dục, bệnh tật, cảm xúc, tri thức, tổn thương, chăm sóc, vòng đời và năng lực sống.",
  relations: "Tập trung vào thân mật, gia đình, cộng đồng, tương tác, mạng quan hệ, vốn xã hội, xung đột và bản sắc nhóm.",
  systems: "Tập trung vào lý thuyết, phương pháp, thể chế, quyền, chính sách, kinh tế, công nghệ, quyền lực, lệch chuẩn và môi trường sống.",
  all: "Hiển thị toàn bộ dữ liệu để kiểm tra bức tranh đầy đủ."
};

const viewCopy = {
  tree: {
    title: "Cây con người trung tâm",
    description: "Cây hiển thị theo đường dẫn tập trung: tổ tiên nằm phía trên, node đang chọn ở giữa, node con nằm phía dưới. Node anh em sẽ được ẩn khi drill-down.",
    status: "Chế độ cây đang sắp xếp khái niệm theo tầng."
  },
  network: {
    title: "Mạng lưới con người - xã hội",
    description: "Network phân bổ node theo vòng quan hệ quanh node đang chọn, không xếp trên-dưới như cây phân cấp.",
    status: "Chế độ mạng lưới đang hiển thị các quan hệ theo bố cục radial."
  },
  timeline: {
    title: "Dòng thời gian đời sống xã hội",
    description: "Timeline chỉ hiển thị khái niệm trong đường dẫn đang xem để người dùng theo dõi từng cụm theo thời gian.",
    status: "Chế độ timeline đang hiển thị diễn tiến theo góc nhìn."
  }
};

const stage = document.querySelector("#visual-stage");
const title = document.querySelector("#view-title");
const description = document.querySelector("#view-description");
const statusText = document.querySelector("#status-text");
const buttons = document.querySelectorAll(".view-button");
const focusButtons = document.querySelectorAll(".focus-chip");
const resetButton = document.querySelector("#reset-button");
const legend = document.querySelector("#legend");
const conceptCount = document.querySelector("#concept-count");
const selectedCard = document.querySelector("#selected-card");
const breadcrumb = document.querySelector("#breadcrumb");
const relationPanel = document.querySelector("#relation-panel");
const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#concept-search");
const searchResults = document.querySelector("#search-results");
const learningPathButtons = document.querySelectorAll("[data-path-target]");

let currentView = "tree";
let currentFocus = "core";
let selectedConceptId = "relationship";
let expandedIds = new Set(["human", "relationship"]);

function conceptById(id) {
  return concepts.find((concept) => concept.id === id);
}

function getChildren(parentId) {
  return concepts.filter((concept) => concept.parent === parentId);
}

function getAncestorPath(id) {
  const path = [];
  let current = conceptById(id);

  while (current) {
    path.unshift(current.id);
    current = current.parent ? conceptById(current.parent) : null;
  }

  return path;
}

function visibleIds() {
  const allowedIds = new Set(focusSets[currentFocus]);
  if (currentView === "network" && currentFocus === "all") {
    return allowedIds;
  }

  const selectedId = allowedIds.has(selectedConceptId) ? selectedConceptId : "human";
  const ids = new Set(getAncestorPath(selectedId).filter((id) => allowedIds.has(id)));

  if (expandedIds.has(selectedId)) {
    getChildren(selectedId).forEach((child) => {
      if (allowedIds.has(child.id)) {
        ids.add(child.id);
      }
    });
  }

  return ids;
}

function visibleConcepts() {
  const ids = visibleIds();
  return concepts.filter((concept) => ids.has(concept.id));
}

function visibleRelationships() {
  const ids = visibleIds();
  return relationships.filter(([from, to]) => ids.has(from) && ids.has(to));
}

function relationshipLabel(from, to) {
  const toConcept = conceptById(to);
  const fromConcept = conceptById(from);

  if (toConcept?.parent === from) return "bao gồm";
  if (fromConcept?.parent === to) return "thuộc về";

  const pairKey = [from, to].sort().join(":");
  const labels = {
    "algorithm:privacy": "gây rủi ro",
    "anger:collective-action": "thúc đẩy",
    "bias:discrimination": "tạo lệch",
    "care-economy:welfare": "được bảo vệ bởi",
    "class:education": "định hình cơ hội",
    "climate-risk:migration": "gây dịch chuyển",
    "collective-action:participation": "biểu hiện",
    "communication:trust": "xây dựng",
    "conflict:governance": "đòi hỏi điều phối",
    "digital-divide:education": "tạo chênh lệch",
    "digital-identity:identity": "tái tạo",
    "disability:rights": "đòi hỏi bảo vệ",
    "education:social-mobility": "mở cơ hội",
    "family:gender": "tái tạo vai trò",
    "freedom:rights": "được bảo đảm bởi",
    "housing:safety": "bảo vệ",
    "labor:dignity": "liên quan phẩm giá",
    "law:morality": "thể chế hóa",
    "mental-health:stress": "ảnh hưởng",
    "poverty:vulnerability": "làm tăng",
    "recognition:identity": "củng cố",
    "social-capital:trust": "tích lũy",
    "surveillance:privacy": "xung đột",
    "urban-space:community": "định hình"
  };

  return labels[pairKey] || "liên hệ";
}

function hasExpandableChildren(id) {
  const allowedIds = new Set(focusSets[currentFocus]);
  return getChildren(id).some((child) => allowedIds.has(child.id));
}

function formatYear(year) {
  if (year < 0) {
    return `${Math.abs(year).toLocaleString("vi-VN")} TCN`;
  }

  return year.toLocaleString("vi-VN");
}

function createNode(concept, className = "") {
  const group = groups[concept.group];
  const hasChildren = hasExpandableChildren(concept.id);
  const isExpanded = expandedIds.has(concept.id);
  const node = document.createElement("article");
  node.className = `concept-node ${className} ${concept.id === "human" ? "is-human" : ""} ${concept.id === selectedConceptId ? "is-selected" : ""} ${hasChildren ? "is-expandable" : ""}`.trim();
  node.style.setProperty("--accent", group.color);
  node.tabIndex = 0;
  if (hasChildren) {
    node.setAttribute("aria-expanded", String(isExpanded));
  }
  node.title = `${concept.label}: ${concept.description}`;
  node.innerHTML = `
    <span class="concept-icon" aria-hidden="true">${concept.icon}</span>
    <span>
      <span class="concept-title">${concept.label}</span>
      <span class="concept-description">${concept.description}</span>
    </span>
    ${hasChildren ? `<span class="expand-indicator" aria-hidden="true">${isExpanded ? "−" : "+"}</span>` : ""}
  `;
  node.addEventListener("click", () => activateConcept(concept.id));
  node.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activateConcept(concept.id);
    }
  });
  return node;
}

function renderLegend() {
  const activeGroups = new Set(visibleConcepts().map((concept) => concept.group));
  legend.innerHTML = Object.entries(groups)
    .filter(([key]) => activeGroups.has(key))
    .map(([, group]) => `
      <div class="legend-item">
        <span class="legend-dot" style="--accent: ${group.color}"></span>
        <span>${group.label}</span>
      </div>
    `)
    .join("");
}

function renderBreadcrumb() {
  const path = getAncestorPath(selectedConceptId);
  breadcrumb.innerHTML = "";

  path.forEach((id) => {
    const concept = conceptById(id);
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = concept.label;
    button.addEventListener("click", () => goToConcept(id, currentFocus));
    breadcrumb.appendChild(button);
  });
}

function conceptQuestions(concept) {
  const groupQuestions = {
    human: ["Trải nghiệm cá nhân này bị điều kiện xã hội nào định hình?", "Khái niệm này liên quan gì đến phẩm giá và năng lực hành động?"],
    relation: ["Quan hệ này tạo hỗ trợ hay tạo ràng buộc?", "Nó thay đổi thế nào giữa gia đình, cộng đồng và môi trường số?"],
    wellbeing: ["Ai được tiếp cận nguồn lực này, ai bị thiếu hụt?", "Thiết chế nào có thể bảo vệ hoặc làm suy yếu điều kiện này?"],
    power: ["Nguồn lực và tiếng nói đang phân bổ không đều ra sao?", "Nhóm nào được lợi, nhóm nào bị đẩy ra bên lề?"],
    institution: ["Quy tắc nào biến khái niệm này thành thực hành xã hội?", "Tính chính danh của thiết chế này đến từ đâu?"],
    culture: ["Ý nghĩa này được học và truyền lại qua đâu?", "Nó củng cố hay thách thức chuẩn mực hiện có?"],
    economy: ["Khái niệm này ảnh hưởng đến sinh kế và vị thế thế nào?", "Lao động nào được nhìn thấy hoặc bị vô hình hóa?"],
    technology: ["Công nghệ này mở rộng hay giới hạn tự do của con người?", "Dữ liệu, thuật toán và quyền riêng tư liên quan ra sao?"],
    environment: ["Không gian sống này tạo cơ hội và rủi ro cho ai?", "Nó liên quan thế nào tới di cư, nhà ở và sức khỏe?"],
    research: ["Cần phương pháp nào để quan sát khái niệm này?", "Người tham gia nghiên cứu cần được bảo vệ ra sao?"],
    theory: ["Lý thuyết này giải thích quyền lực, trật tự hay ý nghĩa thế nào?", "Nó bỏ sót trải nghiệm của nhóm nào?"],
    lifecycle: ["Giai đoạn sống này có vai trò, rủi ro và nguồn lực gì?", "Quan hệ liên thế hệ ảnh hưởng ra sao?"],
    value: ["Giá trị này được công nhận bởi ai?", "Nó xung đột với giá trị hoặc thiết chế nào?"],
    root: ["Các hệ thống xã hội đang xoay quanh con người như thế nào?", "Khái niệm này giúp ta hiểu đời sống chung ra sao?"]
  };

  return groupQuestions[concept.group] || groupQuestions.root;
}

function renderSelectedCard() {
  const concept = conceptById(selectedConceptId) || conceptById("human");
  const group = groups[concept.group];
  selectedCard.style.setProperty("--accent", group.color);
  selectedCard.classList.toggle("is-human-selected", concept.id === "human");
  const parent = concept.parent ? conceptById(concept.parent) : null;
  selectedCard.innerHTML = `
    <span class="selected-card__hint">Đang chọn</span>
    <strong>${concept.icon} ${concept.label}</strong>
    <div class="selected-meta">
      <span>${group.label}</span>
      <span>${formatYear(concept.year)}</span>
      ${parent ? `<span>Thuộc: ${parent.label}</span>` : "<span>Trung tâm</span>"}
    </div>
    <p>${concept.description}</p>
    <ul class="selected-prompts">
      ${conceptQuestions(concept).map((question) => `<li>${question}</li>`).join("")}
    </ul>
  `;
}

function renderRelationPanel() {
  const related = relationships
    .filter(([from, to]) => from === selectedConceptId || to === selectedConceptId)
    .slice(0, 6);

  if (!related.length) {
    relationPanel.innerHTML = "";
    return;
  }

  relationPanel.innerHTML = `
    <span class="relation-panel__title">Kết nối liên quan</span>
    ${related.map(([from, to]) => {
      const otherId = from === selectedConceptId ? to : from;
      const other = conceptById(otherId);
      return `
        <button class="relation-item" type="button" data-related-id="${otherId}">
          <strong>${other.icon} ${other.label}</strong>
          <span>${relationshipLabel(from, to)}</span>
        </button>
      `;
    }).join("")}
  `;

  relationPanel.querySelectorAll("[data-related-id]").forEach((button) => {
    button.addEventListener("click", () => goToConcept(button.dataset.relatedId, "all"));
  });
}

function renderTreeBranch(concept, ids, depth = 0) {
  const branch = document.createElement("section");
  branch.className = `tree-branch depth-${depth}`;
  branch.appendChild(createNode(concept, depth === 0 ? "tree-root" : "branch-heading"));

  const children = getChildren(concept.id).filter((child) => ids.has(child.id));
  if (children.length) {
    const childGrid = document.createElement("div");
    childGrid.className = "tree-children";
    children.forEach((child) => childGrid.appendChild(renderTreeBranch(child, ids, depth + 1)));
    branch.appendChild(childGrid);
  }

  return branch;
}

function renderTree() {
  const ids = visibleIds();
  const view = document.createElement("div");
  view.className = "tree-view fade-in";
  view.appendChild(renderTreeBranch(conceptById("human"), ids));
  stage.replaceChildren(view);
}

function calculateNetworkPositions(ids, links) {
  const layout = new Map();
  const selectedId = ids.has(selectedConceptId) ? selectedConceptId : "human";
  const center = [50, 50];
  const visible = [...ids].filter((id) => id !== selectedId);
  const direct = new Set();

  links.forEach(([from, to]) => {
    if (from === selectedId && ids.has(to)) direct.add(to);
    if (to === selectedId && ids.has(from)) direct.add(from);
  });

  getChildren(selectedId)
    .filter((child) => ids.has(child.id))
    .forEach((child) => direct.add(child.id));

  const ancestors = getAncestorPath(selectedId)
    .filter((id) => id !== selectedId && ids.has(id));
  const directNodes = [...direct].filter((id) => id !== selectedId);
  const secondaryNodes = visible.filter((id) => !direct.has(id) && !ancestors.includes(id));

  layout.set(selectedId, center);

  placeRing(layout, ancestors, 14, 11, -Math.PI / 2);
  placeRing(layout, directNodes, 28, 22, -Math.PI / 2);

  const secondaryRings = chunkByCapacity(secondaryNodes, [18, 26, 34, 42, 50]);
  secondaryRings.forEach((nodes, index) => {
    const radius = 34 + index * 8;
    placeRing(layout, nodes, Math.min(radius, 47), Math.min(radius * 0.76, 39), Math.PI / 2 + index * 0.38);
  });

  return layout;
}

function chunkByCapacity(items, capacities) {
  const chunks = [];
  let cursor = 0;

  capacities.forEach((capacity) => {
    if (cursor >= items.length) return;
    chunks.push(items.slice(cursor, cursor + capacity));
    cursor += capacity;
  });

  if (cursor < items.length) {
    chunks.push(items.slice(cursor));
  }

  return chunks;
}

function placeRing(layout, nodes, radiusX, radiusY, start) {
  nodes.forEach((id, index) => {
    const angle = start + (Math.PI * 2 * index) / Math.max(nodes.length, 1);
    layout.set(id, [
      50 + Math.cos(angle) * radiusX,
      50 + Math.sin(angle) * radiusY
    ]);
  });
}

function renderNetwork() {
  const ids = visibleIds();
  const links = visibleRelationships();
  const layout = calculateNetworkPositions(ids, links);
  const view = document.createElement("div");
  view.className = "network-view fade-in";

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("network-lines");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");

  links.forEach(([from, to]) => {
    const fromPosition = layout.get(from);
    const toPosition = layout.get(to);
    if (!fromPosition || !toPosition) return;

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.dataset.from = from;
    line.dataset.to = to;
    line.dataset.label = relationshipLabel(from, to);
    line.setAttribute("x1", fromPosition[0]);
    line.setAttribute("y1", fromPosition[1]);
    line.setAttribute("x2", toPosition[0]);
    line.setAttribute("y2", toPosition[1]);
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${conceptById(from).label} - ${relationshipLabel(from, to)} - ${conceptById(to).label}`;
    line.appendChild(title);
    svg.appendChild(line);
  });

  view.appendChild(svg);

  concepts
    .filter((concept) => ids.has(concept.id))
    .forEach((concept) => {
      const [x, y] = layout.get(concept.id);
      const node = createNode(concept, `network-node ${concept.id === "human" ? "is-hub" : ""}`);
      node.style.left = `${x}%`;
      node.style.top = `${y}%`;
      node.addEventListener("mouseenter", () => highlightConnections(concept.id, view));
      node.addEventListener("mouseleave", () => clearConnectionHighlight(view));
      view.appendChild(node);
    });

  stage.replaceChildren(view);
}

function highlightConnections(id, view) {
  view.querySelectorAll(".network-lines line").forEach((line) => {
    if (line.dataset.from === id || line.dataset.to === id) {
      line.style.stroke = "#20232a";
      line.style.strokeWidth = "3";
    } else {
      line.style.stroke = "rgba(32, 35, 42, 0.06)";
    }
  });
}

function clearConnectionHighlight(view) {
  view.querySelectorAll(".network-lines line").forEach((line) => {
    line.style.stroke = "rgba(226, 85, 85, 0.2)";
    line.style.strokeWidth = "2";
  });
}

function renderTimeline() {
  const view = document.createElement("div");
  view.className = "timeline-view fade-in";

  visibleConcepts()
    .sort((a, b) => a.year - b.year)
    .forEach((concept) => {
      const item = document.createElement("article");
      item.className = "timeline-item";
      item.innerHTML = `<span class="timeline-year">${formatYear(concept.year)}</span>`;
      item.appendChild(createNode(concept, "timeline-card"));
      view.appendChild(item);
    });

  if (!view.children.length) {
    view.innerHTML = `<div class="empty-state">Không có khái niệm trong góc nhìn này.</div>`;
  }

  stage.replaceChildren(view);
}

function renderCurrentView() {
  if (!visibleIds().has(selectedConceptId)) {
    selectedConceptId = "human";
  }

  const copy = viewCopy[currentView];
  const shownCount = visibleConcepts().length;
  const shownLinks = visibleRelationships().length;

  title.textContent = copy.title;
  description.textContent = `${copy.description} ${focusCopy[currentFocus]}`;
  statusText.textContent = `${copy.status} Đang hiển thị ${shownCount}/${concepts.length} khái niệm và ${shownLinks}/${relationships.length} kết nối.`;

  renderSelectedCard();
  renderBreadcrumb();
  renderRelationPanel();
  renderLegend();

  if (currentView === "tree") renderTree();
  if (currentView === "network") renderNetwork();
  if (currentView === "timeline") renderTimeline();
}

function setView(viewName) {
  currentView = viewName;
  buttons.forEach((button) => {
    const isActive = button.dataset.view === viewName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
  renderCurrentView();
}

function setFocus(focusName) {
  currentFocus = focusName;
  focusButtons.forEach((button) => {
    const isActive = button.dataset.focus === focusName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
  renderCurrentView();
}

function focusForConcept(id) {
  if (focusSets[currentFocus]?.includes(id)) return currentFocus;
  return Object.entries(focusSets).find(([key, ids]) => key !== "all" && ids.includes(id))?.[0] || "all";
}

function expandPathTo(id) {
  getAncestorPath(id).forEach((pathId) => expandedIds.add(pathId));
}

function goToConcept(id, focusName = focusForConcept(id)) {
  selectedConceptId = id;
  currentFocus = focusName;
  expandPathTo(id);
  setFocus(currentFocus);
}

function activateConcept(id) {
  selectedConceptId = id;

  if (hasExpandableChildren(id)) {
    if (expandedIds.has(id)) {
      expandedIds.delete(id);
    } else {
      expandedIds.add(id);
    }
  }

  renderCurrentView();
}

function matchingConcepts(query) {
  const normalized = query.trim().toLocaleLowerCase("vi-VN");
  if (!normalized) return [];

  return concepts
    .filter((concept) => {
      return concept.label.toLocaleLowerCase("vi-VN").includes(normalized)
        || concept.description.toLocaleLowerCase("vi-VN").includes(normalized)
        || concept.id.toLocaleLowerCase("vi-VN").includes(normalized);
    })
    .slice(0, 8);
}

function renderSearchResults(query) {
  const matches = matchingConcepts(query);
  searchResults.classList.toggle("is-open", matches.length > 0);
  searchResults.innerHTML = matches.map((concept) => `
    <button class="search-result" type="button" data-concept-id="${concept.id}">
      <span>${concept.icon} ${concept.label}</span>
      <small>${groups[concept.group].label}</small>
    </button>
  `).join("");

  searchResults.querySelectorAll("[data-concept-id]").forEach((button) => {
    button.addEventListener("click", () => {
      searchInput.value = conceptById(button.dataset.conceptId).label;
      searchResults.classList.remove("is-open");
      goToConcept(button.dataset.conceptId, "all");
    });
  });
}

buttons.forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

focusButtons.forEach((button) => {
  button.addEventListener("click", () => setFocus(button.dataset.focus));
});

learningPathButtons.forEach((button) => {
  button.addEventListener("click", () => goToConcept(button.dataset.pathTarget, focusForConcept(button.dataset.pathTarget)));
});

searchInput.addEventListener("input", () => renderSearchResults(searchInput.value));

searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    searchResults.classList.remove("is-open");
  }
});

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const match = matchingConcepts(searchInput.value)[0];
  if (match) {
    searchInput.value = match.label;
    searchResults.classList.remove("is-open");
    goToConcept(match.id, "all");
  }
});

document.addEventListener("click", (event) => {
  if (!searchForm.contains(event.target)) {
    searchResults.classList.remove("is-open");
  }
});

resetButton.addEventListener("click", () => {
  selectedConceptId = "human";
  currentFocus = "core";
  expandedIds = new Set(["human"]);
  setFocus(currentFocus);
});

if (conceptCount) {
  conceptCount.textContent = concepts.length;
}

setView(currentView);
