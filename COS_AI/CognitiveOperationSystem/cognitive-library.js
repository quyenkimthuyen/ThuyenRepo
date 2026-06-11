/**
 * Cognitive Library — Thư viện nhận thức cố định
 * Framework EEIBVIA: Event, Emotion, Interpretation, Belief, Value, Identity, Action
 *
 * Mọi phân loại đều map vào thư viện này.
 * Mở rộng: thêm item vào mảng tương ứng + keywords.
 */

const COGNITIVE_FRAMEWORK = {
  EVENT: 'Event',
  EMOTION: 'Emotion',
  INTERPRETATION: 'Interpretation',
  BELIEF: 'Belief',
  VALUE: 'Value',
  IDENTITY: 'Identity',
  ACTION: 'Action',
};

/**
 * Nhãn tiếng Việt cho 7 bước khung nhìn lại suy nghĩ (EEIBVIA).
 * Giữ key tiếng Anh trong code; chỉ hiển thị nhãn Việt cho người dùng.
 */
const FRAMEWORK_LABELS_VI = {
  Event: 'Việc xảy ra',
  Emotion: 'Cảm xúc',
  Interpretation: 'Cách hiểu',
  Belief: 'Niềm tin',
  Value: 'Giá trị',
  Identity: 'Vai trò bản thân',
  Action: 'Hành động',
};

/** Mô tả ngắn khung 7 bước — thay cho thuật ngữ EEIBVIA Framework */
const EEIBVIA_DESCRIPTION_VI = '7 bước nhìn lại suy nghĩ';

/** Trạng thái ghi nhận — tránh dịch máy (vd. candidate → ứng viên) */
const NODE_STATUS_LABELS_VI = {
  draft: 'Mới ghi nhận',
  candidate: 'Lặp lại nhiều lần',
  verified: 'Đã vững chắc',
};

function getFrameworkLabel(step) {
  if (typeof I18n !== 'undefined') return I18n.frameworkLabel(step);
  return FRAMEWORK_LABELS_VI[step] || step;
}

function getNodeStatusLabel(status) {
  if (typeof I18n !== 'undefined') return I18n.nodeStatusLabel(status);
  return NODE_STATUS_LABELS_VI[status] || status;
}

const getFrameworkLabelVi = getFrameworkLabel;
const getNodeStatusLabelVi = getNodeStatusLabel;

/** Thứ tự luồng câu hỏi phản chiếu */
const REFLECTION_FLOW = [
  COGNITIVE_FRAMEWORK.EVENT,
  COGNITIVE_FRAMEWORK.EMOTION,
  COGNITIVE_FRAMEWORK.INTERPRETATION,
  COGNITIVE_FRAMEWORK.BELIEF,
  COGNITIVE_FRAMEWORK.VALUE,
  COGNITIVE_FRAMEWORK.IDENTITY,
  COGNITIVE_FRAMEWORK.ACTION,
];

/** Các cây trong Cognitive Forest */
const FOREST_TREES = [
  { id: 'family', label: 'Gia đình', icon: '🌳', keywords: ['gia đình', 'con', 'vợ', 'chồng', 'cha', 'mẹ', 'bố', 'ba', 'anh', 'chị', 'em', 'nhà'] },
  { id: 'work', label: 'Công việc', icon: '🌳', keywords: ['công việc', 'làm việc', 'sếp', 'đồng nghiệp', 'dự án', 'công ty', 'nghề', 'việc'] },
  { id: 'finance', label: 'Tài chính', icon: '🌳', keywords: ['tiền', 'tài chính', 'nợ', 'lương', 'đầu tư', 'chi tiêu', 'giàu', 'nghèo'] },
  { id: 'learning', label: 'Học tập', icon: '🌳', keywords: ['học', 'thi', 'điểm', 'trường', 'giáo viên', 'bài tập', 'kiến thức', 'đại học'] },
  { id: 'health', label: 'Sức khỏe', icon: '🌳', keywords: ['sức khỏe', 'bệnh', 'mệt', 'ngủ', 'ăn', 'tập', 'thể dục', 'stress'] },
  { id: 'self', label: 'Bản thân', icon: '🌳', keywords: ['tôi', 'mình', 'bản thân', 'tự tin', 'tự trọng', 'cảm giác', 'nghĩ'] },
];

/** Màu theo loại node (dùng trong UI) */
const NODE_TYPE_COLORS = {
  Event: { bg: 'rgba(99, 102, 241, 0.2)', border: '#6366f1', text: '#a5b4fc' },
  Emotion: { bg: 'rgba(236, 72, 153, 0.2)', border: '#ec4899', text: '#f9a8d4' },
  Interpretation: { bg: 'rgba(168, 85, 247, 0.2)', border: '#a855f7', text: '#d8b4fe' },
  Belief: { bg: 'rgba(245, 158, 11, 0.2)', border: '#f59e0b', text: '#fcd34d' },
  Value: { bg: 'rgba(34, 197, 94, 0.2)', border: '#22c55e', text: '#86efac' },
  Identity: { bg: 'rgba(6, 182, 212, 0.2)', border: '#06b6d4', text: '#67e8f9' },
  Action: { bg: 'rgba(239, 68, 68, 0.2)', border: '#ef4444', text: '#fca5a5' },
};

/**
 * Cảm xúc — 50+ items
 * Mỗi item: label, keywords để match từ user input
 */
const EMOTIONS = [
  { label: 'Vui', keywords: ['vui', 'hạnh phúc', 'vui vẻ', 'phấn khởi'] },
  { label: 'Buồn', keywords: ['buồn', 'u sầu', 'chán nản', 'thất vọng'] },
  { label: 'Lo lắng', keywords: ['lo', 'lo lắng', 'băn khoăn', 'bồn chồn'] },
  { label: 'Sợ hãi', keywords: ['sợ', 'sợ hãi', 'hoảng sợ', 'kinh hãi'] },
  { label: 'Tức giận', keywords: ['tức', 'giận', 'tức giận', 'phẫn nộ'] },
  { label: 'Áp lực', keywords: ['áp lực', 'căng thẳng', 'stress', 'quá tải'] },
  { label: 'Cô đơn', keywords: ['cô đơn', 'lẻ loi', 'cô lập'] },
  { label: 'Thất vọng', keywords: ['thất vọng', 'chán', 'nản'] },
  { label: 'Hạnh phúc', keywords: ['hạnh phúc', 'mãn nguyện', 'sung sướng'] },
  { label: 'Hy vọng', keywords: ['hy vọng', 'mong', 'tin tưởng tương lai'] },
  { label: 'Bực bội', keywords: ['bực', 'khó chịu', 'bực bội'] },
  { label: 'Xấu hổ', keywords: ['xấu hổ', 'ngại', 'e thẹn'] },
  { label: 'Tự ti', keywords: ['tự ti', 'kém cỏi', 'không đủ'] },
  { label: 'Tự hào', keywords: ['tự hào', 'hãnh diện'] },
  { label: 'Biết ơn', keywords: ['biết ơn', 'tri ân', 'cảm kích'] },
  { label: 'Ghen tị', keywords: ['ghen', 'ghen tị', 'đố kỵ'] },
  { label: 'Thương yêu', keywords: ['thương', 'yêu', 'trìu mến'] },
  { label: 'Ghét bỏ', keywords: ['ghét', 'khinh', 'chán ghét'] },
  { label: 'Bối rối', keywords: ['bối rối', 'lúng túng', 'không biết'] },
  { label: 'Bình yên', keywords: ['bình yên', 'thanh thản', 'an nhiên'] },
  { label: 'Hồi hộp', keywords: ['hồi hộp', 'háo hức', 'mong chờ'] },
  { label: 'Mệt mỏi', keywords: ['mệt', 'kiệt sức', 'uể oải'] },
  { label: 'Trống rỗng', keywords: ['trống rỗng', 'vô nghĩa', 'vô hồn'] },
  { label: 'Tuyệt vọng', keywords: ['tuyệt vọng', 'vô vọng'] },
  { label: 'Hối hận', keywords: ['hối hận', 'ân hận', 'tiếc nuối'] },
  { label: 'Tội lỗi', keywords: ['tội lỗi', 'có lỗi', 'cảm thấy sai'] },
  { label: 'Tò mò', keywords: ['tò mò', 'thắc mắc', 'muốn biết'] },
  { label: 'Ngạc nhiên', keywords: ['ngạc nhiên', 'bất ngờ', 'sửng sốt'] },
  { label: 'Khinh thường', keywords: ['khinh', 'coi thường', 'miệt thị'] },
  { label: 'Tin tưởng', keywords: ['tin', 'tin tưởng', 'yên tâm'] },
  { label: 'Nghi ngờ', keywords: ['nghi', 'nghi ngờ', 'hoài nghi'] },
  { label: 'Bất lực', keywords: ['bất lực', 'vô dụng', 'không làm được'] },
  { label: 'Quyết tâm', keywords: ['quyết tâm', 'kiên định', 'cố gắng'] },
  { label: 'Hứng khởi', keywords: ['hứng khởi', 'nhiệt huyết', 'đam mê'] },
  { label: 'Chán nản', keywords: ['chán nản', 'nản lòng', 'bỏ cuộc'] },
  { label: 'Bồn chồn', keywords: ['bồn chồn', 'không yên', 'lo âu'] },
  { label: 'Thoải mái', keywords: ['thoải mái', 'dễ chịu', 'nhẹ nhàng'] },
  { label: 'Căng thẳng', keywords: ['căng thẳng', 'căng', 'mỏi đầu'] },
  { label: 'Vui mừng', keywords: ['vui mừng', 'phấn khích'] },
  { label: 'Đau khổ', keywords: ['đau', 'đau khổ', 'đau lòng'] },
  { label: 'Bất an', keywords: ['bất an', 'không an tâm'] },
  { label: 'Hài lòng', keywords: ['hài lòng', 'đủ', 'ổn'] },
  { label: 'Không hài lòng', keywords: ['không hài lòng', 'chưa đủ'] },
  { label: 'Tự do', keywords: ['tự do', 'nhẹ nhõm', 'thoát'] },
  { label: 'Bị giam cầm', keywords: ['giam cầm', 'kẹt', 'mắc kẹt'] },
  { label: 'Tự trọng', keywords: ['tự trọng', 'tự tôn'] },
  { label: 'Tổn thương', keywords: ['tổn thương', 'bị tổn thương', 'đau đớn'] },
  { label: 'Hy sinh', keywords: ['hy sinh', 'nhường nhịn'] },
  { label: 'Ganh tị', keywords: ['ganh tị', 'đố kỵ'] },
  { label: 'Thất vọng sâu sắc', keywords: ['vỡ mộng', 'sụp đổ'] },
  { label: 'Lạc quan', keywords: ['lạc quan', 'tích cực', 'sáng sủa'] },
  { label: 'Bi quan', keywords: ['bi quan', 'tiêu cực', 'u ám'] },
  { label: 'Bối cảnh lo âu', keywords: ['lo âu', 'trầm cảm', 'rối loạn'] },
];

/**
 * Giá trị — 50+ items
 */
const VALUES = [
  { label: 'Gia đình', keywords: ['gia đình', 'nhà', 'người thân'] },
  { label: 'Tự do', keywords: ['tự do', 'độc lập', 'tự chủ'] },
  { label: 'Trách nhiệm', keywords: ['trách nhiệm', 'nghĩa vụ'] },
  { label: 'Trung thực', keywords: ['trung thực', 'thật thà', 'chân thành'] },
  { label: 'Phát triển', keywords: ['phát triển', 'tiến bộ', 'lớn lên'] },
  { label: 'Học hỏi', keywords: ['học hỏi', 'học tập', 'kiến thức'] },
  { label: 'Yêu thương', keywords: ['yêu thương', 'tình yêu', 'quan tâm'] },
  { label: 'Cống hiến', keywords: ['cống hiến', 'phục vụ', 'đóng góp'] },
  { label: 'Sức khỏe', keywords: ['sức khỏe', 'khỏe mạnh'] },
  { label: 'Thành tựu', keywords: ['thành tựu', 'thành công', 'đạt được'] },
  { label: 'Công bằng', keywords: ['công bằng', 'công lý', 'đúng đắn'] },
  { label: 'Sáng tạo', keywords: ['sáng tạo', 'đổi mới', 'sáng kiến'] },
  { label: 'An toàn', keywords: ['an toàn', 'bảo vệ', 'ổn định'] },
  { label: 'Hòa bình', keywords: ['hòa bình', 'yên bình', 'thanh bình'] },
  { label: 'Tôn trọng', keywords: ['tôn trọng', 'kính trọng'] },
  { label: 'Khiêm tốn', keywords: ['khiêm tốn', 'nhún nhường'] },
  { label: 'Dũng cảm', keywords: ['dũng cảm', 'can đảm', 'gan dạ'] },
  { label: 'Kiên nhẫn', keywords: ['kiên nhẫn', 'chịu đựng'] },
  { label: 'Kỷ luật', keywords: ['kỷ luật', 'ngăn nắp', 'tự chủ'] },
  { label: 'Tin cậy', keywords: ['tin cậy', 'đáng tin', 'uy tín'] },
  { label: 'Lòng trắc ẩn', keywords: ['trắc ẩn', 'thương người', 'nhân ái'] },
  { label: 'Giàu có', keywords: ['giàu', 'tài sản', 'thịnh vượng'] },
  { label: 'Danh tiếng', keywords: ['danh tiếng', 'uy tín xã hội', 'thanh danh'] },
  { label: 'Quyền lực', keywords: ['quyền lực', 'ảnh hưởng', 'lãnh đạo'] },
  { label: 'Niềm vui', keywords: ['niềm vui', 'hạnh phúc', 'vui sống'] },
  { label: 'Trí tuệ', keywords: ['trí tuệ', 'thông minh', 'sáng suốt'] },
  { label: 'Đạo đức', keywords: ['đạo đức', 'lương thiện', 'đúng sai'] },
  { label: 'Tôn giáo', keywords: ['tôn giáo', 'đức tin', 'thiêng liêng'] },
  { label: 'Thiên nhiên', keywords: ['thiên nhiên', 'môi trường'] },
  { label: 'Cộng đồng', keywords: ['cộng đồng', 'xã hội', 'đoàn kết'] },
  { label: 'Bạn bè', keywords: ['bạn bè', 'tình bạn'] },
  { label: 'Sự nghiệp', keywords: ['sự nghiệp', 'công danh'] },
  { label: 'Cân bằng', keywords: ['cân bằng', 'work-life', 'hài hòa'] },
  { label: 'Tự lập', keywords: ['tự lập', 'tự chủ cuộc đời'] },
  { label: 'Hoàn hảo', keywords: ['hoàn hảo', 'hoàn mỹ', 'chuẩn mực'] },
  { label: 'Đơn giản', keywords: ['đơn giản', 'tối giản'] },
  { label: 'Phiêu lưu', keywords: ['phiêu lưu', 'khám phá', 'mạo hiểm'] },
  { label: 'Ổn định', keywords: ['ổn định', 'an toàn tài chính'] },
  { label: 'Tự do sáng tạo', keywords: ['tự do sáng tạo', 'nghệ thuật'] },
  { label: 'Gia truyền', keywords: ['gia truyền', 'truyền thống'] },
  { label: 'Hiệu quả', keywords: ['hiệu quả', 'năng suất'] },
  { label: 'Chất lượng', keywords: ['chất lượng', 'tốt nhất'] },
  { label: 'Tiết kiệm', keywords: ['tiết kiệm', 'dành dụm'] },
  { label: 'Hưởng thụ', keywords: ['hưởng thụ', 'thưởng thức'] },
  { label: 'Lòng biết ơn', keywords: ['biết ơn', 'tri ân'] },
  { label: 'Tha thứ', keywords: ['tha thứ', 'bỏ qua'] },
  { label: 'Công nhận', keywords: ['công nhận', 'được thấy', 'được khen'] },
  { label: 'Tự chủ', keywords: ['tự chủ', 'quyết định của mình'] },
  { label: 'Hợp tác', keywords: ['hợp tác', 'đồng đội', 'cùng nhau'] },
  { label: 'Cạnh tranh', keywords: ['cạnh tranh', 'chiến thắng', 'thắng'] },
  { label: 'Bền vững', keywords: ['bền vững', 'lâu dài'] },
  { label: 'Tự do tài chính', keywords: ['tự do tài chính', 'độc lập tài chính'] },
  { label: 'Giáo dục', keywords: ['giáo dục', 'dạy con', 'nuôi dạy'] },
];

/**
 * Niềm tin phổ biến — 100+ items
 */
const BELIEFS = [
  { label: 'Học giỏi mới thành công', keywords: ['học giỏi', 'điểm cao', 'thi cử'] },
  { label: 'Tiền mang lại hạnh phúc', keywords: ['tiền', 'hạnh phúc', 'giàu'] },
  { label: 'Cha mẹ phải hy sinh', keywords: ['cha mẹ', 'hy sinh', 'vì con'] },
  { label: 'Con cái phải nghe lời', keywords: ['con', 'nghe lời', 'phải vâng'] },
  { label: 'Làm việc chăm chỉ sẽ thành công', keywords: ['chăm chỉ', 'cần cù', 'nỗ lực'] },
  { label: 'Không ai hiểu tôi', keywords: ['không ai hiểu', 'cô đơn', 'một mình'] },
  { label: 'Tôi phải hoàn hảo', keywords: ['hoàn hảo', 'không được sai', 'phải tốt'] },
  { label: 'Thất bại là đáng xấu hổ', keywords: ['thất bại', 'xấu hổ', 'thua'] },
  { label: 'Người khác đánh giá quyết định giá trị tôi', keywords: ['đánh giá', 'ý kiến người khác'] },
  { label: 'Tôi không đủ giỏi', keywords: ['không đủ', 'kém', 'không giỏi'] },
  { label: 'Mọi thứ phải công bằng', keywords: ['công bằng', 'bất công', 'đối xử'] },
  { label: 'Gia đình là ưu tiên số 1', keywords: ['gia đình', 'ưu tiên', 'số một'] },
  { label: 'Công việc quan trọng hơn nghỉ ngơi', keywords: ['làm việc', 'nghỉ', 'overwork'] },
  { label: 'Con tôi phải thành công', keywords: ['con', 'thành công', 'con tôi'] },
  { label: 'Tuổi trẻ phải nghe người lớn', keywords: ['tuổi trẻ', 'nghe lời', 'lớn tuổi'] },
  { label: 'Đàn ông không được khóc', keywords: ['đàn ông', 'khóc', 'yếu đuối'] },
  { label: 'Phụ nữ phải lo gia đình', keywords: ['phụ nữ', 'nội trợ', 'gia đình'] },
  { label: 'Giàu có mới được tôn trọng', keywords: ['giàu', 'tôn trọng', 'địa vị'] },
  { label: 'Nghèo là do lười', keywords: ['nghèo', 'lười', 'không cố'] },
  { label: 'May mắn quan trọng hơn nỗ lực', keywords: ['may mắn', 'số phận', 'định mệnh'] },
  { label: 'Tôi không thể thay đổi', keywords: ['không thể thay đổi', 'bản chất', 'vốn vậy'] },
  { label: 'Mọi thứ đều là lỗi của tôi', keywords: ['lỗi tôi', 'tại tôi', 'do tôi'] },
  { label: 'Người khác luôn có ý xấu', keywords: ['ý xấu', 'không tin', 'lừa đảo'] },
  { label: 'Tôi phải làm hài lòng mọi người', keywords: ['làm hài lòng', 'people pleasing'] },
  { label: 'Nói ra sẽ bị phán xét', keywords: ['phán xét', 'chỉ trích', 'nói ra'] },
  { label: 'Cảm xúc là điểm yếu', keywords: ['cảm xúc', 'yếu', 'không được yếu'] },
  { label: 'Thành công cần hy sinh gia đình', keywords: ['hy sinh', 'gia đình', 'thành công'] },
  { label: 'Con cái là phản ánh của cha mẹ', keywords: ['con', 'phản ánh', 'thể hiện'] },
  { label: 'Học hành là con đường duy nhất', keywords: ['học', 'duy nhất', 'bằng cấp'] },
  { label: 'Không có tiền không sống được', keywords: ['không tiền', 'sống', 'tài chính'] },
  { label: 'Tuổi già phải được con cháu phụng dưỡng', keywords: ['tuổi già', 'phụng dưỡng'] },
  { label: 'Trẻ em phải biết ơn cha mẹ', keywords: ['biết ơn', 'cha mẹ', 'hiếu thảo'] },
  { label: 'Ly hôn là thất bại', keywords: ['ly hôn', 'thất bại', 'gia đình tan vỡ'] },
  { label: 'Phải có nhà mới an tâm', keywords: ['nhà', 'mua nhà', 'ổn định'] },
  { label: 'Làm việc nhiều giờ chứng tỏ nghiêm túc', keywords: ['nhiều giờ', '14 giờ', 'overtime'] },
  { label: 'Nghỉ ngơi là lười biếng', keywords: ['nghỉ', 'lười', 'nghỉ ngơi'] },
  { label: 'Con không học là tôi thất bại', keywords: ['con không học', 'thất bại', 'con tôi'] },
  { label: 'Thiếu điểm là tương lai tối', keywords: ['thiếu điểm', 'điểm kém', 'thi'] },
  { label: 'Bạn bè ảnh hưởng xấu đến con', keywords: ['bạn bè', 'ảnh hưởng', 'con'] },
  { label: 'Kỷ luật con bằng phạt là đúng', keywords: ['phạt', 'đánh', 'kỷ luật'] },
  { label: 'Yêu thương là chiều con mọi thứ', keywords: ['chiều', 'yêu thương', 'mọi thứ'] },
  { label: 'Con phải theo nghề cha mẹ chọn', keywords: ['nghề', 'cha mẹ chọn', 'định hướng'] },
  { label: 'Thành công phải nhanh', keywords: ['nhanh', 'sớm', 'tuổi trẻ'] },
  { label: 'So sánh với người khác là động lực', keywords: ['so sánh', 'hơn kém', 'đua'] },
  { label: 'Tôi không xứng đáng', keywords: ['không xứng', 'imposter', 'giả mạo'] },
  { label: 'Mọi việc phải trong tầm kiểm soát', keywords: ['kiểm soát', 'mọi thứ'] },
  { label: 'Thay đổi là nguy hiểm', keywords: ['thay đổi', 'nguy hiểm', 'ổn định'] },
  { label: 'Tôi luôn đúng', keywords: ['luôn đúng', 'không sai'] },
  { label: 'Người khác luôn sai', keywords: ['họ sai', 'người khác sai'] },
  { label: 'Không ai có thể giúp tôi', keywords: ['không ai giúp', 'một mình'] },
  { label: 'Tôi phải tự làm mọi thứ', keywords: ['tự làm', 'không nhờ'] },
  { label: 'Yêu cầu giúp đỡ là yếu đuối', keywords: ['nhờ giúp', 'yếu'] },
  { label: 'Sức khỏe có thể hy sinh vì công việc', keywords: ['sức khỏe', 'công việc', 'hy sinh'] },
  { label: 'Giàu mới được hạnh phúc', keywords: ['giàu', 'hạnh phúc'] },
  { label: 'Nghèo khó là định mệnh', keywords: ['định mệnh', 'số phận', 'nghèo'] },
  { label: 'Học nhiều ngoại ngữ mới thành công', keywords: ['ngoại ngữ', 'tiếng anh'] },
  { label: 'Đại học danh tiếng mới có giá trị', keywords: ['đại học', 'danh tiếng', 'bằng'] },
  { label: 'Không có bằng là thất bại', keywords: ['bằng cấp', 'đại học', 'học vấn'] },
  { label: 'Trí tuệ là do bẩm sinh', keywords: ['bẩm sinh', 'gen', 'thông minh'] },
  { label: 'Cố gắng vô ích nếu không tài năng', keywords: ['tài năng', 'cố gắng vô ích'] },
  { label: 'Cha mẹ luôn biết điều tốt nhất', keywords: ['cha mẹ biết', 'tốt nhất'] },
  { label: 'Con phải thành người mà cha mẹ mong muốn', keywords: ['mong muốn', 'kỳ vọng', 'cha mẹ'] },
  { label: 'Tôi phải chứng minh bản thân', keywords: ['chứng minh', 'được công nhận'] },
  { label: 'Thất bại một lần là thất bại mãi mãi', keywords: ['mãi mãi', 'không phục hồi'] },
  { label: 'Một sai lầm hủy hoại tất cả', keywords: ['hủy hoại', 'tất cả', 'sai lầm'] },
  { label: 'Người tốt luôn được đền đáp', keywords: ['đền đáp', 'nhân quả', 'tốt'] },
  { label: 'Người xấu luôn thắng', keywords: ['người xấu', 'bất công', 'thắng'] },
  { label: 'Cuộc sống phải công bằng', keywords: ['cuộc sống', 'công bằng'] },
  { label: 'Tôi không thuộc về nơi nào', keywords: ['không thuộc', 'lạc lõng'] },
  { label: 'Tình yêu đủ để giải quyết mọi thứ', keywords: ['tình yêu', 'đủ', 'mọi thứ'] },
  { label: 'Hôn nhân là mục tiêu cuộc đời', keywords: ['hôn nhân', 'cưới', 'mục tiêu'] },
  { label: 'Con cái hoàn thành cuộc đời tôi', keywords: ['con cái', 'hoàn thành', 'ý nghĩa'] },
  { label: 'Tôi là người cha/mẹ tồi', keywords: ['tồi', 'cha mẹ tồi', 'không đủ'] },
  { label: 'Con sẽ thất bại nếu không nghe tôi', keywords: ['thất bại', 'không nghe'] },
  { label: 'Giáo viên quyết định tương lai con', keywords: ['giáo viên', 'tương lai'] },
  { label: 'Học thêm là giải pháp mọi vấn đề', keywords: ['học thêm', 'khóa học'] },
  { label: 'Công nghệ làm con lười', keywords: ['công nghệ', 'điện thoại', 'lười'] },
  { label: 'Kỳ vọng cao giúp con tiến bộ', keywords: ['kỳ vọng', 'áp lực', 'tiến bộ'] },
  { label: 'Không la mắng là nuông chiều', keywords: ['la mắng', 'nuông chiều'] },
  { label: 'Tôi phải kiểm soát con', keywords: ['kiểm soát', 'con'] },
  { label: 'Con tự lập là bỏ rơi', keywords: ['tự lập', 'bỏ rơi'] },
  { label: 'Thành công đo bằng lương', keywords: ['lương', 'thu nhập', 'đo'] },
  { label: 'Nghỉ phép là thiếu trách nhiệm', keywords: ['nghỉ phép', 'trách nhiệm'] },
  { label: 'Sếp luôn đúng', keywords: ['sếp', 'cấp trên'] },
  { label: 'Đổi việc là không ổn định', keywords: ['đổi việc', 'nhảy việc'] },
  { label: 'Khởi nghiệp quá rủi ro', keywords: ['khởi nghiệp', 'rủi ro'] },
  { label: 'An toàn quan trọng hơn mơ ước', keywords: ['an toàn', 'mơ ước'] },
  { label: 'Tuổi tác quá muộn để thay đổi', keywords: ['quá muộn', 'tuổi', 'già'] },
  { label: 'Tôi đã quá già để học', keywords: ['quá già', 'học'] },
  { label: 'Sức khỏe tâm thần là chuyện riêng', keywords: ['tâm thần', 'riêng tư'] },
  { label: 'Đi tâm lý là điên', keywords: ['tâm lý', 'điên', 'bác sĩ'] },
  { label: 'Thiền là lãng phí thời gian', keywords: ['thiền', 'lãng phí'] },
  { label: 'Tôi không có thời gian cho bản thân', keywords: ['không thời gian', 'bản thân'] },
  { label: 'Chăm sóc bản thân là ích kỷ', keywords: ['ích kỷ', 'chăm sóc bản thân'] },
  { label: 'Gia đình phải hy sinh vì tôi', keywords: ['hy sinh vì tôi', 'gia đình'] },
  { label: 'Tôi phải mang gánh nặng một mình', keywords: ['gánh nặng', 'một mình'] },
  { label: 'Nói không với người thân là sai', keywords: ['nói không', 'người thân'] },
  { label: 'Biên giới với gia đình không tồn tại', keywords: ['biên giới', 'gia đình'] },
  { label: 'Con không chịu học là do tôi dạy sai', keywords: ['không chịu học', 'dạy sai'] },
  { label: 'Mọi hành vi con đều do tôi', keywords: ['hành vi con', 'do tôi'] },
  { label: 'Tôi không đủ tốt làm cha/mẹ', keywords: ['không đủ tốt', 'cha mẹ'] },
  { label: 'Thành công của con là thành công của tôi', keywords: ['thành công con', 'của tôi'] },
  { label: 'Thất bại của con là thất bại của tôi', keywords: ['thất bại con'] },
  { label: 'Cuộc sống vô nghĩa nếu không thành công', keywords: ['vô nghĩa', 'thành công'] },
  { label: 'Hạnh phúc phải kiếm được', keywords: ['kiếm được', 'hạnh phúc', 'xứng đáng'] },
  { label: 'Tôi không được phép nghỉ', keywords: ['không được nghỉ', 'phép'] },
  { label: 'Làm việc 14 giờ/ngày là bình thường', keywords: ['14 giờ', 'làm việc nhiều', 'overwork'] },
];

/**
 * Thiên kiến nhận thức — 30+ items
 */
const COGNITIVE_BIASES = [
  { label: 'Confirmation Bias', labelVi: 'Chỉ tin điều mình đã tin', keywords: ['chỉ thấy', 'bỏ qua', 'xác nhận'] },
  { label: 'Overgeneralization', labelVi: 'Kết luận cho mọi trường hợp', keywords: ['luôn luôn', 'không bao giờ', 'mọi lúc'] },
  { label: 'Black and White Thinking', labelVi: 'Chỉ có đúng hoặc sai', keywords: ['hoặc', 'tất cả hoặc không', 'đen trắng'] },
  { label: 'Catastrophizing', labelVi: 'Nghĩ đến chuyện tồi tệ nhất', keywords: ['thảm họa', 'tệ nhất', 'hủy hoại', 'thất bại'] },
  { label: 'Availability Bias', labelVi: 'Tin vào điều dễ nhớ', keywords: ['nhớ', 'ví dụ gần', 'mới xảy ra'] },
  { label: 'Mind Reading', labelVi: 'Đoán ý người khác', keywords: ['họ nghĩ', 'chắc chắn họ', 'biết họ'] },
  { label: 'Fortune Telling', labelVi: 'Đoán trước tương lai', keywords: ['sẽ', 'chắc chắn sẽ', 'tương lai'] },
  { label: 'Emotional Reasoning', labelVi: 'Tin vào cảm xúc như sự thật', keywords: ['cảm thấy nên', 'vì buồn nên'] },
  { label: 'Should Statements', labelVi: 'Quy tắc phải/nên cứng nhắc', keywords: ['phải', 'nên', 'bắt buộc'] },
  { label: 'Labeling', labelVi: 'Gán nhãn cho bản thân hoặc người khác', keywords: ['tôi là', 'họ là', 'kẻ', 'đồ'] },
  { label: 'Personalization', labelVi: 'Đổ hết lỗi về mình', keywords: ['tại tôi', 'lỗi tôi', 'do tôi'] },
  { label: 'Disqualifying the Positive', labelVi: 'Bỏ qua điều tốt', keywords: ['may mắn thôi', 'không tính', 'tình cờ'] },
  { label: 'Mental Filter', labelVi: 'Chỉ nhìn mặt xấu', keywords: ['chỉ thấy xấu', 'bỏ qua tốt'] },
  { label: 'Jumping to Conclusions', labelVi: 'Vội kết luận', keywords: ['chắc là', 'rõ ràng là', 'kết luận'] },
  { label: 'Magnification', labelVi: 'Phóng đại vấn đề', keywords: ['quá lớn', 'khủng khiếp', 'kinh khủng'] },
  { label: 'Minimization', labelVi: 'Coi nhẹ vấn đề', keywords: ['không quan trọng', 'nhỏ thôi', 'bỏ qua'] },
  { label: 'Blame', labelVi: 'Đổ lỗi cho người khác', keywords: ['tại họ', 'lỗi họ', 'đổ lỗi'] },
  { label: 'Fairness Fallacy', labelVi: 'Mong mọi thứ phải công bằng', keywords: ['không công bằng', 'phải công bằng'] },
  { label: 'Heaven\'s Reward Fallacy', labelVi: 'Mong được đền đáp xứng đáng', keywords: ['xứng đáng', 'đền đáp', 'phải được'] },
  { label: 'Control Fallacy', labelVi: 'Tưởng mình kiểm soát được hết', keywords: ['kiểm soát', 'trong tay', 'quyết định mọi'] },
  { label: 'Fallacy of Change', labelVi: 'Mong thay đổi được người khác', keywords: ['họ phải thay đổi', 'nếu họ'] },
  { label: 'Always Being Right', labelVi: 'Phải luôn đúng', keywords: ['tôi đúng', 'không sai'] },
  { label: 'Hindsight Bias', labelVi: 'Nghĩ là mình đã biết từ trước', keywords: ['đã biết', 'lẽ ra', 'hồi tưởng'] },
  { label: 'Anchoring', labelVi: 'Bám vào ý đầu tiên', keywords: ['con số đầu', 'neo', 'tham chiếu'] },
  { label: 'Sunk Cost Fallacy', labelVi: 'Tiếc công đã bỏ ra nên cứ tiếp tục', keywords: ['đã đầu tư', 'không thể bỏ', 'đã bỏ công'] },
  { label: 'Bandwagon Effect', labelVi: 'Làm theo đám đông', keywords: ['mọi người', 'đám đông', 'theo'] },
  { label: 'Dunning-Kruger', labelVi: 'Tự tin thái quá vì thiếu hiểu biết', keywords: ['giỏi hơn', 'không biết mình kém'] },
  { label: 'Negativity Bias', labelVi: 'Dễ nhớ điều xấu hơn điều tốt', keywords: ['tiêu cực', 'xấu hơn', 'nhớ xấu'] },
  { label: 'Optimism Bias', labelVi: 'Tin mọi thứ sẽ ổn', keywords: ['sẽ ổn', 'không sao', 'lạc quan'] },
  { label: 'Self-serving Bias', labelVi: 'Chỉ thấy mặt tốt của mình', keywords: ['nhờ tôi', 'không phải lỗi tôi'] },
  { label: 'Fundamental Attribution Error', labelVi: 'Quy lỗi do tính cách người khác', keywords: ['tính cách họ', 'họ là người'] },
  { label: 'Halo Effect', labelVi: 'Nhìn một mặt tốt rồi cho là tốt hết', keywords: ['hoàn hảo', 'tốt mọi mặt'] },
  { label: 'Recency Bias', labelVi: 'Chỉ tin vào chuyện mới xảy ra', keywords: ['vừa rồi', 'gần đây', 'mới'] },
];

/** Mẫu trả lời gợi ý theo từng bước — người dùng có thể chọn thay vì tự soạn */
const REFLECTION_SUGGESTIONS = {
  Event: [
    'Hôm nay tôi bị sếp mắng trước mặt đồng nghiệp',
    'Con tôi không nghe lời và bỏ học bài',
    'Tôi làm việc 14 giờ mỗi ngày và mệt mỏi',
    'Vợ/chồng và tôi cãi nhau về việc nuôi dạy con',
    'Tôi không đạt KPI tháng này dù đã cố gắng',
  ],
  Emotion: [
    'Tôi cảm thấy lo lắng và bực bội',
    'Tôi buồn, thất vọng và mệt mỏi',
    'Tôi căng thẳng, áp lực trong ngực',
    'Tôi tức giận nhưng cũng cảm thấy tội lỗi',
    'Tôi cô đơn và không biết nói với ai',
  ],
  Interpretation: [
    'Tôi nghĩ mình đang làm cha mẹ tồi',
    'Có lẽ sếp không coi trọng tôi',
    'Tôi lo con sẽ không thành công trong tương lai',
    'Tôi sợ mọi thứ sẽ trở nên tệ hơn',
    'Có vẻ như dù cố gắng cũng không đủ',
  ],
  Belief: [
    'Tôi tin rằng con phải nghe lời cha mẹ',
    'Tôi nghĩ mình phải hoàn hảo mới được yêu',
    'Tôi tin làm việc chăm chỉ sẽ được đền đáp',
    'Tôi nghĩ thất bại là đáng xấu hổ',
    'Tôi tin gia đình phải là ưu tiên số một',
  ],
  Value: [
    'Gia đình là quan trọng nhất với tôi',
    'Tôi coi trọng trách nhiệm và kỷ luật',
    'Tôi trân trọng sự cân bằng giữa công việc và cuộc sống',
    'Tôi đánh giá cao sự trung thực và tôn trọng',
    'Phát triển bản thân và học hỏi rất quan trọng với tôi',
  ],
  Identity: [
    'Tôi thấy mình là người cha/mẹ đang thất bại',
    'Tôi là người luôn cố hy sinh vì gia đình',
    'Tôi là người làm việc không ngừng nghỉ',
    'Tôi là người phải gánh vác mọi thứ một mình',
    'Tôi là người luôn cố làm hài lòng người khác',
  ],
  Action: [
    'Tôi muốn nói chuyện với con một cách bình tĩnh hơn',
    'Tôi đang cân nhắc giảm giờ làm việc',
    'Tôi sẽ dành thời gian cho gia đình cuối tuần này',
    'Tôi muốn tìm người tư vấn hoặc chia sẻ',
    'Tôi sẽ thử nghỉ ngơi và chăm sóc sức khỏe trước',
  ],
};

/** Câu hỏi theo từng bước trong luồng EEIBVIA */
const REFLECTION_QUESTIONS = {
  Event: [
    'Bạn có thể kể thêm về tình huống đó không?',
    'Điều gì đã xảy ra cụ thể?',
    'Khi nào và ở đâu điều đó diễn ra?',
  ],
  Emotion: [
    'Điều đó khiến bạn cảm thấy thế nào?',
    'Cảm xúc nào nổi bật nhất trong bạn?',
    'Bạn cảm nhận điều gì trong cơ thể khi nghĩ về việc này?',
  ],
  Interpretation: [
    'Bạn lo điều gì sẽ xảy ra?',
    'Bạn hiểu sự việc đó theo cách nào?',
    'Điều gì ý nghĩa nhất với bạn trong tình huống này?',
  ],
  Belief: [
    'Điều gì khiến bạn tin như vậy?',
    'Niềm tin nào đang dẫn dắt suy nghĩ của bạn?',
    'Bạn đã từng nghĩ điều tương tự trước đây chưa?',
  ],
  Value: [
    'Điều gì quan trọng nhất với bạn trong việc này?',
    'Giá trị nào đang bị đe dọa hoặc được khẳng định?',
    'Bạn sẵn sàng hy sinh điều gì vì điều này?',
  ],
  Identity: [
    'Điều này nói gì về con người bạn?',
    'Trong tình huống này, bạn thấy mình là ai?',
    'Vai trò nào của bạn đang được đặt lên bàn cân?',
  ],
  Action: [
    'Bạn muốn làm gì tiếp theo?',
    'Hành động nào bạn đang cân nhắc?',
    'Nếu không có rào cản, bạn sẽ làm gì?',
  ],
};

/** Mẫu mâu thuẫn giá trị-hành động để contradiction engine */
const CONTRADICTION_PATTERNS = [
  {
    valueKeywords: ['gia đình', 'ưu tiên', 'số một'],
    actionKeywords: ['14 giờ', 'làm việc nhiều', 'overtime', 'không có thời gian'],
    message: 'ưu tiên gia đình, trong khi thời gian dành cho công việc có vẻ khá nhiều',
  },
  {
    valueKeywords: ['sức khỏe', 'khỏe mạnh'],
    actionKeywords: ['hy sinh sức khỏe', 'không ngủ', 'làm đêm', 'stress'],
    message: 'coi trọng sức khỏe, nhưng nhịp sống hiện tại có vẻ đang ảnh hưởng đến sức khỏe',
  },
  {
    valueKeywords: ['cân bằng', 'work-life'],
    actionKeywords: ['14 giờ', 'làm việc cuối tuần', 'không nghỉ'],
    message: 'mong có sự cân bằng, nhưng thời gian làm việc có vẻ chưa phản ánh điều đó',
  },
  {
    valueKeywords: ['tự do', 'tự chủ'],
    actionKeywords: ['kiểm soát con', 'bắt con', 'phải nghe'],
    message: 'coi trọng tự do, nhưng đôi khi có thể đang kiểm soát người khác nhiều hơn ý muốn',
  },
  {
    valueKeywords: ['phát triển', 'học hỏi'],
    actionKeywords: ['không có thời gian học', 'không học', 'bỏ học'],
    message: 'coi trọng phát triển, nhưng ít thời gian thực sự dành cho học hỏi',
  },
  {
    beliefKeywords: ['con phải nghe lời'],
    valueKeywords: ['tự do', 'tự chủ'],
    message: 'tin rằng con phải nghe lời, trong khi cũng coi trọng tự do và tự chủ',
  },
  {
    beliefKeywords: ['tiền mang lại hạnh phúc'],
    valueKeywords: ['gia đình', 'yêu thương'],
    message: 'gắn hạnh phúc với tiền bạc, trong khi quan hệ gia đình cũng rất quan trọng với bạn',
  },
];

// Export cho module pattern (global scope vì vanilla JS)
if (typeof window !== 'undefined') {
  window.CognitiveLibrary = {
    COGNITIVE_FRAMEWORK,
    FRAMEWORK_LABELS_VI,
    EEIBVIA_DESCRIPTION_VI,
    NODE_STATUS_LABELS_VI,
    getFrameworkLabel,
    getFrameworkLabelVi,
    getNodeStatusLabel,
    getNodeStatusLabelVi,
    REFLECTION_FLOW,
    FOREST_TREES,
    NODE_TYPE_COLORS,
    EMOTIONS,
    VALUES,
    BELIEFS,
    COGNITIVE_BIASES,
    REFLECTION_QUESTIONS,
    REFLECTION_SUGGESTIONS,
    CONTRADICTION_PATTERNS,
  };
}
