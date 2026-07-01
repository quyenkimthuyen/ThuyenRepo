import {
  sentencesFromText,
  buildCustomLesson,
  parseImportJson,
  normalizeLesson,
} from '../js/customLessons.js';

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const text = `Hello world.
This is line two.
`;
assert(sentencesFromText(text).length === 2, 'split lines');

const built = buildCustomLesson({ title: 'My lesson', sentences: text });
assert(built.lesson?.title === 'My lesson', 'build title');
assert(built.lesson?.id.startsWith('custom-'), 'custom id');
assert(built.lesson?.topic === 'custom', 'default topic');

const json = parseImportJson(
  JSON.stringify({
    title: 'JSON lesson',
    level: 'a2',
    topic: 'travel',
    sentences: ['One.', 'Two.'],
  }),
);
assert(json.lessons.length === 1, 'parse single json');
assert(json.lessons[0].level === 'a2', 'json level');

const multi = parseImportJson(
  JSON.stringify({
    lessons: [
      { title: 'A', sentences: ['Hi.'] },
      { title: 'B', sentences: ['Bye.'] },
    ],
  }),
);
assert(multi.lessons.length === 2, 'parse lessons array');

const bad = buildCustomLesson({ title: '', sentences: '' });
assert(bad.errors.length > 0, 'validation errors');

console.log('customLessons tests: ok');
