"use strict";

const GRID_SIZE = 10;
const MAX_LIVES = 3;
const DIRECTIONS = [
  { x: 0, y: -1, name: "Bắc" },
  { x: 1, y: 0, name: "Đông" },
  { x: 0, y: 1, name: "Nam" },
  { x: -1, y: 0, name: "Tây" }
];

const WORDS = [
  { word: "cat", meaning: "con mèo", category: "animal" },
  { word: "dog", meaning: "con chó", category: "animal" },
  { word: "bird", meaning: "con chim", category: "animal" },
  { word: "fish", meaning: "con cá", category: "animal" },
  { word: "lion", meaning: "sư tử", category: "animal" },
  { word: "tiger", meaning: "con hổ", category: "animal" },
  { word: "bear", meaning: "con gấu", category: "animal" },
  { word: "rabbit", meaning: "con thỏ", category: "animal" },
  { word: "monkey", meaning: "con khỉ", category: "animal" },
  { word: "horse", meaning: "con ngựa", category: "animal" },
  { word: "cow", meaning: "con bò", category: "animal" },
  { word: "duck", meaning: "con vịt", category: "animal" },
  { word: "frog", meaning: "con ếch", category: "animal" },
  { word: "bee", meaning: "con ong", category: "animal" },
  { word: "ant", meaning: "con kiến", category: "animal" },
  { word: "apple", meaning: "quả táo", category: "fruit" },
  { word: "banana", meaning: "quả chuối", category: "fruit" },
  { word: "orange", meaning: "quả cam", category: "fruit" },
  { word: "mango", meaning: "quả xoài", category: "fruit" },
  { word: "grape", meaning: "quả nho", category: "fruit" },
  { word: "lemon", meaning: "quả chanh", category: "fruit" },
  { word: "peach", meaning: "quả đào", category: "fruit" },
  { word: "pear", meaning: "quả lê", category: "fruit" },
  { word: "melon", meaning: "quả dưa", category: "fruit" },
  { word: "cherry", meaning: "quả anh đào", category: "fruit" },
  { word: "book", meaning: "quyển sách", category: "school" },
  { word: "pencil", meaning: "bút chì", category: "school" },
  { word: "pen", meaning: "bút mực", category: "school" },
  { word: "ruler", meaning: "cây thước", category: "school" },
  { word: "bag", meaning: "cái cặp", category: "school" },
  { word: "desk", meaning: "bàn học", category: "school" },
  { word: "chair", meaning: "cái ghế", category: "school" },
  { word: "teacher", meaning: "giáo viên", category: "school" },
  { word: "student", meaning: "học sinh", category: "school" },
  { word: "school", meaning: "trường học", category: "school" },
  { word: "red", meaning: "màu đỏ", category: "color" },
  { word: "blue", meaning: "màu xanh dương", category: "color" },
  { word: "green", meaning: "màu xanh lá", category: "color" },
  { word: "yellow", meaning: "màu vàng", category: "color" },
  { word: "black", meaning: "màu đen", category: "color" },
  { word: "white", meaning: "màu trắng", category: "color" },
  { word: "pink", meaning: "màu hồng", category: "color" },
  { word: "purple", meaning: "màu tím", category: "color" },
  { word: "brown", meaning: "màu nâu", category: "color" },
  { word: "gray", meaning: "màu xám", category: "color" },
  { word: "father", meaning: "bố", category: "family" },
  { word: "mother", meaning: "mẹ", category: "family" },
  { word: "brother", meaning: "anh em trai", category: "family" },
  { word: "sister", meaning: "chị em gái", category: "family" },
  { word: "baby", meaning: "em bé", category: "family" },
  { word: "grandpa", meaning: "ông", category: "family" },
  { word: "grandma", meaning: "bà", category: "family" },
  { word: "family", meaning: "gia đình", category: "family" },
  { word: "friend", meaning: "bạn bè", category: "family" },
  { word: "home", meaning: "ngôi nhà", category: "family" },
  { word: "sun", meaning: "mặt trời", category: "nature" },
  { word: "moon", meaning: "mặt trăng", category: "nature" },
  { word: "star", meaning: "ngôi sao", category: "nature" },
  { word: "tree", meaning: "cái cây", category: "nature" },
  { word: "flower", meaning: "bông hoa", category: "nature" },
  { word: "river", meaning: "dòng sông", category: "nature" },
  { word: "mountain", meaning: "ngọn núi", category: "nature" },
  { word: "cloud", meaning: "đám mây", category: "nature" },
  { word: "rain", meaning: "mưa", category: "nature" },
  { word: "wind", meaning: "gió", category: "nature" },
  { word: "car", meaning: "xe hơi", category: "transport" },
  { word: "bus", meaning: "xe buýt", category: "transport" },
  { word: "bike", meaning: "xe đạp", category: "transport" },
  { word: "train", meaning: "tàu hỏa", category: "transport" },
  { word: "plane", meaning: "máy bay", category: "transport" },
  { word: "boat", meaning: "thuyền", category: "transport" },
  { word: "ship", meaning: "tàu thủy", category: "transport" },
  { word: "road", meaning: "con đường", category: "transport" },
  { word: "door", meaning: "cánh cửa", category: "home" },
  { word: "window", meaning: "cửa sổ", category: "home" },
  { word: "bed", meaning: "cái giường", category: "home" },
  { word: "table", meaning: "cái bàn", category: "home" },
  { word: "lamp", meaning: "đèn bàn", category: "home" },
  { word: "clock", meaning: "đồng hồ", category: "home" },
  { word: "cup", meaning: "cái cốc", category: "home" },
  { word: "plate", meaning: "cái đĩa", category: "home" },
  { word: "rice", meaning: "cơm", category: "food" },
  { word: "bread", meaning: "bánh mì", category: "food" },
  { word: "milk", meaning: "sữa", category: "food" },
  { word: "water", meaning: "nước", category: "food" },
  { word: "egg", meaning: "quả trứng", category: "food" },
  { word: "cake", meaning: "bánh ngọt", category: "food" },
  { word: "candy", meaning: "kẹo", category: "food" },
  { word: "soup", meaning: "súp", category: "food" },
  { word: "happy", meaning: "vui vẻ", category: "feeling" },
  { word: "sad", meaning: "buồn", category: "feeling" },
  { word: "angry", meaning: "tức giận", category: "feeling" },
  { word: "sleepy", meaning: "buồn ngủ", category: "feeling" },
  { word: "hungry", meaning: "đói bụng", category: "feeling" },
  { word: "small", meaning: "nhỏ", category: "adjective" },
  { word: "big", meaning: "to lớn", category: "adjective" },
  { word: "fast", meaning: "nhanh", category: "adjective" },
  { word: "slow", meaning: "chậm", category: "adjective" },
  { word: "hot", meaning: "nóng", category: "adjective" },
  { word: "cold", meaning: "lạnh", category: "adjective" },
  { word: "run", meaning: "chạy", category: "action" },
  { word: "jump", meaning: "nhảy", category: "action" },
  { word: "swim", meaning: "bơi", category: "action" },
  { word: "read", meaning: "đọc", category: "action" },
  { word: "write", meaning: "viết", category: "action" },
  { word: "sing", meaning: "hát", category: "action" },
  { word: "dance", meaning: "nhảy múa", category: "action" }
];

const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
const els = {
  targetMeaning: document.getElementById("targetMeaning"),
  levelText: document.getElementById("levelText"),
  scoreText: document.getElementById("scoreText"),
  livesText: document.getElementById("livesText"),
  currentWord: document.getElementById("currentWord"),
  currentMeaning: document.getElementById("currentMeaning"),
  powerText: document.getElementById("powerText"),
  powerFill: document.getElementById("powerFill"),
  throwStatus: document.getElementById("throwStatus"),
  miniMap: document.getElementById("miniMap"),
  helpText: document.getElementById("helpText"),
  toast: document.getElementById("toast"),
  overlay: document.getElementById("overlay"),
  overlayTitle: document.getElementById("overlayTitle"),
  overlayText: document.getElementById("overlayText"),
  overlayTips: document.getElementById("overlayTips"),
  primaryButton: document.getElementById("primaryButton"),
  secondaryButton: document.getElementById("secondaryButton"),
  pauseButton: document.getElementById("pauseButton")
};

const state = {
  mode: "start",
  level: 1,
  score: 0,
  lives: MAX_LIVES,
  grid: [],
  target: null,
  player: { x: 0, y: 0, dir: 1, lane: 0.5 },
  enemy: { lane: 0.5, nextThrowAt: 0, wobble: 0 },
  moving: null,
  battle: null,
  projectiles: [],
  particles: [],
  lastTime: 0,
  toastTimer: 0,
  audio: null
};

function randomItem(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function shuffle(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function cellAt(x, y) {
  if (x < 0 || y < 0 || x >= GRID_SIZE || y >= GRID_SIZE) {
    return null;
  }
  return state.grid[y][x];
}

function currentCell() {
  return cellAt(state.player.x, state.player.y);
}

function createMap() {
  const chosenWords = shuffle(WORDS).slice(0, GRID_SIZE * GRID_SIZE);
  const grid = [];
  for (let y = 0; y < GRID_SIZE; y += 1) {
    const row = [];
    for (let x = 0; x < GRID_SIZE; x += 1) {
      const vocab = chosenWords[y * GRID_SIZE + x];
      row.push({
        x,
        y,
        vocab,
        discovered: x === 0 && y === 0,
        cleared: x === 0 && y === 0,
        meaningShown: x === 0 && y === 0
      });
    }
    grid.push(row);
  }
  return grid;
}

function resetLevel(keepScore = true) {
  state.grid = createMap();
  state.target = randomItem(state.grid.flat().filter((cell) => !(cell.x === 0 && cell.y === 0))).vocab;
  state.lives = MAX_LIVES;
  state.player = { x: 0, y: 0, dir: 1, lane: 0.5 };
  state.enemy = { lane: 0.5, nextThrowAt: 0, wobble: 0 };
  state.moving = null;
  state.battle = null;
  state.projectiles = [];
  state.particles = [];
  if (!keepScore) {
    state.score = 0;
    state.level = 1;
  }
  showToast(`Tìm nghĩa: ${state.target.meaning}`);
  updateHud();
}

function startGame() {
  initAudio();
  state.mode = "explore";
  resetLevel(false);
  hideOverlay();
}

function nextLevel() {
  state.level += 1;
  state.score += 250;
  state.mode = "explore";
  resetLevel(true);
  hideOverlay();
}

function retryGame() {
  state.mode = "explore";
  resetLevel(false);
  hideOverlay();
}

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(window.innerWidth * dpr);
  canvas.height = Math.floor(window.innerHeight * dpr);
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function initAudio() {
  if (!state.audio) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      state.audio = new AudioContext();
    }
  }
  if (state.audio && state.audio.state === "suspended") {
    state.audio.resume();
  }
}

function playTone(type) {
  if (!state.audio) {
    return;
  }
  const now = state.audio.currentTime;
  const oscillator = state.audio.createOscillator();
  const gain = state.audio.createGain();
  const tones = {
    throw: [430, 0.08],
    hit: [170, 0.18],
    win: [760, 0.22],
    lose: [120, 0.35],
    step: [260, 0.05]
  };
  const [frequency, duration] = tones[type] || tones.step;
  oscillator.frequency.setValueAtTime(frequency, now);
  oscillator.type = type === "win" ? "triangle" : "sine";
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.08, now + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  oscillator.connect(gain).connect(state.audio.destination);
  oscillator.start(now);
  oscillator.stop(now + duration + 0.03);
}

function updateHud() {
  const cell = currentCell();
  els.targetMeaning.textContent = state.target ? state.target.meaning : "---";
  els.levelText.textContent = String(state.level);
  els.scoreText.textContent = String(state.score);
  els.livesText.textContent = "❤".repeat(state.lives) + "♡".repeat(MAX_LIVES - state.lives);
  els.currentWord.textContent = cell && cell.meaningShown ? cell.vocab.word : "Chưa khám phá";
  els.currentMeaning.textContent = cell && cell.meaningShown ? cell.vocab.meaning : "Đánh bại người giữ cửa để xem nghĩa.";
  const power = state.battle ? state.battle.power : 55;
  els.powerText.textContent = `${Math.round(power)}%`;
  els.powerFill.style.width = `${power}%`;
  els.throwStatus.textContent = getThrowStatus();
  els.helpText.textContent = state.mode === "battle"
    ? "Chiến đấu: ← → né, ↑ ↓ chỉnh lực, Space/Enter ném đá cong. Tối đa 2 viên rồi chờ 2 giây."
    : "Di chuyển: ↑ đi tới, ← → xoay hướng, ↓ quay lại. Vào đoạn đường mới sẽ gặp người giữ cửa.";
  renderMiniMap();
}

function getThrowStatus() {
  if (state.mode !== "battle" || !state.battle) {
    return "Sẵn sàng khi gặp người giữ cửa";
  }
  const remaining = Math.max(0, state.battle.cooldownUntil - performance.now());
  if (remaining > 0) {
    return `Đang nghỉ ${Math.ceil(remaining / 1000)}s`;
  }
  return `Có thể ném ${2 - state.battle.throwsInBurst}/2 viên`;
}

function renderMiniMap() {
  const fragment = document.createDocumentFragment();
  for (let y = 0; y < GRID_SIZE; y += 1) {
    for (let x = 0; x < GRID_SIZE; x += 1) {
      const cell = state.grid[y]?.[x];
      const div = document.createElement("div");
      div.className = "map-cell";
      if (cell?.discovered) {
        div.classList.add("discovered");
      }
      if (cell?.cleared) {
        div.classList.add("cleared");
      }
      if (state.player.x === x && state.player.y === y) {
        div.classList.add("player");
      }
      fragment.appendChild(div);
    }
  }
  els.miniMap.replaceChildren(fragment);
}

function showOverlay(title, text, buttonText, action, options = {}) {
  els.overlayTitle.textContent = title;
  els.overlayText.textContent = text;
  els.primaryButton.textContent = buttonText;
  els.primaryButton.onclick = action;
  els.secondaryButton.classList.toggle("hidden", !options.secondaryText);
  if (options.secondaryText) {
    els.secondaryButton.textContent = options.secondaryText;
    els.secondaryButton.onclick = options.secondaryAction;
  }
  els.overlayTips.classList.toggle("hidden", Boolean(options.hideTips));
  els.overlay.classList.remove("hidden");
}

function hideOverlay() {
  els.overlay.classList.add("hidden");
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => els.toast.classList.remove("show"), 1800);
}

function togglePause() {
  if (state.mode === "paused") {
    state.mode = state.battle ? "battle" : "explore";
    hideOverlay();
    return;
  }
  if (state.mode === "explore" || state.mode === "battle") {
    state.mode = "paused";
    showOverlay("Tạm dừng", "Nghỉ một chút rồi tiếp tục tìm từ nhé!", "Resume", togglePause, {
      secondaryText: "Restart",
      secondaryAction: retryGame
    });
  }
}

function turn(delta) {
  if (state.mode !== "explore" || state.moving) {
    return;
  }
  state.player.dir = (state.player.dir + delta + 4) % 4;
  showToast(`Đang nhìn về hướng ${DIRECTIONS[state.player.dir].name}`);
  updateHud();
}

function moveForward(backward = false) {
  if (state.mode !== "explore" || state.moving) {
    return;
  }
  const dir = DIRECTIONS[(state.player.dir + (backward ? 2 : 0)) % 4];
  const targetX = state.player.x + dir.x;
  const targetY = state.player.y + dir.y;
  const target = cellAt(targetX, targetY);
  if (!target) {
    showToast("Tường mê cung ở phía đó rồi!");
    return;
  }
  state.moving = {
    fromX: state.player.x,
    fromY: state.player.y,
    toX: targetX,
    toY: targetY,
    progress: 0,
    battleStarted: false
  };
  target.discovered = true;
  playTone("step");
}

function beginBattle() {
  const target = cellAt(state.moving.toX, state.moving.toY);
  state.player.x = state.moving.toX;
  state.player.y = state.moving.toY;
  state.player.lane = 0.5;
  state.enemy = {
    lane: 0.5,
    nextThrowAt: performance.now() + Math.max(900, 1800 - state.level * 120),
    wobble: 0
  };
  state.battle = {
    cell: target,
    power: 55,
    throwsInBurst: 0,
    cooldownUntil: 0,
    revealTimer: 0,
    enemyDefeated: false
  };
  state.projectiles = [];
  state.mode = "battle";
  state.moving = null;
  showToast(`Người giữ cửa xuất hiện ở đoạn "${target.vocab.word}"!`);
  updateHud();
}

function finishMove() {
  if (!state.moving) {
    return;
  }
  state.player.x = state.moving.toX;
  state.player.y = state.moving.toY;
  state.moving = null;
  updateHud();
}

function handleKeyDown(event) {
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space", "Enter"].includes(event.code)) {
    event.preventDefault();
  }
  if (event.code === "KeyP" || event.code === "Escape") {
    togglePause();
    return;
  }
  if (state.mode === "start" || state.mode === "win" || state.mode === "lose" || state.mode === "paused") {
    return;
  }
  if (state.mode === "battle") {
    handleBattleKey(event.code);
    return;
  }
  if (event.code === "ArrowUp") {
    moveForward(false);
  } else if (event.code === "ArrowDown") {
    moveForward(true);
  } else if (event.code === "ArrowLeft") {
    turn(-1);
  } else if (event.code === "ArrowRight") {
    turn(1);
  }
}

function handleBattleKey(code) {
  if (!state.battle || state.battle.enemyDefeated) {
    return;
  }
  if (code === "ArrowLeft") {
    state.player.lane = clamp(state.player.lane - 0.1, 0.15, 0.85);
  } else if (code === "ArrowRight") {
    state.player.lane = clamp(state.player.lane + 0.1, 0.15, 0.85);
  } else if (code === "ArrowUp") {
    state.battle.power = clamp(state.battle.power + 5, 25, 100);
  } else if (code === "ArrowDown") {
    state.battle.power = clamp(state.battle.power - 5, 25, 100);
  } else if (code === "Space" || code === "Enter") {
    throwPlayerRock();
  }
  updateHud();
}

function laneToX(lane, y) {
  const w = window.innerWidth;
  const center = w * 0.5;
  const widthAtY = Math.max(w * 0.28, w * (0.82 - y / window.innerHeight * 0.42));
  return center - widthAtY / 2 + lane * widthAtY;
}

function playerPosition() {
  const y = window.innerHeight * 0.8;
  return { x: laneToX(state.player.lane, y), y };
}

function enemyPosition() {
  const y = window.innerHeight * 0.37;
  return { x: laneToX(state.enemy.lane, y), y };
}

function throwPlayerRock() {
  const now = performance.now();
  if (!state.battle || state.battle.cooldownUntil > now || state.battle.throwsInBurst >= 2) {
    return;
  }
  const start = playerPosition();
  const end = enemyPosition();
  const power = state.battle.power / 100;
  state.projectiles.push({
    owner: "player",
    x: start.x,
    y: start.y - 55,
    vx: (end.x - start.x) * (0.92 + power * 0.25),
    vy: -window.innerHeight * (0.74 + power * 0.22),
    gravity: window.innerHeight * 1.45,
    radius: 13,
    age: 0
  });
  state.battle.throwsInBurst += 1;
  if (state.battle.throwsInBurst >= 2) {
    state.battle.cooldownUntil = now + 2000;
  }
  playTone("throw");
  updateHud();
}

function throwEnemyRock(now) {
  const start = enemyPosition();
  const end = playerPosition();
  const difficulty = clamp(0.68 + state.level * 0.04, 0.68, 1);
  state.projectiles.push({
    owner: "enemy",
    x: start.x,
    y: start.y + 40,
    vx: (end.x - start.x) * difficulty,
    vy: -window.innerHeight * 0.18,
    gravity: window.innerHeight * 1.12,
    radius: 12,
    age: 0
  });
  state.enemy.nextThrowAt = now + Math.max(950, 2500 - state.level * 170);
  playTone("throw");
}

function updateMoving(dt) {
  if (!state.moving) {
    return;
  }
  state.moving.progress += dt * 1.35;
  const target = cellAt(state.moving.toX, state.moving.toY);
  if (!state.moving.battleStarted && state.moving.progress >= 0.5 && target && !target.cleared) {
    state.moving.battleStarted = true;
    beginBattle();
    return;
  }
  if (state.moving.progress >= 1) {
    finishMove();
  }
}

function updateBattle(dt, now) {
  if (!state.battle) {
    return;
  }
  if (state.battle.cooldownUntil && state.battle.cooldownUntil <= now) {
    state.battle.throwsInBurst = 0;
    state.battle.cooldownUntil = 0;
  }
  if (!state.battle.enemyDefeated) {
    state.enemy.wobble += dt * (1.2 + state.level * 0.18);
    state.enemy.lane = clamp(0.5 + Math.sin(state.enemy.wobble) * 0.24, 0.15, 0.85);
    if (now >= state.enemy.nextThrowAt) {
      throwEnemyRock(now);
    }
  } else {
    state.battle.revealTimer -= dt;
    if (state.battle.revealTimer <= 0) {
      resolveRevealedWord();
    }
  }
}

function updateProjectiles(dt) {
  const enemyPos = enemyPosition();
  const playerPos = playerPosition();
  state.projectiles = state.projectiles.filter((rock) => {
    rock.age += dt;
    rock.x += rock.vx * dt;
    rock.y += rock.vy * dt;
    rock.vy += rock.gravity * dt;
    if (rock.owner === "player" && state.mode === "battle" && !state.battle.enemyDefeated) {
      if (distance(rock.x, rock.y, enemyPos.x, enemyPos.y) < 48) {
        defeatEnemy(enemyPos);
        return false;
      }
    }
    if (rock.owner === "enemy" && state.mode === "battle") {
      if (distance(rock.x, rock.y, playerPos.x, playerPos.y) < 44) {
        damagePlayer();
        return false;
      }
    }
    return rock.y < window.innerHeight + 80 && rock.x > -120 && rock.x < window.innerWidth + 120 && rock.age < 3.5;
  });
}

function distance(x1, y1, x2, y2) {
  return Math.hypot(x1 - x2, y1 - y2);
}

function defeatEnemy(pos) {
  if (!state.battle || state.battle.enemyDefeated) {
    return;
  }
  state.battle.enemyDefeated = true;
  state.battle.cell.cleared = true;
  state.battle.cell.discovered = true;
  state.battle.cell.meaningShown = true;
  state.battle.revealTimer = 1.15;
  state.score += 100;
  burst(pos.x, pos.y, ["#facc15", "#fb7185", "#38bdf8"]);
  canvas.classList.add("shake");
  setTimeout(() => canvas.classList.remove("shake"), 300);
  playTone("hit");
  showToast(`${state.battle.cell.vocab.word} = ${state.battle.cell.vocab.meaning}`);
  updateHud();
}

function resolveRevealedWord() {
  const cell = state.battle.cell;
  const isCorrect = cell.vocab.meaning === state.target.meaning;
  state.battle = null;
  state.projectiles = [];
  if (isCorrect) {
    state.score += 500;
    state.mode = "win";
    burst(window.innerWidth * 0.5, window.innerHeight * 0.35, ["#22c55e", "#facc15", "#fb7185", "#60a5fa"]);
    playTone("win");
    showOverlay(
      "Chiến thắng!",
      `Tuyệt vời! "${cell.vocab.word}" nghĩa là "${cell.vocab.meaning}". Bạn đã tìm đúng từ cần học.`,
      "Next Level",
      nextLevel,
      { secondaryText: "Play Again", secondaryAction: retryGame, hideTips: true }
    );
  } else {
    state.score = Math.max(0, state.score - 25);
    state.mode = "explore";
    showToast(`Chưa đúng. "${cell.vocab.word}" là "${cell.vocab.meaning}". Tiếp tục tìm nhé!`);
  }
  updateHud();
}

function damagePlayer() {
  if (state.mode !== "battle") {
    return;
  }
  state.lives -= 1;
  els.livesText.classList.remove("damage");
  void els.livesText.offsetWidth;
  els.livesText.classList.add("damage");
  burst(...Object.values(playerPosition()), ["#ef4444", "#f97316"]);
  playTone("hit");
  if (state.lives <= 0) {
    state.mode = "lose";
    state.projectiles = [];
    playTone("lose");
    showOverlay(
      "Hết mạng rồi!",
      `Đừng bỏ cuộc. Từ cần tìm là nghĩa "${state.target.meaning}". Hãy thử lại và né đá khéo hơn nhé.`,
      "Try Again",
      retryGame,
      { hideTips: true }
    );
  } else {
    showToast(`Bạn còn ${state.lives} mạng!`);
  }
  updateHud();
}

function burst(x, y, colors) {
  for (let i = 0; i < 28; i += 1) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 90 + Math.random() * 250;
    state.particles.push({
      x,
      y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 0.65 + Math.random() * 0.6,
      color: randomItem(colors),
      size: 4 + Math.random() * 7
    });
  }
}

function updateParticles(dt) {
  state.particles = state.particles.filter((p) => {
    p.life -= dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.vy += 320 * dt;
    return p.life > 0;
  });
}

function draw() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  ctx.clearRect(0, 0, w, h);
  drawWorld(w, h);
  if (state.mode === "battle" && state.battle) {
    drawBattle(w, h);
  } else {
    drawExplorerHints(w, h);
  }
  drawProjectiles();
  drawParticles();
}

function drawWorld(w, h) {
  const horizon = h * 0.34;
  const floorTop = h * 0.53;
  const roadOffset = state.moving ? Math.sin(state.moving.progress * Math.PI) * 30 : 0;

  const sky = ctx.createLinearGradient(0, 0, 0, floorTop);
  sky.addColorStop(0, "#7dd3fc");
  sky.addColorStop(1, "#bfdbfe");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, w, floorTop);

  drawCloud(w * 0.15, h * 0.12, 1.1);
  drawCloud(w * 0.43, h * 0.08, 0.75);
  drawCloud(w * 0.7, h * 0.16, 0.95);

  ctx.fillStyle = "#fde68a";
  ctx.beginPath();
  ctx.arc(w * 0.84, h * 0.12, 42, 0, Math.PI * 2);
  ctx.fill();

  const floor = ctx.createLinearGradient(0, floorTop, 0, h);
  floor.addColorStop(0, "#4ade80");
  floor.addColorStop(1, "#15803d");
  ctx.fillStyle = floor;
  ctx.fillRect(0, floorTop, w, h - floorTop);

  ctx.fillStyle = "#b45309";
  ctx.beginPath();
  ctx.moveTo(w * 0.42, floorTop);
  ctx.lineTo(w * 0.58, floorTop);
  ctx.lineTo(w * 0.88, h);
  ctx.lineTo(w * 0.12, h);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#fbbf24";
  ctx.beginPath();
  ctx.moveTo(w * 0.45, floorTop + roadOffset);
  ctx.lineTo(w * 0.55, floorTop + roadOffset);
  ctx.lineTo(w * 0.77, h);
  ctx.lineTo(w * 0.23, h);
  ctx.closePath();
  ctx.fill();

  ctx.strokeStyle = "rgba(255,255,255,0.52)";
  ctx.lineWidth = 5;
  for (let i = 0; i < 5; i += 1) {
    const t = i / 5;
    const y = floorTop + (h - floorTop) * t * t;
    const half = w * (0.055 + t * 0.26);
    ctx.beginPath();
    ctx.moveTo(w * 0.5 - half, y);
    ctx.lineTo(w * 0.5 + half, y);
    ctx.stroke();
  }

  drawWall(0, horizon, w * 0.37, h, "#38bdf8", "#0ea5e9");
  drawWall(w, horizon, w * 0.63, h, "#a78bfa", "#7c3aed", true);
  drawSign(w, h);
}

function drawWall(edgeX, horizon, innerX, h, color1, color2, flip = false) {
  const grad = ctx.createLinearGradient(flip ? window.innerWidth : 0, horizon, innerX, h);
  grad.addColorStop(0, color2);
  grad.addColorStop(1, color1);
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(edgeX, horizon);
  ctx.lineTo(innerX, h * 0.52);
  ctx.lineTo(innerX + (flip ? -window.innerWidth * 0.22 : window.innerWidth * 0.22), h);
  ctx.lineTo(edgeX, h);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = 4;
  ctx.stroke();
}

function drawCloud(x, y, scale) {
  ctx.fillStyle = "rgba(255, 255, 255, 0.86)";
  ctx.beginPath();
  ctx.arc(x, y, 22 * scale, 0, Math.PI * 2);
  ctx.arc(x + 24 * scale, y - 8 * scale, 28 * scale, 0, Math.PI * 2);
  ctx.arc(x + 55 * scale, y, 22 * scale, 0, Math.PI * 2);
  ctx.fill();
}

function drawSign(w, h) {
  const cell = currentCell();
  const label = cell?.meaningShown ? `${cell.vocab.word} = ${cell.vocab.meaning}` : "???";
  ctx.save();
  ctx.translate(w * 0.5, h * 0.28);
  ctx.fillStyle = "#92400e";
  ctx.fillRect(-8, 40, 16, 72);
  roundedRect(-145, -25, 290, 72, 18, "#fef3c7");
  ctx.strokeStyle = "#f97316";
  ctx.lineWidth = 5;
  ctx.stroke();
  ctx.fillStyle = "#7c2d12";
  ctx.font = "bold 24px Trebuchet MS";
  ctx.textAlign = "center";
  ctx.fillText(label, 0, 19);
  ctx.restore();
}

function drawExplorerHints(w, h) {
  const dir = DIRECTIONS[state.player.dir];
  const cell = currentCell();
  roundedRect(24, h - 118, Math.min(520, w - 420), 82, 22, "rgba(255,255,255,0.82)");
  ctx.fillStyle = "#0f172a";
  ctx.font = "bold 24px Trebuchet MS";
  ctx.fillText(`Vị trí (${state.player.x + 1}, ${state.player.y + 1}) - Hướng ${dir.name}`, 48, h - 78);
  ctx.font = "18px Trebuchet MS";
  ctx.fillStyle = "#475569";
  ctx.fillText(cell?.meaningShown ? `Đã mở: ${cell.vocab.word}` : "Hãy tiến vào đoạn đường mới để gặp thử thách.", 48, h - 48);
}

function drawBattle(w, h) {
  const player = playerPosition();
  const enemy = enemyPosition();
  drawCharacter(player.x, player.y, "#22c55e", "Bạn", true);
  if (!state.battle.enemyDefeated) {
    drawCharacter(enemy.x, enemy.y, "#ef4444", "Guard", false);
    drawAimArc(player, enemy);
  } else {
    roundedRect(w * 0.5 - 210, h * 0.36, 420, 90, 24, "rgba(255,255,255,0.9)");
    ctx.fillStyle = "#0f766e";
    ctx.font = "bold 26px Trebuchet MS";
    ctx.textAlign = "center";
    ctx.fillText(`${state.battle.cell.vocab.word} = ${state.battle.cell.vocab.meaning}`, w * 0.5, h * 0.415);
    ctx.font = "18px Trebuchet MS";
    ctx.fillText("Đang kiểm tra mục tiêu...", w * 0.5, h * 0.455);
  }
}

function drawCharacter(x, y, color, name, isPlayer) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = "rgba(15,23,42,0.18)";
  ctx.beginPath();
  ctx.ellipse(0, 54, 50, 16, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(0, 0, 38, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fff7ed";
  ctx.beginPath();
  ctx.arc(-12, -8, 7, 0, Math.PI * 2);
  ctx.arc(12, -8, 7, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#0f172a";
  ctx.beginPath();
  ctx.arc(-12, -8, 3, 0, Math.PI * 2);
  ctx.arc(12, -8, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(0, 6, 13, 0.15, Math.PI - 0.15);
  ctx.stroke();
  ctx.fillStyle = isPlayer ? "#facc15" : "#7f1d1d";
  ctx.fillRect(-24, -52, 48, 18);
  ctx.fillStyle = "#fff";
  ctx.font = "bold 18px Trebuchet MS";
  ctx.textAlign = "center";
  ctx.fillText(name, 0, 78);
  ctx.restore();
}

function drawAimArc(player, enemy) {
  if (!state.battle) {
    return;
  }
  const power = state.battle.power / 100;
  const vx = (enemy.x - player.x) * (0.92 + power * 0.25);
  let vy = -window.innerHeight * (0.74 + power * 0.22);
  let x = player.x;
  let y = player.y - 55;
  const gravity = window.innerHeight * 1.45;
  ctx.strokeStyle = "rgba(255,255,255,0.78)";
  ctx.setLineDash([10, 10]);
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(x, y);
  for (let t = 0; t < 0.85; t += 0.08) {
    x += vx * 0.08;
    y += vy * 0.08;
    vy += gravity * 0.08;
    ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawProjectiles() {
  state.projectiles.forEach((rock) => {
    ctx.save();
    ctx.translate(rock.x, rock.y);
    ctx.rotate(rock.age * 8);
    ctx.fillStyle = rock.owner === "player" ? "#78716c" : "#44403c";
    ctx.beginPath();
    ctx.arc(0, 0, rock.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.35)";
    ctx.beginPath();
    ctx.arc(-4, -5, rock.radius * 0.35, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  });
}

function drawParticles() {
  state.particles.forEach((p) => {
    ctx.globalAlpha = clamp(p.life, 0, 1);
    ctx.fillStyle = p.color;
    ctx.fillRect(p.x, p.y, p.size, p.size);
    ctx.globalAlpha = 1;
  });
}

function roundedRect(x, y, width, height, radius, fill) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
}

function loop(now) {
  const dt = Math.min(0.033, (now - state.lastTime) / 1000 || 0);
  state.lastTime = now;
  if (state.mode === "explore") {
    updateMoving(dt);
  }
  if (state.mode === "battle") {
    updateBattle(dt, now);
  }
  if (state.mode !== "paused") {
    updateProjectiles(dt);
    updateParticles(dt);
  }
  draw();
  requestAnimationFrame(loop);
}

function boot() {
  resizeCanvas();
  state.grid = createMap();
  state.target = state.grid[0][1].vocab;
  updateHud();
  showOverlay(
    "Word Maze Battle",
    "Tìm đúng từ tiếng Anh trong mê cung 10x10. Vào đoạn đường, ném đá cong như Angry Birds để đánh bại người giữ cửa và mở nghĩa của từ.",
    "Start Game",
    startGame
  );
  requestAnimationFrame(loop);
}

window.addEventListener("resize", resizeCanvas);
window.addEventListener("keydown", handleKeyDown);
els.pauseButton.addEventListener("click", togglePause);
boot();
