#!/usr/bin/env node
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const AUDIO_VI_DIR = path.join(ROOT, 'audio', 'vi');

const DATASETS = {
  grade4: {
    key: 'grade4-basic-english-premium',
    files: [
      path.join(ROOT, 'data/generate/grade4-basic-english-premium.json'),
      path.join(ROOT, 'data/all-topics-grade4.json'),
    ],
  },
};

const GOOGLE_VOICE = process.env.GOOGLE_TTS_VOICE || 'vi-VN-Neural2-D';
const FPT_VOICE = process.env.FPT_TTS_VOICE || 'banmai';
const FPT_SPEED = process.env.FPT_TTS_SPEED || '0';

function parseArgs(argv) {
  const args = {
    dataset: 'grade4',
    provider: process.env.TTS_PROVIDER || 'google',
    force: false,
    pathsOnly: false,
    dryRun: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--dataset') args.dataset = argv[index + 1];
    if (arg === '--provider') args.provider = argv[index + 1];
    if (arg === '--force') args.force = true;
    if (arg === '--paths-only') args.pathsOnly = true;
    if (arg === '--dry-run') args.dryRun = true;
  }
  return args;
}

function loadDataset(filePath, datasetKey) {
  const raw = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  const parsed = JSON.parse(raw);
  if (Array.isArray(parsed)) return { filePath, datasetKey: datasetKey || 'words', words: parsed };
  const key = datasetKey || Object.keys(parsed)[0];
  return { filePath, datasetKey: key, words: parsed[key] };
}

function saveDataset(filePath, datasetKey, words) {
  const payload = { [datasetKey]: words };
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

function audioViPath(wordId) {
  return `audio/vi/${wordId}.mp3`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function base64url(value) {
  return Buffer.from(value).toString('base64url');
}

async function getGoogleAccessToken() {
  if (process.env.GOOGLE_TTS_ACCESS_TOKEN) return process.env.GOOGLE_TTS_ACCESS_TOKEN;

  const credentialsPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (!credentialsPath || !fs.existsSync(credentialsPath)) {
    throw new Error('Set GOOGLE_TTS_ACCESS_TOKEN or GOOGLE_APPLICATION_CREDENTIALS for Google Cloud TTS.');
  }

  const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
  const now = Math.floor(Date.now() / 1000);
  const header = base64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claim = base64url(JSON.stringify({
    iss: credentials.client_email,
    scope: 'https://www.googleapis.com/auth/cloud-platform',
    aud: 'https://oauth2.googleapis.com/token',
    exp: now + 3600,
    iat: now,
  }));
  const signInput = `${header}.${claim}`;
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(signInput);
  signer.end();
  const signature = signer.sign(credentials.private_key, 'base64url');
  const assertion = `${signInput}.${signature}`;

  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion,
    }),
  });
  if (!response.ok) {
    throw new Error(`Google auth failed (${response.status}).`);
  }
  const payload = await response.json();
  if (!payload.access_token) throw new Error('Google auth returned no access token.');
  return payload.access_token;
}

async function synthesizeWithGoogle(text) {
  const accessToken = await getGoogleAccessToken();
  const response = await fetch('https://texttospeech.googleapis.com/v1/text:synthesize', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: { text },
      voice: { languageCode: 'vi-VN', name: GOOGLE_VOICE },
      audioConfig: { audioEncoding: 'MP3', speakingRate: 0.95 },
    }),
  });
  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Google TTS failed (${response.status}): ${details}`);
  }
  const payload = await response.json();
  if (!payload.audioContent) throw new Error('Google TTS returned empty audio.');
  return Buffer.from(payload.audioContent, 'base64');
}

async function synthesizeWithFpt(text) {
  const apiKey = process.env.FPT_AI_API_KEY;
  if (!apiKey) throw new Error('Set FPT_AI_API_KEY for FPT.AI TTS.');
  const response = await fetch('https://api.fpt.ai/hmi/tts/v5', {
    method: 'POST',
    headers: {
      'api-key': apiKey,
      voice: FPT_VOICE,
      speed: FPT_SPEED,
      'Content-Type': 'text/plain; charset=utf-8',
    },
    body: text,
  });
  if (!response.ok) throw new Error(`FPT TTS failed (${response.status}).`);
  const payload = await response.json();
  if (payload.error !== 0 || !payload.async) {
    throw new Error(`FPT TTS error: ${payload.message || 'unknown error'}`);
  }
  const audioResponse = await fetch(payload.async);
  if (!audioResponse.ok) throw new Error(`FPT audio download failed (${audioResponse.status}).`);
  return Buffer.from(await audioResponse.arrayBuffer());
}

async function synthesize(text, provider) {
  if (provider === 'fpt') return synthesizeWithFpt(text);
  return synthesizeWithGoogle(text);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const dataset = DATASETS[args.dataset];
  if (!dataset) {
    throw new Error(`Unknown dataset "${args.dataset}". Available: ${Object.keys(DATASETS).join(', ')}`);
  }

  fs.mkdirSync(AUDIO_VI_DIR, { recursive: true });

  const source = loadDataset(dataset.files[0], dataset.key);
  let created = 0;
  let skipped = 0;
  let updatedPaths = 0;

  for (const word of source.words) {
    const relativePath = audioViPath(word.id);
    const absolutePath = path.join(ROOT, relativePath);
    const text = String(word.meaning_vi || '').trim();
    if (!text) {
      console.warn(`Skip ${word.id}: missing meaning_vi`);
      continue;
    }

    if (word.audio_vi !== relativePath) {
      word.audio_vi = relativePath;
      updatedPaths += 1;
    }

    if (args.pathsOnly) continue;

    if (!args.force && fs.existsSync(absolutePath)) {
      skipped += 1;
      continue;
    }

    if (args.dryRun) {
      console.log(`Would synthesize ${word.id}: ${text}`);
      continue;
    }

    console.log(`Synthesizing ${word.id}: ${text}`);
    const audio = await synthesize(text, args.provider);
    fs.writeFileSync(absolutePath, audio);
    created += 1;
    await sleep(args.provider === 'fpt' ? 250 : 120);
  }

  for (const filePath of dataset.files) {
    saveDataset(filePath, dataset.key, source.words);
  }

  console.log(`Dataset: ${args.dataset}`);
  console.log(`Updated audio_vi paths: ${updatedPaths}`);
  if (args.pathsOnly) {
    console.log('Paths-only mode: skipped audio synthesis.');
    return;
  }
  console.log(`Created: ${created}, skipped existing: ${skipped}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
