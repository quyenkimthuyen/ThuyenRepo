# VietNamSpeak

VietNamSpeak helps Vietnamese learners master English pronunciation through this loop:

English Word -> IPA -> Vietnamese Pronunciation Hint -> Audio -> Speaking Practice -> Gamified Reinforcement

## MVP Features

- Next.js App Router, React, TypeScript strict mode, TailwindCSS, shadcn-style UI primitives.
- Rule-based IPA to Vietnamese pronunciation conversion engine with prioritized multi-character phoneme matching.
- IPA Visualizer that explains each IPA token.
- Word learning flow with IPA, Vietnamese hint, meaning, examples, listen, slow listen, record, replay, and compare feedback.
- IPA Learning Center, Pronunciation Rule Library, Daily Challenge, and IPA Adventure game.
- Browser-first audio: `SpeechSynthesisUtterance`, `MediaRecorder`, and optional browser speech recognition.
- Supabase schema, seed data, and RLS policies for production persistence.
- Vitest unit tests, Playwright E2E smoke test, Dockerfile, and GitHub Actions CI.

## Local Setup

Install Node.js 22 or newer, then:

```bash
npm install
npm run dev
```

Copy `.env.example` to `.env.local` and fill Supabase values when connecting to a real project.

## Quality Commands

```bash
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

## Supabase Setup

1. Create a Supabase project.
2. Run `supabase/migrations/202605310001_initial_schema.sql`.
3. Run `supabase/seed.sql`.
4. Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

The MVP uses public read access for learning content and RLS-protected rows for user progress, favorites, and game sessions.

## Deployment

### Vercel

1. Import the parent repository.
2. Set the project root to `VietNamSpeak`.
3. Add environment variables from `.env.example`.
4. Deploy with the default Next.js preset.

### Docker

```bash
docker build -t vietnam-speak .
docker run -p 3000:3000 --env-file .env.local vietnam-speak
```

## Follow-Up Phases

- Add Azure Speech Assessment for phoneme-level scoring.
- Build the full admin panel for CSV/JSON import and audio upload.
- Add teacher/classroom dashboards and realtime challenge modes.
- Replace local seed reads with generated Supabase types and live queries.
