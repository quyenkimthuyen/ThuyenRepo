const PRIMARY_STORIES = [
  // 1. Chiếc Ghế Trống — Tình Bạn
  {
    id: 'ps-01',
    lifeStage: 'primary_school',
    category: 'friendship',
    visualStyle: 'comic',
    title: { en: 'The Empty Chair', vi: 'Chiếc Ghế Trống' },
    description: {
      en: 'A new student named An sits alone every recess. Your best friend Minh says you two should stay a pair — just the two of you, like always.',
      vi: 'Bạn mới tên An cứ ngồi một mình mỗi giờ ra chơi. Minh — bạn thân nhất của bạn — bảo hai đứa cứ chơi đôi như mọi khi thôi.',
    },
    xpReward: 80,
    totalScenes: 13,
    startScene: 'ps01-01',
    characters: [
      { id: 'minh', name: { en: 'Minh', vi: 'Minh' }, color: '#60a080', emoji: '👦' },
      { id: 'an', name: { en: 'An', vi: 'An' }, color: '#8090c0', emoji: '🧒' },
      { id: 'teacher', name: { en: 'Ms. Hoa', vi: 'Cô Hoa' }, color: '#c08090', emoji: '👩‍🏫' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 'ps01-01',
        character: 'narrator',
        dialogue: {
          en: 'Monday morning. A new desk appears in the back row. A boy with quiet eyes sits down — An. He doesn\'t look at anyone.',
          vi: 'Sáng thứ Hai. Có thêm một bàn ở cuối lớp. Một bạn trai mắt hiền ngồi xuống — An. Bạn ấy không nhìn ai cả.',
        },
        nextScene: 'ps01-02',
      },
      {
        id: 'ps01-02',
        character: 'minh',
        dialogue: {
          en: '"That\'s the new kid. My cousin said he moved here because his parents divorced." Minh pulls you toward the swings. "Come on. We always play together."',
          vi: '"Đó là bạn mới. Chị họ tôi bảo cậu ấy chuyển trường vì bố mẹ ly hôn." Minh kéo bạn ra sân xích đu. "Đi nào. Hai đứa mình chơi với nhau như mọi khi."',
        },
        choices: [
          {
            id: 'ps01-c02a',
            text: { en: 'Go with Minh. You\'ve been best friends since grade one.', vi: 'Đi với Minh. Hai đứa thân từ lớp Một mà.' },
            tags: ['avoid_conflict', 'cooperation'],
            effects: { relationships: { minh: { friendship: 8, trust: 5 } }, personality: { cooperation: 2 } },
            delayedConsequences: [{ triggerAfterScenes: 5, effects: { relationships: { an: { trust: -10, friendship: -5 } } }, message: { en: 'At recess, An sits on the bench again. He sees you laughing with Minh and looks away quickly.', vi: 'Giờ ra chơi, An lại ngồi một mình trên ghế. Bạn ấy thấy bạn cười với Minh rồi quay đi thật nhanh.' } }],
            nextScene: 'ps01-03a',
          },
          {
            id: 'ps01-c02b',
            text: { en: '"Wait. Maybe we should ask if he wants to play."', vi: '"Khoan. Hay mình hỏi xem cậu ấy có muốn chơi cùng không."' },
            tags: ['empathy', 'courage'],
            effects: { relationships: { an: { friendship: 5, trust: 8 }, minh: { trust: -3 } }, personality: { empathy: 3, courage: 2 } },
            nextScene: 'ps01-03b',
          },
          {
            id: 'ps01-c02c',
            text: { en: 'Wave at An from a distance, then go with Minh.', vi: 'Vẫy tay chào An từ xa, rồi đi với Minh.' },
            tags: ['short_term_gain', 'avoid_conflict'],
            effects: { relationships: { an: { friendship: 2 }, minh: { friendship: 5 } }, personality: { empathy: 1 } },
            nextScene: 'ps01-03a',
          },
        ],
      },
      {
        id: 'ps01-03a',
        character: 'narrator',
        dialogue: {
          en: 'You and Minh race to the slide. Behind you, An walks to the bench alone, holding a book.',
          vi: 'Hai đứa chạy đua tới cầu trượt. Phía sau, An đi một mình tới ghế băng, ôm một quyển sách.',
        },
        nextScene: 'ps01-04',
      },
      {
        id: 'ps01-03b',
        character: 'an',
        dialogue: {
          en: 'An looks up, surprised. "...I don\'t know anyone here yet." His voice is small but not unfriendly.',
          vi: 'An ngước lên, hơi ngạc nhiên. "...Em chưa quen ai ở đây." Giọng nhỏ nhưng không lạnh.',
        },
        choices: [
          {
            id: 'ps01-c03a',
            text: { en: '"Want to try the swings? I\'ll push you."', vi: '"Cậu muốn chơi xích đu không? Tớ đẩy cho."' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { an: { friendship: 12, trust: 10 } }, personality: { empathy: 3 } },
            nextScene: 'ps01-04',
          },
          {
            id: 'ps01-c03b',
            text: { en: 'Look at Minh. He\'s waiting, arms crossed.', vi: 'Nhìn Minh. Cậu ấy đang đứng chờ, khoanh tay.' },
            tags: ['avoid_conflict', 'short_term_gain'],
            effects: { relationships: { minh: { friendship: 5 }, an: { trust: -5 } }, personality: { avoidance: 2 } },
            nextScene: 'ps01-03a',
          },
        ],
      },
      {
        id: 'ps01-04',
        character: 'minh',
        dialogue: {
          en: 'At lunch, Minh whispers: "Why are you talking to him? We don\'t need a third person."',
          vi: 'Giờ ăn trưa, Minh thì thầm: "Sao cậu nói chuyện với cậu ta? Mình đâu cần thêm người thứ ba."',
        },
        choices: [
          {
            id: 'ps01-c04a',
            text: { en: '"Having more friends doesn\'t mean we\'re less close."', vi: '"Nhiều bạn hơn không có nghĩa là mình xa nhau hơn."' },
            tags: ['assertiveness', 'empathy'],
            effects: { relationships: { minh: { respect: 8, trust: 5 } }, personality: { assertiveness: 3, empathy: 2 } },
            nextScene: 'ps01-05',
          },
          {
            id: 'ps01-c04b',
            text: { en: 'Say nothing. Eat your rice quietly.', vi: 'Không nói gì. Cắm cơm im lặng.' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { minh: { friendship: 3 } }, personality: { avoidance: 2 } },
            delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { minh: { dependency: 10 } } }, message: { en: 'Minh starts deciding who you can talk to. It feels uncomfortable, but you don\'t say anything.', vi: 'Minh bắt đầu quyết định hộ bạn được nói chuyện với ai. Cảm giác khó chịu, nhưng bạn không nói gì.' } }],
            nextScene: 'ps01-05',
          },
          {
            id: 'ps01-c04c',
            text: { en: '"You\'re right. Sorry, Minh." Stop talking to An.', vi: '"Cậu nói đúng. Xin lỗi, Minh." Và không nói chuyện với An nữa.' },
            tags: ['avoid_conflict', 'short_term_gain'],
            effects: { relationships: { minh: { friendship: 10, dependency: 8 }, an: { friendship: -15, trust: -12 } }, personality: { integrity: -2 } },
            nextScene: 'ps01-05',
          },
        ],
      },
      {
        id: 'ps01-05',
        character: 'narrator',
        dialogue: {
          en: 'Wednesday. Group art project. The teacher says: "Work in groups of three." Minh grabs your arm. An has no group.',
          vi: 'Thứ Tư. Làm bài tập nhóm Mỹ thuật. Cô bảo: "Chia nhóm ba người." Minh nắm tay bạn. An chưa có nhóm.',
        },
        choices: [
          {
            id: 'ps01-c05a',
            text: { en: '"An, join us. We need someone good at drawing."', vi: '"An, vào nhóm mình đi. Cần người vẽ giỏi."' },
            tags: ['cooperation', 'empathy'],
            effects: { relationships: { an: { friendship: 15, trust: 10 }, minh: { respect: 5 } }, personality: { cooperation: 3, empathy: 3 } },
            nextScene: 'ps01-06a',
          },
          {
            id: 'ps01-c05b',
            text: { en: 'Let Minh choose. Follow his lead.', vi: 'Để Minh quyết định. Theo cậu ấy.' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { minh: { friendship: 5 }, an: { trust: -8 } }, personality: { avoidance: 2 } },
            nextScene: 'ps01-06b',
          },
        ],
      },
      {
        id: 'ps01-06a',
        character: 'an',
        dialogue: {
          en: 'An draws a small bird on the poster — delicate, alive. Minh stares, then quietly adds clouds around it.',
          vi: 'An vẽ một chú chim nhỏ trên tờ giấy — mảnh mai, sống động. Minh nhìn, rồi lặng lẽ thêm mấy đám mây xung quanh.',
        },
        nextScene: 'ps01-07',
      },
      {
        id: 'ps01-06b',
        character: 'teacher',
        dialogue: {
          en: '"An, you can join that group over there." An walks across the room with his head down.',
          vi: '"An, em sang nhóm kia nhé." An đi ngang lớp, cúi đầu.',
        },
        nextScene: 'ps01-07',
      },
      {
        id: 'ps01-07',
        character: 'narrator',
        dialogue: {
          en: 'Friday afternoon. Minh\'s bike tire is flat. A new student from class two asks him to play soccer. Minh looks at you.',
          vi: 'Chiều thứ Sáu. Xe đạp Minh bị xịp lốp. Một bạn mới lớp Hai rủ Minh đá bóng. Minh nhìn bạn.',
        },
        choices: [
          {
            id: 'ps01-c07a',
            text: { en: '"I\'ll help fix your bike. An can help too — he\'s good with tools."', vi: '"Tớ giúp sửa xe. An cũng giỏi đồ nghề — cậu ấy giúp được."' },
            tags: ['cooperation', 'empathy'],
            effects: { relationships: { minh: { trust: 10 }, an: { friendship: 10 } }, personality: { cooperation: 3 } },
            nextScene: 'ps01-08',
          },
          {
            id: 'ps01-c07b',
            text: { en: '"Go play soccer. I\'ll wait for you."', vi: '"Cậu đi đá bóng đi. Tớ đợi."' },
            tags: ['empathy', 'avoid_conflict'],
            effects: { relationships: { minh: { friendship: 8 } }, personality: { empathy: 2 } },
            nextScene: 'ps01-08',
          },
        ],
      },
      {
        id: 'ps01-08',
        character: 'minh',
        dialogue: {
          en: 'Minh is quiet for a moment. "...I was scared you\'d like An more than me." He kicks a pebble. "That was dumb."',
          vi: 'Minh im một lúc. "...Tớ sợ cậu thích An hơn tớ." Cậu ấy đá một hòn sỏi. "Ngu thật."',
        },
        choices: [
          {
            id: 'ps01-c08a',
            text: { en: '"You\'re still my first friend. But there\'s room for more."', vi: '"Cậu vẫn là bạn đầu tiên của tớ. Nhưng còn chỗ cho nhiều bạn hơn."' },
            tags: ['empathy', 'assertiveness'],
            effects: { relationships: { minh: { friendship: 15, trust: 12, dependency: -10 } }, personality: { empathy: 4 } },
            nextScene: 'ps01-09',
          },
          {
            id: 'ps01-c08b',
            text: { en: '"I didn\'t know you felt that way."', vi: '"Tớ không biết cậu nghĩ vậy."' },
            tags: ['empathy', 'curiosity'],
            effects: { relationships: { minh: { trust: 10 } }, personality: { empathy: 3, curiosity: 2 } },
            nextScene: 'ps01-09',
          },
        ],
      },
      {
        id: 'ps01-09',
        character: 'an',
        dialogue: {
          en: 'An smiles — the first real smile you\'ve seen. "Thanks for not letting me sit alone forever."',
          vi: 'An cười — nụ cười thật đầu tiên bạn thấy. "Cảm ơn vì không để mình ngồi một mình mãi."',
        },
        nextScene: 'ps01-10',
      },
      {
        id: 'ps01-10',
        character: 'narrator',
        dialogue: {
          en: 'The empty chair in the back row isn\'t empty anymore at recess. But you learned something harder than sharing toys: friendship can feel tight, and still make room.',
          vi: 'Chiếc ghế trống cuối lớp không còn trống nữa khi ra chơi. Nhưng bạn đã học điều khó hơn cả chia đồ chơi: tình bạn có thể chật, mà vẫn đủ rộng để mở cửa.',
        },
        endStory: true,
      },
    ],
  },

  // 2. Cây Bút Chì Gãy — Sự Thật
  {
    id: 'ps-02',
    lifeStage: 'primary_school',
    category: 'honesty',
    title: { en: 'The Broken Pencil', vi: 'Cây Bút Chì Gãy' },
    description: {
      en: 'You borrowed Linh\'s pencil during a test. It snapped in your hand. Nobody saw. Linh will look for it after class.',
      vi: 'Bạn mượn bút chì của Linh trong giờ kiểm tra. Cây bút gãy trong tay. Không ai thấy. Linh sẽ tìm bút sau giờ học.',
    },
    xpReward: 80,
    totalScenes: 12,
    startScene: 'ps02-01',
    characters: [
      { id: 'linh', name: { en: 'Linh', vi: 'Linh' }, color: '#d090a0', emoji: '👧' },
      { id: 'nam', name: { en: 'Nam', vi: 'Nam' }, color: '#5080a0', emoji: '👦' },
      { id: 'teacher', name: { en: 'Ms. Hoa', vi: 'Cô Hoa' }, color: '#c08090', emoji: '👩‍🏫' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 'ps02-01',
        character: 'narrator',
        dialogue: {
          en: 'Math test. Your pencil breaks. Linh — quiet, organized Linh — slides her spare pencil over without a word.',
          vi: 'Kiểm tra Toán. Bút bạn gãy. Linh — bạn gái ít nói, cẩn thận — đẩy sang cây bút dự phòng không cần một lời.',
        },
        nextScene: 'ps02-02',
      },
      {
        id: 'ps02-02',
        character: 'narrator',
        dialogue: {
          en: 'You press too hard on the last problem. A small crack. Then — snap. The pencil breaks in two. Linh\'s favorite one, with the rabbit eraser.',
          vi: 'Bạn ghi quá mạnh ở bài cuối. Một vết nứt nhỏ. Rồi — cách. Cây bút gãy đôi. Cây bút Linh thích nhất, đầu tẩy hình thỏ.',
        },
        choices: [
          {
            id: 'ps02-c02a',
            text: { en: 'Hide the pieces in your pocket.', vi: 'Giấu hai mảnh vào túi.' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { personality: { integrity: -3 } },
            delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { linh: { trust: -20 } } }, message: { en: 'Linh finds pencil shavings on your desk. She looks at you, then looks away.', vi: 'Linh thấy mấy mảnh bút trên bàn bạn. Cô ấy nhìn bạn, rồi quay đi.' } }],
            nextScene: 'ps02-03a',
          },
          {
            id: 'ps02-c02b',
            text: { en: 'Put the pieces on her desk with a note: "I\'m sorry."', vi: 'Đặt hai mảnh lên bàn cô ấy kèm dòng chữ: "Xin lỗi."' },
            tags: ['integrity', 'courage'],
            effects: { relationships: { linh: { trust: 10, respect: 8 } }, personality: { integrity: 4, courage: 3 } },
            nextScene: 'ps02-03b',
          },
          {
            id: 'ps02-c02c',
            text: { en: 'Whisper to Nam: "I broke Linh\'s pencil. What do I do?"', vi: 'Thì thầm với Nam: "Tớ làm gãy bút Linh rồi. Phải làm sao?"' },
            tags: ['curiosity', 'cooperation'],
            effects: { relationships: { nam: { trust: 5 } }, personality: { curiosity: 2 } },
            nextScene: 'ps02-03c',
          },
        ],
      },
      {
        id: 'ps02-03a',
        character: 'linh',
        dialogue: {
          en: 'After class, Linh opens her pencil case. She frowns. "Where\'s my rabbit pencil?"',
          vi: 'Tan học, Linh mở hộp bút. Cô ấy nhíu mày. "Cây bút thỏ của mình đâu nhỉ?"',
        },
        choices: [
          {
            id: 'ps02-c03a',
            text: { en: '"I haven\'t seen it."', vi: '"Tớ không thấy."' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { relationships: { linh: { trust: -15, friendship: -10 } }, personality: { integrity: -5 } },
            delayedConsequences: [{ triggerAfterScenes: 3, effects: { personality: { integrity: -3 } }, message: { en: 'Your stomach feels heavy all afternoon. You keep thinking about the pencil in your pocket.', vi: 'Cả buổi chiều bụng bạn nặng trĩu. Cứ nghĩ tới cây bút trong túi.' } }],
            nextScene: 'ps02-04',
          },
          {
            id: 'ps02-c03b',
            text: { en: 'Pull out the pieces. "I broke it. I\'m really sorry."', vi: 'Lấy hai mảnh ra. "Tớ làm gãy rồi. Xin lỗi thật lòng."' },
            tags: ['courage', 'integrity'],
            effects: { relationships: { linh: { trust: 12, respect: 10 } }, personality: { courage: 4, integrity: 4 } },
            nextScene: 'ps02-04b',
          },
        ],
      },
      {
        id: 'ps02-03b',
        character: 'linh',
        dialogue: {
          en: 'Linh reads your note. She doesn\'t yell. She just looks at the broken pencil, then at you. "...It was a gift from my grandma."',
          vi: 'Linh đọc dòng chữ. Cô ấy không la. Chỉ nhìn cây bút gãy, rồi nhìn bạn. "...Đây là quà bà ngoại tặng."',
        },
        nextScene: 'ps02-04b',
      },
      {
        id: 'ps02-03c',
        character: 'nam',
        dialogue: {
          en: '"Just tell her. Or buy a new one with your allowance." Nam shrugs. "Lying is worse than breaking stuff."',
          vi: '"Nói thật đi. Hoặc dùng tiền tiêu vặt mua cây mới." Nam nhún vai. "Nói dối còn tệ hơn làm hỏng đồ."'
        },
        choices: [
          {
            id: 'ps02-c03d',
            text: { en: 'Tell Linh the truth before she asks.', vi: 'Nói thật với Linh trước khi cô ấy hỏi.' },
            tags: ['courage', 'integrity'],
            effects: { relationships: { linh: { trust: 15 } }, personality: { courage: 3, integrity: 4 } },
            nextScene: 'ps02-04b',
          },
          {
            id: 'ps02-c03e',
            text: { en: '"Maybe she won\'t notice."', vi: '"Biết đâu cô ấy không để ý."' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { personality: { integrity: -3, avoidance: 3 } },
            nextScene: 'ps02-03a',
          },
        ],
      },
      {
        id: 'ps02-04',
        character: 'teacher',
        dialogue: {
          en: 'Ms. Hoa notices the tension. "Is everything okay, Linh?" The whole class turns to look.',
          vi: 'Cô Hoa để ý không khí căng thẳng. "Linh, có chuyện gì không?" Cả lớp quay lại nhìn.',
        },
        nextScene: 'ps02-05',
      },
      {
        id: 'ps02-04b',
        character: 'linh',
        dialogue: {
          en: 'Linh takes a breath. "It\'s okay. Things break." She pauses. "But I wish someone had told me sooner."',
          vi: 'Linh hít một hơi. "Không sao. Đồ vật vốn hay hỏng." Cô ấy dừng lại. "Nhưng ước gì có người nói sớm hơn."',
        },
        choices: [
          {
            id: 'ps02-c04a',
            text: { en: '"I\'ll use my allowance to buy you a new one."', vi: '"Tớ dùng tiền tiêu vặt mua cây mới cho cậu."' },
            tags: ['responsibility', 'empathy'],
            effects: { relationships: { linh: { friendship: 12, trust: 8 } }, personality: { responsibility: 4, empathy: 3 } },
            nextScene: 'ps02-06',
          },
          {
            id: 'ps02-c04b',
            text: { en: '"Can I help glue it? Maybe it can be fixed a little."', vi: '"Mình thử dán lại được không? Biết đâu sửa được chút."' },
            tags: ['responsibility', 'cooperation'],
            effects: { relationships: { linh: { friendship: 10, trust: 10 } }, personality: { responsibility: 3, cooperation: 2 } },
            nextScene: 'ps02-06',
          },
          {
            id: 'ps02-c04c',
            text: { en: '"Sorry." Nothing else.', vi: '"Xin lỗi." Chỉ vậy thôi.' },
            tags: ['honesty'],
            effects: { relationships: { linh: { trust: 5 } }, personality: { integrity: 2 } },
            nextScene: 'ps02-06',
          },
        ],
      },
      {
        id: 'ps02-05',
        character: 'narrator',
        dialogue: {
          en: 'The lie sits in your chest like a stone. Linh doesn\'t ask again. She just closes her pencil case quietly.',
          vi: 'Lời nói dối nằm trong lồng ngực nặng như hòn đá. Linh không hỏi nữa. Cô ấy chỉ khép hộp bút thật nhẹ.',
        },
        nextScene: 'ps02-06',
      },
      {
        id: 'ps02-06',
        character: 'narrator',
        dialogue: {
          en: 'Saturday. You pass a stationery shop. In the window — a pencil with a rabbit eraser, almost the same.',
          vi: 'Thứ Bảy. Bạn đi ngang tiệm văn phòng phẩm. Trong tủ kính — cây bút đầu tẩy hình thỏ, gần giống hệt.',
        },
        choices: [
          {
            id: 'ps02-c06a',
            text: { en: 'Buy it with your saved allowance. Bring it to Linh on Monday.', vi: 'Mua bằng tiền tiêu vặt đã dành. Mang tặng Linh thứ Hai.' },
            tags: ['responsibility', 'empathy'],
            effects: { relationships: { linh: { friendship: 15, trust: 12 } }, personality: { responsibility: 4 } },
            nextScene: 'ps02-07',
          },
          {
            id: 'ps02-c06b',
            text: { en: 'Walk past. You already said sorry.', vi: 'Đi qua. Mình đã xin lỗi rồi.' },
            tags: ['avoidance'],
            effects: { relationships: { linh: { trust: -3 } }, personality: { responsibility: -2 } },
            nextScene: 'ps02-07',
          },
        ],
      },
      {
        id: 'ps02-07',
        character: 'linh',
        dialogue: {
          en: 'Monday. Linh sees the new pencil. For a long moment she doesn\'t speak. Then: "You remembered it was from my grandma."',
          vi: 'Thứ Hai. Linh thấy cây bút mới. Một lúc lâu cô ấy không nói. Rồi: "Cậu nhớ đây là quà bà ngoại tặng."',
        },
        nextScene: 'ps02-08',
      },
      {
        id: 'ps02-08',
        character: 'narrator',
        dialogue: {
          en: 'A broken pencil taught you: telling the truth doesn\'t fix everything instantly. But hiding the truth leaves a crack that grows.',
          vi: 'Một cây bút chì gãy dạy bạn: nói thật không sửa được mọi thứ ngay lập tức. Nhưng giấu sự thật để lại vết nứt — và vết nứt ấy lớn dần.',
        },
        endStory: true,
      },
    ],
  },
];
