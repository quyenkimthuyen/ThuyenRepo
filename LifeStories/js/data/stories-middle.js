const MIDDLE_STORIES = [
  {
    id: 'ms-01',
    lifeStage: 'middle_school',
    category: 'peer_pressure',
    title: { en: 'The Group Chat', vi: 'Nhóm Chat' },
    description: {
      en: 'A photo of Linh tripping in PE spreads in the class group chat. Your friends are waiting to see which emoji you send.',
      vi: 'Ảnh Linh vấp ngã trong giờ TD được chia sẻ trong nhóm chat lớp. Bạn bè đang chờ xem bạn gửi emoji gì.',
    },
    xpReward: 95,
    totalScenes: 12,
    startScene: 'ms01-01',
    characters: [
      { id: 'khanh', name: { en: 'Khanh', vi: 'Khánh' }, color: '#5080a0', emoji: '👦' },
      { id: 'linh', name: { en: 'Linh', vi: 'Linh' }, color: '#d090a0', emoji: '👧' },
      { id: 'vy', name: { en: 'Vy', vi: 'Vy' }, color: '#9060c0', emoji: '👧' },
      { id: 'teacher', name: { en: 'Mr. Duc', vi: 'Thầy Đức' }, color: '#6080b0', emoji: '👨‍🏫' },
      { id: 'narrator', name: { en: '...', vi: '...' }, color: '#888', emoji: '' },
    ],
    scenes: [
      { id: 'ms01-01', character: 'narrator', dialogue: { en: 'Your phone buzzes during dinner. The class group chat — 47 unread messages. Someone posted a photo.', vi: 'Điện thoại rung lúc ăn tối. Nhóm chat lớp — 47 tin chưa đọc. Có người đăng ảnh.' }, nextScene: 'ms01-02' },
      { id: 'ms01-02', character: 'narrator', dialogue: { en: 'Linh, mid-fall during PE. Face red, arms flailing. The caption: "Best moment of the year 😂😂"', vi: 'Linh, đang ngã giữa giờ TD. Mặt đỏ, tay vung vẩy. Chú thích: "Khoảnh khắc đẹp nhất năm 😂😂"' }, choices: [
        { id: 'ms01-c02a', text: { en: 'Send 😂 like everyone else.', vi: 'Gửi 😂 như mọi người.' }, tags: ['avoid_conflict', 'short_term_gain'], effects: { relationships: { linh: { trust: -15, friendship: -12 } }, personality: { integrity: -3 } }, delayedConsequences: [{ triggerAfterScenes: 4, effects: { relationships: { linh: { trust: -10 } } }, message: { en: 'Linh saw you laughed. She unfollowed you on every app.', vi: 'Linh thấy bạn cười. Cô ấy unfollow bạn trên mọi app.' } }], nextScene: 'ms01-03a' },
        { id: 'ms01-c02b', text: { en: 'Type: "Not cool. Take it down."', vi: 'Nhắn: "Không hay. Gỡ đi."' }, tags: ['courage', 'integrity'], effects: { relationships: { linh: { trust: 12, friendship: 8 }, vy: { trust: -5 } }, personality: { courage: 4, integrity: 3 } }, nextScene: 'ms01-03b' },
        { id: 'ms01-c02c', text: { en: 'Close the chat. Pretend you didn\'t see it.', vi: 'Tắt chat. Giả vờ không thấy.' }, tags: ['avoidance', 'avoid_conflict'], effects: { personality: { avoidance: 3 } }, delayedConsequences: [{ triggerAfterScenes: 3, effects: { relationships: { linh: { trust: -8 } } }, message: { en: 'Vy screenshot your "last seen" time. "You were online. You saw."', vi: 'Vy chụp màn hình "lần cuối online". "Cậu online mà. Cậu thấy rồi."' } }], nextScene: 'ms01-03a' },
      ]},
      { id: 'ms01-03a', character: 'khanh', dialogue: { en: '"Bro, why so serious? It\'s just a joke." Khanh sends another meme about Linh.', vi: '"Ông căng gì thế? Đùa thôi mà." Khánh gửi thêm meme về Linh.' }, nextScene: 'ms01-04' },
      { id: 'ms01-03b', character: 'vy', dialogue: { en: '"Wow. Defender of the year." Vy adds a thumbs-down emoji to your message.', vi: '"Wow. Nhà vô địch bênh vực đây." Vy thả emoji thumbs-down vào tin nhắn của bạn.' }, choices: [
        { id: 'ms01-c03a', text: { en: '"Would you want this photo of yourself online?"', vi: '"Cậu có muốn ảnh mình bị đăng thế này không?"' }, tags: ['empathy', 'assertiveness'], effects: { relationships: { vy: { respect: 5 }, linh: { trust: 8 } }, personality: { empathy: 3, assertiveness: 3 } }, nextScene: 'ms01-04' },
        { id: 'ms01-c03b', text: { en: 'Delete your message. Too much drama.', vi: 'Xóa tin nhắn. Phiền quá.' }, tags: ['avoid_conflict', 'short_term_gain'], effects: { relationships: { linh: { trust: -10 } }, personality: { integrity: -2, avoidance: 2 } }, nextScene: 'ms01-04' },
      ]},
      { id: 'ms01-04', character: 'narrator', dialogue: { en: 'Next morning. Linh walks into class with headphones on. She doesn\'t look at anyone.', vi: 'Sáng hôm sau. Linh bước vào lớp đeo tai nghe. Cô ấy không nhìn ai.' }, choices: [
        { id: 'ms01-c04a', text: { en: 'Sit next to her. Say nothing — just be there.', vi: 'Ngồi cạnh cô ấy. Không nói gì — chỉ ở đó.' }, tags: ['empathy', 'courage'], effects: { relationships: { linh: { friendship: 10, trust: 10 } }, personality: { empathy: 4 } }, nextScene: 'ms01-05' },
        { id: 'ms01-c04b', text: { en: 'Stay with Khanh and Vy. Safer.', vi: 'Ở với Khánh và Vy. An toàn hơn.' }, tags: ['avoid_conflict', 'short_term_gain'], effects: { relationships: { khanh: { friendship: 5 }, linh: { friendship: -5 } }, personality: { avoidance: 2 } }, nextScene: 'ms01-05' },
      ]},
      { id: 'ms01-05', character: 'teacher', dialogue: { en: 'Mr. Duc stops the class. "Someone shared a private moment without consent. That\'s not humor — that\'s harm."', vi: 'Thầy Đức dừng lớp. "Có người chia sẻ khoảnh khắc riêng tư mà không được phép. Đó không phải đùa — đó là làm tổn thương."' }, nextScene: 'ms01-06' },
      { id: 'ms01-06', character: 'linh', dialogue: { en: 'After class, Linh speaks quietly: "Thanks. Or sorry. I don\'t know which I should say."', vi: 'Sau giờ học, Linh nói nhỏ: "Cảm ơn. Hay xin lỗi. Mình không biết nên nói cái nào."' }, choices: [
        { id: 'ms01-c06a', text: { en: '"Both can be true. I\'m glad you\'re okay."', vi: '"Cả hai đều có thể đúng. Mình mừng vì cậu ổn."' }, tags: ['empathy', 'cooperation'], effects: { relationships: { linh: { friendship: 15, trust: 12 } }, personality: { empathy: 4 } }, nextScene: 'ms01-07' },
        { id: 'ms01-c06b', text: { en: '"I laughed too, at first. I\'m sorry."', vi: '"Lúc đầu mình cũng cười. Xin lỗi."' }, tags: ['integrity', 'courage'], effects: { relationships: { linh: { trust: 15, respect: 10 } }, personality: { integrity: 4, courage: 3 } }, nextScene: 'ms01-07' },
      ]},
      { id: 'ms01-07', character: 'khanh', dialogue: { en: 'Khanh finds you at recess. "You made us look bad." He\'s not smiling.', vi: 'Khánh tìm bạn ra chơi. "Cậu làm bọn tớ xấu mặt." Cậu ấy không cười.' }, choices: [
        { id: 'ms01-c07a', text: { en: '"Then maybe we were doing something bad."', vi: '"Vậy có lẽ bọn mình đang làm điều không hay."' }, tags: ['assertiveness', 'integrity'], effects: { relationships: { khanh: { respect: 5, friendship: -5 } }, personality: { assertiveness: 4 } }, nextScene: 'ms01-08' },
        { id: 'ms01-c07b', text: { en: '"I didn\'t mean to hurt anyone."', vi: '"Mình không cố làm ai tổn thương."' }, tags: ['empathy'], effects: { relationships: { khanh: { trust: 3 } }, personality: { empathy: 2 } }, nextScene: 'ms01-08' },
      ]},
      { id: 'ms01-08', character: 'narrator', dialogue: { en: 'The photo gets deleted. But the chat history remains. And so does the memory of which side you chose.', vi: 'Ảnh bị gỡ. Nhưng lịch sử chat vẫn còn. Và ký ức về phía bạn đã chọn cũng vậy.' }, nextScene: 'ms01-09' },
      { id: 'ms01-09', character: 'narrator', dialogue: { en: 'Peer pressure doesn\'t always shout. Sometimes it\'s just an emoji, waiting for you to press send.', vi: 'Áp lực đồng trang lứa không lúc nào cũng la hét. Đôi khi chỉ là một emoji, chờ bạn bấm gửi.' }, endStory: true },
    ],
  },
];

STORIES.push(...MIDDLE_STORIES);
