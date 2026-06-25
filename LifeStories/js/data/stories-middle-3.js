const MIDDLE_STORIES_3 = [
  // 4. Sở Thích Lạ — Bản Sắc
  {
    id: 'ms-04',
    lifeStage: 'middle_school',
    category: 'identity',
    title: { en: 'The Strange Hobby', vi: 'Sở Thích Lạ' },
    description: {
      en: 'You love astronomy and stay up watching meteor showers. At the club fair, everyone signs up for basketball. Your friends ask why you\'re different.',
      vi: 'Bạn thích thiên văn, thức khuya xem mưa sao băng. Hội chợ câu lạc bộ, ai cũng đăng ký bóng rổ. Bạn bè hỏi sao bạn khác họ.',
    },
    xpReward: 95,
    totalScenes: 12,
    startScene: 'ms04-01',
    characters: [
      { id: 'dad', name: { en: 'Dad', vi: 'Bố' }, color: '#5080b0', emoji: '👨' },
      { id: 'ha', name: { en: 'Ha', vi: 'Hà' }, color: '#70a090', emoji: '👧' },
      { id: 'coach', name: { en: 'Coach Nam', vi: 'HLV Nam' }, color: '#806040', emoji: '🏀' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      { id: 'ms04-01', character: 'narrator', dialogue: { en: 'Club fair in the gym. Basketball booth has a line. Astronomy club: one folding table and a telescope.', vi: 'Hội chợ CLB trong phòng gym. Gian bóng rổ xếp hàng dài. CLB thiên văn: một bàn gấp và kính thiên văn.' }, nextScene: 'ms04-02' },
      { id: 'ms04-02', character: 'ha', dialogue: { en: '"You\'re not actually joining that, right?" Ha points at the telescope like it\'s contagious.', vi: '"Cậu không thật sự vào đó đâu ha?" Hà chỉ kính thiên văn như thứ gì đó lây lan.' }, choices: [
        { id: 'ms04-c02a', text: { en: 'Sign up for basketball instead. Fit in.', vi: 'Đăng ký bóng rổ. Cho giống mọi người.' }, tags: ['avoid_conflict', 'short_term_gain'], effects: { relationships: { ha: { friendship: 5 } }, personality: { ownership: -4, integrity: -2 } }, delayedConsequences: [{ triggerAfterScenes: 4, effects: { personality: { resilience: -3 } }, message: { en: 'You quit basketball after two practices. You weren\'t bad — you were just somewhere else inside.', vi: 'Bạn bỏ bóng rổ sau hai buổi tập. Không phải kém — mà lòng bạn ở chỗ khác.' } }], nextScene: 'ms04-03a' },
        { id: 'ms04-c02b', text: { en: 'Write your name on the astronomy list.', vi: 'Viết tên vào danh sách CLB thiên văn.' }, tags: ['courage', 'ownership'], effects: { relationships: { ha: { trust: -3 } }, personality: { courage: 4, ownership: 4 } }, nextScene: 'ms04-03b' },
        { id: 'ms04-c02c', text: { en: '"Why can\'t I like both?" Sign up for both clubs.', vi: '"Sao không thể thích cả hai?" Đăng ký cả hai.' }, tags: ['assertiveness', 'curiosity'], effects: { personality: { assertiveness: 3, curiosity: 3 } }, nextScene: 'ms04-03c' },
      ]},
      { id: 'ms04-03a', character: 'coach', dialogue: { en: 'Coach Nam is encouraging but you miss every pass. "Keep trying!" he shouts.', vi: 'HLV Nam động viên nhưng bạn hỏng mọi đường chuyền. "Cố lên!" thầy hô.' }, nextScene: 'ms04-04' },
      { id: 'ms04-03b', character: 'narrator', dialogue: { en: 'The astronomy teacher — old, gentle — shows you Jupiter through the lens. "Small in the eyepiece. Bigger than Earth."', vi: 'Thầy thiên văn — già, hiền — cho bạn nhìn Sao Mộc qua kính. "Nhỏ trong ống kính. Lớn hơn Trái Đất."' }, nextScene: 'ms04-04' },
      { id: 'ms04-03c', character: 'narrator', dialogue: { en: 'Two club meetings overlap. Something has to give.', vi: 'Hai buổi sinh hoạt trùng giờ. Phải buông một thứ.' }, choices: [
        { id: 'ms04-c03a', text: { en: 'Choose astronomy. It\'s where you feel alive.', vi: 'Chọn thiên văn. Nơi mình cảm thấy sống.' }, tags: ['ownership', 'courage'], effects: { personality: { ownership: 4, courage: 3 } }, nextScene: 'ms04-04' },
        { id: 'ms04-c03b', text: { en: 'Choose basketball. Easier socially.', vi: 'Chọn bóng rổ. Dễ hòa đồng hơn.' }, tags: ['avoid_conflict', 'short_term_gain'], effects: { personality: { ownership: -3 } }, nextScene: 'ms04-03a' },
      ]},
      { id: 'ms04-04', character: 'dad', dialogue: { en: 'Dad sees your star chart on the wall. "Practical skills matter more, son." He means well.', vi: 'Bố thấy bản đồ sao trên tường. "Kỹ năng thực tế quan trọng hơn, con." Ông nói với ý tốt.' }, choices: [
        { id: 'ms04-c04a', text: { en: '"This makes me want to learn — including math and physics."', vi: '"Cái này khiến con muốn học — cả Toán và Lý."' }, tags: ['assertiveness', 'curiosity'], effects: { relationships: { dad: { respect: 8, trust: 5 } }, personality: { assertiveness: 3, curiosity: 3 } }, nextScene: 'ms04-05' },
        { id: 'ms04-c04b', text: { en: 'Take down the chart. Avoid the argument.', vi: 'Gỡ bản đồ xuống. Tránh cãi nhau.' }, tags: ['avoid_conflict', 'avoidance'], effects: { relationships: { dad: { trust: 3 } }, personality: { ownership: -3, avoidance: 2 } }, nextScene: 'ms04-05' },
      ]},
      { id: 'ms04-05', character: 'ha', dialogue: { en: 'Ha shows up at astronomy club one day. "Okay fine. What am I looking at?" She pretends to be annoyed.', vi: 'Hà xuất hiện ở CLB thiên văn một hôm. "Thôi được. Nhìn cái gì đây?" Cô ấy giả vờ bực.' }, choices: [
        { id: 'ms04-c05a', text: { en: 'Show her the Pleiades. Let the sky speak.', vi: 'Chỉ cô ấy nhìm Sao Pleiades. Để bầu trời nói.' }, tags: ['empathy', 'cooperation'], effects: { relationships: { ha: { friendship: 12, trust: 10 } }, personality: { empathy: 3, cooperation: 2 } }, nextScene: 'ms04-06' },
        { id: 'ms04-c05b', text: { en: '"Thought this was too weird for you."', vi: '"Tưởng cậu thấy cái này quá dị."' }, tags: ['assertiveness'], effects: { relationships: { ha: { trust: -3 } }, personality: { assertiveness: 2 } }, nextScene: 'ms04-06' },
      ]},
      { id: 'ms04-06', character: 'narrator', dialogue: { en: 'Meteor shower night. Three of you on the school roof — permission slip signed, thermos of tea, eyes on the dark.', vi: 'Đêm mưa sao băng. Ba đứa trên mái trường — giấy phép đã ký, bình trà, mắt hướng bóng tối.' }, nextScene: 'ms04-07' },
      { id: 'ms04-07', character: 'ha', dialogue: { en: '"It\'s actually... beautiful." Ha whispers. No irony this time.', vi: '"Đẹp thật..." Hà thì thầm. Lần này không mỉa mai.' }, nextScene: 'ms04-08' },
      { id: 'ms04-08', character: 'narrator', dialogue: { en: 'Identity isn\'t rebellion for its own sake. It\'s finding what makes you lean forward — and letting that be enough.', vi: 'Bản sắc không phải nổi loạn vì nổi loạn. Là tìm thứ khiến bạn nghiêng người về phía trước — và để nó đủ.' }, endStory: true },
    ],
  },

  // 5. Bàn Số Bảy — Được Chấp Nhận
  {
    id: 'ms-05',
    lifeStage: 'middle_school',
    category: 'social_acceptance',
    title: { en: 'Table Seven', vi: 'Bàn Số Bảy' },
    description: {
      en: 'New semester, new seating in the cafeteria. Your old lunch group saved seats — but not for you. Table seven has one empty chair.',
      vi: 'Học kỳ mới, xếp chỗ ăn trưa mới. Nhóm cũ giữ chỗ — nhưng không phải cho bạn. Bàn số bảy còn một ghế trống.',
    },
    xpReward: 95,
    totalScenes: 12,
    startScene: 'ms05-01',
    characters: [
      { id: 'tram', name: { en: 'Tram', vi: 'Trâm' }, color: '#c080a0', emoji: '👧' },
      { id: 'duc', name: { en: 'Duc', vi: 'Đức' }, color: '#5080a0', emoji: '👦' },
      { id: 'quynh', name: { en: 'Quynh', vi: 'Quỳnh' }, color: '#80a0c0', emoji: '👧' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      { id: 'ms05-01', character: 'narrator', dialogue: { en: 'First lunch of the semester. The cafeteria is loud — trays clattering, friends calling names.', vi: 'Bữa trưa đầu học kỳ. Căng tin ồn ào — khay chén kêu leng keng, bạn bè gọi tên nhau.' }, nextScene: 'ms05-02' },
      { id: 'ms05-02', character: 'narrator', dialogue: { en: 'Your old table — Tram, Duc, and two others — has bags on every chair. No space left. They see you. Look away.', vi: 'Bàn cũ — Trâm, Đức và hai người khác — mỗi ghế để túi. Không còn chỗ. Họ thấy bạn. Quay đi.' }, choices: [
        { id: 'ms05-c02a', text: { en: 'Ask: "Is there room?" anyway.', vi: 'Hỏi: "Còn chỗ không?" dù sao cũng hỏi.' }, tags: ['courage', 'assertiveness'], effects: { relationships: { tram: { trust: -5 } }, personality: { courage: 3, assertiveness: 3 } }, nextScene: 'ms05-03a' },
        { id: 'ms05-c02b', text: { en: 'Walk to table seven without a word.', vi: 'Đi thẳng tới bàn số bảy, không nói gì.' }, tags: ['resilience', 'ownership'], effects: { personality: { resilience: 4, ownership: 3 } }, nextScene: 'ms05-03b' },
        { id: 'ms05-c02c', text: { en: 'Eat in the bathroom stall. Alone.', vi: 'Ăn trong nhà vệ sinh. Một mình.' }, tags: ['avoidance', 'short_term_gain'], effects: { personality: { avoidance: 4, resilience: -4 } }, delayedConsequences: [{ triggerAfterScenes: 3, effects: { personality: { resilience: -3 } }, message: { en: 'Quynh saw you come out of the restroom with your lunch box. She didn\'t ask — but she noticed.', vi: 'Quỳnh thấy bạn ra từ nhà vệ sinh với hộp cơm. Cô ấy không hỏi — nhưng để ý.' } }], nextScene: 'ms05-03c' },
      ]},
      { id: 'ms05-03a', character: 'tram', dialogue: { en: '"We kind of... already arranged things." Tram won\'t meet your eyes. "Sorry."', vi: '"Tụi mình... sắp xếp rồi." Trâm không nhìn bạn. "Xin lỗi."' }, nextScene: 'ms05-04' },
      { id: 'ms05-03b', character: 'quynh', dialogue: { en: 'Table seven: Quynh, a boy from class 7B, and an empty chair. Quynh slides her tray over. "Sit."', vi: 'Bàn số bảy: Quỳnh, một bạn lớp 7B, và ghế trống. Quỳnh đẩy khay sang. "Ngồi đi."' }, nextScene: 'ms05-04' },
      { id: 'ms05-03c', character: 'narrator', dialogue: { en: 'The bathroom echo makes every bite taste like shame. You promise yourself tomorrow will be different.', vi: 'Tiếng vọng trong nhà vệ sinh khiến mỗi miếng cơm nguội lạnh. Bạn hứa ngày mai sẽ khác.' }, nextScene: 'ms05-04' },
      { id: 'ms05-04', character: 'duc', dialogue: { en: 'Duc finds you in the hallway. "It wasn\'t my idea. Tram said the group was getting too big."', vi: 'Đức tìm bạn ở hành lang. "Không phải ý mình. Trâm bảo nhóm đông quá."' }, choices: [
        { id: 'ms05-c04a', text: { en: '"You could have told me."', vi: '"Cậu có thể nói với mình trước."' }, tags: ['assertiveness', 'empathy'], effects: { relationships: { duc: { trust: 5, respect: 5 } }, personality: { assertiveness: 3 } }, nextScene: 'ms05-05' },
        { id: 'ms05-c04b', text: { en: '"It\'s fine. Whatever."', vi: '"Không sao. Tùy các cậu."' }, tags: ['avoid_conflict', 'avoidance'], effects: { relationships: { duc: { trust: -3 } }, personality: { avoidance: 2 } }, nextScene: 'ms05-05' },
        { id: 'ms05-c04c', text: { en: '"I found a better table anyway."', vi: '"Mình tìm được bàn hay hơn rồi."' }, tags: ['resilience', 'assertiveness'], effects: { personality: { resilience: 3, assertiveness: 2 } }, nextScene: 'ms05-05' },
      ]},
      { id: 'ms05-05', character: 'quynh', dialogue: { en: 'Day three at table seven. Quynh shares her fries without asking. "You don\'t have to be funny to sit here."', vi: 'Ngày thứ ba ở bàn bảy. Quỳnh chia khoai tây chiên không cần hỏi. "Cậu không cần hài hước mới được ngồi đây."' }, choices: [
        { id: 'ms05-c05a', text: { en: 'Laugh. "Good. I\'m terrible at jokes."', vi: 'Cười. "Tốt. Mình kể chuyện cười dở lắm."' }, tags: ['cooperation', 'empathy'], effects: { relationships: { quynh: { friendship: 12, trust: 10 } }, personality: { cooperation: 3, empathy: 2 } }, nextScene: 'ms05-06' },
        { id: 'ms05-c05b', text: { en: 'Wonder if you\'re only here because they pity you.', vi: 'Tự hỏi mình ở đây vì họ thương hại.' }, tags: ['avoidance', 'short_term_gain'], effects: { relationships: { quynh: { trust: -5 } }, personality: { avoidance: 2 } }, nextScene: 'ms05-06' },
      ]},
      { id: 'ms05-06', character: 'tram', dialogue: { en: 'Tram passes your new table. Pauses. "Can we talk? Lunch, sometime?"', vi: 'Trâm đi ngang bàn mới. Dừng lại. "Mình nói chuyện được không? Ăn trưa, lúc nào đó?"' }, choices: [
        { id: 'ms05-c06a', text: { en: '"I\'m okay where I am. But we can talk."', vi: '"Mình ổn chỗ này. Nhưng nói chuyện được."' }, tags: ['assertiveness', 'empathy'], effects: { relationships: { tram: { respect: 8 }, quynh: { trust: 5 } }, personality: { assertiveness: 4, empathy: 3 } }, nextScene: 'ms05-07' },
        { id: 'ms05-c06b', text: { en: 'Move back to the old table. Easier.', vi: 'Về bàn cũ. Dễ hơn.' }, tags: ['avoid_conflict', 'short_term_gain'], effects: { relationships: { quynh: { friendship: -8, trust: -10 } }, personality: { avoidance: 3 } }, nextScene: 'ms05-07' },
        { id: 'ms05-c06c', text: { en: 'Ignore her. She made her choice.', vi: 'Làm lơ. Cô ấy đã chọn rồi.' }, tags: ['assertiveness'], effects: { relationships: { tram: { friendship: -10 } }, personality: { assertiveness: 2 } }, nextScene: 'ms05-07' },
      ]},
      { id: 'ms05-07', character: 'quynh', dialogue: { en: '"Table seven was empty for months before you." Quynh shrugs. "We weren\'t waiting for anyone special. Just someone."', vi: '"Bàn bảy trống mấy tháng trước khi cậu đến." Quỳnh nhún vai. "Tụi mình không đợi ai đặc biệt. Chỉ cần một người."' }, nextScene: 'ms05-08' },
      { id: 'ms05-08', character: 'narrator', dialogue: { en: 'Belonging isn\'t always being chosen first. Sometimes it\'s choosing to sit down — and letting a new table become yours.', vi: 'Thuộc về đâu không phải lúc nào cũng được chọn trước. Đôi khi là chọn ngồi xuống — và để một bàn mới trở thành của mình.' }, endStory: true },
    ],
  },
];

STORIES.push(...MIDDLE_STORIES_3);
