const PS01_COMIC_ART = {
  classroom: {
    mood: 'morning',
    caption: { vi: 'Sáng thứ Hai — Lớp có thêm một bàn mới', en: 'Monday morning — A new desk in class' },
  },
  playground: {
    mood: 'playful',
    caption: { vi: 'Giờ ra chơi — Ai sẽ đến bên An?', en: 'Recess — Who will go to An?' },
  },
  lunch: {
    mood: 'tense',
    caption: { vi: 'Giờ ăn trưa — Lời thì thầm', en: 'Lunch — A whispered word' },
  },
  artroom: {
    mood: 'warm',
    caption: { vi: 'Bài tập nhóm — Ba cây bút vẽ một chú chim', en: 'Group art — Three pencils, one bird' },
  },
  ending: {
    mood: 'sunset',
    caption: { vi: 'Chiếc ghế không còn trống', en: 'The chair is no longer empty' },
  },
};

const PS01_SCENE_ILLUSTRATION = {
  'ps01-01': 'classroom',
  'ps01-02': 'playground',
  'ps01-03a': 'playground',
  'ps01-03b': 'playground',
  'ps01-04': 'lunch',
  'ps01-05': 'artroom',
  'ps01-06a': 'artroom',
  'ps01-06b': 'artroom',
  'ps01-07': 'playground',
  'ps01-08': 'playground',
  'ps01-09': 'ending',
  'ps01-10': 'ending',
};

function getComicArtForScene(storyId, sceneId) {
  if (storyId !== 'ps-01') return null;
  const key = PS01_SCENE_ILLUSTRATION[sceneId];
  if (!key) return null;
  return { key, ...PS01_COMIC_ART[key], src: `assets/comics/ps-01/${key}.svg` };
}
