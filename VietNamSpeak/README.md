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
- Static frontend export with local seed data and no required backend service.
- Vitest unit tests, Playwright E2E smoke test, and Dockerfile for static hosting.

## Local Setup

Install Node.js 22 or newer, then:

```bash
npm install
npm run dev
```

No environment variables are required for the static frontend MVP.

## Quality Commands

```bash
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

## Deployment

Build the static site:

```bash
npm run build
```

The generated frontend files are written to `out/`.

### Vercel

1. Import the parent repository.
2. Set the project root to `VietNamSpeak`.
3. Deploy with the default Next.js preset.

### Static Hosting

Upload the `out/` directory to any static host such as Netlify, Cloudflare Pages, GitHub Pages, or an nginx server.

### Local Preview

```bash
npm run build
npm start
```

### VS Code Live Server

```bash
npm run build
```

Open `out/index.html` with Live Server. The workspace config points Live Server at `out/` so static assets and routes resolve from the exported frontend root.

### Docker

```bash
docker build -t vietnam-speak .
docker run -p 3000:80 vietnam-speak
```

## Follow-Up Phases

- Add Azure Speech Assessment for phoneme-level scoring.
- Build the full admin panel for CSV/JSON import and audio upload.
- Add teacher/classroom dashboards and realtime challenge modes.
- Add an optional backend later if user accounts, synced progress, or teacher dashboards need persistence.
