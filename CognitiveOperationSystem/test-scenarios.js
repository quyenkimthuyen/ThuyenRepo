/**
 * Test Scenarios — Kịch bản mẫu để tham khảo và mô phỏng app
 *
 * Thêm kịch bản mới: push object vào TEST_SCENARIOS theo schema bên dưới.
 *
 * @typedef {Object} TestScenario
 * @property {string} id — slug duy nhất
 * @property {string} title — tiêu đề ngắn
 * @property {string} category — family | work | finance | learning | health | self
 * @property {string[]} tags
 * @property {string} summary — mô tả 1–2 câu
 * @property {Object} persona — nhân vật trong kịch bản
 * @property {string} persona.name
 * @property {number} persona.age
 * @property {string} persona.role
 * @property {string} persona.context — bối cảnh đời sống
 * @property {string} situation — tình huống kích hoạt suy nghĩ
 * @property {string} initialThought — câu mở đầu (điền vào Home)
 * @property {Array<{step: string, content: string, note?: string}>} dialogue — lượt trả lời user theo EEIBVIA
 * @property {Object} expectedOutcomes — kết quả kỳ vọng sau mô phỏng
 * @property {string[]} learningPoints — điểm người dùng nên chú ý
 */

const TEST_SCENARIOS = [
  {
    id: 'parent-education-anxiety',
    title: 'Cha lo lắng con không chịu học',
    category: 'family',
    tags: ['gia đình', 'giáo dục', 'lo lắng', 'công việc'],
    summary:
      'Một người cha làm việc nhiều giờ, thấy con chơi game thay vì học — lo cho tương lai con và phản ứng bằng la mắng, ép học.',

    persona: {
      name: 'Anh Minh',
      age: 42,
      role: 'Kỹ sư phần mềm, cha của bé Nam (12 tuổi, lớp 6)',
      context:
        'Sống tại TP.HCM, vợ làm kế toán. Minh thường về nhà sau 21h. Con thích chơi game mobile, điểm Toán gần đây giảm. Đã thử cấm wifi, la mắng — con càng trốn tránh.',
    },

    situation:
      'Tối thứ Tư, Minh về nhà lúc 21h30 sau ngày làm 14 tiếng. Thấy con vẫn cầm điện thoại chơi game trong phòng, bài tập Toán chưa làm. Vợ nhắc nhẹ nhưng Minh bùng nổ, quát con và tự hỏi mình có đang làm cha tồi không.',

    initialThought:
      'Con tôi không chịu học, tôi lo lắng về tương lai của con. Mỗi tối tôi làm việc 14 giờ rồi về nhà thấy con còn chơi game thì rất tức.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy lo lắng, căng thẳng và tức giận. Tim đập nhanh mỗi khi thấy con cầm điện thoại. Cũng có chút tội lỗi vì đã quát con to tiếng.',
        note: 'Tách cảm xúc khỏi sự kiện — không nhầm “tức” với “con sai”.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi lo con sẽ thất bại trong cuộc sống, không vào được trường tốt, sau này không có việc làm. Tôi hiểu là nếu con không học bây giờ thì cả gia đình sẽ hối hận.',
        note: 'Cách hiểu thường chứa dự đoán tương lai — dễ nghĩ đến chuyện tồi tệ nhất.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin rằng học giỏi mới thành công. Con cái phải nghe lời cha mẹ. Làm việc chăm chỉ sẽ thành công — tôi đang làm vậy vì gia đình.',
        note: 'Niềm tin ẩn dẫn dắt phản ứng: ép học, làm nhiều giờ.',
      },
      {
        step: 'Value',
        content:
          'Gia đình là ưu tiên số một với tôi. Giáo dục con đúng cách rất quan trọng. Tôi muốn con có tương lai tốt hơn đời tôi.',
        note: 'Giá trị thật sự — so sánh với hành động ở bước sau.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người cha, có trách nhiệm bảo vệ và hướng dẫn con. Tôi không muốn được coi là cha mẹ thất bại. Tôi thấy mình là người hy sinh vì gia đình.',
        note: 'Vai trò “người cha hy sinh” có thể khiến khó nhận ra mâu thuẫn.',
      },
      {
        step: 'Action',
        content:
          'Tôi thường la mắng con, bắt con học mỗi tối. Tôi làm việc 14 giờ mỗi ngày để kiếm tiền cho con học thêm. Tôi chưa dành thời gian ngồi cạnh con học.',
        note: 'Hành động thực tế — đối chiếu với giá trị “gia đình ưu tiên”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'family',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Học giỏi mới thành công',
        'Niềm tin: Con cái phải nghe lời',
        'Giá trị: Gia đình',
        'Giá trị: Giáo dục',
        'Hành động: La mắng / kỷ luật con',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: [
        'Gia đình ưu tiên vs làm việc 14 giờ/ngày',
        'Con phải nghe lời vs giá trị tự do (nếu được ghi nhận)',
      ],
      biases: ['Catastrophizing', 'Should Statements'],
    },

    learningPoints: [
      'Sau mô phỏng, mở Bản đồ suy nghĩ → nhánh Gia đình để xem ghi nhận Niềm tin và Hành động.',
      'Vào Góc khám phá — tìm mục Mâu thuẫn trong suy nghĩ (gia đình vs 14 giờ làm việc).',
      'Xem Dòng thời gian — ghi nhận chuyển từ Mới ghi nhận → Lặp lại nhiều lần khi lặp phiên.',
      'Thử chạy lại kịch bản lần 2 (không reset) để thấy ghi nhận lên trạng thái Đã vững chắc.',
      'So sánh hội thoại mẫu với cách bạn tự trả lời — càng trung thực, bản đồ suy nghĩ càng phản ánh đúng.',
    ],
  },

  {
    id: 'work-burnout-deadline',
    title: 'Kiệt sức vì deadline dự án',
    category: 'work',
    tags: ['công việc', 'burnout', 'cân bằng', 'sức khỏe'],
    summary:
      'Trưởng nhóm IT bị ép deadline gấp, làm cuối tuần liên tục — mệt kiệt sức nhưng vẫn tin rằng phải cố gắng mới thành công.',

    persona: {
      name: 'Chị Lan',
      age: 34,
      role: 'Trưởng nhóm phát triển phần mềm tại startup công nghệ',
      context:
        'Làm việc 4 năm, vừa được thăng chức. Team 6 người, dự án lớn giao cho khách hàng doanh nghiệp. Sếp yêu cầu hoàn thành sớm 3 tuần. Lan thường trả lời email lúc 1–2 giờ sáng. Bạn bè nhắc nghỉ ngơi nhưng cô sợ bị đánh giá kém.',
    },

    situation:
      'Chủ nhật tối, Lan vẫn ngồi laptop sửa bug sau khi team nghỉ. Ngực đau nhẹ, đầu nhức, chồng nhắn “Em còn sống không?” — cô bật khóc vì vừa mệt vừa tội lỗi. Sáng mai họp với sếp, cô không biết nên xin nghỉ hay cam kết tiếp tục overtime.',

    initialThought:
      'Dự án sắp trễ deadline, sếp đang rất áp lực. Tôi làm việc cuối tuần không nghỉ nhưng vẫn thấy mình chưa đủ cố gắng.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy mệt mỏi, căng thẳng và áp lực. Có lúc tuyệt vọng vì làm mãi không xong. Cũng xấu hổ khi bỏ bê chồng cả tuần.',
        note: 'Burnout thường kèm mệt mỏi + tội lỗi — không chỉ “stress công việc”.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu trễ deadline thì cả team thất bại, sếp sẽ mất niềm tin, tôi có thể bị sa thải. Mọi người sẽ đánh giá tôi là trưởng nhóm kém cỏi.',
        note: 'Cách hiểu “tất cả hoặc không” — dễ nghĩ đến chuyện tồi tệ nhất.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin làm việc chăm chỉ sẽ thành công. Công việc quan trọng hơn nghỉ ngơi. Tôi không được phép nghỉ khi dự án chưa xong — nghỉ ngơi là lười biếng.',
        note: 'Niềm tin “phải hy sinh” thường dẫn tới overwork.',
      },
      {
        step: 'Value',
        content:
          'Tôi trân trọng sự cân bằng giữa công việc và cuộc sống. Gia đình là ưu tiên số một — chồng tôi cần có tôi bên cạnh. Sức khỏe quan trọng với tôi.',
        note: 'Giá trị nói một đằng — hành động ở bước cuối sẽ cho thấy đằng khác.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc, trưởng nhóm phải gánh team. Tôi không muốn được coi là người thất bại. Tôi thấy mình là người kiểm soát — mọi thứ phải trong tay tôi.',
        note: 'Vai trò “người gánh team” khiến khó nhờ hỗ trợ hoặc nói không.',
      },
      {
        step: 'Action',
        content:
          'Tôi làm việc 14 giờ mỗi ngày, làm việc cuối tuần không nghỉ, trả lời tin nhắn lúc làm đêm. Tôi chưa dám nói với sếp là cần thêm thời gian.',
        note: 'Đối chiếu với giá trị cân bằng và sức khỏe.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'work',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Làm việc chăm chỉ sẽ thành công',
        'Niềm tin: Công việc quan trọng hơn nghỉ ngơi',
        'Giá trị: Cân bằng',
        'Giá trị: Sức khỏe',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: [
        'Gia đình ưu tiên vs làm 14 giờ / overtime',
        'Cân bằng work-life vs không nghỉ cuối tuần',
      ],
      biases: ['Catastrophizing', 'Should Statements', 'Overgeneralization'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Công việc — xem ghi nhận Niềm tin và Hành động tập trung thế nào.',
      'Góc khám phá: tìm mâu thuẫn giữa “cân bằng” và hành động làm thêm giờ.',
      'So sánh vai trò “người kiểm soát” với hành động im lặng với sếp.',
      'Thử sửa 1 câu trong hội thoại (ví dụ thêm “nhờ team hỗ trợ”) và chạy lại — xem ghi nhận Hành động thay đổi ra sao.',
    ],
  },

  {
    id: 'finance-debt-house',
    title: 'Nợ ngân hàng và áp lực mua nhà',
    category: 'finance',
    tags: ['tài chính', 'nợ', 'gia đình', 'tiền bạc'],
    summary:
      'Vợ chồng trẻ đang trả nợ vay, vợ muốn mua căn hộ trước khi giá tăng — chồng lo không đủ tiền nhưng im lặng, càng làm nhiều giờ để kiếm thêm.',

    persona: {
      name: 'Anh Tuấn',
      age: 31,
      role: 'Nhân viên kinh doanh B2B, chồng của chị Hương (29 tuổi, giáo viên)',
      context:
        'Cưới 3 năm, thuê nhà tại Hà Nội. Đang trả khoản vay tiêu dùng 80 triệu còn 45 triệu. Hương muốn đặt cọc căn hộ chung cư vì sợ giá tăng. Tuấn thấy thu nhập không ổn định — tháng nào cũng phải lo chi tiêu. Cha mẹ vợ hay so sánh với con nhà người khác đã mua nhà.',
    },

    situation:
      'Tối thứ Sáu, Hương đưa bản kế hoạch tài chính mua nhà. Tuấn nhìn con số nợ và lãi suất, tim đập nhanh. Anh nói “để anh lo” rồi im lặng cả buổi. Trên giường, Hương hỏi “Anh có muốn không?” — Tuấn lảng tránh, mở điện thoại xem email công việc.',

    initialThought:
      'Chúng tôi còn nợ ngân hàng mà vợ muốn mua nhà ngay. Tôi lo lắng về tài chính, sợ không đủ tiền trả nợ nhưng không dám nói thẳng với vợ.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy lo lắng, căng thẳng và bất an. Có chút tội lỗi vì im lặng với vợ, không dám nói thẳng nỗi sợ về nợ.',
        note: 'Cảm xúc tài chính thường lẫn xấu hổ — khó tách riêng khỏi sự kiện.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi lo nếu không mua nhà bây giờ thì giá sẽ tăng, cả gia đình sẽ khó khăn tài chính. Tôi hiểu là không có tiền thì không sống được.',
        note: 'Thảm họa hóa tương lai tài chính — “không sống được” có thể là phóng đại.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin tiền mang lại hạnh phúc. Không có tiền không sống được. Người chồng phải lo tài chính cho gia đình.',
        note: 'Niềm tin về tiền thường ảnh hưởng mọi quyết định lớn.',
      },
      {
        step: 'Value',
        content:
          'Gia đình và yêu thương là quan trọng nhất với tôi. Tôi coi trọng sự trung thực giữa vợ chồng.',
        note: 'Giá trị gia đình + trung thực — đối chiếu với im lặng ở bước Action.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người trưởng thành, người chồng phải bảo vệ gia đình. Tôi thấy mình phải gánh trách nhiệm tài chính một mình.',
        note: 'Vai trò “người gánh vác” dễ dẫn tới tránh né thay vì hợp tác.',
      },
      {
        step: 'Action',
        content:
          'Tôi im lặng, tránh né cuộc nói chuyện với vợ. Tôi làm việc 14 giờ mỗi ngày để kiếm thêm tiền trả nợ.',
        note: 'Im lặng mâu thuẫn với trung thực; overtime mâu thuẫn với dành thời gian cho gia đình.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'finance',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Tiền mang lại hạnh phúc',
        'Niềm tin: Không có tiền không sống được',
        'Giá trị: Gia đình',
        'Giá trị: Yêu thương',
        'Hành động: Tránh né / im lặng',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: [
        'Tiền mang lại hạnh phúc vs giá trị gia đình / yêu thương',
        'Gia đình ưu tiên vs làm 14 giờ để kiếm tiền',
        'Giá trị gia đình vs thiếu thời gian cho gia đình',
      ],
      biases: ['Catastrophizing', 'Mind Reading', 'Personalization'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Tài chính và Gia đình — ghi nhận có thể xuất hiện ở cả hai nhánh.',
      'Góc khám phá: mâu thuẫn niềm tin về tiền vs giá trị quan hệ.',
      'Chú ý hành động “im lặng” khi giá trị là trung thực — điểm can thiệp thực tế.',
      'Thử chạy mô phỏng rồi đọc Dòng thời gian — xem việc xảy ra về tài chính được ghi nhận thế nào.',
    ],
  },
];

if (typeof window !== 'undefined') {
  window.TEST_SCENARIOS = TEST_SCENARIOS;
}
