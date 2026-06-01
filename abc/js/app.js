const { ALPHABET, RHYME_LESSONS, TONE_LESSONS, BADGES } = window.ALPHABET_DATA;

let state = window.LearnStore.loadState();
let currentLetterIndex = 0;
let currentRhymeIndex = 0;
let currentToneIndex = 0;
let activeGame = "hunt";

const screens = document.querySelectorAll(".screen");
const navButtons = document.querySelectorAll("[data-goto]");

function $(selector) {
  return document.querySelector(selector);
}

function speak(text) {
  window.AudioGuide.speak(text, state.sound);
}

function updateHome() {
  const learned = state.learned.length;
  const percent = Math.round((learned / ALPHABET.length) * 100);
  $("#progressText").textContent = `${learned}/${ALPHABET.length}`;
  $("#progressBar").style.width = `${percent}%`;
  $("#starCount").textContent = state.stars;
  $("#xpCount").textContent = state.xp;
  $("#badgeCount").textContent = state.badges.length;
  $("#soundToggle").textContent = state.sound ? "🔊" : "🔇";

  const badgeList = $("#badgeList");
  badgeList.innerHTML = BADGES.map((badge) => {
    const unlocked = state.badges.includes(badge.id);
    return `<article class="${unlocked ? "unlocked" : ""}">
      <span>${badge.icon}</span>
      <strong>${badge.name}</strong>
      <small>${unlocked ? "Đã mở khóa" : badge.condition}</small>
    </article>`;
  }).join("");
}

function goTo(screenName) {
  window.Games.clearGameTimers();
  screens.forEach((screen) => screen.classList.toggle("active", screen.dataset.screen === screenName));
  document.querySelectorAll(".bottom-nav [data-goto]").forEach((button) => {
    button.classList.toggle("active", button.dataset.goto === screenName);
  });

  if (screenName === "home") updateHome();
  if (screenName === "learn") renderLetter();
  if (screenName === "flash") window.Games.renderFlash($("#flashCard"), ALPHABET, state, updateHome);
  if (screenName === "drag") window.Games.renderDrag($("#dragGame"), ALPHABET, state, updateHome);
  if (screenName === "rhyme") renderRhyme();
  if (screenName === "spell") renderSpell();
  if (screenName === "games") renderGames();
  if (screenName === "mindmap") renderMindMap();
}

function renderLetterStrip() {
  $("#letterStrip").innerHTML = ALPHABET.map((item, index) => `
    <button class="${index === currentLetterIndex ? "active" : ""} ${state.learned.includes(item.letter) ? "done" : ""}" data-letter-index="${index}">
      ${item.letter}
    </button>
  `).join("");

  document.querySelectorAll("[data-letter-index]").forEach((button) => {
    button.addEventListener("click", () => {
      currentLetterIndex = Number(button.dataset.letterIndex);
      renderLetter();
    });
  });
}

function renderLetter() {
  const item = ALPHABET[currentLetterIndex];
  $("#learnTitle").textContent = `Chữ ${item.letter}`;
  $("#conceptVisual").textContent = item.visual;
  $("#lowerLetter").textContent = item.letter;
  $("#upperLetter").textContent = item.uppercase;
  $("#conceptName").textContent = item.imageConcept;
  $("#conceptHint").textContent = item.shapeNote;
  $("#phonicsText").textContent = `"${item.phonics}"`;
  $("#spellingText").textContent = item.spelling;
  $("#wordText").textContent = item.exampleWord;
  renderLetterStrip();
}

function changeLetter(delta) {
  currentLetterIndex = (currentLetterIndex + delta + ALPHABET.length) % ALPHABET.length;
  renderLetter();
}

function completeCurrentLetter() {
  const item = ALPHABET[currentLetterIndex];
  window.LearnStore.completeLetter(state, item.letter, ALPHABET, BADGES);
  speak(`${item.phonics}. ${item.spelling}. ${item.exampleWord}`);
  updateHome();
  renderLetter();
}

function renderRhyme() {
  const lesson = RHYME_LESSONS[currentRhymeIndex];
  $("#rhymeLesson").innerHTML = `
    <div class="step-flow">
      <span>${lesson.consonant}</span>
      <b>+</b>
      <span>${lesson.vowel}</span>
      <b>=</b>
      <strong>${lesson.syllable}</strong>
    </div>
    <p class="chant-large">${lesson.chant}</p>
    <p class="word-result">${lesson.word}</p>
    <div class="action-row">
      <button class="pill-btn" data-rhyme-prev>Quay lại</button>
      <button class="pill-btn" data-rhyme-speak>Nghe đọc</button>
      <button class="pill-btn success" data-rhyme-next>Tiếp theo</button>
    </div>
  `;
  $("[data-rhyme-prev]").addEventListener("click", () => {
    currentRhymeIndex = (currentRhymeIndex - 1 + RHYME_LESSONS.length) % RHYME_LESSONS.length;
    renderRhyme();
  });
  $("[data-rhyme-next]").addEventListener("click", () => {
    currentRhymeIndex = (currentRhymeIndex + 1) % RHYME_LESSONS.length;
    window.LearnStore.addReward(state, 5, 1);
    updateHome();
    renderRhyme();
  });
  $("[data-rhyme-speak]").addEventListener("click", () => speak(`${lesson.chant}. ${lesson.spelling}`));
}

function renderSpell() {
  const lesson = TONE_LESSONS[currentToneIndex];
  $("#spellLesson").innerHTML = `
    <div class="step-flow tone">
      <span>${lesson.base}</span>
      <b>+</b>
      <span>${lesson.mark}</span>
      <b>=</b>
      <strong>${lesson.word}</strong>
    </div>
    <p class="chant-large">${lesson.chant}</p>
    <p>Bé đọc chậm từng bước rồi đọc thành từ hoàn chỉnh.</p>
    <div class="action-row">
      <button class="pill-btn" data-tone-prev>Quay lại</button>
      <button class="pill-btn" data-tone-speak>Nghe đánh vần</button>
      <button class="pill-btn success" data-tone-next>Tiếp theo</button>
    </div>
  `;
  $("[data-tone-prev]").addEventListener("click", () => {
    currentToneIndex = (currentToneIndex - 1 + TONE_LESSONS.length) % TONE_LESSONS.length;
    renderSpell();
  });
  $("[data-tone-next]").addEventListener("click", () => {
    currentToneIndex = (currentToneIndex + 1) % TONE_LESSONS.length;
    window.LearnStore.addReward(state, 5, 1);
    updateHome();
    renderSpell();
  });
  $("[data-tone-speak]").addEventListener("click", () => speak(lesson.chant));
}

function renderGames() {
  window.Games.renderGameTabs($("#gameTabs"), activeGame, (id) => {
    activeGame = id;
    renderGames();
  });
  window.Games.renderGameById(activeGame, $("#gameStage"), ALPHABET, TONE_LESSONS, state, updateHome);
}

function renderMindMap() {
  window.MindMap.renderMindMap($("#mindMap"), $("#mindDetail"), ALPHABET, speak, (letter) => {
    currentLetterIndex = ALPHABET.findIndex((item) => item.letter === letter);
    goTo("learn");
  });
}

function bindEvents() {
  navButtons.forEach((button) => button.addEventListener("click", () => goTo(button.dataset.goto)));
  $("[data-prev-letter]").addEventListener("click", () => changeLetter(-1));
  $("[data-next-letter]").addEventListener("click", () => changeLetter(1));
  $("#listenLetter").addEventListener("click", () => {
    const item = ALPHABET[currentLetterIndex];
    speak(`${item.phonics}. ${item.spelling}. ${item.exampleWord}`);
  });
  $("#completeLetter").addEventListener("click", completeCurrentLetter);
  $("#soundToggle").addEventListener("click", () => {
    state.sound = !state.sound;
    window.LearnStore.saveState(state);
    updateHome();
  });
}

bindEvents();
updateHome();
renderLetter();
