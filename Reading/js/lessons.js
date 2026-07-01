/** @type {{ id: string, title: string, sentences: string[] }[]} */
export const LESSONS = [
  {
    id: 'morning-routine',
    title: 'Morning routine',
    sentences: [
      "I wake up at six o'clock every morning.",
      'First, I brush my teeth and wash my face.',
      'Then I eat breakfast with my family.',
      'After that, I go to school by bus.',
    ],
  },
  {
    id: 'self-intro',
    title: 'Self introduction',
    sentences: [
      'Hello, my name is Anna.',
      'I am twenty years old.',
      'I live in Hanoi with my parents.',
      'I like reading books and listening to music.',
    ],
  },
  {
    id: 'weekend',
    title: 'Weekend plans',
    sentences: [
      'On Saturday morning, I usually clean my room.',
      'In the afternoon, I meet my friends at the park.',
      'We sometimes play football or ride bicycles.',
      'On Sunday evening, I prepare for the new week.',
    ],
  },
];

/**
 * @param {string} id
 * @returns {{ id: string, title: string, sentences: string[] } | undefined}
 */
export function getLessonById(id) {
  return LESSONS.find((l) => l.id === id);
}
