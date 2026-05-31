# Deployment Guide

## Supabase

Create a Supabase project, then run:

```bash
supabase db push
supabase db reset
```

If you are not using the Supabase CLI, apply the SQL files manually:

- `supabase/migrations/202605310001_initial_schema.sql`
- `supabase/seed.sql`

## Environment Variables

Required:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Server-only:

- `SUPABASE_SERVICE_ROLE_KEY`

Future integrations:

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `GOOGLE_TTS_API_KEY`

## Vercel

Set the Vercel project root to `VietNamSpeak`, add the environment variables, and deploy with the Next.js preset.

## Docker

```bash
docker build -t vietnam-speak .
docker run -p 3000:3000 --env-file .env.local vietnam-speak
```

## Performance Checklist

- Keep browser-only speech components behind `"use client"`.
- Prefer static content for public word/rule pages.
- Move large future audio files to Supabase Storage or a CDN.
- Use generated Supabase types once the remote schema is stable.
