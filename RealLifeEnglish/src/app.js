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

      <section class="lesson-shell" id="lesson">
        <aside class="sidebar">
          <p class="section-label">Levels</p>
          <div class="level-list">
            ${levelStats.map((level) => levelButton(level, activeLevel)).join("")}
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
      const level = levels.find((item) => item.id === button.dataset.levelId);
      state.activeLevelId = level.id;
      state.activeTopicId = level.topics[0].id;
      state.activeSituationId = level.topics[0].situations[0].id;
      render();
    });
  });

  document.querySelectorAll("[data-topic-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const { activeLevel } = getActiveData();
      const topic = activeLevel.topics.find((item) => item.id === button.dataset.topicId);
      state.activeTopicId = topic.id;
      state.activeSituationId = topic.situations[0].id;
      render();
    });
  });

  document.getElementById("situation-select").addEventListener("change", (event) => {
    state.activeSituationId = event.target.value;
    render();
  });

  document.querySelectorAll("[data-speak-text]").forEach((button) => {
    button.addEventListener("click", () => {
      speakEnglish(button.dataset.speakText, button);
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
        situation.sentences
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
          .join(""),
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
        situation.games.length,
        situation.games
          .map(
            (game) => `
              <article class="game-card">
                <strong>${game.type}</strong>
                <span>${game.prompt}</span>
                ${game.answer ? `<small>Answer: ${game.answer}</small>` : ""}
              </article>
            `,
          )
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

function speakEnglish(text, button) {
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    showAudioMessage("Your browser does not support speech audio.");
    return;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = speechSettings.rate;
  utterance.pitch = speechSettings.pitch;
  utterance.volume = speechSettings.volume;

  const voice = getAmericanEnglishVoice();
  if (voice) {
    utterance.voice = voice;
  }

  button.classList.add("is-playing");
  button.disabled = true;

  utterance.onend = () => resetAudioButton(button);
  utterance.onerror = () => {
    resetAudioButton(button);
    showAudioMessage("Audio could not be played. Please try again.");
  };

  window.speechSynthesis.speak(utterance);
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

window.speechSynthesis?.addEventListener("voiceschanged", () => {
  window.speechSynthesis.getVoices();
});

render();
