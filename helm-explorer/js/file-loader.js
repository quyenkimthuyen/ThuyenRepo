/**
 * Fetch Helm chart source files — auto-detect base path for Live Server
 */
const FileLoader = (() => {
  const cache = new Map();
  let basePath = null;

  async function detectBase() {
    if (basePath !== null) return basePath;
    const candidates = ['', '..'];
    for (const base of candidates) {
      const prefix = base ? `${base}/` : '';
      try {
        const r = await fetch(`${prefix}altiplano-solution/Chart.yaml`, { cache: 'no-store' });
        if (r.ok) {
          basePath = base;
          return base;
        }
      } catch { /* try next */ }
    }
    basePath = '..';
    return basePath;
  }

  function buildUrl(chartPath, fileName) {
    const base = basePath ?? '..';
    const prefix = base ? `${base}/` : '';
    return `${prefix}${chartPath}/${fileName}`.replace(/\/+/g, '/');
  }

  async function fetchFile(chartPath, fileName) {
    await detectBase();
    const key = `${chartPath}/${fileName}`;
    if (cache.has(key)) return cache.get(key);

    const url = buildUrl(chartPath, fileName);
    const promise = fetch(url, { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status} — ${url}`);
        return r.text();
      })
      .catch(err => {
        cache.delete(key);
        throw err;
      });

    cache.set(key, promise);
    return promise;
  }

  async function fetchTemplate(chartPath, templateRel) {
    return fetchFile(chartPath, templateRel);
  }

  async function getBase() {
    return detectBase();
  }

  return { fetchFile, fetchTemplate, getBase, buildUrl };
})();
