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

  {
    id: 'learning-exam-university',
    title: 'Học sinh lo sợ thi đại học',
    category: 'learning',
    tags: ['thi cử', 'đại học', 'áp lực', 'gia đình'],
    summary:
      'Học sinh lớp 12 điểm khá nhưng luôn sợ trượt đại học — ôn thi đến khuya, so sánh với bạn và tin rằng một lần thi quyết định cả đời.',

    persona: {
      name: 'Bé Linh',
      age: 17,
      role: 'Học sinh lớp 12 chuyên Toán tại trường THPT ở Đà Nẵng',
      context:
        'Gia đình kỳ vọng vào đại học top. Mẹ là giáo viên, hay nhắc điểm số. Linh điểm trung bình 8.2 nhưng thi thử dao động. Bạn thân đã có suất học bổng, Linh lên mạng xem điểm chuẩn mỗi tối.',
    },

    situation:
      'Đêm trước kỳ thi thử lần ba, Linh ôn đến 2 giờ sáng. Làm đề Toán sai câu dễ, nước mắt rơi xuống vở. Mẹ gõ cửa hỏi “Con còn học không?” — Linh gật đầu nhưng trong lòng nghĩ mình kém cỏi và sợ làm gia đình thất vọng.',

    initialThought:
      'Kỳ thi đại học sắp tới, tôi sợ trượt và làm gia đình thất vọng. Dù học nhiều nhưng vẫn thấy mình không đủ giỏi.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy lo lắng, căng thẳng và sợ hãi. Tim đập nhanh mỗi khi nghĩ đến phòng thi. Cũng buồn và xấu hổ khi làm sai câu dễ.',
        note: 'Lo thi thường lẫn xấu hổ — không đồng nghĩa “kém thật”.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu trượt đại học thì cả cuộc đời tôi thất bại, ba mẹ sẽ thất vọng, bạn bè sẽ coi thường. Một kỳ thi quyết định tất cả.',
        note: 'Cách hiểu “một lần thi = cả đời” — dễ là thảm họa hóa.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin học giỏi mới thành công. Phải vào trường danh tiếng mới có giá trị. Nếu không đạt điểm cao thì cố gắng vô ích.',
        note: 'Niềm tin về thành tích thường tạo áp lực “phải hoàn hảo”.',
      },
      {
        step: 'Value',
        content:
          'Gia đình rất quan trọng với tôi. Tôi coi trọng sự phát triển và học hỏi. Sức khỏe cũng quan trọng — nhưng tôi hay bỏ qua khi thi cử.',
        note: 'Giá trị sức khỏe vs hành động thức khuya — điểm mâu thuẫn tiềm ẩn.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là học sinh giỏi, con ngoan của gia đình. Tôi không muốn được coi là kẻ thất bại. Tôi thấy mình phải chứng minh bản thân qua điểm số.',
        note: 'Vai trò “học sinh giỏi” khiến khó chấp nhận sai lầm.',
      },
      {
        step: 'Action',
        content:
          'Tôi ôn thi đến khuya mỗi ngày, so sánh điểm với bạn trên mạng xã hội. Tôi chưa dám nói với mẹ là mình mệt và cần nghỉ ngơi.',
        note: 'So sánh + thiếu ngủ — đối chiếu với giá trị sức khỏe.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'learning',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Học giỏi mới thành công',
        'Giá trị: Gia đình',
        'Giá trị: Phát triển',
        'Hành động: So sánh với người khác',
        'Hành động: Tránh né / im lặng',
      ],
      contradictions: ['Coi trọng sức khỏe vs ôn thi đến khuya / stress'],
      biases: ['Catastrophizing', 'Overgeneralization', 'Should Statements'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Học tập — xem niềm tin về thành tích tập trung thế nào.',
      'Góc khám phá: gợi ý suy ngẫm về áp lực “phải/nên” và kịch bản ngoài thi tồi nhất.',
      'Thử sửa bước Hành động (ví dụ “nhờ cô giáo tư vấn”) và chạy lại — so sánh ghi nhận.',
    ],
  },

  {
    id: 'health-insomnia-burnout',
    title: 'Mất ngủ vì căng thẳng kéo dài',
    category: 'health',
    tags: ['mất ngủ', 'stress', 'sức khỏe', 'công việc'],
    summary:
      'Nhân viên văn phòng mất ngủ nhiều tuần — biết cần nghỉ ngơi nhưng vẫn làm đêm, uống cà phê nhiều và tránh đi khám.',

    persona: {
      name: 'Chị Mai',
      age: 38,
      role: 'Chuyên viên nhân sự tại công ty logistics',
      context:
        'Làm việc 9 năm, vừa trải qua đợt sa thải nhân sự. Mai phải xử lý hồ sơ và họp liên tục. Ngủ trung bình 4–5 tiếng/đêm trong 3 tuần. Chồng lo nhưng Mai nói “ổn thôi”.',
    },

    situation:
      '3 giờ sáng, Mai vẫn trằn trọc. Sáng mai có họp với ban giám đốc. Cô mở điện thoại đọc email, tim đập nhanh, đầu nhức. Nghĩ đến việc xin nghỉ nửa ngày nhưng sợ sếp đánh giá kém — cô lên kế hoạch uống thêm cà phê.',

    initialThought:
      'Tôi mất ngủ nhiều tuần rồi, mệt và căng thẳng. Biết sức khỏe quan trọng nhưng vẫn cố làm việc đêm và không dám nghỉ.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy mệt mỏi, căng thẳng và bồn chồn. Lo lắng mỗi khi trời tối vì sợ lại không ngủ được. Có chút tuyệt vọng.',
        note: 'Mất ngủ kéo dài thường kèm lo âu về chính việc ngủ.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu nghỉ hoặc yếu đi thì sếp sẽ thay thế tôi. Không ngủ được chứng tỏ tôi không đủ mạnh mẽ cho công việc này.',
        note: 'Gắn sức khỏe với “đủ mạnh” — dễ tự trách.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin sức khỏe có thể hy sinh vì công việc. Người trưởng thành phải gánh được áp lực. Đi khám là làm phiền người khác trừ khi bệnh nặng.',
        note: 'Niềm tin “hy sinh sức khỏe” thường trì hoãn chăm sóc bản thân.',
      },
      {
        step: 'Value',
        content:
          'Sức khỏe rất quan trọng với tôi. Gia đình là ưu tiên — chồng tôi cần có tôi khỏe mạnh. Tôi cũng coi trọng trách nhiệm với công việc.',
        note: 'Giá trị sức khỏe vs hành động làm đêm — mâu thuẫn rõ.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc đáng tin cậy, không muốn được coi là yếu đuối. Tôi thấy mình phải tự gánh, không nên than vãn.',
        note: 'Vai trò “mạnh mẽ” có thể cản trở nhờ giúp đỡ.',
      },
      {
        step: 'Action',
        content:
          'Tôi làm việc đến khuya, uống nhiều cà phê, không ngủ đủ giấc. Tôi tránh né cuộc nói chuyện với chồng và chưa đặt lịch đi khám.',
        note: 'Đối chiếu với giá trị sức khỏe và gia đình.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'health',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Sức khỏe có thể hy sinh vì công việc',
        'Giá trị: Sức khỏe',
        'Giá trị: Gia đình',
        'Hành động: Làm việc nhiều giờ',
        'Hành động: Tránh né / im lặng',
      ],
      contradictions: ['Coi trọng sức khỏe vs làm đêm / thiếu ngủ / stress'],
      biases: ['Should Statements', 'Personalization', 'Catastrophizing'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Sức khỏe — xem niềm tin “hy sinh” và hành động thực tế.',
      'Góc khám phá: mâu thuẫn sức khỏe–nhịp sống và gợi ý suy ngẫm tiếp.',
      'Chạy lại lần 2 (không reset) sau khi sửa bước Hành động — xem trạng thái ghi nhận thay đổi.',
    ],
  },

  {
    id: 'self-imposter-work',
    title: 'Cảm giác mình là kẻ imposter',
    category: 'self',
    tags: ['tự tin', 'công việc', 'so sánh', 'bản thân'],
    summary:
      'Nhân viên mới được thăng chức nhưng tin rằng mình không xứng đáng — làm việc quá sức để che giấu và sợ bị “phát hiện”.',

    persona: {
      name: 'Anh Đức',
      age: 29,
      role: 'Product designer vừa được thăng lên Senior tại công ty fintech',
      context:
        '3 năm kinh nghiệm, được sếp khen nhưng Đức nghĩ là may mắn. Đồng nghiệp nhiều năm hơn. Đức hay làm thêm giờ để chứng minh, không dám phát biểu trong họp vì sợ nói sai.',
    },

    situation:
      'Trong họp review thiết kế, sếp hỏi ý kiến Đức trước cả team. Đức nói được vài câu rồi im lặng, tay run nhẹ. Chiều đó anh nhận tin thăng chức — vui nhưng lập tức nghĩ “họ sẽ sớm phát hiện mình không đủ giỏi”.',

    initialThought:
      'Tôi vừa được thăng chức nhưng sợ mọi người sớm phát hiện ra tôi không đủ giỏi. Tôi cảm thấy mình là kẻ giả mạo trong team.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy lo lắng, căng thẳng và xấu hổ. Vui một chút khi được thăng chức nhưng sợ hãi chiếm nhiều hơn. Tim đập nhanh trước mỗi cuộc họp.',
        note: 'Imposter thường kèm lo + xấu hổ dù có thành tích.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là thăng chức chỉ là tình cờ, sếp chưa kịp nhìn ra lỗi của tôi. Đồng nghiệp chắc đang nghĩ tôi không xứng đáng.',
        note: 'Đoán ý người khác mà chưa hỏi — mind reading.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin tôi không xứng đáng với vị trí này. Phải hoàn hảo mới được công nhận. Nếu mắc sai lầm thì mọi thứ sẽ sụp đổ.',
        note: 'Niềm tin “phải hoàn hảo” nuôi imposter syndrome.',
      },
      {
        step: 'Value',
        content:
          'Tôi coi trọng sự trung thực và phát triển bản thân. Trân trọng đóng góp có chất lượng cho team. Tôi muốn được tin tưởng thật sự, không phải vì may mắn.',
        note: 'Giá trị trung thực vs che giấu nỗi sợ — điểm khám phá.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc, muốn là designer giỏi. Tôi sợ được coi là kẻ thất bại hoặc kẻ đang giả vờ. Tôi thấy mình phải chứng minh bản thân mỗi ngày.',
        note: 'Vai trò “phải chứng minh” dẫn tới overwork.',
      },
      {
        step: 'Action',
        content:
          'Tôi làm việc nhiều giờ để che lấp nỗi sợ. Tôi im lặng trong họp, tránh né phát biểu. Tôi chưa dám hỏi mentor hoặc sếp về kỳ vọng thực tế.',
        note: 'Im lặng mâu thuẫn trung thực; overtime mâu thuẫn cân bằng.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'self',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Tôi không xứng đáng',
        'Niềm tin: Phải hoàn hảo mới được yêu',
        'Giá trị: Trung thực',
        'Hành động: Làm việc nhiều giờ',
        'Hành động: Tránh né / im lặng',
      ],
      contradictions: [],
      biases: ['Mind Reading', 'Should Statements', 'Catastrophizing'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Bản thân và Công việc.',
      'Góc khám phá: thiên kiến “đoán ý người khác” và gợi ý hỏi trực tiếp thay vì đoán.',
      'Sửa bước Hành động (nhờ mentor tư vấn) và mô phỏng lại.',
    ],
  },

  {
    id: 'family-eldercare-guilt',
    title: 'Lo chăm sóc cha mẹ già',
    category: 'family',
    tags: ['cha mẹ già', 'tội lỗi', 'gia đình', 'công việc'],
    summary:
      'Con trai trung niên muốn chăm cha bệnh nhưng bận công việc xa — tội lỗi, tranh cãi với chị về tiền và thời gian chăm sóc.',

    persona: {
      name: 'Anh Hùng',
      age: 45,
      role: 'Quản lý chi nhánh ngân hàng tại TP.HCM, con trai út',
      context:
        'Cha 78 tuổi sống với chị gái ở quê (Bình Định). Cha đột quỵ nhẹ, cần người theo dõi. Hùng về quê 2 tuần/lần. Chị gái than vất vả, yêu cầu Hùng đóng góp thêm tiền hoặc đưa cha lên thành phố.',
    },

    situation:
      'Chị gọi video, khóc vì mệt chăm cha một mình. Hùng đang trong cuộc họp nhưng bật loa — đồng nghiệp nhìn. Anh cảm thấy tội lỗi, tranh luận với chị qua điện thoại, rồi hứa “anh lo” nhưng không chắc làm được gì cụ thể.',

    initialThought:
      'Cha tôi ốm mà tôi làm việc xa, không ở bên cạnh được nhiều. Tôi cảm thấy tội lỗi và lo lắng về sức khỏe cha, nhưng cũng bực vì chị chỉ trích tôi.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy tội lỗi, lo lắng và bực bội. Buồn khi nghĩ đến cha ốm. Căng thẳng vì phải cân bằng công việc và gia đình.',
        note: 'Tội lỗi + bực bội có thể cùng tồn tại — cả hai đều đáng ghi nhận.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu không về quê ngay thì cha sẽ xấu đi và chị sẽ ghét tôi. Đồng nghiệp có lẽ nghĩ tôi không chuyên nghiệp khi bật loa cuộc gọi gia đình.',
        note: 'Đoán phản ứng người khác + thảm họa hóa sức khỏe cha.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin con trai phải lo cha mẹ hoàn toàn. Người con ở xa là kẻ ích kỷ. Tôi phải gánh trách nhiệm một mình mới là đúng.',
        note: 'Niềm tin “phải gánh một mình” dễ dẫn tới kiệt sức.',
      },
      {
        step: 'Value',
        content:
          'Gia đình là ưu tiên số một. Tôi coi trọng hiếu thảo và yêu thương. Công việc ổn định cũng quan trọng để có tiền chăm cha.',
        note: 'Hai giá trị đều hợp lệ — cần hành động cân bằng, không phải chọn một.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người con trai, người trưởng thành phải bảo vệ cha. Tôi không muốn được coi là con bất hiếu. Tôi cũng là người quản lý phải có mặt tại công ty.',
        note: 'Hai vai trò cùng lúc — xung đột vai trò là bình thường.',
      },
      {
        step: 'Action',
        content:
          'Tôi hứa chị “anh lo” nhưng chưa có kế hoạch cụ thể. Tôi làm việc nhiều giờ, ít gọi điện hỏi thăm cha. Tôi tránh né tranh luận sâu với chị về chia việc chăm sóc.',
        note: 'Hứa hẹn mơ hồ + tránh né — đối chiếu giá trị hiếu thảo.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'family',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Con trai phải lo cha mẹ',
        'Giá trị: Gia đình',
        'Giá trị: Yêu thương',
        'Hành động: Tránh né / im lặng',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: ['Gia đình ưu tiên vs làm nhiều giờ / ít thời gian cho cha'],
      biases: ['Mind Reading', 'Should Statements', 'Personalization'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Gia đình — ghi nhận tội lỗi và niềm tin về trách nhiệm.',
      'Góc khám phá: mâu thuẫn thời gian cho gia đình vs công việc.',
      'Thử sửa hội thoại — thêm bước nhỏ cụ thể (gọi bác sĩ, chia lịch với chị) và chạy lại.',
    ],
  },

  {
    id: 'work-conflict-colleague',
    title: 'Xung đột với đồng nghiệp trong team',
    category: 'work',
    tags: ['đồng nghiệp', 'xung đột', 'giao tiếp', 'công việc'],
    summary:
      'Nhân viên marketing bị đồng nghiệp “cướp” ý tưởng trong họp — tức giận nhưng im lặng, sợ bị coi là tiểu tiết.',

    persona: {
      name: 'Chị Thảo',
      age: 27,
      role: 'Chuyên viên marketing nội dung tại agency quảng cáo',
      context:
        'Team 8 người, làm campaign cho khách hàng lớn. Đồng nghiệp Nam hay trình bày lại ý của Thảo như ý mình. Sếp khen Nam. Thảo muốn được công nhận nhưng sợ phản ứng sẽ ảnh hưởng đánh giá.',
    },

    situation:
      'Trong họp pitch, Thảo đề xuất concept mới. Nam bổ sung vài chi tiết rồi trình bày lại toàn bộ như ý tưởng của anh. Sếp khen Nam. Thảo ngồi im, tay nắm chặt bút, muốn nói nhưng nuốt lời.',

    initialThought:
      'Đồng nghiệp lấy ý tưởng của tôi trình bày trong họp và được sếp khen. Tôi tức giận nhưng không dám nói vì sợ bị coi là khó tính.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy tức giận, tủi thân và bất công. Cũng lo lắng nếu lên tiếng thì mọi người sẽ nghĩ tôi tiểu tiết. Căng thẳng trong ngực.',
        note: 'Tức giận + sợ bị đánh giá — thường dẫn tới im lặng.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là sếp không coi trọng tôi, Nam cố tình hạ thấp tôi. Nếu tôi nói ra thì sẽ bị coi là gây rối và mất cơ hội thăng tiến.',
        note: 'Đoán ý sếp và đồng nghiệp — chưa kiểm chứng.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin im lặng là an toàn hơn đối đầu. Phụ nữ không nên quá mạnh mẽ trong công việc. Tôi phải tự chứng minh bằng kết quả, không được than vãn.',
        note: 'Niềm tin về “im lặng an toàn” duy trì xung đột.',
      },
      {
        step: 'Value',
        content:
          'Công bằng và trung thực rất quan trọng với tôi. Tôi coi trọng sự tôn trọng lẫn nhau trong team. Chất lượng công việc cũng quan trọng.',
        note: 'Giá trị trung thực vs im lặng — mâu thuẫn rõ.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc chuyên nghiệp, muốn được công nhận. Tôi không muốn được coi là người gây rối. Tôi thấy mình phải mạnh mẽ nhưng không được “quá”.',
        note: 'Xung đột vai trò “chuyên nghiệp” vs “bảo vệ bản thân”.',
      },
      {
        step: 'Action',
        content:
          'Tôi im lặng trong họp, tránh né nói chuyện riêng với Nam. Tôi làm việc thêm giờ để bù đắp cảm giác bất công. Chưa nói với sếp về cách phối hợp trong team.',
        note: 'Im lặng mâu thuẫn trung thực; overtime thay vì giải quyết xung đột.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'work',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Giá trị: Trung thực',
        'Giá trị: Công bằng',
        'Hành động: Tránh né / im lặng',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: [],
      biases: ['Mind Reading', 'Should Statements', 'Jumping to Conclusions'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Công việc — hành động “im lặng” khi giá trị là trung thực.',
      'Góc khám phá: gợi ý suy ngẫm về câu hỏi có thể hỏi sếp thay vì đoán.',
      'Sửa bước Hành động và chạy lại để thấy ghi nhận thay đổi.',
    ],
  },

  {
    id: 'self-social-comparison',
    title: 'So sánh bản thân trên mạng xã hội',
    category: 'self',
    tags: ['mạng xã hội', 'so sánh', 'tự trọng', 'bản thân'],
    summary:
      'Nhân viên văn phòng cuối tuần lướt mạng, thấy bạn bè du lịch, mua nhà — cảm thấy mình tụt hậu và xóa bài đăng của mình.',

    persona: {
      name: 'Chị Ngọc',
      age: 32,
      role: 'Kế toán tại công ty xây dựng, sống cùng bạn trai tại Cần Thơ',
      context:
        'Làm việc ổn định 6 năm, lương vừa đủ. Bạn học cùng lớp trên mạng khoe nhà, xe, con. Ngọc vừa đăng ảnh cà phê cuối tuần rồi xóa vì thấy “nhàm”.',
    },

    situation:
      'Chủ nhật chiều, Ngọc nằm trên giường lướt Facebook một tiếng. Mỗi bài đăng khiến cô thở dài. Bạn trai hỏi “Em sao vậy?” — cô nói “Không sao” và tiếp tục so sánh cuộc đời mình với người khác.',

    initialThought:
      'Tôi lướt mạng xã hội thấy bạn bè thành công hơn mình — mua nhà, du lịch, lương cao. Tôi cảm thấy mình tụt hậu và không đủ tốt.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy buồn, ghen tị và xấu hổ về bản thân. Lo lắng mình đang lãng phí thời gian cuộc đời. Cũng cô đơn dù ở cạnh người yêu.',
        note: 'So sánh mạng xã hội thường kích hoạt xấu hổ + ghen tị.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là mọi người đều tiến xa hơn tôi. Cuộc sống tôi nhàm chán và không có gì đáng tự hào. Bạn trai có lẽ cũng thất vọng vì tôi chưa “thành công”.',
        note: 'Kết luận từ highlight reel — không phải toàn bộ sự thật.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin so sánh với người khác là động lực. Thành công đo bằng nhà xe và lương. Tôi không xứng đáng với những gì tôi có nếu chưa bằng bạn bè.',
        note: 'Niềm tin “so sánh = động lực” thường gây tê liệt.',
      },
      {
        step: 'Value',
        content:
          'Tôi coi trọng sự bình yên và chân thật trong quan hệ. Gia đình và bạn bè thật sự quan trọng — không chỉ hình ảnh trên mạng. Tôi cũng muốn phát triển bản thân.',
        note: 'Giá trị chân thật vs hành động xóa bài / so sánh.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người trưởng thành, muốn được coi là thành công. Tôi sợ được nhìn như kẻ thua cuộc. Tôi thấy mình phải chứng minh qua vật chất.',
        note: 'Vai trò “thành công” gắn với vật chất — dễ mệt mỏi.',
      },
      {
        step: 'Action',
        content:
          'Tôi lướt mạng xã hội hàng giờ, so sánh với người khác. Tôi xóa bài đăng của mình, im lặng với bạn trai. Tôi chưa dành thời gian cho sở thích hoặc gọi bạn thân ngoài mạng.',
        note: 'So sánh + tránh né — đối chiếu giá trị quan hệ chân thật.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'self',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: So sánh với người khác là động lực',
        'Niềm tin: Tôi không xứng đáng',
        'Hành động: So sánh với người khác',
        'Hành động: Tránh né / im lặng',
      ],
      contradictions: [],
      biases: ['Overgeneralization', 'Mind Reading', 'Emotional Reasoning'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Bản thân — niềm tin về so sánh và xung đột tự trọng.',
      'Góc khám phá: thiên kiến kết luận cho mọi trường hợp (“mọi người đều hơn tôi”).',
      'Thử chạy lại sau khi sửa bước Hành động — ví dụ “dành thời gian gọi bạn thân”.',
    ],
  },

  {
    id: 'learning-career-upskill',
    title: 'Muốn học kỹ năng mới nhưng thiếu thời gian',
    category: 'learning',
    tags: ['học tập', 'nghề nghiệp', 'thời gian', 'phát triển'],
    summary:
      'Nhân viên kế toán muốn học data analysis để đổi hướng nghề — mua khóa học nhưng không mở, tự trách vì lười.',

    persona: {
      name: 'Anh Phong',
      age: 36,
      role: 'Kế toán tổng hợp tại công ty sản xuất',
      context:
        'Làm kế toán 12 năm, thấy ngành thay đổi. Đồng nghiệp trẻ biết Excel nâng cao và Power BI. Phong mua khóa online 3 tháng trước, mới học 2 bài. Vợ khuyên nhưng anh nói “bận”.',
    },

    situation:
      'Tối thứ Hai, Phong về nhà sau giờ làm, ăn cơm rồi nằm xem video ngắn đến 11 giờ. Nhận email nhắc khóa học sắp hết hạn. Anh thở dài, nghĩ mình quá già để học và sợ đổi nghề thất bại.',

    initialThought:
      'Tôi muốn học kỹ năng mới để phát triển nghề nghiệp nhưng không có thời gian. Tôi tự trách mình lười và lo đã quá muộn để thay đổi.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy thất vọng, lo lắng và tội lỗi. Ghen tị với đồng nghiệp trẻ hơn. Mệt mỏi khi nghĩ đến việc phải học thêm sau giờ làm.',
        note: 'Muốn phát triển + mệt mỏi — cảm xúc có thể đồng thời đúng.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu không học ngay thì sẽ bị sa thải, cả gia đình sẽ khó khăn. Đổi nghề ở tuổi này chắc chắn thất bại.',
        note: 'Thảm họa hóa + “quá muộn” — kiểm tra có bằng chứng không.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin tuổi tác quá muộn để thay đổi. Học thêm là giải pháp mọi vấn đề nhưng tôi không đủ kỷ luật. Người trưởng thành phải ổn định, không nên nhảy việc.',
        note: 'Niềm tin mâu thuẫn nội tại: “phải học” vs “quá muộn”.',
      },
      {
        step: 'Value',
        content:
          'Tôi coi trọng phát triển và học hỏi suốt đời. Gia đình ổn định quan trọng. Tôi muốn làm tốt vai trò người chồng, người cha.',
        note: 'Giá trị phát triển vs hành động không học — gap rõ.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc, kế toán có kinh nghiệm. Tôi không muốn được coi là kẻ thất bại hoặc quá già. Tôi thấy mình phải tự làm mọi thứ.',
        note: 'Vai trò “ổn định” có thể cản trở thử nghiệm nhỏ.',
      },
      {
        step: 'Action',
        content:
          'Tôi mua khóa học nhưng không học, lãng phí thời gian xem video giải trí. Tôi làm việc nhiều giờ và tự trách móc. Tôi chưa nhờ vợ hoặc đồng nghiệp gợi ý lộ trình học ngắn.',
        note: 'Đối chiếu “coi trọng phát triển” với không có thời gian học.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'learning',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Tuổi tác quá muộn để thay đổi',
        'Niềm tin: Học thêm là giải pháp mọi vấn đề',
        'Giá trị: Phát triển',
        'Hành động: Tự trách móc',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: ['Coi trọng phát triển vs ít thời gian thực sự dành cho học hỏi'],
      biases: ['Catastrophizing', 'Overgeneralization', 'Should Statements'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Học tập — mâu thuẫn phát triển vs hành động.',
      'Góc khám phá: gợi ý một bước học nhỏ trong khả năng tuần này.',
      'Sửa bước Hành động (15 phút học/ngày, nhờ đồng nghiệp hướng dẫn) và mô phỏng lại.',
    ],
  },

  {
    id: 'health-exercise-guilt',
    title: 'Muốn tập thể dục nhưng không bắt đầu',
    category: 'health',
    tags: ['thể dục', 'sức khỏe', 'tội lỗi', 'thói quen'],
    summary:
      'Nhân viên văn phòng đăng ký phòng gym 6 tháng nhưng đi 3 lần — tự trách lười, tin sức khỏe quan trọng nhưng ưu tiên công việc.',

    persona: {
      name: 'Chị Vy',
      age: 33,
      role: 'Nhân viên hành chính tại công ty bảo hiểm',
      context:
        'Ngồi văn phòng 8 tiếng/ngày, đau lưng thỉnh thoảng. Vy đăng ký gym gần nhà, bạn bè khoe marathon. Mẹ nhắc tập thể dục mỗi khi gọi điện.',
    },

    situation:
      'Túi đồ gym nằm dưới bàn làm việc từ thứ Hai. Đến thứ Sáu, Vy chưa mở túi. Tan ca 18h30, đồng nghiệp rủ đi gym — cô nói “tuần sau” vì còn báo cáo. Trên xe buýt, cô thấy quảng cáo yoga và cảm thấy tội lỗi.',

    initialThought:
      'Tôi biết tập thể dục tốt cho sức khỏe nhưng tuần này lại không đi gym. Tôi tự trách mình lười và lo sức khỏe ngày càng kém.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy tội lỗi, xấu hổ và mệt mỏi. Lo lắng về cân nặng và đau lưng. Cũng ghen tị với bạn bè tập đều đặn.',
        note: 'Tội lỗi thường không tạo động lực bền — chỉ thêm áp lực.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là tôi lười và thiếu kỷ luật. Nếu cứ thế này tôi sẽ bệnh nặng, không theo kịp bạn bè, và mẹ sẽ thất vọng.',
        note: 'Gán nhãn “lười” — có thể bỏ qua rào cản thật (mệt, giờ làm).',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin phải tập ít nhất 1 giờ mới có ích. Chăm sóc bản thân là ích kỷ nếu còn việc chưa xong. Tôi không có thời gian cho bản thân.',
        note: 'Quy tắc “phải 1 giờ” dễ khiến không bắt đầu.',
      },
      {
        step: 'Value',
        content:
          'Sức khỏe rất quan trọng với tôi. Tôi coi trọng kỷ luật và sống chủ động. Gia đình cũng quan trọng — mẹ luôn nhắc tôi giữ sức khỏe.',
        note: 'Giá trị sức khỏe vs hành động trì hoãn.',
      },
      {
        step: 'Identity',
        content:
          'Tôi muốn là người năng động, có sức khỏe tốt. Tôi không muốn được coi là lười biếng. Tôi thấy mình là người làm việc — ưu tiên công việc trước.',
        note: 'Hai hình ảnh bản thân xung đột: “năng động” vs “người làm việc”.',
      },
      {
        step: 'Action',
        content:
          'Tôi trì hoãn đi gym, làm việc thêm giờ để xong báo cáo. Tôi tự trách móc thay vì điều chỉnh kế hoạch. Tôi chưa thử tập 10 phút tại nhà hoặc đi bộ ngắn.',
        note: 'Tự trách thay vì bước nhỏ — điểm thử nghiệm khi sửa hội thoại.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'health',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Giá trị: Sức khỏe',
        'Niềm tin: Tôi không có thời gian cho bản thân',
        'Hành động: Tự trách móc',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: ['Coi trọng sức khỏe vs không tập / ưu tiên công việc'],
      biases: ['Should Statements', 'Labeling', 'Overgeneralization'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Sức khỏe — gap giữa giá trị và hành động.',
      'Thử sửa bước Hành động: “đi bộ 15 phút sau bữa tối” — chạy lại và so sánh ghi nhận.',
      'Góc khám phá: gợi ý suy ngẫm về bước nhỏ thay vì quy tắc “phải 1 giờ”.',
    ],
  },

  {
    id: 'family-new-parent-overwhelm',
    title: 'Cha mẹ mới kiệt sức chăm con nhỏ',
    category: 'family',
    tags: ['con nhỏ', 'cha mẹ mới', 'mệt mỏi', 'hôn nhân'],
    summary:
      'Mẹ bỉm sữa con 8 tháng, thiếu ngủ, tranh cãi với chồng về chia việc — yêu con nhưng tự trách không làm mẹ tốt.',

    persona: {
      name: 'Chị Trang',
      age: 30,
      role: 'Designer freelance, mẹ của bé Bơ (8 tháng)',
      context:
        'Nghỉ thai sản kéo dài, làm việc tại nhà khi con ngủ. Chồng làm IT, về nhà muộn. Trang cho con bú đêm, dọn nhà, deadline khách hàng. Mẹ chồng hay so sánh “ngày xưa nuôi con”.',
    },

    situation:
      '3 giờ sáng, bé khóc. Trang bế con, chồng ngủ say. Sáng đó họ cãi nhau vì chồng quên pha sữa. Trang khóc, nói “anh không hiểu em mệt thế nào” — rồi tự trách vì đã nổi nóng với người yêu.',

    initialThought:
      'Tôi mệt mỏi vì chăm con nhỏ thiếu ngủ. Tôi yêu con nhưng cảm thấy mình làm mẹ tồi và hay cãi với chồng.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy mệt mỏi, kiệt sức và tủi thân. Lo lắng con không được chăm đúng cách. Tức giận với chồng nhưng ngay sau đó tội lỗi.',
        note: 'Kiệt sức cha mẹ mới — cảm xúc mạnh là phản ứng bình thường với thiếu ngủ.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là mình làm mẹ tồi vì không kiên nhẫn. Chồng tôi không yêu thương nữa vì không giúp đủ. Mẹ chồng chắc đang đánh giá tôi kém cỏi.',
        note: 'Đoán ý người khác + gán nhãn bản thân.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin mẹ phải hy sinh hoàn toàn cho con. Người mẹ tốt không được tức giận. Tôi phải tự làm mọi thứ, nhờ giúp là yếu đuối.',
        note: 'Niềm tin “hy sinh hoàn toàn” dễ dẫn tới kiệt sức.',
      },
      {
        step: 'Value',
        content:
          'Gia đình và yêu thương là quan trọng nhất. Tôi coi trọng sự bình yên trong nhà. Sức khỏe của tôi cũng quan trọng — để chăm con lâu dài.',
        note: 'Giá trị sức khỏe mẹ vs thiếu ngủ — mâu thuẫn thực tế.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người mẹ, muốn làm tốt nhất cho con. Tôi không muốn được coi là mẹ tồi hay vợ hay cáu gắt. Tôi cũng là người làm việc cần hoàn thành deadline.',
        note: 'Nhiều vai trò cùng lúc — không cần chọn một.',
      },
      {
        step: 'Action',
        content:
          'Tôi tự gánh hầu hết việc con, ít nói rõ nhu cầu với chồng. Tôi làm việc khi con ngủ, không nghỉ ngơi. Tôi tự trách móc thay vì đề nghị chia việc cụ thể.',
        note: 'Tự gánh + tự trách — thử sửa thành “nhờ chồng trực ca sáng chủ nhật”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'family',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Mẹ phải hy sinh hoàn toàn',
        'Giá trị: Gia đình',
        'Giá trị: Yêu thương',
        'Hành động: Tự trách móc',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: ['Coi trọng sức khỏe vs thiếu ngủ / không nghỉ ngơi'],
      biases: ['Should Statements', 'Mind Reading', 'Labeling'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Gia đình — niềm tin về vai trò mẹ.',
      'Góc khám phá: quy tắc “phải/nên” và gợi ý nhờ hỗ trợ thay vì tự gánh.',
      'Sửa hội thoại, chạy lại (không reset) — xem ghi nhận lặp lại thế nào.',
    ],
  },

  {
    id: 'finance-investment-fomo',
    title: 'FOMO đầu tư chứng khoán',
    category: 'finance',
    tags: ['đầu tư', 'FOMO', 'rủi ro', 'tiền bạc'],
    summary:
      'Nhân viên ngân hàng thấy bạn bè kiếm lời cổ phiếu — vay margin đầu tư, lỗ tiền và giấu vợ, càng làm nhiều giờ để gỡ.',

    persona: {
      name: 'Anh Quân',
      age: 35,
      role: 'Nhân viên tín dụng tại ngân hàng thương mại',
      context:
        'Lương ổn định, vợ là dược sĩ. Bạn cùng phòng khoe lãi chứng khoán trên nhóm chat. Quân mở tài khoản, vay margin theo lời khuyên “nhanh thôi”. Thị trường điều chỉnh, lỗ 40 triệu trong 2 tuần.',
    },

    situation:
      'Đêm thứ Năm, Quân ngồi xem bảng điện tử chứng khoán đến 1 giờ sáng. Vợ hỏi sao gần đây anh hay căng thẳng — anh nói “công việc áp lực”. Sáng mai phải trả nợ margin một phần, anh tính xin làm thêm ca cuối tuần mà không dám thú nhận với vợ.',

    initialThought:
      'Tôi đầu tư chứng khoán theo bạn bè và bị lỗ. Tôi sợ vợ biết, lo không đủ tiền trả nợ và tự trách mình tham lam.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy lo lắng, căng thẳng và xấu hổ. Sợ hãi mỗi khi điện thoại reo — sợ vợ hoặc sếp hỏi. Cũng ghen tị với bạn đã chốt lời.',
        note: 'FOMO tài chính thường kèm xấu hổ — khó tách khỏi quyết định.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu không gỡ gấp thì mất hết, gia đình sẽ tan vỡ. Mọi người sẽ coi tôi là kẻ ngu ngốc. Một lần lỗ là thất bại cả đời tài chính.',
        note: 'Thảm họa hóa + kết luận cho mọi trường hợp.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin tiền mang lại hạnh phúc và an toàn. Người khôn phải biết kiếm tiền nhanh. Thất bại tài chính là đáng xấu hổ, không được nói với người thân.',
        note: 'Niềm tin về tiền + im lặng — mâu thuẫn với trung thực.',
      },
      {
        step: 'Value',
        content:
          'Gia đình và trung thực rất quan trọng với tôi. Tôi coi trọng an toàn tài chính lâu dài. Sức khỏe tinh thần cũng quan trọng — nhưng tôi đang mất ngủ vì lo.',
        note: 'Giá trị an toàn vs hành động đầu cơ — đối chiếu ở Action.',
      },
      {
        step: 'Identity',
        content:
          'Tôi làm trong ngành tài chính, muốn được coi là am hiểu tiền bạc. Tôi không muốn là người thất bại trước vợ và bạn bè. Tôi thấy mình phải tự gỡ một mình.',
        note: 'Vai trò “am hiểu tài chính” làm khó nhận sai lầm.',
      },
      {
        step: 'Action',
        content:
          'Tôi giấu vợ về khoản lỗ, tiếp tục theo dõi thị trường đến khuya. Tôi làm việc thêm giờ để kiếm thêm tiền. Tôi chưa nhờ tư vấn độc lập hay nói thật với vợ.',
        note: 'Im lặng + làm thêm giờ — thử sửa thành “thú nhận và lập kế hoạch trả nợ”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'finance',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Tiền mang lại hạnh phúc',
        'Giá trị: Gia đình',
        'Giá trị: Trung thực',
        'Hành động: Tránh né / im lặng',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: ['Tiền mang lại hạnh phúc vs giấu vợ / mất an toàn tài chính'],
      biases: ['Catastrophizing', 'Overgeneralization', 'Mind Reading'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Tài chính — niềm tin về tiền và hành động giấu giếm.',
      'Góc khám phá: mâu thuẫn trung thực vs im lặng; gợi ý suy ngẫm tiếp.',
      'Sửa bước Hành động và chạy lại — so sánh ghi nhận Hành động.',
    ],
  },

  {
    id: 'finance-layoff-anxiety',
    title: 'Lo sợ bị sa thải',
    category: 'finance',
    tags: ['sa thải', 'công việc', 'an toàn', 'tài chính'],
    summary:
      'Nhân viên sản xuất nghe tin công ty cắt giảm — tiết kiệm từng đồng, làm thêm ca, không dám chi cho con dù chưa chắc mất việc.',

    persona: {
      name: 'Chị Hạnh',
      age: 40,
      role: 'Công nhân may tại khu công nghiệp Bình Dương',
      context:
        'Làm công ty 11 năm, chồng lái xe grab. Hai con đang học. Tin đồn cắt 20% nhân sự cuối quý. Hạnh thấy sếp họp riêng, lo sợ tên mình trong danh sách.',
    },

    situation:
      'Sau buổi họp toàn công ty về “tái cơ cấu”, Hạnh nhận được email mời họp 1–1 chiều mai. Cô gọi chồng, giọng run. Tối đó cô từ chối mua sách cho con, nói “mẹ tiết kiệm” — con hỏi “mẹ sao vậy?” cô im lặng.',

    initialThought:
      'Công ty có thể sa thải tôi tuần tới. Tôi lo không đủ tiền trả học phí con và sợ cả gia đình rơi vào khó khăn.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy sợ hãi, lo lắng và bất an. Tim đập nhanh mỗi khi thấy email công ty. Buồn khi phải từ chối con.',
        note: 'Lo mất việc thường kích hoạt sợ hãi sâu — cần ghi nhận trước khi phân tích.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là họp 1–1 chắc chắn là sa thải. Mất việc thì không ai thuê, con phải bỏ học, chồng không gánh nổi. Cả nhà sẽ nghèo đói.',
        note: 'Chưa có kết quả họp đã kết luận — vội kết luận.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin không có việc làm thì không sống được. Phải tiết kiệm mọi thứ khi có tin xấu. Người lớn phải chịu đựng, không được lộ yếu đuối với con.',
        note: 'Niềm tin “phải giấu” có thể làm con lo thêm.',
      },
      {
        step: 'Value',
        content:
          'Gia đình là ưu tiên số một. Giáo dục con rất quan trọng. Tôi coi trọng trung thực với người thân — nhưng đang giấu nỗi lo.',
        note: 'Giá trị giáo dục vs hành động cắt chi sách học — xung đột tiềm ẩn.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người mẹ, người lao động chăm chỉ. Tôi không muốn được coi là gánh nặng. Tôi thấy mình phải gánh cả nhà nếu mất việc.',
        note: 'Vai trò “gánh nhà” tăng áp lực tự gánh một mình.',
      },
      {
        step: 'Action',
        content:
          'Tôi làm thêm ca tăng ca mỗi khi có cơ hội. Tôi cắt chi tiêu cho con và im lặng với chồng về mức lo thật sự. Tôi chưa chuẩn bị kế hoạch tài chính hay hỏi HR nội dung họp.',
        note: 'Phản ứng vội — thử sửa: “hỏi rõ buổi họp, bàn với chồng”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'finance',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Không có tiền không sống được',
        'Giá trị: Gia đình',
        'Giá trị: Giáo dục',
        'Hành động: Tránh né / im lặng',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: ['Giá trị giáo dục vs cắt chi cho con vì lo sợ'],
      biases: ['Catastrophizing', 'Fortune Telling', 'Jumping to Conclusions'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Tài chính và Gia đình.',
      'Góc khám phá: kịch bản ngoài “mất việc = hết đường”.',
      'Chạy mô phỏng rồi xem Dòng thời gian — sự kiện “họp 1–1” được ghi thế nào.',
    ],
  },

  {
    id: 'work-resignation-dilemma',
    title: 'Muốn nghỉ việc nhưng sợ bất ổn',
    category: 'work',
    tags: ['nghỉ việc', 'đổi việc', 'sợ hãi', 'công việc'],
    summary:
      'Nhân viên sales mệt mỏi vì áp lực KPI — muốn đổi ngành nhưng sợ lương giảm và gia đình phản đối.',

    persona: {
      name: 'Anh Bình',
      age: 37,
      role: 'Trưởng phòng kinh doanh tại công ty phân phối điện tử',
      context:
        '15 năm kinh doanh, lương tốt nhưng KPI tăng mỗi quý. Bình mơ mở quán cà phê nhỏ. Vợ lo mất thu nhập ổn định. Cha nói “đừng bỏ việc ngớ ngẩn”.',
    },

    situation:
      'Cuối tháng, Bình không đạt KPI lần thứ hai liên tiếp. Sếp nhắc nhở trước team. Tối đó Bình tìm khóa học pha chế, rồi tắt tab vì sợ. Vợ hỏi “Anh có muốn đổi việc không?” — anh nói “ổn mà” nhưng không ngủ được.',

    initialThought:
      'Tôi mệt mỏi vì áp lực KPI và muốn đổi việc, nhưng sợ mất thu nhập ổn định. Gia đình sẽ không đồng ý nếu tôi nghỉ.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy mệt mỏi, bế tắc và lo lắng. Ghen tị với bạn đã làm chủ quán nhỏ. Xấu hổ khi không đạt KPI trước đồng nghiệp.',
        note: 'Muốn đổi hướng + sợ — hai cảm xúc cùng hợp lệ.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu nghỉ việc thì hối hận cả đời, gia đình sẽ khổ. Nếu ở lại thì sẽ bệnh vì stress. Không có lựa chọn nào đúng.',
        note: 'Tư duy đen trắng — “ở lại hoặc hủy hoại”.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin đổi việc là không ổn định. An toàn quan trọng hơn mơ ước. Người trưởng thành phải nhịn để nuôi gia đình.',
        note: 'Niềm tin “phải nhịn” vs giá trị phát triển bản thân.',
      },
      {
        step: 'Value',
        content:
          'Tôi coi trọng tự do và sáng tạo trong công việc. Gia đình ổn định rất quan trọng. Sức khỏe tinh thần cũng quan trọng với tôi.',
        note: 'Tự do vs an toàn — mâu thuẫn cốt lõi của kịch bản.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người trưởng thành, người chồng người cha phải lo kinh tế. Tôi không muốn được coi là kẻ bỏ cuộc. Tôi cũng mơ là người làm chủ nhỏ.',
        note: 'Hai hình ảnh bản thân — không cần chọn ngay.',
      },
      {
        step: 'Action',
        content:
          'Tôi ở lại công việc cũ, làm việc nhiều giờ để cố đạt KPI. Tôi im lặng với vợ về mức mệt thật sự. Tôi chưa thử trải nghiệm nhỏ (part-time, thử quán cuối tuần).',
        note: 'Im lặng + overwork — sửa thành “bàn kế hoạch thử 3 tháng”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'work',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Đổi việc là không ổn định',
        'Giá trị: Tự do',
        'Giá trị: Gia đình',
        'Hành động: Làm việc nhiều giờ',
        'Hành động: Tránh né / im lặng',
      ],
      contradictions: ['Mong tự do vs ở lại vì an toàn / không thử'],
      biases: ['Black and White Thinking', 'Catastrophizing', 'Should Statements'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Công việc — niềm tin về ổn định.',
      'Góc khám phá: thiên kiến đen trắng và gợi ý bước thử nhỏ.',
      'Sửa hội thoại và chạy lại — xem Hành động và mâu thuẫn thay đổi.',
    ],
  },

  {
    id: 'work-presentation-fear',
    title: 'Sợ thuyết trình trước sếp',
    category: 'work',
    tags: ['thuyết trình', 'sợ hãi', 'tự tin', 'công việc'],
    summary:
      'Chuyên viên phân tích được giao pitch trước ban giám đốc — lo sợ bị đánh giá kém, ôn kịch bản đến mất ngủ, muốn nhờ đồng nghiệp thay.',

    persona: {
      name: 'Chị Yến',
      age: 26,
      role: 'Chuyên viên phân tích dữ liệu tại công ty bán lẻ',
      context:
        'Vào công ty 2 năm, giỏi Excel nhưng ngại nói trước đám đông. Lần đầu pitch trực tiếp với GĐ và phòng ban. Đồng nghiệp khuyên “cứ tự tin” nhưng Yến tay run khi tập.',
    },

    situation:
      'Chiều mai pitch 20 phút. Yến tập ở nhà trước gương, quên lời ở slide 5, bật khóc. Nhắn đồng nghiệp “chắc em làm không được”. Tối đó cô sửa slide lần thứ mười, nghĩ sếp sẽ nghĩ mình không đủ tài năng để thăng tiến.',

    initialThought:
      'Ngày mai tôi phải thuyết trình trước ban giám đốc. Tôi sợ nói sai, bị đánh giá kém và mất cơ hội thăng tiến.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy sợ hãi, lo lắng và căng thẳng. Tim đập nhanh khi nghĩ đến phòng họp. Xấu hổ vì tay run khi tập nói.',
        note: 'Lo thuyết trình là phổ biến — không đồng nghĩa “yếu kém”.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là nếu run hoặc vấp một câu thì sếp sẽ coi tôi là kẻ không chuyên nghiệp. Một lần trình bày tệ sẽ hủy hoại cả sự nghiệp.',
        note: 'Phóng đại hậu quả một sự kiện.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin phải hoàn hảo mới được công nhận. Người giỏi không được run hay ngập ngừng. Tôi không xứng đáng với vị trí này nếu không nói trôi chảy.',
        note: 'Chủ nghĩa hoàn hảo nuôi sợ thuyết trình.',
      },
      {
        step: 'Value',
        content:
          'Tôi coi trọng chất lượng công việc và trung thực. Muốn đóng góp giá trị thật cho team. Phát triển bản thân cũng quan trọng.',
        note: 'Giá trị đóng góp vs tránh né cơ hội pitch.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc, chuyên viên phân tích. Tôi không muốn được coi là nhút nhát hay kém cỏi. Tôi thấy mình phải chứng minh qua mỗi lần nói.',
        note: 'Áp lực “chứng minh” mỗi lần xuất hiện.',
      },
      {
        step: 'Action',
        content:
          'Tôi ôn slide đến khuya, sửa đi sửa lại nhiều lần. Tôi nhắn muốn nhờ đồng nghiệp thay nhưng chưa nói với sếp về nỗi lo. Tôi chưa tập trước một người bạn tin tưởng.',
        note: 'Tránh né từng bước — thử sửa: “tập 10 phút với mentor”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'work',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Phải hoàn hảo mới được yêu',
        'Niềm tin: Tôi không xứng đáng',
        'Hành động: Tìm kiếm giải pháp',
      ],
      contradictions: [],
      biases: ['Catastrophizing', 'Should Statements', 'Magnification'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Công việc và Bản thân.',
      'Góc khám phá: gợi ý về quy tắc “phải hoàn hảo”.',
      'Sửa bước Hành động (nhờ mentor tập 10 phút) và mô phỏng lại.',
    ],
  },

  {
    id: 'learning-language-barrier',
    title: 'Học tiếng Anh mãi không tiến bộ',
    category: 'learning',
    tags: ['tiếng Anh', 'học tập', 'tự tin', 'công việc'],
    summary:
      'Nhân viên muốn học tiếng Anh để thăng tiến — đăng ký app, học được vài tuần rồi bỏ, tự tiện mình “dốt ngoại ngữ”.',

    persona: {
      name: 'Anh Kiệt',
      age: 28,
      role: 'Nhân viên logistics tại công ty xuất nhập khẩu',
      context:
        'Cần đọc email tiếng Anh hàng ngày, thường dùng Google dịch. Đồng nghiệp trẻ hơn giao tiếp tốt hơn. Kiệt mua gói app học 1 năm, streak 12 ngày rồi đứt.',
    },

    situation:
      'Sếp gợi ý Kiệt tham gia cuộc họp với đối tác nước ngoài tháng sau. Kiệt đồng ý trong lúc phấn khích, về nhà lo sợ. Mở app học lại, sai phát âm một từ, tắt app và nghĩ “mình không có năng khiếu”.',

    initialThought:
      'Tôi học tiếng Anh mãi không tiến bộ và sợ mất cơ hội thăng tiến. Mỗi lần nói sai tôi cảm thấy xấu hổ và muốn bỏ cuộc.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy xấu hổ, thất vọng và lo lắng. Ghen tị với đồng nghiệp nói lưu loát. Buồn khi nghĩ đến cuộc họp tháng sau.',
        note: 'Xấu hổ khi học — thường làm dừng sớm hơn là thiếu năng lực.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là mình không có năng khiếu ngôn ngữ. Nói sai một lần là chứng tỏ sẽ không bao giờ giỏi. Sếp chắc đang hối hận vì giao tôi họp.',
        note: 'Đoán ý sếp + kết luận “không bao giờ”.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin trí tuệ là do bẩm sinh — không tài năng thì cố cũng vô ích. Người lớn học ngoại ngữ quá muộn. Phải giỏi hoàn hảo mới được nói.',
        note: 'Niềm tin “bẩm sinh / quá muộn” — kiểm tra bằng ví dụ nhỏ.',
      },
      {
        step: 'Value',
        content:
          'Tôi coi trọng phát triển và học hỏi. Công việc ổn định quan trọng. Tôi muốn được tin tưởng trong team quốc tế.',
        note: 'Giá trị phát triển vs hành động bỏ học.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc logistics, không phải “dân ngoại ngữ”. Tôi không muốn được cười nhạo khi phát âm sai. Tôi thấy mình phải giỏi ngay lần đầu.',
        note: 'Gán nhãn “dốt ngoại ngữ” — có thể thử lại với bước nhỏ.',
      },
      {
        step: 'Action',
        content:
          'Tôi bỏ app học nhiều ngày, chỉ dùng Google dịch. Tôi tránh né luyện nói trước gương. Tôi chưa nhờ đồng nghiệp giỏi tiếng Anh luyện 15 phút/tuần.',
        note: 'Tránh né — sửa thành “nhờ đồng nghiệp hỗ trợ”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'learning',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Trí tuệ là do bẩm sinh',
        'Niềm tin: Phải hoàn hảo mới được yêu',
        'Giá trị: Phát triển',
        'Hành động: Tránh né / im lặng',
      ],
      contradictions: ['Coi trọng phát triển vs bỏ học / tránh luyện nói'],
      biases: ['Overgeneralization', 'Mind Reading', 'Labeling'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Học tập.',
      'Góc khám phá: mâu thuẫn phát triển vs hành động; thử sửa hội thoại.',
      'Chạy lại lần 2 (không reset) sau khi sửa — xem ghi nhận lặp lại.',
    ],
  },

  {
    id: 'health-medical-anxiety',
    title: 'Lo sợ kết quả khám sức khỏe',
    category: 'health',
    tags: ['khám bệnh', 'lo âu', 'sức khỏe', 'gia đình'],
    summary:
      'Nhân viên văn phòng nhận kết quả xét nghiệm có chỉ số lệch — chưa gặp bác sĩ đã nghĩ đến bệnh nặng, tra Google đến khuya, giấu vợ.',

    persona: {
      name: 'Anh Long',
      age: 44,
      role: 'Kế toán trưởng tại công ty sản xuất thực phẩm',
      context:
        'Khám định kỳ công ty, men gan hơi cao. Bác sĩ hẹn tái khám sau 2 tuần. Long tra mạng thấy nhiều bệnh nặng. Cha mất vì ung thư gan khi Long 20 tuổi.',
    },

    situation:
      'Nhận email kết quả xét nghiệm chiều thứ Sáu. Long đọc “men gan tăng nhẹ”, lập tức nghĩ đến bệnh của cha. Tối đó anh tra Google 2 tiếng, không ăn cơm. Vợ hỏi anh có sao không — anh nói “không sao” và trốn vào phòng làm việc.',

    initialThought:
      'Kết quả khám sức khỏe có chỉ số bất thường. Tôi lo có thể bị bệnh nặng như cha tôi và sợ không kịp nhìn con lớn.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy sợ hãi, lo lắng và bất an. Buồn khi nhớ cha. Căng thẳng mỗi khi nhìn thấy email bệnh viện.',
        note: 'Lo sức khỏe có thể gắn ký ức người thân — đáng ghi nhận.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là men gan cao chắc là bệnh nặng, có thể ung thư. Bác sĩ hẹn tái khám vì đã quá muộn. Tôi sẽ không sống đủ lâu để thấy con học đại học.',
        note: 'Tra mạng + kết luận tồi nhất trước khi gặp bác sĩ.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin bệnh tật chạy theo gia đình — số phận tôi giống cha. Biết tin xấu phải tự gánh, không nên làm vợ con lo. Đi khám là điều đáng sợ.',
        note: 'Niềm tin “số phận” + giấu giếm — đối chiếu giá trị gia đình.',
      },
      {
        step: 'Value',
        content:
          'Gia đình là ưu tiên số một. Sức khỏe quan trọng để ở bên con lâu dài. Trung thực với người thân cũng quan trọng với tôi.',
        note: 'Trung thực vs giấu vợ — mâu thuẫn rõ.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người cha, người chồng phải mạnh mẽ. Tôi không muốn được coi là yếu đuối. Tôi thấy mình phải kiểm soát mọi thứ — kể cả tin xấu.',
        note: '“Phải mạnh” có thể trì hoãn đi khám đúng cách.',
      },
      {
        step: 'Action',
        content:
          'Tôi tra cứu bệnh trên mạng đến khuya, tự dọa mình. Tôi im lặng với vợ, trì hoãn gọi bác sĩ hỏi rõ. Tôi làm việc nhiều giờ để không nghĩ — nhưng ăn uống kém.',
        note: 'Tránh chuyên môn — sửa: “đặt lịch tái khám, nói với vợ”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'health',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Số phận / định mệnh',
        'Giá trị: Gia đình',
        'Giá trị: Sức khỏe',
        'Hành động: Tránh né / im lặng',
      ],
      contradictions: ['Coi trọng sức khỏe vs trì hoãn gặp bác sĩ / tra mạng hoảng'],
      biases: ['Catastrophizing', 'Emotional Reasoning', 'Fortune Telling'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Sức khỏe — cách hiểu vs sự kiện khám.',
      'Góc khám phá: thiên kiến thảm họa hóa và gợi ý suy ngẫm tiếp.',
      'Disclaimer app vẫn áp dụng — đây là suy ngẫm, không thay tư vấn y tế.',
    ],
  },

  {
    id: 'self-perfectionism-burnout',
    title: 'Chủ nghĩa hoàn hảo trong công việc',
    category: 'self',
    tags: ['hoàn hảo', 'tự trách', 'công việc', 'bản thân'],
    summary:
      'Biên tập viên chỉnh sửa báo cáo đến 15 lần — deadline trễ, tự trách, tin một sai sót nhỏ sẽ hủy hoại uy tín cả năm.',

    persona: {
      name: 'Chị Quỳnh',
      age: 31,
      role: 'Biên tập viên nội dung tại công ty truyền thông',
      context:
        'Tốt nghiệp báo chí loại giỏi, được khen cẩn thận. Sếp giao báo cáo quý cho khách hàng lớn. Quỳnh sửa từng dấu phẩy, gửi bản 8 chưa hài lòng, deadline còn 6 tiếng.',
    },

    situation:
      '23h đêm trước deadline, Quỳnh vẫn sửa slide. Đồng nghiệp nhắn “gửi bản 8 được rồi”. Cô thấy một lỗi chính tả nhỏ trong bản cũ, hoảng sợ, bắt đầu sửa lại từ đầu. Tay run, mắt đỏ vì màn hình.',

    initialThought:
      'Tôi sợ gửi báo cáo chưa hoàn hảo. Một lỗi nhỏ có thể khiến khách hàng mất tin tưởng và sếp đánh giá tôi kém cả năm.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy căng thẳng, sợ hãi và tức giận với bản thân. Lo đến mức không ăn được. Xấu hổ nếu nghĩ đến việc gửi bản “chưa đủ tốt”.',
        note: 'Hoàn hảo hóa thường kèm tự trách mạnh.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là một lỗi chính tả nghĩa là thiếu chuyên nghiệp hoàn toàn. Khách hàng sẽ hủy hợp đồng. Sếp sẽ nghĩ tôi không đủ tài năng cho vị trí này.',
        note: 'Một chi tiết nhỏ → kết luận toàn bộ sự nghiệp.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin phải hoàn hảo mới được yêu và công nhận. Sai lầm là đáng xấu hổ. Gửi sớm hơn deadline là thiếu trách nhiệm nếu chưa “đủ tốt”.',
        note: 'Niềm tin cốt lõi của perfectionism.',
      },
      {
        step: 'Value',
        content:
          'Tôi coi trọng chất lượng và trung thực trong công việc. Uy tín với khách hàng quan trọng. Sức khỏe cũng quan trọng — nhưng tôi hay bỏ qua khi deadline.',
        note: 'Chất lượng vs sức khỏe / deadline — cân bằng thực tế.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người làm việc cẩn thận, không muốn được coi là cẩu thả. Tôi thấy mình phải chứng minh bằng sản phẩm hoàn hảo mỗi lần.',
        note: 'Danh tính gắn với “không sai” — rất căng.',
      },
      {
        step: 'Action',
        content:
          'Tôi sửa báo cáo đến khuya, trễ deadline. Tôi tự trách móc thay vì hỏi sếp mức “đủ tốt”. Tôi từ chối giúp đỡ đồng nghiệp vì “bận sửa”.',
        note: 'Over-edit — thử sửa: “gửi bản 8, ghi chú chỉnh sửa sau”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'self',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Phải hoàn hảo mới được yêu',
        'Niềm tin: Sai lầm là đáng xấu hổ',
        'Hành động: Tự trách móc',
        'Hành động: Làm việc nhiều giờ',
      ],
      contradictions: ['Coi trọng sức khỏe vs làm khuya / trễ deadline'],
      biases: ['Catastrophizing', 'Should Statements', 'Magnification'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Bản thân — niềm tin hoàn hảo.',
      'Góc khám phá: gợi ý “đủ tốt” vs “hoàn hảo”.',
      'Sửa bước Hành động và chạy lại — so sánh ghi nhận.',
    ],
  },

  {
    id: 'family-teen-rebellion',
    title: 'Mâu thuẫn với con tuổi teen',
    category: 'family',
    tags: ['tuổi teen', 'gia đình', 'giao tiếp', 'tự do'],
    summary:
      'Mẹ đơn thân cãi với con gái 15 tuổi vì đi chơi khuya — lo con sa đà, quy tắc cứng, con càng lì, mẹ tự trách nuôi dạy sai.',

    persona: {
      name: 'Chị Loan',
      age: 41,
      role: 'Y tá tại bệnh viện đa khoa, mẹ đơn của bé An (15 tuổi)',
      context:
        'Ly hôn 5 năm, con sống với mẹ. Loan làm ca đêm, ít thời gian. An hay đi chơi với bạn, về khuya. Hôm qua An nói “mẹ không hiểu con” và đóng cửa phòng.',
    },

    situation:
      '1 giờ sáng, An chưa về. Loan gọi 10 cuộc không nghe. Khi con về, mẹ quát, tịch thu điện thoại. An khóc nói “con ghét nhà này”. Sáng sau cả hai im lặng, Loan nghỉ ca vì mệt và tự hỏi mình có phải mẹ tồi không.',

    initialThought:
      'Con gái tôi đi chơi khuya, không nghe lời. Tôi lo con sa vào bạn xấu và tức giận vì cảm thấy mình không kiểm soát được gì.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy tức giận, lo lắng và tủi thân. Sợ con gặp nguy hiểm. Tội lỗi vì đã quát to và nói lời nặng.',
        note: 'Lo + tức — phổ biến với cha mẹ teen; cả hai đều hợp lệ.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là con coi thường mình, sẽ sa vào tệ nạn nếu không kiểm soát chặt. Hàng xóm chắc nghĩ tôi dạy con kém vì mẹ đơn.',
        note: 'Đoán ý người khác + dự đoán tồi tệ nhất cho con.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin con phải nghe lời cha mẹ. Mẹ đơn phải vừa là mẹ vừa là cha — không được yếu. Nếu buông lỏng một chút thì mọi thứ sụp đổ.',
        note: 'Niềm tin kiểm soát — đối chiếu giá trị tự do của teen.',
      },
      {
        step: 'Value',
        content:
          'An toàn của con là quan trọng nhất. Tôi coi trọng tình yêu thương và kết nối — dù đang khó nói chuyện. Tôn trọng lẫn nhau cũng quan trọng.',
        note: 'Yêu thương vs quy tắc cứng — tìm điểm gặp.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là người mẹ, phải bảo vệ con. Tôi không muốn được coi là mẹ thất bại. Tôi thấy mình là người kiểm soát — mất kiểm soát là đáng sợ.',
        note: 'Vai trò “kiểm soát” vs con cần tự chủ.',
      },
      {
        step: 'Action',
        content:
          'Tôi quát mắng, tịch thu điện thoại, đặt giờ giấc cứng. Tôi làm việc ca đêm, ít trò chuyện bình thường với con. Tôi chưa ngồi nghe con giải thích bạn bè và nhu cầu đi chơi.',
        note: 'Kiểm soát vs kết nối — sửa: “hẹn 30 phút nói chuyện cuối tuần”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'family',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Con phải nghe lời',
        'Giá trị: Gia đình',
        'Giá trị: Yêu thương',
        'Hành động: La mắng / kỷ luật con',
      ],
      contradictions: [
        'Con phải nghe lời vs coi trọng tự do / tôn trọng',
        'Yêu thương vs kiểm soát chặt',
      ],
      biases: ['Catastrophizing', 'Mind Reading', 'Should Statements'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Gia đình — mâu thuẫn nghe lời vs tự do.',
      'Góc khám phá: gợi ý ranh giới vs kiểm soát.',
      'Sửa hội thoại (thêm “ngồi nghe con 30 phút”) và mô phỏng lại.',
    ],
  },

  {
    id: 'family-inlaw-expectations',
    title: 'Áp lực từ gia đình chồng',
    category: 'family',
    tags: ['mẹ chồng', 'hôn nhân', 'kỳ vọng', 'gia đình'],
    summary:
      'Dâu trẻ bị mẹ chồng so sánh với con dâu người khác — cố gắng làm đúng ý, mệt mỏi, chồng trung lập, cô im lặng và tự trách.',

    persona: {
      name: 'Chị Hà',
      age: 29,
      role: 'Giáo viên mầm non, vợ của anh Tùng (kỹ sư)',
      context:
        'Sống cùng mẹ chồng ở ngoại thành Hà Nội sau cưới 2 năm. Mẹ chồng hay nhắc “nhà người ta dâu nấu giỏi”. Hà làm việc và nội trợ, chưa có con — bà hỏi “bao giờ có cháu”.',
    },

    situation:
      'Bữa cơm tối Chủ nhật, mẹ chồng nhận xét canh mặn. Hà xin lỗi, vào bếp nấu lại. Chồng nói “Mẹ nói vậy thôi, em đừng buồn” rồi xem TV. Hà rửa bát, khóc trong bồn rửa, không dám nói với ai.',

    initialThought:
      'Mẹ chồng luôn chê tôi không đủ tốt so với người khác. Tôi cố gắng làm hài lòng mọi người nhưng mệt mỏi và cảm thấy không được trân trọng.',

    dialogue: [
      {
        step: 'Emotion',
        content:
          'Tôi cảm thấy tủi thân, buồn và tức giận. Lo lắng mối quan hệ gia đình xấu đi. Cô đơn dù sống chung nhà đông người.',
        note: 'Cô đơn trong nhà — cảm xúc thật, dễ bị bỏ qua.',
      },
      {
        step: 'Interpretation',
        content:
          'Tôi hiểu là mẹ chồng không thích tôi, chồng không bảo vệ tôi. Nếu nói ra thì sẽ thành dâu bất hiếu. Hôn nhân có lẽ là sai lầm.',
        note: 'Vội kết luận “hôn nhân sai” — kiểm tra bằng hội thoại.',
      },
      {
        step: 'Belief',
        content:
          'Tôi tin dâu phải hiếu thảo, nhịn để hòa khí. Người vợ tốt phải hòa hợp với gia đình chồng. Nói không với người lớn là sai.',
        note: 'Niềm tin “phải nhịn” — đối chiếu giá trị tôn trọng bản thân.',
      },
      {
        step: 'Value',
        content:
          'Hòa hợp gia đình quan trọng với tôi. Tôi cũng coi trọng sự tôn trọng và bình đẳng trong hôn nhân. Yêu thương chồng vẫn quan trọng.',
        note: 'Hòa hợp vs tôn trọng — mâu thuẫn cốt lõi.',
      },
      {
        step: 'Identity',
        content:
          'Tôi là con dâu, người vợ, giáo viên. Tôi không muốn được coi là ích kỷ hay bất hiếu. Tôi thấy mình phải chứng minh đủ tốt.',
        note: 'Áp lực “đủ tốt” — gánh nặng vai trò.',
      },
      {
        step: 'Action',
        content:
          'Tôi im lặng, xin lỗi và cố làm đúng ý mẹ chồng. Tôi chưa nói với chồng cảm giác thật sự. Tôi tự trách móc khi nấu không vừa ý.',
        note: 'Im lặng — sửa: “hẹn chồng nói chuyện riêng 20 phút”.',
      },
    ],

    expectedOutcomes: {
      forestTree: 'family',
      nodeTypes: ['Event', 'Emotion', 'Interpretation', 'Belief', 'Value', 'Identity', 'Action'],
      highlights: [
        'Niềm tin: Dâu phải hiếu thảo',
        'Giá trị: Hòa hợp',
        'Hành động: Tránh né / im lặng',
        'Hành động: Tự trách móc',
      ],
      contradictions: [],
      biases: ['Mind Reading', 'Should Statements', 'Emotional Reasoning'],
    },

    learningPoints: [
      'Mở Bản đồ suy nghĩ → nhánh Gia đình.',
      'Góc khám phá: quy tắc “phải nhịn” và gợi ý đặt ranh giới nhẹ nhàng.',
      'Thử sửa hội thoại và chạy lại — xem ghi nhận Hành động thay đổi.',
    ],
  },
];

if (typeof window !== 'undefined') {
  window.TEST_SCENARIOS = TEST_SCENARIOS;
}
