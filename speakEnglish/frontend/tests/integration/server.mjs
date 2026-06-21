/**
 * Spawn/stop backend cho integration & E2E tests
 */

import { spawn } from 'node:child_process';
import { access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const BACKEND_DIR = path.join(ROOT, 'backend');

export function repoRoot() {
  return ROOT;
}

async function pathExists(p) {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

export async function resolvePython() {
  const venvPy = path.join(BACKEND_DIR, '.venv/bin/python');
  if (await pathExists(venvPy)) return venvPy;
  const venvPyWin = path.join(BACKEND_DIR, '.venv/Scripts/python.exe');
  if (await pathExists(venvPyWin)) return venvPyWin;
  return 'python3';
}

export async function waitForHealth(baseUrl, timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs;
  let lastErr = '';
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${baseUrl}/api/v1/health`, { signal: AbortSignal.timeout(3000) });
      if (res.ok) return;
      lastErr = `HTTP ${res.status}`;
    } catch (e) {
      lastErr = e.message;
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`Backend not ready at ${baseUrl}: ${lastErr}`);
}

/**
 * @returns {Promise<{ proc: import('node:child_process').ChildProcess, baseUrl: string, port: number }>}
 */
export async function startBackend(port = null) {
  const listenPort = port ?? (18000 + Math.floor(Math.random() * 2000));
  const python = await resolvePython();
  const proc = spawn(
    python,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(listenPort)],
    { cwd: BACKEND_DIR, stdio: 'pipe', env: { ...process.env, PYTHONUNBUFFERED: '1' } },
  );

  const baseUrl = `http://127.0.0.1:${listenPort}`;

  proc.stderr?.on('data', (chunk) => {
    const msg = String(chunk);
    if (msg.includes('ERROR') || msg.includes('Error')) {
      process.stderr.write(`[backend] ${msg}`);
    }
  });

  try {
    await waitForHealth(baseUrl);
  } catch (e) {
    proc.kill('SIGTERM');
    throw e;
  }

  return { proc, baseUrl, port: listenPort };
}

export function stopBackend(server) {
  if (!server?.proc || server.proc.killed) return;
  server.proc.kill('SIGTERM');
}

/** WAV 16kHz mono sine — đủ lớn cho API evaluate */
export function createTestWavBuffer(durationSec = 0.6, sampleRate = 16000, freq = 440) {
  const numSamples = Math.floor(durationSec * sampleRate);
  const dataSize = numSamples * 2;
  const buf = Buffer.alloc(44 + dataSize);

  buf.write('RIFF', 0);
  buf.writeUInt32LE(36 + dataSize, 4);
  buf.write('WAVE', 8);
  buf.write('fmt ', 12);
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(sampleRate, 24);
  buf.writeUInt32LE(sampleRate * 2, 28);
  buf.writeUInt16LE(2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write('data', 36);
  buf.writeUInt32LE(dataSize, 40);

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;
    const sample = Math.sin(2 * Math.PI * freq * t) * 0.25;
    const int16 = Math.max(-32768, Math.min(32767, Math.floor(sample * 32767)));
    buf.writeInt16LE(int16, 44 + i * 2);
  }

  return buf;
}
