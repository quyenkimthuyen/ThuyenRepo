# Real Life English

Frontend-only English learning app based on the curriculum idea in `Note.txt`.
Open `index.html` with Live Server to run it.

## Architecture

- This is a pure HTML/CSS/JavaScript app.
- There is no React, Vite, Node server, backend, database, API server, or server-side rendering.
- Lesson content currently lives in `src/curriculum.js`.
- The UI logic lives in `src/app.js`.

## Run With Live Server

1. Install the VS Code/Cursor extension named `Live Server`.
2. Right-click `index.html`.
3. Choose `Open with Live Server`.

Do not open the file directly with `file://` because browser ES modules work best through Live Server.

## Content Editing

To add more lessons, edit `src/curriculum.js` using this structure:

```js
Level -> Topic -> Situation -> Common Sentences -> Useful Phrases -> Vocabulary -> Games
```

Keep the data practical and natural, following the rules in `Note.txt`.
