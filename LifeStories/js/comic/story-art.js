/* Primary school illustration registry */
const ILLUSTRATED_STYLES = ['comic', 'watercolor', 'flat', 'crayon', 'papercut'];

const ILLUSTRATION_STYLE_LABELS = {
  comic: { vi: 'Truyện Tranh', en: 'Comic' },
  watercolor: { vi: 'Màu Nước', en: 'Watercolor' },
  flat: { vi: 'Phẳng Màu', en: 'Flat Design' },
  crayon: { vi: 'Sáp Màu', en: 'Crayon' },
  papercut: { vi: 'Cắt Giấy', en: 'Paper Cut' },
};

function getStoryArtForScene(storyId, sceneId) {
  let art = null;
  if (storyId === 'ps-01' && typeof getPS01Art === 'function') art = getPS01Art(sceneId);
  else if (storyId === 'ps-02' && typeof getPS02Art === 'function') art = getPS02Art(sceneId);
  else if (storyId === 'ps-03' && typeof getPS03Art === 'function') art = getPS03Art(sceneId);
  else if (storyId === 'ps-04' && typeof getPS04Art === 'function') art = getPS04Art(sceneId);
  else if (storyId === 'ps-05' && typeof getPS05Art === 'function') art = getPS05Art(sceneId);
  return art;
}

function getComicArtForScene(storyId, sceneId) {
  return getStoryArtForScene(storyId, sceneId);
}

function isIllustratedStyle(style) {
  return ILLUSTRATED_STYLES.includes(style);
}
