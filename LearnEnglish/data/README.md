Store vocabulary topics in this folder.

Each topic has one JSON file, for example:

- `toeic-words.json`

When the app is served by a static server, it automatically loads the known `.json` topic files in this folder. If the server exposes directory listing, the app can also discover additional `.json` files automatically.

The topic name is the filename without `.json`, for example:

- `toeic-airport.json` becomes `toeic-airport`
- `toeic-business.json` becomes `toeic-business`

Each topic file contains an array of words. Add another topic by creating a new JSON file in this folder.

Consolidated source files used by the app include TOEIC, school-grade vocabulary, American IPA pronunciation practice, and English dictation practice. The IPA source (`all-topics-american-ipa.json`) groups American English vowel sounds, consonants, Vietnamese reading approximations, decoding rules, minimal pairs, common practice words, Vietnamese spelling-pattern drills, final-consonant practice, stress/reduction lessons, and common Vietnamese pronunciation mistakes. The dictation source (`all-topics-english-dictation.json`) groups listening-to-spelling drills for Vietnamese learners, including short vowels, long vowels, final consonants, consonant clusters, silent letters, and common difficult words.
