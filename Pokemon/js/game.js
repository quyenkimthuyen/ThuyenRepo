import { GameAudio } from "./audio.js";
import { BattleSystem } from "./battle.js";
import { Player } from "./player.js";
import { addRewards, loadState, markDailyProgress, resetState, saveState, unlockAchievements } from "./storage.js";
import { UI } from "./ui.js";
import { buildWordmons, getCaptureReward } from "./wordmon.js";
import { World } from "./world.js";

class EnglishMonsterQuest {
  constructor() {
    this.canvas = document.querySelector("#gameCanvas");
    this.ctx = this.canvas.getContext("2d");
    this.miniMap = document.querySelector("#miniMap");
    this.miniCtx = this.miniMap.getContext("2d");
    this.lastTime = performance.now();
    this.paused = false;
    this.lastAutoSave = Date.now();
  }

  async init() {
    this.vocabulary = await fetch("data/vocabulary.json").then((response) => response.json());
    this.state = loadState();
    this.audio = new GameAudio(this.state);
    this.wordmons = buildWordmons(this.vocabulary);
    this.world = new World(this.wordmons, this.state);
    this.player = new Player(this.world);
    this.ui = new UI(this.state, this.vocabulary, this.audio);
    this.battle = new BattleSystem(this.vocabulary, this.audio, this.createBattleCallbacks());

    this.resizeCanvas();
    this.bindGlobalEvents();
    this.world.revealAround(this.player);
    this.ui.refreshDrawers();
    requestAnimationFrame((time) => this.loop(time));
  }

  bindGlobalEvents() {
    window.addEventListener("resize", () => this.resizeCanvas());
    window.addEventListener("beforeunload", () => saveState(this.state));
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) saveState(this.state);
    });
    document.body.addEventListener("pointerdown", () => this.audio.startAmbience(), { once: true });

    window.addEventListener("emq:reset-save", () => {
      if (confirm("Start a fresh adventure?")) {
        this.state = resetState();
        saveState(this.state);
        location.reload();
      }
    });
  }

  resizeCanvas() {
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.floor(rect.width);
    this.canvas.height = Math.floor(rect.height);
  }

  loop(time) {
    const delta = Math.min(0.04, (time - this.lastTime) / 1000);
    this.lastTime = time;

    if (!this.paused) {
      const moved = this.player.update(delta);
      if (moved) {
        this.world.revealAround(this.player);
        this.checkExplorationEvents();
      }
      this.state.activeSeconds += delta;
    }

    this.world.draw(this.ctx, this.canvas, this.player);
    this.world.drawMiniMap(this.miniCtx, this.miniMap, this.player);
    this.ui.updateHud(this.world);

    if (Date.now() - this.lastAutoSave > 60000) {
      saveState(this.state);
      this.lastAutoSave = Date.now();
    }

    requestAnimationFrame((nextTime) => this.loop(nextTime));
  }

  checkExplorationEvents() {
    const treasure = this.world.getNearbyTreasure(this.player);
    if (treasure) this.openTreasure(treasure);

    const wordmon = this.world.getNearbyWordmon(this.player);
    if (wordmon && !this.paused) {
      this.paused = true;
      this.battle.startEncounter(wordmon);
    }

    const completion = this.world.getCompletion();
    if (completion >= 90 && this.state.captured.length >= 15 && !this.state.bossCleared) {
      this.paused = true;
      this.battle.startBoss();
    }
  }

  openTreasure(treasure) {
    treasure.opened = true;
    this.state.treasureOpened.push(treasure.id);
    addRewards(this.state, treasure.reward);
    this.audio.play("treasure");
    this.ui.toast(`Treasure found! +${treasure.reward.xp} XP and +${treasure.reward.coins || 0} coins`);
    saveState(this.state);
  }

  createBattleCallbacks() {
    return {
      onEncounterOpen: (wordmon, challenge) => {
        this.ui.renderEncounter(wordmon, challenge, (answer, button) => this.battle.answerEncounter(answer, button));
      },
      onChallengeResult: (correct, wordmon, button) => {
        this.handleEncounterResult(correct, wordmon, button);
      },
      onBossOpen: (boss, challenge) => {
        this.ui.renderBoss(boss, challenge, (answer, button) => this.battle.answerBoss(answer, button));
      },
      onBossResult: (correct, boss, button) => {
        if (button) button.classList.add(correct ? "correct" : "wrong");
        if (!correct) this.state.hearts = Math.max(0, this.state.hearts - 1);
        this.ui.updateBoss(boss);
        if (this.state.hearts <= 0) {
          this.state.hearts = 3;
          this.paused = false;
          this.ui.closeBoss();
          this.ui.toast("The dragon lets you retry with full hearts.");
        }
      },
      onBossNext: (boss, challenge) => {
        this.ui.renderBoss(boss, challenge, (answer, button) => this.battle.answerBoss(answer, button));
      },
      onBossWin: () => {
        this.state.bossCleared = true;
        addRewards(this.state, { xp: 120, coins: 50, stars: 3 });
        this.audio.play("achievement");
        this.ui.closeBoss();
        this.ui.toast("Dragon of Animals is calm! World complete reward earned.");
        this.paused = false;
        saveState(this.state);
      }
    };
  }

  handleEncounterResult(correct, wordmon, button) {
    this.state.totalAnswers += 1;

    if (correct) {
      this.state.correctAnswers += 1;
      this.state.currentStreak += 1;
      this.state.bestStreak = Math.max(this.state.bestStreak, this.state.currentStreak);
      this.state.perfectQuizStreak += 1;
      wordmon.captured = true;
      if (!this.state.captured.includes(wordmon.id)) this.state.captured.push(wordmon.id);
      const reward = getCaptureReward(wordmon, this.state.currentStreak);
      addRewards(this.state, reward);
      this.audio.play("capture");
      this.ui.showEncounterResult(true, wordmon, button, reward);
      this.markLearningProgress();
    } else {
      this.state.currentStreak = 0;
      this.state.perfectQuizStreak = 0;
      this.state.hearts = Math.max(1, this.state.hearts - 1);
      wordmon.visible = false;
      this.state.escaped.push(wordmon.id);
      window.setTimeout(() => {
        wordmon.visible = true;
      }, 10000);
      this.audio.play("wrong");
      this.ui.showEncounterResult(false, wordmon, button, { xp: 0, coins: 0 });
    }

    this.checkAchievements();
    this.paused = false;
    saveState(this.state);
  }

  markLearningProgress() {
    const completed = [
      markDailyProgress(this.state, "learn5", 1),
      markDailyProgress(this.state, "capture3", 1),
      markDailyProgress(this.state, "answer10", 1)
    ].filter(Boolean);

    completed.forEach((mission) => {
      this.audio.play("achievement");
      this.ui.toast(`Daily mission complete: ${mission.title}`);
    });
  }

  checkAchievements() {
    const unlocked = unlockAchievements(this.state, this.vocabulary);
    unlocked.forEach((id) => {
      this.audio.play("achievement");
      this.ui.toast(`Achievement unlocked: ${id}`);
    });
  }
}

const game = new EnglishMonsterQuest();
game.init().catch((error) => {
  console.error(error);
  document.querySelector("#floatingTip").textContent = "Could not load the game files. Please refresh.";
});
