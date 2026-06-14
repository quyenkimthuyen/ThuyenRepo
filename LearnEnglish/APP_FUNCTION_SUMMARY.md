# LexiRise App Function Summary

LexiRise is a standalone, frontend-only vocabulary app. The app UI runs from `index.html`, while vocabulary words are loaded dynamically from JSON files in the `data/` folder. It does not need Vite, React, npm, backend API, authentication, or a database.

## How To Use

1. Open the folder through a simple static server so the browser can read `data/*.json`.
2. Study, quiz, and track progress.

The app has no visible JSON load/export buttons. Browser progress is saved in `localStorage`.

Optional start command:

```bash
npm start
```

## Topic JSON Files

Words are stored in `data/` as consolidated source files. The Stats page settings let the user choose which source file to load.

Current source files:

- `data/all-topics-toeic.json`
- `data/all-topics-grade9.json`
- `data/all-topics-grade4.json`
- `data/all-topics-american-ipa.json`
- `data/all-topics-english-dictation.json`

Topic file example:

Example:

```json
{
  "id": "word-001",
  "word": "abandon",
  "ipa_us": "/əˈbæn.dən/",
  "ipa_uk": "/əˈbæn.dən/",
  "meaning_vi": "từ bỏ",
  "topic": "toeic-airport",
  "example": "She refused to abandon her dream.",
  "audio_us": "https://api.dictionaryapi.dev/media/pronunciations/en/abandon-us.mp3",
  "audio_vi": "audio/vi/word-001.mp3",
  "status": "new",
  "reviewLevel": 0,
  "reviewCount": 0,
  "createdAt": 1771142156378
}
```

Important fields:

- `word`: English word.
- `meaning_vi`: Vietnamese meaning.
- `topic`: learning topic; if omitted, the app uses the source group name.
- `audio_us`: optional audio path or internet URL, such as `audio/word.mp3` or a public `.mp3` URL.
- `audio_vi`: optional local Vietnamese meaning audio path, such as `audio/vi/g4-0001.mp3`.
- `example`: optional example sentence.
- `ipa_us`: optional American pronunciation text.

Put local audio files in the `audio/` folder or use public internet audio URLs in topic JSON files under `data/`. If `audio_us` is empty or cannot play, the app falls back to browser text-to-speech. Vietnamese meaning audio uses `audio_vi` when present; otherwise Auto Audio Learning falls back to browser Vietnamese text-to-speech.

Grade 4 Vietnamese audio can be generated once with `npm run generate:audio-vi:grade4`. See `data/generate/README-vietnamese-audio.md`.

The American IPA source includes pronunciation topics for US IPA symbols, Vietnamese-friendly reading approximations, spelling-to-sound patterns, final consonants, stress and reduction, common Vietnamese pronunciation mistakes, and guided steps for reading new English words from IPA.

The English Dictation source includes listening-to-spelling topics for Vietnamese learners: short and long vowels, diphthongs, final consonants, consonant clusters, th/sh/ch/j sounds, silent letters, and common difficult words.

To add another source, add the JSON file in `data/` and register it in the app's `DATA_SOURCES` list.

## Main Functions

### Learn Vocabulary

- Shows a vocabulary learning screen.
- Keeps JSON source/import instructions out of the main learning GUI.
- Loads words from the selected source file.
- Lets the user filter vocabulary by topic.
- Limits the active learning queue to 10 words.
- Shows words in a stable randomized order instead of JSON order.
- Displays English word, American IPA, Vietnamese meaning, and example sentence when available.
- Lets the user reveal or hide the meaning.
- Plays `audio_us` from a compact pronunciation button in the card action row, otherwise uses browser speech synthesis.
- Provides Auto Audio Learning for the selected topic: the app loops through every topic word, plays the Vietnamese meaning from `audio_vi` when available (otherwise browser Vietnamese speech), then plays the English audio or speech fallback while showing the current English word.
- Hides `Forgot` on learning words and hides `Remembered` on known words.
- Lets the user mark eligible words as `Remembered` or `Forgot`, then reshuffles the word order.
- Refills the learning queue with new words after remembered words become known.

### Search And Filter

- Searches by English word, Vietnamese meaning, or IPA.
- Searches by topic name.
- Keeps focus in the search box while typing.
- Filters words by topic, including `toeic words`.
- Filters words by status: `Learning`, `Known`, or `All Status`.
- In `All Status`, shows each word's quiz attempt count and correct percentage when that word has been tested.
- Saves the selected filter and search query locally.

### Quiz Practice

Quiz modes:

- Meaning: shows the English word and asks for the Vietnamese meaning.
- English: shows the Vietnamese meaning and asks for the English word.
- Listen: plays `audio_us` or text-to-speech and asks for the Vietnamese meaning.
- Typing: shows the Vietnamese meaning and asks the user to type the answer.
- Dictation: plays `audio_us` or text-to-speech and asks the user to type the English word they hear.

Quiz behavior:

- Shows the selected quiz topic on the quiz screen and lets the user change it before starting.
- Builds each test from the configured number of unique words in the selected topic, or all available words when the topic has fewer words.
- Prioritizes words with fewer quiz attempts and lower correct rates, then shuffles a shortlist so each quiz still has variety.
- Uses multiple-choice answers for non-typing modes, with up to four choices depending on the topic size.
- Compares answers case-insensitively after trimming whitespace.
- Automatically advances to the next question after a correct answer.
- Automatically submits typing answers when the typed text matches the correct English word.
- Keeps the typing input value and focus when replaying audio in Typing and Dictation.
- In Typing and Dictation, each Hint tap reveals two more letters of the answer (capped at the full word length).
- In Typing and Dictation, each revealed hint letter reduces the question score proportionally. For example, an 8-letter word with 2 letters revealed from hints earns 6/8 of a point when answered correctly.
- Quiz score and accuracy use weighted points in Typing and Dictation, while other modes still award full points for each correct answer.
- Automatically plays the word audio or speech fallback when a Listen or Dictation question first appears.
- Limits manual Play taps in Listen and Dictation to one play every 2 seconds to avoid repeated audio spam.
- Tracks total answers, correct answers, weighted score, streak, elapsed time, and accuracy.
- Records per-word quiz attempt count and correct count for display on the Learn screen.
- Shows a quiz result summary after the final question, including correct count, wrong count, accuracy, elapsed time, and each question's selected/correct answer.
- Supports quiz reset.

### Progress And Stats

- Shows total word count.
- Shows known word count.
- Shows learning word count.
- Shows scheduled review count.
- Shows completion percentage with a progress bar.
- Shows recently known words.
- Shows the current learning queue.
- Shows stats for the selected topic or all topics.
- Lets the user choose the vocabulary source: TOEIC, Grade 9, Grade 4, American IPA, or English Dictation.
- Lets the user set the number of words used in each quiz.
- Saves source and quiz-size preferences locally.
- Provides a reset button to clear saved browser progress and reload fresh data from `data/`.

## Data And Storage

Editable source data:

- consolidated JSON source files in `data/`

Optional audio files:

- `audio/`

Browser storage key:

- `lexirise-vocabulary-store`

Persisted data:

- vocabulary words
- Vietnamese meanings
- topics
- audio paths
- review progress
- per-word quiz attempt count and correct count
- selected filter
- selected topic filter
- search query
- selected theme
- selected vocabulary source
- quiz word count
- selected quiz mode

Not persisted:

- current quiz question
- current quiz results
- quiz timer
- temporary card reveal state

## Current File Structure

- `index.html`: standalone app UI and logic.
- `data/*.json`: source vocabulary files.
- `data/README.md`: topic data instructions.
- `audio/`: optional local audio files.
- `APP_FUNCTION_SUMMARY.md`: this function summary.
- `package.json`: optional metadata only.
- `.cursor/rules/`: project rules for future AI changes.

## Limitations

- Browsers do not allow reliable JSON loading from `file://`; use a simple static server.
- Extra source files must be added to the app's `DATA_SOURCES` list.
- There is no backend sync between devices.
- Progress is stored only in the current browser unless exported.
- Audio playback requires valid local paths or public internet URLs in `audio_us`.
