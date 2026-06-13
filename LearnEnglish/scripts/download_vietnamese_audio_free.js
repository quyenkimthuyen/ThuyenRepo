// scripts/download_vietnamese_audio_free.js
const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.resolve(__dirname, '..');
const AUDIO_VI_DIR = path.join(ROOT, 'audio', 'vi');

const DATA_FILES = [
  path.join(ROOT, 'data', 'all-topics-grade4.json'),
  path.join(ROOT, 'data', 'generate', 'grade4-basic-english-premium.json')
];

if (!fs.existsSync(AUDIO_VI_DIR)) {
  fs.mkdirSync(AUDIO_VI_DIR, { recursive: true });
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      }
    };
    https.get(url, options, (res) => {
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  try {
    console.log('Loading dataset...');
    const dataFile = DATA_FILES[0];
    if (!fs.existsSync(dataFile)) {
      throw new Error(`Data file not found: ${dataFile}`);
    }

    const raw = fs.readFileSync(dataFile, 'utf8').replace(/^\uFEFF/, '');
    const parsed = JSON.parse(raw);
    const key = 'grade4-basic-english-premium';
    const words = parsed[key];

    if (!Array.isArray(words)) {
      throw new Error(`Invalid grade4 dataset format. Expected array key: ${key}`);
    }

    console.log(`Found ${words.length} words in Grade 4 dataset.`);
    let downloaded = 0;
    let skipped = 0;

    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      const meaning = String(word.meaning_vi || '').trim();
      if (!meaning) {
        console.log(`[${i + 1}/${words.length}] Skipping ${word.id} (${word.word}): No Vietnamese meaning`);
        continue;
      }

      // Ensure audio_vi field is set correctly
      const relativePath = `audio/vi/${word.id}.mp3`;
      word.audio_vi = relativePath;

      const destPath = path.join(AUDIO_VI_DIR, `${word.id}.mp3`);
      if (fs.existsSync(destPath)) {
        skipped++;
        continue;
      }

      console.log(`[${i + 1}/${words.length}] Downloading audio for "${word.word}" ("${meaning}")...`);
      const url = `https://translate.google.com/translate_tts?ie=UTF-8&q=${encodeURIComponent(meaning)}&tl=vi&client=tw-ob`;
      
      try {
        await downloadFile(url, destPath);
        downloaded++;
        // Be gentle with requests to avoid rate limits
        await sleep(300);
      } catch (err) {
        console.error(`Failed to download audio for ${word.id}:`, err.message);
      }
    }

    // Save updated lists back to files
    console.log('Saving updated datasets...');
    for (const filePath of DATA_FILES) {
      if (fs.existsSync(filePath)) {
        const payload = { [key]: words };
        fs.writeFileSync(filePath, JSON.stringify(payload, null, 2) + '\n', 'utf8');
        console.log(`Updated ${filePath}`);
      }
    }

    console.log(`\nFinished! Downloaded: ${downloaded}, Skipped existing: ${skipped}`);
  } catch (error) {
    console.error('An error occurred:', error);
  }
})();
