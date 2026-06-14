/**
 * Cursor Bridge — HTTP API cục bộ cho app trình duyệt
 *
 * Cần: CURSOR_API_KEY trong môi trường, npm install trong thư mục server/
 * Chạy: npm start  (mặc định http://127.0.0.1:3847)
 */

import http from 'node:http';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const PORT = Number(process.env.CURSOR_BRIDGE_PORT || 3847);
const HOST = process.env.CURSOR_BRIDGE_HOST || '127.0.0.1';
const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

let Agent = null;
let sdkError = null;

try {
  ({ Agent } = await import('@cursor/sdk'));
} catch (err) {
  sdkError = err?.message || String(err);
}

/** @type {Map<string, { agent: import('@cursor/sdk').Agent, createdAt: number }>} */
const sessions = new Map();

const SESSION_TTL_MS = 4 * 60 * 60 * 1000;

function cors(res, req) {
  const origin = req.headers.origin || '*';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Max-Age', '86400');
}

function send(res, req, status, data) {
  cors(res, req);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > 2 * 1024 * 1024) {
        reject(new Error('payload_too_large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error('invalid_json'));
      }
    });
    req.on('error', reject);
  });
}

async function collectAssistantText(run) {
  let text = '';
  for await (const event of run.stream()) {
    if (event.type === 'assistant') {
      for (const block of event.message.content) {
        if (block.type === 'text') text += block.text;
      }
    }
  }
  await run.wait();
  if (!text && run.result) {
    text = String(run.result);
  }
  return text.trim();
}

async function createAgent() {
  if (!Agent) {
    throw new Error(sdkError || 'SDK not installed — run npm install in server/');
  }
  if (!process.env.CURSOR_API_KEY) {
    throw new Error('CURSOR_API_KEY is not set');
  }
  return Agent.create({
    apiKey: process.env.CURSOR_API_KEY,
    model: { id: process.env.CURSOR_MODEL || 'composer-2.5' },
    local: { cwd: PROJECT_ROOT },
  });
}

function purgeStaleSessions() {
  const now = Date.now();
  for (const [key, entry] of sessions) {
    if (now - entry.createdAt > SESSION_TTL_MS) {
      sessions.delete(key);
    }
  }
}

async function disposeSession(sessionKey) {
  const entry = sessions.get(sessionKey);
  if (!entry) return;
  sessions.delete(sessionKey);
  try {
    if (typeof entry.agent?.[Symbol.asyncDispose] === 'function') {
      await entry.agent[Symbol.asyncDispose]();
    }
  } catch {
    /* ignore cleanup errors */
  }
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    cors(res, req);
    res.writeHead(204);
    res.end();
    return;
  }

  purgeStaleSessions();

  const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);

  try {
    if (req.method === 'GET' && url.pathname === '/health') {
      send(res, req, 200, {
        ok: true,
        hasApiKey: Boolean(process.env.CURSOR_API_KEY),
        sdkReady: Boolean(Agent),
        sdkError: sdkError || null,
        port: PORT,
        activeSessions: sessions.size,
      });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/api/session/start') {
      const body = await readJson(req);
      const reflectionPrompt = (body.reflectionPrompt || '').trim();
      if (!reflectionPrompt) {
        send(res, req, 400, { ok: false, error: 'missing_prompt' });
        return;
      }

      const agent = await createAgent();
      const run = await agent.send(reflectionPrompt);
      const reply = await collectAssistantText(run);
      const sessionKey = `cs_${randomUUID().replace(/-/g, '').slice(0, 16)}`;
      sessions.set(sessionKey, { agent, createdAt: Date.now() });

      send(res, req, 200, { ok: true, sessionKey, reply });
      return;
    }

    const msgMatch = url.pathname.match(/^\/api\/session\/([^/]+)\/message$/);
    if (req.method === 'POST' && msgMatch) {
      const sessionKey = decodeURIComponent(msgMatch[1]);
      const entry = sessions.get(sessionKey);
      if (!entry) {
        send(res, req, 404, { ok: false, error: 'session_not_found' });
        return;
      }

      const body = await readJson(req);
      const content = (body.content || '').trim();
      if (!content) {
        send(res, req, 400, { ok: false, error: 'missing_content' });
        return;
      }

      const run = await entry.agent.send(content);
      const reply = await collectAssistantText(run);
      send(res, req, 200, { ok: true, reply });
      return;
    }

    const exportMatch = url.pathname.match(/^\/api\/session\/([^/]+)\/export$/);
    if (req.method === 'POST' && exportMatch) {
      const sessionKey = decodeURIComponent(exportMatch[1]);
      const entry = sessions.get(sessionKey);
      if (!entry) {
        send(res, req, 404, { ok: false, error: 'session_not_found' });
        return;
      }

      const body = await readJson(req);
      const exportPrompt = (body.exportPrompt || '').trim();
      if (!exportPrompt) {
        send(res, req, 400, { ok: false, error: 'missing_export_prompt' });
        return;
      }

      const run = await entry.agent.send(exportPrompt);
      const raw = await collectAssistantText(run);
      send(res, req, 200, { ok: true, raw });
      return;
    }

    const delMatch = url.pathname.match(/^\/api\/session\/([^/]+)$/);
    if (req.method === 'DELETE' && delMatch) {
      const sessionKey = decodeURIComponent(delMatch[1]);
      await disposeSession(sessionKey);
      send(res, req, 200, { ok: true });
      return;
    }

    send(res, req, 404, { ok: false, error: 'not_found' });
  } catch (err) {
    console.error('[cursor-bridge]', err);
    send(res, req, 500, {
      ok: false,
      error: 'server_error',
      message: err?.message || String(err),
    });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Cursor bridge listening on http://${HOST}:${PORT}`);
  console.log(`Project root: ${PROJECT_ROOT}`);
  if (!process.env.CURSOR_API_KEY) {
    console.warn('Warning: set CURSOR_API_KEY before chatting.');
  }
  if (sdkError) {
    console.warn('Warning: @cursor/sdk not loaded:', sdkError);
  }
});
