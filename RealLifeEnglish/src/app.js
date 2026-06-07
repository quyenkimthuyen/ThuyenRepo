import { levels, topicCatalog } from "./curriculum.js";

const state = {
  activeLevelId: levels[0].id,
  activeTopicId: levels[0].topics[0].id,
  activeSituationId: levels[0].topics[0].situations[0].id,
};

const totalSituations = levels.reduce(
  (sum, level) =>
    sum +
    level.topics.reduce((topicSum, topic) => topicSum + topic.situations.length, 0),
  0,
);

const root = document.getElementById("root");

const speechSettings = {
  rate: 0.86,
  pitch: 1,
  volume: 1,
};

let audioSequenceId = 0;

function getActiveData() {
  const activeLevel = levels.find((level) => level.id === state.activeLevelId) ?? levels[0];
  const activeTopic =
    activeLevel.topics.find((topic) => topic.id === state.activeTopicId) ??
    activeLevel.topics[0];
  const activeSituation =
    activeTopic.situations.find((situation) => situation.id === state.activeSituationId) ??
    activeTopic.situations[0];

  return { activeLevel, activeTopic, activeSituation };
}

function render() {
  const { activeLevel, activeTopic, activeSituation } = getActiveData();
  const levelStats = levels.map((level) => ({
    ...level,
    situationCount: level.topics.reduce(
      (sum, topic) => sum + topic.situations.length,
      0,
    ),
  }));

  root.innerHTML = `
    <main class="app">
      <section class="hero">
        <div class="hero__content">
          <p class="eyebrow">Real-life communication first</p>
          <h1>Learn English by situations, not word lists.</h1>
          <p class="hero__text">
            A static frontend app for natural English lessons: common sentences,
            reusable phrases, Vietnamese support, audio metadata, and game-ready
            practice. Open index.html with Live Server. No Node, Vite, backend,
            or server-side rendering required.
          </p>
          <div class="hero__actions">
            <a href="#lesson" class="button button--primary">Start Learning</a>
            <a href="#coverage" class="button button--ghost">View Coverage</a>
          </div>
        </div>
        <div class="hero__card" aria-label="Course structure">
          <span>Situation</span>
          <strong>Common Sentences</strong>
          <strong>Useful Phrases</strong>
          <strong>Vocabulary</strong>
          <strong>Games</strong>
        </div>
      </section>

      <section class="stats" aria-label="Course summary">
        ${statCard(levels.length, "Levels")}
        ${statCard(topicCatalog.length, "Topics in roadmap")}
        ${statCard(totalSituations, "Sample situations")}
      </section>

      <section class="level-now-playing" data-level-now-playing hidden aria-live="polite">
        <div>
          <p class="section-label" data-level-now-playing-label>Playing Full Level</p>
          <span data-level-now-playing-meta></span>
          <strong data-level-now-playing-english></strong>
          <small data-level-now-playing-meaning></small>
        </div>
        <div class="level-now-playing__side">
          <div class="level-now-playing__progress" data-level-now-playing-progress></div>
          <button class="stop-audio-button" type="button" data-stop-audio>
            Stop Audio
          </button>
        </div>
      </section>

      <section class="lesson-shell" id="lesson">
        <aside class="sidebar">
          <p class="section-label">Levels</p>
          <div class="level-list">
            ${levelStats.map((level) => levelButton(level, activeLevel)).join("")}
          </div>
          <div class="level-audio-panel">
            <button class="play-level-button" type="button" data-play-all-level>
              <span aria-hidden="true">▶</span>
              Play All Level
            </button>
            <small>Auto plays all sentences in ${activeLevel.title}.</small>
          </div>

          <p class="section-label">Topics</p>
          <div class="topic-list">
            ${activeLevel.topics.map((topic) => topicButton(topic, activeTopic)).join("")}
          </div>
        </aside>

        <section class="lesson-panel">
          <div class="lesson-header">
            <div>
              <p class="eyebrow">${activeLevel.subtitle} · ${activeTopic.title}</p>
              <h2>${activeSituation.title}</h2>
              <p>${activeSituation.description}</p>
            </div>
            <select id="situation-select" aria-label="Choose situation">
              ${activeTopic.situations
                .map(
                  (situation) => `
                    <option value="${situation.id}" ${
                      situation.id === activeSituation.id ? "selected" : ""
                    }>
                      ${situation.title}
                    </option>
                  `,
                )
                .join("")}
            </select>
          </div>

          ${contentGrid(activeSituation)}
        </section>
      </section>

      <section class="coverage" id="coverage">
        <div>
          <p class="section-label">Roadmap coverage</p>
          <h2>Topics from the full learning system</h2>
          <p>
            The app is ready to expand from these seeded lessons into the full
            real-life communication curriculum described in Note.txt, while
            staying completely frontend-only.
          </p>
        </div>
        <div class="coverage__topics">
          ${topicCatalog.map((topic) => `<span>${topic}</span>`).join("")}
        </div>
      </section>
    </main>
  `;

  bindEvents();
}

function bindEvents() {
  document.querySelectorAll("[data-level-id]").forEach((button) => {
    button.addEventListener("click", () => {
      audioSequenceId += 1;
      window.speechSynthesis?.cancel();
      const level = levels.find((item) => item.id === button.dataset.levelId);
      state.activeLevelId = level.id;
      state.activeTopicId = level.topics[0].id;
      state.activeSituationId = level.topics[0].situations[0].id;
      render();
    });
  });

  document.querySelectorAll("[data-topic-id]").forEach((button) => {
    button.addEventListener("click", () => {
      audioSequenceId += 1;
      window.speechSynthesis?.cancel();
      const { activeLevel } = getActiveData();
      const topic = activeLevel.topics.find((item) => item.id === button.dataset.topicId);
      state.activeTopicId = topic.id;
      state.activeSituationId = topic.situations[0].id;
      render();
    });
  });

  document.getElementById("situation-select").addEventListener("change", (event) => {
    audioSequenceId += 1;
    window.speechSynthesis?.cancel();
    state.activeSituationId = event.target.value;
    render();
  });

  document.querySelectorAll("[data-speak-text]").forEach((button) => {
    button.addEventListener("click", () => {
      speakEnglish(button.dataset.speakText, button);
    });
  });

  document.querySelectorAll("[data-play-all-sentences]").forEach((button) => {
    button.addEventListener("click", () => {
      playAllSentences(button);
    });
  });

  document.querySelectorAll("[data-play-all-level]").forEach((button) => {
    button.addEventListener("click", () => {
      playAllLevel(button);
    });
  });

  document.querySelectorAll("[data-stop-audio]").forEach((button) => {
    button.addEventListener("click", () => {
      stopAudioPlayback();
    });
  });

  document.querySelectorAll("[data-practice-type]").forEach((button) => {
    button.addEventListener("click", () => {
      startPractice(button.dataset.practiceType);
    });
  });
}

function statCard(value, label) {
  return `
    <article class="stat-card">
      <strong>${value}</strong>
      <span>${label}</span>
    </article>
  `;
}

function levelButton(level, activeLevel) {
  return `
    <button
      class="level-card ${level.id === activeLevel.id ? "is-active" : ""}"
      data-level-id="${level.id}"
      style="--accent: ${level.color}"
    >
      <span>${level.title}</span>
      <strong>${level.subtitle}</strong>
      <small>${level.topics.length} topics · ${level.situationCount} situations</small>
    </button>
  `;
}

function topicButton(topic, activeTopic) {
  return `
    <button
      class="topic-pill ${topic.id === activeTopic.id ? "is-active" : ""}"
      data-topic-id="${topic.id}"
    >
      ${topic.title}
    </button>
  `;
}

function contentGrid(situation) {
  return `
    <div class="content-grid">
      ${lessonSection(
        "Common Sentences",
        situation.sentences.length,
        `
          <div class="sentence-toolbar">
            <button class="play-all-button" type="button" data-play-all-sentences>
              <span aria-hidden="true">▶</span>
              Play All Sentences
            </button>
            <small>Auto plays every sentence in this situation.</small>
          </div>
          ${situation.sentences
            .map(
              (sentence) => `
              <article class="sentence-card">
                <div>
                  <strong>${sentence.english}</strong>
                  <span>${sentence.meaning}</span>
                </div>
                ${audioButton(sentence.english, "Listen to sentence")}
              </article>
            `,
            )
            .join("")}
        `,
      )}

      ${lessonSection(
        "Useful Phrases",
        situation.phrases.length,
        situation.phrases
          .map(
            (phrase) => `
              <article class="phrase-card">
                <strong>${phrase.phrase}</strong>
                <span>${phrase.meaning}</span>
              </article>
            `,
          )
          .join(""),
      )}

      ${lessonSection(
        "Vocabulary",
        situation.vocabulary.length,
        `
          <div class="vocab-list">
            ${situation.vocabulary
              .map(
                (item) => `
                  <article class="vocab-card">
                    <span class="vocab-card__emoji" aria-hidden="true">${item.emoji}</span>
                    <div>
                      <strong>${item.word}</strong>
                      <small>${item.ipa}</small>
                      <span>${item.meaning}</span>
                    </div>
                    ${audioButton(item.word, "Listen to word")}
                  </article>
                `,
              )
              .join("")}
          </div>
        `,
      )}

      ${lessonSection(
        "Learning Games",
        getPracticeTypes(situation).length,
        getPracticeTypes(situation)
          .map((type) => {
            const game = situation.games.find((item) => item.type === type);
            return `
              <article class="game-card game-card--interactive">
                <strong>${type}</strong>
                <span>${game?.prompt ?? practiceDescriptions[type]}</span>
                <button class="practice-button" type="button" data-practice-type="${type}">
                  Practice
                </button>
              </article>
            `;
          })
          .join(""),
      )}
    </div>
  `;
}

function lessonSection(title, count, content) {
  return `
    <section class="lesson-section">
      <div class="lesson-section__header">
        <h3>${title}</h3>
        <span>${count}</span>
      </div>
      <div class="lesson-section__body">${content}</div>
    </section>
  `;
}

function audioButton(text, label) {
  return `
    <button
      class="audio-button"
      type="button"
      data-speak-text="${escapeAttribute(text)}"
      aria-label="${label}: ${escapeAttribute(text)}"
    >
      <span aria-hidden="true">▶</span>
      Listen
    </button>
  `;
}

function playAllSentences(button) {
  const { activeLevel, activeTopic, activeSituation } = getActiveData();
  const sentences = activeSituation.sentences.map((sentence) => ({
    ...sentence,
    levelTitle: activeLevel.title,
    topicTitle: activeTopic.title,
    situationTitle: activeSituation.title,
  }));

  playSentenceSequence(button, sentences, "Play All Sentences", {
    showLevelText: true,
    nowPlayingLabel: "Playing Situation",
  });
}

function playAllLevel(button) {
  const { activeLevel } = getActiveData();
  const sentences = activeLevel.topics.flatMap((topic) =>
    topic.situations.flatMap((situation) =>
      situation.sentences.map((sentence) => ({
        ...sentence,
        levelTitle: activeLevel.title,
        topicTitle: topic.title,
        situationTitle: situation.title,
      })),
    ),
  );
  playSentenceSequence(button, sentences, "Play All Level", {
    showLevelText: true,
    nowPlayingLabel: "Playing Full Level",
  });
}

function playSentenceSequence(button, sentences, defaultLabel, options = {}) {
  if (!sentences.length) {
    showAudioMessage("There are no sentences to play.");
    return;
  }

  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    showAudioMessage("Your browser does not support speech audio.");
    return;
  }

  resetAllPlayButtons();
  window.speechSynthesis.cancel();
  button.disabled = true;
  button.classList.add("is-playing");

  const sequenceId = ++audioSequenceId;
  let index = 0;
  const nowPlayingCard = document.querySelector("[data-now-playing]");
  const levelNowPlayingCard = document.querySelector("[data-level-now-playing]");

  function playNext() {
    if (sequenceId !== audioSequenceId) {
      resetPlayAllButton(button, defaultLabel);
      hideNowPlaying(nowPlayingCard);
      hideLevelNowPlaying(levelNowPlayingCard);
      return;
    }

    if (index >= sentences.length) {
      resetPlayAllButton(button, defaultLabel);
      hideNowPlaying(nowPlayingCard);
      hideLevelNowPlaying(levelNowPlayingCard);
      return;
    }

    const currentSentence = sentences[index];
    button.innerHTML = `<span aria-hidden="true">▶</span> Playing ${index + 1}/${sentences.length}`;

    if (options.showCurrentText) {
      updateNowPlaying(nowPlayingCard, currentSentence);
    }

    if (options.showLevelText) {
      updateLevelNowPlaying(
        levelNowPlayingCard,
        currentSentence,
        index + 1,
        sentences.length,
        options.nowPlayingLabel,
      );
    }

    const utterance = createEnglishUtterance(currentSentence.english);

    utterance.onend = () => {
      index += 1;
      window.setTimeout(playNext, 350);
    };
    utterance.onerror = () => {
      resetPlayAllButton(button, defaultLabel);
      hideNowPlaying(nowPlayingCard);
      hideLevelNowPlaying(levelNowPlayingCard);
      showAudioMessage("Audio could not be played. Please try again.");
    };

    window.speechSynthesis.speak(utterance);
  }

  playNext();
}

function updateNowPlaying(card, sentence) {
  if (!card) {
    return;
  }

  card.hidden = false;
  card.querySelector("[data-now-playing-english]").textContent = sentence.english;
  card.querySelector("[data-now-playing-meaning]").textContent = sentence.meaning;
}

function hideNowPlaying(card = document.querySelector("[data-now-playing]")) {
  if (!card) {
    return;
  }

  card.hidden = true;
  card.querySelector("[data-now-playing-english]").textContent = "";
  card.querySelector("[data-now-playing-meaning]").textContent = "";
}

function updateLevelNowPlaying(
  card,
  sentence,
  currentIndex,
  totalCount,
  label = "Playing Full Level",
) {
  if (!card) {
    return;
  }

  card.hidden = false;
  card.querySelector("[data-level-now-playing-label]").textContent = label;
  card.querySelector("[data-level-now-playing-meta]").textContent =
    `${sentence.levelTitle} · ${sentence.topicTitle} · ${sentence.situationTitle}`;
  card.querySelector("[data-level-now-playing-english]").textContent = sentence.english;
  card.querySelector("[data-level-now-playing-meaning]").textContent = sentence.meaning;
  card.querySelector("[data-level-now-playing-progress]").textContent =
    `${currentIndex} / ${totalCount}`;
}

function hideLevelNowPlaying(
  card = document.querySelector("[data-level-now-playing]"),
) {
  if (!card) {
    return;
  }

  card.hidden = true;
  card.querySelector("[data-level-now-playing-label]").textContent = "Playing Full Level";
  card.querySelector("[data-level-now-playing-meta]").textContent = "";
  card.querySelector("[data-level-now-playing-english]").textContent = "";
  card.querySelector("[data-level-now-playing-meaning]").textContent = "";
  card.querySelector("[data-level-now-playing-progress]").textContent = "";
}

function resetPlayAllButton(button, label = "Play All Sentences") {
  button.disabled = false;
  button.classList.remove("is-playing");
  button.innerHTML = `<span aria-hidden="true">▶</span> ${label}`;
}

function resetAllPlayButtons() {
  document.querySelectorAll("[data-play-all-sentences]").forEach((button) => {
    resetPlayAllButton(button, "Play All Sentences");
  });
  document.querySelectorAll("[data-play-all-level]").forEach((button) => {
    resetPlayAllButton(button, "Play All Level");
  });
  hideNowPlaying();
  hideLevelNowPlaying();
}

function stopAudioPlayback() {
  audioSequenceId += 1;
  window.speechSynthesis?.cancel();
  resetAllPlayButtons();
}

const practiceDescriptions = {
  "Listen and Choose": "Listen to English audio and choose the matching sentence.",
  "Phrase Matching": "Choose the Vietnamese meaning for a useful phrase.",
  Flashcards: "Review English, IPA, Vietnamese meaning, and recall before flipping.",
  "Multiple Choice": "Read a sentence and choose the correct meaning.",
  "Sentence Builder": "Tap words in the right order to rebuild a sentence.",
  "Memory Match": "Match English phrases with Vietnamese meanings.",
  "Speaking Practice": "Listen, repeat, and optionally check your pronunciation.",
  "Role Play Conversation": "Practice responding in a real-life mini conversation.",
};

function getPracticeTypes(situation) {
  const preferredTypes = [
    "Listen and Choose",
    "Phrase Matching",
    "Flashcards",
    "Multiple Choice",
    "Sentence Builder",
    "Memory Match",
    "Speaking Practice",
    "Role Play Conversation",
  ];
  const existingTypes = situation.games.map((item) => item.type);
  return preferredTypes.filter(
    (type) =>
      existingTypes.includes(type) ||
      ["Flashcards", "Multiple Choice", "Memory Match"].includes(type),
  );
}

function startPractice(type) {
  const { activeSituation } = getActiveData();

  if (type === "Listen and Choose") {
    openChoicePractice({
      title: "Listen and Choose",
      instruction: "Listen, then choose the sentence you hear.",
      promptHtml: audioButton(pick(activeSituation.sentences).english, "Listen to question"),
      getQuestion: () => {
        const target = pick(activeSituation.sentences);
        return {
          promptHtml: audioButton(target.english, "Listen to question"),
          answer: target.english,
          options: choiceOptions(activeSituation.sentences, target, "english"),
          feedback: `Correct: ${target.meaning}`,
        };
      },
    });
    return;
  }

  if (type === "Phrase Matching") {
    openChoicePractice({
      title: "Phrase Matching",
      instruction: "Choose the Vietnamese meaning for the phrase.",
      getQuestion: () => {
        const target = pick(activeSituation.phrases);
        return {
          promptHtml: `<strong class="practice-prompt-text">${escapeHtml(target.phrase)}</strong>`,
          answer: target.meaning,
          options: choiceOptions(activeSituation.phrases, target, "meaning"),
          feedback: `Phrase: ${target.phrase}`,
        };
      },
    });
    return;
  }

  if (type === "Multiple Choice") {
    openChoicePractice({
      title: "Multiple Choice",
      instruction: "Read the sentence and choose the correct Vietnamese meaning.",
      getQuestion: () => {
        const target = pick(activeSituation.sentences);
        return {
          promptHtml: `<strong class="practice-prompt-text">${escapeHtml(target.english)}</strong>`,
          answer: target.meaning,
          options: choiceOptions(activeSituation.sentences, target, "meaning"),
          feedback: `Meaning: ${target.meaning}`,
        };
      },
    });
    return;
  }

  if (type === "Flashcards") {
    openFlashcards(activeSituation);
    return;
  }

  if (type === "Sentence Builder") {
    openSentenceBuilder(activeSituation);
    return;
  }

  if (type === "Memory Match") {
    openMemoryMatch(activeSituation);
    return;
  }

  if (type === "Speaking Practice") {
    openSpeakingPractice(activeSituation);
    return;
  }

  if (type === "Role Play Conversation") {
    openRolePlay(activeSituation);
  }
}

function openChoicePractice({ title, instruction, getQuestion }) {
  const question = getQuestion();
  openPracticeModal(
    title,
    `
      <p class="practice-instruction">${instruction}</p>
      <div class="practice-question">${question.promptHtml}</div>
      <div class="practice-options">
        ${question.options
          .map(
            (option) => `
              <button class="practice-option" type="button" data-answer="${escapeAttribute(
                option,
              )}">
                ${escapeHtml(option)}
              </button>
            `,
          )
          .join("")}
      </div>
      <div class="practice-feedback" aria-live="polite"></div>
      <button class="practice-button practice-button--secondary" type="button" data-next-question>
        New Question
      </button>
    `,
  );

  const modal = document.querySelector(".practice-modal");
  bindAudioButtons(modal);
  modal.querySelectorAll("[data-answer]").forEach((button) => {
    button.addEventListener("click", () => {
      const isCorrect = button.dataset.answer === question.answer;
      modal.querySelectorAll("[data-answer]").forEach((item) => {
        item.disabled = true;
        item.classList.toggle("is-correct", item.dataset.answer === question.answer);
      });
      button.classList.toggle("is-wrong", !isCorrect);
      modal.querySelector(".practice-feedback").textContent = isCorrect
        ? `Correct. ${question.feedback}`
        : `Not quite. ${question.feedback}`;
    });
  });
  modal.querySelector("[data-next-question]").addEventListener("click", () => {
    openChoicePractice({ title, instruction, getQuestion });
  });
}

function openFlashcards(situation) {
  const cards = situation.vocabulary.length
    ? situation.vocabulary.map((item) => ({
        front: item.word,
        back: `${item.ipa} · ${item.meaning}`,
        audio: item.word,
      }))
    : situation.phrases.map((item) => ({
        front: item.phrase,
        back: item.meaning,
        audio: item.phrase,
      }));
  let index = 0;
  let flipped = false;

  function renderCard() {
    const card = cards[index];
    const modal = document.querySelector(".practice-modal");
    modal.querySelector("[data-flashcard-card]").innerHTML = `
      <span>${index + 1} / ${cards.length}</span>
      <strong>${escapeHtml(flipped ? card.back : card.front)}</strong>
      ${audioButton(card.audio, "Listen to flashcard")}
    `;
    bindAudioButtons(modal);
  }

  openPracticeModal(
    "Flashcards",
    `
      <p class="practice-instruction">Try to remember the meaning before you flip the card.</p>
      <div class="flashcard" data-flashcard-card></div>
      <div class="practice-actions">
        <button class="practice-button" type="button" data-flip-card>Flip</button>
        <button class="practice-button practice-button--secondary" type="button" data-next-card>
          Next
        </button>
      </div>
    `,
  );

  renderCard();
  const modal = document.querySelector(".practice-modal");
  modal.querySelector("[data-flip-card]").addEventListener("click", () => {
    flipped = !flipped;
    renderCard();
  });
  modal.querySelector("[data-next-card]").addEventListener("click", () => {
    index = (index + 1) % cards.length;
    flipped = false;
    renderCard();
  });
}

function openSentenceBuilder(situation) {
  const target = pick(situation.sentences).english;
  const targetWords = cleanSentence(target).split(" ");
  const chosenWords = [];

  openPracticeModal(
    "Sentence Builder",
    `
      <p class="practice-instruction">Tap the words in the correct order.</p>
      <div class="sentence-target">${escapeHtml(situation.sentences.find((item) => item.english === target)?.meaning ?? "")}</div>
      <div class="sentence-build" data-built-sentence></div>
      <div class="word-bank">
        ${shuffle([...targetWords])
          .map(
            (word, index) => `
              <button class="word-chip" type="button" data-word="${escapeAttribute(
                word,
              )}" data-word-index="${index}">
                ${escapeHtml(word)}
              </button>
            `,
          )
          .join("")}
      </div>
      <div class="practice-actions">
        <button class="practice-button" type="button" data-check-sentence>Check</button>
        <button class="practice-button practice-button--secondary" type="button" data-reset-sentence>Reset</button>
      </div>
      <div class="practice-feedback" aria-live="polite"></div>
    `,
  );

  const modal = document.querySelector(".practice-modal");
  const builtSentence = modal.querySelector("[data-built-sentence]");
  modal.querySelectorAll("[data-word]").forEach((button) => {
    button.addEventListener("click", () => {
      chosenWords.push(button.dataset.word);
      button.disabled = true;
      builtSentence.textContent = chosenWords.join(" ");
    });
  });
  modal.querySelector("[data-check-sentence]").addEventListener("click", () => {
    const isCorrect = normalizeAnswer(chosenWords.join(" ")) === normalizeAnswer(target);
    modal.querySelector(".practice-feedback").textContent = isCorrect
      ? `Correct: ${target}`
      : `Try again. Correct sentence: ${target}`;
  });
  modal.querySelector("[data-reset-sentence]").addEventListener("click", () => {
    chosenWords.length = 0;
    builtSentence.textContent = "";
    modal.querySelectorAll("[data-word]").forEach((button) => {
      button.disabled = false;
    });
    modal.querySelector(".practice-feedback").textContent = "";
  });
}

function openMemoryMatch(situation) {
  const pairs = shuffle(situation.phrases).slice(0, 4);
  const cards = shuffle(
    pairs.flatMap((item, pairIndex) => [
      { text: item.phrase, pairIndex },
      { text: item.meaning, pairIndex },
    ]),
  );
  let firstCard = null;
  let lockBoard = false;
  let matches = 0;

  openPracticeModal(
    "Memory Match",
    `
      <p class="practice-instruction">Match each English phrase with its Vietnamese meaning.</p>
      <div class="memory-grid">
        ${cards
          .map(
            (card, index) => `
              <button class="memory-card" type="button" data-card-index="${index}" data-pair-index="${card.pairIndex}">
                <span>?</span>
                <strong>${escapeHtml(card.text)}</strong>
              </button>
            `,
          )
          .join("")}
      </div>
      <div class="practice-feedback" aria-live="polite"></div>
    `,
  );

  const modal = document.querySelector(".practice-modal");
  modal.querySelectorAll(".memory-card").forEach((button) => {
    button.addEventListener("click", () => {
      if (lockBoard || button.classList.contains("is-open") || button.classList.contains("is-matched")) {
        return;
      }
      button.classList.add("is-open");
      if (!firstCard) {
        firstCard = button;
        return;
      }
      const isMatch = firstCard.dataset.pairIndex === button.dataset.pairIndex;
      if (isMatch) {
        firstCard.classList.add("is-matched");
        button.classList.add("is-matched");
        firstCard = null;
        matches += 1;
        modal.querySelector(".practice-feedback").textContent =
          matches === pairs.length ? "Great job. You matched all pairs." : "Nice match.";
        return;
      }
      lockBoard = true;
      modal.querySelector(".practice-feedback").textContent = "Try another pair.";
      window.setTimeout(() => {
        firstCard.classList.remove("is-open");
        button.classList.remove("is-open");
        firstCard = null;
        lockBoard = false;
      }, 800);
    });
  });
}

function openSpeakingPractice(situation) {
  const target = pick(situation.sentences);
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  openPracticeModal(
    "Speaking Practice",
    `
      <p class="practice-instruction">Listen, repeat out loud, then check yourself.</p>
      <div class="practice-question">
        <strong class="practice-prompt-text">${escapeHtml(target.english)}</strong>
        <span>${escapeHtml(target.meaning)}</span>
        ${audioButton(target.english, "Listen to sentence")}
      </div>
      <div class="practice-actions">
        ${
          SpeechRecognition
            ? `<button class="practice-button" type="button" data-record-speech>Record My Voice</button>`
            : `<button class="practice-button" type="button" data-mark-spoken>I Repeated It</button>`
        }
      </div>
      <div class="practice-feedback" aria-live="polite"></div>
    `,
  );

  const modal = document.querySelector(".practice-modal");
  bindAudioButtons(modal);

  const markButton = modal.querySelector("[data-mark-spoken]");
  if (markButton) {
    markButton.addEventListener("click", () => {
      modal.querySelector(".practice-feedback").textContent =
        "Good. Repeat it 3 times: slow, normal speed, then natural speed.";
    });
  }

  const recordButton = modal.querySelector("[data-record-speech]");
  if (recordButton) {
    recordButton.addEventListener("click", () => {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recordButton.disabled = true;
      modal.querySelector(".practice-feedback").textContent = "Listening...";
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const score = speakingScore(target.english, transcript);
        modal.querySelector(".practice-feedback").textContent = `You said: "${transcript}". Match score: ${score}%.`;
      };
      recognition.onerror = () => {
        modal.querySelector(".practice-feedback").textContent =
          "Speech check did not work. Try again or repeat without recording.";
      };
      recognition.onend = () => {
        recordButton.disabled = false;
      };
      recognition.start();
    });
  }
}

function openRolePlay(situation) {
  const roleGame = situation.games.find((item) => item.type === "Role Play Conversation");
  const nativeLine =
    roleGame?.prompt.replace(/^.*?:\s*/, "") ??
    situation.sentences[Math.min(1, situation.sentences.length - 1)].english;
  const responses = shuffle(situation.sentences)
    .filter((item) => item.english !== nativeLine)
    .slice(0, 3);

  openPracticeModal(
    "Role Play Conversation",
    `
      <p class="practice-instruction">Read the native speaker line, then choose or say a natural response.</p>
      <div class="roleplay-line">
        <span>Native speaker</span>
        <strong>${escapeHtml(nativeLine)}</strong>
        ${audioButton(nativeLine, "Listen to native speaker")}
      </div>
      <div class="practice-options">
        ${responses
          .map(
            (item) => `
              <button class="practice-option" type="button" data-role-response="${escapeAttribute(
                item.english,
              )}">
                ${escapeHtml(item.english)}
                <small>${escapeHtml(item.meaning)}</small>
              </button>
            `,
          )
          .join("")}
      </div>
      <textarea class="roleplay-textarea" placeholder="Or type your own answer here..."></textarea>
      <button class="practice-button" type="button" data-check-roleplay>Check My Answer</button>
      <div class="practice-feedback" aria-live="polite"></div>
    `,
  );

  const modal = document.querySelector(".practice-modal");
  bindAudioButtons(modal);
  modal.querySelectorAll("[data-role-response]").forEach((button) => {
    button.addEventListener("click", () => {
      modal.querySelector(".roleplay-textarea").value = button.dataset.roleResponse;
      modal.querySelector(".practice-feedback").textContent =
        "Good choice. Say it out loud, then listen and repeat.";
      speakEnglish(button.dataset.roleResponse, button);
    });
  });
  modal.querySelector("[data-check-roleplay]").addEventListener("click", () => {
    const answer = modal.querySelector(".roleplay-textarea").value.trim();
    modal.querySelector(".practice-feedback").textContent = answer
      ? "Nice. Check if your answer is short, polite, and fits the situation."
      : "Type or choose an answer first.";
  });
}

function openPracticeModal(title, bodyHtml) {
  document.querySelector(".practice-overlay")?.remove();
  const overlay = document.createElement("div");
  overlay.className = "practice-overlay";
  overlay.innerHTML = `
    <section class="practice-modal" role="dialog" aria-modal="true" aria-label="${escapeAttribute(title)}">
      <div class="practice-modal__header">
        <h2>${escapeHtml(title)}</h2>
        <button class="practice-close" type="button" aria-label="Close practice">&times;</button>
      </div>
      ${bodyHtml}
    </section>
  `;
  document.body.appendChild(overlay);
  overlay.querySelector(".practice-close").addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      overlay.remove();
    }
  });
}

function bindAudioButtons(container = document) {
  container.querySelectorAll("[data-speak-text]").forEach((button) => {
    button.addEventListener("click", () => {
      speakEnglish(button.dataset.speakText, button);
    });
  });
}

function pick(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function shuffle(items) {
  return [...items].sort(() => Math.random() - 0.5);
}

function choiceOptions(items, target, key) {
  return shuffle([
    target[key],
    ...shuffle(items.filter((item) => item !== target))
      .slice(0, 3)
      .map((item) => item[key]),
  ]);
}

function cleanSentence(text) {
  return text.replace(/[.,!?]/g, "");
}

function normalizeAnswer(text) {
  return text.toLowerCase().replace(/[^a-z0-9\s']/g, "").replace(/\s+/g, " ").trim();
}

function speakingScore(target, transcript) {
  const targetWords = new Set(normalizeAnswer(target).split(" "));
  const spokenWords = normalizeAnswer(transcript).split(" ");
  const matchedWords = spokenWords.filter((word) => targetWords.has(word)).length;
  return Math.round((matchedWords / Math.max(targetWords.size, 1)) * 100);
}

function speakEnglish(text, button) {
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    showAudioMessage("Your browser does not support speech audio.");
    return;
  }

  audioSequenceId += 1;
  resetAllPlayButtons();
  window.speechSynthesis.cancel();

  const utterance = createEnglishUtterance(text);

  button.classList.add("is-playing");
  button.disabled = true;

  utterance.onend = () => resetAudioButton(button);
  utterance.onerror = () => {
    resetAudioButton(button);
    showAudioMessage("Audio could not be played. Please try again.");
  };

  window.speechSynthesis.speak(utterance);
}

function createEnglishUtterance(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = speechSettings.rate;
  utterance.pitch = speechSettings.pitch;
  utterance.volume = speechSettings.volume;

  const voice = getAmericanEnglishVoice();
  if (voice) {
    utterance.voice = voice;
  }

  return utterance;
}

function getAmericanEnglishVoice() {
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((voice) => voice.lang === "en-US" && /natural|samantha|google|microsoft/i.test(voice.name)) ??
    voices.find((voice) => voice.lang === "en-US") ??
    voices.find((voice) => voice.lang.startsWith("en"))
  );
}

function resetAudioButton(button) {
  button.classList.remove("is-playing");
  button.disabled = false;
}

function showAudioMessage(message) {
  const existingMessage = document.querySelector(".audio-message");
  if (existingMessage) {
    existingMessage.remove();
  }

  const messageElement = document.createElement("div");
  messageElement.className = "audio-message";
  messageElement.textContent = message;
  document.body.appendChild(messageElement);

  window.setTimeout(() => {
    messageElement.remove();
  }, 2600);
}

function escapeAttribute(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeHtml(value) {
  return escapeAttribute(value).replaceAll("'", "&#039;");
}

window.speechSynthesis?.addEventListener("voiceschanged", () => {
  window.speechSynthesis.getVoices();
});

render();
