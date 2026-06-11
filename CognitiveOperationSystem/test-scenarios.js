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
];

if (typeof window !== 'undefined') {
  window.TEST_SCENARIOS = TEST_SCENARIOS;
}
