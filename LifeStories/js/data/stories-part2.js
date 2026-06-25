const STORIES_PART2 = [
  // Story 3: The Competition
  {
    id: 'hs-03',
    lifeStage: 'high_school',
    category: 'competition',
    title: { en: 'The Competition', vi: 'Cuộc Thi' },
    description: {
      en: 'The national science fair is in two weeks. Your teammate Hoa found a flaw in your project. The rival team might be cheating.',
      vi: 'Hội thi Khoa học còn hai tuần nữa. Hoa — đồng đội của bạn — phát hiện lỗi trong dự án. Đội đối thủ thì có vẻ đang gian lận.',
    },
    xpReward: 110,
    totalScenes: 12,
    startScene: 's03-01',
    characters: [
      { id: 'hoa', name: { en: 'Hoa', vi: 'Hoa' }, color: '#d07090', emoji: '👧' },
      { id: 'kien', name: { en: 'Kien', vi: 'Kiên' }, color: '#5080a0', emoji: '👦' },
      { id: 'judge', name: { en: 'Dr. Linh', vi: 'Tiến sĩ Linh' }, color: '#8060a0', emoji: '👩‍🔬' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 's03-01',
        character: 'narrator',
        dialogue: {
          en: 'The lab smells like solder and coffee. Your water purification prototype sits on the bench — three months of work.',
          vi: 'Phòng lab có mùi hàn và cà phê. Mô hình lọc nước của bạn trên bàn — ba tháng công sức.',
        },
        nextScene: 's03-02',
      },
      {
        id: 's03-02',
        character: 'hoa',
        dialogue: {
          en: '"There\'s a problem with the filter membrane. The data from last week doesn\'t match our model. We need to fix this before the fair."',
          vi: '"Có vấn đề với màng lọc. Dữ liệu tuần trước không khớp mô hình. Mình cần sửa trước hội thi."',
        },
        choices: [
          {
            id: 'c03-02a',
            text: { en: '"You\'re right. Let\'s redo the tests tonight."', vi: '"Bạn đúng. Mình làm lại thí nghiệm tối nay."' },
            tags: ['responsibility', 'cooperation'],
            effects: { relationships: { hoa: { trust: 10, respect: 8 } }, personality: { responsibility: 3, cooperation: 3 } },
            nextScene: 's03-03a',
          },
          {
            id: 'c03-02b',
            text: { en: '"It\'s probably fine. Judges won\'t notice small errors."', vi: '"Chắc không sao. Ban giám khảo không để ý lỗi nhỏ."' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { relationships: { hoa: { trust: -10, respect: -8 } }, personality: { integrity: -3 } },
            delayedConsequences: [{ triggerAfterScenes: 5, effects: { relationships: { judge: { respect: -20 } } }, message: { en: 'Dr. Linh asked a technical question you couldn\'t answer. Hoa looked away.', vi: 'Tiến sĩ Linh hỏi câu kỹ thuật bạn không trả lời được. Hoa quay mặt đi.' } }],
            nextScene: 's03-03b',
          },
          {
            id: 'c03-02c',
            text: { en: '"Show me exactly where. I want to understand."', vi: '"Chỉ cho mình chính xác chỗ nào. Mình muốn hiểu."' },
            tags: ['curiosity', 'teaching'],
            effects: { relationships: { hoa: { trust: 8, friendship: 5 } }, personality: { curiosity: 4 } },
            nextScene: 's03-03a',
          },
        ],
      },
      {
        id: 's03-03a',
        character: 'narrator',
        dialogue: {
          en: 'You work until 2 AM. The membrane issue was real. By morning, the data looks clean.',
          vi: 'Bạn làm đến 2 giờ sáng. Vấn đề màng lọc là thật. Sáng hôm sau, dữ liệu đã sạch.',
        },
        nextScene: 's03-04',
      },
      {
        id: 's03-03b',
        character: 'hoa',
        dialogue: {
          en: '"If you don\'t care about accuracy, I\'ll fix it myself." She turns back to the equipment, jaw tight.',
          vi: '"Nếu bạn không quan tâm độ chính xác, mình sẽ tự sửa." Cô ấy quay lại thiết bị, cằm căng.',
        },
        nextScene: 's03-04',
      },
      {
        id: 's03-04',
        character: 'kien',
        dialogue: {
          en: '"Hey. I saw the other team\'s setup. Their results look too perfect. Like, suspiciously perfect." He lowers his voice.',
          vi: '"Này. Tôi thấy setup đội kia. Kết quả hoàn hảo quá. Kiểu, đáng ngờ luôn." Anh ấy hạ giọng.',
        },
        choices: [
          {
            id: 'c03-04a',
            text: { en: '"That\'s not our business. We focus on our work."', vi: '"Không phải việc mình. Mình tập trung vào dự án."' },
            tags: ['discipline', 'integrity'],
            effects: { personality: { discipline: 3, integrity: 2 } },
            nextScene: 's03-05',
          },
          {
            id: 'c03-04b',
            text: { en: '"We should report it to the organizers."', vi: '"Mình nên báo ban tổ chức."' },
            tags: ['courage', 'integrity'],
            effects: { relationships: { kien: { trust: 5 } }, personality: { courage: 3, integrity: 3 } },
            delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { kien: { respect: 10 } } }, message: { en: 'The organizers investigated. Kien thanked you for speaking up.', vi: 'Ban tổ chức điều tra. Kiên cảm ơn bạn đã lên tiếng.' } }],
            nextScene: 's03-05',
          },
          {
            id: 'c03-04c',
            text: { en: '"Maybe we should make our data look better too..."', vi: '"Hay mình cũng làm dữ liệu đẹp hơn..."' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { relationships: { hoa: { trust: -15, respect: -10 } }, personality: { integrity: -5 } },
            nextScene: 's03-05',
          },
        ],
      },
      {
        id: 's03-05',
        character: 'hoa',
        dialogue: {
          en: '"Competition day. Remember — we present as a team. If I speak, don\'t interrupt. If you speak, I\'ll back you up."',
          vi: '"Ngày thi. Nhớ — mình thuyết trình theo đội. Nếu mình nói, đừng ngắt. Nếu bạn nói, mình sẽ hỗ trợ."'
        },
        choices: [
          {
            id: 'c03-05a',
            text: { en: '"Got it. We\'ve got this together."', vi: '"Hiểu rồi. Mình làm được cùng nhau."' },
            tags: ['cooperation', 'responsibility'],
            effects: { relationships: { hoa: { friendship: 10, trust: 5 } }, personality: { cooperation: 3 } },
            nextScene: 's03-06',
          },
          {
            id: 'c03-05b',
            text: { en: '"I should present the technical part. It\'s my design."', vi: '"Mình nên trình bày phần kỹ thuật. Đó là thiết kế của mình."' },
            tags: ['assertiveness', 'ownership'],
            effects: { relationships: { hoa: { respect: 3, trust: -3 } }, personality: { assertiveness: 3, ownership: 3 } },
            nextScene: 's03-06',
          },
        ],
      },
      {
        id: 's03-06',
        character: 'judge',
        dialogue: {
          en: '"Impressive prototype. Can you explain why you chose graphene oxide for the membrane layer?"',
          vi: '"Mô hình ấn tượng. Các em giải thích tại sao chọn graphene oxide cho lớp màng?"',
        },
        choices: [
          {
            id: 'c03-06a',
            text: { en: 'Explain clearly, step by step.', vi: 'Giải thích rõ ràng, từng bước.' },
            tags: ['discipline', 'curiosity'],
            effects: { relationships: { judge: { respect: 10, trust: 8 } }, personality: { discipline: 2 } },
            nextScene: 's03-07',
          },
          {
            id: 'c03-06b',
            text: { en: 'Let Hoa answer — she knows the chemistry better.', vi: 'Để Hoa trả lời — cô ấy giỏi hóa học hơn.' },
            tags: ['cooperation', 'empathy'],
            effects: { relationships: { hoa: { trust: 10, respect: 8 }, judge: { respect: 5 } }, personality: { cooperation: 3, empathy: 2 } },
            nextScene: 's03-07',
          },
          {
            id: 'c03-06c',
            text: { en: 'Bluff through it. Use big words.', vi: 'Nói qua loa. Dùng từ chuyên ngành.' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { relationships: { judge: { trust: -15, respect: -10 } }, personality: { integrity: -3 } },
            nextScene: 's03-07',
          },
        ],
      },
      {
        id: 's03-07',
        character: 'narrator',
        dialogue: {
          en: 'The presentation ends. The rival team wins second place. Your team takes third. Hoa is quiet on the bus ride home.',
          vi: 'Phần thuyết trình kết thúc. Đội đối thủ giành nhì. Đội bạn giành ba. Hoa im lặng trên xe buýt về.',
        },
        nextScene: 's03-08',
      },
      {
        id: 's03-08',
        character: 'hoa',
        dialogue: {
          en: '"Third isn\'t bad. But I wanted us to be proud of how we got here, not just where we placed."',
          vi: '"Giải ba không tệ. Nhưng mình muốn chúng ta tự hào về cách mình đến đây, không chỉ thứ hạng."',
        },
        choices: [
          {
            id: 'c03-08a',
            text: { en: '"You\'re right. The work we did together mattered more."', vi: '"Bạn đúng. Công việc chúng ta làm cùng nhau quan trọng hơn."' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { hoa: { friendship: 15, trust: 10 } }, personality: { empathy: 3 } },
            nextScene: 's03-09',
          },
          {
            id: 'c03-08b',
            text: { en: '"We should have won. The other team cheated."', vi: '"Lẽ ra mình thắng. Đội kia gian lận."' },
            tags: ['assertiveness', 'avoid_conflict'],
            effects: { relationships: { hoa: { trust: -5 } }, personality: { assertiveness: 2 } },
            nextScene: 's03-09',
          },
        ],
      },
      {
        id: 's03-09',
        character: 'narrator',
        dialogue: {
          en: 'Two weeks later, an email arrives. A university lab wants to develop your prototype further. They mention your "rigorous methodology."',
          vi: 'Hai tuần sau, email đến. Một phòng lab đại học muốn phát triển mô hình của bạn. Họ nhắc đến "phương pháp nghiêm ngặt" của bạn.',
        },
        nextScene: 's03-10',
      },
      {
        id: 's03-10',
        character: 'hoa',
        dialogue: {
          en: '"See? That\'s the real prize. Not a trophy." She finally smiles.',
          vi: '"Thấy chưa? Đó mới là giải thưởng thật. Không phải cúp."'
        },
        nextScene: 's03-11',
      },
      {
        id: 's03-11',
        character: 'narrator',
        dialogue: {
          en: 'Competition taught you something grades never could: how you compete reveals who you are more than where you finish.',
          vi: 'Cuộc thi dạy bạn điều mà điểm số không thể: cách bạn cạnh tranh bộc lộ con người bạn hơn vị trí về đích.',
        },
        endStory: true,
      },
    ],
  },

  // Story 4: First Snow — First Love
  {
    id: 'hs-04',
    lifeStage: 'high_school',
    category: 'love',
    title: { en: 'First Snow', vi: 'Tuyết Đầu Mùa' },
    description: {
      en: 'Mai sits next to you in literature class. She lent you her notes. Winter break is coming, and she asked if you\'re free on Saturday.',
      vi: 'Mai ngồi cạnh bạn trong lớp Văn, từng cho mượn vở. Kỳ nghỉ đông sắp đến — cô ấy hỏi thứ Bảy bạn có rảnh không.',
    },
    xpReward: 100,
    totalScenes: 14,
    startScene: 's04-01',
    characters: [
      { id: 'mai', name: { en: 'Mai', vi: 'Mai' }, color: '#c080a0', emoji: '👧' },
      { id: 'binh', name: { en: 'Binh', vi: 'Bình' }, color: '#6090b0', emoji: '👦' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 's04-01',
        character: 'narrator',
        dialogue: {
          en: 'Literature class. Mai passes you a folded note. Inside: "Are you free Saturday? There\'s a book fair at the old library."',
          vi: 'Lớp Văn. Mai đưa bạn một mảnh giấy gấp. Bên trong: "Thứ Bảy bạn rảnh không? Có hội sách ở thư viện cũ."',
        },
        choices: [
          {
            id: 'c04-01a',
            text: { en: 'Write back: "Yes. I\'d like that."', vi: 'Viết lại: "Có. Mình muốn đi."' },
            tags: ['courage', 'empathy'],
            effects: { relationships: { mai: { friendship: 10, trust: 8 } }, personality: { courage: 3, empathy: 2 } },
            nextScene: 's04-02a',
          },
          {
            id: 'c04-01b',
            text: { en: 'Write back: "Maybe. I\'ll let you know."', vi: 'Viết lại: "Có lẽ. Mình báo sau."' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { mai: { trust: -5 } }, personality: { avoidance: 2 } },
            delayedConsequences: [{ triggerAfterScenes: 3, effects: { relationships: { mai: { friendship: -10, trust: -8 } } }, message: { en: 'Mai went to the book fair with someone else. She didn\'t mention it, but you noticed.', vi: 'Mai đi hội sách với người khác. Cô ấy không nói, nhưng bạn để ý.' } }],
            nextScene: 's04-02b',
          },
          {
            id: 'c04-01c',
            text: { en: 'Ask Binh what he thinks you should do.', vi: 'Hỏi Bình xem nên làm gì.' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { relationships: { binh: { dependency: 10 } }, personality: { ownership: -2 } },
            nextScene: 's04-02c',
          },
        ],
      },
      {
        id: 's04-02a',
        character: 'mai',
        dialogue: {
          en: 'She reads your note and smiles — a small, genuine smile that makes your stomach flip.',
          vi: 'Cô ấy đọc note và mỉm cười — nụ cười nhỏ chân thành khiến bạn hồi hộp.',
        },
        nextScene: 's04-03',
      },
      {
        id: 's04-02b',
        character: 'mai',
        dialogue: {
          en: '"Okay." She turns back to her book. The smile is gone.',
          vi: '"Ừ." Cô ấy quay lại sách. Nụ cười biến mất.',
        },
        nextScene: 's04-03',
      },
      {
        id: 's04-02c',
        character: 'binh',
        dialogue: {
          en: '"Just go, man. Stop overthinking everything." He rolls his eyes but means well.',
          vi: '"Cứ đi đi. Đừng nghĩ quá nhiều." Anh ấy đảo mắt nhưng thật lòng.',
        },
        nextScene: 's04-03',
      },
      {
        id: 's04-03',
        character: 'narrator',
        dialogue: {
          en: 'Saturday. Light snow falls as you walk to the old library. Mai is already there, holding two cups of hot chocolate.',
          vi: 'Thứ Bảy. Tuyết rơi nhẹ khi bạn đi đến thư viện cũ. Mai đã ở đó, cầm hai cốc cacao nóng.',
        },
        choices: [
          {
            id: 'c04-03a',
            text: { en: '"You remembered I like extra marshmallows."', vi: '"Bạn nhớ mình thích thêm marshmallow."' },
            tags: ['empathy', 'curiosity'],
            effects: { relationships: { mai: { trust: 10, friendship: 8 } }, personality: { empathy: 3 } },
            nextScene: 's04-04',
          },
          {
            id: 'c04-03b',
            text: { en: '"Thanks. I wasn\'t sure you\'d actually come."', vi: '"Cảm ơn. Mình không chắc bạn thật sự đến."' },
            tags: ['honesty', 'vulnerability'],
            effects: { relationships: { mai: { trust: 8 } }, personality: { courage: 2 } },
            nextScene: 's04-04',
          },
        ],
      },
      {
        id: 's04-04',
        character: 'mai',
        dialogue: {
          en: '"I found this poetry collection. The author writes about growing up in a small town. Reminded me of you, actually."',
          vi: '"Mình tìm được tập thơ này. Tác giả viết về lớn lên ở thị trấn nhỏ. Thực ra mình nghĩ đến bạn."',
        },
        choices: [
          {
            id: 'c04-04a',
            text: { en: 'Read a poem together, out loud.', vi: 'Đọc một bài thơ cùng nhau, thành tiếng.' },
            tags: ['cooperation', 'empathy'],
            effects: { relationships: { mai: { friendship: 12, trust: 5 } }, personality: { cooperation: 2, empathy: 3 } },
            nextScene: 's04-05',
          },
          {
            id: 'c04-04b',
            text: { en: 'Make a joke to hide how nervous you feel.', vi: 'Nói đùa để che giấu sự hồi hộp.' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { mai: { trust: -3 } }, personality: { avoidance: 2 } },
            delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { mai: { trust: -8 } } }, message: { en: 'Mai became quieter after that moment. Something shifted.', vi: 'Mai trở nên trầm hơn sau khoảnh khắc đó. Có gì đó thay đổi.' } }],
            nextScene: 's04-05',
          },
        ],
      },
      {
        id: 's04-05',
        character: 'binh',
        dialogue: {
          en: 'Later, Binh texts: "Saw you at the library with Mai. 👀 You gonna tell her how you feel or what?"',
          vi: 'Sau đó, Bình nhắn: "Thấy ông ở thư viện với Mai. 👀 Ông sẽ nói cảm xúc hay gì?"',
        },
        choices: [
          {
            id: 'c04-05a',
            text: { en: '"It\'s not that simple. We\'re just getting to know each other."', vi: '"Không đơn giản vậy. Mình đang tìm hiểu nhau."' },
            tags: ['responsibility', 'empathy'],
            effects: { personality: { responsibility: 2, empathy: 2 } },
            nextScene: 's04-06',
          },
          {
            id: 'c04-05b',
            text: { en: '"Mind your own business."', vi: '"Lo chuyện của ông đi."' },
            tags: ['assertiveness'],
            effects: { relationships: { binh: { trust: -3 } }, personality: { assertiveness: 2 } },
            nextScene: 's04-06',
          },
        ],
      },
      {
        id: 's04-06',
        character: 'narrator',
        dialogue: {
          en: 'Monday. Mai doesn\'t sit in her usual seat. She\'s at the back, talking to someone from the drama club.',
          vi: 'Thứ Hai. Mai không ngồi chỗ thường. Cô ấy ở cuối lớp, nói chuyện với ai đó từ câu lạc bộ kịch.',
        },
        choices: [
          {
            id: 'c04-06a',
            text: { en: 'Walk over and say hi naturally.', vi: 'Đi lại chào một cách tự nhiên.' },
            tags: ['courage', 'assertiveness'],
            effects: { relationships: { mai: { friendship: 5, trust: 5 } }, personality: { courage: 3 } },
            nextScene: 's04-07',
          },
          {
            id: 'c04-06b',
            text: { en: 'Feel jealous but say nothing.', vi: 'Ghen tị nhưng không nói gì.' },
            tags: ['avoidance', 'avoid_conflict'],
            effects: { personality: { avoidance: 3 } },
            delayedConsequences: [{ triggerAfterScenes: 3, effects: { relationships: { mai: { friendship: -5, trust: -5 } } }, message: { en: 'Days passed without you two talking. The distance grew quietly.', vi: 'Nhiều ngày trôi qua không nói chuyện. Khoảng cách lớn dần.' } }],
            nextScene: 's04-07',
          },
          {
            id: 'c04-06c',
            text: { en: 'Send her a message: "Hey, is everything okay?"', vi: 'Nhắn: "Này, mọi thứ ổn chứ?"' },
            tags: ['empathy', 'courage'],
            effects: { relationships: { mai: { trust: 8, friendship: 5 } }, personality: { empathy: 3, courage: 2 } },
            nextScene: 's04-07',
          },
        ],
      },
      {
        id: 's04-07',
        character: 'mai',
        dialogue: {
          en: '"I heard you might like me." She says it quietly, not looking up. "Is that true?"',
          vi: '"Mình nghe nói bạn có thể thích mình." Cô ấy nói nhỏ, không ngước lên. "Đúng không?"',
        },
        choices: [
          {
            id: 'c04-07a',
            text: { en: '"Yes. I do. I was scared to say it."', vi: '"Đúng. Mình thích bạn. Mình sợ nói ra."' },
            tags: ['courage', 'integrity'],
            effects: { relationships: { mai: { trust: 15, friendship: 10 } }, personality: { courage: 4, integrity: 3 } },
            nextScene: 's04-08a',
          },
          {
            id: 'c04-07b',
            text: { en: '"I think you\'re really special. But I\'m not sure what this is."', vi: '"Mình nghĩ bạn rất đặc biệt. Nhưng mình chưa chắc đây là gì."' },
            tags: ['honesty', 'empathy'],
            effects: { relationships: { mai: { trust: 10 } }, personality: { empathy: 3, honesty: 2 } },
            nextScene: 's04-08b',
          },
          {
            id: 'c04-07c',
            text: { en: '"Who told you that? It\'s not a big deal."', vi: '"Ai nói vậy? Không phải chuyện lớn."' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { mai: { trust: -12, friendship: -8 } }, personality: { avoidance: 4 } },
            nextScene: 's04-08c',
          },
        ],
      },
      {
        id: 's04-08a',
        character: 'mai',
        dialogue: {
          en: 'She laughs — nervous, happy. "Good. Because I like you too. But I don\'t want us to rush anything."',
          vi: 'Cô ấy cười — hồi hộp, vui. "Tốt. Vì mình cũng thích bạn. Nhưng mình không muốn vội vàng."',
        },
        nextScene: 's04-09',
      },
      {
        id: 's04-08b',
        character: 'mai',
        dialogue: {
          en: '"Honest. I like that." She smiles. "Let\'s just see where this goes. No pressure."',
          vi: '"Thật thà. Mình thích điều đó." Cô ấy mỉm cười. "Cứ xem sao. Không áp lực."',
        },
        nextScene: 's04-09',
      },
      {
        id: 's04-08c',
        character: 'mai',
        dialogue: {
          en: '"Okay." She closes her book. The conversation is over.',
          vi: '"Ừ." Cô ấy đóng sách. Cuộc nói chuyện kết thúc.',
        },
        nextScene: 's04-09',
      },
      {
        id: 's04-09',
        character: 'narrator',
        dialogue: {
          en: 'Winter break begins. Snow covers the schoolyard. Whatever happens next, something already changed — you learned that feelings require the same courage as any exam.',
          vi: 'Kỳ nghỉ đông bắt đầu. Tuyết phủ sân trường. Dù chuyện gì xảy ra, điều gì đó đã thay đổi — bạn học được rằng cảm xúc cần dũng khí như bất kỳ kỳ thi nào.',
        },
        nextScene: 's04-10',
      },
      {
        id: 's04-10',
        character: 'narrator',
        dialogue: {
          en: 'First love isn\'t about getting it right. It\'s about learning to be honest — with someone else, and with yourself.',
          vi: 'Tình yêu đầu không phải về làm đúng. Mà là học cách thành thật — với người khác, và với chính mình.',
        },
        endStory: true,
      },
    ],
  },

  // Story 5: After the Fall — Failure
  {
    id: 'hs-05',
    lifeStage: 'high_school',
    category: 'failure',
    title: { en: 'After the Fall', vi: 'Sau Cú Ngã' },
    description: {
      en: 'You didn\'t make the basketball team. Your essay was rejected from the school magazine. Dad says "try harder." You want to disappear.',
      vi: 'Bạn trượt đội bóng rổ. Bài văn bị từ chối khỏi tạp chí trường. Bố bảo "cố lên đi." Bạn chỉ muốn biến mất.',
    },
    xpReward: 130,
    totalScenes: 13,
    startScene: 's05-01',
    characters: [
      { id: 'dad', name: { en: 'Dad', vi: 'Bố' }, color: '#5080b0', emoji: '👨' },
      { id: 'coach', name: { en: 'Coach Phong', vi: 'HLV Phong' }, color: '#806040', emoji: '🏀' },
      { id: 'linh', name: { en: 'Linh', vi: 'Linh' }, color: '#70a090', emoji: '👧' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 's05-01',
        character: 'narrator',
        dialogue: {
          en: 'The team list is posted on the gym wall. Your name isn\'t on it. You stand there for a long time while others celebrate around you.',
          vi: 'Danh sách đội dán trên tường phòng gym. Tên bạn không có. Bạn đứng đó rất lâu trong khi người khác ăn mừng xung quanh.',
        },
        nextScene: 's05-02',
      },
      {
        id: 's05-02',
        character: 'coach',
        dialogue: {
          en: '"You played well in tryouts. But we only had two spots. Come see me after practice — I want to talk."',
          vi: '"Em chơi tốt trong buổi tuyển chọn. Nhưng chỉ có hai suất. Gặp thầy sau buổi tập — thầy muốn nói chuyện."',
        },
        choices: [
          {
            id: 'c05-02a',
            text: { en: '"What\'s the point? I already failed."', vi: '"Còn gì để nói? Mình đã trượt rồi."' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { relationships: { coach: { respect: -5 } }, personality: { resilience: -2 } },
            delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { coach: { trust: -10 } } }, message: { en: 'Coach Phong waited after practice. You never showed up.', vi: 'HLV Phong đợi sau buổi tập. Bạn không đến.' } }],
            nextScene: 's05-03a',
          },
          {
            id: 'c05-02b',
            text: { en: '"Okay. I\'ll be there."', vi: '"Vâng. Em sẽ đến."' },
            tags: ['resilience', 'courage'],
            effects: { relationships: { coach: { trust: 8, respect: 5 } }, personality: { resilience: 3, courage: 2 } },
            nextScene: 's05-03b',
          },
          {
            id: 'c05-02c',
            text: { en: 'Nod and walk away without answering.', vi: 'Gật đầu và bỏ đi không trả lời.' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { coach: { trust: -3 } }, personality: { avoidance: 3 } },
            nextScene: 's05-03a',
          },
        ],
      },
      {
        id: 's05-03a',
        character: 'narrator',
        dialogue: {
          en: 'You skip the meeting. At home, another blow — an email: your essay wasn\'t selected for the school magazine.',
          vi: 'Bạn bỏ cuộc gặp. Ở nhà, thêm một cú sốc — email: bài văn không được chọn vào tạp chí trường.',
        },
        nextScene: 's05-04',
      },
      {
        id: 's05-03b',
        character: 'coach',
        dialogue: {
          en: '"You have real potential. I run a development squad for players who didn\'t make the cut. It\'s not glamorous, but it works."',
          vi: '"Em có tiềm năng thật. Thầy có đội phát triển cho cầu thủ trượt tuyển. Không hào nhoáng, nhưng hiệu quả."',
        },
        choices: [
          {
            id: 'c05-03a',
            text: { en: '"I\'ll show up. Every session."', vi: '"Em sẽ đến. Mỗi buổi."' },
            tags: ['discipline', 'resilience'],
            effects: { relationships: { coach: { trust: 12, respect: 10 } }, personality: { discipline: 4, resilience: 4 } },
            nextScene: 's05-04',
          },
          {
            id: 'c05-03b',
            text: { en: '"Thanks, but I think I\'m done with basketball."', vi: '"Cảm ơn thầy, nhưng em nghĩ mình dừng bóng rổ."' },
            tags: ['assertiveness', 'ownership'],
            effects: { relationships: { coach: { respect: 5 } }, personality: { assertiveness: 3, ownership: 3 } },
            nextScene: 's05-04',
          },
        ],
      },
      {
        id: 's05-04',
        character: 'dad',
        dialogue: {
          en: '"Two rejections in one day. You need to try harder. Life doesn\'t hand out participation trophies."',
          vi: '"Hai lần bị từ chối trong một ngày. Con cần cố gắng hơn. Cuộc sống không trao cúp tham gia."',
        },
        choices: [
          {
            id: 'c05-04a',
            text: { en: '"I DID try hard. That\'s what hurts."', vi: '"Con ĐÃ cố gắng. Đó mới là điều đau."' },
            tags: ['assertiveness', 'courage'],
            effects: { relationships: { dad: { respect: 8, trust: 5 } }, personality: { assertiveness: 4, courage: 3 } },
            nextScene: 's05-05',
          },
          {
            id: 'c05-04b',
            text: { en: 'Stay silent and go to your room.', vi: 'Im lặng và về phòng.' },
            tags: ['avoid_conflict', 'avoidance'],
            effects: { relationships: { dad: { trust: -5 } }, personality: { avoidance: 3, resilience: -2 } },
            delayedConsequences: [{ triggerAfterScenes: 3, effects: { relationships: { dad: { trust: -8 } } }, message: { en: 'Dad knocked on your door that evening. You pretended to be asleep.', vi: 'Bố gõ cửa phòng tối hôm đó. Bạn giả vờ đang ngủ.' } }],
            nextScene: 's05-05',
          },
          {
            id: 'c05-04c',
            text: { en: '"You\'re right. I\'ll do better."', vi: '"Bố đúng. Con sẽ làm tốt hơn."' },
            tags: ['avoid_conflict', 'short_term_gain'],
            effects: { relationships: { dad: { trust: 5, dependency: 8 } }, personality: { ownership: -2 } },
            nextScene: 's05-05',
          },
        ],
      },
      {
        id: 's05-05',
        character: 'linh',
        dialogue: {
          en: '"I read your essay before you submitted it. It was honest and raw. The magazine wanted something safer." She sits next to you on the bench.',
          vi: '"Mình đọc bài văn trước khi bạn nộp. Nó chân thật và sâu sắc. Tạp chí muốn thứ an toàn hơn." Cô ấy ngồi cạnh bạn trên ghế.',
        },
        choices: [
          {
            id: 'c05-05a',
            text: { en: '"Maybe it wasn\'t good enough."', vi: '"Có lẽ nó chưa đủ tốt."' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { relationships: { linh: { trust: -3 } }, personality: { resilience: -2 } },
            nextScene: 's05-06',
          },
          {
            id: 'c05-05b',
            text: { en: '"Thanks for saying that. I needed to hear it."', vi: '"Cảm ơn. Mình cần nghe điều đó."' },
            tags: ['empathy', 'resilience'],
            effects: { relationships: { linh: { friendship: 10, trust: 8 } }, personality: { empathy: 2, resilience: 3 } },
            nextScene: 's05-06',
          },
          {
            id: 'c05-05c',
            text: { en: '"I\'m starting an online blog instead. Want to be my first reader?"', vi: '"Mình sẽ mở blog online. Bạn làm độc giả đầu tiên nhé?"' },
            tags: ['courage', 'ownership'],
            effects: { relationships: { linh: { friendship: 12, trust: 10 } }, personality: { courage: 4, ownership: 4 } },
            nextScene: 's05-06',
          },
        ],
      },
      {
        id: 's05-06',
        character: 'narrator',
        dialogue: {
          en: 'A week of grey days. You notice something: the players who made the team practice twice as hard now. Fear of losing what they have.',
          vi: 'Một tuần ngày xám xịt. Bạn để ý: cầu thủ vào đội tập gấp đôi. Sợ mất thứ mình có.',
        },
        choices: [
          {
            id: 'c05-06a',
            text: { en: 'Go to the development squad practice.', vi: 'Đến buổi tập đội phát triển.' },
            tags: ['resilience', 'discipline'],
            effects: { relationships: { coach: { trust: 10 } }, personality: { resilience: 4, discipline: 3 } },
            nextScene: 's05-07a',
          },
          {
            id: 'c05-06b',
            text: { en: 'Focus on writing. Publish the rejected essay online.', vi: 'Tập trung viết. Đăng bài bị từ chối lên mạng.' },
            tags: ['courage', 'ownership'],
            effects: { relationships: { linh: { respect: 10 } }, personality: { courage: 4, ownership: 4 } },
            nextScene: 's05-07b',
          },
          {
            id: 'c05-06c',
            text: { en: 'Do nothing. Scroll your phone until midnight.', vi: 'Không làm gì. Lướt điện thoại đến nửa đêm.' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { personality: { resilience: -4, discipline: -3 } },
            delayedConsequences: [{ triggerAfterScenes: 2, effects: { personality: { resilience: -3 } }, message: { en: 'The days blurred together. Nothing changed, and that was the worst part.', vi: 'Các ngày trôi qua mờ nhạt. Không gì thay đổi, và đó là phần tệ nhất.' } }],
            nextScene: 's05-07c',
          },
        ],
      },
      {
        id: 's05-07a',
        character: 'coach',
        dialogue: {
          en: '"You came back. That\'s already more than most." He tosses you a ball. "Let\'s work on your weak hand."',
          vi: '"Em quay lại. Điều đó đã hơn hầu hết người khác." Thầy ném bóng cho bạn. "Luyện tay yếu đi."',
        },
        nextScene: 's05-08',
      },
      {
        id: 's05-07b',
        character: 'linh',
        dialogue: {
          en: '"Fifty people shared your essay in the first day. Someone commented: This is exactly how failure feels."',
          vi: '"Năm mươi người share bài trong ngày đầu. Có người comment: Đây chính xác là cảm giác thất bại."',
        },
        nextScene: 's05-08',
      },
      {
        id: 's05-07c',
        character: 'narrator',
        dialogue: {
          en: 'Time passes, but you\'re stuck in the same loop. Rejection becomes a story you tell yourself about who you are.',
          vi: 'Thời gian trôi, nhưng bạn kẹt trong vòng lặp cũ. Thất bại trở thành câu chuyện bạn kể về bản thân.',
        },
        nextScene: 's05-08',
      },
      {
        id: 's05-08',
        character: 'dad',
        dialogue: {
          en: '"I was hard on you. I thought that\'s what you needed." He pauses. "Maybe I was wrong about that."',
          vi: '"Bố cứng rắn với con. Bố nghĩ đó là điều con cần." Ông dừng lại. "Có lẽ bố sai."'
        },
        choices: [
          {
            id: 'c05-08a',
            text: { en: '"I know you meant well. But I need to find my own way back."', vi: '"Con biết bố tốt. Nhưng con cần tự tìm đường quay lại."' },
            tags: ['empathy', 'ownership'],
            effects: { relationships: { dad: { trust: 12, respect: 10 } }, personality: { empathy: 3, ownership: 3 } },
            nextScene: 's05-09',
          },
          {
            id: 'c05-08b',
            text: { en: '"It\'s okay. We\'re both learning."', vi: '"Không sao. Cả hai đều đang học."' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { dad: { friendship: 10, trust: 8 } }, personality: { empathy: 4, cooperation: 2 } },
            nextScene: 's05-09',
          },
        ],
      },
      {
        id: 's05-09',
        character: 'narrator',
        dialogue: {
          en: 'Months later. You didn\'t make the team that season. But you\'re stronger, faster, and you found a voice in writing that no rejection could take away.',
          vi: 'Vài tháng sau. Bạn không vào đội mùa đó. Nhưng bạn khỏe hơn, nhanh hơn, và tìm được giọng viết mà không lời từ chối nào lấy đi được.',
        },
        nextScene: 's05-10',
      },
      {
        id: 's05-10',
        character: 'narrator',
        dialogue: {
          en: 'Failure didn\'t define you. How you responded to it started to. That\'s the lesson no trophy could teach.',
          vi: 'Thất bại không định nghĩa bạn. Cách bạn phản ứng mới bắt đầu định nghĩa. Đó là bài học không cúp nào dạy được.',
        },
        endStory: true,
      },
    ],
  },
];

STORIES.push(...STORIES_PART2);

function getStoriesForStage(stageId) {
  return STORIES.filter(s => s.lifeStage === stageId);
}

function getStoryById(id) {
  return STORIES.find(s => s.id === id);
}

function getAllCharacters() {
  const chars = {};
  STORIES.forEach(story => {
    story.characters.forEach(c => {
      if (!chars[c.id]) chars[c.id] = c;
    });
  });
  return chars;
}
