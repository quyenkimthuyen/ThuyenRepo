/** @type {{ id: string, label: string }[]} */
export const LEVELS = [
  { id: 'a1', label: 'A1 — Sơ cấp' },
  { id: 'a2', label: 'A2 — Cơ bản' },
  { id: 'b1', label: 'B1 — Trung cấp' },
  { id: 'b2', label: 'B2 — Khá' },
  { id: 'c1', label: 'C1 — Nâng cao' },
];

/** @type {{ id: string, label: string }[]} */
export const TOPICS = [
  { id: 'daily', label: 'Đời sống' },
  { id: 'travel', label: 'Du lịch' },
  { id: 'work', label: 'Công việc' },
  { id: 'study', label: 'Học tập' },
  { id: 'ielts', label: 'IELTS Speaking' },
  { id: 'health', label: 'Sức khỏe' },
  { id: 'tech', label: 'Công nghệ' },
  { id: 'society', label: 'Xã hội' },
  { id: 'custom', label: 'Của tôi' },
];

/** @typedef {{ id: string, level: string, topic: string, title: string, sentences: string[], translations?: string[], custom?: boolean }} Lesson */

/** @type {Lesson[]} */
export const LESSONS = [
  // ── A1 · Đời sống ───────────────────────────────────
  {
    id: 'a1-greetings',
    level: 'a1',
    topic: 'daily',
    title: 'Greetings',
    sentences: [
      'Hello.',
      'Hi, how are you?',
      'I am fine, thank you.',
      'Nice to meet you.',
      'Goodbye, see you tomorrow.',
    ],
  },
  {
    id: 'a1-my-family',
    level: 'a1',
    topic: 'daily',
    title: 'My family',
    sentences: [
      'This is my mother.',
      'This is my father.',
      'I have one brother and one sister.',
      'We live in a small house.',
      'I love my family very much.',
    ],
  },
  {
    id: 'a1-at-home',
    level: 'a1',
    topic: 'daily',
    title: 'At home',
    sentences: [
      'I am at home now.',
      'The cat is on the chair.',
      'The book is on the table.',
      'I drink water every day.',
      'It is cold today.',
    ],
  },
  {
    id: 'morning-routine',
    level: 'a1',
    topic: 'daily',
    title: 'Morning routine',
    sentences: [
      "I wake up at six o'clock.",
      'I wash my face.',
      'I eat bread and drink milk.',
      'I go to school at seven.',
    ],
  },
  {
    id: 'a1-food',
    level: 'a1',
    topic: 'daily',
    title: 'Food I like',
    sentences: [
      'I like rice and chicken.',
      'She likes fruit and vegetables.',
      'We do not like coffee.',
      'They eat lunch at twelve.',
      'The food is very good.',
    ],
  },

  // ── A1 · Học tập ───────────────────────────────────
  {
    id: 'a1-colors-numbers',
    level: 'a1',
    topic: 'study',
    title: 'Colors and numbers',
    sentences: [
      'The sky is blue.',
      'The sun is yellow.',
      'I have three red apples.',
      'There are ten students in the class.',
      'My favourite color is green.',
    ],
  },

  // ── A2 · Đời sống ───────────────────────────────────
  {
    id: 'a2-daily-routine',
    level: 'a2',
    topic: 'daily',
    title: 'A busy day',
    sentences: [
      'I usually get up at half past six.',
      'After breakfast, I take the bus to work.',
      'I start work at nine in the morning.',
      'In the evening, I cook dinner and watch TV.',
      'I go to bed at about eleven.',
    ],
  },
  {
    id: 'a2-weekend',
    level: 'a2',
    topic: 'daily',
    title: 'Weekend plans',
    sentences: [
      'On Saturday morning, I usually clean my room.',
      'In the afternoon, I meet my friends at the park.',
      'We sometimes play football or ride bicycles.',
      'On Sunday evening, I prepare for the new week.',
    ],
  },
  {
    id: 'a2-shopping',
    level: 'a2',
    topic: 'daily',
    title: 'At the shop',
    sentences: [
      'I need to buy some bread and milk.',
      'How much does this shirt cost?',
      'It is too expensive for me.',
      'Do you have a cheaper one?',
      'I will pay by card, please.',
    ],
  },
  {
    id: 'a2-weather',
    level: 'a2',
    topic: 'daily',
    title: 'The weather',
    sentences: [
      'It is sunny and warm today.',
      'Yesterday it rained all afternoon.',
      'In winter it is often cold and windy.',
      'I always carry an umbrella in autumn.',
      'The weather forecast says it will be hot tomorrow.',
    ],
  },

  // ── A2 · IELTS ──────────────────────────────────────
  {
    id: 'a2-self-intro',
    level: 'a2',
    topic: 'ielts',
    title: 'IELTS Part 1 — Introduce yourself',
    sentences: [
      'Hello, my name is Anna.',
      'I am twenty years old.',
      'I live in Hanoi with my parents.',
      'I like reading books and listening to music.',
      'I want to learn English well.',
    ],
  },
  {
    id: 'a2-ielts-daily-habits',
    level: 'a2',
    topic: 'ielts',
    title: 'IELTS Part 1 — Daily habits',
    sentences: [
      "I usually wake up at seven o'clock.",
      'I have coffee and toast for breakfast.',
      'I check my phone before I leave the house.',
      'In the evening I like to relax and watch TV.',
      'I try to go to bed before midnight.',
    ],
  },

  // ── A2 · Du lịch ────────────────────────────────────
  {
    id: 'a2-travel',
    level: 'a2',
    topic: 'travel',
    title: 'A short trip',
    sentences: [
      'Last summer we visited Da Nang.',
      'We stayed in a hotel near the beach.',
      'Every morning we swam in the sea.',
      'The food was delicious and the people were friendly.',
      'I took many photos of the beautiful sunset.',
    ],
  },
  {
    id: 'a2-travel-hotel',
    level: 'a2',
    topic: 'travel',
    title: 'Checking into a hotel',
    sentences: [
      'I have a reservation under the name Nguyen.',
      'I would like a room with a view, please.',
      'What time is breakfast served?',
      'Could you call a taxi for me tomorrow morning?',
      'Here is my passport and credit card.',
    ],
  },
  {
    id: 'a2-travel-directions',
    level: 'a2',
    topic: 'travel',
    title: 'Asking for directions',
    sentences: [
      'Excuse me, where is the nearest train station?',
      'Is it far from here?',
      'Should I turn left or right at the traffic lights?',
      'How long does it take to walk there?',
      'Thank you very much for your help.',
    ],
  },

  // ── A2 · Công việc ──────────────────────────────────
  {
    id: 'a2-work-office',
    level: 'a2',
    topic: 'work',
    title: 'First day at the office',
    sentences: [
      'Good morning, I am the new intern.',
      'Nice to meet you all.',
      'Where should I put my bag?',
      'Could you show me how to use the printer?',
      'I look forward to working with the team.',
    ],
  },
  {
    id: 'a2-work-phone',
    level: 'a2',
    topic: 'work',
    title: 'A phone call at work',
    sentences: [
      'Good afternoon, ABC Company, how can I help you?',
      'One moment, please. I will transfer your call.',
      'I am afraid she is in a meeting right now.',
      'Can I take a message?',
      'I will ask her to call you back this afternoon.',
    ],
  },

  // ── B1 · IELTS ──────────────────────────────────────
  {
    id: 'b1-ielts-hometown',
    level: 'b1',
    topic: 'ielts',
    title: 'IELTS Part 1 — Hometown',
    sentences: [
      'I come from a medium-sized city in the north of Vietnam.',
      'It is famous for its old quarter and delicious street food.',
      'The pace of life there is quite relaxed compared to the capital.',
      'Young people often move to bigger cities for better job opportunities.',
      'I still visit my hometown several times a year to see my relatives.',
    ],
  },
  {
    id: 'b1-ielts-free-time',
    level: 'b1',
    topic: 'ielts',
    title: 'IELTS Part 1 — Free time',
    sentences: [
      'In my spare time I enjoy cooking and trying new recipes.',
      'I usually do this on weekends when I am less busy.',
      'I started cooking seriously about three years ago.',
      'It helps me unwind after a stressful week at work.',
      'I would like to take a professional cooking course one day.',
    ],
  },
  {
    id: 'b1-ielts-work-study',
    level: 'b1',
    topic: 'ielts',
    title: 'IELTS Part 1 — Work or study',
    sentences: [
      'I am currently working as a marketing assistant for a tech company.',
      'I have been in this role for almost two years now.',
      'The most challenging part is managing tight deadlines.',
      'I chose this field because I enjoy creative problem solving.',
      'In the future I hope to lead my own marketing team.',
    ],
  },

  // ── B1 · Du lịch ────────────────────────────────────
  {
    id: 'b1-travel-backpacking',
    level: 'b1',
    topic: 'travel',
    title: 'Backpacking abroad',
    sentences: [
      'Travelling with just a backpack gives you a wonderful sense of freedom.',
      'You can change your plans at the last minute without much hassle.',
      'Staying in hostels is a great way to meet other travellers.',
      'However, you need to keep your valuables safe at all times.',
      'I always research local customs before visiting a new country.',
    ],
  },
  {
    id: 'b1-travel-food',
    level: 'b1',
    topic: 'travel',
    title: 'Food and travel',
    sentences: [
      'One of the best parts of travelling is tasting local dishes.',
      'I often ask locals to recommend restaurants off the tourist trail.',
      'Street food can be amazing, but you should choose busy stalls.',
      'I try to learn a few food-related words in the local language.',
      'Sharing a meal is one of the fastest ways to connect with people.',
    ],
  },

  // ── B1 · Công việc ──────────────────────────────────
  {
    id: 'b1-remote-work',
    level: 'b1',
    topic: 'work',
    title: 'Working from home',
    sentences: [
      'More and more people now work from home at least part of the week.',
      'Working remotely saves commuting time but requires good self-discipline.',
      'It is important to create a quiet space where you can concentrate.',
      'Video calls have become a normal part of office communication.',
      'Some workers miss the social atmosphere of a shared workplace.',
    ],
  },
  {
    id: 'b1-first-job',
    level: 'b1',
    topic: 'work',
    title: 'My first job',
    sentences: [
      'When I finished university, I was nervous about finding my first job.',
      'I sent dozens of applications before I received a single interview.',
      'The interview was stressful, but the manager was friendly and professional.',
      'On my first day, a colleague showed me around the office and introduced the team.',
      'Although the work was challenging, I learned a great deal in those first months.',
    ],
  },
  {
    id: 'b1-work-interview',
    level: 'b1',
    topic: 'work',
    title: 'Job interview answers',
    sentences: [
      'I believe my strongest skill is communicating clearly under pressure.',
      'In my previous role I managed a project that finished ahead of schedule.',
      'I am comfortable working both independently and as part of a team.',
      'I am eager to develop new skills and take on more responsibility.',
      'This position appeals to me because it aligns with my long-term career goals.',
    ],
  },

  // ── B1 · Học tập ────────────────────────────────────
  {
    id: 'b1-learning-english',
    level: 'b1',
    topic: 'study',
    title: 'Learning English',
    sentences: [
      'Learning a new language takes time and patience.',
      'The best way to improve your speaking is to practise every day.',
      'Do not be afraid of making mistakes when you talk.',
      'Watching films with subtitles can help you learn new words.',
      'Reading aloud is a simple but effective exercise.',
    ],
  },

  // ── B1 · Sức khỏe ───────────────────────────────────
  {
    id: 'b1-healthy-habits',
    level: 'b1',
    topic: 'health',
    title: 'Healthy habits',
    sentences: [
      'Eating a balanced diet helps you stay healthy.',
      'Doctors recommend at least thirty minutes of exercise every day.',
      'Getting enough sleep is just as important as eating well.',
      'Many people drink too much sugary soda and not enough water.',
      'Small changes in your daily routine can make a big difference.',
    ],
  },

  // ── B1 · Xã hội ─────────────────────────────────────
  {
    id: 'b1-environment',
    level: 'b1',
    topic: 'society',
    title: 'Protecting the environment',
    sentences: [
      'Plastic waste is a serious problem for oceans and wildlife.',
      'Recycling paper, glass, and metal reduces the amount of rubbish we produce.',
      'Using public transport or a bicycle can lower air pollution in cities.',
      'Governments and individuals must work together to fight climate change.',
      'Even small actions, like turning off unused lights, can help the planet.',
    ],
  },
  {
    id: 'b1-social-media',
    level: 'b1',
    topic: 'society',
    title: 'Social media',
    sentences: [
      'Social media connects people across the world in seconds.',
      'However, spending too much time online can affect your mental health.',
      'Many teenagers feel pressure to look perfect in every photo they post.',
      'It is wise to think carefully before sharing personal information online.',
      'A digital detox once in a while can help you feel more relaxed.',
    ],
  },

  // ── B2 · IELTS ──────────────────────────────────────
  {
    id: 'b2-ielts-describe-place',
    level: 'b2',
    topic: 'ielts',
    title: 'IELTS Part 2 — Describe a memorable place',
    sentences: [
      'I would like to talk about a coastal town I visited last year.',
      'I went there with two close friends during the autumn break.',
      'The town is known for its dramatic cliffs and crystal-clear water.',
      'We spent our days hiking along the coast and eating fresh seafood.',
      'What made it special was how peaceful and unspoiled everything felt.',
      'I would definitely recommend it to anyone who needs to escape city life.',
    ],
  },
  {
    id: 'b2-ielts-technology',
    level: 'b2',
    topic: 'ielts',
    title: 'IELTS Part 3 — Technology in education',
    sentences: [
      'Technology has fundamentally changed the way students access information.',
      'Online platforms allow learners to study at their own pace from anywhere.',
      'Nevertheless, excessive screen time may reduce face-to-face interaction among students.',
      'Teachers must learn to integrate digital tools without replacing critical thinking.',
      'In my view, the most effective classrooms combine technology with human guidance.',
    ],
  },
  {
    id: 'b2-ielts-environment',
    level: 'b2',
    topic: 'ielts',
    title: 'IELTS Part 3 — Environmental responsibility',
    sentences: [
      'Individuals alone cannot solve environmental problems of this scale.',
      'Governments need to enforce regulations on pollution and deforestation.',
      'Corporations should be held accountable for the waste they generate.',
      'Consumer choices, however small, send powerful signals to the market.',
      'Education plays a crucial role in shaping environmentally conscious citizens.',
    ],
  },

  // ── B2 · Du lịch ────────────────────────────────────
  {
    id: 'b2-travel-sustainable',
    level: 'b2',
    topic: 'travel',
    title: 'Sustainable tourism',
    sentences: [
      'Mass tourism can damage fragile ecosystems and displace local communities.',
      'Responsible travellers should respect cultural norms and support local businesses.',
      'Choosing direct flights less often and staying longer in one place can reduce emissions.',
      'Some destinations have introduced visitor caps to protect natural heritage sites.',
      'The travel industry is gradually shifting towards more sustainable practices.',
    ],
  },
  {
    id: 'b2-cultural-differences',
    level: 'b2',
    topic: 'travel',
    title: 'Cultural differences',
    sentences: [
      'When living abroad, you quickly discover that customs vary widely from country to country.',
      'What is considered polite in one culture may be seen as rude in another.',
      'Gestures, eye contact, and personal space all carry different meanings across cultures.',
      'Adapting to a new environment requires openness, humility, and a willingness to learn.',
      'Cultural exchange enriches our understanding of humanity and broadens our perspective.',
    ],
  },

  // ── B2 · Công việc ──────────────────────────────────
  {
    id: 'b2-work-leadership',
    level: 'b2',
    topic: 'work',
    title: 'Leadership at work',
    sentences: [
      'Effective leaders listen more than they speak and empower their teams.',
      'They set a clear vision but remain flexible when circumstances change.',
      'Trust is built through consistency, transparency, and genuine recognition.',
      'Micromanaging rarely improves performance and often damages morale.',
      'The best managers invest in developing the people who work for them.',
    ],
  },
  {
    id: 'b2-work-negotiation',
    level: 'b2',
    topic: 'work',
    title: 'Negotiating a deal',
    sentences: [
      "Successful negotiations begin with understanding the other party's priorities.",
      'It is important to separate the people from the problem during difficult discussions.',
      'Both sides should aim for an outcome that creates mutual value.',
      'Walking away is sometimes the strongest move if terms are unreasonable.',
      'A well-prepared negotiator anticipates objections and has alternatives ready.',
    ],
  },

  // ── B2 · Công nghệ ──────────────────────────────────
  {
    id: 'b2-artificial-intelligence',
    level: 'b2',
    topic: 'tech',
    title: 'Artificial intelligence',
    sentences: [
      'Artificial intelligence is transforming industries from healthcare to finance.',
      'Machine learning systems can analyse vast amounts of data far faster than humans.',
      'Critics warn that automation may displace workers in certain sectors.',
      'Proponents argue that AI will create new jobs and improve productivity.',
      'Governments are debating how to regulate technology that evolves so rapidly.',
      'The ethical implications of AI decision-making remain a topic of intense discussion.',
    ],
  },
  {
    id: 'b2-space-exploration',
    level: 'b2',
    topic: 'tech',
    title: 'Space exploration',
    sentences: [
      'Humanity has always been fascinated by the mysteries of the universe.',
      'The Apollo missions proved that reaching the Moon was within our grasp.',
      'Private companies have now entered the space race alongside national agencies.',
      'Mars is considered the most likely destination for future manned missions.',
      'Some scientists believe that exploring space is essential for the survival of our species.',
      'Others question whether the enormous cost would be better spent solving problems on Earth.',
    ],
  },

  // ── B2 · Học tập ────────────────────────────────────
  {
    id: 'b2-education-system',
    level: 'b2',
    topic: 'study',
    title: 'Education reform',
    sentences: [
      'Traditional education systems often emphasise memorisation over critical thinking.',
      'Educators are calling for curricula that develop creativity and problem-solving skills.',
      'Standardised testing has been criticised for narrowing the focus of classroom teaching.',
      'Finland is frequently cited as a model for its holistic approach to schooling.',
      'Technology in the classroom can be a powerful tool when used thoughtfully.',
      'Ultimately, the goal of education should be to prepare students for a changing world.',
    ],
  },

  // ── B2 · Xã hội ─────────────────────────────────────
  {
    id: 'b2-urbanisation',
    level: 'b2',
    topic: 'society',
    title: 'Urbanisation',
    sentences: [
      'Over half of the global population now lives in urban areas.',
      'Rapid urbanisation has led to overcrowded housing and strained infrastructure.',
      'City planners face the challenge of providing adequate public transport and green spaces.',
      'Some megacities have implemented congestion charges to reduce traffic.',
      'Despite the problems, cities remain engines of innovation and economic growth.',
    ],
  },

  // ── C1 · IELTS ──────────────────────────────────────
  {
    id: 'c1-ielts-globalisation',
    level: 'c1',
    topic: 'ielts',
    title: 'IELTS Part 3 — Globalisation',
    sentences: [
      'Globalisation has accelerated the exchange of ideas, goods, and capital across borders.',
      'Proponents argue that it has lifted millions out of poverty through expanded trade.',
      'Critics contend that it exacerbates inequality and erodes local cultural identities.',
      'Multinational corporations wield enormous influence over labour standards and environmental policy.',
      'Navigating this tension requires nuanced policy rather than simplistic protectionism.',
    ],
  },

  // ── C1 · Công việc ──────────────────────────────────
  {
    id: 'c1-global-economy',
    level: 'c1',
    topic: 'work',
    title: 'The interconnected economy',
    sentences: [
      'Globalisation has woven national economies into a intricate web of supply chains, capital flows, and digital transactions.',
      'A disruption in one region — whether a pandemic, a conflict, or a financial crisis — can reverberate across continents within days.',
      'Emerging markets have become indispensable manufacturing hubs, yet they remain vulnerable to shifts in demand from wealthier nations.',
      'Central banks must navigate the delicate balance between stimulating growth and containing inflation in an unpredictable environment.',
      'Economists increasingly argue that resilience, not mere efficiency, should guide the restructuring of global trade networks.',
    ],
  },

  // ── C1 · Học tập ────────────────────────────────────
  {
    id: 'c1-language-evolution',
    level: 'c1',
    topic: 'study',
    title: 'How languages evolve',
    sentences: [
      'Languages are living systems that continuously adapt to the needs and influences of their speakers.',
      'Contact between communities through trade, migration, and conquest has historically been a powerful catalyst for linguistic change.',
      'English itself is a testament to this process, having absorbed vocabulary from Latin, French, Norse, and countless other sources.',
      'Purists who resist neologisms and grammatical shifts often overlook the fact that every "standard" language was once considered informal or corrupt.',
      'Understanding language evolution reminds us that communication, not rigid adherence to rules, is the ultimate purpose of speech.',
    ],
  },

  // ── C1 · Sức khỏe ───────────────────────────────────
  {
    id: 'c1-neuroscience-habit',
    level: 'c1',
    topic: 'health',
    title: 'The neuroscience of habit',
    sentences: [
      'Habits are formed when the brain converts a sequence of actions into an automatic routine to conserve cognitive energy.',
      'Neuroscientists have identified a loop consisting of a cue, a routine, and a reward that underpins most habitual behaviour.',
      'Once entrenched, habits are remarkably resistant to change because they are encoded in structures that operate below conscious awareness.',
      'However, research demonstrates that the same neural mechanisms can be harnessed to replace detrimental habits with constructive ones.',
      'The key is to identify the underlying craving that drives the routine and substitute a healthier behaviour that satisfies it.',
      'Lasting transformation therefore depends less on willpower alone than on redesigning the environmental triggers that shape our daily lives.',
    ],
  },

  // ── C1 · Xã hội ─────────────────────────────────────
  {
    id: 'c1-philosophy-choice',
    level: 'c1',
    topic: 'society',
    title: 'The paradox of choice',
    sentences: [
      'Modern consumers are confronted with an overwhelming abundance of options in virtually every domain of life.',
      'Psychologists have observed that excessive choice, rather than liberating us, can lead to anxiety and decision paralysis.',
      'When the cost of reversing a decision is low, people tend to second-guess themselves and report lower satisfaction.',
      'Curating a smaller set of meaningful alternatives may paradoxically increase our sense of autonomy and contentment.',
      'The challenge lies not in eliminating choice altogether but in developing the discernment to choose wisely.',
    ],
  },
];

/**
 * @param {{ topic?: string, level?: string }} filters
 * @param {Lesson[]} [source]
 * @returns {Lesson[]}
 */
export function filterLessons(filters = {}, source = LESSONS) {
  return source.filter((lesson) => {
    if (filters.topic && filters.topic !== 'all' && lesson.topic !== filters.topic) {
      return false;
    }
    if (filters.level && filters.level !== 'all' && lesson.level !== filters.level) {
      return false;
    }
    return true;
  });
}

/**
 * @param {string} id
 * @returns {Lesson | undefined}
 */
export function getLessonById(id) {
  return LESSONS.find((l) => l.id === id);
}

/**
 * @param {string} levelId
 * @returns {Lesson[]}
 */
export function getLessonsByLevel(levelId) {
  return LESSONS.filter((l) => l.level === levelId);
}

/**
 * @param {string} topicId
 * @returns {Lesson[]}
 */
export function getLessonsByTopic(topicId) {
  return LESSONS.filter((l) => l.topic === topicId);
}

/**
 * @param {string} levelId
 * @returns {string}
 */
export function getLevelLabel(levelId) {
  return LEVELS.find((l) => l.id === levelId)?.label ?? levelId.toUpperCase();
}

/**
 * @param {string} topicId
 * @returns {string}
 */
export function getTopicLabel(topicId) {
  return TOPICS.find((t) => t.id === topicId)?.label ?? topicId;
}
