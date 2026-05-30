// scripts/download_audio.js
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const DATA_FILE = path.resolve(__dirname, '..', 'data', 'all-topics.json');
const AUDIO_DIR = path.resolve(__dirname, '..', 'audio');

if (!fs.existsSync(AUDIO_DIR)) {
  fs.mkdirSync(AUDIO_DIR, { recursive: true });
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`Failed to get '${url}' (${res.statusCode})`));
        return;
      }
      const file = fs.createWriteStream(dest);
      res.pipe(file);
      file.on('finish', () => file.close(() => resolve()));
    }).on('error', (err) => {
      fs.unlink(dest, () => reject(err));
    });
  });
}

(async () => {
  const raw = fs.readFileSync(DATA_FILE, 'utf8').replace(/^\uFEFF/, '');
  const parsed = JSON.parse(raw);
  // Support both array and object-with-array formats
  const data = Array.isArray(parsed) ? parsed : (Object.values(parsed)[0] || []);

  let changed = false;
  for (const entry of data) {
    if (entry.audio_us && typeof entry.audio_us === 'string' && entry.audio_us.trim()) {
      if (!entry.audio_us.startsWith('http')) continue;
      const extMatch = entry.audio_us.match(/\.([a-z0-9]+)(?:\?|$)/i);
      const ext = extMatch ? extMatch[1] : 'mp3';
      const filename = `${entry.id}.${ext}`;
      const destPath = path.join(AUDIO_DIR, filename);
      if (!fs.existsSync(destPath)) {
        console.log(`Downloading ${entry.audio_us} -> ${destPath}`);
        try {
          await downloadFile(entry.audio_us, destPath);
        } catch (e) {
          console.error('Download failed for', entry.audio_us, e);
          continue;
        }
      }
      const relativePath = `audio/${filename}`;
    entry.audio_us = relativePath;
      changed = true;
    }
  }
  if (changed) {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
    console.log('Updated data file with local audio paths.');
  } else {
    console.log('No changes made to data file.');
  }
})();
