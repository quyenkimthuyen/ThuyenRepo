import { SUPPLEMENT_LESSONS } from './supplementLessons.js';
import { EXTRA_TOPIC_LESSONS } from './extraTopicLessons.js';
import { TOEIC_LESSONS } from './toeicLessons.js';

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
  { id: 'toeic', label: 'TOEIC Listening' },
  { id: 'health', label: 'Sức khỏe' },
  { id: 'tech', label: 'Công nghệ' },
  { id: 'society', label: 'Xã hội' },
  { id: 'food', label: 'Ẩm thực' },
  { id: 'sports', label: 'Thể thao' },
  { id: 'communication', label: 'Giao tiếp thực tế' },
  { id: 'custom', label: 'Của tôi' },
];

/** @typedef {{ id: string, level: string, topic: string, title: string, sentences: string[], translations?: string[], custom?: boolean }} Lesson */

/** @type {Lesson[]} */
export const BUNDLED_LESSONS = [
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
  {
    id: 'a1-school-things',
    level: 'a1',
    topic: 'study',
    title: 'School things',
    sentences: [
      'This is my pen.',
      'That is your book.',
      'My bag is on the desk.',
      'The teacher is in the classroom.',
      'I write in my notebook.',
    ],
  },
  {
    id: 'a1-days-and-time',
    level: 'a1',
    topic: 'study',
    title: 'Days and time',
    sentences: [
      'Today is Monday.',
      'Tomorrow is Tuesday.',
      'I go to class in the morning.',
      'The lesson starts at eight.',
      'We study English every day.',
    ],
  },

  // ── A1 · Du lịch ────────────────────────────────────
  {
    id: 'a1-at-the-park',
    level: 'a1',
    topic: 'travel',
    title: 'At the park',
    sentences: [
      'I am at the park.',
      'The trees are tall.',
      'The flowers are red and yellow.',
      'Children play near the lake.',
      'I walk with my friend.',
    ],
  },
  {
    id: 'a1-on-the-bus',
    level: 'a1',
    topic: 'travel',
    title: 'On the bus',
    sentences: [
      'I wait for the bus.',
      'The bus is blue.',
      'I sit by the window.',
      'The driver is very kind.',
      'I get off near my school.',
    ],
  },

  // ── A1 · Sức khỏe ───────────────────────────────────
  {
    id: 'a1-my-body',
    level: 'a1',
    topic: 'health',
    title: 'My body',
    sentences: [
      'I have two eyes.',
      'I have two hands.',
      'My head hurts today.',
      'I wash my hands with soap.',
      'I drink water to stay healthy.',
    ],
  },

  // ── A1 · IELTS ──────────────────────────────────────
  {
    id: 'a1-ielts-simple-answers',
    level: 'a1',
    topic: 'ielts',
    title: 'IELTS Part 1 — Simple answers',
    sentences: [
      'My name is Minh.',
      'I am from Vietnam.',
      'I live with my family.',
      'I like English very much.',
      'My hobby is drawing pictures.',
    ],
  },

  // ── A1 · Công việc ──────────────────────────────────
  {
    id: 'a1-jobs',
    level: 'a1',
    topic: 'work',
    title: 'Jobs',
    sentences: [
      'My father is a doctor.',
      'My mother is a teacher.',
      'The nurse works in a hospital.',
      'The farmer has many animals.',
      'I want to be a singer.',
    ],
  },
  {
    id: 'a1-in-the-office',
    level: 'a1',
    topic: 'work',
    title: 'In the office',
    sentences: [
      'This is my desk.',
      'The computer is new.',
      'I open my email.',
      'My boss is very friendly.',
      'We have a meeting today.',
    ],
  },

  // ── A1 · Công nghệ ──────────────────────────────────
  {
    id: 'a1-my-phone',
    level: 'a1',
    topic: 'tech',
    title: 'My phone',
    sentences: [
      'I have a phone.',
      'My phone is small.',
      'I call my mother.',
      'I take a photo.',
      'The battery is low.',
    ],
  },
  {
    id: 'a1-computer-class',
    level: 'a1',
    topic: 'tech',
    title: 'Computer class',
    sentences: [
      'I use a computer.',
      'The keyboard is black.',
      'I click the mouse.',
      'The screen is bright.',
      'We learn online today.',
    ],
  },

  // ── A1 · Xã hội ─────────────────────────────────────
  {
    id: 'a1-good-friends',
    level: 'a1',
    topic: 'society',
    title: 'Good friends',
    sentences: [
      'I have a good friend.',
      'We help each other.',
      'She shares her toys.',
      'He says sorry.',
      'Friends are kind.',
    ],
  },
  {
    id: 'a1-keep-the-city-clean',
    level: 'a1',
    topic: 'society',
    title: 'Keep the city clean',
    sentences: [
      'I see trash on the street.',
      'I put paper in the bin.',
      'We keep the park clean.',
      'Clean water is important.',
      'I love my city.',
    ],
  },

  // ── A1 · Đời sống bổ sung ───────────────────────────
  {
    id: 'a1-my-clothes',
    level: 'a1',
    topic: 'daily',
    title: 'My clothes',
    sentences: [
      'I wear a blue shirt.',
      'My shoes are white.',
      'This hat is too big.',
      'I put on my jacket.',
      'My socks are clean.',
    ],
  },
  {
    id: 'a1-feelings',
    level: 'a1',
    topic: 'health',
    title: 'Feelings',
    sentences: [
      'I am happy today.',
      'She is sad now.',
      'He is tired after school.',
      'We are hungry.',
      'They are excited.',
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
      'I would like to describe a memorable place that left a strong impression on me.',
      'It is a small coastal town in central Vietnam that I visited last October.',
      'I went there with two close friends during a short autumn break from university.',
      'We had been feeling exhausted from exams, so we wanted somewhere quiet by the sea.',
      'The town is famous for its dramatic cliffs, soft white sand, and crystal-clear water.',
      'Every morning we hiked along the coast and took photos of the sunrise.',
      'In the afternoons we swam in the sea and tried fresh seafood at tiny family restaurants.',
      'What made it truly special was how peaceful and unspoiled everything felt.',
      'There were no crowded tourist buses, and the locals were warm and welcoming.',
      'I felt completely relaxed for the first time in months, as if my mind finally slowed down.',
      'I would definitely recommend it to anyone who needs to escape busy city life for a few days.',
      'In fact, I am already planning to return there with my family next summer.',
    ],
  },
  {
    id: 'b2-ielts-describe-gift',
    level: 'b2',
    topic: 'ielts',
    title: 'IELTS Part 2 — Describe a gift you received',
    sentences: [
      'I would like to talk about a special gift that I received a couple of years ago.',
      'It was a high-quality leather notebook that my older sister gave me for my birthday.',
      'At the time I had just started my first full-time job and was feeling quite overwhelmed.',
      'She said she wanted to give me something practical that would also feel personal.',
      'The notebook has a simple dark-brown cover and thick cream-coloured pages inside.',
      'What I love most is that she wrote a short encouraging message on the first page.',
      'I have been using it ever since to plan my goals and record new English vocabulary.',
      'Whenever I open it, I am reminded of her support during a difficult transition in my life.',
      'It was not the most expensive present I have ever received, but it was deeply meaningful.',
      'I still carry it in my bag when I attend meetings or study at a café.',
      'In fact, I am nearly at the last few pages, so I hope she will buy me another one soon.',
      'I would definitely recommend giving thoughtful gifts like this to people you care about.',
    ],
  },
  {
    id: 'b2-ielts-describe-skill',
    level: 'b2',
    topic: 'ielts',
    title: 'IELTS Part 2 — Describe a skill you learned',
    sentences: [
      'I would like to describe a useful skill that I learned in my early twenties.',
      'The skill is public speaking, which I began developing through a university debate club.',
      'Before joining, I was extremely nervous about speaking in front of a large audience.',
      'Our coach taught us how to structure arguments, control our voice, and maintain eye contact.',
      'We practised every week by preparing short speeches on social and environmental topics.',
      'The first time I competed in a tournament, my hands were shaking and I spoke too quickly.',
      'However, I gradually improved and even won a small award at a regional contest.',
      'Learning this skill has helped me enormously in job interviews and workplace presentations.',
      'It also boosted my confidence when communicating with people from different backgrounds.',
      'Looking back, I realise that progress came from consistent practice rather than natural talent.',
      'I still watch online talks to learn from experienced speakers around the world.',
      'I would encourage anyone who feels shy to join a club and practise in a supportive environment.',
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

  {
    "id": "a1-ielts-pets",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Pets",
    "sentences": [
      "Do you like animals?",
      "Yes, I really like animals.",
      "I have a small cat at home.",
      "She has soft white fur.",
      "We play together in the evening."
    ]
  },

  {
    "id": "a1-ielts-colors",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Colors",
    "sentences": [
      "What is your favourite color?",
      "My favourite color is blue.",
      "It is the color of the sky.",
      "I have a blue backpack.",
      "It makes me feel happy."
    ]
  },

  {
    "id": "a1-ielts-fruits",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Fruits",
    "sentences": [
      "Do you eat a lot of fruit?",
      "Yes, I eat fruit every day.",
      "I like apples and bananas best.",
      "They are sweet and healthy.",
      "My mother buys them at the market."
    ]
  },

  {
    "id": "a1-ielts-weather",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Weather",
    "sentences": [
      "What is the weather like today?",
      "It is sunny and hot today.",
      "I like sunny weather very much.",
      "I can go to the park.",
      "I do not like rainy days."
    ]
  },

  {
    "id": "a1-ielts-music",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Music",
    "sentences": [
      "Do you like listening to music?",
      "Yes, I listen to music every day.",
      "I like pop music best.",
      "It is very exciting.",
      "I listen on my phone."
    ]
  },

  {
    "id": "a1-ielts-toys",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Toys",
    "sentences": [
      "What was your favourite toy as a child?",
      "I loved my red toy car.",
      "My grandfather gave it to me.",
      "I played with it all day.",
      "I still keep it in my room."
    ]
  },

  {
    "id": "a1-ielts-drinks",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Drinks",
    "sentences": [
      "What do you like to drink?",
      "I like to drink fresh water.",
      "I also drink orange juice.",
      "It has a sweet taste.",
      "I do not like soda."
    ]
  },

  {
    "id": "a1-ielts-flowers",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Flowers",
    "sentences": [
      "Do you like flowers?",
      "Yes, I think flowers are beautiful.",
      "I like red roses best.",
      "They have a lovely smell.",
      "We have some flowers in our garden."
    ]
  },

  {
    "id": "a1-ielts-weekends",
    "level": "a1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Weekends",
    "sentences": [
      "What do you do on weekends?",
      "I sleep late on Saturday.",
      "Then I visit my grandfather.",
      "We eat dinner together.",
      "I relax before Monday."
    ]
  },

  {
    "id": "a2-ielts-accommodation",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Accommodation",
    "sentences": [
      "Do you live in a house or an apartment?",
      "I live in a comfortable apartment.",
      "It is located near the city centre.",
      "My favorite room is my bedroom.",
      "I decorated it with nice posters."
    ]
  },

  {
    "id": "a2-ielts-movies",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Movies",
    "sentences": [
      "How often do you watch movies?",
      "I watch movies once or twice a week.",
      "I prefer action and comedy films.",
      "They help me relax after study.",
      "Sometimes I go to the cinema with friends."
    ]
  },

  {
    "id": "a2-ielts-sports",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Sports",
    "sentences": [
      "Do you play any sports?",
      "I play badminton on weekends.",
      "It is a great way to stay fit.",
      "I also enjoy watching football on TV.",
      "My favorite team is very famous."
    ]
  },

  {
    "id": "a2-ielts-birthdays",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Birthdays",
    "sentences": [
      "How do you usually celebrate your birthday?",
      "I have a small party at home.",
      "I invite my close friends and family.",
      "We eat cake and blow out candles.",
      "I love receiving birthday cards."
    ]
  },

  {
    "id": "a2-ielts-reading",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Reading",
    "sentences": [
      "Do you like reading books?",
      "Yes, reading is one of my hobbies.",
      "I read comic books and novels.",
      "I usually read before going to sleep.",
      "It helps me learn new words."
    ]
  },

  {
    "id": "a2-ielts-clothes",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Clothes",
    "sentences": [
      "What kind of clothes do you like to wear?",
      "I prefer casual clothes like jeans and T-shirts.",
      "They are very comfortable for daily wear.",
      "I wear formal clothes for special events.",
      "My favorite colors for clothes are black and white."
    ]
  },

  {
    "id": "a2-ielts-photos",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Photos",
    "sentences": [
      "Do you like taking photos?",
      "Yes, I take a lot of photos with my phone.",
      "I enjoy taking pictures of nature and food.",
      "I share them with my friends online.",
      "Photos help me save good memories."
    ]
  },

  {
    "id": "a2-ielts-holidays",
    "level": "a2",
    "topic": "ielts",
    "title": "IELTS Part 1 — Holidays",
    "sentences": [
      "Where do you go on holidays?",
      "I usually go to the countryside.",
      "It is very peaceful and quiet there.",
      "I can breathe fresh air and relax.",
      "Sometimes we go to the beach in summer."
    ]
  },

  {
    "id": "b1-ielts-internet",
    "level": "b1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Internet",
    "sentences": [
      "How much time do you spend online every day?",
      "I think I spend about three hours on the internet daily.",
      "I mostly use it for studying and checking social media.",
      "It is a convenient tool to search for information.",
      "However, staying online too long can be a waste of time."
    ]
  },

  {
    "id": "b1-ielts-festivals",
    "level": "b1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Festivals",
    "sentences": [
      "What is the most important festival in your country?",
      "Tet is definitely the most significant festival in Vietnam.",
      "It is a time for family reunions and celebrating the new year.",
      "We clean our houses and prepare traditional food.",
      "Children receive lucky money in red envelopes."
    ]
  },

  {
    "id": "b1-ielts-neighbors",
    "level": "b1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Neighbors",
    "sentences": [
      "Do you get along well with your neighbors?",
      "Yes, my neighbors are very friendly and helpful.",
      "We always say hello and sometimes chat in the evening.",
      "They helped us water the plants when we went away.",
      "I think having good neighbors makes life much easier."
    ]
  },

  {
    "id": "b1-ielts-shopping",
    "level": "b1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Online shopping",
    "sentences": [
      "Do you prefer shopping online or in local stores?",
      "Honestly, I prefer shopping online because it saves time.",
      "I can compare prices easily without walking around.",
      "On the other hand, buying clothes online can be risky.",
      "Sometimes the actual size does not fit me well."
    ]
  },

  {
    "id": "b1-ielts-gardens",
    "level": "b1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Gardens and Parks",
    "sentences": [
      "Are there many parks near where you live?",
      "Yes, there is a large park just ten minutes away from my house.",
      "I often go there for a walk in the late afternoon.",
      "It has many green trees and a small lake.",
      "Public parks are essential for residents in crowded cities."
    ]
  },

  {
    "id": "b1-ielts-museums",
    "level": "b1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Museums",
    "sentences": [
      "Do you like visiting museums?",
      "Yes, I enjoy visiting history museums occasionally.",
      "It is an interesting way to learn about the past.",
      "I went to the national museum last month.",
      "The tickets were free for students."
    ]
  },

  {
    "id": "b1-ielts-handcrafts",
    "level": "b1",
    "topic": "ielts",
    "title": "IELTS Part 1 — Handcrafts",
    "sentences": [
      "Did you make any handcrafts when you were young?",
      "Yes, we learned to make paper stars in primary school.",
      "It was a fun activity for children.",
      "I also tried making clay pots once.",
      "Handmade gifts are very meaningful to receive."
    ]
  },

  {
    "id": "b2-ielts-describe-book",
    "level": "b2",
    "topic": "ielts",
    "title": "IELTS Part 2 — Describe a book",
    "sentences": [
      "I would like to talk about a book that has influenced me in a meaningful way.",
      "It is called Atomic Habits, and it focuses on building small positive routines.",
      "A close friend recommended it to me last year when I was struggling to stay motivated.",
      "I bought a copy at a local bookstore during a particularly stressful period at work.",
      "The author explains how tiny daily actions can lead to remarkable long-term results.",
      "One idea that stayed with me is that you do not rise to the level of your goals, but fall to the level of your systems.",
      "After reading it, I started waking up thirty minutes earlier to study English every day.",
      "I also began tracking my habits in a simple notebook, which kept me accountable.",
      "Within three months I noticed I was more focused, organised, and less anxious.",
      "The book is written in clear, practical language, so it is easy to apply the advice immediately.",
      "I have since lent it to two colleagues, and they said it helped them as well.",
      "I would wholeheartedly recommend it to anyone who wants to improve their daily discipline."
    ]
  },

  {
    "id": "b2-ielts-describe-event",
    "level": "b2",
    "topic": "ielts",
    "title": "IELTS Part 2 — Describe a historic event",
    "sentences": [
      "I would like to describe a historic event that is extremely important in my country.",
      "The event I have in mind is the declaration of independence on the second of September, nineteen forty-five.",
      "I first learned about it in detail during a history lesson in secondary school.",
      "Our teacher showed us old photographs and played a recording of the historic speech.",
      "On that day, hundreds of thousands of people gathered in Ba Dinh Square in Hanoi.",
      "They waited patiently in the heat to hear the president announce the birth of a new nation.",
      "The speech marked the end of decades of colonial rule and foreign occupation.",
      "For many families, including my grandparents, it was the most emotional moment of their lives.",
      "Every year we commemorate this day with ceremonies, flags, and television programmes.",
      "When I watch the footage today, I still feel a deep sense of pride and gratitude.",
      "It reminds me that freedom and independence should never be taken for granted.",
      "I believe every young Vietnamese should understand the meaning of this historic milestone."
    ]
  },

  {
    "id": "b2-ielts-describe-person",
    "level": "b2",
    "topic": "ielts",
    "title": "IELTS Part 2 — Describe a successful person",
    "sentences": [
      "I would like to talk about a successful person whom I truly admire.",
      "She is a local entrepreneur in my hometown who started a green packaging business.",
      "I first heard about her through a documentary that aired on national television.",
      "At the time, she was working alone from a small rented warehouse on the edge of the city.",
      "Her company produces biodegradable packaging materials for restaurants and online shops.",
      "She told interviewers that she was inspired by the amount of plastic waste in her neighbourhood.",
      "In the early years she faced financial difficulties and many people doubted her idea.",
      "However, she persisted, improved her product, and gradually won the trust of larger clients.",
      "Today her business employs dozens of workers and exports products to several countries.",
      "What I admire most is her determination and her genuine commitment to protecting the environment.",
      "She also mentors young founders and speaks at schools about sustainable entrepreneurship.",
      "Her story has motivated me to believe that meaningful success is possible with patience and clear values."
    ]
  },

  {
    "id": "b2-ielts-describe-journey",
    "level": "b2",
    "topic": "ielts",
    "title": "IELTS Part 2 — Describe a memorable journey",
    "sentences": [
      "I would like to describe a memorable journey that I took by overnight train.",
      "It happened two summers ago when I travelled from Hanoi to Da Nang with three university friends.",
      "We had booked soft sleeper tickets because we wanted to save money and enjoy the scenery.",
      "The train left the station at nine in the evening, just as the city lights began to fade.",
      "At first we chatted and played cards, but later we opened the window to feel the cool night air.",
      "In the morning we woke up to stunning views of mountains, rivers, and green rice fields.",
      "We spent the rest of the day swimming at the beach and eating local specialities.",
      "What made the journey special was the relaxed pace and the time we had to talk without distractions.",
      "There were a few delays, but none of us minded because the experience felt like an adventure.",
      "I took hundreds of photos, and we still laugh when we look at them together.",
      "It was one of the most affordable trips we have ever taken, yet also one of the most enjoyable.",
      "I would love to repeat the same route someday, perhaps with my younger brother."
    ]
  },

  {
    "id": "b2-ielts-describe-teacher",
    "level": "b2",
    "topic": "ielts",
    "title": "IELTS Part 2 — Describe a teacher who influenced you",
    "sentences": [
      "I would like to talk about a teacher who had a major influence on my academic life.",
      "Her name is Ms Lan, and she taught me English throughout upper secondary school.",
      "When I first entered her class, I was shy and afraid of making pronunciation mistakes.",
      "Instead of criticising us harshly, she created a friendly atmosphere where errors were part of learning.",
      "She often used short videos, role plays, and group discussions to make lessons engaging.",
      "One activity I remember clearly was a weekly speaking circle where everyone had to share an opinion.",
      "She also gave personalised feedback in a small notebook she kept for each student.",
      "Thanks to her encouragement, I joined an English speaking contest and reached the school final.",
      "More importantly, she taught me that confidence grows when you prepare carefully and take small risks.",
      "We still exchange messages on social media, and she always asks about my studies.",
      "I genuinely believe I would not have pursued international opportunities without her guidance.",
      "If I could meet her again, I would thank her for changing the way I see language learning."
    ]
  },

  {
    "id": "b2-ielts-describe-hobby",
    "level": "b2",
    "topic": "ielts",
    "title": "IELTS Part 2 — Describe a hobby you enjoy",
    "sentences": [
      "I would like to describe a hobby that helps me relax after a busy week.",
      "It is photography, especially taking pictures of street life and old architecture in my city.",
      "I became interested in it about three years ago when a friend lent me a second-hand mirrorless camera.",
      "At first I simply took random shots, but soon I started learning about light, composition, and perspective.",
      "I usually go out early on Sunday mornings when the streets are quiet and the light is soft.",
      "Sometimes I walk for hours without noticing the time because I am searching for an interesting angle.",
      "I have created an online album where I share selected photos with friends and fellow enthusiasts.",
      "Occasionally people message me to ask where a particular picture was taken, which feels rewarding.",
      "The hobby has taught me to observe small details that I used to ignore in daily life.",
      "It is also a creative outlet that does not require expensive equipment to begin with.",
      "On rainy days I edit photos at home and read articles by professional photographers.",
      "I would recommend photography to anyone who wants to slow down and appreciate their surroundings."
    ]
  },

  {
    "id": "b2-ielts-describe-city",
    "level": "b2",
    "topic": "ielts",
    "title": "IELTS Part 2 — Describe a city you have visited",
    "sentences": [
      "I would like to talk about a city I visited that left a lasting impression on me.",
      "The city is Hoi An, a historic town in central Vietnam that I explored during a short holiday.",
      "I went there with my parents during the lantern festival, which takes place on the full moon.",
      "As soon as we arrived, we noticed the colourful lanterns hanging along every narrow street.",
      "The old wooden houses, yellow walls, and riverside cafés created a wonderfully peaceful atmosphere.",
      "During the day we visited a traditional craft village and tried making our own small lanterns.",
      "In the evening we took a boat ride on the river while thousands of lights reflected on the water.",
      "The local food was another highlight, especially cao lau and fresh mango desserts.",
      "What impressed me most was how the city has preserved its heritage while welcoming tourists respectfully.",
      "I felt as if I had stepped back in time, yet the people were modern and welcoming.",
      "I bought handmade souvenirs for my cousins and took photos that still decorate my room.",
      "I would highly recommend visiting Hoi An if you want to experience culture, history, and cuisine in one place."
    ]
  },

  {
    "id": "c1-ielts-ai-ethics",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Artificial Intelligence ethics",
    "sentences": [
      "The rapid development of artificial intelligence raises profound ethical questions.",
      "One major concern is the potential displacement of workers across various industries.",
      "Additionally, biases embedded in algorithms can perpetuate social inequality.",
      "Regulatory frameworks must be established to ensure AI transparency and accountability.",
      "We must prioritize human well-being over corporate profit in technological advancement."
    ]
  },

  {
    "id": "c1-ielts-higher-ed-value",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Higher education value",
    "sentences": [
      "The utility of a university degree is increasingly scrutinized in the modern job market.",
      "Critics argue that academic curricula are often disconnected from practical industry demands.",
      "Conversely, higher education fosters critical thinking and intellectual growth.",
      "Universities should integrate vocational training to enhance graduate employability.",
      "A balanced approach prepares students for both professional success and civic responsibility."
    ]
  },

  {
    "id": "c1-ielts-work-life-balance",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Work-life balance",
    "sentences": [
      "Achieving a healthy work-life balance is challenging in a hyper-connected society.",
      "Digital communication tools have blurred the boundaries between professional and personal life.",
      "Chronic stress and burnout can lead to severe physical and psychological issues.",
      "Employers should cultivate a supportive environment that respects personal time.",
      "Ultimately, prioritizing well-being enhances both individual happiness and long-term productivity."
    ]
  },

  {
    "id": "c1-ielts-climate-policies",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Climate change policies",
    "sentences": [
      "Addressing climate change demands robust international cooperation and decisive action.",
      "Transitioning to renewable energy sources is imperative to reduce carbon emissions.",
      "Governments should implement carbon pricing mechanisms to incentivize green transition.",
      "However, developing nations require financial support to adopt sustainable technologies.",
      "Failure to act collectively will lead to catastrophic ecological consequences."
    ]
  },

  {
    "id": "c1-ielts-cultural-preservation",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Cultural preservation",
    "sentences": [
      "Globalisation presents a formidable threat to indigenous languages and cultural heritage.",
      "As dominant cultures expand, unique traditions risk being marginalized or lost entirely.",
      "Preserving cultural diversity is essential for maintaining historical identity.",
      "Educational curricula should integrate local history and indigenous languages.",
      "Community-led initiatives play a vital role in keeping traditions alive for future generations."
    ]
  },

  {
    "id": "c1-ielts-economic-disparity",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Economic disparity",
    "sentences": [
      "Growing wealth inequality poses a significant threat to global social stability.",
      "Systemic factors such as tax policies often favor capital accumulation over labor.",
      "Disproportionate wealth distribution limits access to quality education and healthcare.",
      "Progressive taxation and social safety nets are necessary to bridge this divide.",
      "Fostering inclusive economic growth benefits society as a whole."
    ]
  },

  {
    "id": "c1-ielts-urbanization-challenges",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Urbanization challenges",
    "sentences": [
      "The relentless influx of population into metropolitan areas strains city resources.",
      "Inadequate housing leads to the proliferation of informal settlements.",
      "Moreover, traffic congestion and waste management place immense pressure on municipal systems.",
      "Urban planners must design smart cities with sustainable infrastructure and green spaces.",
      "Decentralizing economic opportunities can help alleviate the pressure on major capitals."
    ]
  },

  {
    "id": "c1-ielts-scientific-research",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Scientific research funding",
    "sentences": [
      "Public funding for scientific research is indispensable for long-term societal progress.",
      "Private corporations tend to prioritize research with immediate commercial viability.",
      "In contrast, fundamental scientific breakthroughs often require years of speculative investment.",
      "Governments should allocate substantial budgets to academic research institutions.",
      "Investing in basic science expands human knowledge and drives future innovation."
    ]
  },

  {
    "id": "c1-ielts-leadership-qualities",
    "level": "c1",
    "topic": "ielts",
    "title": "IELTS Part 3 — Leadership qualities",
    "sentences": [
      "Effective leadership in the twenty-first century demands empathy and adaptability.",
      "Traditional top-down authority is increasingly ineffective in diverse workplaces.",
      "A great leader inspires collaboration and empowers team members to take initiative.",
      "Furthermore, integrity and transparency are essential to build trust and credibility.",
      "Ultimately, leadership is about serving the collective purpose rather than asserting power."
    ]
  },

  ...SUPPLEMENT_LESSONS,

  ...EXTRA_TOPIC_LESSONS,

  ...TOEIC_LESSONS,
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
