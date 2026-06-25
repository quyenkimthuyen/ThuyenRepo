const LIFE_STAGES = [
  { id: 'primary_school', unlocked: false, storyCount: 0 },
  { id: 'middle_school', unlocked: false, storyCount: 0 },
  { id: 'high_school', unlocked: true, storyCount: 5 },
  { id: 'university', unlocked: false, storyCount: 0 },
  { id: 'working_adult', unlocked: false, storyCount: 0 },
  { id: 'family_life', unlocked: false, storyCount: 0 },
  { id: 'midlife', unlocked: false, storyCount: 0 },
  { id: 'retirement', unlocked: false, storyCount: 0 },
];

const STORIES = [
  // Story 1: The Night Before — Exams
  {
    id: 'hs-01',
    lifeStage: 'high_school',
    category: 'exams',
    title: { en: 'The Night Before', vi: 'Đêm Trước Kỳ Thi' },
    description: {
      en: 'Tomorrow is the math final. Your friend Lan is panicking. Your phone buzzes with a study group invite. Mom wants you in bed by ten.',
      vi: 'Ngày mai thi Toán cuối kỳ. Lan nhắn hoảng loạn nhờ giúp bài. Điện thoại reo — lời mời học nhóm. Mẹ bảo mười giờ phải ngủ.',
    },
    xpReward: 100,
    totalScenes: 12,
    startScene: 's01-01',
    characters: [
      { id: 'lan', name: { en: 'Lan', vi: 'Lan' }, color: '#e879a0', emoji: '👧' },
      { id: 'mom', name: { en: 'Mom', vi: 'Mẹ' }, color: '#f0a060', emoji: '👩' },
      { id: 'hung', name: { en: 'Mr. Hung', vi: 'Thầy Hùng' }, color: '#6090d0', emoji: '👨‍🏫' },
      { id: 'minh', name: { en: 'Minh', vi: 'Minh' }, color: '#70c090', emoji: '👦' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 's01-01',
        character: 'narrator',
        dialogue: {
          en: '11 PM. Your desk is covered in practice tests. The math final is tomorrow morning. Your eyes burn from reading the same problem for the third time.',
          vi: '11 giờ đêm. Bàn học chất đầy đề luyện. Ngày mai thi Toán. Mắt bạn cay xè vì đọc đi đọc lại cùng một bài toán lần thứ ba.',
        },
        nextScene: 's01-02',
      },
      {
        id: 's01-02',
        character: 'lan',
        dialogue: {
          en: '"I\'m going to fail. I don\'t understand chapter 7 at all. Can you come over? I need help."',
          vi: '"Mình sẽ trượt mất. Mình chẳng hiểu chương 7 gì cả. Bạn sang nhà mình được không? Mình cần giúp đỡ."',
        },
        choices: [
          {
            id: 'c01-a',
            text: { en: '"Okay, I\'ll be there in 20 minutes."', vi: '"Được, mình sang trong 20 phút."' },
            tags: ['empathy', 'responsibility'],
            effects: { relationships: { lan: { friendship: 10, trust: 5 } }, personality: { empathy: 3, responsibility: 2 } },
            nextScene: 's01-03a',
          },
          {
            id: 'c01-b',
            text: { en: '"I can\'t tonight. But I\'ll send you my notes on chapter 7."', vi: '"Tối nay mình không được. Nhưng mình gửi bạn ghi chú chương 7."' },
            tags: ['discipline', 'cooperation'],
            effects: { relationships: { lan: { friendship: 3, trust: 5 } }, personality: { discipline: 2, cooperation: 2 } },
            nextScene: 's01-03b',
          },
          {
            id: 'c01-c',
            text: { en: '"You should have studied earlier. I need to sleep."', vi: '"Bạn nên học sớm hơn. Mình cần ngủ."' },
            tags: ['assertiveness', 'avoid_conflict'],
            effects: { relationships: { lan: { friendship: -8, trust: -5 } }, personality: { assertiveness: 2 } },
            delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { lan: { trust: -10, friendship: -5 } } }, message: { en: 'Lan didn\'t reply to your texts the next day.', vi: 'Lan không trả lời tin nhắn của bạn ngày hôm sau.' } }],
            nextScene: 's01-03c',
          },
        ],
      },
      {
        id: 's01-03a',
        character: 'narrator',
        dialogue: {
          en: 'You grab your jacket. At Lan\'s house, she\'s crying over her textbook. You spend two hours explaining derivatives. She finally smiles.',
          vi: 'Bạn lấy áo khoác. Ở nhà Lan, cô ấy đang khóc trước sách giáo khoa. Bạn dành hai tiếng giải thích đạo hàm. Cuối cùng cô ấy cũng mỉm cười.',
        },
        nextScene: 's01-04',
      },
      {
        id: 's01-03b',
        character: 'lan',
        dialogue: {
          en: '"Thanks... I guess that helps. Good luck tomorrow." She sounds disappointed but understanding.',
          vi: '"Cảm ơn... Chắc cũng được. Chúc bạn may mắn ngày mai." Giọng cô ấy thất vọng nhưng vẫn thông cảm.',
        },
        nextScene: 's01-04',
      },
      {
        id: 's01-03c',
        character: 'lan',
        dialogue: {
          en: '"Fine. Whatever." The message comes back cold. You stare at the screen for a moment, then put your phone down.',
          vi: '"Thôi kệ. Tùy bạn." Tin nhắn trả về lạnh lùng. Bạn nhìn màn hình một lúc, rồi đặt điện thoại xuống.',
        },
        nextScene: 's01-04',
      },
      {
        id: 's01-04',
        character: 'mom',
        dialogue: {
          en: '"It\'s almost midnight. You need sleep. No screen after 11:30." She stands in your doorway, arms crossed.',
          vi: '"Gần nửa đêm rồi. Con cần ngủ. Không dùng điện thoại sau 11:30." Mẹ đứng ở cửa phòng, khoanh tay.',
        },
        choices: [
          {
            id: 'c04-a',
            text: { en: '"Five more minutes, Mom. Just five."', vi: '"Năm phút nữa thôi mẹ. Chỉ năm phút."' },
            tags: ['short_term_gain', 'avoid_conflict'],
            effects: { relationships: { mom: { trust: -3 } }, personality: { discipline: -1 } },
            delayedConsequences: [{ triggerAfterScenes: 3, effects: { personality: { discipline: -2 } }, message: { en: 'You fell asleep at your desk. Your alarm didn\'t wake you properly.', vi: 'Bạn ngủ gục trên bàn. Báo thức không đánh thức bạn kịp.' } }],
            nextScene: 's01-05a',
          },
          {
            id: 'c04-b',
            text: { en: '"You\'re right. I\'ll set my alarm and sleep now."', vi: '"Mẹ nói đúng. Con đặt báo thức và đi ngủ ngay."' },
            tags: ['discipline', 'responsibility'],
            effects: { relationships: { mom: { trust: 8, respect: 5 } }, personality: { discipline: 3 } },
            nextScene: 's01-05b',
          },
        ],
      },
      {
        id: 's01-05a',
        character: 'narrator',
        dialogue: {
          en: 'You keep studying. At 1 AM, your head hits the desk. You don\'t remember falling asleep.',
          vi: 'Bạn tiếp tục học. Lúc 1 giờ sáng, đầu bạn chạm bàn. Bạn không nhớ mình đã ngủ thế nào.',
        },
        nextScene: 's01-06',
      },
      {
        id: 's01-05b',
        character: 'narrator',
        dialogue: {
          en: 'You close your books. For the first time tonight, your mind feels quiet. Sleep comes easily.',
          vi: 'Bạn đóng sách. Lần đầu tiên tối nay, đầu óc bạn thấy yên bình. Giấc ngủ đến dễ dàng.',
        },
        nextScene: 's01-06',
      },
      {
        id: 's01-06',
        character: 'narrator',
        dialogue: {
          en: 'Exam day. The classroom is silent except for shuffling papers. Question 5 stares at you — the exact type you struggled with last night.',
          vi: 'Ngày thi. Lớp học im lặng, chỉ có tiếng sột soạt giấy. Câu 5 nhìn bạn chằm chằm — đúng dạng bài bạn vật lộn đêm qua.',
        },
        choices: [
          {
            id: 'c06-a',
            text: { en: 'Take a breath. Work through it step by step.', vi: 'Hít thở. Giải từng bước một.' },
            tags: ['discipline', 'resilience'],
            effects: { personality: { discipline: 2, resilience: 3 } },
            nextScene: 's01-07',
          },
          {
            id: 'c06-b',
            text: { en: 'Glance at Minh\'s paper. Just for a hint.', vi: 'Liếc bài của Minh. Chỉ để tham khảo thôi.' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { relationships: { minh: { trust: -5 } }, personality: { integrity: -3 } },
            delayedConsequences: [{ triggerAfterScenes: 2, effects: { relationships: { hung: { respect: -15, trust: -10 } } }, message: { en: 'Mr. Hung noticed something during the exam. He says nothing now, but his look stays with you.', vi: 'Thầy Hùng để ý điều gì đó trong giờ thi. Thầy không nói gì, nhưng ánh mắt thầy khiến bạn không quên.' } }],
            nextScene: 's01-07',
          },
          {
            id: 'c06-c',
            text: { en: 'Skip it. Focus on what you know.', vi: 'Bỏ qua. Tập trung vào phần mình biết.' },
            tags: ['assertiveness', 'resilience'],
            effects: { personality: { assertiveness: 2, resilience: 2 } },
            nextScene: 's01-07',
          },
        ],
      },
      {
        id: 's01-07',
        character: 'hung',
        dialogue: {
          en: '"Time\'s up. Pass your papers forward." He collects them without expression.',
          vi: '"Hết giờ. Nộp bài lên phía trước." Thầy thu bài không biểu cảm.',
        },
        nextScene: 's01-08',
      },
      {
        id: 's01-08',
        character: 'lan',
        dialogue: {
          en: '"How was it? I think I did okay on chapter 7, actually. Thanks to you." She bumps your shoulder.',
          vi: '"Thi sao rồi? Mình nghĩ mình làm được chương 7 đấy. Nhờ có bạn." Cô ấy huých vai bạn.',
        },
        choices: [
          {
            id: 'c08-a',
            text: { en: '"I\'m glad I could help. We both did our best."', vi: '"Mình vui vì giúp được bạn. Cả hai đều cố hết sức."' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { lan: { friendship: 8, trust: 5 } }, personality: { empathy: 2 } },
            nextScene: 's01-09',
          },
          {
            id: 'c08-b',
            text: { en: '"I don\'t know. Question 5 destroyed me."', vi: '"Mình không biết. Câu 5 giết chết mình rồi."' },
            tags: ['honesty', 'resilience'],
            effects: { relationships: { lan: { trust: 5 } }, personality: { resilience: 2, courage: 1 } },
            nextScene: 's01-09',
          },
        ],
      },
      {
        id: 's01-09',
        character: 'narrator',
        dialogue: {
          en: 'A week later. Grades are posted. You open the portal with trembling fingers.',
          vi: 'Một tuần sau. Điểm được công bố. Bạn mở cổng thông tin với ngón tay run run.',
        },
        nextScene: 's01-10',
      },
      {
        id: 's01-10',
        character: 'narrator',
        dialogue: {
          en: 'Your score isn\'t perfect. But it\'s yours. In the hallway, Lan runs up to you with her phone showing her grade — a B+, up from her usual C.',
          vi: 'Điểm của bạn không hoàn hảo. Nhưng đó là điểm của chính bạn. Trong hành lang, Lan chạy đến khoe điện thoại — điểm B+, cao hơn C thường ngày của cô ấy.',
        },
        choices: [
          {
            id: 'c10-a',
            text: { en: 'Celebrate together. Grades aren\'t everything.', vi: 'Ăn mừng cùng nhau. Điểm số không phải tất cả.' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { lan: { friendship: 10 } }, personality: { empathy: 3 } },
            nextScene: 's01-11',
          },
          {
            id: 'c10-b',
            text: { en: 'Feel quietly proud, but wonder what you could have done differently.', vi: 'Tự hào thầm lặng, nhưng tự hỏi mình có thể làm khác đi không.' },
            tags: ['curiosity', 'responsibility'],
            effects: { personality: { curiosity: 3, responsibility: 2 } },
            nextScene: 's01-11',
          },
        ],
      },
      {
        id: 's01-11',
        character: 'mom',
        dialogue: {
          en: '"I saw your grade. I\'m proud of you — not for the number, but for how you handled this week."',
          vi: '"Mẹ thấy điểm của con. Mẹ tự hào về con — không phải vì con số, mà vì cách con xử lý tuần này."',
        },
        nextScene: 's01-12',
      },
      {
        id: 's01-12',
        character: 'narrator',
        dialogue: {
          en: 'The exam is over. But the choices you made — who you helped, how you prepared, what you valued — those stay with you longer than any grade.',
          vi: 'Kỳ thi đã qua. Nhưng những lựa chọn bạn đã làm — bạn giúp ai, bạn chuẩn bị thế nào, bạn coi trọng điều gì — những thứ đó ở lại lâu hơn bất kỳ con điểm nào.',
        },
        endStory: true,
      },
    ],
  },

  // Story 2: Crossroads — Future Planning
  {
    id: 'hs-02',
    lifeStage: 'high_school',
    category: 'future',
    title: { en: 'Crossroads', vi: 'Ngã Ba Đường' },
    description: {
      en: 'University applications are due next month. Your parents want medicine. Your heart wants design. Your counselor wants to talk.',
      vi: 'Tháng sau hết hạn nộp hồ sơ đại học. Bố mẹ muốn bạn học Y. Bạn lại mơ đến Thiết kế. Cô Thảo — cố vấn học đường — muốn nói chuyện.',
    },
    xpReward: 120,
    totalScenes: 13,
    startScene: 's02-01',
    characters: [
      { id: 'dad', name: { en: 'Dad', vi: 'Bố' }, color: '#5080b0', emoji: '👨' },
      { id: 'counselor', name: { en: 'Ms. Thao', vi: 'Cô Thảo' }, color: '#9060c0', emoji: '👩‍💼' },
      { id: 'tuan', name: { en: 'Tuan', vi: 'Tuấn' }, color: '#60a080', emoji: '👦' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 's02-01',
        character: 'narrator',
        dialogue: {
          en: 'Dinner table. Dad slides a brochure across — a medical university, top-ranked. "This is a good path for you."',
          vi: 'Bàn ăn tối. Bố đẩy một cuốn brochure — trường y hàng đầu. "Đây là con đường tốt cho con."',
        },
        choices: [
          {
            id: 'c02-01a',
            text: { en: '"I\'ll think about it, Dad."', vi: '"Con sẽ suy nghĩ, bố."' },
            tags: ['avoid_conflict', 'short_term_gain'],
            effects: { relationships: { dad: { trust: 3 } }, personality: { empathy: 1 } },
            delayedConsequences: [{ triggerAfterScenes: 5, effects: { relationships: { dad: { trust: -15 } } }, message: { en: 'Dad found out you never opened the brochure. The silence at dinner was heavy.', vi: 'Bố biết con chưa bao giờ mở brochure. Bữa tối im lặng nặng nề.' } }],
            nextScene: 's02-02',
          },
          {
            id: 'c02-01b',
            text: { en: '"Dad, I want to talk about what I actually want to study."', vi: '"Bố ơi, con muốn nói về thứ con thực sự muốn học."' },
            tags: ['assertiveness', 'courage'],
            effects: { relationships: { dad: { respect: 8, trust: 5 } }, personality: { assertiveness: 3, courage: 3 } },
            nextScene: 's02-02b',
          },
          {
            id: 'c02-01c',
            text: { en: 'Nod silently and take the brochure.', vi: 'Gật đầu im lặng và nhận brochure.' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { dad: { trust: 5, dependency: 10 } }, personality: { ownership: -2 } },
            delayedConsequences: [{ triggerAfterScenes: 6, effects: { personality: { resilience: -3 } }, message: { en: 'You\'ve been carrying a choice that isn\'t yours. It\'s starting to show.', vi: 'Bạn đang mang theo một lựa chọn không phải của mình. Nó bắt đầu lộ ra.' } }],
            nextScene: 's02-02',
          },
        ],
      },
      {
        id: 's02-02',
        character: 'narrator',
        dialogue: {
          en: 'The conversation ends without resolution. That night, you open your sketchbook — pages of logos, layouts, characters you\'ve designed.',
          vi: 'Cuộc nói chuyện kết thúc không có kết luận. Đêm đó, bạn mở sketchbook — những trang logo, bố cục, nhân vật bạn đã thiết kế.',
        },
        nextScene: 's02-03',
      },
      {
        id: 's02-02b',
        character: 'dad',
        dialogue: {
          en: '"Design? That\'s not a stable career. Medicine gives you security." His voice is firm but not angry.',
          vi: '"Thiết kế? Đó không phải nghề ổn định. Y khoa cho con sự an toàn." Giọng bố cứng rắn nhưng không giận.',
        },
        choices: [
          {
            id: 'c02-02a',
            text: { en: '"I understand your concern. Can we look at options together?"', vi: '"Con hiểu lo lắng của bố. Mình xem các lựa chọn cùng nhau được không?"' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { dad: { trust: 10, respect: 8 } }, personality: { empathy: 3, cooperation: 3 } },
            nextScene: 's02-03',
          },
          {
            id: 'c02-02b',
            text: { en: '"Security isn\'t the only thing that matters to me."', vi: '"An toàn không phải thứ duy nhất quan trọng với con."' },
            tags: ['assertiveness', 'courage'],
            effects: { relationships: { dad: { respect: 5, trust: -3 } }, personality: { assertiveness: 4, courage: 3 } },
            nextScene: 's02-03',
          },
        ],
      },
      {
        id: 's02-03',
        character: 'counselor',
        dialogue: {
          en: '"I\'ve reviewed your file. Your art portfolio is exceptional. Have you considered applying to design programs?"',
          vi: '"Cô đã xem hồ sơ của em. Portfolio nghệ thuật của em rất ấn tượng. Em có cân nhắc nộp vào ngành thiết kế không?"',
        },
        choices: [
          {
            id: 'c02-03a',
            text: { en: '"Yes. But my family expects medicine."', vi: '"Có. Nhưng gia đình em kỳ vọng học y."' },
            tags: ['honesty', 'empathy'],
            effects: { relationships: { counselor: { trust: 10 } }, personality: { empathy: 2 } },
            nextScene: 's02-04',
          },
          {
            id: 'c02-03b',
            text: { en: '"I\'m not sure what I want yet."', vi: '"Em chưa chắc mình muốn gì."' },
            tags: ['avoidance', 'curiosity'],
            effects: { relationships: { counselor: { trust: 3 } }, personality: { curiosity: 1 } },
            nextScene: 's02-04',
          },
          {
            id: 'c02-03c',
            text: { en: '"Can you help me figure out a path that works?"', vi: '"Cô giúp em tìm con đường phù hợp được không?"' },
            tags: ['curiosity', 'responsibility'],
            effects: { relationships: { counselor: { trust: 8, respect: 5 } }, personality: { curiosity: 3, responsibility: 2 } },
            nextScene: 's02-04',
          },
        ],
      },
      {
        id: 's02-04',
        character: 'counselor',
        dialogue: {
          en: '"Some students apply to both — a safe option and a passion option. It\'s more work, but it keeps doors open."',
          vi: '"Một số học sinh nộp cả hai — một lựa chọn an toàn và một lựa chọn đam mê. Vất vả hơn, nhưng giữ nhiều cánh cửa mở."',
        },
        nextScene: 's02-05',
      },
      {
        id: 's02-05',
        character: 'tuan',
        dialogue: {
          en: '"Dude, just apply where you want. My brother studied what my parents wanted. He\'s miserable." Tuan kicks a pebble on the walk home.',
          vi: '"Ông cứ nộp nơi mình muốn đi. Anh tôi học theo ý bố mẹ. Ảnh khổ lắm." Tuấn đá một hòn sỏi trên đường về.',
        },
        choices: [
          {
            id: 'c02-05a',
            text: { en: '"That\'s easy to say. Not everyone can afford to disappoint their parents."', vi: '"Nói thì dễ. Không phải ai cũng dám làm bố mẹ thất vọng."' },
            tags: ['empathy', 'responsibility'],
            effects: { relationships: { tuan: { trust: 5 } }, personality: { empathy: 3 } },
            nextScene: 's02-06',
          },
          {
            id: 'c02-05b',
            text: { en: '"Maybe you\'re right. I need to stop avoiding this."', vi: '"Có lẽ ông đúng. Mình cần ngừng trốn tránh."' },
            tags: ['courage', 'ownership'],
            effects: { relationships: { tuan: { friendship: 8 } }, personality: { courage: 3, ownership: 3 } },
            nextScene: 's02-06',
          },
        ],
      },
      {
        id: 's02-06',
        character: 'narrator',
        dialogue: {
          en: 'Deadline week. Your desk has two application folders — medicine and design. Both half-finished.',
          vi: 'Tuần deadline. Bàn bạn có hai bộ hồ sơ — y khoa và thiết kế. Cả hai đều làm dở.',
        },
        choices: [
          {
            id: 'c02-06a',
            text: { en: 'Finish both applications. Sleep less.', vi: 'Hoàn thành cả hai hồ sơ. Ngủ ít hơn.' },
            tags: ['discipline', 'resilience'],
            effects: { personality: { discipline: 4, resilience: 3 } },
            nextScene: 's02-07a',
          },
          {
            id: 'c02-06b',
            text: { en: 'Focus on design. It\'s time to commit.', vi: 'Tập trung thiết kế. Đã đến lúc quyết định.' },
            tags: ['courage', 'ownership'],
            effects: { relationships: { dad: { trust: -10, respect: 5 } }, personality: { courage: 4, ownership: 4 } },
            nextScene: 's02-07b',
          },
          {
            id: 'c02-06c',
            text: { en: 'Submit only medicine. It\'s the safer choice.', vi: 'Chỉ nộp y khoa. Đó là lựa chọn an toàn hơn.' },
            tags: ['avoid_conflict', 'short_term_gain'],
            effects: { relationships: { dad: { trust: 10 } }, personality: { ownership: -3 } },
            delayedConsequences: [{ triggerAfterScenes: 3, effects: { personality: { resilience: -5, curiosity: -3 } }, message: { en: 'You submitted the application. But you haven\'t touched your sketchbook in weeks.', vi: 'Bạn đã nộp hồ sơ. Nhưng bạn không đụng đến sketchbook đã mấy tuần.' } }],
            nextScene: 's02-07c',
          },
        ],
      },
      {
        id: 's02-07a',
        character: 'narrator',
        dialogue: {
          en: 'Two weeks of exhaustion. Both applications submitted. Your hands shake as you click "confirm" on the second one.',
          vi: 'Hai tuần kiệt sức. Cả hai hồ sơ đã nộp. Tay bạn run khi bấm "xác nhận" hồ sơ thứ hai.',
        },
        nextScene: 's02-08',
      },
      {
        id: 's02-07b',
        character: 'narrator',
        dialogue: {
          en: 'You spend three days perfecting your design portfolio. Every piece tells a story about who you are.',
          vi: 'Bạn dành ba ngày hoàn thiện portfolio thiết kế. Mỗi tác phẩm kể một câu chuyện về con người bạn.',
        },
        nextScene: 's02-08',
      },
      {
        id: 's02-07c',
        character: 'narrator',
        dialogue: {
          en: 'The medicine application is submitted. Dad smiles at dinner. You smile back, but something feels hollow.',
          vi: 'Hồ sơ y khoa đã nộp. Bố mỉm cười trong bữa tối. Bạn cười lại, nhưng có gì đó trống rỗng.',
        },
        nextScene: 's02-08',
      },
      {
        id: 's02-08',
        character: 'dad',
        dialogue: {
          en: '"Whatever happens, I want you to know — I\'m trying to understand." He doesn\'t look at you directly.',
          vi: '"Dù sao đi nữa, bố muốn con biết — bố đang cố hiểu." Ông không nhìn thẳng vào mắt bạn.',
        },
        choices: [
          {
            id: 'c02-08a',
            text: { en: '"I know, Dad. I\'m trying too."', vi: '"Con biết, bố. Con cũng đang cố."' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { dad: { trust: 15, friendship: 10 } }, personality: { empathy: 4 } },
            nextScene: 's02-09',
          },
          {
            id: 'c02-08b',
            text: { en: 'Say nothing. Some things take time.', vi: 'Không nói gì. Một số thứ cần thời gian.' },
            tags: ['avoid_conflict', 'resilience'],
            effects: { relationships: { dad: { trust: 5 } }, personality: { resilience: 2 } },
            nextScene: 's02-09',
          },
        ],
      },
      {
        id: 's02-09',
        character: 'narrator',
        dialogue: {
          en: 'Months later. Acceptance letters arrive. Your future isn\'t one path — it\'s the sum of every conversation you had, every risk you took or didn\'t.',
          vi: 'Vài tháng sau. Thư trúng tuyển đến. Tương lai không phải một con đường — mà là tổng của mọi cuộc trò chuyện, mọi rủi ro bạn chấp nhận hoặc không.',
        },
        nextScene: 's02-10',
      },
      {
        id: 's02-10',
        character: 'counselor',
        dialogue: {
          en: '"You made it through the hardest part — deciding who gets to choose your life. That person should be you."',
          vi: '"Em đã vượt qua phần khó nhất — quyết định ai được chọn cuộc đời em. Người đó nên là chính em."',
        },
        nextScene: 's02-11',
      },
      {
        id: 's02-11',
        character: 'narrator',
        dialogue: {
          en: 'The crossroads don\'t disappear after high school. But this time, you learned what it feels like to stand at one — and choose.',
          vi: 'Ngã ba đường không biến mất sau THPT. Nhưng lần này, bạn đã học cảm giác đứng trước ngã ba — và chọn.',
        },
        endStory: true,
      },
    ],
  },
];
