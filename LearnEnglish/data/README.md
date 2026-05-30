Store vocabulary topics in this folder.

Each topic has one JSON file, for example:

- `toeic-words.json`

When the app is served by a static server, it automatically loads the known `.json` topic files in this folder. If the server exposes directory listing, the app can also discover additional `.json` files automatically.

The topic name is the filename without `.json`, for example:

- `toeic-airport.json` becomes `toeic-airport`
- `toeic-business.json` becomes `toeic-business`

Each topic file contains an array of words. Add another topic by creating a new JSON file in this folder.
