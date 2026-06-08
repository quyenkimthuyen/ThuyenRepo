(function () {
const STORAGE_KEY = "cognitive-tree:data:v1";
const QUIZ_STATE_VERSION = "opposing-views-complete-tree-v1";
const REMOVED_SAMPLE_TREE_IDS = new Set([
  "sample_tree_understanding_love_mindfulness"
]);

function node(id, parentId, type, content, order, createdAt) {
  return {
    id,
    parentId,
    type,
    content,
    order,
    createdAt
  };
}

function getRelationshipGroup(tree) {
  const groups = {
    sample_tree_parent_child_conflict: "Cha mẹ - Con cái",
    sample_tree_quit_job: "Cá nhân - Công việc",
    sample_tree_i_am_right: "Cá nhân - Tự phản biện",
    sample_tree_anger_friend: "Bạn bè",
    sample_tree_spouse_chores: "Vợ chồng",
    sample_tree_spouse_money: "Vợ chồng",
    sample_tree_in_laws_boundary: "Cha mẹ - Ông bà",
    sample_tree_child_screen_time: "Cha mẹ - Con cái",
    sample_tree_child_grades: "Cha mẹ - Con cái",
    sample_tree_sibling_fight: "Anh chị em",
    sample_tree_silent_spouse: "Vợ chồng",
    sample_tree_care_for_parents: "Con cái - Cha mẹ già",
    sample_tree_family_comparison: "Cha mẹ - Con trưởng thành",
    sample_tree_parenting_style_conflict: "Vợ chồng - Nuôi dạy con",
    sample_tree_husband_gentle_parenting: "Vợ chồng - Nuôi dạy con"
  };

  return tree.relationshipGroup || groups[tree.id] || (tree.id?.startsWith("sample_") ? "Khác" : "Tự tạo");
}

function normalizeTree(tree) {
  return {
    ...tree,
    relationshipGroup: getRelationshipGroup(tree)
  };
}

function createSampleTrees() {
  const createdAt = "2026-06-08T07:00:00.000Z";

  const trees = [
    {
      id: "sample_tree_parent_child_conflict",
      title: "Khi con cãi lại",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_parent_root",
      nodes: [
        node("sample_parent_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ con cần nghe lời ngay khi được nhắc làm bài; con nghĩ mình đã biết rồi và không muốn bị nhắc tiếp.", 0, createdAt),
        node("sample_parent_fact_1", "sample_parent_root", "BELIEF", "Ý kiến của tôi: Con cần nghe lời ngay khi cha mẹ nhắc làm bài.", 0, createdAt),
        node("sample_parent_action_0", "sample_parent_fact_1", "ACTION", "Tôi nhắc nhiều lần và yêu cầu con làm ngay để giữ kỷ luật.", 0, createdAt),
        node("sample_parent_consequence_0", "sample_parent_action_0", "CONSEQUENCE", "Con có thể làm bài ngay lúc đó, nhưng dễ thấy bị ép và khó học cách tự chịu trách nhiệm.", 0, createdAt),
        node("sample_parent_fact_2", "sample_parent_root", "BELIEF", "Ý kiến của con: Con đã biết rồi và không muốn bị nhắc tiếp.", 1, createdAt),
        node("sample_parent_interpretation_1", "sample_parent_fact_2", "INTERPRETATION", "Tôi diễn giải câu nói đó là con đang coi thường mình.", 0, createdAt),
        node("sample_parent_interpretation_2", "sample_parent_fact_2", "INTERPRETATION", "Một cách hiểu khác: con có thể đang mệt, xấu hổ hoặc muốn tự chủ.", 1, createdAt),
        node("sample_parent_belief_1", "sample_parent_interpretation_1", "BELIEF", "Con ngoan phải nghe lời ngay khi cha mẹ nhắc.", 0, createdAt),
        node("sample_parent_belief_2", "sample_parent_interpretation_2", "BELIEF", "Tôn trọng không nhất thiết đồng nghĩa với vâng lời tức thì.", 1, createdAt),
        node("sample_parent_emotion_1", "sample_parent_belief_1", "EMOTION", "Tức giận, bị xúc phạm, lo lắng mình mất quyền làm cha mẹ.", 0, createdAt),
        node("sample_parent_action_1", "sample_parent_emotion_1", "ACTION", "Tôi lớn tiếng và nói con hỗn.", 0, createdAt),
        node("sample_parent_consequence_1", "sample_parent_action_1", "CONSEQUENCE", "Con im lặng, khóc và tránh nói chuyện với tôi.", 0, createdAt),
        node("sample_parent_action_2", "sample_parent_belief_2", "ACTION", "Tôi có thể hỏi: 'Con cần thêm 10 phút hay cần bố/mẹ giúp phần nào?'", 1, createdAt),
        node("sample_parent_consequence_2", "sample_parent_action_2", "CONSEQUENCE", "Cuộc nói chuyện có cơ hội chuyển từ đối đầu sang hợp tác.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_quit_job",
      title: "Tôi muốn nghỉ việc",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_job_root",
      nodes: [
        node("sample_job_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ công ty không trân trọng công sức của mình; quản lý có thể nghĩ công việc chưa rõ ưu tiên và cả hai cần trao đổi lại.", 0, createdAt),
        node("sample_job_fact_1", "sample_job_root", "BELIEF", "Ý kiến của tôi: Công ty không trân trọng công sức nên tôi muốn nghỉ.", 0, createdAt),
        node("sample_job_action_0", "sample_job_fact_1", "ACTION", "Tôi âm thầm tìm việc mới và giảm giao tiếp với quản lý.", 0, createdAt),
        node("sample_job_consequence_0", "sample_job_action_0", "CONSEQUENCE", "Tôi có cảm giác tự bảo vệ mình, nhưng có thể bỏ lỡ cơ hội nói rõ nhu cầu hoặc cải thiện điều kiện làm việc.", 0, createdAt),
        node("sample_job_fact_2", "sample_job_root", "BELIEF", "Ý kiến của quản lý: Công việc đang quá tải và cần trao đổi lại ưu tiên trước khi quyết định.", 1, createdAt),
        node("sample_job_interpretation_1", "sample_job_fact_2", "INTERPRETATION", "Tôi đang diễn giải rằng công ty không trân trọng mình.", 0, createdAt),
        node("sample_job_interpretation_2", "sample_job_fact_2", "INTERPRETATION", "Có thể quản lý đang quá tải hoặc kỳ vọng công việc chưa được làm rõ.", 1, createdAt),
        node("sample_job_belief_1", "sample_job_interpretation_1", "BELIEF", "Nếu tôi giỏi, người khác phải tự nhận ra và ghi nhận công sức của tôi.", 0, createdAt),
        node("sample_job_emotion_1", "sample_job_belief_1", "EMOTION", "Kiệt sức, thất vọng, tủi thân và mất động lực.", 0, createdAt),
        node("sample_job_action_1", "sample_job_emotion_1", "ACTION", "Tôi né họp, phản hồi ngắn và bắt đầu tìm việc trong tâm trạng bực bội.", 0, createdAt),
        node("sample_job_consequence_1", "sample_job_action_1", "CONSEQUENCE", "Quan hệ công việc xấu đi, tôi càng thấy mình bị cô lập.", 0, createdAt),
        node("sample_job_action_2", "sample_job_interpretation_2", "ACTION", "Tôi có thể hẹn 30 phút để nói rõ tải việc, ưu tiên và điều kiện tiếp tục.", 1, createdAt),
        node("sample_job_consequence_2", "sample_job_action_2", "CONSEQUENCE", "Tôi có thêm dữ kiện trước khi quyết định nghỉ, chuyển team hoặc thương lượng lại.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_i_am_right",
      title: "Tôi cảm thấy mình đúng",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_right_root",
      nodes: [
        node("sample_right_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ cách của mình là đúng và nên làm ngay; người kia nghĩ cách đó còn rủi ro về thời gian và chất lượng.", 0, createdAt),
        node("sample_right_fact_1", "sample_right_root", "BELIEF", "Ý kiến của tôi: Cách triển khai của tôi đúng và nên làm ngay.", 0, createdAt),
        node("sample_right_action_0", "sample_right_fact_1", "ACTION", "Tôi thúc đẩy mọi người làm theo phương án của mình nhanh hơn.", 0, createdAt),
        node("sample_right_consequence_0", "sample_right_action_0", "CONSEQUENCE", "Công việc có thể chạy nhanh hơn, nhưng người khác dễ cảm thấy không được lắng nghe và ít góp ý rủi ro.", 0, createdAt),
        node("sample_right_fact_2", "sample_right_root", "BELIEF", "Ý kiến của người kia: Cách đó còn rủi ro về thời gian và chất lượng.", 1, createdAt),
        node("sample_right_interpretation_1", "sample_right_fact_2", "INTERPRETATION", "Tôi diễn giải rằng họ đang chống đối ý tưởng của tôi.", 0, createdAt),
        node("sample_right_interpretation_2", "sample_right_fact_2", "INTERPRETATION", "Cũng có thể họ đang bảo vệ mục tiêu chung bằng cách chỉ ra điểm mù.", 1, createdAt),
        node("sample_right_belief_1", "sample_right_interpretation_1", "BELIEF", "Nếu tôi có lý thì người khác nên đồng ý ngay.", 0, createdAt),
        node("sample_right_belief_2", "sample_right_interpretation_2", "BELIEF", "Một ý tưởng tốt vẫn cần chịu được phản biện.", 1, createdAt),
        node("sample_right_emotion_1", "sample_right_belief_1", "EMOTION", "Khó chịu, phòng thủ, muốn chứng minh mình đúng.", 0, createdAt),
        node("sample_right_action_1", "sample_right_emotion_1", "ACTION", "Tôi ngắt lời và lặp lại lập luận của mình mạnh hơn.", 0, createdAt),
        node("sample_right_consequence_1", "sample_right_action_1", "CONSEQUENCE", "Cuộc họp chuyển thành tranh thắng thua, ít ai còn tập trung vào dữ kiện.", 0, createdAt),
        node("sample_right_action_2", "sample_right_belief_2", "ACTION", "Tôi có thể hỏi: 'Bằng chứng nào sẽ khiến tôi cần đổi hướng?'", 1, createdAt),
        node("sample_right_consequence_2", "sample_right_action_2", "CONSEQUENCE", "Tôi giữ được sự kiên định với mục tiêu nhưng giảm cố chấp với phương án.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_anger_friend",
      title: "Tôi đang giận một người bạn",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_friend_root",
      nodes: [
        node("sample_friend_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ bạn thân nên trả lời sớm để thể hiện sự quan tâm; bạn ấy có thể nghĩ mình đang quá tải và chưa đủ sức trả lời ngay.", 0, createdAt),
        node("sample_friend_fact_1", "sample_friend_root", "BELIEF", "Ý kiến của tôi: Bạn thân nên trả lời sớm nếu còn coi trọng mình.", 0, createdAt),
        node("sample_friend_fact_2", "sample_friend_root", "BELIEF", "Ý kiến của bạn: Khi đang quá tải, bạn ấy có thể cần thời gian rồi mới trả lời.", 1, createdAt),
        node("sample_friend_interpretation_1", "sample_friend_fact_1", "INTERPRETATION", "Tôi diễn giải rằng bạn ấy không còn coi trọng mình.", 0, createdAt),
        node("sample_friend_interpretation_2", "sample_friend_fact_2", "INTERPRETATION", "Một khả năng khác là bạn ấy đang quá tải và chưa có năng lượng trả lời.", 1, createdAt),
        node("sample_friend_belief_1", "sample_friend_interpretation_1", "BELIEF", "Bạn thân thì phải phản hồi nhanh, nếu không nghĩa là không quan tâm.", 0, createdAt),
        node("sample_friend_emotion_1", "sample_friend_belief_1", "EMOTION", "Buồn, giận, cảm thấy bị bỏ rơi.", 0, createdAt),
        node("sample_friend_action_1", "sample_friend_emotion_1", "ACTION", "Tôi định nhắn một câu mỉa mai hoặc im lặng để người kia tự hiểu.", 0, createdAt),
        node("sample_friend_consequence_1", "sample_friend_action_1", "CONSEQUENCE", "Mối quan hệ dễ căng thẳng hơn, dù sự thật có thể chưa được kiểm chứng.", 0, createdAt),
        node("sample_friend_action_2", "sample_friend_interpretation_2", "ACTION", "Tôi có thể nhắn: 'Mình hơi lo và cũng hơi buồn, khi nào ổn bạn trả lời mình nhé.'", 1, createdAt),
        node("sample_friend_consequence_2", "sample_friend_action_2", "CONSEQUENCE", "Tôi nói thật cảm xúc mà không biến diễn giải thành cáo buộc.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_spouse_chores",
      title: "Vợ chồng cãi nhau vì việc nhà",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_chores_root",
      nodes: [
        node("sample_chores_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ người kia phải tự thấy việc nhà cần làm; bạn đời có thể nghĩ việc nhà cần được phân chia rõ thay vì tự đoán.", 0, createdAt),
        node("sample_chores_fact_1", "sample_chores_root", "BELIEF", "Ý kiến của tôi: Người kia phải tự thấy việc nhà cần làm.", 0, createdAt),
        node("sample_chores_fact_2", "sample_chores_root", "BELIEF", "Ý kiến của bạn đời: Việc nhà cần chia rõ, không nên bắt nhau tự đoán.", 1, createdAt),
        node("sample_chores_interpretation_1", "sample_chores_fact_1", "INTERPRETATION", "Tôi diễn giải rằng người kia ỷ lại và không tôn trọng công sức của tôi.", 0, createdAt),
        node("sample_chores_interpretation_2", "sample_chores_fact_2", "INTERPRETATION", "Cũng có thể việc phân chia trách nhiệm chưa rõ và cả hai đang mặc định khác nhau.", 1, createdAt),
        node("sample_chores_belief_1", "sample_chores_interpretation_1", "BELIEF", "Nếu yêu thương gia đình thì phải tự nhìn thấy việc cần làm.", 0, createdAt),
        node("sample_chores_belief_2", "sample_chores_interpretation_2", "BELIEF", "Công bằng trong gia đình cần được nói rõ, không chỉ kỳ vọng người kia tự đoán.", 1, createdAt),
        node("sample_chores_emotion_1", "sample_chores_belief_1", "EMOTION", "Tức, tủi thân, cảm giác mình gánh hết.", 0, createdAt),
        node("sample_chores_action_1", "sample_chores_emotion_1", "ACTION", "Tôi nói mỉa: 'Nhà này chắc có mỗi tôi biết rửa bát.'", 0, createdAt),
        node("sample_chores_consequence_1", "sample_chores_action_1", "CONSEQUENCE", "Người kia phòng thủ, cuộc nói chuyện chuyển thành đổ lỗi.", 0, createdAt),
        node("sample_chores_action_2", "sample_chores_belief_2", "ACTION", "Tôi có thể đề nghị chia lịch việc nhà cụ thể cho tuần này.", 1, createdAt),
        node("sample_chores_consequence_2", "sample_chores_action_2", "CONSEQUENCE", "Vấn đề chuyển từ trách móc nhân cách sang thoả thuận hành vi cụ thể.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_spouse_money",
      title: "Mâu thuẫn tiền bạc",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_money_root",
      nodes: [
        node("sample_money_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ khoản chi lớn phải hỏi trước; bạn đời có thể nghĩ đây là khoản cá nhân và chưa có quy tắc chung rõ ràng.", 0, createdAt),
        node("sample_money_fact_1", "sample_money_root", "BELIEF", "Ý kiến của tôi: Khoản chi lớn phải hỏi trước để tôn trọng gia đình.", 0, createdAt),
        node("sample_money_fact_2", "sample_money_root", "BELIEF", "Ý kiến của bạn đời: Đây là khoản cá nhân và hai người chưa thống nhất quy tắc chung.", 1, createdAt),
        node("sample_money_interpretation_1", "sample_money_fact_1", "INTERPRETATION", "Tôi diễn giải rằng người kia ích kỷ và không nghĩ đến gia đình.", 0, createdAt),
        node("sample_money_interpretation_2", "sample_money_fact_2", "INTERPRETATION", "Có thể người kia xem đây là khoản cá nhân, còn tôi xem là khoản chung.", 1, createdAt),
        node("sample_money_belief_1", "sample_money_interpretation_1", "BELIEF", "Người có trách nhiệm phải luôn hỏi trước khi tiêu khoản lớn.", 0, createdAt),
        node("sample_money_belief_2", "sample_money_interpretation_2", "BELIEF", "Minh bạch tài chính cần quy ước chung, không chỉ dựa vào cảm giác đúng sai của một người.", 1, createdAt),
        node("sample_money_emotion_1", "sample_money_belief_1", "EMOTION", "Bất an, giận, sợ mất kiểm soát tài chính.", 0, createdAt),
        node("sample_money_action_1", "sample_money_emotion_1", "ACTION", "Tôi kiểm tra sao kê và chất vấn bằng giọng buộc tội.", 0, createdAt),
        node("sample_money_consequence_1", "sample_money_action_1", "CONSEQUENCE", "Người kia cảm thấy bị kiểm soát, còn tôi vẫn không yên tâm.", 0, createdAt),
        node("sample_money_action_2", "sample_money_belief_2", "ACTION", "Tôi có thể đề xuất ngưỡng chi tiêu cần trao đổi trước, ví dụ trên 1 triệu đồng.", 1, createdAt),
        node("sample_money_consequence_2", "sample_money_action_2", "CONSEQUENCE", "Gia đình có quy tắc rõ hơn và giảm tranh cãi ở lần sau.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_in_laws_boundary",
      title: "Ông bà can thiệp cách nuôi con",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_inlaws_root",
      nodes: [
        node("sample_inlaws_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ bố mẹ mới là người quyết định cách nuôi con; ông bà nghĩ kinh nghiệm cũ của mình vẫn đúng và đang giúp cháu.", 0, createdAt),
        node("sample_inlaws_fact_1", "sample_inlaws_root", "BELIEF", "Ý kiến của tôi: Bố mẹ mới là người quyết định quy tắc nuôi con.", 0, createdAt),
        node("sample_inlaws_action_0", "sample_inlaws_fact_1", "ACTION", "Tôi nhắc lại quy tắc với ông bà ngay khi thấy ông bà làm khác ý mình.", 0, createdAt),
        node("sample_inlaws_consequence_0", "sample_inlaws_action_0", "CONSEQUENCE", "Quy tắc của bố mẹ rõ hơn, nhưng nếu nói quá căng thì quan hệ với ông bà dễ bị tổn thương.", 0, createdAt),
        node("sample_inlaws_fact_2", "sample_inlaws_root", "BELIEF", "Ý kiến của ông bà: Kinh nghiệm cũ vẫn đúng và ông bà đang thương cháu.", 1, createdAt),
        node("sample_inlaws_interpretation_1", "sample_inlaws_fact_2", "INTERPRETATION", "Tôi diễn giải rằng ông bà coi thường vai trò làm cha mẹ của tôi.", 0, createdAt),
        node("sample_inlaws_interpretation_2", "sample_inlaws_fact_2", "INTERPRETATION", "Có thể ông bà đang thể hiện tình thương bằng kinh nghiệm cũ, dù cách đó không phù hợp.", 1, createdAt),
        node("sample_inlaws_belief_1", "sample_inlaws_interpretation_1", "BELIEF", "Nếu tôi không phản ứng mạnh, mọi người sẽ tiếp tục vượt ranh giới.", 0, createdAt),
        node("sample_inlaws_belief_2", "sample_inlaws_interpretation_2", "BELIEF", "Ranh giới có thể được nói rõ mà vẫn giữ sự tôn trọng.", 1, createdAt),
        node("sample_inlaws_emotion_1", "sample_inlaws_belief_1", "EMOTION", "Bực, căng thẳng, cảm giác bị phủ nhận.", 0, createdAt),
        node("sample_inlaws_action_1", "sample_inlaws_emotion_1", "ACTION", "Tôi nói gay gắt trước mặt con và trách ông bà không nghe lời.", 0, createdAt),
        node("sample_inlaws_consequence_1", "sample_inlaws_action_1", "CONSEQUENCE", "Không khí gia đình căng, con chứng kiến người lớn tranh cãi.", 0, createdAt),
        node("sample_inlaws_action_2", "sample_inlaws_belief_2", "ACTION", "Tôi có thể nói riêng: 'Con biết ông bà thương cháu, nhưng chuyện đồ ngọt xin để bố mẹ quyết định.'", 1, createdAt),
        node("sample_inlaws_consequence_2", "sample_inlaws_action_2", "CONSEQUENCE", "Thông điệp về ranh giới rõ hơn mà ít làm tổn thương quan hệ.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_child_screen_time",
      title: "Con dùng điện thoại quá nhiều",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_screen_root",
      nodes: [
        node("sample_screen_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ con phải dừng điện thoại ngay khi cha mẹ yêu cầu; con có thể nghĩ mình chỉ cần thêm chút thời gian để kết thúc việc đang làm.", 0, createdAt),
        node("sample_screen_fact_1", "sample_screen_root", "BELIEF", "Ý kiến của tôi: Con phải dừng điện thoại ngay khi cha mẹ yêu cầu.", 0, createdAt),
        node("sample_screen_fact_2", "sample_screen_root", "BELIEF", "Ý kiến của con: Con cần thêm ít phút để kết thúc việc đang làm.", 1, createdAt),
        node("sample_screen_interpretation_1", "sample_screen_fact_2", "INTERPRETATION", "Tôi diễn giải rằng con nghiện điện thoại và không tôn trọng kỷ luật.", 0, createdAt),
        node("sample_screen_interpretation_2", "sample_screen_fact_1", "INTERPRETATION", "Có thể con đang dùng điện thoại để xả stress hoặc thiếu hoạt động thay thế hấp dẫn.", 1, createdAt),
        node("sample_screen_belief_1", "sample_screen_interpretation_1", "BELIEF", "Trẻ ngoan phải dừng ngay khi cha mẹ yêu cầu.", 0, createdAt),
        node("sample_screen_belief_2", "sample_screen_interpretation_2", "BELIEF", "Tự kiểm soát cần được luyện bằng quy tắc rõ, môi trường hỗ trợ và hậu quả nhất quán.", 1, createdAt),
        node("sample_screen_emotion_1", "sample_screen_belief_1", "EMOTION", "Lo, giận, sợ con hư.", 0, createdAt),
        node("sample_screen_action_1", "sample_screen_emotion_1", "ACTION", "Tôi giật điện thoại và mắng con thiếu ý thức.", 0, createdAt),
        node("sample_screen_consequence_1", "sample_screen_action_1", "CONSEQUENCE", "Con phản kháng hoặc lén dùng tiếp, còn tôi càng phải kiểm soát nhiều hơn.", 0, createdAt),
        node("sample_screen_action_2", "sample_screen_belief_2", "ACTION", "Tôi có thể cùng con đặt lịch dùng, cảnh báo trước 10 phút và thống nhất hậu quả nếu vi phạm.", 1, createdAt),
        node("sample_screen_consequence_2", "sample_screen_action_2", "CONSEQUENCE", "Con có cơ hội học tự quản thay vì chỉ sợ bị tịch thu.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_child_grades",
      title: "Áp lực điểm số của con",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_grades_root",
      nodes: [
        node("sample_grades_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ điểm thấp cho thấy con chưa đủ cố gắng; con có thể nghĩ mình đang gặp khó hoặc chưa biết cách học hiệu quả.", 0, createdAt),
        node("sample_grades_fact_1", "sample_grades_root", "BELIEF", "Ý kiến của tôi: Điểm thấp cho thấy con chưa cố gắng đủ.", 0, createdAt),
        node("sample_grades_fact_2", "sample_grades_root", "BELIEF", "Ý kiến của con: Con có thể đang hổng kiến thức hoặc chưa biết cách học.", 1, createdAt),
        node("sample_grades_interpretation_1", "sample_grades_fact_1", "INTERPRETATION", "Tôi diễn giải rằng con lười và không cố gắng.", 0, createdAt),
        node("sample_grades_interpretation_2", "sample_grades_fact_2", "INTERPRETATION", "Có thể con bị hổng một phần kiến thức hoặc chưa biết cách học hiệu quả.", 1, createdAt),
        node("sample_grades_belief_1", "sample_grades_interpretation_1", "BELIEF", "Điểm thấp nghĩa là con thiếu trách nhiệm.", 0, createdAt),
        node("sample_grades_belief_2", "sample_grades_interpretation_2", "BELIEF", "Điểm số là dữ liệu để tìm chỗ cần hỗ trợ, không phải kết luận về giá trị của con.", 1, createdAt),
        node("sample_grades_emotion_1", "sample_grades_belief_1", "EMOTION", "Thất vọng, xấu hổ, lo cho tương lai của con.", 0, createdAt),
        node("sample_grades_action_1", "sample_grades_emotion_1", "ACTION", "Tôi so sánh con với bạn khác và nói con làm bố mẹ buồn.", 0, createdAt),
        node("sample_grades_consequence_1", "sample_grades_action_1", "CONSEQUENCE", "Con sợ học, giấu điểm hoặc thấy mình không đủ tốt.", 0, createdAt),
        node("sample_grades_action_2", "sample_grades_belief_2", "ACTION", "Tôi có thể hỏi con sai phần nào và cùng lập kế hoạch ôn 20 phút mỗi ngày.", 1, createdAt),
        node("sample_grades_consequence_2", "sample_grades_action_2", "CONSEQUENCE", "Con nhận được hỗ trợ cụ thể và ít gắn điểm số với sự xấu hổ.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_sibling_fight",
      title: "Anh chị em tranh giành",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_sibling_root",
      nodes: [
        node("sample_sibling_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ các con phải tự biết nhường nhau; mỗi con lại nghĩ mình cũng có quyền chơi món đồ đó trước.", 0, createdAt),
        node("sample_sibling_fact_1", "sample_sibling_root", "BELIEF", "Ý kiến của tôi: Anh chị em phải tự biết nhường nhau.", 0, createdAt),
        node("sample_sibling_fact_2", "sample_sibling_root", "BELIEF", "Ý kiến của các con: Mỗi bé đều nghĩ mình có quyền chơi món đồ đó trước.", 1, createdAt),
        node("sample_sibling_interpretation_1", "sample_sibling_fact_2", "INTERPRETATION", "Tôi diễn giải rằng các con ích kỷ và cố tình làm tôi phát điên.", 0, createdAt),
        node("sample_sibling_interpretation_2", "sample_sibling_fact_1", "INTERPRETATION", "Có thể các con chưa biết thương lượng lượt chơi và cần người lớn dạy kỹ năng.", 1, createdAt),
        node("sample_sibling_belief_1", "sample_sibling_interpretation_1", "BELIEF", "Anh chị em trong nhà phải tự biết nhường nhịn.", 0, createdAt),
        node("sample_sibling_belief_2", "sample_sibling_interpretation_2", "BELIEF", "Nhường nhịn là kỹ năng cần luyện, không tự nhiên xuất hiện khi trẻ đang kích động.", 1, createdAt),
        node("sample_sibling_emotion_1", "sample_sibling_belief_1", "EMOTION", "Mệt, cáu, bất lực.", 0, createdAt),
        node("sample_sibling_action_1", "sample_sibling_emotion_1", "ACTION", "Tôi quát cả hai và cất hết đồ chơi.", 0, createdAt),
        node("sample_sibling_consequence_1", "sample_sibling_action_1", "CONSEQUENCE", "Hai con ngừng tranh lúc đó nhưng vẫn chưa học cách giải quyết lần sau.", 0, createdAt),
        node("sample_sibling_action_2", "sample_sibling_belief_2", "ACTION", "Tôi có thể tách hai con bình tĩnh, đặt lượt chơi 10 phút và yêu cầu từng bé nói nhu cầu.", 1, createdAt),
        node("sample_sibling_consequence_2", "sample_sibling_action_2", "CONSEQUENCE", "Trẻ học gọi tên nhu cầu, chờ lượt và sửa hành vi cụ thể.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_silent_spouse",
      title: "Bạn đời im lặng khi có xung đột",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_silent_root",
      nodes: [
        node("sample_silent_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ im lặng là lạnh nhạt và trừng phạt; bạn đời có thể nghĩ im lặng là cách tạm dừng để khỏi nói điều làm nhau đau.", 0, createdAt),
        node("sample_silent_fact_1", "sample_silent_root", "BELIEF", "Ý kiến của tôi: Im lặng khi cãi nhau là lạnh nhạt và trừng phạt.", 0, createdAt),
        node("sample_silent_fact_2", "sample_silent_root", "BELIEF", "Ý kiến của bạn đời: Tạm im lặng là cách hạ nhiệt để khỏi nói lời làm nhau đau.", 1, createdAt),
        node("sample_silent_interpretation_1", "sample_silent_fact_1", "INTERPRETATION", "Tôi diễn giải rằng người kia lạnh nhạt và muốn trừng phạt tôi.", 0, createdAt),
        node("sample_silent_interpretation_2", "sample_silent_fact_2", "INTERPRETATION", "Có thể người kia đang quá tải cảm xúc và chưa biết cách quay lại cuộc trò chuyện.", 1, createdAt),
        node("sample_silent_belief_1", "sample_silent_interpretation_1", "BELIEF", "Nếu yêu nhau thì không được im lặng khi tôi đang cần câu trả lời.", 0, createdAt),
        node("sample_silent_belief_2", "sample_silent_interpretation_2", "BELIEF", "Tạm dừng có thể lành mạnh nếu có hẹn thời điểm quay lại nói chuyện.", 1, createdAt),
        node("sample_silent_emotion_1", "sample_silent_belief_1", "EMOTION", "Bị bỏ rơi, lo lắng, tức giận.", 0, createdAt),
        node("sample_silent_action_1", "sample_silent_emotion_1", "ACTION", "Tôi liên tục hỏi dồn và nói người kia vô trách nhiệm.", 0, createdAt),
        node("sample_silent_consequence_1", "sample_silent_action_1", "CONSEQUENCE", "Người kia càng rút lui, tôi càng hoảng và căng thẳng hơn.", 0, createdAt),
        node("sample_silent_action_2", "sample_silent_belief_2", "ACTION", "Tôi có thể nói: 'Mình tạm dừng 30 phút, sau đó quay lại nói tiếp được không?'", 1, createdAt),
        node("sample_silent_consequence_2", "sample_silent_action_2", "CONSEQUENCE", "Cả hai có không gian hạ nhiệt mà không biến im lặng thành bỏ rơi.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_care_for_parents",
      title: "Chăm sóc cha mẹ già",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_eldercare_root",
      nodes: [
        node("sample_eldercare_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ anh chị em phải trực tiếp chia phần chăm sóc cha mẹ; họ có thể nghĩ gửi tiền hoặc hỗ trợ cách khác cũng là góp phần.", 0, createdAt),
        node("sample_eldercare_fact_1", "sample_eldercare_root", "BELIEF", "Ý kiến của tôi: Anh chị em phải trực tiếp chia việc chăm sóc cha mẹ.", 0, createdAt),
        node("sample_eldercare_action_0", "sample_eldercare_fact_1", "ACTION", "Tôi yêu cầu mọi người thay phiên trực tiếp đưa cha mẹ đi khám và chăm sóc.", 0, createdAt),
        node("sample_eldercare_consequence_0", "sample_eldercare_action_0", "CONSEQUENCE", "Việc chăm sóc có thể công bằng hơn, nhưng nếu chỉ yêu cầu mà không bàn khả năng từng người thì dễ thành trách móc.", 0, createdAt),
        node("sample_eldercare_fact_2", "sample_eldercare_root", "BELIEF", "Ý kiến của họ: Gửi tiền hoặc hỗ trợ cách khác cũng là góp phần chăm sóc.", 1, createdAt),
        node("sample_eldercare_interpretation_1", "sample_eldercare_fact_2", "INTERPRETATION", "Tôi diễn giải rằng họ vô tâm và đẩy hết trách nhiệm cho tôi.", 0, createdAt),
        node("sample_eldercare_interpretation_2", "sample_eldercare_fact_2", "INTERPRETATION", "Có thể mỗi người đang đóng góp theo cách khác nhưng chưa có phân công minh bạch.", 1, createdAt),
        node("sample_eldercare_belief_1", "sample_eldercare_interpretation_1", "BELIEF", "Ai không trực tiếp chăm sóc thì là bất hiếu hoặc ích kỷ.", 0, createdAt),
        node("sample_eldercare_belief_2", "sample_eldercare_interpretation_2", "BELIEF", "Trách nhiệm gia đình cần được phân chia theo khả năng, thời gian và tiền bạc cụ thể.", 1, createdAt),
        node("sample_eldercare_emotion_1", "sample_eldercare_belief_1", "EMOTION", "Tủi thân, kiệt sức, giận dữ.", 0, createdAt),
        node("sample_eldercare_action_1", "sample_eldercare_emotion_1", "ACTION", "Tôi nhắn trong nhóm gia đình bằng giọng trách móc.", 0, createdAt),
        node("sample_eldercare_consequence_1", "sample_eldercare_action_1", "CONSEQUENCE", "Mọi người phòng thủ, cuộc trao đổi dễ thành so đo công lao.", 0, createdAt),
        node("sample_eldercare_action_2", "sample_eldercare_belief_2", "ACTION", "Tôi có thể lập danh sách việc cần làm hằng tháng và đề nghị từng người nhận phần cụ thể.", 1, createdAt),
        node("sample_eldercare_consequence_2", "sample_eldercare_action_2", "CONSEQUENCE", "Vấn đề trở nên đo được, dễ thương lượng hơn và giảm cảm giác bị bỏ mặc.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_family_comparison",
      title: "Bị so sánh với người khác",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_compare_root",
      nodes: [
        node("sample_compare_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ việc so sánh làm mình bị hạ thấp; mẹ có thể nghĩ so sánh là cách nhắc tôi cố gắng hơn.", 0, createdAt),
        node("sample_compare_fact_1", "sample_compare_root", "BELIEF", "Ý kiến của tôi: So sánh làm tôi bị hạ thấp và tổn thương.", 0, createdAt),
        node("sample_compare_fact_2", "sample_compare_root", "BELIEF", "Ý kiến của mẹ: So sánh là cách nhắc tôi cố gắng hơn cho tương lai.", 1, createdAt),
        node("sample_compare_action_0", "sample_compare_fact_2", "ACTION", "Mẹ tiếp tục dùng ví dụ của người khác để thúc đẩy tôi thay đổi.", 0, createdAt),
        node("sample_compare_consequence_0", "sample_compare_action_0", "CONSEQUENCE", "Mẹ có thể nghĩ mình đang khuyên con, nhưng tôi dễ thấy xấu hổ và xa cách hơn.", 0, createdAt),
        node("sample_compare_interpretation_1", "sample_compare_fact_1", "INTERPRETATION", "Tôi diễn giải rằng mẹ thất vọng và xem tôi là kém cỏi.", 0, createdAt),
        node("sample_compare_interpretation_2", "sample_compare_fact_1", "INTERPRETATION", "Có thể mẹ đang lo cho tương lai của tôi nhưng dùng cách nói gây tổn thương.", 1, createdAt),
        node("sample_compare_belief_1", "sample_compare_interpretation_1", "BELIEF", "Nếu gia đình yêu thương tôi thì họ phải công nhận tôi, không được so sánh.", 0, createdAt),
        node("sample_compare_belief_2", "sample_compare_interpretation_2", "BELIEF", "Tôi có thể đặt ranh giới với cách nói làm tổn thương mà không phủ nhận sự lo lắng của mẹ.", 1, createdAt),
        node("sample_compare_emotion_1", "sample_compare_belief_1", "EMOTION", "Xấu hổ, giận, muốn bỏ đi.", 0, createdAt),
        node("sample_compare_action_1", "sample_compare_emotion_1", "ACTION", "Tôi đáp trả: 'Vậy mẹ nhận anh ấy làm con đi.'", 0, createdAt),
        node("sample_compare_consequence_1", "sample_compare_action_1", "CONSEQUENCE", "Mẹ tổn thương, tôi vẫn không được hiểu đúng nhu cầu của mình.", 0, createdAt),
        node("sample_compare_action_2", "sample_compare_belief_2", "ACTION", "Tôi có thể nói riêng: 'Khi mẹ so sánh trước mặt mọi người, con thấy xấu hổ và khó nghe lời khuyên.'", 1, createdAt),
        node("sample_compare_consequence_2", "sample_compare_action_2", "CONSEQUENCE", "Tôi bảo vệ lòng tự trọng bằng cách nói rõ tác động thay vì tấn công lại.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_parenting_style_conflict",
      title: "Vợ chồng bất đồng cách dạy con",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_parenting_style_root",
      nodes: [
        node("sample_parenting_style_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ cần kỷ luật rõ và có hậu quả khi con sai; bạn đời nghĩ cần giữ kết nối, tránh làm con áp lực trước.", 0, createdAt),
        node("sample_parenting_style_fact_1", "sample_parenting_style_root", "BELIEF", "Ý kiến của tôi: Con cần kỷ luật rõ và có hậu quả khi không làm bài.", 0, createdAt),
        node("sample_parenting_style_action_0", "sample_parenting_style_fact_1", "ACTION", "Tôi đặt hình phạt hoặc cắt thời gian chơi để con nhớ bài học.", 0, createdAt),
        node("sample_parenting_style_consequence_0", "sample_parenting_style_action_0", "CONSEQUENCE", "Con có thể làm theo quy tắc hơn, nhưng nếu thiếu giải thích và kết nối thì dễ chống đối hoặc sợ sai.", 0, createdAt),
        node("sample_parenting_style_fact_2", "sample_parenting_style_root", "BELIEF", "Ý kiến của bạn đời: Trước hết cần giữ kết nối và tránh làm con áp lực.", 1, createdAt),
        node("sample_parenting_style_interpretation_1", "sample_parenting_style_fact_2", "INTERPRETATION", "Tôi diễn giải rằng bạn đời phá uy của tôi và đứng về phía con.", 0, createdAt),
        node("sample_parenting_style_interpretation_2", "sample_parenting_style_fact_2", "INTERPRETATION", "Có thể bạn đời cũng muốn tốt cho con nhưng ưu tiên sự kết nối và sợ con bị áp lực.", 1, createdAt),
        node("sample_parenting_style_belief_1", "sample_parenting_style_interpretation_1", "BELIEF", "Cha mẹ phải thống nhất tuyệt đối ngay lúc đó, nếu không con sẽ coi thường kỷ luật.", 0, createdAt),
        node("sample_parenting_style_belief_2", "sample_parenting_style_interpretation_2", "BELIEF", "Hai vợ chồng có thể cùng mục tiêu nhưng khác cách làm; bất đồng nên được bàn riêng, không biến con thành phe thứ ba.", 1, createdAt),
        node("sample_parenting_style_emotion_1", "sample_parenting_style_belief_1", "EMOTION", "Tức giận, bị phản bội, lo mất vai trò làm cha mẹ.", 0, createdAt),
        node("sample_parenting_style_action_1", "sample_parenting_style_emotion_1", "ACTION", "Tôi tranh cãi với bạn đời ngay trước mặt con và nhấn mạnh rằng cách của tôi mới đúng.", 0, createdAt),
        node("sample_parenting_style_consequence_1", "sample_parenting_style_action_1", "CONSEQUENCE", "Con thấy cha mẹ chia rẽ, vấn đề bài tập bị lu mờ bởi cuộc tranh thắng thua của người lớn.", 0, createdAt),
        node("sample_parenting_style_action_2", "sample_parenting_style_belief_2", "ACTION", "Tôi có thể nói: 'Mình tạm thống nhất nhắc con hoàn thành bài, tối nay hai vợ chồng bàn riêng cách xử lý lâu dài.'", 1, createdAt),
        node("sample_parenting_style_consequence_2", "sample_parenting_style_action_2", "CONSEQUENCE", "Cha mẹ giữ được mặt trận ổn định trước con và có không gian tìm phương pháp chung.", 0, createdAt),
        node("sample_parenting_style_fact_3", "sample_parenting_style_root", "FACT", "Cả hai đều nói rằng muốn con có trách nhiệm và cảm thấy được yêu thương.", 2, createdAt),
        node("sample_parenting_style_interpretation_3", "sample_parenting_style_fact_3", "INTERPRETATION", "Điểm chung không phải là cách phạt hay không phạt, mà là mong muốn con trưởng thành lành mạnh.", 0, createdAt),
        node("sample_parenting_style_action_3", "sample_parenting_style_interpretation_3", "ACTION", "Hai vợ chồng có thể thống nhất 3 nguyên tắc: không phủ nhận nhau trước mặt con, hậu quả rõ ràng, và luôn có bước kết nối sau kỷ luật.", 0, createdAt),
        node("sample_parenting_style_consequence_3", "sample_parenting_style_action_3", "CONSEQUENCE", "Con nhận được giới hạn nhất quán mà vẫn cảm thấy cha mẹ là một đội.", 0, createdAt)
      ]
    },
    {
      id: "sample_tree_husband_gentle_parenting",
      title: "Chồng muốn vợ dạy con bao dung hơn",
      createdAt,
      updatedAt: createdAt,
      rootId: "sample_gentle_parenting_root",
      nodes: [
        node("sample_gentle_parenting_root", null, "ROOT", "Hai ý kiến đối lập: Tôi nghĩ nên dạy con bằng bao dung, thuyết phục và làm gương; vợ nghĩ cần la mắng hoặc phạt để con nhớ lỗi và có kỷ luật.", 0, createdAt),
        node("sample_gentle_parenting_fact_1", "sample_gentle_parenting_root", "BELIEF", "Ý kiến của tôi: Nên dạy con bằng bao dung, thuyết phục, giảng giải và làm gương.", 0, createdAt),
        node("sample_gentle_parenting_action_0", "sample_gentle_parenting_fact_1", "ACTION", "Tôi can thiệp để con được nghe giải thích nhẹ nhàng hơn thay vì bị la mắng.", 0, createdAt),
        node("sample_gentle_parenting_consequence_0", "sample_gentle_parenting_action_0", "CONSEQUENCE", "Con có thể bớt sợ, nhưng nếu tôi phủ nhận vợ trước mặt con thì vợ chồng dễ đối đầu hơn.", 0, createdAt),
        node("sample_gentle_parenting_fact_2", "sample_gentle_parenting_root", "BELIEF", "Ý kiến của vợ: Cần la mắng hoặc phạt để con nhớ lỗi và có kỷ luật.", 1, createdAt),
        node("sample_gentle_parenting_fact_3", "sample_gentle_parenting_root", "FACT", "Sau đó con khóc, cúi mặt và tránh nhìn cả hai vợ chồng.", 2, createdAt),
        node("sample_gentle_parenting_interpretation_1", "sample_gentle_parenting_fact_2", "INTERPRETATION", "Tôi diễn giải rằng vợ đang làm tổn thương con và dạy con bằng sợ hãi.", 0, createdAt),
        node("sample_gentle_parenting_interpretation_2", "sample_gentle_parenting_fact_2", "INTERPRETATION", "Có thể vợ đang quá mệt, lo con thiếu kỷ luật và tin rằng nghiêm khắc là cần thiết.", 1, createdAt),
        node("sample_gentle_parenting_belief_1", "sample_gentle_parenting_interpretation_1", "BELIEF", "La mắng và trừng phạt khiến con sợ cha mẹ, không thật sự học được trách nhiệm.", 0, createdAt),
        node("sample_gentle_parenting_belief_2", "sample_gentle_parenting_interpretation_2", "BELIEF", "Vợ có thể đang bảo vệ giá trị kỷ luật, nhưng cách thể hiện bị cảm xúc dẫn dắt.", 1, createdAt),
        node("sample_gentle_parenting_belief_3", "sample_gentle_parenting_root", "BELIEF", "Dạy con tốt cần có giới hạn rõ ràng đi cùng bao dung, thuyết phục, giảng giải và làm gương.", 3, createdAt),
        node("sample_gentle_parenting_emotion_1", "sample_gentle_parenting_belief_1", "EMOTION", "Tôi xót con, giận vợ, lo rằng con sẽ tổn thương lâu dài.", 0, createdAt),
        node("sample_gentle_parenting_action_1", "sample_gentle_parenting_emotion_1", "ACTION", "Tôi can thiệp ngay và nói trước mặt con rằng vợ đang sai, quá nóng tính.", 0, createdAt),
        node("sample_gentle_parenting_consequence_1", "sample_gentle_parenting_action_1", "CONSEQUENCE", "Vợ cảm thấy bị phủ nhận vai trò làm mẹ, con thấy cha mẹ đối đầu và vấn đề ban đầu bị lu mờ.", 0, createdAt),
        node("sample_gentle_parenting_action_2", "sample_gentle_parenting_belief_2", "ACTION", "Tôi có thể đợi lúc riêng tư và nói: 'Anh thấy em rất muốn con có trách nhiệm, nhưng khi mình la mắng, con có vẻ chỉ sợ chứ chưa hiểu lỗi.'", 1, createdAt),
        node("sample_gentle_parenting_consequence_2", "sample_gentle_parenting_action_2", "CONSEQUENCE", "Cuộc nói chuyện ít công kích hơn vì bắt đầu từ việc công nhận ý định tốt của vợ.", 0, createdAt),
        node("sample_gentle_parenting_action_3", "sample_gentle_parenting_belief_3", "ACTION", "Hai vợ chồng có thể thống nhất cách xử lý: bình tĩnh gọi tên lỗi, yêu cầu con sửa hậu quả, giải thích lý do và cha mẹ làm gương xin lỗi khi mình nóng giận.", 2, createdAt),
        node("sample_gentle_parenting_consequence_3", "sample_gentle_parenting_action_3", "CONSEQUENCE", "Con học trách nhiệm qua sửa lỗi và quan sát cách cha mẹ kiểm soát cảm xúc, không chỉ qua nỗi sợ bị phạt.", 0, createdAt),
        node("sample_gentle_parenting_interpretation_3", "sample_gentle_parenting_fact_3", "INTERPRETATION", "Phản ứng khóc của con là tín hiệu cần xem lại cách dạy, nhưng chưa đủ để kết luận vợ là người mẹ xấu.", 0, createdAt),
        node("sample_gentle_parenting_action_4", "sample_gentle_parenting_interpretation_3", "ACTION", "Tôi có thể hỏi con sau khi bình tĩnh: 'Con hiểu lỗi ở đâu? Lần sau con có thể làm gì khác?'", 0, createdAt),
        node("sample_gentle_parenting_consequence_4", "sample_gentle_parenting_action_4", "CONSEQUENCE", "Trọng tâm chuyển từ trừng phạt sang học bài học và phục hồi kết nối.", 0, createdAt)
      ]
    }
  ];

  return trees.map(normalizeTree);
}

function mergeSampleTrees(trees) {
  const sampleTrees = createSampleTrees();
  const sampleIds = new Set(sampleTrees.map((tree) => tree.id));
  const userTrees = trees.filter((tree) => !sampleIds.has(tree.id));
  return [...sampleTrees, ...userTrees];
}

const defaultData = {
  trees: createSampleTrees(),
  moduleState: {
    conviction: {
      text: "",
      certainty: 50,
      evidenceFor: "",
      evidenceAgainst: "",
      egoCost: "",
      changeCondition: "",
      balancedThought: "",
      choices: {},
      answers: {}
    },
    healing: {
      emotionalState: "",
      checks: {},
      boundaries: {},
      repair: {}
    },
    quiz: {
      version: QUIZ_STATE_VERSION,
      treeId: "",
      path: [],
      choices: {}
    },
    relationship: {
      situation: "",
      myView: "",
      myNeed: "",
      otherView: "",
      otherNeed: "",
      conflictLoop: "",
      myResponsibility: "",
      needStatement: "",
      commitment: "",
      choices: {},
      checks: {}
    },
    truth: {
      situation: "",
      truthValue: "",
      selfImage: "",
      mirrorTest: "",
      admitCost: "",
      truthAction: "",
      choices: {},
      answers: {}
    }
  }
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeQuizState(quizState) {
  if (quizState?.version !== QUIZ_STATE_VERSION) {
    return clone(defaultData.moduleState.quiz);
  }

  return {
    ...clone(defaultData.moduleState.quiz),
    ...quizState,
    path: Array.isArray(quizState.path) ? quizState.path : []
  };
}

function normalizeData(data, options = {}) {
  const trees = Array.isArray(data?.trees) ? data.trees : [];
  const normalizedTrees = (options.includeSamples ? mergeSampleTrees(trees) : trees)
    .filter((tree) => !REMOVED_SAMPLE_TREE_IDS.has(tree.id))
    .map(normalizeTree);

  return {
    ...clone(defaultData),
    ...data,
    moduleState: {
      ...clone(defaultData.moduleState),
      ...(data?.moduleState || {}),
      conviction: {
        ...clone(defaultData.moduleState.conviction),
        ...(data?.moduleState?.conviction || {})
      },
      healing: {
        ...clone(defaultData.moduleState.healing),
        ...(data?.moduleState?.healing || {})
      },
      relationship: {
        ...clone(defaultData.moduleState.relationship),
        ...(data?.moduleState?.relationship || {})
      },
      quiz: normalizeQuizState(data?.moduleState?.quiz),
      truth: {
        ...clone(defaultData.moduleState.truth),
        ...(data?.moduleState?.truth || {})
      }
    },
    trees: options.seedEmpty && normalizedTrees.length === 0 ? createSampleTrees() : normalizedTrees
  };
}

function loadData() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? normalizeData(JSON.parse(raw), { includeSamples: true, seedEmpty: true }) : clone(defaultData);
  } catch (error) {
    console.warn("Không thể đọc LocalStorage, dùng dữ liệu mặc định.", error);
    return clone(defaultData);
  }
}

function saveData(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeData(data)));
}

function exportData(data) {
  return JSON.stringify(normalizeData(data), null, 2);
}

function importData(jsonText) {
  const parsed = JSON.parse(jsonText);
  const data = normalizeData(parsed);
  saveData(data);
  return data;
}

window.CognitiveStorage = {
  loadData,
  saveData,
  exportData,
  importData
};
})();
