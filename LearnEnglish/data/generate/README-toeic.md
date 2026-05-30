# TOEIC Basic English Premium Dataset

This dataset contains TOEIC-oriented workplace English vocabulary and collocations for use in a production learning app. It follows the same app-ready structure as the Grade 3/4/5 datasets, but the content is aimed at adult and young-adult TOEIC learners.

## Files

- `toeic-basic-english-premium.json`: 800 TOEIC vocabulary entries.
- `validate-toeic.js`: Validation script for required fields, duplicate IDs, duplicate words, duplicate examples, IPA shape, URL format, topics, CEFR levels, and basic example quality.
- `README-toeic.md`: Documentation and maintenance guide.

## Topics

The dataset covers 20 TOEIC contexts:

`office`, `meetings`, `communication`, `scheduling`, `travel`, `transportation`, `hospitality`, `dining`, `shopping`, `finance`, `banking`, `accounting`, `sales`, `marketing`, `human-resources`, `training`, `operations`, `manufacturing`, `technology`, and `shipping`.

## JSON Structure

```json
{
  "toeic-basic-english-premium": [
    {
      "id": "toeic-0001",
      "word": "annual report",
      "ipa_us": "/ˈænjuəl rɪˈpɔːrt/",
      "meaning_vi": "báo cáo hằng năm",
      "example": "The manager reviewed the annual report before the meeting.",
      "topic": "office",
      "cefr_level": "B1",
      "difficulty": 2
    }
  ]
}
```

The full records also include app review fields, `createdAt`, `audio_us`, and `image_keyword`.

## Validation

Run:

```bash
node validate-toeic.js
```

The validator prints summary statistics, warnings, and errors. Errors should be fixed before using the file in production.

## Quality Rules

- Keep entries practical for TOEIC Listening and Reading contexts.
- Prefer business collocations such as `annual report`, `confirmed reservation`, and `delayed shipment`.
- Use real IPA notation, not spelling inside slashes.
- Use natural workplace examples with correct grammar and punctuation.
- Avoid duplicate vocabulary items and duplicate example sentences.
- Keep CEFR levels around `B1` to `B2` for general TOEIC preparation.
