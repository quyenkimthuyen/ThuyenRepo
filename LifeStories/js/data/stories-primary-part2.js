const PRIMARY_STORIES_PART2 = [
  // 3. Hộp Cơm Thừa — Chia Sẻ
  {
    id: 'ps-03',
    lifeStage: 'primary_school',
    category: 'sharing',
    title: { en: 'The Extra Lunch', vi: 'Hộp Cơm Thừa' },
    description: {
      en: 'Mom packed extra spring rolls — your favorite. At lunch, Tú opens an empty box. He forgot his lunch at home.',
      vi: 'Mẹ gói thêm nem rán — món bạn thích nhất. Giờ ăn trưa, Tú mở hộp cơm trống không. Cậu ấy quên mang cơm đến trường.',
    },
    xpReward: 80,
    totalScenes: 12,
    startScene: 'ps03-01',
    characters: [
      { id: 'tu', name: { en: 'Tú', vi: 'Tú' }, color: '#a08050', emoji: '👦' },
      { id: 'lan', name: { en: 'Lan', vi: 'Lan' }, color: '#80a0c0', emoji: '👧' },
      { id: 'mom', name: { en: 'Mom', vi: 'Mẹ' }, color: '#c09070', emoji: '👩' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 'ps03-01',
        character: 'narrator',
        dialogue: {
          en: 'Lunch bell. You open your box — rice, vegetables, and three golden spring rolls. Mom made extra because you loved them yesterday.',
          vi: 'Trống giờ ăn trưa. Bạn mở hộp — cơm, rau, và ba cái nem rán vàng ươm. Mẹ gói thêm vì hôm qua bạn thích lắm.',
        },
        nextScene: 'ps03-02',
      },
      {
        id: 'ps03-02',
        character: 'tu',
        dialogue: {
          en: 'Tú opens his lunch box. Empty. He stares inside, then quickly closes it. His ears turn red.',
          vi: 'Tú mở hộp cơm. Trống không. Cậu ấy nhìn chằm chằm, rồi đóng nắp lại thật nhanh. Tai đỏ ửng.',
        },
        choices: [
          {
            id: 'ps03-c02a',
            text: { en: 'Slide one spring roll onto his tray without saying anything.', vi: 'Đẩy một cái nem sang khay Tú, không nói gì.' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { tu: { friendship: 12, trust: 10 } }, personality: { empathy: 4 } },
            nextScene: 'ps03-03a',
          },
          {
            id: 'ps03-c02b',
            text: { en: '"Tú, want to share? I have extra."', vi: '"Tú, chia nhau không? Tớ có thừa."' },
            tags: ['empathy', 'assertiveness'],
            effects: { relationships: { tu: { friendship: 10, trust: 8 } }, personality: { empathy: 3, assertiveness: 2 } },
            nextScene: 'ps03-03a',
          },
          {
            id: 'ps03-c02c',
            text: { en: 'Pretend not to notice. You wanted those rolls for after-school club.', vi: 'Giả vờ không thấy. Bạn định để ăn sau giờ sinh hoạt ngoại khóa.' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { relationships: { tu: { friendship: -8, trust: -10 } }, personality: { empathy: -2 } },
            delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { tu: { friendship: -5 } } }, message: { en: 'At club time, Tú sits far from you. He didn\'t forget.', vi: 'Giờ sinh hoạt, Tú ngồi xa bạn. Cậu ấy không quên đâu.' } }],
            nextScene: 'ps03-03b',
          },
        ],
      },
      {
        id: 'ps03-03a',
        character: 'tu',
        dialogue: {
          en: 'Tú looks at the spring roll, then at you. "...Thanks." He breaks it in half and gives you back a piece. "Half for you too."',
          vi: 'Tú nhìn cái nem, rồi nhìn bạn. "...Cảm ơn." Cậu ấy bẻ đôi, đưa lại bạn một nửa. "Nửa của cậu nữa."',
        },
        nextScene: 'ps03-04',
      },
      {
        id: 'ps03-03b',
        character: 'lan',
        dialogue: {
          en: 'Lan whispers: "Tú forgot his lunch again. His mom works far away — he rushes out every morning."',
          vi: 'Lan thì thầm: "Tú hay quên cơm lắm. Mẹ cậu ấy làm xa — sáng nào cũng vội ra khỏi nhà."',
        },
        choices: [
          {
            id: 'ps03-c03a',
            text: { en: 'Walk over with two spring rolls. "I can\'t eat all of these."', vi: 'Mang hai cái nem qua. "Tớ ăn hết không nổi đâu."' },
            tags: ['empathy', 'courage'],
            effects: { relationships: { tu: { friendship: 10, trust: 8 } }, personality: { empathy: 3, courage: 2 } },
            nextScene: 'ps03-04',
          },
          {
            id: 'ps03-c03b',
            text: { en: 'Feel bad but keep eating. Maybe tomorrow.', vi: 'Thấy buồn nhưng vẫn ăn. Hay là ngày mai.' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { personality: { empathy: 1, avoidance: 2 } },
            nextScene: 'ps03-04',
          },
        ],
      },
      {
        id: 'ps03-04',
        character: 'narrator',
        dialogue: {
          en: 'After lunch, your stomach is fine but your mind isn\'t. You keep thinking about the third spring roll still in your box.',
          vi: 'Ăn xong, bụng no nhưng đầu óc thì không. Bạn cứ nghĩ tới cái nem thứ ba còn nằm trong hộp.',
        },
        choices: [
          {
            id: 'ps03-c04a',
            text: { en: 'Give Tú the last one too. You\'ll be hungry later — but he\'s hungrier now.', vi: 'Đưa Tú cái nem cuối. Chiều mình đói — nhưng giờ cậu ấy đói hơn.' },
            tags: ['empathy', 'responsibility'],
            effects: { relationships: { tu: { friendship: 15, trust: 12 } }, personality: { empathy: 4, responsibility: 2 } },
            nextScene: 'ps03-05',
          },
          {
            id: 'ps03-c04b',
            text: { en: 'Save it. Sharing doesn\'t mean giving away everything.', vi: 'Giữ lại. Chia sẻ không có nghĩa đưa hết đi.' },
            tags: ['assertiveness', 'discipline'],
            effects: { relationships: { tu: { trust: 5 } }, personality: { assertiveness: 2, discipline: 2 } },
            nextScene: 'ps03-05',
          },
        ],
      },
      {
        id: 'ps03-05',
        character: 'tu',
        dialogue: {
          en: 'Tú walks beside you after school. "My mom... she works at the market. Leaves before I wake up." He kicks a leaf. "I forget stuff a lot."',
          vi: 'Tú đi cạnh bạn tan học. "Mẹ tớ... mẹ bán chợ. Đi sớm trước khi tớ thức dậy." Cậu ấy đá một chiếc lá. "Tớ hay quên đồ lắm."',
        },
        choices: [
          {
            id: 'ps03-c05a',
            text: { en: '"I forget things too. Want to remind each other in the morning?"', vi: '"Tớ cũng hay quên. Mai mình nhắc nhau được không?"' },
            tags: ['cooperation', 'empathy'],
            effects: { relationships: { tu: { friendship: 15, trust: 10 } }, personality: { cooperation: 4, empathy: 3 } },
            nextScene: 'ps03-06',
          },
          {
            id: 'ps03-c05b',
            text: { en: '"That must be hard." Walk together in silence.', vi: '"Chắc vất vả lắm." Đi cạnh nhau trong im lặng.' },
            tags: ['empathy'],
            effects: { relationships: { tu: { trust: 8 } }, personality: { empathy: 3 } },
            nextScene: 'ps03-06',
          },
        ],
      },
      {
        id: 'ps03-06',
        character: 'mom',
        dialogue: {
          en: 'At home, Mom asks: "You ate all the spring rolls?" She smiles. "I can make more tomorrow."',
          vi: 'Về nhà, Mẹ hỏi: "Con ăn hết nem rồi à?" Mẹ cười. "Mai mẹ làm thêm."',
        },
        choices: [
          {
            id: 'ps03-c06a',
            text: { en: 'Tell her about Tú. "Can we pack a little extra sometimes?"', vi: 'Kể về Tú. "Mẹ có thể gói thêm chút đôi khi được không?"' },
            tags: ['empathy', 'cooperation'],
            effects: { relationships: { tu: { friendship: 5 } }, personality: { empathy: 3, cooperation: 3 } },
            delayedConsequences: [{ triggerAfterScenes: 2, effects: { relationships: { tu: { friendship: 10, trust: 8 } } }, message: { en: 'The next week, Mom packs two small boxes. Tú\'s eyes get wet, but he laughs.', vi: 'Tuần sau, Mẹ gói hai hộp nhỏ. Tú rớm nước mắt, nhưng cười.' } }],
            nextScene: 'ps03-07',
          },
          {
            id: 'ps03-c06b',
            text: { en: '"I shared with a friend." Leave it at that.', vi: '"Con chia bạn rồi." Chỉ nói vậy thôi.' },
            tags: ['integrity'],
            effects: { personality: { integrity: 2 } },
            nextScene: 'ps03-07',
          },
        ],
      },
      {
        id: 'ps03-07',
        character: 'lan',
        dialogue: {
          en: 'Lan says at recess: "Tú told everyone you shared lunch. Now three kids want to do a lunch swap club."',
          vi: 'Lan nói lúc ra chơi: "Tú kể cả lớp cậu chia cơm. Giờ ba bạn muốn lập câu lạc bộ đổi đồ ăn trưa."',
        },
        choices: [
          {
            id: 'ps03-c07a',
            text: { en: '"Good idea. But only if everyone brings something."', vi: '"Hay đấy. Nhưng ai cũng phải mang gì đó đến."' },
            tags: ['cooperation', 'responsibility'],
            effects: { personality: { cooperation: 3, responsibility: 3 } },
            nextScene: 'ps03-08',
          },
          {
            id: 'ps03-c07b',
            text: { en: '"I just helped one friend. Not a club."', vi: '"Tớ chỉ giúp một bạn. Không phải câu lạc bộ."' },
            tags: ['assertiveness'],
            effects: { personality: { assertiveness: 3 } },
            nextScene: 'ps03-08',
          },
        ],
      },
      {
        id: 'ps03-08',
        character: 'narrator',
        dialogue: {
          en: 'Sharing isn\'t about being a hero. Sometimes it\'s one spring roll, given quietly, at the right moment.',
          vi: 'Chia sẻ không phải làm anh hùng. Đôi khi chỉ là một cái nem, đưa đi thật nhẹ, đúng lúc cần.',
        },
        endStory: true,
      },
    ],
  },

  // 4. Con Chó Cuối Ngõ — Dũng Cảm
  {
    id: 'ps-04',
    lifeStage: 'primary_school',
    category: 'courage',
    title: { en: 'The Dog at the Alley', vi: 'Con Chó Cuối Ngõ' },
    description: {
      en: 'The shortcut home goes through an alley. A big dog lies in the middle. Your friends are watching to see what you do.',
      vi: 'Đường tắt về nhà phải đi qua một ngõ. Một con chó to nằm giữa lối. Bạn bè đứng nhìn xem bạn sẽ làm gì.',
    },
    xpReward: 90,
    totalScenes: 13,
    startScene: 'ps04-01',
    characters: [
      { id: 'bao', name: { en: 'Bảo', vi: 'Bảo' }, color: '#6080a0', emoji: '👦' },
      { id: 'vy', name: { en: 'Vy', vi: 'Vy' }, color: '#c080a0', emoji: '👧' },
      { id: 'uncle', name: { en: 'Uncle Tám', vi: 'Chú Tám' }, color: '#807060', emoji: '👨' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 'ps04-01',
        character: 'narrator',
        dialogue: {
          en: 'School ends. Bảo says: "Let\'s take the alley. It\'s faster." Vy nods. The alley is narrow, cool, and quiet.',
          vi: 'Tan học. Bảo bảo: "Đi ngõ cho nhanh." Vy gật đầu. Ngõ hẹp, mát, yên lặng.',
        },
        nextScene: 'ps04-02',
      },
      {
        id: 'ps04-02',
        character: 'narrator',
        dialogue: {
          en: 'Halfway through — a dog. Not small. Brown fur, tired eyes. It lies across the path, not moving.',
          vi: 'Đi được nửa ngõ — một con chó. Không nhỏ. Lông nâu, mắt mệt. Nó nằm ngang lối, không nhúc nhích.',
        },
        choices: [
          {
            id: 'ps04-c02a',
            text: { en: 'Walk forward slowly, trying to look brave.', vi: 'Bước từ từ về phía trước, cố trông dũng cảm.' },
            tags: ['courage', 'short_term_gain'],
            effects: { personality: { courage: 2 } },
            delayedConsequences: [{ triggerAfterScenes: 2, effects: { relationships: { bao: { respect: -5 } } }, message: { en: 'The dog growls. You jump back. Your hands shake.', vi: 'Con chó gầm gừ. Bạn giật lùi. Tay run.' } }],
            nextScene: 'ps04-03a',
          },
          {
            id: 'ps04-c02b',
            text: { en: '"Let\'s go back. We can take the main road."', vi: '"Quay lại đi. Mình đi đường lớn."' },
            tags: ['responsibility', 'curiosity'],
            effects: { relationships: { vy: { trust: 5 } }, personality: { responsibility: 2 } },
            nextScene: 'ps04-03b',
          },
          {
            id: 'ps04-c02c',
            text: { en: 'Call out: "Is anyone\'s dog here?"', vi: 'Gọi to: "Nhà ai nuôi chó đây không ạ?"' },
            tags: ['courage', 'cooperation'],
            effects: { personality: { courage: 3, cooperation: 2 } },
            nextScene: 'ps04-03c',
          },
        ],
      },
      {
        id: 'ps04-03a',
        character: 'bao',
        dialogue: {
          en: '"Scared?" Bảo laughs, but he doesn\'t walk forward either.',
          vi: '"Sợ à?" Bảo cười, nhưng cậu ấy cũng không bước lên.'
        },
        nextScene: 'ps04-04',
      },
      {
        id: 'ps04-03b',
        character: 'bao',
        dialogue: {
          en: '"Chicken!" Bảo shouts. Vy doesn\'t laugh. She looks at the dog quietly.',
          vi: '"Nhát gan!" Bảo la. Vy không cười. Cô ấy nhìn con chó lặng lẽ.'
        },
        choices: [
          {
            id: 'ps04-c03a',
            text: { en: '"Being scared is okay. Getting hurt isn\'t smart."', vi: '"Sợ cũng được. Bị thương thì không hay."' },
            tags: ['assertiveness', 'responsibility'],
            effects: { relationships: { vy: { friendship: 8, respect: 8 } }, personality: { assertiveness: 3, responsibility: 3 } },
            nextScene: 'ps04-04',
          },
          {
            id: 'ps04-c03b',
            text: { en: 'Run back without answering.', vi: 'Chạy quay lại, không trả lời.' },
            tags: ['avoidance'],
            effects: { relationships: { bao: { friendship: -3 } }, personality: { avoidance: 3 } },
            nextScene: 'ps04-04',
          },
        ],
      },
      {
        id: 'ps04-03c',
        character: 'uncle',
        dialogue: {
          en: 'Uncle Tám opens a door. "That\'s Bông — my shop dog. He\'s sick today. Sorry, kids." He pats the dog gently.',
          vi: 'Chú Tám mở cửa. "Con Bông đấy — chó tiệm chú. Hôm nay nó ốm. Xin lỗi các cháu." Chú xoa đầu chó nhẹ nhàng.',
        },
        nextScene: 'ps04-05',
      },
      {
        id: 'ps04-04',
        character: 'vy',
        dialogue: {
          en: 'Vy whispers: "My brother said — if a dog lies down, it might be tired, not angry. Maybe we should tell an adult."',
          vi: 'Vy thì thầm: "Anh tớ bảo — chó nằm có thể mệt, chưa chắc đã dữ. Hay mình nói người lớn nhỉ."'
        },
        choices: [
          {
            id: 'ps04-c04a',
            text: { en: 'Knock on the nearest door and ask for help.', vi: 'Gõ cửa nhà gần nhất nhờ giúp.' },
            tags: ['courage', 'responsibility'],
            effects: { personality: { courage: 4, responsibility: 4 } },
            nextScene: 'ps04-03c',
          },
          {
            id: 'ps04-c04b',
            text: { en: 'Throw a stone to scare the dog away.', vi: 'Ném đá để dọa chó chạy.' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { personality: { empathy: -3, integrity: -2 } },
            delayedConsequences: [{ triggerAfterScenes: 3, effects: { relationships: { vy: { trust: -15, respect: -10 } } }, message: { en: 'The dog yelps. Vy looks at you like she doesn\'t know you.', vi: 'Chó kêu đau. Vy nhìn bạn như không nhận ra.' } }],
            nextScene: 'ps04-05',
          },
          {
            id: 'ps04-c04c',
            text: { en: 'Wait at a distance until the dog moves on its own.', vi: 'Đứng xa đợi chó tự đi.' },
            tags: ['discipline', 'curiosity'],
            effects: { personality: { discipline: 2, curiosity: 2 } },
            nextScene: 'ps04-05',
          },
        ],
      },
      {
        id: 'ps04-05',
        character: 'uncle',
        dialogue: {
          en: 'Uncle Tám brings water for Bông. "Brave doesn\'t mean not scared." He looks at you three. "Brave means doing the right thing even when scared."',
          vi: 'Chú Tám mang nước cho Bông. "Dũng cảm không phải không sợ." Chú nhìn ba đứa. "Dũng cảm là vẫn làm điều đúng dù đang sợ."',
        },
        nextScene: 'ps04-06',
      },
      {
        id: 'ps04-06',
        character: 'bao',
        dialogue: {
          en: 'Bảo is quiet. "...Sorry I called you chicken. I was scared too." He looks at his shoes.',
          vi: 'Bảo im lặng. "...Xin lỗi vì gọi cậu nhát gan. Tớ cũng sợ mà." Cậu ấy nhìn giày.',
        },
        choices: [
          {
            id: 'ps04-c06a',
            text: { en: '"We were all scared. Next time, let\'s find an adult together."', vi: '"Cả bọn đều sợ. Lần sau mình tìm người lớn cùng nhau nhé."' },
            tags: ['cooperation', 'empathy'],
            effects: { relationships: { bao: { friendship: 10, trust: 8 }, vy: { friendship: 8 } }, personality: { cooperation: 3, empathy: 3 } },
            nextScene: 'ps04-07',
          },
          {
            id: 'ps04-c06b',
            text: { en: '"Yeah. Don\'t do that again."', vi: '"Ừ. Đừng làm vậy nữa."' },
            tags: ['assertiveness'],
            effects: { relationships: { bao: { respect: 5 } }, personality: { assertiveness: 3 } },
            nextScene: 'ps04-07',
          },
        ],
      },
      {
        id: 'ps04-07',
        character: 'narrator',
        dialogue: {
          en: 'You take the long way home. It adds ten minutes. But your chest feels lighter.',
          vi: 'Bạn đi đường vòng về nhà. Mất thêm mười phút. Nhưng lồng ngực nhẹ hơn.',
        },
        nextScene: 'ps04-08',
      },
      {
        id: 'ps04-08',
        character: 'narrator',
        dialogue: {
          en: 'A week later, Bông wags his tail when he sees you. Courage, you realize, isn\'t a roar. Sometimes it\'s a knock on a door.',
          vi: 'Một tuần sau, Bông vẫy đuôi khi thấy bạn. Bạn hiểu ra: dũng cảm không phải tiếng gầm. Đôi khi chỉ là một cú gõ cửa.',
        },
        endStory: true,
      },
    ],
  },

  // 5. Cây Cảnh Của Cô — Trách Nhiệm
  {
    id: 'ps-05',
    lifeStage: 'primary_school',
    category: 'responsibility',
    title: { en: 'The Teacher\'s Plant', vi: 'Cây Cảnh Của Cô' },
    description: {
      en: 'You were chosen to water the class plant this week. On Thursday, you forget — too excited about the field trip tomorrow.',
      vi: 'Tuần này bạn được giao tưới cây cảnh lớp. Thứ Năm, bạn quên mất — vì mải mê chuyến dã ngoại ngày mai.',
    },
    xpReward: 90,
    totalScenes: 13,
    startScene: 'ps05-01',
    characters: [
      { id: 'teacher', name: { en: 'Ms. Hoa', vi: 'Cô Hoa' }, color: '#c08090', emoji: '👩‍🏫' },
      { id: 'duy', name: { en: 'Duy', vi: 'Duy' }, color: '#70a080', emoji: '👦' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      {
        id: 'ps05-01',
        character: 'teacher',
        dialogue: {
          en: '"This week, you\'ll care for our class plant." Ms. Hoa puts a small watering chart on the board with your name on it. "Just a little water each day."',
          vi: '"Tuần này, em sẽ chăm cây cảnh lớp nhé." Cô Hoa dán bảng tưới nước trên bảng, có tên bạn. "Mỗi ngày một chút thôi."',
        },
        choices: [
          {
            id: 'ps05-c01a',
            text: { en: '"I\'ll take good care of it!"', vi: '"Em sẽ chăm cẩn thận ạ!"' },
            tags: ['responsibility', 'ownership'],
            effects: { relationships: { teacher: { trust: 10, respect: 8 } }, personality: { responsibility: 3, ownership: 3 } },
            nextScene: 'ps05-02',
          },
          {
            id: 'ps05-c01b',
            text: { en: 'Nod quietly. It seems easy enough.', vi: 'Gật đầu nhẹ. Có vẻ dễ mà.' },
            tags: ['short_term_gain'],
            effects: { relationships: { teacher: { trust: 5 } }, personality: { responsibility: 1 } },
            nextScene: 'ps05-02',
          },
        ],
      },
      {
        id: 'ps05-02',
        character: 'narrator',
        dialogue: {
          en: 'Monday, Tuesday, Wednesday — you water the plant. A small green sprout seems happier each day.',
          vi: 'Thứ Hai, Ba, Tư — bạn tưới cây. Mầm xanh nhỏ có vẻ vui hơn mỗi ngày.',
        },
        nextScene: 'ps05-03',
      },
      {
        id: 'ps05-03',
        character: 'duy',
        dialogue: {
          en: '"Field trip tomorrow! Zoo!" Duy can\'t stop talking. You forget the chart on the board completely.',
          vi: '"Ngày mai dã ngoại! Sở thú đấy!" Duy nói không ngừng. Bạn quên sạch bảng tưới nước trên bảng.',
        },
        choices: [
          {
            id: 'ps05-c03a',
            text: { en: 'Run back to class before going home to water the plant.', vi: 'Chạy về lớp trước khi về nhà để tưới cây.' },
            tags: ['discipline', 'responsibility'],
            effects: { relationships: { teacher: { trust: 8 } }, personality: { discipline: 4, responsibility: 4 } },
            nextScene: 'ps05-04a',
          },
          {
            id: 'ps05-c03b',
            text: { en: 'Go home excited. You\'ll remember tomorrow morning.', vi: 'Về nhà mải mê. Sáng mai nhớ cũng được.' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { personality: { discipline: -2, responsibility: -3 } },
            delayedConsequences: [{ triggerAfterScenes: 2, effects: { relationships: { teacher: { trust: -10 } } }, message: { en: 'Thursday passes. The soil is dry, cracked.', vi: 'Thứ Năm trôi qua. Đất khô, nứt nẻ.' } }],
            nextScene: 'ps05-04b',
          },
        ],
      },
      {
        id: 'ps05-04a',
        character: 'narrator',
        dialogue: {
          en: 'You water the plant alone in the empty classroom. The leaves seem to sigh with relief.',
          vi: 'Bạn tưới cây một mình trong lớp trống. Lá cây như thở phào.',
        },
        nextScene: 'ps05-05',
      },
      {
        id: 'ps05-04b',
        character: 'narrator',
        dialogue: {
          en: 'Friday morning — field trip day. You rush past the plant. Its leaves hang down, soft and sad.',
          vi: 'Sáng thứ Sáu — ngày dã ngoại. Bạn chạy qua cây cảnh. Lá cây rũ xuống, mềm và buồn.',
        },
        choices: [
          {
            id: 'ps05-c04a',
            text: { en: 'Water it quickly before boarding the bus.', vi: 'Tưới nhanh trước khi lên xe buýt.' },
            tags: ['responsibility', 'courage'],
            effects: { relationships: { teacher: { trust: 5 } }, personality: { responsibility: 3 } },
            nextScene: 'ps05-05',
          },
          {
            id: 'ps05-c04b',
            text: { en: 'Tell yourself: "It\'s just a plant. The trip is more important."', vi: 'Tự nhủ: "Chỉ là cây thôi. Dã ngoại quan trọng hơn."' },
            tags: ['short_term_gain', 'avoidance'],
            effects: { personality: { responsibility: -4, empathy: -2 } },
            nextScene: 'ps05-05',
          },
        ],
      },
      {
        id: 'ps05-05',
        character: 'narrator',
        dialogue: {
          en: 'After the zoo trip — happy, tired, full of animal stories — you return to class. The plant\'s leaves are brown at the edges.',
          vi: 'Sau chuyến dã ngoại sở thú — vui, mệt, đầy chuyện kể — bạn về lớp. Lá cây úa vàng ở mép.',
        },
        nextScene: 'ps05-06',
      },
      {
        id: 'ps05-06',
        character: 'duy',
        dialogue: {
          en: 'Duy points at the plant. "It looks sick. Who was supposed to water it?" A few kids look at the chart — at your name.',
          vi: 'Duy chỉ cây cảnh. "Cây ốm rồi. Ai tưới thế?" Vài bạn nhìn bảng — nhìn tên bạn.',
        },
        choices: [
          {
            id: 'ps05-c06a',
            text: { en: '"I forgot. It\'s my fault."', vi: '"Tớ quên mất. Lỗi tớ."' },
            tags: ['integrity', 'courage'],
            effects: { relationships: { teacher: { trust: 8, respect: 10 } }, personality: { integrity: 4, courage: 4 } },
            nextScene: 'ps05-07',
          },
          {
            id: 'ps05-c06b',
            text: { en: '"I watered it Wednesday..." Leave out Thursday.', vi: '"Tớ tưới thứ Tư rồi..." Không nói thứ Năm.' },
            tags: ['avoidance', 'short_term_gain'],
            effects: { relationships: { teacher: { trust: -12 } }, personality: { integrity: -4 } },
            delayedConsequences: [{ triggerAfterScenes: 2, effects: { relationships: { duy: { trust: -10 } } }, message: { en: 'Duy saw you forget on Thursday. He doesn\'t say anything, but he knows.', vi: 'Duy thấy bạn quên thứ Năm. Cậu ấy không nói, nhưng biết.' } }],
            nextScene: 'ps05-07',
          },
          {
            id: 'ps05-c06c',
            text: { en: 'Stay silent. Hope nobody noticed.', vi: 'Im lặng. Mong không ai để ý.' },
            tags: ['avoidance'],
            effects: { personality: { integrity: -3, avoidance: 4 } },
            nextScene: 'ps05-07',
          },
        ],
      },
      {
        id: 'ps05-07',
        character: 'teacher',
        dialogue: {
          en: 'Ms. Hoa touches the dry soil gently. "Plants don\'t need much. But they need consistency." She looks at you — not angry, just serious.',
          vi: 'Cô Hoa chạm đất khô nhẹ nhàng. "Cây không cần nhiều. Nhưng cần đều đặn." Cô nhìn bạn — không giận, chỉ nghiêm.',
        },
        choices: [
          {
            id: 'ps05-c07a',
            text: { en: '"I\'m sorry, Ms. Hoa. Can I try to save it?"', vi: '"Em xin lỗi cô. Em thử cứu cây được không ạ?"' },
            tags: ['responsibility', 'resilience'],
            effects: { relationships: { teacher: { trust: 12, respect: 12 } }, personality: { responsibility: 4, resilience: 3 } },
            nextScene: 'ps05-08',
          },
          {
            id: 'ps05-c07b',
            text: { en: '"It\'s just one day..."', vi: '"Chỉ quên một ngày thôi mà..."' },
            tags: ['avoid_conflict', 'short_term_gain'],
            effects: { relationships: { teacher: { respect: -8 } }, personality: { responsibility: -2 } },
            nextScene: 'ps05-08',
          },
        ],
      },
      {
        id: 'ps05-08',
        character: 'narrator',
        dialogue: {
          en: 'You come early every morning for two weeks. Water, check leaves, whisper encouragement to a small plant.',
          vi: 'Hai tuần, bạn đến sớm mỗi sáng. Tưới nước, xem lá, thì thầm động viên cây nhỏ.',
        },
        nextScene: 'ps05-09',
      },
      {
        id: 'ps05-09',
        character: 'teacher',
        dialogue: {
          en: 'A new green leaf unfolds. Ms. Hoa smiles. "Responsibility isn\'t about never forgetting. It\'s about what you do after."',
          vi: 'Một lá xanh mới vươn ra. Cô Hoa mỉm cười. "Trách nhiệm không phải không bao giờ quên. Mà là bạn làm gì sau khi quên."',
        },
        nextScene: 'ps05-10',
      },
      {
        id: 'ps05-10',
        character: 'duy',
        dialogue: {
          en: 'Duy waters the plant with you one morning. "I forget stuff too. Maybe we can make a reminder chart together."',
          vi: 'Một sáng Duy tưới cây cùng bạn. "Tớ cũng hay quên. Hay mình làm bảng nhắc nhở chung."',
        },
        nextScene: 'ps05-11',
      },
      {
        id: 'ps05-11',
        character: 'narrator',
        dialogue: {
          en: 'The plant lives. So does the lesson: small duties, done steadily, grow into something you can be proud of.',
          vi: 'Cây sống. Bài học cũng vậy: việc nhỏ, làm đều đặn, lớn dần thành thứ bạn có thể tự hào.',
        },
        endStory: true,
      },
    ],
  },
];

PRIMARY_STORIES.push(...PRIMARY_STORIES_PART2);
STORIES.unshift(...PRIMARY_STORIES);
