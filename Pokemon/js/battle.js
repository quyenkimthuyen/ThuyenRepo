const challengeTypes = [
  "meaningToWord",
  "wordToMeaning",
  "audioToImage",
  "imageToWord",
  "spelling",
  "pronunciation"
];

export class BattleSystem {
  constructor(vocabulary, audio, callbacks) {
    this.vocabulary = vocabulary;
    this.audio = audio;
    this.callbacks = callbacks;
    this.activeWordmon = null;
    this.activeChallenge = null;
    this.boss = null;
  }

  startEncounter(wordmon) {
    this.activeWordmon = wordmon;
    this.activeChallenge = this.createChallenge(wordmon);
    this.callbacks.onEncounterOpen(wordmon, this.activeChallenge);
    window.setTimeout(() => this.audio.speak(wordmon.word), 250);
  }

  answerEncounter(answer, button) {
    if (!this.activeChallenge || !this.activeWordmon) return;
    const correct = answer === this.activeChallenge.correct;
    this.callbacks.onChallengeResult(correct, this.activeWordmon, button);
    this.activeChallenge = null;
    this.activeWordmon = null;
  }

  startBoss() {
    this.boss = { hp: 5, maxHp: 5 };
    const challenge = this.createChallenge(this.randomWord());
    this.callbacks.onBossOpen(this.boss, challenge);
    this.activeChallenge = challenge;
    this.audio.speak(challenge.word.word);
  }

  answerBoss(answer, button) {
    if (!this.boss || !this.activeChallenge) return;
    const correct = answer === this.activeChallenge.correct;
    if (correct) {
      this.boss.hp -= 1;
      this.audio.play("correct");
    } else {
      this.audio.play("wrong");
    }
    this.callbacks.onBossResult(correct, this.boss, button);

    if (this.boss.hp <= 0) {
      this.callbacks.onBossWin();
      this.boss = null;
      this.activeChallenge = null;
      return;
    }

    this.activeChallenge = this.createChallenge(this.randomWord());
    window.setTimeout(() => {
      this.callbacks.onBossNext(this.boss, this.activeChallenge);
      this.audio.speak(this.activeChallenge.word.word);
    }, 700);
  }

  createChallenge(wordmon) {
    const type = challengeTypes[Math.floor(Math.random() * challengeTypes.length)];
    const distractors = this.getDistractors(wordmon, 3);
    const options = shuffle([wordmon, ...distractors]);

    if (type === "meaningToWord") {
      return {
        type,
        word: wordmon,
        prompt: wordmon.meaning_vi,
        help: "Choose the English word.",
        options: options.map((entry) => ({ label: entry.word, value: entry.word })),
        correct: wordmon.word
      };
    }

    if (type === "wordToMeaning") {
      return {
        type,
        word: wordmon,
        prompt: wordmon.word,
        help: "Choose the Vietnamese meaning.",
        options: options.map((entry) => ({ label: entry.meaning_vi, value: entry.meaning_vi })),
        correct: wordmon.meaning_vi
      };
    }

    if (type === "audioToImage") {
      return {
        type,
        word: wordmon,
        prompt: "🔊 Listen and choose the picture.",
        help: "Audio → Image",
        options: options.map((entry) => ({ label: entry.image, subLabel: entry.name, value: entry.image, image: true })),
        correct: wordmon.image,
        autoAudio: true
      };
    }

    if (type === "imageToWord") {
      return {
        type,
        word: wordmon,
        prompt: wordmon.image,
        help: "Image → Word",
        options: options.map((entry) => ({ label: entry.word, value: entry.word })),
        correct: wordmon.word
      };
    }

    if (type === "spelling") {
      const missingIndex = Math.max(1, Math.floor(wordmon.word.length / 2));
      const prompt = `${wordmon.word.slice(0, missingIndex)} _ ${wordmon.word.slice(missingIndex + 1)}`;
      const letters = shuffle([wordmon.word[missingIndex], ..."abcdefghijklmnopqrstuvwxyz".split("").filter((letter) => !wordmon.word.includes(letter)).slice(0, 3)]);
      return {
        type,
        word: wordmon,
        prompt,
        help: "Select the missing letter.",
        options: letters.map((letter) => ({ label: letter, value: letter })),
        correct: wordmon.word[missingIndex]
      };
    }

    return {
      type,
      word: wordmon,
      prompt: wordmon.word,
      help: "Choose the correct pronunciation.",
      options: shuffle([
        { label: "🔊 Sound A", value: wordmon.word, sound: wordmon.word },
        { label: "🔊 Sound B", value: distractors[0].word, sound: distractors[0].word },
        { label: "🔊 Sound C", value: distractors[1].word, sound: distractors[1].word },
        { label: "🔊 Sound D", value: distractors[2].word, sound: distractors[2].word }
      ]),
      correct: wordmon.word,
      pronunciation: true
    };
  }

  getDistractors(wordmon, count) {
    return shuffle(this.vocabulary.filter((entry) => entry.id !== wordmon.id)).slice(0, count);
  }

  randomWord() {
    return this.vocabulary[Math.floor(Math.random() * this.vocabulary.length)];
  }
}

export function shuffle(items) {
  return [...items].sort(() => Math.random() - 0.5);
}
