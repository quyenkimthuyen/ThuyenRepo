const EVENTS = [
  // === TÀI CHÍNH (12) ===
  {
    id: 'fin_001', category: 'finance', subcategory: 'tiêu dùng',
    text: 'Bạn vừa nhận được 500$. Bạn sẽ làm gì?',
    choices: [
      { id: 'A', text: 'Mua điện thoại mới', tags: ['short_term', 'risk_low'],
        immediate: { wealth: -400, happiness: 15 },
        delayed: [{ days: 30, effects: { wealth: -20 }, message: 'Chi phí sửa chữa và phụ kiện điện thoại tăng lên.', traceChoice: 'Mua điện thoại mới' }],
        flags: ['impulse_spending'] },
      { id: 'B', text: 'Đầu tư học kỹ năng', tags: ['long_term', 'learning', 'risk_low'],
        immediate: { wealth: -200, knowledge: 15, happiness: 5 },
        delayed: [{ days: 45, effects: { wealth: 25, knowledge: 10 }, message: 'Kỹ năng mới giúp bạn có thêm cơ hội thu nhập.', traceChoice: 'Đầu tư học kỹ năng' }] },
      { id: 'C', text: 'Tiết kiệm', tags: ['long_term', 'risk_low'],
        immediate: { wealth: 50, happiness: -3 },
        delayed: [{ days: 60, effects: { wealth: 30, happiness: 5 }, message: 'Quỹ tiết kiệm tạo cảm giác an tâm.', traceChoice: 'Tiết kiệm' }] },
      { id: 'D', text: 'Chia sẻ với gia đình', tags: ['relationship', 'short_term'],
        immediate: { wealth: -150, relationships: 20, happiness: 10 },
        delayed: [{ days: 40, effects: { relationships: 10, happiness: 5 }, message: 'Gia đình nhớ đến sự hỗ trợ của bạn.', traceChoice: 'Chia sẻ với gia đình' }] }
    ]
  },
  {
    id: 'fin_002', category: 'finance', subcategory: 'đầu tư',
    text: 'Một người bạn giới thiệu cơ hội đầu tư với lợi nhuận cao nhưng rủi ro lớn.',
    choices: [
      { id: 'A', text: 'Đầu tư toàn bộ tiền tiết kiệm', tags: ['risk_high', 'short_term'],
        immediate: { wealth: -80 },
        delayed: [{ days: 20, effects: { wealth: -40, happiness: -10 }, message: 'Kết quả đầu tư rủi ro không như kỳ vọng.', traceChoice: 'Đầu tư toàn bộ' }] },
      { id: 'B', text: 'Đầu tư một phần nhỏ', tags: ['risk_high', 'long_term'],
        immediate: { wealth: -30, knowledge: 5 },
        delayed: [{ days: 30, effects: { wealth: 20, knowledge: 5 }, message: 'Bạn học được bài học về quản lý rủi ro.', traceChoice: 'Đầu tư một phần' }] },
      { id: 'C', text: 'Từ chối và tìm hiểu thêm', tags: ['risk_low', 'long_term', 'learning'],
        immediate: { knowledge: 10 },
        delayed: [{ days: 25, effects: { wealth: 15 }, message: 'Kiến thức giúp bạn tránh được rủi ro lớn.', traceChoice: 'Từ chối và tìm hiểu' }] },
      { id: 'D', text: 'Hỏi ý kiến chuyên gia', tags: ['long_term', 'learning', 'risk_low'],
        immediate: { wealth: -10, knowledge: 15 },
        delayed: [{ days: 35, effects: { wealth: 20 }, message: 'Lời khuyên chuyên gia giúp bạn đưa ra quyết định tốt hơn.', traceChoice: 'Hỏi chuyên gia' }] }
    ]
  },
  {
    id: 'fin_003', category: 'finance', subcategory: 'tiết kiệm',
    text: 'Cuối tháng bạn còn dư 200$. Bạn muốn dùng thế nào?',
    choices: [
      { id: 'A', text: 'Mua sắm thưởng bản thân', tags: ['short_term'],
        immediate: { wealth: -150, happiness: 12 }, flags: ['impulse_spending'] },
      { id: 'B', text: 'Gửi tiết kiệm', tags: ['long_term', 'risk_low'],
        immediate: { wealth: 30, happiness: 3 },
        delayed: [{ days: 50, effects: { wealth: 25 }, message: 'Tiền tiết kiệm tích lũy tạo nền tảng vững chắc.', traceChoice: 'Gửi tiết kiệm' }] },
      { id: 'C', text: 'Trả nợ trước hạn', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -100, happiness: 8 },
        delayed: [{ days: 40, effects: { wealth: 15, happiness: 5 }, message: 'Giảm nợ giúp bạn nhẹ nhõm hơn.', traceChoice: 'Trả nợ' }] },
      { id: 'D', text: 'Tặng quà cho người thân', tags: ['relationship', 'short_term'],
        immediate: { wealth: -80, relationships: 15, happiness: 8 } }
    ]
  },
  {
    id: 'fin_004', category: 'finance', subcategory: 'nợ',
    text: 'Bạn được mời mở thẻ tín dụng với hạn mức cao.',
    choices: [
      { id: 'A', text: 'Mở thẻ và chi tiêu thoải mái', tags: ['short_term', 'risk_high'],
        immediate: { happiness: 15, wealth: 30 },
        delayed: [{ days: 35, effects: { wealth: -40, happiness: -10 }, message: 'Nợ tín dụng tích lũy gây áp lực.', traceChoice: 'Chi tiêu thẻ tín dụng' }],
        flags: ['impulse_spending'] },
      { id: 'B', text: 'Mở thẻ chỉ dùng khẩn cấp', tags: ['long_term', 'risk_low'],
        immediate: { happiness: 3 },
        delayed: [{ days: 60, effects: { wealth: 10 }, message: 'Thẻ dự phòng giúp bạn vượt qua khó khăn.', traceChoice: 'Thẻ khẩn cấp' }] },
      { id: 'C', text: 'Không mở thẻ', tags: ['risk_low', 'long_term'],
        immediate: { happiness: -2, wealth: 5 } },
      { id: 'D', text: 'Tìm hiểu cách quản lý tín dụng', tags: ['learning', 'long_term'],
        immediate: { knowledge: 12, wealth: -5 } }
    ]
  },
  {
    id: 'fin_005', category: 'finance', subcategory: 'tiêu dùng',
    text: 'Sale lớn cuối năm. Bạn thấy nhiều món đồ hấp dẫn.',
    choices: [
      { id: 'A', text: 'Mua ngay những gì thích', tags: ['short_term', 'risk_low'],
        immediate: { wealth: -120, happiness: 18 }, flags: ['impulse_spending'] },
      { id: 'B', text: 'Lập danh sách cần thiết trước', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -60, happiness: 8, knowledge: 3 } },
      { id: 'C', text: 'Bỏ qua sale', tags: ['long_term', 'risk_low'],
        immediate: { wealth: 20, happiness: -5 },
        delayed: [{ days: 30, effects: { wealth: 15 }, message: 'Tiền không chi tiêu bốc đồng vẫn còn đó.', traceChoice: 'Bỏ qua sale' }] },
      { id: 'D', text: 'Mua quà cho người khác', tags: ['relationship'],
        immediate: { wealth: -80, relationships: 18, happiness: 10 } }
    ]
  },
  {
    id: 'fin_006', category: 'finance', subcategory: 'đầu tư',
    text: 'Công ty đề xuất mua cổ phiếu nhân viên với giá ưu đãi.',
    choices: [
      { id: 'A', text: 'Mua nhiều nhất có thể', tags: ['risk_high', 'long_term'],
        immediate: { wealth: -60 },
        delayed: [{ days: 50, effects: { wealth: 50 }, message: 'Cổ phiếu công ty tăng giá trị.', traceChoice: 'Mua cổ phiếu' }] },
      { id: 'B', text: 'Mua một phần vừa phải', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -30, knowledge: 5 } },
      { id: 'C', text: 'Từ chối, giữ tiền mặt', tags: ['risk_low'],
        immediate: { wealth: 10, happiness: 3 } },
      { id: 'D', text: 'Nghiên cứu báo cáo tài chính trước', tags: ['learning', 'long_term'],
        immediate: { knowledge: 15, energy: -5 } }
    ]
  },
  {
    id: 'fin_007', category: 'finance', subcategory: 'tiết kiệm',
    text: 'Bạn nhận được khoản thưởng bất ngờ 1000$.',
    choices: [
      { id: 'A', text: 'Du lịch ngay', tags: ['short_term'],
        immediate: { wealth: -800, happiness: 25, energy: 15 } },
      { id: 'B', text: 'Đầu tư dài hạn', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -500, knowledge: 8 },
        delayed: [{ days: 70, effects: { wealth: 80 }, message: 'Đầu tư dài hạn sinh lời.', traceChoice: 'Đầu tư dài hạn' }] },
      { id: 'C', text: 'Trả hết nợ', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -600, happiness: 15 },
        delayed: [{ days: 45, effects: { happiness: 10 }, message: 'Không nợ giúp bạn ngủ ngon hơn.', traceChoice: 'Trả hết nợ' }] },
      { id: 'D', text: 'Chia: tiết kiệm, đầu tư, thưởng bản thân', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -200, happiness: 12, knowledge: 5 } }
    ]
  },
  {
    id: 'fin_008', category: 'finance', subcategory: 'nợ',
    text: 'Bạn cần tiền gấp cho việc quan trọng. Có người cho vay với lãi suất cao.',
    choices: [
      { id: 'A', text: 'Vay ngay', tags: ['short_term', 'risk_high'],
        immediate: { wealth: 100, happiness: 10 },
        delayed: [{ days: 25, effects: { wealth: -80, happiness: -15 }, message: 'Lãi suất cao gây áp lực tài chính.', traceChoice: 'Vay lãi cao' }] },
      { id: 'B', text: 'Vay người thân', tags: ['relationship', 'risk_low'],
        immediate: { wealth: 80, relationships: -5 },
        delayed: [{ days: 40, effects: { relationships: 10 }, message: 'Bạn đã trả nợ đúng hạn, quan hệ được củng cố.', traceChoice: 'Vay người thân' }] },
      { id: 'C', text: 'Hoãn việc, tiết kiệm thêm', tags: ['long_term', 'avoidance'],
        immediate: { happiness: -8, wealth: 10 },
        flags: ['avoided_learning'] },
      { id: 'D', text: 'Tìm nguồn thu nhập phụ', tags: ['long_term', 'learning'],
        immediate: { energy: -15, knowledge: 10 },
        delayed: [{ days: 35, effects: { wealth: 60 }, message: 'Thu nhập phụ giúp giải quyết vấn đề.', traceChoice: 'Thu nhập phụ' }] }
    ]
  },
  {
    id: 'fin_009', category: 'finance', subcategory: 'tiêu dùng',
    text: 'Đồng nghiệp mời bạn ăn trưa ở nhà hàng đắt tiền.',
    choices: [
      { id: 'A', text: 'Đi cùng, chi trả phần mình', tags: ['relationship', 'short_term'],
        immediate: { wealth: -50, relationships: 10, happiness: 8 } },
      { id: 'B', text: 'Đề xuất quán rẻ hơn', tags: ['long_term', 'relationship'],
        immediate: { wealth: -20, relationships: 5, happiness: 5 } },
      { id: 'C', text: 'Từ chối lịch sự', tags: ['avoidance', 'risk_low'],
        immediate: { relationships: -5, wealth: 5 } },
      { id: 'D', text: 'Đi nhưng đặt giới hạn chi tiêu', tags: ['long_term', 'relationship'],
        immediate: { wealth: -30, relationships: 8, knowledge: 3 } }
    ]
  },
  {
    id: 'fin_010', category: 'finance', subcategory: 'đầu tư',
    text: 'Bạn nghe podcast về đầu tư bất động sản.',
    choices: [
      { id: 'A', text: 'Bắt đầu tìm mua ngay', tags: ['risk_high', 'short_term'],
        immediate: { wealth: -50, knowledge: 5 },
        delayed: [{ days: 55, effects: { wealth: 30 }, message: 'Thị trường bất động sản có biến động.', traceChoice: 'Tìm mua BĐS' }] },
      { id: 'B', text: 'Học thêm 6 tháng rồi quyết định', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, energy: -5 } },
      { id: 'C', text: 'Bỏ qua, không quan tâm', tags: ['avoidance'],
        immediate: { knowledge: -3 } },
      { id: 'D', text: 'Tham gia nhóm đầu tư nhỏ', tags: ['long_term', 'learning', 'risk_low'],
        immediate: { knowledge: 12, relationships: 5, wealth: -20 } }
    ]
  },
  {
    id: 'fin_011', category: 'finance', subcategory: 'tiết kiệm',
    text: 'Giá sinh hoạt tăng. Thu nhập không đổi.',
    choices: [
      { id: 'A', text: 'Cắt giảm chi tiêu giải trí', tags: ['long_term', 'risk_low'],
        immediate: { happiness: -10, wealth: 15 } },
      { id: 'B', text: 'Giữ nguyên lối sống, dùng tiết kiệm', tags: ['short_term'],
        immediate: { wealth: -20, happiness: 5 },
        delayed: [{ days: 40, effects: { wealth: -25 }, message: 'Tiết kiệm cạn kiệt do chi tiêu không điều chỉnh.', traceChoice: 'Dùng tiết kiệm' }] },
      { id: 'C', text: 'Tìm cách tăng thu nhập', tags: ['long_term', 'learning'],
        immediate: { energy: -10, knowledge: 8 },
        delayed: [{ days: 45, effects: { wealth: 40 }, message: 'Nỗ lực tăng thu nhập có kết quả.', traceChoice: 'Tăng thu nhập' }] },
      { id: 'D', text: 'Nhờ gia đình hỗ trợ', tags: ['relationship', 'short_term'],
        immediate: { relationships: -8, wealth: 30, happiness: -5 } }
    ]
  },
  {
    id: 'fin_012', category: 'finance', subcategory: 'nợ',
    text: 'Bạn phát hiện mình chi tiêu vượt ngân sách 3 tháng liên tiếp.',
    choices: [
      { id: 'A', text: 'Lập ngân sách chi tiết', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, energy: -5 },
        delayed: [{ days: 30, effects: { wealth: 20 }, message: 'Ngân sách giúp kiểm soát chi tiêu.', traceChoice: 'Lập ngân sách' }] },
      { id: 'B', text: 'Bỏ qua, tháng sau sẽ khác', tags: ['avoidance', 'short_term'],
        immediate: { happiness: 5 },
        delayed: [{ days: 25, effects: { wealth: -30 }, message: 'Chi tiêu không kiểm soát tiếp tục.', traceChoice: 'Bỏ qua ngân sách' }],
        flags: ['impulse_spending'] },
      { id: 'C', text: 'Dùng app theo dõi chi tiêu', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, wealth: 5 } },
      { id: 'D', text: 'Chia sẻ với bạn bè để cùng kiểm soát', tags: ['relationship', 'long_term'],
        immediate: { relationships: 10, knowledge: 5 } }
    ]
  },

  // === SỨC KHỎE (12) ===
  {
    id: 'hea_001', category: 'health', subcategory: 'tập luyện',
    text: 'Sáng nay bạn rất mệt. Lịch tập gym đang chờ.',
    choices: [
      { id: 'A', text: 'Vẫn đi tập', tags: ['long_term', 'risk_low'],
        immediate: { health: 10, energy: -5, happiness: 5 } },
      { id: 'B', text: 'Bỏ tập, nghỉ ngơi', tags: ['short_term', 'avoidance'],
        immediate: { energy: 10, health: -3 },
        flags: ['skipped_exercise'] },
      { id: 'C', text: 'Tập nhẹ tại nhà', tags: ['long_term'],
        immediate: { health: 5, energy: 5 } },
      { id: 'D', text: 'Đi dạo nhẹ 15 phút', tags: ['long_term', 'risk_low'],
        immediate: { health: 5, happiness: 5, energy: 3 } }
    ]
  },
  {
    id: 'hea_002', category: 'health', subcategory: 'ăn uống',
    text: 'Bạn đói và thấy quán fast food gần đó.',
    choices: [
      { id: 'A', text: 'Ăn fast food', tags: ['short_term'],
        immediate: { happiness: 10, health: -8, wealth: -15 } },
      { id: 'B', text: 'Nấu bữa ăn lành mạnh', tags: ['long_term'],
        immediate: { health: 8, energy: -5, happiness: 3 } },
      { id: 'C', text: 'Ăn nhẹ healthy snack', tags: ['long_term', 'risk_low'],
        immediate: { health: 3, wealth: -5 } },
      { id: 'D', text: 'Nhịn đến bữa chính', tags: ['short_term', 'avoidance'],
        immediate: { energy: -10, health: -5 } }
    ]
  },
  {
    id: 'hea_003', category: 'health', subcategory: 'ngủ nghỉ',
    text: 'Đêm khuya, bạn vẫn còn việc chưa xong.',
    choices: [
      { id: 'A', text: 'Thức khuya hoàn thành', tags: ['short_term'],
        immediate: { knowledge: 5, energy: -15, health: -8 },
        flags: ['poor_sleep'] },
      { id: 'B', text: 'Ngủ đủ giấc, làm sáng mai', tags: ['long_term'],
        immediate: { energy: 10, health: 8, happiness: 5 } },
      { id: 'C', text: 'Làm thêm 1 giờ rồi ngủ', tags: ['long_term'],
        immediate: { knowledge: 3, energy: -8, health: -3 } },
      { id: 'D', text: 'Nhờ đồng nghiệp hỗ trợ', tags: ['relationship'],
        immediate: { relationships: 8, energy: 5 } }
    ]
  },
  {
    id: 'hea_004', category: 'health', subcategory: 'stress',
    text: 'Áp lực công việc khiến bạn căng thẳng suốt tuần.',
    choices: [
      { id: 'A', text: 'Làm việc liên tục để kịp deadline', tags: ['short_term'],
        immediate: { wealth: 10, energy: -20, health: -10, happiness: -8 } },
      { id: 'B', text: 'Nghỉ 1 ngày để phục hồi', tags: ['long_term', 'risk_low'],
        immediate: { energy: 15, health: 10, wealth: -5, happiness: 10 } },
      { id: 'C', text: 'Thiền và tập thở 15 phút/ngày', tags: ['long_term', 'learning'],
        immediate: { health: 8, happiness: 8, energy: 5 } },
      { id: 'D', text: 'Trò chuyện với bạn thân', tags: ['relationship'],
        immediate: { relationships: 12, happiness: 10, health: 5 } }
    ]
  },
  {
    id: 'hea_005', category: 'health', subcategory: 'tập luyện',
    text: 'Bạn được mời tham gia giải chạy bộ cộng đồng.',
    choices: [
      { id: 'A', text: 'Tham gia và luyện tập', tags: ['long_term', 'relationship'],
        immediate: { health: 12, energy: -10, relationships: 8, happiness: 10 } },
      { id: 'B', text: 'Đến xem cổ vũ', tags: ['relationship', 'short_term'],
        immediate: { relationships: 5, happiness: 5 } },
      { id: 'C', text: 'Từ chối vì bận', tags: ['avoidance'],
        immediate: { relationships: -3 },
        flags: ['skipped_exercise'] },
      { id: 'D', text: 'Đăng ký nhưng tập một mình', tags: ['long_term'],
        immediate: { health: 8, happiness: 5 } }
    ]
  },
  {
    id: 'hea_006', category: 'health', subcategory: 'ăn uống',
    text: 'Bạn phát hiện mình uống quá nhiều cà phê.',
    choices: [
      { id: 'A', text: 'Tiếp tục như cũ', tags: ['short_term', 'avoidance'],
        immediate: { energy: 5, health: -5 },
        delayed: [{ days: 30, effects: { health: -10, energy: -8 }, message: 'Quá nhiều caffeine ảnh hưởng sức khỏe.', traceChoice: 'Tiếp tục uống cà phê' }] },
      { id: 'B', text: 'Giảm dần, thay bằng trà', tags: ['long_term'],
        immediate: { health: 8, energy: -3 } },
      { id: 'C', text: 'Cắt hoàn toàn ngay lập tức', tags: ['short_term'],
        immediate: { health: 5, energy: -15, happiness: -8 } },
      { id: 'D', text: 'Tìm hiểu về dinh dưỡng', tags: ['learning', 'long_term'],
        immediate: { knowledge: 12, health: 5 } }
    ]
  },
  {
    id: 'hea_007', category: 'health', subcategory: 'ngủ nghỉ',
    text: 'Cuối tuần bạn có thể ngủ nướng hoặc dậy sớm làm việc cá nhân.',
    choices: [
      { id: 'A', text: 'Ngủ nướng đến trưa', tags: ['short_term'],
        immediate: { energy: 15, happiness: 10, health: -3 } },
      { id: 'B', text: 'Dậy sớm, tận dụng buổi sáng', tags: ['long_term'],
        immediate: { energy: 10, knowledge: 8, happiness: 5 } },
      { id: 'C', text: 'Cân bằng: ngủ thêm 1-2 giờ', tags: ['long_term', 'risk_low'],
        immediate: { energy: 12, health: 5, happiness: 5 } },
      { id: 'D', text: 'Dậy sớm đi chơi với bạn', tags: ['relationship', 'short_term'],
        immediate: { relationships: 12, energy: 5, happiness: 10 } }
    ]
  },
  {
    id: 'hea_008', category: 'health', subcategory: 'stress',
    text: 'Tin tức tiêu cực khiến bạn lo lắng cả ngày.',
    choices: [
      { id: 'A', text: 'Tiếp tục lướt tin tức', tags: ['short_term', 'avoidance'],
        immediate: { happiness: -12, health: -5, energy: -5 } },
      { id: 'B', text: 'Tắt mạng xã hội 1 ngày', tags: ['long_term'],
        immediate: { happiness: 10, health: 5, energy: 8 } },
      { id: 'C', text: 'Chia sẻ lo lắng với người thân', tags: ['relationship'],
        immediate: { relationships: 8, happiness: 5 } },
      { id: 'D', text: 'Tập trung vào việc mình kiểm soát được', tags: ['long_term', 'learning'],
        immediate: { knowledge: 5, happiness: 8, energy: 5 } }
    ]
  },
  {
    id: 'hea_009', category: 'health', subcategory: 'tập luyện',
    text: 'Phòng gym tăng giá. Bạn vẫn muốn tập.',
    choices: [
      { id: 'A', text: 'Trả giá mới', tags: ['long_term'],
        immediate: { wealth: -30, health: 5 } },
      { id: 'B', text: 'Tập tại nhà', tags: ['long_term', 'risk_low'],
        immediate: { health: 8, knowledge: 5 } },
      { id: 'C', text: 'Bỏ tập gym', tags: ['avoidance', 'short_term'],
        immediate: { wealth: 15, health: -5 },
        flags: ['skipped_exercise'] },
      { id: 'D', text: 'Tìm bạn cùng tập ngoài trời', tags: ['relationship', 'long_term'],
        immediate: { health: 10, relationships: 10, happiness: 8 } }
    ]
  },
  {
    id: 'hea_010', category: 'health', subcategory: 'ăn uống',
    text: 'Bạn được mời tiệc buffet với đồ ăn rất nhiều.',
    choices: [
      { id: 'A', text: 'Ăn thả ga', tags: ['short_term'],
        immediate: { happiness: 15, health: -10 } },
      { id: 'B', text: 'Ăn vừa phải, chọn món healthy', tags: ['long_term'],
        immediate: { happiness: 8, health: 3, relationships: 5 } },
      { id: 'C', text: 'Không đi', tags: ['avoidance'],
        immediate: { relationships: -5, health: 3 } },
      { id: 'D', text: 'Đi nhưng ăn chậm, tận hưởng', tags: ['long_term', 'relationship'],
        immediate: { happiness: 10, relationships: 8, health: -3 } }
    ]
  },
  {
    id: 'hea_011', category: 'health', subcategory: 'ngủ nghỉ',
    text: 'Bạn thường xuyên thức dậy giữa đêm.',
    choices: [
      { id: 'A', text: 'Lướt điện thoại cho đến khi buồn ngủ', tags: ['short_term'],
        immediate: { happiness: 3, health: -8, energy: -5 },
        flags: ['poor_sleep'] },
      { id: 'B', text: 'Thiết lập routine ngủ mới', tags: ['long_term', 'learning'],
        immediate: { health: 10, knowledge: 5, energy: 5 } },
      { id: 'C', text: 'Bỏ qua, sẽ tự khỏi', tags: ['avoidance'],
        immediate: {},
        delayed: [{ days: 35, effects: { health: -12, energy: -10 }, message: 'Mất ngủ kéo dài ảnh hưởng sức khỏe.', traceChoice: 'Bỏ qua mất ngủ' }] },
      { id: 'D', text: 'Đi khám bác sĩ', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -20, health: 12, knowledge: 5 } }
    ]
  },
  {
    id: 'hea_012', category: 'health', subcategory: 'stress',
    text: 'Bạn cảm thấy kiệt sức nhưng không muốn nghỉ phép.',
    choices: [
      { id: 'A', text: 'Cố gắng tiếp tục', tags: ['short_term', 'avoidance'],
        immediate: { wealth: 5, energy: -20, health: -12, happiness: -10 } },
      { id: 'B', text: 'Xin nghỉ phép 2 ngày', tags: ['long_term'],
        immediate: { energy: 20, health: 15, happiness: 12, wealth: -10 } },
      { id: 'C', text: 'Giảm tải công việc không cần thiết', tags: ['long_term', 'learning'],
        immediate: { energy: 10, knowledge: 5 } },
      { id: 'D', text: 'Nói chuyện với sếp về workload', tags: ['relationship', 'long_term'],
        immediate: { relationships: 5, energy: 8, happiness: 5 } }
    ]
  },

  // === QUAN HỆ (10) ===
  {
    id: 'rel_001', category: 'relationships', subcategory: 'gia đình',
    text: 'Bố mẹ gọi hỏi thăm nhưng bạn đang bận.',
    choices: [
      { id: 'A', text: 'Gọi lại ngay, trò chuyện 30 phút', tags: ['relationship', 'long_term'],
        immediate: { relationships: 15, happiness: 10, energy: -5 } },
      { id: 'B', text: 'Nhắn tin "bận, gọi sau"', tags: ['short_term'],
        immediate: { relationships: 3 } },
      { id: 'C', text: 'Bỏ qua, quên mất', tags: ['avoidance'],
        immediate: { relationships: -10, happiness: -5 },
        delayed: [{ days: 20, effects: { relationships: -8 }, message: 'Bố mẹ cảm thấy bạn xa cách hơn.', traceChoice: 'Bỏ qua gọi bố mẹ' }] },
      { id: 'D', text: 'Hẹn cuối tuần về thăm', tags: ['relationship', 'long_term'],
        immediate: { relationships: 12, happiness: 8, wealth: -20 } }
    ]
  },
  {
    id: 'rel_002', category: 'relationships', subcategory: 'bạn bè',
    text: 'Bạn thân mời bạn đi chơi cuối tuần.',
    choices: [
      { id: 'A', text: 'Đồng ý ngay', tags: ['relationship', 'short_term'],
        immediate: { relationships: 15, happiness: 15, wealth: -30, energy: -5 } },
      { id: 'B', text: 'Hẹn tuần sau vì cần nghỉ', tags: ['long_term'],
        immediate: { relationships: 5, energy: 10 } },
      { id: 'C', text: 'Từ chối vì muốn ở nhà một mình', tags: ['avoidance'],
        immediate: { relationships: -8, happiness: 5, energy: 10 } },
      { id: 'D', text: 'Đề xuất hoạt động ít tốn kém', tags: ['relationship', 'long_term'],
        immediate: { relationships: 12, happiness: 10, wealth: -10 } }
    ]
  },
  {
    id: 'rel_003', category: 'relationships', subcategory: 'đồng nghiệp',
    text: 'Đồng nghiệp nhờ bạn giúp việc ngoài giờ.',
    choices: [
      { id: 'A', text: 'Giúp ngay', tags: ['relationship', 'short_term'],
        immediate: { relationships: 12, energy: -15, happiness: 5 } },
      { id: 'B', text: 'Từ chối lịch sự', tags: ['long_term', 'risk_low'],
        immediate: { relationships: -3, energy: 10, happiness: 5 } },
      { id: 'C', text: 'Giúp nhưng đặt giới hạn thời gian', tags: ['long_term', 'relationship'],
        immediate: { relationships: 8, energy: -8, knowledge: 3 } },
      { id: 'D', text: 'Đề xuất giúp vào ngày mai', tags: ['long_term'],
        immediate: { relationships: 5, energy: 5 } }
    ]
  },
  {
    id: 'rel_004', category: 'relationships', subcategory: 'gia đình',
    text: 'Họ hàng mời dự tiệc cưới xa, tốn kém.',
    choices: [
      { id: 'A', text: 'Tham dự đầy đủ', tags: ['relationship', 'short_term'],
        immediate: { relationships: 20, wealth: -80, happiness: 10, energy: -10 } },
      { id: 'B', text: 'Gửi quà, không đi', tags: ['long_term'],
        immediate: { relationships: 8, wealth: -40, happiness: 3 } },
      { id: 'C', text: 'Không tham dự, không gửi quà', tags: ['avoidance'],
        immediate: { relationships: -15, wealth: 10 } },
      { id: 'D', text: 'Đi một mình thay vì cả gia đình', tags: ['long_term', 'relationship'],
        immediate: { relationships: 12, wealth: -40, happiness: 5 } }
    ]
  },
  {
    id: 'rel_005', category: 'relationships', subcategory: 'bạn bè',
    text: 'Bạn thân chia sẻ vấn đề cá nhân và cần lắng nghe.',
    choices: [
      { id: 'A', text: 'Lắng nghe tận tình', tags: ['relationship', 'long_term'],
        immediate: { relationships: 18, happiness: 8, energy: -8 } },
      { id: 'B', text: 'Đưa lời khuyên nhanh', tags: ['short_term'],
        immediate: { relationships: 5, knowledge: 3 } },
      { id: 'C', text: 'Nói bận, hẹn lúc khác', tags: ['avoidance'],
        immediate: { relationships: -10, energy: 5 } },
      { id: 'D', text: 'Mời gặp trực tiếp uống cà phê', tags: ['relationship', 'long_term'],
        immediate: { relationships: 15, wealth: -15, happiness: 10 } }
    ]
  },
  {
    id: 'rel_006', category: 'relationships', subcategory: 'đồng nghiệp',
    text: 'Có xung đột ý kiến trong cuộc họp nhóm.',
    choices: [
      { id: 'A', text: 'Tranh luận mạnh để thắng', tags: ['short_term', 'risk_high'],
        immediate: { relationships: -10, happiness: -5, knowledge: 3 } },
      { id: 'B', text: 'Lắng nghe và tìm điểm chung', tags: ['relationship', 'long_term'],
        immediate: { relationships: 10, knowledge: 5, happiness: 5 } },
      { id: 'C', text: 'Im lặng, tránh xung đột', tags: ['avoidance'],
        immediate: { relationships: -3, happiness: -3 } },
      { id: 'D', text: 'Đề xuất họp riêng giải quyết', tags: ['long_term', 'relationship'],
        immediate: { relationships: 8, knowledge: 5, energy: -5 } }
    ]
  },
  {
    id: 'rel_007', category: 'relationships', subcategory: 'gia đình',
    text: 'Anh/chị em tranh cãi về việc chia tài sản thừa kế.',
    choices: [
      { id: 'A', text: 'Đứng về phía một bên', tags: ['short_term', 'relationship'],
        immediate: { relationships: -5, happiness: -8 } },
      { id: 'B', text: 'Làm trung gian hòa giải', tags: ['long_term', 'relationship'],
        immediate: { relationships: 10, energy: -10, happiness: 5 } },
      { id: 'C', text: 'Tránh không tham gia', tags: ['avoidance'],
        immediate: { relationships: -8, happiness: 3 } },
      { id: 'D', text: 'Đề xuất thuê luật sư trung lập', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, wealth: -30, relationships: 5 } }
    ]
  },
  {
    id: 'rel_008', category: 'relationships', subcategory: 'bạn bè',
    text: 'Nhóm bạn lập kế hoạch du lịch chung.',
    choices: [
      { id: 'A', text: 'Tham gia ngay', tags: ['relationship', 'short_term'],
        immediate: { relationships: 15, wealth: -100, happiness: 20, energy: 10 } },
      { id: 'B', text: 'Tham gia nhưng đặt ngân sách', tags: ['long_term', 'relationship'],
        immediate: { relationships: 12, wealth: -60, happiness: 15 } },
      { id: 'C', text: 'Từ chối vì không đủ tiền', tags: ['avoidance', 'risk_low'],
        immediate: { relationships: -8, happiness: -5, wealth: 5 } },
      { id: 'D', text: 'Đề xuất chuyến đi gần, rẻ hơn', tags: ['long_term', 'relationship'],
        immediate: { relationships: 10, wealth: -40, happiness: 12 } }
    ]
  },
  {
    id: 'rel_009', category: 'relationships', subcategory: 'đồng nghiệp',
    text: 'Bạn được mời tham gia dự án thú vị nhưng tốn nhiều thời gian.',
    choices: [
      { id: 'A', text: 'Tham gia hết mình', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, relationships: 12, energy: -15 } },
      { id: 'B', text: 'Tham gia với vai trò nhỏ', tags: ['long_term', 'risk_low'],
        immediate: { knowledge: 8, relationships: 8, energy: -8 } },
      { id: 'C', text: 'Từ chối để tập trung công việc chính', tags: ['avoidance', 'long_term'],
        immediate: { relationships: -5, energy: 10 } },
      { id: 'D', text: 'Tham gia nhưng đặt deadline rõ ràng', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, relationships: 10, energy: -10 } }
    ]
  },
  {
    id: 'rel_010', category: 'relationships', subcategory: 'gia đình',
    text: 'Con bạn cần bạn tham gia hoạt động ở trường.',
    choices: [
      { id: 'A', text: 'Sắp xếp tham gia', tags: ['relationship', 'long_term'],
        immediate: { relationships: 20, happiness: 15, energy: -10, wealth: -10 } },
      { id: 'B', text: 'Nhờ người khác thay', tags: ['short_term'],
        immediate: { relationships: -5, energy: 5 } },
      { id: 'C', text: 'Hứa tham gia lần sau', tags: ['avoidance'],
        immediate: { relationships: -8, happiness: -5 } },
      { id: 'D', text: 'Tham gia một phần thời gian', tags: ['long_term', 'relationship'],
        immediate: { relationships: 12, happiness: 10, energy: -5 } }
    ]
  },

  // === HỌC TẬP (10) ===
  {
    id: 'lea_001', category: 'learning', subcategory: 'đọc sách',
    text: 'Bạn có 1 giờ rảnh buổi tối.',
    choices: [
      { id: 'A', text: 'Đọc sách phát triển bản thân', tags: ['long_term', 'learning'],
        immediate: { knowledge: 12, happiness: 5 } },
      { id: 'B', text: 'Xem phim/series', tags: ['short_term'],
        immediate: { happiness: 12, energy: -3 } },
      { id: 'C', text: 'Lướt mạng xã hội', tags: ['short_term', 'avoidance'],
        immediate: { happiness: 5, energy: -5, knowledge: -3 } },
      { id: 'D', text: 'Gọi điện trò chuyện với bạn', tags: ['relationship'],
        immediate: { relationships: 10, happiness: 8 } }
    ]
  },
  {
    id: 'lea_002', category: 'learning', subcategory: 'học kỹ năng',
    text: 'Khóa học online giảm giá 50% về kỹ năng bạn quan tâm.',
    choices: [
      { id: 'A', text: 'Đăng ký ngay', tags: ['long_term', 'learning'],
        immediate: { wealth: -50, knowledge: 15, energy: -5 } },
      { id: 'B', text: 'Thêm vào wishlist, suy nghĩ thêm', tags: ['long_term', 'risk_low'],
        immediate: { knowledge: 3 } },
      { id: 'C', text: 'Bỏ qua', tags: ['avoidance'],
        immediate: {},
        flags: ['avoided_learning'] },
      { id: 'D', text: 'Tìm tài liệu miễn phí thay thế', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, energy: -8 } }
    ]
  },
  {
    id: 'lea_003', category: 'learning', subcategory: 'xây dựng dự án',
    text: 'Bạn có ý tưởng side project nhưng chưa chắc sẽ thành công.',
    choices: [
      { id: 'A', text: 'Bắt đầu ngay tối nay', tags: ['long_term', 'learning', 'risk_high'],
        immediate: { knowledge: 10, energy: -15, happiness: 8 } },
      { id: 'B', text: 'Lập kế hoạch chi tiết trước', tags: ['long_term', 'learning'],
        immediate: { knowledge: 12, energy: -5 } },
      { id: 'C', text: 'Chờ đợi thời điểm thích hợp hơn', tags: ['avoidance'],
        immediate: { happiness: -3 },
        flags: ['avoided_learning'] },
      { id: 'D', text: 'Tìm partner cùng làm', tags: ['long_term', 'relationship', 'learning'],
        immediate: { knowledge: 8, relationships: 10, energy: -10 } }
    ]
  },
  {
    id: 'lea_004', category: 'learning', subcategory: 'đọc sách',
    text: 'Thư viện gần nhà mở cửa miễn phí cuối tuần.',
    choices: [
      { id: 'A', text: 'Đến mượn 3 cuốn sách', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, happiness: 8 } },
      { id: 'B', text: 'Đến ngồi đọc tại chỗ', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, happiness: 5, energy: 5 } },
      { id: 'C', text: 'Không đi, ở nhà nghỉ', tags: ['avoidance', 'short_term'],
        immediate: { energy: 10, happiness: 5 } },
      { id: 'D', text: 'Mời bạn cùng đi', tags: ['relationship', 'learning'],
        immediate: { knowledge: 8, relationships: 10, happiness: 10 } }
    ]
  },
  {
    id: 'lea_005', category: 'learning', subcategory: 'học kỹ năng',
    text: 'Công ty tổ chức workshop kỹ năng mềm.',
    choices: [
      { id: 'A', text: 'Đăng ký tham gia', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, relationships: 8, energy: -8 } },
      { id: 'B', text: 'Xin nghỉ để làm việc riêng', tags: ['short_term'],
        immediate: { wealth: 5, energy: 5, relationships: -3 } },
      { id: 'C', text: 'Tham gia online từ xa', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, energy: -3 } },
      { id: 'D', text: 'Ghi chú từ đồng nghiệp tham gia', tags: ['relationship', 'learning'],
        immediate: { knowledge: 5, relationships: 5 } }
    ]
  },
  {
    id: 'lea_006', category: 'learning', subcategory: 'xây dựng dự án',
    text: 'Bạn hoàn thành 70% dự án cá nhân nhưng gặp khó khăn.',
    choices: [
      { id: 'A', text: 'Tiếp tục cố gắng hoàn thành', tags: ['long_term', 'learning'],
        immediate: { knowledge: 12, energy: -15, happiness: 5 } },
      { id: 'B', text: 'Tạm dừng, học thêm kiến thức', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, energy: -5 } },
      { id: 'C', text: 'Bỏ dự án', tags: ['avoidance', 'short_term'],
        immediate: { happiness: -10, energy: 10 },
        flags: ['avoided_learning'] },
      { id: 'D', text: 'Nhờ mentor tư vấn', tags: ['long_term', 'learning', 'relationship'],
        immediate: { knowledge: 18, relationships: 8, wealth: -20 } }
    ]
  },
  {
    id: 'lea_007', category: 'learning', subcategory: 'đọc sách',
    text: 'Podcast về tài chính cá nhân rất hay.',
    choices: [
      { id: 'A', text: 'Nghe hết series', tags: ['long_term', 'learning'],
        immediate: { knowledge: 12, wealth: 5 } },
      { id: 'B', text: 'Nghe khi làm việc nhà', tags: ['long_term', 'learning'],
        immediate: { knowledge: 8, energy: -3 } },
      { id: 'C', text: 'Lưu lại, chưa có thời gian', tags: ['avoidance'],
        immediate: {},
        flags: ['avoided_learning'] },
      { id: 'D', text: 'Chia sẻ với bạn bè', tags: ['relationship', 'learning'],
        immediate: { knowledge: 5, relationships: 8 } }
    ]
  },
  {
    id: 'lea_008', category: 'learning', subcategory: 'học kỹ năng',
    text: 'Bạn muốn học ngoại ngữ mới.',
    choices: [
      { id: 'A', text: 'Đăng ký lớp có giáo viên', tags: ['long_term', 'learning'],
        immediate: { wealth: -80, knowledge: 15, energy: -10 } },
      { id: 'B', text: 'Học qua app miễn phí', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, energy: -8 } },
      { id: 'C', text: 'Hoãn lại, chưa cần thiết', tags: ['avoidance'],
        immediate: { happiness: 3 },
        flags: ['avoided_learning'] },
      { id: 'D', text: 'Tìm bạn trao đổi ngôn ngữ', tags: ['long_term', 'learning', 'relationship'],
        immediate: { knowledge: 12, relationships: 10, happiness: 8 } }
    ]
  },
  {
    id: 'lea_009', category: 'learning', subcategory: 'xây dựng dự án',
    text: 'Hackathon cuối tuần với giải thưởng hấp dẫn.',
    choices: [
      { id: 'A', text: 'Tham gia solo', tags: ['long_term', 'learning', 'risk_high'],
        immediate: { knowledge: 20, energy: -25, happiness: 10 } },
      { id: 'B', text: 'Lập team với bạn', tags: ['long_term', 'learning', 'relationship'],
        immediate: { knowledge: 15, relationships: 12, energy: -20 } },
      { id: 'C', text: 'Không tham gia, nghỉ ngơi', tags: ['avoidance', 'short_term'],
        immediate: { energy: 15, happiness: 5 } },
      { id: 'D', text: 'Đến xem và học hỏi', tags: ['learning', 'long_term'],
        immediate: { knowledge: 10, relationships: 5 } }
    ]
  },
  {
    id: 'lea_010', category: 'learning', subcategory: 'đọc sách',
    text: 'Sách bạn đọc dở có phần khó hiểu.',
    choices: [
      { id: 'A', text: 'Đọc lại phần đó kỹ hơn', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, energy: -5 } },
      { id: 'B', text: 'Bỏ qua, đọc tiếp', tags: ['short_term', 'avoidance'],
        immediate: { knowledge: 3 },
        flags: ['avoided_learning'] },
      { id: 'C', text: 'Tìm video giải thích', tags: ['long_term', 'learning'],
        immediate: { knowledge: 12, energy: -3 } },
      { id: 'D', text: 'Thảo luận với người đã đọc', tags: ['relationship', 'learning'],
        immediate: { knowledge: 15, relationships: 8 } }
    ]
  },

  // === KHỦNG HOẢNG (6) ===
  {
    id: 'cri_001', category: 'crisis', subcategory: 'mất việc',
    text: 'Công ty thông báo cắt giảm nhân sự. Bạn có thể bị ảnh hưởng.',
    choices: [
      { id: 'A', text: 'Cập nhật CV và tìm việc ngay', tags: ['long_term', 'learning'],
        immediate: { energy: -15, knowledge: 10, happiness: -5 } },
      { id: 'B', text: 'Chờ đợi, hy vọng không bị ảnh hưởng', tags: ['avoidance', 'short_term'],
        immediate: { happiness: -10, energy: -5 } },
      { id: 'C', text: 'Nói chuyện với sếp về tình hình', tags: ['relationship', 'long_term'],
        immediate: { relationships: 5, knowledge: 5, happiness: -3 } },
      { id: 'D', text: 'Học thêm kỹ năng để tăng giá trị', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, energy: -10, wealth: -30 } }
    ]
  },
  {
    id: 'cri_002', category: 'crisis', subcategory: 'bệnh tật',
    text: 'Bạn cảm thấy đau đầu và mệt mỏi kéo dài vài ngày.',
    choices: [
      { id: 'A', text: 'Đi khám bác sĩ', tags: ['long_term', 'risk_low'],
        immediate: { wealth: -30, health: 15, knowledge: 5 } },
      { id: 'B', text: 'Tự uống thuốc, nghỉ ngơi', tags: ['short_term'],
        immediate: { health: 5, wealth: -10 },
        delayed: [{ days: 15, effects: { health: -15 }, message: 'Bệnh không được điều trị đúng cách trở nặng hơn.', traceChoice: 'Tự điều trị' }] },
      { id: 'C', text: 'Bỏ qua, cố làm việc', tags: ['avoidance', 'short_term'],
        immediate: { health: -10, energy: -15, wealth: 5 } },
      { id: 'D', text: 'Nhờ người thân đưa đi khám', tags: ['relationship', 'long_term'],
        immediate: { health: 12, relationships: 10, wealth: -20 } }
    ]
  },
  {
    id: 'cri_003', category: 'crisis', subcategory: 'thất bại',
    text: 'Dự án quan trọng của bạn thất bại hoàn toàn.',
    choices: [
      { id: 'A', text: 'Phân tích nguyên nhân và rút kinh nghiệm', tags: ['long_term', 'learning'],
        immediate: { knowledge: 15, happiness: -5, energy: -5 } },
      { id: 'B', text: 'Từ bỏ, thử việc khác', tags: ['avoidance', 'short_term'],
        immediate: { happiness: -15, energy: 10 },
        flags: ['avoided_learning'] },
      { id: 'C', text: 'Nghỉ ngơi vài ngày rồi tiếp tục', tags: ['long_term'],
        immediate: { energy: 15, happiness: 5, health: 5 } },
      { id: 'D', text: 'Chia sẻ với mentor để được hỗ trợ', tags: ['relationship', 'learning'],
        immediate: { knowledge: 12, relationships: 10, happiness: 5 } }
    ]
  },
  {
    id: 'cri_004', category: 'crisis', subcategory: 'cơ hội bất ngờ',
    text: 'Một startup mời bạn tham gia với vai trò cofounder.',
    choices: [
      { id: 'A', text: 'Nhận lời ngay, bỏ việc hiện tại', tags: ['risk_high', 'long_term'],
        immediate: { happiness: 15, energy: -10, wealth: -20 },
        delayed: [{ days: 60, effects: { wealth: 80, knowledge: 20 }, message: 'Rủi ro lớn nhưng startup phát triển tốt.', traceChoice: 'Tham gia startup' }] },
      { id: 'B', text: 'Tham gia part-time trước', tags: ['long_term', 'risk_low', 'learning'],
        immediate: { knowledge: 15, energy: -15, happiness: 8 } },
      { id: 'C', text: 'Từ chối, giữ việc ổn định', tags: ['risk_low', 'long_term'],
        immediate: { happiness: 3, wealth: 10 } },
      { id: 'D', text: 'Đàm phán điều khoản trước khi quyết định', tags: ['long_term', 'learning'],
        immediate: { knowledge: 10, happiness: 5 } }
    ]
  },
  {
    id: 'cri_005', category: 'crisis', subcategory: 'mất việc',
    text: 'Bạn thực sự bị sa thải. Thu nhập dừng lại.',
    choices: [
      { id: 'A', text: 'Tích cực ứng tuyển mỗi ngày', tags: ['long_term', 'learning'],
        immediate: { energy: -20, knowledge: 5, happiness: -10, wealth: -30 } },
      { id: 'B', text: 'Nghỉ ngơi vài tuần rồi tìm việc', tags: ['long_term'],
        immediate: { energy: 20, health: 10, wealth: -50, happiness: 5 } },
      { id: 'C', text: 'Chấp nhận việc tạm thời bất kỳ', tags: ['short_term', 'risk_low'],
        immediate: { wealth: 20, happiness: -8, energy: -10 } },
      { id: 'D', text: 'Khởi nghiệp với tiền tiết kiệm', tags: ['risk_high', 'long_term', 'learning'],
        immediate: { wealth: -80, knowledge: 15, happiness: 5, energy: -15 } }
    ]
  },
  {
    id: 'cri_006', category: 'crisis', subcategory: 'cơ hội bất ngờ',
    text: 'Bạn trúng vé số nhỏ: 2000$.',
    choices: [
      { id: 'A', text: 'Chi tiêu ngay cho sở thích', tags: ['short_term'],
        immediate: { wealth: 200, happiness: 20 },
        flags: ['impulse_spending'] },
      { id: 'B', text: 'Đầu tư toàn bộ', tags: ['long_term', 'risk_low'],
        immediate: { wealth: 500, knowledge: 5 },
        delayed: [{ days: 50, effects: { wealth: 100 }, message: 'Khoản đầu tư may mắn sinh lời.', traceChoice: 'Đầu tư tiền trúng' }] },
      { id: 'C', text: 'Chia: tiết kiệm, đầu tư, thưởng bản thân', tags: ['long_term'],
        immediate: { wealth: 300, happiness: 15, knowledge: 5 } },
      { id: 'D', text: 'Quyên góp một phần', tags: ['relationship', 'long_term'],
        immediate: { wealth: 100, happiness: 20, relationships: 10 } }
    ]
  }
];
