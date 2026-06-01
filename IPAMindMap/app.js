(function () {
  "use strict";

  const STORAGE_KEY = "ipa-adventure-progress-v1";

  const fallbackData = {
    sounds: [
      { id: "i-long", symbol: "iː", category: "vowel", title: "Long /iː/", vnHint: "ii kéo dài", unlocked: true, examples: ["see", "green", "eat"] },
      { id: "i-short", symbol: "ɪ", category: "vowel", title: "Short /ɪ/", vnHint: "i ngắn, nhẹ", unlocked: true, examples: ["sit", "fish", "pretty"] },
      { id: "e", symbol: "e", category: "vowel", title: "Clear /e/", vnHint: "e rõ như tiếng Việt", unlocked: true, examples: ["red", "bed", "many"] },
      { id: "ae", symbol: "æ", category: "vowel", title: "Wide /æ/", vnHint: "ea, mở miệng rộng", unlocked: false, examples: ["cat", "map", "language"] },
      { id: "aa", symbol: "ɑː", category: "vowel", title: "Open /ɑː/", vnHint: "aa kéo dài", unlocked: false, examples: ["car", "father", "start"] },
      { id: "aw", symbol: "ɔː", category: "vowel", title: "Round /ɔː/", vnHint: "oo tròn môi", unlocked: false, examples: ["law", "talk", "more"] },
      { id: "u-long", symbol: "uː", category: "vowel", title: "Long /uː/", vnHint: "uu kéo dài", unlocked: false, examples: ["blue", "food", "school"] },
      { id: "uh", symbol: "ʌ", category: "vowel", title: "Central /ʌ/", vnHint: "â bật nhanh", unlocked: false, examples: ["cup", "love", "enough"] },
      { id: "schwa", symbol: "ə", category: "vowel", title: "Schwa /ə/", vnHint: "ơ rất nhẹ", unlocked: false, examples: ["about", "teacher", "beautiful"] },
      { id: "sh", symbol: "ʃ", category: "consonant", title: "Soft /ʃ/", vnHint: "sh như suỵt", unlocked: false, examples: ["she", "fish", "English"] },
      { id: "ch", symbol: "tʃ", category: "consonant", title: "Strong /tʃ/", vnHint: "ch bật mạnh", unlocked: false, examples: ["chair", "teacher", "watch"] },
      { id: "j", symbol: "dʒ", category: "consonant", title: "Buzz /dʒ/", vnHint: "j mềm, có rung", unlocked: false, examples: ["job", "orange", "language"] },
      { id: "theta", symbol: "θ", category: "consonant", title: "Air /θ/", vnHint: "th cắn lưỡi, không rung", unlocked: false, examples: ["think", "three", "math"] },
      { id: "eth", symbol: "ð", category: "consonant", title: "Voice /ð/", vnHint: "dh cắn lưỡi, có rung", unlocked: false, examples: ["this", "mother", "they"] },
      { id: "ng", symbol: "ŋ", category: "consonant", title: "Back /ŋ/", vnHint: "ng cuối âm", unlocked: false, examples: ["sing", "English", "language"] }
    ],
    words: [
      { word: "school", ipa: "/skuːl/", vn: "skuul", meaning: "trường học", level: "beginner", soundIds: ["u-long"] },
      { word: "see", ipa: "/siː/", vn: "sii", meaning: "nhìn thấy", level: "beginner", soundIds: ["i-long"] },
      { word: "green", ipa: "/ɡriːn/", vn: "griin", meaning: "màu xanh lá", level: "beginner", soundIds: ["i-long"] },
      { word: "eat", ipa: "/iːt/", vn: "iit", meaning: "ăn", level: "beginner", soundIds: ["i-long"] },
      { word: "sit", ipa: "/sɪt/", vn: "sit", meaning: "ngồi", level: "beginner", soundIds: ["i-short"] },
      { word: "fish", ipa: "/fɪʃ/", vn: "fish", meaning: "con cá", level: "beginner", soundIds: ["i-short", "sh"] },
      { word: "red", ipa: "/red/", vn: "red", meaning: "màu đỏ", level: "beginner", soundIds: ["e"] },
      { word: "cat", ipa: "/kæt/", vn: "keat", meaning: "con mèo", level: "beginner", soundIds: ["ae"] },
      { word: "car", ipa: "/kɑːr/", vn: "kaar", meaning: "xe hơi", level: "beginner", soundIds: ["aa"] },
      { word: "talk", ipa: "/tɔːk/", vn: "took", meaning: "nói chuyện", level: "beginner", soundIds: ["aw"] },
      { word: "blue", ipa: "/bluː/", vn: "bluu", meaning: "màu xanh dương", level: "beginner", soundIds: ["u-long"] },
      { word: "cup", ipa: "/kʌp/", vn: "kâp", meaning: "cái cốc", level: "beginner", soundIds: ["uh"] },
      { word: "about", ipa: "/əˈbaʊt/", vn: "ơ-baut", meaning: "về, khoảng", level: "beginner", soundIds: ["schwa"] },
      { word: "beautiful", ipa: "/ˈbjuːtəfəl/", vn: "biu-tờ-phồ", meaning: "xinh đẹp", level: "intermediate", soundIds: ["u-long", "schwa"] },
      { word: "language", ipa: "/ˈlæŋɡwɪdʒ/", vn: "leang-quịch", meaning: "ngôn ngữ", level: "intermediate", soundIds: ["ae", "ng", "i-short", "j"] },
      { word: "enough", ipa: "/ɪˈnʌf/", vn: "i-nâf", meaning: "đủ", level: "beginner", soundIds: ["i-short", "uh"] },
      { word: "chair", ipa: "/tʃer/", vn: "cher", meaning: "cái ghế", level: "beginner", soundIds: ["ch", "e"] },
      { word: "think", ipa: "/θɪŋk/", vn: "thingk", meaning: "suy nghĩ", level: "intermediate", soundIds: ["theta", "i-short", "ng"] },
      { word: "this", ipa: "/ðɪs/", vn: "dhis", meaning: "này", level: "intermediate", soundIds: ["eth", "i-short"] },
      { word: "teacher", ipa: "/ˈtiːtʃər/", vn: "tii-chờ", meaning: "giáo viên", level: "beginner", soundIds: ["i-long", "ch", "schwa"] }
    ],
    lessons: [
      { id: "lesson-i-long", soundId: "i-long", title: "Stretch the Smile", planet: "vowel-moon", order: 1, xp: 25, goal: "Hear and pronounce long /iː/ without reading it as the letter E.", tip: "Smile slightly, keep the sound long: ii.", examples: ["see", "green", "eat"] },
      { id: "lesson-i-short", soundId: "i-short", title: "Quick Little I", planet: "vowel-moon", order: 2, xp: 25, goal: "Separate /ɪ/ from Vietnamese i by making it shorter and softer.", tip: "Do not stretch the sound. Say it quickly.", examples: ["sit", "fish", "enough"] },
      { id: "lesson-e", soundId: "e", title: "Bright E", planet: "vowel-moon", order: 3, xp: 25, goal: "Use a clean /e/ sound in common beginner words.", tip: "Keep the mouth relaxed and clear.", examples: ["red", "chair"] },
      { id: "lesson-ae", soundId: "ae", title: "Wide Cat Sound", planet: "vowel-moon", order: 4, xp: 30, goal: "Open the mouth wider for /æ/ instead of saying Vietnamese 'a'.", tip: "Think of ea: keat, leang.", examples: ["cat", "language"] },
      { id: "lesson-u-long", soundId: "u-long", title: "Blue Moon /uː/", planet: "vowel-moon", order: 5, xp: 30, goal: "Round the lips and hold /uː/ clearly.", tip: "Hold uu for a little longer.", examples: ["blue", "school"] },
      { id: "lesson-schwa", soundId: "schwa", title: "Tiny Schwa", planet: "vowel-moon", order: 6, xp: 35, goal: "Notice weak /ə/ sounds that Vietnamese learners often over-pronounce.", tip: "Say ơ very lightly, almost like a shadow.", examples: ["about", "beautiful", "teacher"] },
      { id: "lesson-sh", soundId: "sh", title: "Shh Cave", planet: "consonant-planet", order: 7, xp: 30, goal: "Make /ʃ/ soft and airy.", tip: "Push air forward like saying 'suỵt'.", examples: ["fish"] },
      { id: "lesson-ch", soundId: "ch", title: "Ch Rocket", planet: "consonant-planet", order: 8, xp: 30, goal: "Make /tʃ/ crisp and stronger than Vietnamese ch.", tip: "Start with a tiny t, then release ch.", examples: ["chair", "teacher"] },
      { id: "lesson-th", soundId: "theta", planet: "consonant-planet", title: "Tongue Air", order: 9, xp: 40, goal: "Practice /θ/ with air and no voice.", tip: "Put the tongue gently between the teeth.", examples: ["think"] },
      { id: "lesson-dh", soundId: "eth", planet: "consonant-planet", title: "Tongue Voice", order: 10, xp: 40, goal: "Practice /ð/ with tongue position and vibration.", tip: "Same tongue as /θ/, but turn your voice on.", examples: ["this"] }
    ],
    rules: [
      { id: "long-vowels", title: "Long IPA marks", pattern: "ː", explanation: "The ː mark means the sound is held longer. Vietnamese hints often double the vowel, such as ii or uu." },
      { id: "stress", title: "Stress mark", pattern: "ˈ", explanation: "The ˈ mark shows the next syllable is stronger. The Vietnamese hint uses hyphens to make chunks easier to see." },
      { id: "schwa", title: "Schwa is weak", pattern: "ə", explanation: "/ə/ is the most common weak English vowel. Vietnamese learners can think of it as a very light 'ơ'." },
      { id: "th-pair", title: "Two TH sounds", pattern: "θ / ð", explanation: "/θ/ has no voice, as in think. /ð/ has voice vibration, as in this." },
      { id: "ng-final", title: "Final NG", pattern: "ŋ", explanation: "/ŋ/ is made at the back of the mouth. Avoid adding a strong g after it unless the IPA shows /ɡ/." }
    ]
  };

  const planets = [
    { id: "vowel-moon", name: "🌕 Vowel Moon", className: "planet-vowel", items: ["iː", "ɪ", "e", "æ", "ɑː", "ɔː", "uː", "ʌ", "ə"] },
    { id: "consonant-planet", name: "🔥 Consonant Planet", className: "planet-consonant", items: ["ʃ", "tʃ", "dʒ", "θ", "ð", "ŋ"] },
    { id: "phonics-planet", name: "⚡ Phonics Planet", className: "planet-phonics", items: ["sh", "ch", "ph", "th", "ng", "tion", "sion", "magic e"] },
    { id: "silent-letter-planet", name: "🧊 Silent Letter Planet", className: "planet-silent", items: ["silent b", "silent k", "silent gh", "silent w"] },
    { id: "master-planet", name: "👑 Master Planet", className: "planet-master", items: ["mixed IPA", "listening", "shadowing", "boss quiz"] }
  ];

  const state = {
    data: fallbackData,
    progress: loadProgress(),
    currentMode: "ipaToVn",
    currentQuestion: null
  };

  const $ = (selector) => document.querySelector(selector);

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    state.data = await loadAllData();
    renderAll();
    bindEvents();
    makeQuestion();
  }

  async function loadAllData() {
    const keys = ["sounds", "words", "lessons", "rules"];
    const loaded = await Promise.all(keys.map((key) => loadJson(`data/${key}.json`, fallbackData[key])));
    return keys.reduce((data, key, index) => {
      data[key] = loaded[index];
      return data;
    }, {});
  }

  async function loadJson(path, fallback) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Cannot load ${path}`);
      }
      return response.json();
    } catch (error) {
      return fallback;
    }
  }

  function loadProgress() {
    const starter = {
      xp: 0,
      coins: 0,
      streak: 1,
      completedLessons: [],
      masteredSounds: [],
      learnedWords: [],
      lastPlayed: new Date().toISOString()
    };

    try {
      return { ...starter, ...JSON.parse(localStorage.getItem(STORAGE_KEY)) };
    } catch (error) {
      return starter;
    }
  }

  function saveProgress() {
    state.progress.lastPlayed = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.progress));
  }

  function bindEvents() {
    document.querySelectorAll(".nav-item").forEach((button) => {
      button.addEventListener("click", () => switchTab(button.dataset.tab));
    });

    document.querySelectorAll(".mode-pill").forEach((button) => {
      button.addEventListener("click", () => {
        state.currentMode = button.dataset.mode;
        document.querySelectorAll(".mode-pill").forEach((pill) => pill.classList.toggle("active", pill === button));
        makeQuestion();
      });
    });

    $("#skillTree").addEventListener("click", (event) => {
      const node = event.target.closest(".skill-node");
      if (!node || node.classList.contains("locked")) {
        return;
      }
      openLesson(node.dataset.lessonId);
    });

    $("#answerOptions").addEventListener("click", (event) => {
      const button = event.target.closest(".answer-button");
      if (button) {
        answerQuestion(button);
      }
    });

    $("#newQuestionBtn").addEventListener("click", makeQuestion);
    $("#speakQuestionBtn").addEventListener("click", speakCurrentQuestion);
    $("#closeLessonBtn").addEventListener("click", closeLesson);
    $("#lessonDialog").addEventListener("click", (event) => {
      if (event.target.id === "lessonDialog") {
        closeLesson();
      }
    });
    $("#resetProgressBtn").addEventListener("click", resetProgress);
  }

  function renderAll() {
    renderHeaderProgress();
    renderSkillTree();
    renderPlanetMap();
    renderReview();
  }

  function renderHeaderProgress() {
    const level = getLevel();
    $("#xpCount").textContent = state.progress.xp;
    $("#coinCount").textContent = state.progress.coins;
    $("#completedCount").textContent = state.progress.completedLessons.length;
    $("#streakCount").textContent = state.progress.streak;
    $("#levelLabel").textContent = `Level ${level}`;
    $("#xpBar").style.width = `${state.progress.xp % 100}%`;
  }

  function getLevel() {
    return Math.max(1, Math.floor(state.progress.xp / 100) + 1);
  }

  function renderSkillTree() {
    const sortedLessons = [...state.data.lessons].sort((a, b) => a.order - b.order);
    $("#skillTree").innerHTML = sortedLessons.map((lesson) => {
      const sound = getSound(lesson.soundId);
      const status = getLessonStatus(lesson);
      return `
        <button class="skill-node ${status}" data-lesson-id="${lesson.id}" ${status === "locked" ? "aria-disabled=\"true\"" : ""}>
          <span class="status-chip">${statusLabel(status)}</span>
          <span class="node-symbol">/${sound.symbol}/</span>
          <span class="node-title">${lesson.title}</span>
          <span class="node-hint">${sound.vnHint}</span>
        </button>
      `;
    }).join("");
  }

  function getLessonStatus(lesson) {
    if (state.progress.completedLessons.includes(lesson.id)) {
      return "completed";
    }

    const completedOrders = state.data.lessons
      .filter((item) => state.progress.completedLessons.includes(item.id))
      .map((item) => item.order);
    const highestCompleted = completedOrders.length ? Math.max(...completedOrders) : 0;
    const sound = getSound(lesson.soundId);

    return sound.unlocked || lesson.order <= highestCompleted + 2 ? "unlocked" : "locked";
  }

  function statusLabel(status) {
    return {
      completed: "✓ Done",
      unlocked: "Play",
      locked: "🔒 Locked"
    }[status];
  }

  function renderPlanetMap() {
    $("#planetMap").innerHTML = planets.map((planet) => {
      const completedCount = state.data.lessons.filter((lesson) => lesson.planet === planet.id && state.progress.completedLessons.includes(lesson.id)).length;
      const totalCount = state.data.lessons.filter((lesson) => lesson.planet === planet.id).length || planet.items.length;
      return `
        <article class="planet-card ${planet.className}">
          <p class="eyebrow" style="color: rgba(255,255,255,.78)">Adventure Map</p>
          <h3>${planet.name}</h3>
          <p>${completedCount}/${totalCount} missions cleared</p>
          <div class="planet-lessons">
            ${planet.items.map((item) => `<span class="sound-chip">${item}</span>`).join("")}
          </div>
        </article>
      `;
    }).join("");
  }

  function renderReview() {
    const completedLessons = state.data.lessons.filter((lesson) => state.progress.completedLessons.includes(lesson.id));
    const masteredSounds = state.data.sounds.filter((sound) => state.progress.masteredSounds.includes(sound.id));
    const learnedWords = state.data.words.filter((word) => state.progress.learnedWords.includes(word.word));
    const todaysWords = learnedWords.length ? learnedWords.slice(-5).reverse() : state.data.words.slice(0, 5);

    $("#reviewContent").innerHTML = `
      <article class="review-card">
        <h3>Today's Review</h3>
        <p>Practice ${todaysWords.length} words to keep pronunciation fresh.</p>
        <ul class="mini-list">
          ${todaysWords.map((word) => `<li><strong>${word.word}</strong><span>${word.ipa} · ${word.vn}</span></li>`).join("")}
        </ul>
      </article>
      <article class="review-card">
        <h3>Completed Lessons</h3>
        <p>${completedLessons.length ? completedLessons.map((lesson) => lesson.title).join(", ") : "No lessons completed yet. Start with /iː/ on the Learn tab."}</p>
      </article>
      <article class="review-card">
        <h3>Mastered Sounds</h3>
        <div class="planet-lessons">
          ${masteredSounds.length ? masteredSounds.map((sound) => `<span class="sound-chip" style="background:#6c5ce7">/${sound.symbol}/</span>`).join("") : "<span class=\"sound-chip\" style=\"background:#b9c3d8\">Keep exploring</span>"}
        </div>
      </article>
      ${state.data.rules.map((rule) => `
        <article class="rule-card">
          <h3>${rule.pattern} · ${rule.title}</h3>
          <p>${rule.explanation}</p>
        </article>
      `).join("")}
    `;
  }

  function switchTab(tabId) {
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === tabId));
    document.querySelectorAll(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.tab === tabId));
    if (tabId === "review") {
      renderReview();
    }
  }

  function openLesson(lessonId) {
    const lesson = state.data.lessons.find((item) => item.id === lessonId);
    const sound = getSound(lesson.soundId);
    const examples = lesson.examples.map((wordText) => state.data.words.find((word) => word.word === wordText)).filter(Boolean);

    $("#lessonContent").innerHTML = `
      <section class="lesson-hero">
        <p class="eyebrow" style="color: rgba(255,255,255,.78)">Sound</p>
        <div class="lesson-title-row">
          <div>
            <div class="lesson-symbol">/${sound.symbol}/</div>
            <h2>${lesson.title}</h2>
          </div>
          <span class="badge">+${lesson.xp} XP</span>
        </div>
        <p><strong>Vietnamese Hint:</strong> ${sound.vnHint}</p>
        <p>${lesson.goal}</p>
      </section>
      <h3 style="margin-top: 18px">Examples</h3>
      ${examples.map((word) => exampleCard(word)).join("")}
      <article class="rule-card" style="margin-top: 14px">
        <h3>Coach Tip</h3>
        <p>${lesson.tip}</p>
      </article>
      <button class="complete-button" data-complete-lesson="${lesson.id}">Complete Lesson</button>
    `;

    $("#lessonContent").querySelectorAll("[data-speak]").forEach((button) => {
      button.addEventListener("click", () => speak(button.dataset.speak, Number(button.dataset.rate || 0.9)));
    });

    $("#lessonContent").querySelectorAll("[data-practice]").forEach((button) => {
      button.addEventListener("click", () => {
        button.textContent = "🎤 Great try!";
      });
    });

    $("#lessonContent").querySelector("[data-complete-lesson]").addEventListener("click", () => completeLesson(lesson.id));

    const dialog = $("#lessonDialog");
    if (dialog.showModal) {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
  }

  function exampleCard(word) {
    const engineHint = window.IPAEngine.convert(word.ipa);
    return `
      <article class="example-card">
        <div class="example-main">
          <strong>${word.word}</strong>
          <span>${word.ipa}</span>
        </div>
        <p><b>Hint:</b> ${word.vn || engineHint}</p>
        <p><b>Meaning:</b> ${word.meaning}</p>
        <div class="lesson-actions">
          <button class="lesson-action" data-speak="${word.word}" data-rate="0.9">▶ Listen</button>
          <button class="lesson-action" data-speak="${word.word}" data-rate="0.55">🐢 Slow</button>
          <button class="lesson-action" data-practice="${word.word}">🎤 Practice</button>
        </div>
      </article>
    `;
  }

  function closeLesson() {
    $("#lessonDialog").close();
  }

  function completeLesson(lessonId) {
    const lesson = state.data.lessons.find((item) => item.id === lessonId);
    const sound = getSound(lesson.soundId);
    const lessonWords = lesson.examples.map((wordText) => state.data.words.find((word) => word.word === wordText)).filter(Boolean);

    addUnique(state.progress.completedLessons, lesson.id);
    addUnique(state.progress.masteredSounds, sound.id);
    lessonWords.forEach((word) => addUnique(state.progress.learnedWords, word.word));
    state.progress.xp += lesson.xp;
    state.progress.coins += 10;
    saveProgress();
    closeLesson();
    renderAll();
  }

  function makeQuestion() {
    const word = randomItem(state.data.words);
    const question = buildQuestion(word, state.currentMode);
    state.currentQuestion = question;

    $("#gameModeLabel").textContent = question.modeLabel;
    $("#questionText").textContent = question.prompt;
    $("#gameFeedback").textContent = "";
    $("#gameFeedback").className = "feedback";
    $("#answerOptions").innerHTML = shuffle(question.options).map((option, index) => `
      <button class="answer-button" data-answer="${escapeAttribute(option)}">
        <span>${String.fromCharCode(65 + index)}. ${option}</span>
        <span>›</span>
      </button>
    `).join("");

    if (state.currentMode === "listenToIpa") {
      speak(word.word, 0.8);
    }
  }

  function buildQuestion(word, mode) {
    const modeMap = {
      ipaToVn: {
        modeLabel: "IPA → Vietnamese Hint",
        prompt: word.ipa,
        answer: word.vn,
        pool: state.data.words.map((item) => item.vn)
      },
      wordToIpa: {
        modeLabel: "Word → IPA",
        prompt: word.word,
        answer: word.ipa,
        pool: state.data.words.map((item) => item.ipa)
      },
      meaningToWord: {
        modeLabel: "Meaning → Word",
        prompt: word.meaning,
        answer: word.word,
        pool: state.data.words.map((item) => item.word)
      },
      listenToIpa: {
        modeLabel: "Listen → IPA",
        prompt: "Tap ▶, listen, choose the IPA",
        answer: word.ipa,
        pool: state.data.words.map((item) => item.ipa)
      }
    };

    const config = modeMap[mode];
    return {
      ...config,
      word,
      options: makeOptions(config.answer, config.pool)
    };
  }

  function makeOptions(answer, pool) {
    const options = [answer];
    const candidates = shuffle([...new Set(pool.filter((item) => item !== answer))]);
    while (options.length < 4 && candidates.length) {
      options.push(candidates.pop());
    }
    return options;
  }

  function answerQuestion(button) {
    const selected = button.dataset.answer;
    const correct = state.currentQuestion.answer;
    const buttons = document.querySelectorAll(".answer-button");
    buttons.forEach((item) => {
      item.disabled = true;
      if (item.dataset.answer === correct) {
        item.classList.add("correct");
      }
    });

    if (selected === correct) {
      button.classList.add("correct");
      $("#gameFeedback").textContent = "✔ Correct! +12 XP, +3 coins";
      $("#gameFeedback").classList.add("good");
      state.progress.xp += 12;
      state.progress.coins += 3;
      addUnique(state.progress.learnedWords, state.currentQuestion.word.word);
      state.currentQuestion.word.soundIds.forEach((soundId) => addUnique(state.progress.masteredSounds, soundId));
      saveProgress();
      renderHeaderProgress();
      renderReview();
    } else {
      button.classList.add("wrong");
      $("#gameFeedback").textContent = `✖ Wrong. Correct answer: ${correct}`;
      $("#gameFeedback").classList.add("bad");
    }

    window.setTimeout(makeQuestion, 1300);
  }

  function speakCurrentQuestion() {
    if (!state.currentQuestion) {
      return;
    }

    speak(state.currentQuestion.word.word, state.currentMode === "listenToIpa" ? 0.8 : 0.65);
  }

  function speak(text, rate) {
    if (!("speechSynthesis" in window)) {
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = rate;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }

  function resetProgress() {
    if (!confirm("Reset all XP, coins, completed lessons, and review progress?")) {
      return;
    }

    localStorage.removeItem(STORAGE_KEY);
    state.progress = loadProgress();
    renderAll();
    makeQuestion();
  }

  function getSound(soundId) {
    return state.data.sounds.find((sound) => sound.id === soundId) || state.data.sounds[0];
  }

  function randomItem(items) {
    return items[Math.floor(Math.random() * items.length)];
  }

  function shuffle(items) {
    return items
      .map((value) => ({ value, sort: Math.random() }))
      .sort((a, b) => a.sort - b.sort)
      .map((item) => item.value);
  }

  function addUnique(collection, value) {
    if (!collection.includes(value)) {
      collection.push(value);
    }
  }

  function escapeAttribute(value) {
    return String(value).replace(/"/g, "&quot;");
  }
})();
