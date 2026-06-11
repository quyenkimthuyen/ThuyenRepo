/**
 * Cursor AI proxy — chạy local khi dev
 *
 * export CURSOR_API_KEY="cursor_..."   # Cursor Dashboard → Integrations
 * npm install && npm start
 */

import cors from 'cors';
import express from 'express';
import { Agent, CursorAgentError } from '@cursor/sdk';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.AI_SERVER_PORT || 3001);
const PROJECT_ROOT = path.resolve(__dirname, '..');

const FLOW_STEPS = [
  'Event',
  'Emotion',
  'Interpretation',
  'Belief',
  'Value',
  'Identity',
  'Action',
];

const app = express();
app.use(
  cors({
    origin: true,
    methods: ['GET', 'POST', 'OPTIONS'],
  })
);
app.use(express.json({ limit: '512kb' }));

function parseJsonFromText(text) {
  if (!text) throw new Error('Empty AI response');
  const trimmed = String(text).trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    /* continue */
  }
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) return JSON.parse(fenced[1].trim());
  const start = trimmed.indexOf('{');
  const end = trimmed.lastIndexOf('}');
  if (start >= 0 && end > start) {
    return JSON.parse(trimmed.slice(start, end + 1));
  }
  throw new Error('AI response is not valid JSON');
}

function buildPrompt({ message, session, locale, phase }) {
  const isVi = locale !== 'en';
  const history = (session?.messages || [])
    .slice(-12)
    .map((m) => `${m.role === 'user' ? 'User' : 'Guide'}: ${m.content}`)
    .join('\n');

  const langNote = isVi
    ? 'Trả lời bằng tiếng Việt, giọng ấm áp, không phán xét.'
    : 'Respond in English, warm and non-judgmental tone.';

  return `You are a reflection guide in the app "Nhìn lại suy nghĩ" (Cognitive OS).
${langNote}

Framework EEIBVIA steps: ${FLOW_STEPS.join(' → ')}
Current step: ${session?.flowStep || 'Event'}
Phase: ${phase}
Initial thought: ${session?.initialThought || ''}

Conversation so far:
${history || '(none)'}

Latest user message:
${message}

Rules:
- Do NOT use tools, do NOT read files, do NOT write code.
- Only output a single JSON object, no markdown outside JSON.
- Ask ONE reflective follow-up question in "nextQuestion" (empathic, specific to user words).
- Advance "flowStep" along EEIBVIA when appropriate.
- Set "sessionEnd": true only after Action step has been explored enough (usually 6+ user turns).

JSON schema:
{
  "flowStep": "Emotion|Interpretation|Belief|Value|Identity|Action",
  "nextQuestion": "string",
  "sessionEnd": false,
  "extracted": {
    "emotions": ["string"],
    "interpretation": "string or null",
    "beliefs": ["string"],
    "values": ["string"],
    "identity": ["string"],
    "actions": ["string"]
  }
}`;
}

function normalizeResponse(raw, session) {
  const flowStep = FLOW_STEPS.includes(raw?.flowStep)
    ? raw.flowStep
    : session?.flowStep || 'Emotion';

  return {
    flowStep,
    nextQuestion: String(raw?.nextQuestion || '').trim() || null,
    sessionEnd: Boolean(raw?.sessionEnd),
    extracted: {
      emotions: Array.isArray(raw?.extracted?.emotions) ? raw.extracted.emotions : [],
      interpretation: raw?.extracted?.interpretation || null,
      beliefs: Array.isArray(raw?.extracted?.beliefs) ? raw.extracted.beliefs : [],
      values: Array.isArray(raw?.extracted?.values) ? raw.extracted.values : [],
      identity: Array.isArray(raw?.extracted?.identity) ? raw.extracted.identity : [],
      actions: Array.isArray(raw?.extracted?.actions) ? raw.extracted.actions : [],
    },
  };
}

app.get('/api/health', (_req, res) => {
  res.json({
    ok: true,
    hasKey: Boolean(process.env.CURSOR_API_KEY),
    model: process.env.CURSOR_MODEL || 'composer-2.5',
  });
});

app.post('/api/reflect', async (req, res) => {
  const apiKey = process.env.CURSOR_API_KEY;
  if (!apiKey) {
    return res.status(503).json({
      error: 'CURSOR_API_KEY not set',
      hint: 'Create a key at Cursor Dashboard → Integrations, then export CURSOR_API_KEY',
    });
  }

  const { message, session, locale = 'vi', phase = 'continue' } = req.body || {};
  if (!message || typeof message !== 'string') {
    return res.status(400).json({ error: 'message is required' });
  }

  const prompt = buildPrompt({ message, session, locale, phase });
  const modelId = process.env.CURSOR_MODEL || 'composer-2.5';

  try {
    const result = await Agent.prompt(prompt, {
      apiKey,
      model: { id: modelId },
      local: {
        cwd: PROJECT_ROOT,
        settingSources: [],
      },
    });

    if (result.status === 'error') {
      return res.status(502).json({ error: 'Cursor agent run failed', runId: result.id });
    }

    const parsed = parseJsonFromText(result.result);
    return res.json(normalizeResponse(parsed, session));
  } catch (err) {
    if (err instanceof CursorAgentError) {
      return res.status(502).json({
        error: err.message,
        retryable: err.isRetryable,
      });
    }
    console.error('[reflect-server]', err);
    return res.status(500).json({ error: err.message || 'Unknown error' });
  }
});

app.listen(PORT, () => {
  console.log(`[reflect-server] http://localhost:${PORT}`);
  console.log(`[reflect-server] CURSOR_API_KEY: ${process.env.CURSOR_API_KEY ? 'set' : 'MISSING'}`);
});
