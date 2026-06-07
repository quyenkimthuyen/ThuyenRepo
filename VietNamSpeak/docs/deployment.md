# Deployment Guide

## Static Build

Build the frontend:

```bash
npm run build
```

The generated static site is written to `out/`.

## Environment Variables

No environment variables are required for the static frontend MVP.

## Vercel

Set the Vercel project root to `VietNamSpeak` and deploy with the default Next.js preset.

## Static Hosting

Upload `out/` to any static host such as Netlify, Cloudflare Pages, GitHub Pages, or an nginx server.

## Local Preview

```bash
npm run build
npm start
```

## VS Code Live Server

Build the static files, then open `out/index.html` with Live Server:

```bash
npm run build
```

The workspace Live Server root is configured as `out/`, so `/_next` assets and static routes are served from the generated frontend output.

## Docker

```bash
docker build -t vietnam-speak .
docker run -p 3000:80 vietnam-speak
```

## Performance Checklist

- Keep browser-only speech components behind `"use client"`.
- Prefer static content for public word/rule pages.
- Move large future audio files to a CDN.
- Add a backend only if synced accounts, progress, or teacher dashboards become required.
