# Vietnamese Audio Generation

Generate consistent Vietnamese MP3 files for vocabulary meanings using Google Cloud TTS or FPT.AI.

## Output

- Audio files: `audio/vi/{word-id}.mp3`
- JSON field: `audio_vi: "audio/vi/{word-id}.mp3"`

Currently supported dataset:

- `grade4` → `data/all-topics-grade4.json` and `data/generate/grade4-basic-english-premium.json`

## Setup

No extra npm packages are required. The script uses Node.js `fetch` and the Google Cloud Text-to-Speech REST API.

### Google Cloud TTS (recommended)

1. Enable **Cloud Text-to-Speech API** in your Google Cloud project.
2. Create a service account JSON key.
3. Export credentials:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GOOGLE_TTS_VOICE=vi-VN-Neural2-D
```

Or pass a short-lived access token directly:

```bash
export GOOGLE_TTS_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"
```

### FPT.AI TTS (alternative)

```bash
export TTS_PROVIDER=fpt
export FPT_AI_API_KEY=your-api-key
export FPT_TTS_VOICE=banmai
```

## Usage

Update JSON paths only (no API call):

```bash
npm run generate:audio-vi:grade4 -- --paths-only
```

Generate missing MP3 files for Grade 4:

```bash
npm run generate:audio-vi:grade4
```

Force regenerate all files:

```bash
npm run generate:audio-vi:grade4 -- --force
```

Use FPT.AI instead of Google:

```bash
npm run generate:audio-vi:grade4 -- --provider fpt
```

Dry run:

```bash
npm run generate:audio-vi:grade4 -- --dry-run
```

## App behavior

Auto Audio Learning plays `audio_vi` first when available. If the file is missing or cannot play, the app falls back to browser Vietnamese text-to-speech.
