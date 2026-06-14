/**
 * Đọc Cursor API key — ưu tiên env, sau đó file key.txt
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SERVER_DIR = path.dirname(fileURLToPath(import.meta.url));

export function resolveApiKeyFileCandidates(projectRoot) {
  return [
    process.env.CURSOR_KEY_FILE,
    path.join(SERVER_DIR, 'key.txt'),
    path.join(projectRoot, 'server', 'key.txt'),
    '/home/toc/thuyen/repo/CognitiveOperationSystem/server/key.txt',
  ].filter(Boolean);
}

export function loadApiKey(projectRoot) {
  const fromEnv = (process.env.CURSOR_API_KEY || '').trim();
  if (fromEnv) return fromEnv;

  for (const file of resolveApiKeyFileCandidates(projectRoot)) {
    try {
      const raw = fs.readFileSync(file, 'utf8').trim();
      const key = raw
        .split('\n')
        .map((line) => line.trim())
        .find((line) => line && !line.startsWith('#'));
      if (key) return key;
    } catch {
      /* thử file tiếp theo */
    }
  }
  return null;
}
