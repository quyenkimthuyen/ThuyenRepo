# Sound Assets

To guarantee compatibility, zero latency, and offline support without the risk of missing asset files, all game sounds (gunshots, splash drops, bomb explosions, lasers, warnings, alarms, powerups, level-ups, victory fanfares, and defeat tones) are programmatically synthesized using the HTML5 **Web Audio API** inside `game.js`.

If you prefer to load pre-recorded audio files:
1. Place `.mp3` or `.wav` files in this directory.
2. Initialize them via standard JavaScript `new Audio('assets/sounds/filename.mp3')` or load them as array buffers using fetch and decodeAudioData in `game.js`.
