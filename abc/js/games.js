let huntTimer = null;

const gameNames = [
  { id: "hunt", label: "Săn chữ" },
  { id: "word", label: "Ghép từ" },
  { id: "sound", label: "Nghe chọn" },
  { id: "memory", label: "Lật thẻ" },
  { id: "tone", label: "Dấu thanh" }
];

function shuffle(items) {
  return [...items].sort(() => Math.random() - 0.5);
}

function pick(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function reward(state, onUpdate, xp = 6, stars = 1) {
  window.LearnStore.addReward(state, xp, stars);
  onUpdate?.();
}

function clearGameTimers() {
  if (huntTimer) {
    clearInterval(huntTimer);
    huntTimer = null;
  }
}

function optionLetters(answer, alphabet, amount = 4) {
  const distractors = shuffle(alphabet.filter((item) => item.letter !== answer.letter)).slice(0, amount - 1);
  return shuffle([answer, ...distractors]);
}

function renderFlash(container, alphabet, state, onUpdate) {
  const answer = pick(alphabet);
  const options = optionLetters(answer, alphabet);
  container.innerHTML = `
    <div class="game-visual">${answer.visual}</div>
    <p class="game-question">Đây là hình gì? Chọn chữ đúng cho <strong>${answer.imageConcept}</strong>.</p>
    <div class="answer-grid">
      ${options.map((item) => `<button data-answer="${item.letter}">${item.uppercase}<small>${item.letter}</small></button>`).join("")}
    </div>
    <p class="feedback" aria-live="polite"></p>
  `;

  container.querySelectorAll("[data-answer]").forEach((button) => {
    button.addEventListener("click", () => {
      const correct = button.dataset.answer === answer.letter;
      container.querySelector(".feedback").textContent = correct ? "🎉 Chính xác!" : "😊 Thử lại nhé";
      if (correct) {
        reward(state, onUpdate);
        setTimeout(() => renderFlash(container, alphabet, state, onUpdate), 650);
      }
    });
  });
}

function renderDrag(container, alphabet, state, onUpdate) {
  const answer = pick(alphabet);
  const options = optionLetters(answer, alphabet);
  container.innerHTML = `
    <div class="game-visual">${answer.visual}</div>
    <p class="game-question">Kéo hoặc chạm chữ đúng vào ô trống: <strong>${answer.imageConcept}</strong></p>
    <div class="drop-zone" data-drop>Thả chữ vào đây</div>
    <div class="drag-bank">
      ${options.map((item) => `<button draggable="true" data-drag="${item.letter}">${item.letter}</button>`).join("")}
    </div>
    <p class="feedback" aria-live="polite"></p>
  `;

  const dropZone = container.querySelector("[data-drop]");
  const check = (letter) => {
    const correct = letter === answer.letter;
    dropZone.textContent = letter;
    dropZone.classList.toggle("correct", correct);
    container.querySelector(".feedback").textContent = correct ? "🎈 Tuyệt vời!" : "Gần đúng rồi, thử chữ khác nhé.";
    if (correct) {
      reward(state, onUpdate);
      setTimeout(() => renderDrag(container, alphabet, state, onUpdate), 700);
    }
  };

  container.querySelectorAll("[data-drag]").forEach((button) => {
    button.addEventListener("dragstart", (event) => event.dataTransfer.setData("text/plain", button.dataset.drag));
    button.addEventListener("click", () => check(button.dataset.drag));
  });
  dropZone.addEventListener("dragover", (event) => event.preventDefault());
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    check(event.dataTransfer.getData("text/plain"));
  });
}

function renderHunt(container, alphabet, state, onUpdate) {
  clearGameTimers();
  const target = pick(alphabet);
  let score = 0;
  let level = 1;
  container.innerHTML = `
    <div class="hunt-top">
      <div><span>Tìm chữ</span><strong>${target.letter}</strong></div>
      <div><span>Điểm</span><strong data-score>0</strong></div>
      <div><span>Cấp</span><strong data-level>1</strong></div>
    </div>
    <div class="falling-area"></div>
    <p class="feedback">Chạm đúng chữ ${target.letter}</p>
  `;
  window.AudioGuide.speak(`Tìm chữ ${target.letter}`, state.sound);
  const area = container.querySelector(".falling-area");

  huntTimer = setInterval(() => {
    const item = Math.random() > 0.42 ? target : pick(alphabet);
    const letter = document.createElement("button");
    letter.className = "falling-letter";
    letter.textContent = item.letter;
    letter.style.left = `${Math.random() * 78 + 4}%`;
    letter.style.animationDuration = `${Math.max(2.4, 5 - level * 0.35)}s`;
    letter.addEventListener("click", () => {
      if (item.letter === target.letter) {
        score += 10;
        level = Math.min(6, Math.floor(score / 40) + 1);
        container.querySelector("[data-score]").textContent = score;
        container.querySelector("[data-level]").textContent = level;
        container.querySelector(".feedback").textContent = "⭐ Bắt đúng rồi!";
        reward(state, onUpdate, 4, 1);
        letter.remove();
      } else {
        container.querySelector(".feedback").textContent = "Không phải chữ này nhé.";
      }
    });
    area.appendChild(letter);
    setTimeout(() => letter.remove(), 5400);
  }, 850);
}

function renderWordBuilder(container, alphabet, state, onUpdate) {
  const wordItems = alphabet.filter((item) => item.exampleWord.length <= 3 && !item.exampleWord.includes(" "));
  const answer = pick(wordItems);
  const letters = shuffle([...answer.exampleWord.normalize("NFC"), ...shuffle(alphabet).slice(0, 2).map((item) => item.letter)]).slice(0, 5);
  let built = "";
  container.innerHTML = `
    <div class="game-visual">${answer.visual}</div>
    <p class="game-question">Ghép từ chỉ <strong>${answer.imageConcept}</strong></p>
    <div class="word-slots" data-built>_</div>
    <div class="drag-bank">
      ${letters.map((letter, index) => `<button data-piece="${letter}" data-index="${index}">${letter}</button>`).join("")}
    </div>
    <div class="action-row"><button class="pill-btn" data-reset>Chơi lại</button></div>
    <p class="feedback"></p>
  `;
  const builtNode = container.querySelector("[data-built]");
  const reset = () => renderWordBuilder(container, alphabet, state, onUpdate);
  container.querySelector("[data-reset]").addEventListener("click", reset);
  container.querySelectorAll("[data-piece]").forEach((button) => {
    button.addEventListener("click", () => {
      built += button.dataset.piece;
      button.disabled = true;
      builtNode.textContent = built;
      if (built === answer.exampleWord) {
        container.querySelector(".feedback").textContent = "🏆 Bé ghép đúng từ rồi!";
        window.AudioGuide.speak(answer.spelling, state.sound);
        reward(state, onUpdate, 8, 1);
        setTimeout(reset, 900);
      } else if (!answer.exampleWord.startsWith(built)) {
        container.querySelector(".feedback").textContent = "Sai thứ tự rồi, mình làm lại nhé.";
        setTimeout(reset, 700);
      }
    });
  });
}

function renderSoundChoice(container, alphabet, state, onUpdate) {
  const answer = pick(alphabet);
  const options = optionLetters(answer, alphabet);
  container.innerHTML = `
    <button class="primary-action small" data-play>Nghe lại</button>
    <p class="game-question">Nghe âm và chọn chữ đúng.</p>
    <div class="answer-grid">
      ${options.map((item) => `<button data-answer="${item.letter}">${item.letter}</button>`).join("")}
    </div>
    <p class="feedback"></p>
  `;
  const play = () => window.AudioGuide.speak(answer.phonics, state.sound);
  container.querySelector("[data-play]").addEventListener("click", play);
  play();
  container.querySelectorAll("[data-answer]").forEach((button) => {
    button.addEventListener("click", () => {
      const correct = button.dataset.answer === answer.letter;
      container.querySelector(".feedback").textContent = correct ? "Đúng âm rồi!" : "Nghe kỹ lại nhé.";
      if (correct) {
        reward(state, onUpdate);
        setTimeout(() => renderSoundChoice(container, alphabet, state, onUpdate), 700);
      }
    });
  });
}

function renderMemory(container, alphabet, state, onUpdate) {
  const picks = shuffle(alphabet).slice(0, 4);
  const cards = shuffle(picks.flatMap((item) => [
    { id: item.letter, text: item.visual },
    { id: item.letter, text: item.letter }
  ]));
  let opened = [];
  let matched = 0;
  container.innerHTML = `
    <p class="game-question">Lật thẻ để nối hình với chữ.</p>
    <div class="memory-grid">
      ${cards.map((card, index) => `<button data-card="${index}" data-id="${card.id}" data-text="${card.text}">?</button>`).join("")}
    </div>
    <p class="feedback"></p>
  `;
  container.querySelectorAll("[data-card]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.classList.contains("open") || opened.length === 2) return;
      button.textContent = button.dataset.text;
      button.classList.add("open");
      opened.push(button);
      if (opened.length === 2) {
        const same = opened[0].dataset.id === opened[1].dataset.id;
        if (same) {
          opened.forEach((item) => item.classList.add("matched"));
          opened = [];
          matched += 1;
          reward(state, onUpdate, 3, 0);
          if (matched === picks.length) {
            container.querySelector(".feedback").textContent = "🎉 Hoàn thành bộ thẻ!";
            setTimeout(() => renderMemory(container, alphabet, state, onUpdate), 1000);
          }
        } else {
          setTimeout(() => {
            opened.forEach((item) => {
              item.textContent = "?";
              item.classList.remove("open");
            });
            opened = [];
          }, 650);
        }
      }
    });
  });
}

function renderToneGame(container, toneLessons, state, onUpdate) {
  const answer = pick(toneLessons);
  const options = shuffle(toneLessons).slice(0, 4);
  if (!options.some((item) => item.mark === answer.mark)) options[0] = answer;
  container.innerHTML = `
    <div class="tone-word">${answer.base} + ? = ${answer.word}</div>
    <p class="game-question">Chọn dấu thanh đúng.</p>
    <div class="answer-grid">
      ${shuffle(options).map((item) => `<button data-mark="${item.mark}">${item.mark}</button>`).join("")}
    </div>
    <p class="feedback"></p>
  `;
  container.querySelectorAll("[data-mark]").forEach((button) => {
    button.addEventListener("click", () => {
      const correct = button.dataset.mark === answer.mark;
      container.querySelector(".feedback").textContent = correct ? answer.chant : "Dấu này chưa đúng nhé.";
      if (correct) {
        window.AudioGuide.speak(answer.chant, state.sound);
        reward(state, onUpdate);
        setTimeout(() => renderToneGame(container, toneLessons, state, onUpdate), 850);
      }
    });
  });
}

function renderGameTabs(tabs, activeId, onSelect) {
  tabs.innerHTML = gameNames.map((game) => `<button class="${game.id === activeId ? "active" : ""}" data-game="${game.id}">${game.label}</button>`).join("");
  tabs.querySelectorAll("[data-game]").forEach((button) => button.addEventListener("click", () => onSelect(button.dataset.game)));
}

function renderGameById(id, container, alphabet, toneLessons, state, onUpdate) {
  clearGameTimers();
  if (id === "hunt") renderHunt(container, alphabet, state, onUpdate);
  if (id === "word") renderWordBuilder(container, alphabet, state, onUpdate);
  if (id === "sound") renderSoundChoice(container, alphabet, state, onUpdate);
  if (id === "memory") renderMemory(container, alphabet, state, onUpdate);
  if (id === "tone") renderToneGame(container, toneLessons, state, onUpdate);
}

window.Games = {
  clearGameTimers,
  renderFlash,
  renderDrag,
  renderGameTabs,
  renderGameById
};
