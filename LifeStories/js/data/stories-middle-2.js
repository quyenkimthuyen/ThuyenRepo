const MIDDLE_STORIES_2 = [
  // 2. Con Số — Lòng Tự Trọng
  {
    id: 'ms-02',
    lifeStage: 'middle_school',
    category: 'self_esteem',
    title: { en: 'The Numbers', vi: 'Con Số' },
    description: {
      en: 'Midterm rankings are posted. You dropped twelve places. Your cousin posts her top-3 certificate online. Mom sighs at dinner.',
      vi: 'Bảng xếp hạng giữa kỳ dán lên. Bạn tụt mười hai bậc. Chị họ đăng ảnh giấy khen top 3 lên mạng. Mẹ thở dài trong bữa tối.',
    },
    xpReward: 95,
    totalScenes: 12,
    startScene: 'ms02-01',
    characters: [
      { id: 'mom', name: { en: 'Mom', vi: 'Mẹ' }, color: '#c09070', emoji: '👩' },
      { id: 'thao', name: { en: 'Ms. Thao', vi: 'Cô Thảo' }, color: '#9060c0', emoji: '👩‍🏫' },
      { id: 'phuc', name: { en: 'Phuc', vi: 'Phúc' }, color: '#60a080', emoji: '👦' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      { id: 'ms02-01', character: 'narrator', dialogue: { en: 'The ranking list is on the bulletin board. Names and numbers in neat columns. You scan for yours.', vi: 'Bảng xếp hạng dán trên bảng tin. Tên và con số xếp thẳng hàng. Bạn dò tìm tên mình.' }, nextScene: 'ms02-02' },
      { id: 'ms02-02', character: 'narrator', dialogue: { en: 'Last time: 14th. This time: 26th. The number sits in your stomach like a stone.', vi: 'Lần trước: thứ 14. Lần này: thứ 26. Con số nằm trong bụng nặng như hòn đá.' }, choices: [
        { id: 'ms02-c02a', text: { en: 'Rip the corner of the list where your name is.', vi: 'Xé góc bảng chỗ tên mình.' }, tags: ['avoidance', 'short_term_gain'], effects: { personality: { resilience: -2, integrity: -2 } }, delayedConsequences: [{ triggerAfterScenes: 3, effects: { relationships: { thao: { trust: -10 } } }, message: { en: 'Ms. Thao noticed the torn list. She didn\'t yell — which was worse.', vi: 'Cô Thảo thấy bảng bị xé. Cô không la — mà còn tệ hơn.' } }], nextScene: 'ms02-03a' },
        { id: 'ms02-c02b', text: { en: 'Take a photo. Study which subjects dropped.', vi: 'Chụp ảnh. Xem môn nào tụt điểm.' }, tags: ['responsibility', 'curiosity'], effects: { personality: { responsibility: 3, curiosity: 3 } }, nextScene: 'ms02-03b' },
        { id: 'ms02-c02c', text: { en: 'Walk away fast before anyone sees your face.', vi: 'Bỏ đi nhanh trước khi ai thấy mặt mình.' }, tags: ['avoidance'], effects: { personality: { avoidance: 3, resilience: -2 } }, nextScene: 'ms02-03a' },
      ]},
      { id: 'ms02-03a', character: 'phuc', dialogue: { en: '"Hey. You okay?" Phuc didn\'t check the list. He never does.', vi: '"Này. Ổn không?" Phúc không xem bảng. Cậu ấy chưa bao giờ xem.' }, nextScene: 'ms02-04' },
      { id: 'ms02-03b', character: 'phuc', dialogue: { en: '"Math and Literature — same as me. We can study together." Phuc shows his phone calendar.', vi: '"Toán với Văn — giống mình. Mình học cùng nhé." Phúc đưa lịch trên điện thoại.' }, choices: [
        { id: 'ms02-c03a', text: { en: '"Yeah. I don\'t want to do this alone."', vi: '"Ừ. Mình không muốn một mình."' }, tags: ['cooperation', 'resilience'], effects: { relationships: { phuc: { friendship: 12, trust: 10 } }, personality: { cooperation: 3, resilience: 3 } }, nextScene: 'ms02-04' },
        { id: 'ms02-c03b', text: { en: '"You\'re ranked higher. You\'ll think I\'m slow."', vi: '"Cậu xếp hạng cao hơn. Sẽ nghĩ mình kém."' }, tags: ['avoidance', 'short_term_gain'], effects: { relationships: { phuc: { trust: -5 } }, personality: { avoidance: 2 } }, nextScene: 'ms02-04' },
      ]},
      { id: 'ms02-04', character: 'mom', dialogue: { en: 'Dinner. Mom puts down her phone — your cousin\'s certificate post still on screen. "When I was your age..."', vi: 'Bữa tối. Mẹ đặt điện thoại xuống — màn hình vẫn hiện ảnh giấy khen chị họ. "Hồi bằng tuổi con..."' }, choices: [
        { id: 'ms02-c04a', text: { en: '"I know I dropped. I\'m already working on it."', vi: '"Con biết mình tụt rồi. Con đang cố sửa."' }, tags: ['assertiveness', 'responsibility'], effects: { relationships: { mom: { respect: 8, trust: 5 } }, personality: { assertiveness: 3, responsibility: 3 } }, nextScene: 'ms02-05' },
        { id: 'ms02-c04b', text: { en: 'Stay silent. Push rice around your bowl.', vi: 'Im lặng. Khuấy cơm trong bát.' }, tags: ['avoid_conflict', 'avoidance'], effects: { relationships: { mom: { trust: -5 } }, personality: { avoidance: 3 } }, delayedConsequences: [{ triggerAfterScenes: 2, effects: { relationships: { mom: { trust: -8 } } }, message: { en: 'Mom stopped asking about school. The silence felt worse than shouting.', vi: 'Mẹ không hỏi chuyện học nữa. Im lặng còn tệ hơn la mắng.' } }], nextScene: 'ms02-05' },
        { id: 'ms02-c04c', text: { en: '"Comparison never helped anyone, Mom."', vi: '"So sánh chẳng giúp được ai, mẹ."' }, tags: ['assertiveness', 'courage'], effects: { relationships: { mom: { respect: 5, trust: -3 } }, personality: { assertiveness: 4, courage: 3 } }, nextScene: 'ms02-05' },
      ]},
      { id: 'ms02-05', character: 'thao', dialogue: { en: 'Ms. Thao calls you after class. "Your writing improved. The ranking doesn\'t show that — yet."', vi: 'Cô Thảo gọi bạn sau giờ học. "Bài văn con tiến bộ. Bảng xếp hạng chưa phản ánh điều đó — chưa."' }, choices: [
        { id: 'ms02-c05a', text: { en: '"What if it never does?"', vi: '"Nếu không bao giờ thì sao ạ?"' }, tags: ['curiosity', 'honesty'], effects: { relationships: { thao: { trust: 8 } }, personality: { curiosity: 2 } }, nextScene: 'ms02-06' },
        { id: 'ms02-c05b', text: { en: '"Thank you, Ms. Thao. That means a lot."', vi: '"Cảm ơn cô. Điều đó quan trọng với em."' }, tags: ['empathy', 'resilience'], effects: { relationships: { thao: { trust: 10, respect: 8 } }, personality: { resilience: 3, empathy: 2 } }, nextScene: 'ms02-06' },
      ]},
      { id: 'ms02-06', character: 'narrator', dialogue: { en: 'Three weeks of studying with Phuc. You still check rankings — but less often.', vi: 'Ba tuần học cùng Phúc. Bạn vẫn xem bảng xếp hạng — nhưng ít hơn.' }, nextScene: 'ms02-07' },
      { id: 'ms02-07', character: 'narrator', dialogue: { en: 'Final midterm update: 19th. Not 14th. Not 26th. Something in between — and something shifting inside you.', vi: 'Cập nhật giữa kỳ: thứ 19. Không phải 14. Không phải 26. Ở giữa — và có gì đó thay đổi bên trong bạn.' }, choices: [
        { id: 'ms02-c07a', text: { en: 'Text Phuc: "Thanks for sticking around."', vi: 'Nhắn Phúc: "Cảm ơn vì vẫn ở đây."' }, tags: ['empathy', 'cooperation'], effects: { relationships: { phuc: { friendship: 10 } }, personality: { empathy: 3 } }, nextScene: 'ms02-08' },
        { id: 'ms02-c07b', text: { en: 'Feel relieved — but wonder why you needed a number to feel okay.', vi: 'Nhẹ nhõm — nhưng tự hỏi sao cần con số mới thấy ổn.' }, tags: ['curiosity', 'responsibility'], effects: { personality: { curiosity: 4, responsibility: 2 } }, nextScene: 'ms02-08' },
      ]},
      { id: 'ms02-08', character: 'mom', dialogue: { en: 'Mom notices without mentioning rankings. "You seem lighter lately." She almost smiles.', vi: 'Mẹ để ý mà không nhắc xếp hạng. "Dạo này con có vẻ nhẹ hơn." Mẹ gần như mỉm cười.' }, nextScene: 'ms02-09' },
      { id: 'ms02-09', character: 'narrator', dialogue: { en: 'Self-esteem isn\'t a rank on a wall. But learning that — while the numbers still exist — is its own kind of growth.', vi: 'Lòng tự trọng không phải thứ hạng trên tường. Nhưng học được điều đó — khi con số vẫn còn đó — là một kiểu trưởng thành riêng.' }, endStory: true },
    ],
  },

  // 3. Góc Cầu Thang — Bắt Nạt
  {
    id: 'ms-03',
    lifeStage: 'middle_school',
    category: 'bullying',
    title: { en: 'The Stairwell', vi: 'Góc Cầu Thang' },
    description: {
      en: 'Between periods, you see three older students cornering Bao by the stairwell. They\'re "just joking." Nobody else is watching.',
      vi: 'Giữa hai tiết học, bạn thấy ba học sinh lớn chặn Bảo ở góc cầu thang. Họ bảo "đùa thôi." Không ai khác nhìn thấy.',
    },
    xpReward: 100,
    totalScenes: 13,
    startScene: 'ms03-01',
    characters: [
      { id: 'bao', name: { en: 'Bao', vi: 'Bảo' }, color: '#8090a0', emoji: '👦' },
      { id: 'tung', name: { en: 'Tung', vi: 'Tùng' }, color: '#806040', emoji: '👦' },
      { id: 'guard', name: { en: 'Security Uncle Hai', vi: 'Bác Hải Bảo Vệ' }, color: '#607080', emoji: '👨' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      { id: 'ms03-01', character: 'narrator', dialogue: { en: 'The stairwell smells like floor cleaner. Voices bounce off concrete walls.', vi: 'Cầu thang có mùi nước lau sàn. Tiếng nói dội trên tường bê tông.' }, nextScene: 'ms03-02' },
      { id: 'ms03-02', character: 'narrator', dialogue: { en: 'Bao — small, always quiet — is pressed against the railing. Tung and two others block the way down.', vi: 'Bảo — nhỏ con, luôn ít nói — bị ép vào lan can. Tùng và hai người khác chặn lối xuống.' }, choices: [
        { id: 'ms03-c02a', text: { en: 'Walk past quickly. Not your problem.', vi: 'Đi qua nhanh. Không phải việc mình.' }, tags: ['avoidance', 'short_term_gain'], effects: { relationships: { bao: { trust: -15, friendship: -10 } }, personality: { integrity: -3, avoidance: 3 } }, delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { bao: { trust: -10 } } }, message: { en: 'Bao saw you look. He remembers who walked away.', vi: 'Bảo thấy bạn nhìn. Cậu ấy nhớ ai đã bỏ đi.' } }], nextScene: 'ms03-03a' },
        { id: 'ms03-c02b', text: { en: '"Hey! Bell\'s about to ring. Bao, c\'mon."', vi: '"Này! Sắp trống rồi. Bảo, đi thôi."' }, tags: ['courage', 'cooperation'], effects: { relationships: { bao: { trust: 12, friendship: 10 } }, personality: { courage: 4 } }, nextScene: 'ms03-03b' },
        { id: 'ms03-c02c', text: { en: 'Find Uncle Hai at the gate.', vi: 'Tìm bác Hải bảo vệ.' }, tags: ['responsibility', 'courage'], effects: { personality: { responsibility: 4, courage: 3 } }, delayedConsequences: [{ triggerAfterScenes: 2, effects: { relationships: { bao: { trust: 8 } } }, message: { en: 'Uncle Hai arrived before it escalated. Bao nodded at you once.', vi: 'Bác Hải đến trước khi leo thang. Bảo gật đầu với bạn một cái.' } }], nextScene: 'ms03-03c' },
      ]},
      { id: 'ms03-03a', character: 'tung', dialogue: { en: 'Tung laughs as you pass. "Good kid. Knows when to mind his business."', vi: 'Tùng cười khi bạn đi qua. "Ngoan. Biết chuyện không liên quan."' }, nextScene: 'ms03-04' },
      { id: 'ms03-03b', character: 'tung', dialogue: { en: '"What\'s it to you?" Tung steps closer. He\'s taller. But the hallway isn\'t completely empty.', vi: '"Mày làm gì?" Tùng bước lại gần. Cao hơn. Nhưng hành lang không hoàn toàn vắng.' }, choices: [
        { id: 'ms03-c03a', text: { en: 'Stand your ground. "Leave him alone."', vi: 'Đứng vững. "Để cậu ấy yên."' }, tags: ['assertiveness', 'courage'], effects: { relationships: { bao: { trust: 15 }, tung: { respect: -5 } }, personality: { assertiveness: 4, courage: 4 } }, nextScene: 'ms03-04' },
        { id: 'ms03-c03b', text: { en: 'Step back. You\'re not sure you can handle this.', vi: 'Lùi lại. Không chắc mình xử lý được.' }, tags: ['avoidance'], effects: { relationships: { bao: { trust: -5 } }, personality: { avoidance: 3 } }, nextScene: 'ms03-04' },
      ]},
      { id: 'ms03-03c', character: 'guard', dialogue: { en: 'Uncle Hai walks up the stairs. Tung\'s group disperses like smoke.', vi: 'Bác Hải lên cầu thang. Nhóm Tùng tan như khói.' }, nextScene: 'ms03-04' },
      { id: 'ms03-04', character: 'bao', dialogue: { en: 'Later, Bao finds you. "They take my lunch money on Mondays." He says it like a weather report.', vi: 'Sau đó, Bảo tìm bạn. "Thứ Hai họ lấy tiền ăn trưa của mình." Cậu ấy nói như đọc dự báo thời tiết.' }, choices: [
        { id: 'ms03-c04a', text: { en: '"We should tell someone. Together."', vi: '"Mình nên nói với người lớn. Cùng nhau."' }, tags: ['cooperation', 'responsibility'], effects: { relationships: { bao: { trust: 15, friendship: 12 } }, personality: { cooperation: 4, responsibility: 4 } }, nextScene: 'ms03-05' },
        { id: 'ms03-c04b', text: { en: '"Why didn\'t you say anything before?"', vi: '"Sao trước giờ cậu không nói?"' }, tags: ['curiosity'], effects: { relationships: { bao: { trust: -5 } }, personality: { empathy: -1 } }, nextScene: 'ms03-05' },
        { id: 'ms03-c04c', text: { en: '"I\'ll walk with you on Mondays."', vi: '"Thứ Hai mình đi cùng cậu."' }, tags: ['empathy', 'courage'], effects: { relationships: { bao: { friendship: 15, trust: 12 } }, personality: { empathy: 4, courage: 3 } }, nextScene: 'ms03-05' },
      ]},
      { id: 'ms03-05', character: 'narrator', dialogue: { en: 'Monday comes. The stairwell is empty. Tung isn\'t there. But the fear was real — and so is what you choose next.', vi: 'Thứ Hai đến. Cầu thang vắng. Tùng không có. Nhưng nỗi sợ là thật — và lựa chọn tiếp theo cũng vậy.' }, nextScene: 'ms03-06' },
      { id: 'ms03-06', character: 'guard', dialogue: { en: 'Uncle Hai mentions more patrols. "Kids think \'just joking\' means no damage. They\'re wrong."', vi: 'Bác Hải nói sẽ tuần tra thêm. "Học trò tưởng \'đùa thôi\' là không ai hại. Họ sai."' }, choices: [
        { id: 'ms03-c06a', text: { en: 'Share what you saw — without naming Bao if he\'s not ready.', vi: 'Kể những gì mình thấy — không nêu tên Bảo nếu cậu ấy chưa sẵn sàng.' }, tags: ['integrity', 'empathy'], effects: { personality: { integrity: 3, empathy: 3 } }, nextScene: 'ms03-07' },
        { id: 'ms03-c06b', text: { en: 'Let Bao decide when to speak.', vi: 'Để Bảo quyết định khi nào nói.' }, tags: ['empathy', 'respect'], effects: { relationships: { bao: { trust: 10 } }, personality: { empathy: 4 } }, nextScene: 'ms03-07' },
      ]},
      { id: 'ms03-07', character: 'bao', dialogue: { en: '"I thought nobody saw." Bao\'s voice cracks slightly. "But you did."', vi: '"Mình tưởng không ai thấy." Giọng Bảo hơi run. "Nhưng cậu thấy."' }, nextScene: 'ms03-08' },
      { id: 'ms03-08', character: 'narrator', dialogue: { en: 'Bullying doesn\'t always leave bruises. Sometimes it leaves a stairwell — and the memory of who walked past, and who stopped.', vi: 'Bắt nạt không lúc nào cũng để lại vết bầm. Đôi khi chỉ còn góc cầu thang — và ký ức ai đi qua, ai dừng lại.' }, endStory: true },
    ],
  },
];

STORIES.push(...MIDDLE_STORIES_2);
