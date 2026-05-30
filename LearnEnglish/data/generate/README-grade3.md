# Grade 3 Basic English Premium Dataset

This project contains a curated English vocabulary dataset for Vietnamese Grade 3 learners in Ho Chi Minh City. It follows the same production-ready structure as the Grade 4 dataset and is suitable for flashcards, spaced repetition, pronunciation practice, quizzes, AI tutors, and children's learning games.

## Files

- `grade3-basic-english-premium.json`: 200 vocabulary entries across school, family, animals, food, colors, activities, weather, transportation, body, clothes, sports, house, nature, jobs, daily routines, friends, hobbies, places, and time.
- `validate-grade3.js`: Node.js validation script for structure, duplicates, IPA shape, audio URL format, grammar patterns, and repeated example templates.
- `README-grade3.md`: Dataset documentation and maintenance guide.

## Dataset Structure

The JSON file uses one top-level key:

```json
{
  "grade3-basic-english-premium": [
    {
      "id": "g3-0001",
      "word": "teacher",
      "ipa_us": "/ˈtiːtʃɚ/",
      "meaning_vi": "giáo viên",
      "example": "My teacher helps us learn new things.",
      "status": "new",
      "reviewLevel": 0,
      "reviewCount": 0,
      "createdAt": 1779703568473,
      "audio_us": "https://api.dictionaryapi.dev/media/pronunciations/en/teacher-us.mp3",
      "topic": "school",
      "cefr_level": "A1",
      "difficulty": 1,
      "image_keyword": "teacher classroom school"
    }
  ]
}
```

## Schema Explanation

- `id`: Stable unique ID in `g3-0001` format.
- `word`: English headword suitable for Grade 3 learners.
- `ipa_us`: US pronunciation in real IPA notation.
- `meaning_vi`: Vietnamese meaning written for children and parents.
- `example`: Natural, child-friendly English sentence with correct grammar.
- `status`, `reviewLevel`, `reviewCount`: App-ready spaced repetition fields.
- `createdAt`: Unix timestamp in milliseconds.
- `audio_us`: DictionaryAPI-style US pronunciation URL.
- `topic`: Curriculum topic bucket.
- `cefr_level`: Grade 3 entries are kept at `A1`.
- `difficulty`: 1 for core beginner words and 2 for slightly harder but still visual words.
- `image_keyword`: Search phrase for image generation or asset lookup.

## Generation Steps

1. Build a vocabulary pool from Grade 3 daily-life and school themes.
2. Categorize each word by topic.
3. Write varied examples using actions, routines, descriptions, questions, observations, and school situations.
4. Check IPA manually against common US pronunciations.
5. Run validation for required fields, duplicates, grammar patterns, URL format, and template repetition.
6. Export the JSON with `JSON.stringify(data, null, 2)` and UTF-8 encoding.

## Validation Usage

Run the validator with Node.js:

```bash
node validate-grade3.js
```

The script prints summary statistics plus warnings and errors. Errors should be fixed before shipping. Warnings usually mean a human should review the entry, especially for IPA or example similarity.

## How To Add New Words

1. Add a new object to `grade3-basic-english-premium.json` with the next sequential ID.
2. Use a real IPA transcription, not a spelling wrapped in slashes.
3. Write a fresh example sentence that is natural and useful for children.
4. Keep the topic from the required topic list unless the app schema is updated.
5. Use a CEFR level of `A1` for Grade 3.
6. Run `node validate-grade3.js` and resolve all errors.

## Quality Rules

- Do not use fake IPA such as `/teacher/` or `/school/`.
- Avoid repetitive openings like `I like ...`, `I can see ...`, and `This is my ...`.
- Do not use ungrammatical examples such as `I can see a homework` or `I like read`.
- Prefer concrete, visual, child-safe vocabulary.
- Keep examples realistic for Vietnamese Grade 3 students in school, home, and city life.
- Avoid duplicate words, duplicate examples, and near-identical sentence templates.
