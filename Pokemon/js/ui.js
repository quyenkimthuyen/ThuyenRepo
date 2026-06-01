import { categorySummary } from "./wordmon.js";
import { worlds } from "./world.js";
import { xpForLevel } from "./storage.js";

const achievementLabels = {
  firstCapture: "First Capture",
  tenWords: "10 Words Learned",
  perfectQuiz: "Perfect Quiz",
  animalMaster: "Animal Master",
  foodCollector: "Food Collector",
  pronunciationExpert: "Pronunciation Expert"
};

export class UI {
  constructor(state, vocabulary, audio) {
    this.state = state;
    this.vocabulary = vocabulary;
    this.audio = audio;
    this.toastTimer = null;
    this.bindNavigation();
    this.bindSettings();
  }

  bindNavigation() {
    document.querySelectorAll("[data-screen]").forEach((button) => {
      button.addEventListener("click", () => this.openDrawer(button.dataset.screen));
    });

    document.querySelectorAll("[data-close]").forEach((button) => {
      button.addEventListener("click", () => this.closeDrawer(button.dataset.close));
    });

    document.querySelector("#settingsButton").addEventListener("click", () => this.openDrawer("settingsScreen"));
  }

  bindSettings() {
    const speechToggle = document.querySelector("#speechToggle");
    const sfxToggle = document.querySelector("#sfxToggle");
    const reset = document.querySelector("#resetSave");

    speechToggle.checked = this.state.settings.speech;
    sfxToggle.checked = this.state.settings.sfx;
    speechToggle.addEventListener("change", () => {
      this.state.settings.speech = speechToggle.checked;
      this.toast("Pronunciation setting saved.");
    });
    sfxToggle.addEventListener("change", () => {
      this.state.settings.sfx = sfxToggle.checked;
      this.toast("Sound setting saved.");
    });
    reset.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("emq:reset-save"));
    });
  }

  updateHud(world) {
    document.querySelector("#heartHud").textContent = "❤ ".repeat(this.state.hearts).trim() || "♡";
    document.querySelector("#levelHud").textContent = this.state.level;
    document.querySelector("#xpHud").textContent = `${this.state.xp}/${xpForLevel(this.state.level)}`;
    document.querySelector("#coinHud").textContent = this.state.coins;
    document.querySelector("#starHud").textContent = this.state.stars;
    document.querySelector("#completionBadge").textContent = `${world.getCompletion()}%`;
    const mission = this.state.daily.missions[0];
    document.querySelector("#dailyMission").textContent = mission.title;
    document.querySelector("#dailyReward").textContent = `+${mission.reward.xp} XP`;
    document.querySelector("#dailyProgress").style.width = `${(mission.progress / mission.goal) * 100}%`;
  }

  renderEncounter(wordmon, challenge, onAnswer) {
    const screen = document.querySelector("#encounterScreen");
    document.querySelector("#encounterArt").textContent = wordmon.image;
    document.querySelector("#encounterName").textContent = wordmon.name;
    document.querySelector("#encounterRarity").textContent = wordmon.rarity;
    document.querySelector("#encounterFeedback").textContent = "";
    document.querySelector("#replayPronunciation").onclick = () => this.audio.speak(wordmon.word);
    document.querySelector("#closeEncounter").onclick = () => this.closeEncounter();
    this.renderChallenge(challenge, "#challengeBox", "#answerOptions", onAnswer);
    screen.classList.remove("hidden");
  }

  renderChallenge(challenge, promptSelector, optionsSelector, onAnswer) {
    const prompt = document.querySelector(promptSelector);
    const options = document.querySelector(optionsSelector);
    prompt.innerHTML = `<span>${challenge.prompt}</span><small>${challenge.help}</small>`;
    options.innerHTML = "";

    challenge.options.forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.innerHTML = option.image
        ? `<span class="answer-image">${option.label}</span><small>${option.subLabel}</small>`
        : option.label;
      button.addEventListener("click", () => {
        if (option.sound) this.audio.speak(option.sound);
        onAnswer(option.value, button);
      });
      options.appendChild(button);
    });
  }

  showEncounterResult(correct, wordmon, button, reward) {
    const feedback = document.querySelector("#encounterFeedback");
    if (button) button.classList.add(correct ? "correct" : "wrong");
    document.querySelectorAll("#answerOptions button").forEach((item) => {
      item.disabled = true;
    });

    if (correct) {
      feedback.textContent = `Captured ${wordmon.name}! +${reward.xp} XP, +${reward.coins} coins`;
      document.querySelector("#encounterArt").classList.add("capture-pop");
    } else {
      feedback.textContent = `${wordmon.name} skipped away. Try again soon!`;
    }

    window.setTimeout(() => this.closeEncounter(), correct ? 1400 : 1100);
  }

  closeEncounter() {
    document.querySelector("#encounterScreen").classList.add("hidden");
    document.querySelector("#encounterArt").classList.remove("capture-pop");
  }

  renderBoss(boss, challenge, onAnswer) {
    document.querySelector("#bossScreen").classList.remove("hidden");
    this.updateBoss(boss);
    this.renderChallenge(challenge, "#bossQuestion", "#bossOptions", onAnswer);
  }

  updateBoss(boss) {
    document.querySelector("#bossHpBar").style.width = `${(boss.hp / boss.maxHp) * 100}%`;
    document.querySelector("#bossStatus").textContent = `${boss.hp}/${boss.maxHp} calm hearts left`;
  }

  closeBoss() {
    document.querySelector("#bossScreen").classList.add("hidden");
  }

  renderBook() {
    const grid = document.querySelector("#bookGrid");
    const captured = new Set(this.state.captured);
    grid.innerHTML = "";
    document.querySelector("#collectionStats").innerHTML = `
      <div class="dashboard-card"><strong>${captured.size}/${this.vocabulary.length}</strong><span>Wordmons captured</span></div>
    `;

    this.vocabulary.forEach((entry) => {
      const isCaptured = captured.has(entry.id);
      const card = document.createElement("article");
      card.className = `book-card ${isCaptured ? "" : "locked"}`;
      card.innerHTML = isCaptured
        ? `<div class="creature">${entry.image}</div><h3>${entry.word}</h3><p>${entry.ipa}</p><p>${entry.meaning_vi}</p><p>${entry.example}</p><button type="button">🔊 Pronounce</button>`
        : `<div class="creature">?</div><h3>${entry.name}</h3><p>Find this Wordmon on the map.</p>`;
      const button = card.querySelector("button");
      if (button) button.addEventListener("click", () => this.audio.speak(entry.word));
      grid.appendChild(card);
    });
  }

  renderWorldMap() {
    const list = document.querySelector("#worldList");
    list.innerHTML = "";
    worlds.forEach((world, index) => {
      const unlocked = index === 0 || this.state.level >= index * 5;
      const card = document.createElement("article");
      card.className = `world-card ${unlocked ? "" : "locked"}`;
      card.innerHTML = `<h3>World ${index + 1}: ${world}</h3><p>${unlocked ? "Unlocked" : `Unlocks at level ${index * 5}`}</p>`;
      list.appendChild(card);
    });
  }

  renderDaily() {
    const list = document.querySelector("#dailyList");
    list.innerHTML = "";
    this.state.daily.missions.forEach((mission) => {
      const card = document.createElement("article");
      card.className = "mission-card";
      card.innerHTML = `
        <h3>${mission.title}</h3>
        <p>${mission.progress}/${mission.goal} complete ${mission.claimed ? "• Reward claimed" : ""}</p>
        <div class="progress-track"><span style="width:${(mission.progress / mission.goal) * 100}%"></span></div>
      `;
      list.appendChild(card);
    });
  }

  renderParentDashboard() {
    const captured = new Set(this.state.captured);
    const categories = categorySummary(this.vocabulary, this.state.captured);
    const accuracy = this.state.totalAnswers ? Math.round((this.state.correctAnswers / this.state.totalAnswers) * 100) : 0;
    const minutes = Math.max(1, Math.round(this.state.activeSeconds / 60));
    const completedCategories = Object.values(categories).filter((entry) => entry.captured === entry.total).length;

    document.querySelector("#parentDashboard").innerHTML = `
      <div class="dashboard-card"><strong>${captured.size}</strong><span>Words learned</span></div>
      <div class="dashboard-card"><strong>${completedCategories}</strong><span>Categories completed</span></div>
      <div class="dashboard-card"><strong>${accuracy}%</strong><span>Accuracy</span></div>
      <div class="dashboard-card"><strong>${minutes}m</strong><span>Time spent learning</span></div>
      <div class="dashboard-card"><strong>${this.state.learningStreak}</strong><span>Day streak</span></div>
      <div class="dashboard-card"><strong>${this.state.bestStreak}</strong><span>Best correct streak</span></div>
    `;

    this.renderAchievements();
  }

  renderAchievements() {
    const list = document.querySelector("#achievementList");
    list.innerHTML = "";
    Object.entries(achievementLabels).forEach(([id, label]) => {
      const unlocked = this.state.achievements[id];
      const card = document.createElement("article");
      card.className = `achievement-card ${unlocked ? "unlocked" : ""}`;
      card.innerHTML = `<strong>${unlocked ? "🏆" : "🔒"} ${label}</strong>`;
      list.appendChild(card);
    });
  }

  refreshDrawers() {
    this.renderBook();
    this.renderWorldMap();
    this.renderDaily();
    this.renderParentDashboard();
  }

  openDrawer(id) {
    this.refreshDrawers();
    document.querySelector(`#${id}`).classList.remove("hidden");
  }

  closeDrawer(id) {
    document.querySelector(`#${id}`).classList.add("hidden");
  }

  toast(message) {
    const toast = document.querySelector("#toast");
    toast.textContent = message;
    toast.classList.remove("hidden");
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => toast.classList.add("hidden"), 2500);
  }
}
