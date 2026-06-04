/**
 * Word Snake
 * Mouse-controlled English/Vietnamese learning snake.
 */

const FALLBACK_VOCAB = [
    { word: 'Dog', meaning: 'Con chó', emoji: '🐶' },
    { word: 'Cat', meaning: 'Con mèo', emoji: '🐱' },
    { word: 'Fish', meaning: 'Con cá', emoji: '🐟' },
    { word: 'Apple', meaning: 'Quả táo', emoji: '🍎' },
    { word: 'Banana', meaning: 'Quả chuối', emoji: '🍌' },
    { word: 'Bird', meaning: 'Con chim', emoji: '🐦' },
    { word: 'Book', meaning: 'Quyển sách', emoji: '📖' },
    { word: 'School', meaning: 'Trường học', emoji: '🏫' },
    { word: 'Teacher', meaning: 'Giáo viên', emoji: '👩‍🏫' },
    { word: 'Run', meaning: 'Chạy', emoji: '🏃' }
];

const SPEED_BOOST_MULTIPLIER = 3;
const SPEED_BOOST_DURATION_SECONDS = 1;
const SPEED_BOOST_COOLDOWN_SECONDS = 10;
const AUTO_SNAKE_MAX_COUNT = 1;
const AUTO_SNAKE_SPAWN_STAGGER_FRAMES = 90;
const LOTUS_HIT_EFFECT_FRAMES = 24;

const MODE_CONFIG = {
    'vi-en': {
        label: 'VI -> EN',
        firstPromptType: 'vi',
        speechOrder: ['vi', 'en'],
        speed: 5.2,
        wrongHurts: true
    },
    'en-vi': {
        label: 'EN -> VI',
        firstPromptType: 'en',
        speechOrder: ['en', 'vi'],
        speed: 5.2,
        wrongHurts: true
    },
    mixed: {
        label: 'AUDIO',
        firstPromptType: 'en',
        speechOrder: ['en', 'vi'],
        speed: 5.45,
        wrongHurts: true
    },
    practice: {
        label: 'PRACTICE',
        firstPromptType: 'vi',
        speechOrder: ['vi', 'en'],
        speed: 4.25,
        wrongHurts: false
    },
    swamp: {
        label: 'LOTUS',
        firstPromptType: 'food',
        speechOrder: [],
        speed: 4.7,
        wrongHurts: false,
        survival: true
    },
    train: {
        label: 'TRAIN',
        firstPromptType: 'food',
        speechOrder: [],
        speed: 4.35,
        wrongHurts: false,
        survival: true,
        train: true
    }
};

const VOCAB_SOURCES = {
    grade1: { label: 'Grade 1', file: 'grade1.json' },
    grade2: { label: 'Grade 2', file: 'grade2.json' },
    grade3: { label: 'Grade 3', file: 'grade3.json' },
    grade4: { label: 'Grade 4', file: 'grade4.json' },
    grade5: { label: 'Grade 5', file: 'grade5.json' },
    grade6: { label: 'Grade 6', file: 'grade6.json' },
    grade7: { label: 'Grade 7', file: 'grade7.json' },
    grade8: { label: 'Grade 8', file: 'grade8.json' },
    grade9: { label: 'Grade 9', file: 'grade9.json' },
    grade10: { label: 'Grade 10', file: 'grade10.json' },
    grade11: { label: 'Grade 11', file: 'grade11.json' },
    grade12: { label: 'Grade 12', file: 'grade12.json' },
    toeic: { label: 'TOEIC', file: 'toeic.json' },
    all: { label: 'All Grades', file: 'merged_all_grades.json' }
};

const DEFAULT_VOCAB_SOURCE = 'grade4';

const AUTO_SNAKE_COLORS = [
    { body: '#f97316', dark: '#7c2d12', glow: 'rgba(253, 186, 116, 0.62)', shadow: 'rgba(43, 15, 6, 0.48)', headLight: '#fed7aa', headEnd: '#9a3412', particle: '#f97316' },
    { body: '#8b5cf6', dark: '#4c1d95', glow: 'rgba(196, 181, 253, 0.62)', shadow: 'rgba(30, 27, 75, 0.48)', headLight: '#ddd6fe', headEnd: '#5b21b6', particle: '#a78bfa' },
    { body: '#ec4899', dark: '#831843', glow: 'rgba(249, 168, 212, 0.62)', shadow: 'rgba(80, 7, 36, 0.48)', headLight: '#fbcfe8', headEnd: '#be185d', particle: '#f472b6' },
    { body: '#22c55e', dark: '#14532d', glow: 'rgba(134, 239, 172, 0.58)', shadow: 'rgba(5, 46, 22, 0.44)', headLight: '#bbf7d0', headEnd: '#15803d', particle: '#4ade80' },
    { body: '#06b6d4', dark: '#164e63', glow: 'rgba(103, 232, 249, 0.56)', shadow: 'rgba(8, 47, 73, 0.44)', headLight: '#cffafe', headEnd: '#0e7490', particle: '#22d3ee' }
];

class SoundFx {
    constructor() {
        this.ctx = null;
        this.muted = false;
    }

    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    tone(freq, duration, type = 'sine', volume = 0.08, delay = 0) {
        if (this.muted || !this.ctx) return;

        const start = this.ctx.currentTime + delay;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, start);
        gain.gain.setValueAtTime(volume, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(start);
        osc.stop(start + duration);
    }

    eat() {
        [392, 523, 659].forEach((freq, index) => {
            this.tone(freq, 0.12, 'triangle', 0.09, index * 0.065);
        });
    }

    wrong() {
        this.tone(170, 0.18, 'sawtooth', 0.12);
        this.tone(110, 0.22, 'sawtooth', 0.08, 0.08);
    }

    gameOver() {
        [330, 247, 196, 147].forEach((freq, index) => {
            this.tone(freq, 0.2, 'triangle', 0.1, index * 0.12);
        });
    }

    victory() {
        [392, 523, 659, 784, 1046].forEach((freq, index) => {
            this.tone(freq, 0.16, 'triangle', 0.1, index * 0.09);
        });
    }

    toggleMute() {
        this.muted = !this.muted;
        if (this.muted && window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        return this.muted;
    }
}

class WordSnakeGame {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.fx = new SoundFx();

        this.screenStart = document.getElementById('screen-start');
        this.screenGame = document.getElementById('screen-game');
        this.modalPause = document.getElementById('modal-pause');
        this.modalGameOver = document.getElementById('modal-gameover');
        this.targetValue = document.getElementById('target-value');
        this.bossHud = document.getElementById('boss-hud');
        this.chainLabel = document.querySelector('#boss-hud .boss-title');

        this.mode = 'vi-en';
        this.config = MODE_CONFIG[this.mode];
        this.vocab = FALLBACK_VOCAB;
        this.vocabSource = this.getSavedVocabSource();
        this.state = 'loading';
        this.score = 0;
        this.bestCombo = 0;
        this.combo = 0;
        this.correct = 0;
        this.incorrect = 0;
        this.lives = 3;
        this.frame = 0;
        this.elapsedGameSeconds = 0;
        this.timeLeft = 300;
        this.gameDurationSeconds = 300;
        this.lastTime = 0;
        this.pointerActive = false;
        this.mouse = { x: 0, y: 0 };
        this.head = { x: 0, y: 0, vx: 0, vy: 0, heading: 0 };
        this.trail = [];
        this.segments = [];
        this.foods = [];
        this.swampPatches = [];
        this.lotusFlowers = [];
        this.trainObstacles = [];
        this.meaningPopups = [];
        this.fishFrenzyTimer = 0;
        this.lotusBonusTimer = 0;
        this.nextLotusAmbientAt = 0;
        this.autoSnakeEnabled = false;
        this.autoSnake = null;
        this.autoSnakes = [];
        this.autoSnakeEnabledAt = 0;
        this.autoSnakeMaxCount = 0;
        this.autoSnakeGrowthTimer = 0;
        this.autoSnakeRespawnTimer = 0;
        this.autoSnakeColorIndex = 0;
        this.particles = [];
        this.currentPromptType = 'vi';
        this.currentItem = null;
        this.speechEnabled = true;
        this.speechQueue = [];
        this.speechSpeaking = false;
        this.hintEnabled = false;
        this.motoMode = false;
        this.keys = { left: false, right: false };
        this.worldBounds = { left: 0, top: 0, right: 0, bottom: 0 };
        this.wrongCooldown = 0;
        this.poisonTimer = 0;
        this.growthTimer = 0;
        this.bodyBiteCooldown = 0;
        this.speedMultiplier = 1;
        this.speedBoostUntil = 0;
        this.nextSpeedBoostAt = 0;
        this.speedBoostFlash = 0;
        this.lastPromptSpeechFrame = -Infinity;
        this.lastPromptSpeechTimeMs = -Infinity;
        this.lastPromptSpeechGameSecond = -Infinity;

        this.bindEvents();
        this.resizeCanvas();
        this.loadVocab();
        requestAnimationFrame((time) => this.loop(time));
    }

    async loadVocab() {
        const source = VOCAB_SOURCES[this.vocabSource] || VOCAB_SOURCES[DEFAULT_VOCAB_SOURCE];
        try {
            const response = await fetch(`global-success-vocabulary/${source.file}`);
            if (response.ok) {
                const data = await response.json();
                this.vocab = this.normalizeVocab(data);
            } else {
                await this.loadFallbackVocabFile();
            }
        } catch (error) {
            console.warn(`Using fallback vocabulary because ${source.file} could not be loaded.`, error);
            await this.loadFallbackVocabFile();
        }

        this.state = 'start';
        this.updateVocabSourceControl();
        this.updateStartHighScore();
        this.renderStartPlayHistory();
    }

    getSavedVocabSource() {
        const saved = localStorage.getItem('word_snake_vocab_source');
        return VOCAB_SOURCES[saved] ? saved : DEFAULT_VOCAB_SOURCE;
    }

    saveVocabSource(sourceKey) {
        if (!VOCAB_SOURCES[sourceKey]) return;
        this.vocabSource = sourceKey;
        localStorage.setItem('word_snake_vocab_source', sourceKey);
    }

    updateVocabSourceControl() {
        const select = document.getElementById('vocab-source-select');
        const count = document.getElementById('vocab-source-count');
        if (select) select.value = this.vocabSource;
        if (count) {
            const source = VOCAB_SOURCES[this.vocabSource] || VOCAB_SOURCES[DEFAULT_VOCAB_SOURCE];
            count.innerText = `${source.label} · ${this.vocab.length} words`;
        }
    }

    async loadFallbackVocabFile() {
        try {
            const response = await fetch('vocab.json');
            if (response.ok) {
                const data = await response.json();
                this.vocab = this.normalizeVocab(data);
            }
        } catch (error) {
            console.warn('Using built-in fallback vocabulary because vocab.json could not be loaded.', error);
        }
    }

    normalizeVocab(data) {
        const uniqueWords = new Set();
        return data
            .filter(item => item && item.word && item.meaning)
            .map(item => ({
                word: String(item.word).trim(),
                meaning: String(item.meaning).trim(),
                emoji: item.emoji || '🌱',
                topic: item.topic || '',
                grade: item.grade || null
            }))
            .filter(item => {
                const key = item.word.toLowerCase();
                if (!item.word || !item.meaning || uniqueWords.has(key)) return false;
                uniqueWords.add(key);
                return true;
            });
    }

    bindEvents() {
        window.addEventListener('resize', () => this.resizeCanvas());
        window.addEventListener('pointermove', (event) => this.updatePointer(event));
        window.addEventListener('pointerdown', (event) => {
            this.fx.init();
            this.updatePointer(event);
            this.pointerActive = true;
            if (event.button === 0 && event.target === this.canvas) {
                this.trySpeedBoost();
            }
        });

        document.querySelectorAll('.mode-btn').forEach((button) => {
            button.addEventListener('click', () => {
                document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                this.mode = button.dataset.mode;
                this.config = MODE_CONFIG[this.mode] || MODE_CONFIG['vi-en'];
                this.updateStartHighScore();
                this.renderStartPlayHistory();
            });
        });

        const vocabSourceSelect = document.getElementById('vocab-source-select');
        if (vocabSourceSelect) {
            vocabSourceSelect.value = this.vocabSource;
            vocabSourceSelect.addEventListener('change', async () => {
                this.saveVocabSource(vocabSourceSelect.value);
                this.state = 'loading';
                await this.loadVocab();
            });
        }

        document.getElementById('btn-play').addEventListener('click', () => {
            this.fx.init();
            this.startGame();
        });
        document.getElementById('btn-reset-state').addEventListener('click', () => this.resetLearningState());
        document.getElementById('btn-pause').addEventListener('click', () => this.pauseGame());
        document.getElementById('btn-resume').addEventListener('click', () => this.resumeGame());
        document.getElementById('btn-restart-paused').addEventListener('click', () => this.startGame());
        document.getElementById('btn-quit-paused').addEventListener('click', () => this.quitToMenu());
        document.getElementById('btn-play-again').addEventListener('click', () => this.startGame());
        document.getElementById('btn-quit-gameover').addEventListener('click', () => this.quitToMenu());

        const soundButton = document.getElementById('btn-sound-toggle');
        soundButton.addEventListener('click', () => {
            this.fx.init();
            const muted = this.fx.toggleMute();
            soundButton.innerText = muted ? '🔇' : '🔊';
            soundButton.classList.toggle('active', !muted);
            if (muted) this.clearSpeechQueue();
        });

        const speechButton = document.getElementById('btn-bilingual-toggle');
        speechButton.addEventListener('click', () => {
            this.speechEnabled = !this.speechEnabled;
            speechButton.classList.toggle('active', this.speechEnabled);
            speechButton.innerText = this.speechEnabled ? 'VOICE' : 'QUIET';
            if (!this.speechEnabled) this.clearSpeechQueue();
        });

        const hintButton = document.getElementById('btn-hint-toggle');
        hintButton.addEventListener('click', () => {
            this.hintEnabled = !this.hintEnabled;
            hintButton.classList.toggle('active', this.hintEnabled);
            hintButton.title = this.hintEnabled ? 'Hint is on' : 'Hint is off';
        });

        const autoSnakeButton = document.getElementById('btn-auto-snake-toggle');
        autoSnakeButton.addEventListener('click', () => {
            this.setAutoSnakeEnabled(!this.autoSnakeEnabled);
        });

        const motoButton = document.getElementById('btn-moto-toggle');
        motoButton.addEventListener('click', () => {
            this.setMotoMode(!this.motoMode);
            motoButton.classList.toggle('active', this.motoMode);
            motoButton.title = this.motoMode ? 'Moto camera is on' : 'Moto camera is off';
        });

        window.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                if (this.motoMode) event.preventDefault();
                if (event.key === 'ArrowLeft') this.keys.left = true;
                if (event.key === 'ArrowRight') this.keys.right = true;
            }
            if (event.key === 'Escape') {
                if (this.state === 'playing') this.pauseGame();
                else if (this.state === 'paused') this.resumeGame();
            }
        });

        window.addEventListener('keyup', (event) => {
            if (event.key === 'ArrowLeft') this.keys.left = false;
            if (event.key === 'ArrowRight') this.keys.right = false;
        });
    }

    resizeCanvas() {
        const scale = window.devicePixelRatio || 1;
        this.canvas.width = Math.floor(window.innerWidth * scale);
        this.canvas.height = Math.floor(window.innerHeight * scale);
        this.ctx.setTransform(scale, 0, 0, scale, 0, 0);
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.mouse.x = this.mouse.x || this.width / 2;
        this.mouse.y = this.mouse.y || this.height / 2;
    }

    updatePointer(event) {
        const rect = this.canvas.getBoundingClientRect();
        this.mouse.x = event.clientX - rect.left;
        this.mouse.y = event.clientY - rect.top;
        this.pointerActive = true;
    }

    isSurvivalMode() {
        return Boolean(this.config && this.config.survival);
    }

    isTrainMode() {
        return this.mode === 'train';
    }

    setMotoMode(enabled) {
        if (this.isSurvivalMode() && this.state === 'playing' && !enabled) {
            const motoButton = document.getElementById('btn-moto-toggle');
            if (motoButton) {
                motoButton.classList.add('active');
                motoButton.title = this.isTrainMode() ? 'Country Train uses moto camera' : 'Lotus Pond uses moto camera';
            }
            return;
        }
        if (this.motoMode === enabled) return;

        if (!enabled && this.state === 'playing') {
            const camera = this.getCamera();
            this.translateWorld(-camera.x, -camera.y);
        }

        this.motoMode = enabled;
        this.configureWorldBounds();

        if (enabled && this.state === 'playing') {
            this.centerMotoWorldAroundHead();
        }
    }

    setAutoSnakeEnabled(enabled) {
        const nextEnabled = Boolean(enabled && this.isSurvivalMode() && this.state === 'playing');
        this.autoSnakeEnabled = nextEnabled;
        if (nextEnabled) {
            this.autoSnake = null;
            this.autoSnakes = [];
            this.autoSnakeEnabledAt = this.elapsedGameSeconds;
            this.autoSnakeMaxCount = 1;
            this.autoSnakeRespawnTimer = 0;
            this.fx.tone(440, 0.08, 'triangle', 0.035);
            this.fx.tone(660, 0.1, 'sine', 0.03, 0.06);
        } else {
            this.autoSnake = null;
            this.autoSnakes = [];
            this.autoSnakeMaxCount = 0;
            this.autoSnakeRespawnTimer = 0;
        }
        this.updateAutoSnakeButton();
    }

    updateAutoSnakeButton() {
        const button = document.getElementById('btn-auto-snake-toggle');
        if (!button) return;
        button.classList.toggle('active', this.autoSnakeEnabled);
        const count = this.getActiveAutoSnakes().length;
        const maxCount = this.autoSnakeEnabled ? this.getAutoSnakeMaxCount() : 0;
        const waiting = this.autoSnakeEnabled && count < maxCount;
        button.classList.toggle('waiting', waiting);
        button.title = waiting ? `Auto snake ${count}/${maxCount}, spawning replacement` : (this.autoSnakeEnabled ? `Auto snake ${count}/${maxCount}` : 'Auto snake is off');
        button.setAttribute('aria-label', button.title);
        button.setAttribute('aria-pressed', String(this.autoSnakeEnabled));
        button.textContent = waiting ? '⏳' : '🤖';
    }

    getActiveAutoSnakes() {
        return (this.autoSnakes || []).filter(snake => snake && snake.active);
    }

    syncPrimaryAutoSnake() {
        this.autoSnakes = this.getActiveAutoSnakes();
        this.autoSnake = this.autoSnakes[0] || null;
    }

    getAutoSnakeMaxCount() {
        if (!this.autoSnakeEnabled) return 0;
        return AUTO_SNAKE_MAX_COUNT;
    }

    initAutoSnake() {
        const pond = this.getLotusPondShape(42);
        const angle = this.head.heading + Math.PI;
        let x = pond.cx + Math.cos(angle) * pond.rx * 0.38;
        let y = pond.cy + Math.sin(angle) * pond.ry * 0.38;

        for (let attempt = 0; attempt < 24; attempt++) {
            const clearFromPlayer = Math.hypot(x - this.head.x, y - this.head.y) > 240;
            const clearFromRivals = this.getActiveAutoSnakes().every(snake => Math.hypot(x - snake.head.x, y - snake.head.y) > 180);
            if (!this.isPointOnSwampLand(x, y, 34) && clearFromPlayer && clearFromRivals) break;
            const randomAngle = Math.random() * Math.PI * 2;
            const radius = 0.18 + Math.random() * 0.55;
            x = pond.cx + Math.cos(randomAngle) * pond.rx * radius;
            y = pond.cy + Math.sin(randomAngle) * pond.ry * radius;
        }

        const colors = AUTO_SNAKE_COLORS[this.autoSnakeColorIndex % AUTO_SNAKE_COLORS.length];
        this.autoSnakeColorIndex++;
        const heading = Math.random() * Math.PI * 2;
        const snake = {
            head: { x, y, vx: 0, vy: 0, heading },
            steerHeading: heading,
            trail: [{ x, y }],
            segments: 1,
            active: true,
            bodyBiteCooldown: 0,
            growthTimer: 0,
            aiThinkTimer: Math.random() * 2,
            desiredHeading: heading,
            lastDangerScore: 100,
            colors
        };
        this.autoSnakes.push(snake);
        this.syncPrimaryAutoSnake();
        this.updateAutoSnakeButton();
    }

    configureWorldBounds() {
        if (this.isSurvivalMode()) {
            const pondWidth = Math.max(this.width * 1.85, 1320);
            const pondHeight = Math.max((this.height - 120) * 1.65, 820);
            this.worldBounds = {
                left: (this.width - pondWidth) / 2,
                top: 120 + ((this.height - 120) - pondHeight) / 2,
                right: (this.width + pondWidth) / 2,
                bottom: 120 + ((this.height - 120) + pondHeight) / 2
            };
            return;
        }

        this.worldBounds = {
            left: 28,
            top: 120,
            right: this.width - 28,
            bottom: this.height - 32
        };
    }

    centerMotoWorldAroundHead() {
        const centerX = (this.worldBounds.left + this.worldBounds.right) / 2;
        const centerY = (this.worldBounds.top + this.worldBounds.bottom) / 2;
        this.translateWorld(centerX - this.head.x, centerY - this.head.y);
    }

    translateWorld(dx, dy) {
        this.head.x += dx;
        this.head.y += dy;
        this.trail.forEach(point => {
            point.x += dx;
            point.y += dy;
        });
        this.foods.forEach(food => {
            food.x += dx;
            food.y += dy;
        });
        this.particles.forEach(particle => {
            particle.x += dx;
            particle.y += dy;
        });
    }

    getCamera() {
        if (!this.motoMode) return { x: 0, y: 0 };
        return {
            x: this.head.x - this.width / 2,
            y: this.head.y - this.height / 2
        };
    }

    worldToScreen(point) {
        const camera = this.getCamera();
        return {
            x: point.x - camera.x,
            y: point.y - camera.y
        };
    }

    startGame() {
        this.clearSpeechQueue();
        document.body.classList.add('snake-mode');
        document.body.classList.toggle('swamp-mode', this.mode === 'swamp');
        document.body.classList.toggle('train-mode', this.mode === 'train');
        this.screenStart.classList.remove('active');
        this.screenGame.classList.add('active');
        this.modalPause.classList.add('hidden');
        this.modalGameOver.classList.add('hidden');
        this.bossHud.classList.add('hidden');

        this.config = MODE_CONFIG[this.mode] || MODE_CONFIG['vi-en'];
        if (this.isSurvivalMode()) {
            this.motoMode = true;
            const motoButton = document.getElementById('btn-moto-toggle');
            if (motoButton) {
                motoButton.classList.add('active');
                motoButton.title = this.isTrainMode() ? 'Country Train uses moto camera' : 'Lotus Pond uses moto camera';
            }
        }
        this.score = 0;
        this.combo = 0;
        this.bestCombo = 0;
        this.correct = 0;
        this.incorrect = 0;
        this.lives = 3;
        this.frame = 0;
        this.elapsedGameSeconds = 0;
        this.timeLeft = this.gameDurationSeconds;
        this.wrongCooldown = 0;
        this.poisonTimer = 0;
        this.growthTimer = 0;
        this.bodyBiteCooldown = 0;
        this.speedMultiplier = 1;
        this.speedBoostUntil = 0;
        this.nextSpeedBoostAt = 0;
        this.speedBoostFlash = 0;
        this.lastPromptSpeechFrame = -Infinity;
        this.lastPromptSpeechTimeMs = -Infinity;
        this.lastPromptSpeechGameSecond = -Infinity;
        this.particles = [];
        this.foods = [];
        this.swampPatches = [];
        this.lotusFlowers = [];
        this.trainObstacles = [];
        this.meaningPopups = [];
        this.fishFrenzyTimer = 0;
        this.lotusBonusTimer = 0;
        this.nextLotusAmbientAt = 0;
        this.autoSnakeEnabled = false;
        this.autoSnake = null;
        this.autoSnakes = [];
        this.autoSnakeEnabledAt = 0;
        this.autoSnakeMaxCount = 0;
        this.autoSnakeGrowthTimer = 0;
        this.autoSnakeRespawnTimer = 0;
        this.autoSnakeColorIndex = 0;
        this.updateAutoSnakeButton();
        this.trail = [];
        this.configureWorldBounds();
        const startX = this.motoMode ? (this.worldBounds.left + this.worldBounds.right) / 2 : this.width / 2;
        const startY = this.motoMode ? (this.worldBounds.top + this.worldBounds.bottom) / 2 : this.height / 2;
        this.head = {
            x: startX,
            y: startY,
            vx: this.config.speed,
            vy: 0,
            heading: 0
        };
        this.mouse = { x: this.width / 2 + 120, y: this.height / 2 };

        this.currentPromptType = this.getFirstPromptType();
        this.currentItem = null;
        this.segments = [{
            type: this.currentPromptType,
            item: null,
            label: ''
        }];

        if (this.isSurvivalMode()) {
            if (this.isTrainMode()) {
                this.generateTrainTerrain();
            } else {
                this.generateSwampTerrain();
            }
        }
        this.spawnFoods();
        if (!this.isSurvivalMode()) {
            this.selectRandomTargetFromFoods();
        }
        this.updateHUD();
        this.state = 'playing';
        if (!this.isSurvivalMode()) {
            this.speakPair(this.currentItem, this.currentPromptType);
        }
    }

    getFirstPromptType() {
        if (this.config.firstPromptType === 'random') {
            return Math.random() < 0.5 ? 'vi' : 'en';
        }
        return this.config.firstPromptType;
    }

    pickWord(excludeItem = null) {
        if (this.vocab.length === 0) return FALLBACK_VOCAB[0];
        const pool = excludeItem
            ? this.vocab.filter(item => item.word !== excludeItem.word)
            : this.vocab;
        return pool[Math.floor(Math.random() * pool.length)] || this.vocab[0];
    }

    getLabel(item, type) {
        return type === 'vi'
            ? `${item.emoji || ''} ${item.meaning}`.trim()
            : item.word;
    }

    getTargetType() {
        if (this.isSurvivalMode()) return 'food';
        if (this.mode === 'en-vi') return 'vi';
        return 'en';
    }

    getPromptTypeForMode() {
        if (this.isSurvivalMode()) return 'food';
        if (this.mode === 'en-vi') return 'en';
        if (this.mode === 'mixed') return 'en';
        return 'vi';
    }

    spawnFoods() {
        const targetType = this.getTargetType();
        this.foods = this.shuffle(this.vocab)
            .slice(0, this.isSurvivalMode() ? 8 : 4)
            .map((item, index) => this.createFood(item, targetType, index));
        this.foods.forEach((food) => this.placeFood(food));
    }

    createFood(item, type, index = 0) {
        const angle = Math.random() * Math.PI * 2;
        const driftSpeed = this.isSurvivalMode()
            ? 0.08 + Math.random() * 0.1
            : (0.35 + Math.random() * 0.75) * 0.5;

        return {
            item,
            type,
            label: this.isSurvivalMode() ? item.word : this.getLabel(item, type),
            x: 0,
            y: 0,
            vx: Math.cos(angle) * driftSpeed,
            vy: Math.sin(angle) * driftSpeed,
            radius: 28,
            pulse: Math.random() * Math.PI * 2,
            spawnAge: 0,
            wavePhase: Math.random() * Math.PI * 2,
            waveStrength: this.isSurvivalMode()
                ? 0.004 + Math.random() * 0.006
                : 0.012 + Math.random() * 0.012,
            color: ['#38bdf8', '#ffd000', '#ff8c42', '#f472b6', '#00ff88'][index % 5]
        };
    }

    addRandomFood() {
        const visibleWords = new Set(this.foods.map(food => food.item.word.toLowerCase()));
        const pool = this.vocab.filter(item => !visibleWords.has(item.word.toLowerCase()));
        const item = pool.length > 0
            ? pool[Math.floor(Math.random() * pool.length)]
            : this.pickWord();
        const food = this.createFood(item, this.getTargetType(), this.foods.length);
        this.placeFood(food);
        this.foods.push(food);
    }

    placeFood(food) {
        const bounds = this.getFoodBounds();
        const margin = this.isSurvivalMode() ? 46 : 86;
        let tries = 0;

        do {
            food.x = bounds.left + margin + Math.random() * Math.max(1, bounds.right - bounds.left - margin * 2);
            food.y = bounds.top + margin + Math.random() * Math.max(1, bounds.bottom - bounds.top - margin * 2);
            tries++;
        } while (tries < 80 && this.isFoodTooClose(food));
    }

    getFoodBounds() {
        if (this.isSurvivalMode()) {
            if (this.isTrainMode()) {
                const land = this.trainLand || {
                    cx: (this.worldBounds.left + this.worldBounds.right) / 2,
                    cy: (this.worldBounds.top + this.worldBounds.bottom) / 2,
                    rx: (this.worldBounds.right - this.worldBounds.left) * 0.4,
                    ry: (this.worldBounds.bottom - this.worldBounds.top) * 0.36
                };
                return {
                    left: land.cx - land.rx,
                    top: land.cy - land.ry,
                    right: land.cx + land.rx,
                    bottom: land.cy + land.ry
                };
            }
            const pond = this.getLotusPondShape(18);
            return {
                left: pond.cx - pond.rx,
                top: pond.cy - pond.ry,
                right: pond.cx + pond.rx,
                bottom: pond.cy + pond.ry
            };
        }
        if (this.motoMode) return this.worldBounds;
        return {
            left: 0,
            top: 64,
            right: this.width,
            bottom: this.height
        };
    }

    isFoodTooClose(food) {
        const headDistance = Math.hypot(food.x - this.head.x, food.y - this.head.y);
        if (headDistance < 140) return true;
        if (this.isSurvivalMode() && this.isPointOnSwampLand(food.x, food.y, food.radius + 28)) return true;

        return this.foods.some(other => (
            other !== food &&
            other.x &&
            Math.hypot(food.x - other.x, food.y - other.y) < 150
        ));
    }

    generateSwampTerrain() {
        const b = this.worldBounds;
        const w = b.right - b.left;
        const h = b.bottom - b.top;
        const makePatch = (x, y, radius, rot = 0) => {
            const sizeJitter = 0.78 + Math.random() * 0.5;
            const roundnessJitter = 0.9 + Math.random() * 0.18;
            const baseRadius = Math.max(34, Math.min(w, h) * radius * sizeJitter);
            const flowerRadius = Math.max(14, baseRadius * 0.5);
            const leafRadius = flowerRadius * 3;
            return {
                x: b.left + w * x,
                y: b.top + h * y,
                rx: leafRadius * roundnessJitter,
                ry: leafRadius * (0.96 + Math.random() * 0.12),
                flowerRadius,
                rot
            };
        };
        const makeFlower = (x, y, radius, rot = 0) => ({
            x: b.left + w * x,
            y: b.top + h * y,
            radius,
            rot
        });

        this.swampPatches = [
            makePatch(0.22, 0.22, 0.05, -0.45),
            makePatch(0.58, 0.24, 0.045, 0.22),
            makePatch(0.8, 0.34, 0.054, 0.48),
            makePatch(0.36, 0.43, 0.052, -0.18),
            makePatch(0.64, 0.52, 0.048, 0.72),
            makePatch(0.18, 0.65, 0.046, 0.34),
            makePatch(0.47, 0.75, 0.055, -0.38),
            makePatch(0.77, 0.72, 0.047, 0.1),
            makePatch(0.31, 0.58, 0.04, 0.58),
            makePatch(0.52, 0.34, 0.038, -0.62),
            makePatch(0.69, 0.82, 0.04, -0.25),
            makePatch(0.86, 0.55, 0.036, 0.82)
        ];

        const flowerRadius = (patchIndex) => {
            const patch = this.swampPatches[patchIndex];
            return patch.flowerRadius;
        };

        this.lotusFlowers = [
            makeFlower(0.3, 0.32, flowerRadius(0), -0.2),
            makeFlower(0.7, 0.28, flowerRadius(2), 0.4),
            makeFlower(0.52, 0.47, flowerRadius(3), 0.1),
            makeFlower(0.28, 0.74, flowerRadius(6), -0.55),
            makeFlower(0.72, 0.66, flowerRadius(7), 0.3),
            makeFlower(0.4, 0.6, flowerRadius(8), 0.52),
            makeFlower(0.58, 0.34, flowerRadius(9), -0.4),
            makeFlower(0.86, 0.55, flowerRadius(11), 0.75)
        ];
    }

    generateTrainTerrain() {
        const b = this.worldBounds;
        const w = b.right - b.left;
        const h = b.bottom - b.top;
        this.trainLand = {
            cx: (b.left + b.right) / 2,
            cy: (b.top + b.bottom) / 2,
            rx: w * 0.49,
            ry: h * 0.45
        };
        const makeObstacle = (type, x, y, rx, ry, rot = 0) => ({
            type,
            x: b.left + w * x,
            y: b.top + h * y,
            rx: Math.max(36, Math.min(w, h) * rx),
            ry: Math.max(28, Math.min(w, h) * ry),
            rot,
            hitTimer: 0
        });

        this.trainObstacles = [
            makeObstacle('pine', 0.42, 0.34, 0.032, 0.04, 0.08),
            makeObstacle('pine', 0.73, 0.54, 0.035, 0.044, -0.22),
            makeObstacle('pine', 0.5, 0.76, 0.03, 0.038, 0.32),
            makeObstacle('house', 0.58, 0.42, 0.045, 0.038, 0.08),
            makeObstacle('house', 0.39, 0.62, 0.047, 0.04, -0.18),
            makeObstacle('pine', 0.18, 0.24, 0.03, 0.04, -0.12),
            makeObstacle('pine', 0.21, 0.28, 0.034, 0.043, 0.18),
            makeObstacle('pine', 0.25, 0.22, 0.028, 0.038, -0.28),
            makeObstacle('house', 0.31, 0.3, 0.044, 0.036, 0.08),
            makeObstacle('house', 0.36, 0.28, 0.04, 0.034, -0.12),
            makeObstacle('pine', 0.65, 0.24, 0.032, 0.042, 0.22),
            makeObstacle('pine', 0.69, 0.27, 0.03, 0.039, -0.18),
            makeObstacle('house', 0.76, 0.3, 0.045, 0.037, 0.16),
            makeObstacle('house', 0.8, 0.34, 0.041, 0.035, -0.1),
            makeObstacle('pine', 0.84, 0.29, 0.03, 0.04, 0.34),
            makeObstacle('house', 0.2, 0.7, 0.044, 0.036, -0.2),
            makeObstacle('house', 0.25, 0.74, 0.042, 0.034, 0.12),
            makeObstacle('pine', 0.31, 0.69, 0.033, 0.042, 0.18),
            makeObstacle('pine', 0.34, 0.76, 0.03, 0.039, -0.28),
            makeObstacle('pine', 0.66, 0.7, 0.032, 0.041, -0.14),
            makeObstacle('house', 0.72, 0.73, 0.046, 0.038, 0.1),
            makeObstacle('pine', 0.78, 0.69, 0.031, 0.04, 0.26),
            makeObstacle('house', 0.82, 0.76, 0.04, 0.034, -0.18),
            makeObstacle('pine', 0.57, 0.72, 0.034, 0.052, -0.08),
            makeObstacle('pine', 0.61, 0.78, 0.032, 0.05, 0.16),
            makeObstacle('pine', 0.88, 0.68, 0.034, 0.054, 0.08),
            makeObstacle('pine', 0.74, 0.84, 0.03, 0.048, -0.2),
            makeObstacle('pine', 0.14, 0.18, 0.028, 0.046, 0.12),
            makeObstacle('pine', 0.9, 0.24, 0.03, 0.048, -0.12)
        ];
    }

    isPointOnSwampLand(x, y, padding = 0) {
        if (!this.isSurvivalMode()) return false;
        if (this.isTrainMode()) return this.isPointOnTrainObstacle(x, y, padding);

        const pond = this.getLotusPondShape(padding);
        const nx = (x - pond.cx) / pond.rx;
        const ny = (y - pond.cy) / pond.ry;
        if (nx * nx + ny * ny > 1) {
            return true;
        }

        return this.swampPatches.some(patch => this.isPointInSwampPatch(x, y, patch, padding)) ||
            this.lotusFlowers.some(flower => Math.hypot(x - flower.x, y - flower.y) <= flower.radius + padding);
    }

    isPointOnTrainObstacle(x, y, padding = 0) {
        if (!this.isPointOnTrainLand(x, y, padding)) return true;
        return this.trainObstacles.some(obstacle => this.isPointInTrainObstacle(x, y, obstacle, padding));
    }

    isPointOnTrainLand(x, y, padding = 0) {
        if (!this.trainLand) return true;
        const halfWidth = Math.max(120, this.trainLand.rx - padding);
        const halfHeight = Math.max(90, this.trainLand.ry - padding);
        return Math.abs(x - this.trainLand.cx) <= halfWidth &&
            Math.abs(y - this.trainLand.cy) <= halfHeight;
    }

    getLotusPondShape(padding = 0) {
        const b = this.worldBounds;
        const width = b.right - b.left;
        const height = b.bottom - b.top;
        return {
            cx: (b.left + b.right) / 2,
            cy: (b.top + b.bottom) / 2,
            rx: Math.max(120, width * 0.48 - padding),
            ry: Math.max(90, height * 0.46 - padding)
        };
    }

    isPointInSwampPatch(x, y, patch, padding = 0) {
        const cos = Math.cos(-patch.rot);
        const sin = Math.sin(-patch.rot);
        const dx = x - patch.x;
        const dy = y - patch.y;
        const localX = dx * cos - dy * sin;
        const localY = dx * sin + dy * cos;
        const rx = patch.rx + padding;
        const ry = patch.ry + padding;
        return (localX * localX) / (rx * rx) + (localY * localY) / (ry * ry) <= 1;
    }

    isPointInTrainObstacle(x, y, obstacle, padding = 0) {
        const cos = Math.cos(-obstacle.rot);
        const sin = Math.sin(-obstacle.rot);
        const dx = x - obstacle.x;
        const dy = y - obstacle.y;
        const localX = dx * cos - dy * sin;
        const localY = dx * sin + dy * cos;
        const rx = obstacle.rx + padding;
        const ry = obstacle.ry + padding;
        return (localX * localX) / (rx * rx) + (localY * localY) / (ry * ry) <= 1;
    }

    shuffle(items) {
        const result = [...items];
        for (let index = result.length - 1; index > 0; index--) {
            const swapIndex = Math.floor(Math.random() * (index + 1));
            [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
        }
        return result;
    }

    selectRandomTargetFromFoods() {
        if (this.isSurvivalMode()) return;
        if (this.foods.length === 0) {
            this.addRandomFood();
        }

        const targetType = this.getTargetType();
        this.foods.forEach((food) => {
            food.type = targetType;
            food.label = this.getLabel(food.item, targetType);
        });

        const food = this.foods[Math.floor(Math.random() * this.foods.length)];
        this.currentItem = food.item;
        this.currentPromptType = this.getPromptTypeForMode();
        this.segments[0] = {
            type: this.currentPromptType,
            item: this.currentItem,
            label: this.getLabel(this.currentItem, this.currentPromptType)
        };
    }

    loop(time) {
        const rawDeltaMs = this.lastTime ? time - this.lastTime : 0;
        const deltaMs = Math.min(100, Math.max(0, rawDeltaMs));
        const delta = deltaMs / 16.6667;
        const deltaSeconds = deltaMs / 1000;
        this.lastTime = time;

        if (this.state === 'playing') {
            this.update(delta, deltaSeconds);
        }
        this.draw();

        requestAnimationFrame((nextTime) => this.loop(nextTime));
    }

    update(delta, deltaSeconds) {
        this.frame += delta;
        this.elapsedGameSeconds += deltaSeconds;
        this.timeLeft = Math.max(0, this.gameDurationSeconds - Math.floor(this.elapsedGameSeconds));
        if (this.timeLeft <= 0) {
            this.endGame('VICTORY!', true);
            return;
        }

        if (this.wrongCooldown > 0) {
            this.wrongCooldown -= delta;
        }
        if (this.poisonTimer > 0) {
            this.poisonTimer -= delta;
        }
        if (this.growthTimer > 0) {
            this.growthTimer -= delta;
        }
        if (this.bodyBiteCooldown > 0) {
            this.bodyBiteCooldown -= delta;
        }
        if (this.speedMultiplier > 1 && this.elapsedGameSeconds >= this.speedBoostUntil) {
            this.speedMultiplier = 1;
        }
        if (this.speedBoostFlash > 0) {
            this.speedBoostFlash -= delta;
        }
        if (this.fishFrenzyTimer > 0) {
            this.fishFrenzyTimer -= delta;
        }
        if (this.lotusBonusTimer > 0) {
            this.lotusBonusTimer -= delta;
        }
        if (this.autoSnakeGrowthTimer > 0) {
            this.autoSnakeGrowthTimer -= delta;
        }
        this.swampPatches.forEach((patch) => {
            if (patch.hitTimer > 0) patch.hitTimer -= delta;
        });
        this.lotusFlowers.forEach((flower) => {
            if (flower.hitTimer > 0) flower.hitTimer -= delta;
        });
        this.trainObstacles.forEach((obstacle) => {
            if (obstacle.hitTimer > 0) obstacle.hitTimer -= delta;
        });
        this.getActiveAutoSnakes().forEach((snake) => {
            if (snake.growthTimer > 0) {
                snake.growthTimer -= delta;
            }
        });
        this.updateMeaningPopups(delta);
        this.playLotusAmbientIfNeeded();

        this.updateSnake(deltaSeconds, delta);
        this.updateAutoSnake(deltaSeconds, delta);
        this.updateFoods(delta);
        this.updateParticles(delta);
        this.checkBoundaryCollision();
        this.checkSelfCollision();
        this.checkAutoSnakeSelfCollision();
        this.checkFoodCollisions();
        this.checkAutoSnakeFoodCollisions();
        this.checkInterSnakeCollisions();
        this.replayPromptAudioIfNeeded();
        this.updateHUD();
    }

    updateSnake(deltaSeconds, deltaFrames) {
        const camera = this.getCamera();
        const targetX = (this.pointerActive ? this.mouse.x : this.width / 2) + camera.x;
        const targetY = (this.pointerActive ? this.mouse.y : this.height / 2) + camera.y;
        const dx = targetX - this.head.x;
        const dy = targetY - this.head.y;
        const turnRate = 5.7 * deltaSeconds;
        const keyboardTurn = (this.keys.right ? 1 : 0) - (this.keys.left ? 1 : 0);

        if (this.motoMode && keyboardTurn !== 0) {
            this.head.heading += keyboardTurn * turnRate;
        } else {
            const desiredHeading = Math.atan2(dy, dx);
            const headingDelta = Math.atan2(
                Math.sin(desiredHeading - this.head.heading),
                Math.cos(desiredHeading - this.head.heading)
            );
            this.head.heading += Math.max(-turnRate, Math.min(turnRate, headingDelta));
        }

        const margin = 38;
        const wallTurnBlend = 1 - Math.pow(0.82, deltaFrames);
        if (this.motoMode) {
            const bounds = this.worldBounds;
            if (this.isSurvivalMode() && !this.isTrainMode()) {
                this.turnAwayFromLotusPondBank(wallTurnBlend, margin);
            } else if (this.isTrainMode()) {
                // Train terrain uses rectangular islands and bridges, so avoid the hidden lotus-pond ellipse steering.
            } else {
                if (this.head.x < bounds.left + margin) this.head.heading = this.blendHeading(this.head.heading, 0, wallTurnBlend);
                if (this.head.x > bounds.right - margin) this.head.heading = this.blendHeading(this.head.heading, Math.PI, wallTurnBlend);
                if (this.head.y < bounds.top + margin) this.head.heading = this.blendHeading(this.head.heading, Math.PI / 2, wallTurnBlend);
                if (this.head.y > bounds.bottom - margin) this.head.heading = this.blendHeading(this.head.heading, -Math.PI / 2, wallTurnBlend);
            }
        } else if (this.isSurvivalMode()) {
            const bounds = this.worldBounds;
            if (this.head.x < bounds.left + margin) this.head.heading = this.blendHeading(this.head.heading, 0, wallTurnBlend);
            if (this.head.x > bounds.right - margin) this.head.heading = this.blendHeading(this.head.heading, Math.PI, wallTurnBlend);
            if (this.head.y < bounds.top + margin) this.head.heading = this.blendHeading(this.head.heading, Math.PI / 2, wallTurnBlend);
            if (this.head.y > bounds.bottom - margin) this.head.heading = this.blendHeading(this.head.heading, -Math.PI / 2, wallTurnBlend);
        } else {
            if (this.head.x < margin) this.head.heading = this.blendHeading(this.head.heading, 0, wallTurnBlend);
            if (this.head.x > this.width - margin) this.head.heading = this.blendHeading(this.head.heading, Math.PI, wallTurnBlend);
            if (this.head.y < 120 + margin) this.head.heading = this.blendHeading(this.head.heading, Math.PI / 2, wallTurnBlend);
            if (this.head.y > this.height - margin) this.head.heading = this.blendHeading(this.head.heading, -Math.PI / 2, wallTurnBlend);
        }

        const modeSpeedScale = this.motoMode ? 0.8 : 1;
        const speed = this.config.speed * 60 * 0.7 * modeSpeedScale * this.speedMultiplier;
        this.head.vx = Math.cos(this.head.heading) * speed;
        this.head.vy = Math.sin(this.head.heading) * speed;

        this.head.x += this.head.vx * deltaSeconds;
        this.head.y += this.head.vy * deltaSeconds;
        if (this.motoMode) {
            const bounds = this.worldBounds;
            this.head.x = Math.max(bounds.left + 24, Math.min(bounds.right - 24, this.head.x));
            this.head.y = Math.max(bounds.top + 24, Math.min(bounds.bottom - 24, this.head.y));
        } else if (this.isSurvivalMode()) {
            const bounds = this.worldBounds;
            this.head.x = Math.max(bounds.left + 24, Math.min(bounds.right - 24, this.head.x));
            this.head.y = Math.max(bounds.top + 24, Math.min(bounds.bottom - 24, this.head.y));
        } else {
            this.head.x = Math.max(28, Math.min(this.width - 28, this.head.x));
            this.head.y = Math.max(120, Math.min(this.height - 32, this.head.y));
        }

        this.resolveSwampLandCollision();

        this.trail.unshift({ x: this.head.x, y: this.head.y });
        const maxTrailLength = 1200;
        if (this.trail.length > maxTrailLength) {
            this.trail.length = maxTrailLength;
        }
    }

    blendHeading(from, to, amount) {
        const delta = Math.atan2(Math.sin(to - from), Math.cos(to - from));
        return from + delta * amount;
    }

    turnAwayFromLotusPondBank(blendAmount, margin) {
        const pond = this.getLotusPondShape(margin);
        const nx = (this.head.x - pond.cx) / pond.rx;
        const ny = (this.head.y - pond.cy) / pond.ry;
        const distance = nx * nx + ny * ny;
        if (distance < 0.82) return;

        const backToCenter = Math.atan2(pond.cy - this.head.y, pond.cx - this.head.x);
        this.head.heading = this.blendHeading(this.head.heading, backToCenter, Math.max(blendAmount, 0.08));
    }

    updateAutoSnake(deltaSeconds, deltaFrames) {
        if (!this.autoSnakeEnabled) return;
        this.syncPrimaryAutoSnake();
        this.autoSnakeMaxCount = this.getAutoSnakeMaxCount();
        if (this.autoSnakes.length < this.autoSnakeMaxCount) {
            this.autoSnakeRespawnTimer -= deltaFrames;
            if (this.autoSnakeRespawnTimer <= 0) {
                this.initAutoSnake();
                this.autoSnakeRespawnTimer = AUTO_SNAKE_SPAWN_STAGGER_FRAMES;
            }
        } else {
            this.autoSnakeRespawnTimer = 0;
        }

        this.getActiveAutoSnakes().forEach((snake) => {
            this.updateSingleAutoSnake(snake, deltaSeconds, deltaFrames);
        });
        this.syncPrimaryAutoSnake();
    }

    updateSingleAutoSnake(snake, deltaSeconds, deltaFrames) {
        if (snake.bodyBiteCooldown > 0) {
            snake.bodyBiteCooldown -= deltaFrames;
        }

        snake.aiThinkTimer = (snake.aiThinkTimer || 0) - deltaFrames;
        if (snake.aiThinkTimer <= 0) {
            const target = this.getAutoSnakeTarget(snake);
            let desiredHeading = target
                ? Math.atan2(target.y - snake.head.y, target.x - snake.head.x)
                : snake.head.heading + Math.sin(this.frame * 0.018) * 0.35;
            desiredHeading = this.getAutoSnakeAvoidanceHeading(snake, desiredHeading, target);
            desiredHeading = this.getAutoSnakeBodyAvoidanceHeading(snake, desiredHeading);
            desiredHeading = this.getSaferAutoSnakeHeading(snake, desiredHeading, target);
            snake.desiredHeading = desiredHeading;
            snake.lastDangerScore = this.scoreAutoSnakeHeading(snake, desiredHeading, target);
            snake.aiThinkTimer = 6;
        }

        const desiredHeading = snake.desiredHeading ?? snake.head.heading;
        const steeringBlend = 1 - Math.pow(0.9, deltaFrames);
        snake.steerHeading = this.blendHeading(snake.steerHeading ?? snake.head.heading, desiredHeading, steeringBlend);
        const turnRate = ((snake.lastDangerScore ?? 100) < -20 ? 7.2 : 5.0) * deltaSeconds;
        const headingDelta = Math.atan2(
            Math.sin(snake.steerHeading - snake.head.heading),
            Math.cos(snake.steerHeading - snake.head.heading)
        );
        snake.head.heading += Math.max(-turnRate, Math.min(turnRate, headingDelta));

        this.turnAutoSnakeAwayFromLotusPondBank(snake, 1 - Math.pow(0.82, deltaFrames), 34);

        const tightTurnSlowdown = 1 - Math.min(0.22, Math.abs(headingDelta) / Math.PI * 0.28);
        const speed = this.config.speed * 60 * 0.7 * 0.78 * this.speedMultiplier * tightTurnSlowdown;
        snake.head.vx = Math.cos(snake.head.heading) * speed;
        snake.head.vy = Math.sin(snake.head.heading) * speed;
        snake.head.x += snake.head.vx * deltaSeconds;
        snake.head.y += snake.head.vy * deltaSeconds;

        const bounds = this.worldBounds;
        snake.head.x = Math.max(bounds.left + 24, Math.min(bounds.right - 24, snake.head.x));
        snake.head.y = Math.max(bounds.top + 24, Math.min(bounds.bottom - 24, snake.head.y));
        this.resolveAutoSnakeLandCollision(snake);

        snake.trail.unshift({ x: snake.head.x, y: snake.head.y });
        if (snake.trail.length > 900) snake.trail.length = 900;
    }

    getAutoSnakeTarget(snake = this.autoSnake) {
        if (this.foods.length === 0 || !snake) return null;
        const heading = snake.head.heading;
        return this.foods.reduce((best, food) => {
            const distance = Math.hypot(food.x - snake.head.x, food.y - snake.head.y);
            const angle = Math.atan2(food.y - snake.head.y, food.x - snake.head.x);
            const turn = Math.abs(Math.atan2(Math.sin(angle - heading), Math.cos(angle - heading)));
            const frontBias = Math.cos(turn);
            const score = distance + turn * 210 + (frontBias < -0.15 ? 520 : 0);
            if (!best || score < best.score) return { ...food, distance, score };
            return best;
        }, null);
    }

    getAutoSnakeAvoidanceHeading(snake, desiredHeading, target = null) {
        const playerDistance = Math.hypot(this.head.x - snake.head.x, this.head.y - snake.head.y);
        if (playerDistance < 230) {
            const awayFromPlayer = Math.atan2(snake.head.y - this.head.y, snake.head.x - this.head.x);
            const strength = Math.max(0.28, 1 - playerDistance / 230);
            desiredHeading = this.blendHeading(desiredHeading, awayFromPlayer, strength);
        }

        if (this.isAutoSnakeHeadingDangerous(snake, desiredHeading, target)) {
            const left = snake.head.heading - Math.PI * 0.42;
            const right = snake.head.heading + Math.PI * 0.42;
            desiredHeading = this.scoreAutoSnakeHeading(snake, left, target) > this.scoreAutoSnakeHeading(snake, right, target) ? left : right;
        }
        return desiredHeading;
    }

    getAutoSnakeBodyAvoidanceHeading(snake, desiredHeading) {
        const bodyLength = this.getAutoSnakeBodyLength(snake);
        if (bodyLength < 150) return desiredHeading;

        let avoidX = 0;
        let avoidY = 0;
        const dangerRange = Math.min(260, 125 + snake.segments * 13);
        const sampleDistances = [110, 170, 240].filter(distance => distance <= bodyLength);
        sampleDistances.forEach((distance) => {
            const point = this.getAutoPointAtDistance(distance, snake);
            const dx = snake.head.x - point.x;
            const dy = snake.head.y - point.y;
            const gap = Math.hypot(dx, dy);
            if (gap <= 1 || gap > dangerRange) return;

            const bodyAngle = Math.atan2(point.y - snake.head.y, point.x - snake.head.x);
            const ahead = Math.max(0, Math.cos(bodyAngle - snake.head.heading));
            const weight = (1 - gap / dangerRange) * (0.35 + ahead * 0.9);
            avoidX += (dx / gap) * weight;
            avoidY += (dy / gap) * weight;
        });

        const force = Math.hypot(avoidX, avoidY);
        if (force < 0.08) return desiredHeading;

        const avoidHeading = Math.atan2(avoidY, avoidX);
        return this.blendHeading(desiredHeading, avoidHeading, Math.min(0.62, force * 0.42));
    }

    getSaferAutoSnakeHeading(snake, desiredHeading, target = null) {
        const maxTurn = Math.PI * 0.58;
        const delta = Math.atan2(Math.sin(desiredHeading - snake.head.heading), Math.cos(desiredHeading - snake.head.heading));
        let bestHeading = snake.head.heading + Math.max(-maxTurn, Math.min(maxTurn, delta));
        let bestScore = this.scoreAutoSnakeHeading(snake, bestHeading, target);
        [-0.72, -0.36, 0, 0.36, 0.72].forEach((offset) => {
            const candidate = snake.head.heading + offset;
            const score = this.scoreAutoSnakeHeading(snake, candidate, target) - Math.abs(offset - delta) * 24;
            if (score > bestScore) {
                bestScore = score;
                bestHeading = candidate;
            }
        });
        return bestHeading;
    }

    isAutoSnakeHeadingDangerous(snake, heading, target = null) {
        return this.scoreAutoSnakeHeading(snake, heading, target) < -35;
    }

    scoreAutoSnakeHeading(snake, heading, target = null) {
        let score = 100;
        const probes = [64, 132, 220];
        probes.forEach((distance, index) => {
            const point = {
                x: snake.head.x + Math.cos(heading) * distance,
                y: snake.head.y + Math.sin(heading) * distance
            };
            const nearWeight = Math.max(0.35, 1 - index * 0.12);
            if (this.isPointOnSwampLand(point.x, point.y, 34)) score -= (132 - index * 14) * nearWeight;
            if (this.isPointNearPlayerBody(point.x, point.y, 42)) score -= (130 - index * 16) * nearWeight;
            const playerDistance = Math.hypot(point.x - this.head.x, point.y - this.head.y);
            if (playerDistance < 150) score -= (150 - playerDistance) * 0.9;
        });

        if (target) {
            const targetAngle = Math.atan2(target.y - snake.head.y, target.x - snake.head.x);
            const turn = Math.abs(Math.atan2(Math.sin(targetAngle - heading), Math.cos(targetAngle - heading)));
            score += Math.cos(turn) * 35;
        }
        return score;
    }

    turnAutoSnakeAwayFromLotusPondBank(snake, blendAmount, margin) {
        const pond = this.getLotusPondShape(margin);
        const nx = (snake.head.x - pond.cx) / pond.rx;
        const ny = (snake.head.y - pond.cy) / pond.ry;
        if (nx * nx + ny * ny < 0.82) return;

        const backToCenter = Math.atan2(pond.cy - snake.head.y, pond.cx - snake.head.x);
        snake.head.heading = this.blendHeading(snake.head.heading, backToCenter, Math.max(blendAmount, 0.08));
    }

    triggerLotusObstacleHit(x, y, padding) {
        let hit = false;
        this.swampPatches.forEach((patch) => {
            if (!this.isPointInSwampPatch(x, y, patch, padding)) return;
            patch.hitTimer = LOTUS_HIT_EFFECT_FRAMES;
            hit = true;
        });
        this.lotusFlowers.forEach((flower) => {
            if (Math.hypot(x - flower.x, y - flower.y) > flower.radius + padding) return;
            flower.hitTimer = LOTUS_HIT_EFFECT_FRAMES;
            hit = true;
        });
        return hit;
    }

    resolveAutoSnakeLandCollision(snake) {
        if (!this.isPointOnSwampLand(snake.head.x, snake.head.y, 24)) return;

        const pond = this.getLotusPondShape(24);
        let angle = Math.atan2(pond.cy - snake.head.y, pond.cx - snake.head.x);
        this.swampPatches.forEach((patch) => {
            if (this.isPointInSwampPatch(snake.head.x, snake.head.y, patch, 24)) {
                angle = Math.atan2(snake.head.y - patch.y, snake.head.x - patch.x);
            }
        });
        this.lotusFlowers.forEach((flower) => {
            if (Math.hypot(snake.head.x - flower.x, snake.head.y - flower.y) <= flower.radius + 24) {
                angle = Math.atan2(snake.head.y - flower.y, snake.head.x - flower.x);
            }
        });
        this.triggerLotusObstacleHit(snake.head.x, snake.head.y, 24);
        snake.head.heading = this.blendHeading(snake.head.heading, angle, 0.35);
        snake.head.x += Math.cos(angle) * 9;
        snake.head.y += Math.sin(angle) * 9;
    }

    updateParticles(delta) {
        this.particles.forEach((particle) => {
            particle.x += particle.vx * delta;
            particle.y += particle.vy * delta;
            particle.life -= delta;
            particle.size *= 0.985;
        });
        this.particles = this.particles.filter(particle => particle.life > 0 && particle.size > 0.5);
    }

    updateFoods(delta) {
        const bounds = this.isSurvivalMode()
            ? this.getFoodBounds()
            : (this.motoMode ? this.worldBounds : { left: 44, top: 138, right: this.width - 44, bottom: this.height - 46 });
        const foodSpeedScale = this.isSurvivalMode() ? 0.42 : (this.motoMode ? 0.5 : 1);
        const edgeMargin = this.isSurvivalMode() ? 28 : 44;
        const left = bounds.left + edgeMargin;
        const right = bounds.right - edgeMargin;
        const top = bounds.top + (this.motoMode && !this.isSurvivalMode() ? 44 : edgeMargin);
        const bottom = bounds.bottom - (this.isSurvivalMode() ? edgeMargin : 46);

        this.foods.forEach((food, index) => {
            food.spawnAge = Math.min(45, (food.spawnAge || 0) + delta);
            const time = this.frame * 0.018 + food.wavePhase;
            const currentX = Math.cos(time * 0.75 + index) * food.waveStrength;
            const currentY = Math.sin(time + index * 1.7) * food.waveStrength;
            food.vx += currentX * delta;
            food.vy += currentY * delta;

            const speed = Math.hypot(food.vx, food.vy) || 1;
            const maxSpeed = this.isSurvivalMode() ? 0.2 : 0.675;
            const minSpeed = this.isSurvivalMode() ? 0.055 : 0.14;
            if (speed > maxSpeed) {
                food.vx = (food.vx / speed) * maxSpeed;
                food.vy = (food.vy / speed) * maxSpeed;
            } else if (speed < minSpeed) {
                const nudge = this.isSurvivalMode() ? 0.018 : 0.06;
                food.vx += (Math.random() - 0.5) * nudge;
                food.vy += (Math.random() - 0.5) * nudge;
            }

            food.x += food.vx * delta * foodSpeedScale;
            food.y += food.vy * delta * foodSpeedScale;

            if (food.x < left || food.x > right) {
                food.x = Math.max(left, Math.min(right, food.x));
                food.vx *= -0.85;
                food.vy += (Math.random() - 0.5) * 0.175;
            }
            if (food.y < top || food.y > bottom) {
                food.y = Math.max(top, Math.min(bottom, food.y));
                food.vy *= -0.85;
                food.vx += (Math.random() - 0.5) * 0.175;
            }

            if (this.isSurvivalMode() && this.isPointOnSwampLand(food.x, food.y, food.radius + 20)) {
                if (this.isTrainMode()) {
                    const obstacle = this.trainObstacles.find(item => this.isPointInTrainObstacle(food.x, food.y, item, food.radius + 20));
                    const angle = obstacle
                        ? Math.atan2(food.y - obstacle.y, food.x - obstacle.x)
                        : food.wavePhase;
                    food.x += Math.cos(angle) * 10;
                    food.y += Math.sin(angle) * 10;
                    food.vx = this.blendValue(food.vx, Math.cos(angle) * 0.11, 0.45);
                    food.vy = this.blendValue(food.vy, Math.sin(angle) * 0.11, 0.45);
                    return;
                }
                const pond = this.getLotusPondShape(food.radius + 22);
                const angleToCenter = Math.atan2(pond.cy - food.y, pond.cx - food.x);
                food.x += Math.cos(angleToCenter) * 10;
                food.y += Math.sin(angleToCenter) * 10;
                food.vx = this.blendValue(food.vx, Math.cos(angleToCenter) * 0.11, 0.45);
                food.vy = this.blendValue(food.vy, Math.sin(angleToCenter) * 0.11, 0.45);
            }
        });
    }

    blendValue(from, to, amount) {
        return from + (to - from) * amount;
    }

    isFoodCorrect(food) {
        if (this.isSurvivalMode()) return true;
        return food.item.word === this.currentItem.word && food.type === this.getTargetType();
    }

    resolveSwampLandCollision() {
        if (!this.isSurvivalMode()) return;
        if (this.isTrainMode()) {
            this.resolveTrainObstacleCollision();
            return;
        }

        const padding = this.getSnakeThickness() * 0.45;
        if (!this.isPointOnSwampLand(this.head.x, this.head.y, padding)) return;

        let bestAngle = this.head.heading + Math.PI;
        let bestDepth = 0;
        let hitLotusObstacle = false;
        const pond = this.getLotusPondShape(padding);
        const nx = (this.head.x - pond.cx) / pond.rx;
        const ny = (this.head.y - pond.cy) / pond.ry;
        if (nx * nx + ny * ny > 1) {
            bestAngle = Math.atan2(pond.cy - this.head.y, pond.cx - this.head.x);
            bestDepth = 999;
        }

        this.swampPatches.forEach(patch => {
            if (!this.isPointInSwampPatch(this.head.x, this.head.y, patch, padding)) return;
            patch.hitTimer = LOTUS_HIT_EFFECT_FRAMES;
            hitLotusObstacle = true;
            const angle = Math.atan2(this.head.y - patch.y, this.head.x - patch.x);
            const depth = Math.hypot(this.head.x - patch.x, this.head.y - patch.y);
            if (depth > bestDepth) {
                bestDepth = depth;
                bestAngle = angle;
            }
        });
        this.lotusFlowers.forEach((flower) => {
            if (Math.hypot(this.head.x - flower.x, this.head.y - flower.y) > flower.radius + padding) return;
            flower.hitTimer = LOTUS_HIT_EFFECT_FRAMES;
            hitLotusObstacle = true;
            const angle = Math.atan2(this.head.y - flower.y, this.head.x - flower.x);
            const depth = Math.hypot(this.head.x - flower.x, this.head.y - flower.y);
            if (depth > bestDepth) {
                bestDepth = depth;
                bestAngle = angle;
            }
        });

        const b = this.worldBounds;
        if (this.head.x < b.left + 52) bestAngle = 0;
        if (this.head.x > b.right - 52) bestAngle = Math.PI;
        if (this.head.y < b.top + 52) bestAngle = Math.PI / 2;
        if (this.head.y > b.bottom - 52) bestAngle = -Math.PI / 2;

        const gentleObstacleHit = hitLotusObstacle && bestDepth < 999;
        const pushAmount = gentleObstacleHit ? 3 : 8;
        const headingBlend = gentleObstacleHit ? 0.16 : 0.32;
        this.head.heading = this.blendHeading(this.head.heading, bestAngle, headingBlend);
        this.head.x += Math.cos(bestAngle) * pushAmount;
        this.head.y += Math.sin(bestAngle) * pushAmount;
        this.poisonTimer = Math.max(this.poisonTimer, 12);
    }

    resolveTrainObstacleCollision() {
        const padding = this.getSnakeThickness() * 0.42;
        if (!this.isPointOnTrainLand(this.head.x, this.head.y, padding)) {
            const land = this.trainLand;
            const angle = Math.atan2(land.cy - this.head.y, land.cx - this.head.x);
            this.head.heading = this.blendHeading(this.head.heading, angle, 0.26);
            this.head.x += Math.cos(angle) * 7;
            this.head.y += Math.sin(angle) * 7;
            return;
        }

        let bestObstacle = null;
        let bestDepth = -Infinity;

        this.trainObstacles.forEach((obstacle) => {
            if (!this.isPointInTrainObstacle(this.head.x, this.head.y, obstacle, padding)) return;
            const depth = 1 - Math.hypot((this.head.x - obstacle.x) / (obstacle.rx + padding), (this.head.y - obstacle.y) / (obstacle.ry + padding));
            if (depth > bestDepth) {
                bestDepth = depth;
                bestObstacle = obstacle;
            }
        });
        if (!bestObstacle) return;

        bestObstacle.hitTimer = LOTUS_HIT_EFFECT_FRAMES;
        const angle = Math.atan2(this.head.y - bestObstacle.y, this.head.x - bestObstacle.x);
        this.head.heading = this.blendHeading(this.head.heading, angle, 0.18);
        this.head.x += Math.cos(angle) * 4;
        this.head.y += Math.sin(angle) * 4;
    }

    checkBoundaryCollision() {
        // Moto mode now treats the border like a soft wall and turns the snake back.
    }

    checkSelfCollision() {
        if (this.bodyBiteCooldown > 0 || this.segments.length < 3) return;

        const bodyLength = this.getSnakeBodyLength();
        const biteRadius = this.getSnakeThickness() * (this.motoMode ? 1.05 : 0.82);
        const safeHeadDistance = this.motoMode ? 78 : 96;
        const sampleStep = this.motoMode ? 10 : 14;
        for (let distance = safeHeadDistance; distance <= bodyLength; distance += sampleStep) {
            const point = this.getPointAtDistance(distance);
            if (Math.hypot(point.x - this.head.x, point.y - this.head.y) < biteRadius) {
                this.bodyBiteCooldown = 90;
                this.endGame('TAIL BITE!');
                return;
            }
        }
    }

    checkFoodCollisions() {
        for (let index = this.foods.length - 1; index >= 0; index--) {
            const food = this.foods[index];
            const distance = Math.hypot(food.x - this.head.x, food.y - this.head.y);
            if (distance > food.radius + 22) continue;

            if (this.isFoodCorrect(food)) {
                this.eatCorrect(food, index);
            } else if (this.wrongCooldown <= 0) {
                this.eatWrong(food);
            }
            return;
        }
    }

    checkAutoSnakeFoodCollisions() {
        if (!this.autoSnakeEnabled) return;

        for (const snake of this.getActiveAutoSnakes()) {
            for (let index = this.foods.length - 1; index >= 0; index--) {
                const food = this.foods[index];
                const distance = Math.hypot(food.x - snake.head.x, food.y - snake.head.y);
                if (distance > food.radius + 22) continue;

                snake.segments++;
                snake.growthTimer = 35;
                this.autoSnakeGrowthTimer = 35;
                this.fishFrenzyTimer = Math.max(this.fishFrenzyTimer, 55);
                this.addParticles(food.x, food.y, snake.colors?.particle || '#f97316', 16);
                this.meaningPopups.push({
                    x: food.x,
                    y: food.y - 34,
                    text: `AUTO ate ${food.item.word}`,
                    life: 70,
                    maxLife: 70,
                    bonus: true
                });
                this.foods.splice(index, 1);
                this.addRandomFood();
                return;
            }
        }
    }

    checkInterSnakeCollisions() {
        if (!this.autoSnakeEnabled) return;

        const playerThickness = this.getSnakeThickness();
        for (const snake of this.getActiveAutoSnakes()) {
            const autoThickness = this.getAutoSnakeThickness(snake);
            const headDistance = Math.hypot(this.head.x - snake.head.x, this.head.y - snake.head.y);
            if (headDistance < (playerThickness + autoThickness) * 0.72) {
                this.autoSnakes = [];
                this.autoSnake = null;
                this.autoSnakeEnabled = false;
                this.updateAutoSnakeButton();
                this.addParticles(this.head.x, this.head.y, '#f97316', 28);
                this.endGame('HEAD CRASH!');
                return;
            }

            if (this.isPointNearAutoSnakeBody(this.head.x, this.head.y, playerThickness * 0.78, 78, null)) {
                this.autoSnakes = [];
                this.autoSnake = null;
                this.autoSnakeEnabled = false;
                this.updateAutoSnakeButton();
                this.endGame('RIVAL BITE!');
                return;
            }

            if (this.isPointNearPlayerBody(snake.head.x, snake.head.y, autoThickness * 0.78)) {
                this.defeatAutoSnake(snake, 'AUTO SNAKE DOWN');
                return;
            }
        }
    }

    checkAutoSnakeSelfCollision() {
        if (!this.autoSnakeEnabled) return;

        for (const snake of this.getActiveAutoSnakes()) {
            if (snake.segments < 3 || snake.bodyBiteCooldown > 0) continue;

            const biteRadius = this.getAutoSnakeThickness(snake) * 0.86;
            if (this.isPointNearAutoSnakeBody(snake.head.x, snake.head.y, biteRadius, 116, snake)) {
                snake.bodyBiteCooldown = 90;
                this.defeatAutoSnake(snake, 'AUTO BIT TAIL');
                return;
            }
        }
    }

    isPointNearAutoSnakeBody(x, y, radius, safeHeadDistance = 78, sourceSnake = null) {
        const snakes = this.getActiveAutoSnakes();
        if (snakes.length === 0) return false;

        for (const snake of snakes) {
            const startDistance = snake === sourceSnake ? safeHeadDistance : 0;
            const bodyLength = this.getAutoSnakeBodyLength(snake);
            for (let distance = startDistance; distance <= bodyLength; distance += 12) {
                const point = this.getAutoPointAtDistance(distance, snake);
                if (Math.hypot(point.x - x, point.y - y) < radius) return true;
            }
        }
        return false;
    }

    isPointNearPlayerBody(x, y, radius) {
        const bodyLength = this.getSnakeBodyLength();
        for (let distance = 78; distance <= bodyLength; distance += 12) {
            const point = this.getPointAtDistance(distance);
            if (Math.hypot(point.x - x, point.y - y) < radius) return true;
        }
        return false;
    }

    defeatAutoSnake(snake, message) {
        if (!snake) return;

        const colors = snake.colors || AUTO_SNAKE_COLORS[0];
        this.addParticles(snake.head.x, snake.head.y, colors.particle, 32);
        this.meaningPopups.push({
            x: snake.head.x,
            y: snake.head.y - 38,
            text: message,
            life: 90,
            maxLife: 90,
            bonus: true
        });
        snake.active = false;
        this.syncPrimaryAutoSnake();
        this.autoSnakeRespawnTimer = Math.min(this.autoSnakeRespawnTimer || AUTO_SNAKE_SPAWN_STAGGER_FRAMES, AUTO_SNAKE_SPAWN_STAGGER_FRAMES);
        this.updateAutoSnakeButton();
        this.fx.tone(220, 0.14, 'sawtooth', 0.04);
    }

    eatCorrect(food, index) {
        this.fx.eat();
        this.correct++;
        this.combo++;
        this.bestCombo = Math.max(this.bestCombo, this.combo);
        this.score += 100 + Math.min(500, this.combo * 25);

        this.segments.push({
            type: food.type,
            item: food.item,
            label: food.label
        });
        this.growthTimer = 35;

        this.addParticles(food.x, food.y, '#00ff88', 18);
        if (this.isSurvivalMode()) {
            this.speakTypes(food.item, ['en', 'vi']);
            this.applyLotusPondFoodReward(food);
        }
        this.foods.splice(index, 1);
        this.nextChallenge();
    }

    applyLotusPondFoodReward(food) {
        this.meaningPopups.push({
            x: food.x,
            y: food.y - 36,
            text: `${food.item.word} = ${food.item.meaning}`,
            life: 130,
            maxLife: 130,
            bonus: false
        });

        if (this.combo >= 3) {
            this.fishFrenzyTimer = Math.max(this.fishFrenzyTimer, 75);
        }

        const bonusFlower = this.lotusFlowers.find((flower) => (
            Math.hypot(food.x - flower.x, food.y - flower.y) < flower.radius * 3.4
        ));
        if (!bonusFlower) return;

        this.score += 150;
        this.lotusBonusTimer = 90;
        this.fishFrenzyTimer = Math.max(this.fishFrenzyTimer, 95);
        this.addParticles(bonusFlower.x, bonusFlower.y, '#ffd166', 24);
        this.meaningPopups.push({
            x: bonusFlower.x,
            y: bonusFlower.y - bonusFlower.radius - 26,
            text: 'LOTUS BONUS +150',
            life: 95,
            maxLife: 95,
            bonus: true
        });
        this.fx.tone(660, 0.08, 'triangle', 0.045);
        this.fx.tone(990, 0.12, 'sine', 0.04, 0.08);
    }

    updateMeaningPopups(delta) {
        if (this.meaningPopups.length === 0) return;

        this.meaningPopups.forEach((popup) => {
            popup.life -= delta;
            popup.y -= 0.22 * delta;
        });
        this.meaningPopups = this.meaningPopups.filter(popup => popup.life > 0);
    }

    playLotusAmbientIfNeeded() {
        if (!this.isSurvivalMode() || this.elapsedGameSeconds < this.nextLotusAmbientAt) return;

        this.nextLotusAmbientAt = this.elapsedGameSeconds + 5 + Math.random() * 4;
        if (this.fx.muted) return;

        const baseDelay = Math.random() * 0.1;
        this.fx.tone(196 + Math.random() * 24, 0.22, 'sine', 0.012, baseDelay);
        this.fx.tone(294 + Math.random() * 30, 0.12, 'triangle', 0.01, baseDelay + 0.18);
        if (Math.random() < 0.45) {
            this.fx.tone(110 + Math.random() * 18, 0.08, 'sine', 0.014, baseDelay + 0.42);
        }
    }

    eatWrong(food) {
        this.fx.wrong();
        this.incorrect++;
        this.combo = 0;
        this.score = Math.max(0, this.score - 40);
        this.lives = Math.max(0, this.lives - 1);
        this.wrongCooldown = 45;
        this.poisonTimer = 85;
        this.addParticles(food.x, food.y, '#ff3c3c', 12);

        const cutCount = Math.min(Math.max(1, Math.ceil(this.segments.length * 0.28)), this.segments.length - 1);
        const tailPoint = this.getPointAtDistance(this.getSnakeBodyLength());
        for (let index = 0; index < cutCount; index++) {
            this.segments.pop();
        }
        this.addParticles(tailPoint.x, tailPoint.y, '#baff29', 22);

        if (this.lives <= 0) {
            this.endGame('POISONED!');
        }
    }

    nextChallenge() {
        if (this.isSurvivalMode()) {
            this.currentItem = null;
            this.currentPromptType = 'food';
            this.addRandomFood();
            return;
        }

        this.selectRandomTargetFromFoods();
        this.addRandomFood();
        this.speakPair(this.currentItem, this.currentPromptType);
    }

    replayPromptAudioIfNeeded() {
        if (this.isSurvivalMode()) return;
        if (!this.currentItem || this.elapsedGameSeconds - this.lastPromptSpeechGameSecond < 10) return;
        this.speakPair(this.currentItem, this.currentPromptType);
    }

    addParticles(x, y, color, count) {
        for (let index = 0; index < count; index++) {
            const angle = Math.random() * Math.PI * 2;
            const speed = 1 + Math.random() * 4;
            this.particles.push({
                x,
                y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                size: 4 + Math.random() * 8,
                color,
                life: 35 + Math.random() * 20
            });
        }
    }

    speakPair(item, sourceType) {
        this.lastPromptSpeechFrame = this.frame;
        this.lastPromptSpeechTimeMs = performance.now();
        this.lastPromptSpeechGameSecond = this.elapsedGameSeconds;
        const order = this.config.speechOrder || [sourceType, sourceType === 'vi' ? 'en' : 'vi'];
        this.speakTypes(item, order);
    }

    speakTypes(item, order) {
        if (!item || !this.speechEnabled || this.fx.muted || !window.speechSynthesis) return;

        order.forEach((type) => {
            this.speechQueue.push({
                text: type === 'vi' ? item.meaning : item.word,
                lang: type === 'vi' ? 'vi-VN' : 'en-US',
                rate: type === 'vi' ? 0.9 : 0.95,
                type
            });
        });
        this.processSpeechQueue();
    }

    processSpeechQueue() {
        if (this.speechSpeaking || this.speechQueue.length === 0) return;
        if (this.state !== 'playing' || !this.speechEnabled || this.fx.muted || !window.speechSynthesis) {
            this.speechQueue = [];
            this.speechSpeaking = false;
            return;
        }

        const entry = this.speechQueue.shift();
        const utterance = new SpeechSynthesisUtterance(entry.text);
        utterance.lang = entry.lang;
        utterance.rate = entry.rate;
        utterance.pitch = 1.05;
        const voices = window.speechSynthesis.getVoices();
        const voice = voices.find(v => (v.lang || '').toLowerCase().startsWith(entry.type === 'vi' ? 'vi' : 'en'));
        if (voice) utterance.voice = voice;

        this.speechSpeaking = true;
        utterance.onend = () => {
            this.speechSpeaking = false;
            this.processSpeechQueue();
        };
        utterance.onerror = () => {
            this.speechSpeaking = false;
            this.processSpeechQueue();
        };

        window.speechSynthesis.speak(utterance);
    }

    clearSpeechQueue() {
        this.speechQueue = [];
        this.speechSpeaking = false;
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    }

    pauseGame() {
        if (this.state !== 'playing') return;
        this.state = 'paused';
        this.modalPause.classList.remove('hidden');
        if (window.speechSynthesis) window.speechSynthesis.pause();
    }

    resumeGame() {
        if (this.state !== 'paused') return;
        this.state = 'playing';
        this.modalPause.classList.add('hidden');
        if (window.speechSynthesis) window.speechSynthesis.resume();
    }

    quitToMenu() {
        this.state = 'start';
        this.clearSpeechQueue();
        this.autoSnakeEnabled = false;
        this.autoSnake = null;
        this.autoSnakes = [];
        this.autoSnakeMaxCount = 0;
        this.updateAutoSnakeButton();
        document.body.classList.remove('snake-mode');
        document.body.classList.remove('swamp-mode');
        document.body.classList.remove('train-mode');
        this.screenGame.classList.remove('active');
        this.screenStart.classList.add('active');
        this.modalPause.classList.add('hidden');
        this.modalGameOver.classList.add('hidden');
        this.updateStartHighScore();
        this.renderStartPlayHistory();
    }

    endGame(title, won = false) {
        if (this.state !== 'playing') return;
        this.state = 'gameover';
        this.clearSpeechQueue();
        if (won) {
            this.fx.victory();
        } else {
            this.lives = 0;
            this.fx.gameOver();
        }
        this.saveHighScore();
        this.savePlayHistory();
        this.populateGameOver(title, won);
        this.modalGameOver.classList.remove('hidden');
    }

    updateHUD() {
        const accuracy = this.correct + this.incorrect === 0
            ? 100
            : Math.round((this.correct / (this.correct + this.incorrect)) * 100);

        document.getElementById('hud-score').innerText = String(this.score).padStart(5, '0');
        document.getElementById('hud-hearts').innerText = '❤️'.repeat(Math.max(0, this.lives)) + '🖤'.repeat(Math.max(0, 3 - this.lives));
        document.getElementById('hud-diff').innerText = `${this.config.label} x${this.speedMultiplier.toFixed(1)}`;
        document.getElementById('hud-time').innerText = this.formatTime(this.timeLeft);
        document.getElementById('hud-accuracy').innerText = `${accuracy}%`;

        this.targetValue.innerText = this.isSurvivalMode()
            ? (this.isTrainMode() ? 'COUNTRY TRAIN' : 'LOTUS POND')
            : (this.mode === 'mixed'
                ? '🔊 LISTEN'
                : this.getLabel(this.currentItem || this.vocab[0], this.currentPromptType));
    }

    trySpeedBoost() {
        if (this.state !== 'playing' || this.elapsedGameSeconds < this.nextSpeedBoostAt) return;

        this.speedMultiplier = SPEED_BOOST_MULTIPLIER;
        this.speedBoostUntil = this.elapsedGameSeconds + SPEED_BOOST_DURATION_SECONDS;
        this.nextSpeedBoostAt = this.elapsedGameSeconds + SPEED_BOOST_COOLDOWN_SECONDS;
        this.speedBoostFlash = 35;
        this.fx.tone(740, 0.08, 'square', 0.07);
        this.fx.tone(1180, 0.12, 'triangle', 0.06, 0.06);
        this.addParticles(this.head.x, this.head.y, '#38bdf8', 36);
    }

    updateChainHud() {
        const recent = this.segments
            .slice(-9)
            .map(segment => segment.type.toUpperCase())
            .join(' - ');
        this.chainLabel.innerText = `WORD CHAIN: ${recent}`;
    }

    populateGameOver(title, won = false) {
        const accuracy = this.correct + this.incorrect === 0
            ? 100
            : Math.round((this.correct / (this.correct + this.incorrect)) * 100);

        document.getElementById('gameover-title').innerText = title;
        document.querySelector('.gameover-subtitle').innerText = this.getGameOverSubtitle(title, won);
        document.getElementById('go-score').innerText = this.score;
        document.getElementById('go-best-score').innerText = this.getHighScore();
        document.getElementById('go-combo').innerText = this.bestCombo;
        document.getElementById('go-accuracy').innerText = `${accuracy}%`;
        document.getElementById('go-correct').innerText = this.correct;
        document.getElementById('go-incorrect').innerText = this.incorrect;
        document.getElementById('go-bosses').innerText = this.segments.length;

        const learnedWords = document.getElementById('learned-words-list');
        learnedWords.innerHTML = '';
        this.segments.slice(0, 30).forEach((segment) => {
            const tag = document.createElement('div');
            tag.className = 'learned-word-tag mastered';
            tag.textContent = segment.label;
            learnedWords.appendChild(tag);
        });

        this.renderPlayHistory();
    }

    getGameOverSubtitle(title, won = false) {
        if (won) return 'You survived the full 5-minute word swim!';
        if (this.isTrainMode()) return 'The train hit an obstacle on the countryside route.';
        if (title === 'POISONED!') return 'The snake ate the wrong food three times.';
        if (title === 'HEAD CRASH!') return 'Both snakes crashed head-first into each other.';
        if (title === 'RIVAL BITE!') return 'Your snake bit into the auto snake body.';
        return 'The snake bit its own tail.';
    }

    draw() {
        this.drawBackground();

        if (this.state === 'start' || this.state === 'loading') {
            return;
        }

        this.drawWorldBoundary();
        this.drawSnakeWaterWake();
        this.foods.forEach(food => this.drawFood(food));
        this.drawAutoSnake();
        if (this.isTrainMode()) {
            this.drawTrain();
        } else {
            this.drawSnake();
        }
        this.drawMeaningPopups();
        this.drawSpeedBoostReadyHint();
        this.drawSpeedBoostEffect();
        this.drawParticles();

        if (this.state === 'paused') {
            this.drawOverlayText('PAUSED');
        }
    }

    drawBackground() {
        const ctx = this.ctx;
        const time = this.frame * 0.01;
        const camera = this.getCamera();
        ctx.clearRect(0, 0, this.width, this.height);

        const gradient = ctx.createRadialGradient(
            this.width * 0.5,
            this.height * 0.45,
            80,
            this.width * 0.5,
            this.height * 0.5,
            Math.max(this.width, this.height)
        );
        if (this.isSurvivalMode()) {
            gradient.addColorStop(0, '#2e786f');
            gradient.addColorStop(0.52, '#14524f');
            gradient.addColorStop(1, '#062925');
        } else {
            gradient.addColorStop(0, '#173d6f');
            gradient.addColorStop(0.55, '#071a31');
            gradient.addColorStop(1, '#020711');
        }
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, this.width, this.height);

        if (!this.isSurvivalMode()) {
            ctx.save();
            ctx.globalAlpha = 0.24;
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 1;
            for (let y = 120; y < this.height; y += 60) {
                ctx.beginPath();
                for (let x = 0; x <= this.width; x += 24) {
                    const worldX = x + camera.x;
                    const worldY = y + camera.y;
                    const wave = Math.sin(worldX * 0.018 + time + worldY * 0.01) * 8;
                    if (x === 0) ctx.moveTo(x, y + wave);
                    else ctx.lineTo(x, y + wave);
                }
                ctx.stroke();
            }
            ctx.restore();
        }

        ctx.save();
        ctx.globalAlpha = 0.2;
        for (let index = 0; index < 18; index++) {
            const x = ((index * 173 + time * 36 - camera.x * 0.35) % (this.width + 120)) - 60;
            const y = 150 + ((index * 91 + Math.sin(time + index) * 36 - camera.y * 0.18) % Math.max(1, this.height - 190));
            const size = 8 + (index % 4) * 5;
            ctx.strokeStyle = index % 2 === 0 ? '#7dd3fc' : '#a7f3d0';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(x, y, size, 0, Math.PI * 2);
            ctx.stroke();
        }
        ctx.restore();

        if (this.isTrainMode()) {
            this.drawTrainTerrain();
        } else {
            this.drawSwampTerrain();
        }
    }

    drawSwampTerrain() {
        if (!this.isSurvivalMode()) return;
        if (this.isTrainMode()) return;

        const ctx = this.ctx;
        const camera = this.getCamera();
        const b = this.worldBounds;
        const x = b.left - camera.x;
        const y = b.top - camera.y;
        const w = b.right - b.left;
        const h = b.bottom - b.top;
        const pond = this.getLotusPondShape(0);
        const pondCenter = this.worldToScreen({ x: pond.cx, y: pond.cy });

        ctx.save();
        ctx.fillStyle = '#5a422f';
        ctx.beginPath();
        ctx.rect(0, 0, this.width, this.height);
        ctx.ellipse(pondCenter.x, pondCenter.y, pond.rx + 34, pond.ry + 28, 0, 0, Math.PI * 2);
        ctx.fill('evenodd');

        ctx.fillStyle = '#4f783b';
        ctx.beginPath();
        ctx.ellipse(pondCenter.x, pondCenter.y, pond.rx + 34, pond.ry + 28, 0, 0, Math.PI * 2);
        ctx.fill();

        const waterGradient = ctx.createRadialGradient(
            pondCenter.x - pond.rx * 0.25,
            pondCenter.y - pond.ry * 0.22,
            20,
            pondCenter.x,
            pondCenter.y,
            Math.max(pond.rx, pond.ry)
        );
        waterGradient.addColorStop(0, '#4fb7a4');
        waterGradient.addColorStop(0.58, '#227268');
        waterGradient.addColorStop(1, '#0c403b');
        ctx.fillStyle = waterGradient;
        ctx.beginPath();
        ctx.ellipse(pondCenter.x, pondCenter.y, pond.rx, pond.ry, 0, 0, Math.PI * 2);
        ctx.fill();

        const shallowWidth = (this.foods[0]?.radius || 28) * 2;
        const shallowRx = Math.max(40, pond.rx - shallowWidth);
        const shallowRy = Math.max(34, pond.ry - shallowWidth);
        ctx.save();
        ctx.fillStyle = 'rgba(96, 75, 42, 0.28)';
        ctx.beginPath();
        ctx.ellipse(pondCenter.x, pondCenter.y, pond.rx, pond.ry, 0, 0, Math.PI * 2);
        ctx.ellipse(pondCenter.x, pondCenter.y, shallowRx, shallowRy, 0, 0, Math.PI * 2);
        ctx.fill('evenodd');
        ctx.restore();

        this.drawLotusPondDepthEffects(pond, pondCenter);

        ctx.strokeStyle = 'rgba(38, 75, 38, 0.85)';
        ctx.lineWidth = 12;
        ctx.beginPath();
        ctx.ellipse(pondCenter.x, pondCenter.y, pond.rx + 18, pond.ry + 14, 0, 0, Math.PI * 2);
        ctx.stroke();

        ctx.strokeStyle = 'rgba(191, 226, 144, 0.55)';
        ctx.lineWidth = 4;
        ctx.setLineDash([14, 18]);
        ctx.beginPath();
        ctx.ellipse(pondCenter.x, pondCenter.y, pond.rx + 26, pond.ry + 21, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.strokeStyle = 'rgba(214, 246, 230, 0.18)';
        ctx.lineWidth = 2;
        for (let i = 0; i < 34; i++) {
            const angle = i * 1.73 + Math.sin(i * 2.1) * 0.22;
            const reedX = pondCenter.x + Math.cos(angle) * (pond.rx + 24 + (i % 3) * 8);
            const reedY = pondCenter.y + Math.sin(angle) * (pond.ry + 18 + (i % 4) * 5);
            ctx.beginPath();
            ctx.moveTo(reedX, reedY);
            ctx.lineTo(reedX + Math.cos(angle - 0.35) * 18, reedY - 24);
            ctx.stroke();
        }

        ctx.fillStyle = 'rgba(183, 226, 190, 0.16)';
        for (let i = 0; i < 18; i++) {
            const padX = x + ((i * 97 + this.frame * 0.08) % Math.max(1, w));
            const padY = y + 58 + ((i * 53) % Math.max(1, h - 116));
            ctx.beginPath();
            ctx.ellipse(padX, padY, 14 + (i % 3) * 4, 8 + (i % 2) * 3, i * 0.4, 0, Math.PI * 2);
            ctx.fill();
        }

        this.swampPatches.forEach((patch, index) => {
            const p = this.worldToScreen(patch);
            const hitPulse = Math.max(0, Math.min(1, (patch.hitTimer || 0) / LOTUS_HIT_EFFECT_FRAMES));
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate(patch.rot);

            if (hitPulse > 0) {
                ctx.save();
                ctx.globalAlpha = 0.08 + hitPulse * 0.12;
                ctx.shadowColor = 'rgba(254, 240, 138, 0.42)';
                ctx.shadowBlur = 7 * hitPulse;
                ctx.fillStyle = 'rgba(254, 240, 138, 0.16)';
                ctx.beginPath();
                ctx.ellipse(0, 0, patch.rx * (1.03 + hitPulse * 0.02), patch.ry * (1.03 + hitPulse * 0.02), 0, 0, Math.PI * 2);
                ctx.fill();
                ctx.restore();
            }

            const leafGradient = ctx.createRadialGradient(-patch.rx * 0.18, -patch.ry * 0.16, 4, 0, 0, patch.rx);
            leafGradient.addColorStop(0, '#a3c95f');
            leafGradient.addColorStop(0.5, index % 2 === 0 ? '#4f9a54' : '#438a4c');
            leafGradient.addColorStop(1, '#1f5e42');
            ctx.fillStyle = leafGradient;
            ctx.beginPath();
            ctx.ellipse(0, 0, patch.rx, patch.ry, 0, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = 'rgba(12, 64, 59, 0.72)';
            ctx.beginPath();
            ctx.moveTo(patch.rx * 0.16, 0);
            ctx.quadraticCurveTo(patch.rx * 0.58, -patch.ry * 0.18, patch.rx * 0.86, -patch.ry * 0.06);
            ctx.quadraticCurveTo(patch.rx * 0.48, patch.ry * 0.08, patch.rx * 0.16, 0);
            ctx.fill();

            ctx.strokeStyle = 'rgba(224, 255, 208, 0.42)';
            ctx.lineWidth = 2;
            for (let vein = 0; vein < 10; vein++) {
                const angle = -Math.PI * 0.88 + vein * (Math.PI * 1.58 / 9);
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.quadraticCurveTo(
                    Math.cos(angle) * patch.rx * 0.35,
                    Math.sin(angle) * patch.ry * 0.35,
                    Math.cos(angle) * patch.rx * 0.86,
                    Math.sin(angle) * patch.ry * 0.86
                );
                ctx.stroke();
            }

            ctx.strokeStyle = 'rgba(5, 35, 28, 0.34)';
            ctx.lineWidth = 3;
            if (hitPulse > 0) {
                ctx.strokeStyle = `rgba(254, 240, 138, ${0.22 + hitPulse * 0.22})`;
                ctx.lineWidth = 3 + hitPulse * 0.8;
            }
            ctx.beginPath();
            ctx.ellipse(0, 0, patch.rx, patch.ry, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();
        });

        this.lotusFlowers.forEach((flower, index) => {
            const p = this.worldToScreen(flower);
            const size = flower.radius;
            const bonusPulse = Math.max(0, Math.min(1, this.lotusBonusTimer / 90));
            const hitPulse = Math.max(0, Math.min(1, (flower.hitTimer || 0) / LOTUS_HIT_EFFECT_FRAMES));
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate(flower.rot + Math.sin(this.frame * 0.018 + index) * 0.04);

            ctx.fillStyle = bonusPulse > 0 || hitPulse > 0
                ? `rgba(253, 224, 71, ${0.16 + bonusPulse * 0.18 + hitPulse * 0.12})`
                : 'rgba(255, 229, 239, 0.2)';
            ctx.shadowColor = hitPulse > 0 ? 'rgba(254, 240, 138, 0.45)' : 'transparent';
            ctx.shadowBlur = hitPulse * 6;
            ctx.beginPath();
            ctx.arc(0, 0, size * (1.05 + bonusPulse * 0.35 + hitPulse * 0.06), 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;

            for (let layer = 0; layer < 2; layer++) {
                ctx.fillStyle = layer === 0 ? '#f8a7c6' : '#ffd2e3';
                const petals = layer === 0 ? 8 : 6;
                const petalLength = size * (layer === 0 ? 0.95 : 0.68);
                const petalWidth = size * (layer === 0 ? 0.22 : 0.18);
                for (let petal = 0; petal < petals; petal++) {
                    ctx.save();
                    ctx.rotate(petal * Math.PI * 2 / petals + layer * 0.26);
                    ctx.beginPath();
                    ctx.ellipse(0, -petalLength * 0.42, petalWidth, petalLength * 0.5, 0, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.restore();
                }
            }

            ctx.fillStyle = '#ffd166';
            ctx.beginPath();
            ctx.arc(0, 0, size * 0.18, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        });
        ctx.restore();
    }

    drawTrainTerrain() {
        if (!this.isTrainMode()) return;

        const ctx = this.ctx;
        const camera = this.getCamera();
        const b = this.worldBounds;
        const x = b.left - camera.x;
        const y = b.top - camera.y;
        const w = b.right - b.left;
        const h = b.bottom - b.top;
        const land = this.trainLand || {
            cx: (b.left + b.right) / 2,
            cy: (b.top + b.bottom) / 2,
            rx: w * 0.49,
            ry: h * 0.45
        };
        const landCenter = this.worldToScreen({ x: land.cx, y: land.cy });

        ctx.save();
        const seaGradient = ctx.createRadialGradient(landCenter.x, landCenter.y, Math.min(land.rx, land.ry) * 0.35, landCenter.x, landCenter.y, Math.max(w, h) * 0.8);
        seaGradient.addColorStop(0, '#38bdf8');
        seaGradient.addColorStop(0.58, '#0ea5e9');
        seaGradient.addColorStop(1, '#075985');
        ctx.fillStyle = seaGradient;
        ctx.fillRect(0, 0, this.width, this.height);

        ctx.globalAlpha = 0.16;
        ctx.strokeStyle = '#dff7ff';
        ctx.lineWidth = 2;
        for (let wave = 0; wave < 18; wave++) {
            const waveY = ((wave * 73 + this.frame * 0.15 - camera.y * 0.12) % (this.height + 80)) - 40;
            ctx.beginPath();
            for (let step = 0; step <= 36; step++) {
                const px = (this.width / 36) * step;
                const py = waveY + Math.sin(step * 0.9 + wave) * 6;
                if (step === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
            }
            ctx.stroke();
        }
        ctx.globalAlpha = 1;

        ctx.fillStyle = '#475569';
        ctx.beginPath();
        ctx.roundRect(landCenter.x - land.rx - 58, landCenter.y - land.ry - 48, (land.rx + 58) * 2, (land.ry + 48) * 2, 44);
        ctx.fill();

        ctx.fillStyle = '#64748b';
        ctx.beginPath();
        ctx.roundRect(landCenter.x - land.rx - 38, landCenter.y - land.ry - 31, (land.rx + 38) * 2, (land.ry + 31) * 2, 36);
        ctx.fill();

        ctx.strokeStyle = 'rgba(226, 232, 240, 0.42)';
        ctx.lineWidth = 4;
        ctx.setLineDash([14, 10]);
        ctx.beginPath();
        ctx.roundRect(landCenter.x - land.rx - 48, landCenter.y - land.ry - 39, (land.rx + 48) * 2, (land.ry + 39) * 2, 40);
        ctx.stroke();
        ctx.setLineDash([]);

        const groundGradient = ctx.createRadialGradient(landCenter.x - land.rx * 0.25, landCenter.y - land.ry * 0.2, 20, landCenter.x, landCenter.y, Math.max(land.rx, land.ry));
        groundGradient.addColorStop(0, '#9bd36a');
        groundGradient.addColorStop(0.58, '#6fa04f');
        groundGradient.addColorStop(1, '#4f7f3c');
        ctx.fillStyle = groundGradient;
        ctx.beginPath();
        ctx.roundRect(landCenter.x - land.rx, landCenter.y - land.ry, land.rx * 2, land.ry * 2, 32);
        ctx.fill();

        ctx.globalAlpha = 0.18;
        ctx.strokeStyle = '#e6c37d';
        ctx.lineWidth = 8;
        for (let lane = 0; lane < 5; lane++) {
            const laneY = landCenter.y - land.ry * 0.55 + lane * land.ry * 0.26;
            ctx.beginPath();
            for (let step = 0; step <= 48; step++) {
                const px = landCenter.x - land.rx * 0.82 + (land.rx * 1.64 / 48) * step;
                const py = laneY + Math.sin(step * 0.55 + lane * 1.7) * 16;
                if (step === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
            }
            ctx.stroke();
        }
        ctx.globalAlpha = 1;

        ctx.fillStyle = 'rgba(255, 245, 196, 0.16)';
        for (let dot = 0; dot < 44; dot++) {
            const px = landCenter.x - land.rx * 0.82 + ((dot * 157) % Math.max(1, land.rx * 1.64));
            const py = landCenter.y - land.ry * 0.72 + ((dot * 91) % Math.max(1, land.ry * 1.44));
            ctx.beginPath();
            ctx.ellipse(px, py, 3 + (dot % 3), 2 + (dot % 2), dot * 0.4, 0, Math.PI * 2);
            ctx.fill();
        }

        this.trainObstacles.forEach((obstacle) => this.drawTrainObstacle(obstacle));
        ctx.restore();
    }

    drawTrainObstacle(obstacle) {
        const ctx = this.ctx;
        const p = this.worldToScreen(obstacle);
        const hitPulse = Math.max(0, Math.min(1, (obstacle.hitTimer || 0) / LOTUS_HIT_EFFECT_FRAMES));
        const isWater = obstacle.type === 'pond' || obstacle.type === 'lake' || obstacle.type === 'river' || obstacle.type === 'coast';
        const isTree = obstacle.type === 'tree';
        const isPine = obstacle.type === 'pine';
        const isHouse = obstacle.type === 'house';

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(obstacle.rot);
        if (hitPulse > 0) {
            ctx.shadowColor = 'rgba(254, 240, 138, 0.5)';
            ctx.shadowBlur = hitPulse * 8;
        }

        if (isWater) {
            const waterRy = obstacle.type === 'pond' || obstacle.type === 'lake'
                ? Math.max(obstacle.ry, obstacle.rx * 0.86)
                : obstacle.ry;
            const gradient = ctx.createRadialGradient(-obstacle.rx * 0.25, -waterRy * 0.25, 4, 0, 0, obstacle.rx);
            gradient.addColorStop(0, '#8ee4ff');
            gradient.addColorStop(0.55, obstacle.type === 'coast' ? '#38bdf8' : '#2f9db4');
            gradient.addColorStop(1, obstacle.type === 'coast' ? '#0369a1' : '#0f5e70');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.ellipse(0, 0, obstacle.rx, waterRy, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = 'rgba(219, 234, 254, 0.45)';
            ctx.lineWidth = 2;
            ctx.stroke();
        } else if (isTree) {
            ctx.fillStyle = '#7c4a22';
            ctx.fillRect(-obstacle.rx * 0.12, -obstacle.ry * 0.05, obstacle.rx * 0.24, obstacle.ry * 0.72);
            const gradient = ctx.createRadialGradient(-obstacle.rx * 0.2, -obstacle.ry * 0.3, 4, 0, -obstacle.ry * 0.2, obstacle.rx);
            gradient.addColorStop(0, '#86efac');
            gradient.addColorStop(0.55, '#22c55e');
            gradient.addColorStop(1, '#166534');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.ellipse(0, -obstacle.ry * 0.26, obstacle.rx, obstacle.ry * 0.78, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = 'rgba(20, 83, 45, 0.48)';
            ctx.lineWidth = 2;
            ctx.stroke();
        } else if (isPine) {
            ctx.fillStyle = '#7c4a22';
            ctx.fillRect(-obstacle.rx * 0.09, -obstacle.ry * 0.04, obstacle.rx * 0.18, obstacle.ry * 0.76);
            ctx.fillStyle = '#14532d';
            for (let layer = 0; layer < 3; layer++) {
                const y = -obstacle.ry * (0.45 - layer * 0.22);
                const width = obstacle.rx * (1.1 - layer * 0.18);
                ctx.beginPath();
                ctx.moveTo(0, y - obstacle.ry * 0.32);
                ctx.lineTo(-width, y + obstacle.ry * 0.28);
                ctx.lineTo(width, y + obstacle.ry * 0.28);
                ctx.closePath();
                ctx.fill();
            }
            ctx.strokeStyle = 'rgba(220, 252, 231, 0.32)';
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            ctx.moveTo(0, -obstacle.ry * 0.82);
            ctx.lineTo(0, obstacle.ry * 0.28);
            ctx.stroke();
        } else if (isHouse) {
            const width = obstacle.rx * 1.55;
            const height = obstacle.ry * 1.12;
            ctx.fillStyle = '#f5d0a9';
            ctx.strokeStyle = '#78350f';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.roundRect(-width / 2, -height * 0.18, width, height * 0.72, 5);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = '#b45309';
            ctx.beginPath();
            ctx.moveTo(-width * 0.62, -height * 0.16);
            ctx.lineTo(0, -height * 0.78);
            ctx.lineTo(width * 0.62, -height * 0.16);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = '#60a5fa';
            ctx.fillRect(-width * 0.28, height * 0.02, width * 0.18, height * 0.18);
            ctx.fillStyle = '#7c2d12';
            ctx.fillRect(width * 0.15, height * 0.08, width * 0.2, height * 0.46);
        } else {
            const gradient = ctx.createRadialGradient(-obstacle.rx * 0.2, -obstacle.ry * 0.35, 8, 0, 0, obstacle.rx);
            gradient.addColorStop(0, obstacle.type === 'mountain' ? '#d6c3a5' : '#9fbd5e');
            gradient.addColorStop(0.58, obstacle.type === 'mountain' ? '#8b7355' : '#577c36');
            gradient.addColorStop(1, obstacle.type === 'mountain' ? '#4d3f34' : '#34522b');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.ellipse(0, 0, obstacle.rx, obstacle.ry, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = obstacle.type === 'mountain' ? 'rgba(60, 45, 34, 0.5)' : 'rgba(29, 72, 43, 0.45)';
            ctx.lineWidth = 2.5;
            ctx.stroke();
        }

        if (hitPulse > 0) {
            ctx.strokeStyle = `rgba(254, 240, 138, ${0.24 + hitPulse * 0.24})`;
            ctx.lineWidth = 2 + hitPulse;
            ctx.beginPath();
            ctx.ellipse(0, 0, obstacle.rx + 5, obstacle.ry + 5, 0, 0, Math.PI * 2);
            ctx.stroke();
        }
        ctx.restore();
    }

    drawLotusPondDepthEffects(pond, pondCenter) {
        if (!this.isSurvivalMode()) return;

        const ctx = this.ctx;
        const time = this.frame * 0.018;
        const frenzy = Math.max(0, Math.min(1, this.fishFrenzyTimer / 120));

        ctx.save();
        ctx.beginPath();
        ctx.ellipse(pondCenter.x, pondCenter.y, pond.rx, pond.ry, 0, 0, Math.PI * 2);
        ctx.clip();

        ctx.fillStyle = 'rgba(4, 24, 27, 0.22)';
        ctx.beginPath();
        ctx.ellipse(pondCenter.x + pond.rx * 0.15, pondCenter.y + pond.ry * 0.12, pond.rx * 0.62, pond.ry * 0.5, -0.18, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = 'rgba(125, 211, 252, 0.08)';
        ctx.beginPath();
        ctx.ellipse(pondCenter.x - pond.rx * 0.35, pondCenter.y - pond.ry * 0.34, pond.rx * 0.34, pond.ry * 0.22, 0.16, 0, Math.PI * 2);
        ctx.fill();

        for (let bubble = 0; bubble < 32; bubble++) {
            const lane = (bubble * 0.61803398875) % 1;
            const baseX = pondCenter.x - pond.rx * 0.82 + lane * pond.rx * 1.64;
            const rise = (time * (14 + (bubble % 5) * 3) + bubble * 29) % (pond.ry * 1.55);
            const y = pondCenter.y + pond.ry * 0.68 - rise;
            const x = baseX + Math.sin(time * 0.8 + bubble) * 10;
            const size = 2.2 + (bubble % 4) * 1.3;

            ctx.globalAlpha = 0.08 + (bubble % 3) * 0.035;
            ctx.strokeStyle = '#d7fff3';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(x, y, size, 0, Math.PI * 2);
            ctx.stroke();
        }

        for (let plant = 0; plant < 34; plant++) {
            const spread = (plant * 0.381966) % 1;
            const baseX = pondCenter.x - pond.rx * 0.78 + spread * pond.rx * 1.56;
            const baseY = pondCenter.y + pond.ry * (0.28 + (plant % 6) * 0.085);
            const height = 42 + (plant % 5) * 12;
            const sway = Math.sin(time * 1.4 + plant * 0.9) * 10;
            ctx.globalAlpha = 0.14;
            ctx.strokeStyle = plant % 3 === 0 ? '#7bbf73' : '#4c9a68';
            ctx.lineWidth = 2 + (plant % 2);
            ctx.beginPath();
            ctx.moveTo(baseX, baseY);
            ctx.bezierCurveTo(baseX + sway * 0.2, baseY - height * 0.35, baseX + sway, baseY - height * 0.72, baseX + sway * 0.7, baseY - height);
            ctx.stroke();
        }

        if (frenzy > 0) {
            ctx.globalAlpha = frenzy * 0.18;
            ctx.strokeStyle = '#fef9c3';
            ctx.lineWidth = 1.2;
            for (let bubble = 0; bubble < 10; bubble++) {
                const angle = bubble * 2.17 + time * 0.35;
                const radius = 42 + (bubble % 5) * 26;
                const x = pondCenter.x + Math.cos(angle) * radius;
                const y = pondCenter.y + Math.sin(angle * 1.3) * radius * 0.48;
                const size = 3 + (bubble % 3) * 2;
                ctx.beginPath();
                ctx.arc(x, y, size, 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        ctx.restore();
    }

    drawSnakeWaterWake() {
        if (!this.isSurvivalMode() || this.isTrainMode() || this.trail.length < 3) return;

        const ctx = this.ctx;
        const bodyLength = Math.min(this.getSnakeBodyLength(), 520);
        const thickness = this.getSnakeThickness();
        const head = this.worldToScreen(this.head);

        ctx.save();
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.strokeStyle = 'rgba(210, 252, 244, 0.28)';
        ctx.lineWidth = 2;

        for (let distance = 18; distance <= bodyLength; distance += 34) {
            const point = this.getPointAtDistance(distance);
            const next = this.getPointAtDistance(distance + 18);
            const screen = this.worldToScreen(point);
            const nextScreen = this.worldToScreen(next);
            const angle = Math.atan2(screen.y - nextScreen.y, screen.x - nextScreen.x);
            const sideAngle = angle + Math.PI / 2;
            const wakeSize = Math.max(8, thickness * (0.55 - distance / (bodyLength * 1.7)));
            const alpha = Math.max(0.05, 0.22 * (1 - distance / (bodyLength + 40)));

            ctx.globalAlpha = alpha;
            [-1, 1].forEach((side) => {
                const ox = screen.x + Math.cos(sideAngle) * side * (thickness * 0.72);
                const oy = screen.y + Math.sin(sideAngle) * side * (thickness * 0.72);
                ctx.beginPath();
                ctx.ellipse(ox, oy, wakeSize * 1.8, wakeSize * 0.55, angle, 0, Math.PI * 2);
                ctx.stroke();
            });
        }

        ctx.globalAlpha = 0.24;
        ctx.strokeStyle = 'rgba(231, 255, 250, 0.42)';
        for (let ring = 0; ring < 3; ring++) {
            const size = thickness * (1.1 + ring * 0.48) + Math.sin(this.frame * 0.12 + ring) * 2;
            ctx.beginPath();
            ctx.ellipse(head.x - Math.cos(this.head.heading) * 12, head.y - Math.sin(this.head.heading) * 12, size * 1.2, size * 0.42, this.head.heading, 0, Math.PI * 2);
            ctx.stroke();
        }

        ctx.restore();
    }

    drawMeaningPopups() {
        if (this.meaningPopups.length === 0) return;

        const ctx = this.ctx;
        this.meaningPopups.forEach((popup) => {
            const p = this.worldToScreen(popup);
            const progress = popup.life / popup.maxLife;
            const alpha = Math.min(1, progress * 1.8);
            if (p.x < -180 || p.x > this.width + 180 || p.y < 70 || p.y > this.height + 60) return;

            ctx.save();
            ctx.globalAlpha = alpha;
            ctx.font = `800 ${popup.bonus ? 18 : 16}px ${this.fontHeading()}`;
            const padding = popup.bonus ? 18 : 14;
            const textWidth = Math.min(320, ctx.measureText(popup.text).width + padding * 2);
            const height = popup.bonus ? 38 : 34;
            const x = p.x - textWidth / 2;
            const y = p.y - height / 2;

            ctx.fillStyle = popup.bonus ? 'rgba(92, 58, 10, 0.78)' : 'rgba(10, 32, 38, 0.72)';
            ctx.strokeStyle = popup.bonus ? 'rgba(253, 224, 71, 0.62)' : 'rgba(167, 243, 208, 0.32)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.roundRect(x, y, textWidth, height, 12);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = popup.bonus ? '#fde68a' : '#d1fae5';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(popup.text, p.x, p.y + 1, textWidth - padding);
            ctx.restore();
        });
    }

    drawWorldBoundary() {
        if (!this.motoMode) return;

        const ctx = this.ctx;
        const camera = this.getCamera();
        const bounds = this.worldBounds;
        if (this.isSurvivalMode()) {
            if (this.isTrainMode()) return;
            const pond = this.getLotusPondShape(0);
            const center = this.worldToScreen({ x: pond.cx, y: pond.cy });

            ctx.save();
            ctx.strokeStyle = 'rgba(15, 23, 42, 0.22)';
            ctx.lineWidth = 4;
            ctx.setLineDash([18, 22]);
            ctx.beginPath();
            ctx.ellipse(center.x, center.y, pond.rx, pond.ry, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.restore();
            return;
        }

        const x = bounds.left - camera.x;
        const y = bounds.top - camera.y;
        const width = bounds.right - bounds.left;
        const height = bounds.bottom - bounds.top;

        ctx.save();
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.46)';
        ctx.lineWidth = 5;
        ctx.setLineDash([18, 18]);
        ctx.shadowColor = 'rgba(15, 23, 42, 0.18)';
        ctx.shadowBlur = 6;
        ctx.strokeRect(x, y, width, height);
        ctx.setLineDash([]);

        ctx.fillStyle = 'rgba(15, 23, 42, 0.08)';
        ctx.fillRect(x, y, width, 14);
        ctx.fillRect(x, y + height - 14, width, 14);
        ctx.fillRect(x, y, 14, height);
        ctx.fillRect(x + width - 14, y, 14, height);
        ctx.restore();
    }

    drawTrain() {
        const ctx = this.ctx;
        const bodyLength = this.getSnakeBodyLength();
        const spacing = 34;
        const cars = [];
        for (let distance = 0; distance <= bodyLength; distance += spacing) {
            const point = this.worldToScreen(this.getPointAtDistance(distance));
            const next = this.worldToScreen(this.getPointAtDistance(distance + 18));
            const angle = Math.atan2(point.y - next.y, point.x - next.x);
            cars.push({ ...point, angle });
        }
        if (cars.length === 0) return;

        ctx.save();
        for (let index = cars.length - 1; index >= 1; index--) {
            this.drawTrainCar(cars[index], index);
        }
        ctx.restore();
        this.drawTrainEngine(cars[0]);
    }

    applyTrainUprightTransform(ctx, x, y, angle, scale = 1) {
        const forwardX = Math.cos(angle);
        const forwardY = Math.sin(angle);
        let downX = -Math.sin(angle);
        let downY = Math.cos(angle);
        if (downY < 0) {
            downX *= -1;
            downY *= -1;
        }
        ctx.transform(
            forwardX * scale,
            forwardY * scale,
            downX * scale,
            downY * scale,
            x,
            y
        );
    }

    drawTrainCar(car, index) {
        const ctx = this.ctx;
        const width = 34;
        const height = 22;
        const bottomY = height * 0.52;
        const colors = ['#dc2626', '#2563eb', '#16a34a', '#ca8a04'];
        ctx.save();
        this.applyTrainUprightTransform(ctx, car.x, car.y, car.angle);

        ctx.fillStyle = 'rgba(20, 20, 20, 0.32)';
        ctx.beginPath();
        ctx.roundRect(-width * 0.52, -height * 0.42 + 4, width, height * 0.86, 6);
        ctx.fill();

        ctx.fillStyle = colors[index % colors.length];
        ctx.strokeStyle = '#1f2937';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(-width * 0.55, -height * 0.5, width, height, 6);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = 'rgba(219, 234, 254, 0.86)';
        ctx.fillRect(-width * 0.2, -height * 0.25, 7, 6);
        ctx.fillRect(width * 0.08, -height * 0.25, 7, 6);

        ctx.fillStyle = '#111827';
        ctx.beginPath();
        ctx.arc(-width * 0.25, bottomY, 3.4, 0, Math.PI * 2);
        ctx.arc(width * 0.25, bottomY, 3.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    drawTrainEngine(engine) {
        const ctx = this.ctx;
        const width = 42;
        const height = 26;
        const frontX = width * 0.48;
        const bottomY = height * 0.52;
        const topY = -height * 0.5;
        const pulse = this.growthTimer > 0 ? 1 + Math.sin(this.growthTimer * 0.28) * 0.03 : 1;
        ctx.save();
        this.applyTrainUprightTransform(ctx, engine.x, engine.y, engine.angle, pulse);

        const headlightGradient = ctx.createRadialGradient(frontX + 4, 0, 2, frontX + 36, 0, 58);
        headlightGradient.addColorStop(0, 'rgba(254, 240, 138, 0.34)');
        headlightGradient.addColorStop(0.55, 'rgba(254, 240, 138, 0.12)');
        headlightGradient.addColorStop(1, 'rgba(254, 240, 138, 0)');
        ctx.fillStyle = headlightGradient;
        ctx.beginPath();
        ctx.moveTo(frontX, -7);
        ctx.lineTo(frontX + 62, -24);
        ctx.lineTo(frontX + 62, 24);
        ctx.lineTo(frontX, 7);
        ctx.closePath();
        ctx.fill();

        ctx.fillStyle = 'rgba(20, 20, 20, 0.35)';
        ctx.beginPath();
        ctx.roundRect(-width * 0.55, -height * 0.42 + 5, width * 1.1, height * 0.84, 8);
        ctx.fill();

        ctx.fillStyle = '#b91c1c';
        ctx.strokeStyle = '#1f2937';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.roundRect(-width * 0.45, -height * 0.5, width * 0.9, height, 8);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#111827';
        ctx.fillRect(width * 0.12, topY - 10, 9, 12);
        ctx.fillStyle = '#fbbf24';
        ctx.beginPath();
        ctx.arc(frontX, 0, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#fef3c7';
        ctx.lineWidth = 1.4;
        ctx.stroke();

        ctx.fillStyle = '#dbeafe';
        ctx.fillRect(-width * 0.24, topY + 4, 15, 9);
        ctx.fillStyle = '#111827';
        ctx.beginPath();
        ctx.arc(-width * 0.25, bottomY, 4, 0, Math.PI * 2);
        ctx.arc(width * 0.2, bottomY, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    drawSnake() {
        const ctx = this.ctx;
        const bodyLength = this.getSnakeBodyLength();
        const sampleSpacing = 14;
        const worldPositions = [];

        for (let distance = 0; distance <= bodyLength; distance += sampleSpacing) {
            worldPositions.push(this.getPointAtDistance(distance));
        }
        const positions = worldPositions.map(point => this.worldToScreen(point));

        ctx.save();
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        const thickness = this.getSnakeThickness();
        const isPoisoned = this.poisonTimer > 0;
        const poisonWave = isPoisoned ? Math.sin(this.frame * 0.45) * 2.5 : 0;
        const layers = [
            { width: thickness + 13, color: 'rgba(2, 8, 23, 0.5)' },
            { width: thickness + 6, color: isPoisoned ? '#526b13' : '#0f3f3b' },
            { width: thickness, color: isPoisoned ? '#baff29' : '#2f9d83' },
            { width: Math.max(8, thickness * 0.5), color: isPoisoned ? 'rgba(240, 255, 80, 0.72)' : 'rgba(151, 211, 194, 0.58)' }
        ];

        layers.forEach((layer) => {
            if (positions.length < 2) return;
            ctx.strokeStyle = layer.color;
            ctx.lineWidth = layer.width;
            ctx.beginPath();
            ctx.moveTo(positions[0].x + poisonWave, positions[0].y);
            for (let index = 1; index < positions.length; index++) {
                const previous = positions[index - 1];
                const current = positions[index];
                const wobble = isPoisoned ? Math.sin(this.frame * 0.35 + index * 0.9) * 3.5 : 0;
                const midX = (previous.x + current.x) / 2 + wobble;
                const midY = (previous.y + current.y) / 2;
                ctx.quadraticCurveTo(previous.x + wobble, previous.y, midX, midY);
            }
            ctx.stroke();
        });

        ctx.save();
        ctx.globalAlpha = isPoisoned ? 0.38 : 0.32;
        ctx.fillStyle = isPoisoned ? '#efff7a' : '#c7e8dc';
        for (let index = 5; index < positions.length; index += 4) {
            const point = positions[index];
            const previous = positions[Math.max(0, index - 1)];
            const angle = Math.atan2(point.y - previous.y, point.x - previous.x) + Math.PI / 2;
            const side = index % 8 === 0 ? 1 : -1;
            const offset = thickness * 0.26 * side;
            const scale = 0.62 + (index % 3) * 0.08;
            ctx.beginPath();
            ctx.ellipse(
                point.x + Math.cos(angle) * offset,
                point.y + Math.sin(angle) * offset,
                thickness * 0.17 * scale,
                thickness * 0.09 * scale,
                angle,
                0,
                Math.PI * 2
            );
            ctx.fill();
        }
        ctx.restore();

        if (isPoisoned) {
            ctx.globalAlpha = 0.75;
            ctx.fillStyle = '#d9ff4f';
            for (let index = 7; index < positions.length; index += 7) {
                const point = positions[index];
                const bubble = 3 + Math.sin(this.frame * 0.2 + index) * 1.5;
                ctx.beginPath();
                ctx.arc(point.x, point.y - thickness * 0.65, bubble, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();

        this.drawSnakeHead(positions[0] || this.head);
    }

    drawAutoSnake() {
        if (!this.autoSnakeEnabled) return;

        this.getActiveAutoSnakes().forEach((snake) => this.drawSingleAutoSnake(snake));
    }

    drawSingleAutoSnake(snake) {
        if (!snake || !snake.active) return;
        const ctx = this.ctx;
        const bodyLength = this.getAutoSnakeBodyLength(snake);
        const sampleSpacing = 18;
        const worldPositions = [];
        for (let distance = 0; distance <= bodyLength; distance += sampleSpacing) {
            worldPositions.push(this.getAutoPointAtDistance(distance, snake));
        }
        const positions = worldPositions.map(point => this.worldToScreen(point));
        if (positions.length < 2) return;

        const thickness = this.getAutoSnakeThickness(snake);
        const colors = snake.colors || AUTO_SNAKE_COLORS[0];
        const layers = [
            { width: thickness + 12, color: colors.shadow },
            { width: thickness + 5, color: colors.dark },
            { width: thickness, color: colors.body },
            { width: Math.max(7, thickness * 0.45), color: colors.glow }
        ];

        ctx.save();
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        layers.forEach((layer) => {
            ctx.strokeStyle = layer.color;
            ctx.lineWidth = layer.width;
            ctx.beginPath();
            ctx.moveTo(positions[0].x, positions[0].y);
            for (let index = 1; index < positions.length; index++) {
                const previous = positions[index - 1];
                const current = positions[index];
                const midX = (previous.x + current.x) / 2;
                const midY = (previous.y + current.y) / 2;
                ctx.quadraticCurveTo(previous.x, previous.y, midX, midY);
            }
            ctx.stroke();
        });
        ctx.restore();

        this.drawAutoSnakeHead(snake, positions[0]);
    }

    drawAutoSnakeHead(snake, position) {
        if (!snake) return;

        const ctx = this.ctx;
        const radius = this.getAutoSnakeThickness(snake) * 1.14;
        const angle = snake.head.heading;
        const pulse = snake.growthTimer > 0 ? 1 + Math.sin(snake.growthTimer * 0.28) * 0.05 : 1;
        const colors = snake.colors || AUTO_SNAKE_COLORS[0];

        ctx.save();
        ctx.translate(position.x, position.y);
        ctx.rotate(angle);
        ctx.scale(pulse, pulse);

        ctx.fillStyle = colors.shadow;
        ctx.beginPath();
        ctx.ellipse(-radius * 0.16, radius * 0.18, radius * 1.08, radius * 0.84, 0, 0, Math.PI * 2);
        ctx.fill();

        const gradient = ctx.createRadialGradient(-radius * 0.3, -radius * 0.26, radius * 0.1, 0, 0, radius * 1.1);
        gradient.addColorStop(0, colors.headLight);
        gradient.addColorStop(0.45, colors.body);
        gradient.addColorStop(1, colors.headEnd);
        ctx.fillStyle = gradient;
        ctx.strokeStyle = colors.dark;
        ctx.lineWidth = 3.4;
        ctx.beginPath();
        ctx.ellipse(0, 0, radius * 1.04, radius * 0.88, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#1f2937';
        ctx.beginPath();
        ctx.arc(radius * 0.28, -radius * 0.25, radius * 0.09, 0, Math.PI * 2);
        ctx.arc(radius * 0.28, radius * 0.25, radius * 0.09, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = colors.headLight;
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.moveTo(radius * 0.92, -2);
        ctx.lineTo(radius * 1.28, -radius * 0.18);
        ctx.moveTo(radius * 0.92, 2);
        ctx.lineTo(radius * 1.28, radius * 0.18);
        ctx.stroke();
        ctx.restore();
    }

    getSnakeBodyLength() {
        return 100 + Math.max(0, this.segments.length - 1) * 68;
    }

    getSnakeThickness() {
        const base = 21 + Math.min(13, Math.max(0, this.segments.length - 1) * 0.85);
        const growthPulse = this.growthTimer > 0 ? Math.sin(this.growthTimer * 0.28) * 3 : 0;
        const poisonShrink = this.poisonTimer > 0 ? 5 : 0;
        return Math.max(18, base + growthPulse - poisonShrink);
    }

    getAutoSnakeBodyLength(snake = this.autoSnake) {
        if (!snake) return 0;
        return 100 + Math.max(0, snake.segments - 1) * 68;
    }

    getAutoSnakeThickness(snake = this.autoSnake) {
        if (!snake) return 18;
        const base = 19 + Math.min(12, Math.max(0, snake.segments - 1) * 0.85);
        const growthPulse = snake.growthTimer > 0 ? Math.sin(snake.growthTimer * 0.28) * 3 : 0;
        return Math.max(17, base + growthPulse);
    }

    getPointAtDistance(targetDistance) {
        if (targetDistance <= 0 || this.trail.length < 2) {
            return { x: this.head.x, y: this.head.y };
        }

        let walked = 0;
        for (let index = 1; index < this.trail.length; index++) {
            const prev = this.trail[index - 1];
            const next = this.trail[index];
            const segmentDistance = Math.hypot(prev.x - next.x, prev.y - next.y);

            if (walked + segmentDistance >= targetDistance) {
                const ratio = (targetDistance - walked) / (segmentDistance || 1);
                return {
                    x: prev.x + (next.x - prev.x) * ratio,
                    y: prev.y + (next.y - prev.y) * ratio
                };
            }
            walked += segmentDistance;
        }

        return this.trail[this.trail.length - 1] || this.head;
    }

    getAutoPointAtDistance(targetDistance, snake = this.autoSnake) {
        if (!snake) return { x: this.head.x, y: this.head.y };
        if (targetDistance <= 0 || snake.trail.length < 2) {
            return { x: snake.head.x, y: snake.head.y };
        }

        let walked = 0;
        for (let index = 1; index < snake.trail.length; index++) {
            const prev = snake.trail[index - 1];
            const next = snake.trail[index];
            const segmentDistance = Math.hypot(prev.x - next.x, prev.y - next.y);

            if (walked + segmentDistance >= targetDistance) {
                const ratio = (targetDistance - walked) / (segmentDistance || 1);
                return {
                    x: prev.x + (next.x - prev.x) * ratio,
                    y: prev.y + (next.y - prev.y) * ratio
                };
            }
            walked += segmentDistance;
        }

        return snake.trail[snake.trail.length - 1] || snake.head;
    }

    drawSnakeHead(position) {
        const ctx = this.ctx;
        const radius = this.getSnakeThickness() * 1.22;
        const fill = this.poisonTimer > 0 ? '#baff29' : '#6bc6a8';
        const angle = this.head.heading;
        const pulse = this.growthTimer > 0 ? 1 + Math.sin(this.growthTimer * 0.28) * 0.05 : 1;

        ctx.save();
        ctx.translate(position.x, position.y);
        ctx.rotate(angle);
        ctx.scale(pulse, pulse);

        ctx.fillStyle = 'rgba(2, 8, 23, 0.28)';
        ctx.beginPath();
        ctx.ellipse(-radius * 0.18, radius * 0.18, radius * 1.12, radius * 0.86, 0, 0, Math.PI * 2);
        ctx.fill();

        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        const headGradient = ctx.createRadialGradient(
            -radius * 0.32,
            -radius * 0.26,
            radius * 0.15,
            0,
            0,
            radius * 1.18
        );
        headGradient.addColorStop(0, '#b8c4bf');
        headGradient.addColorStop(0.42, fill);
        headGradient.addColorStop(1, this.poisonTimer > 0 ? '#80a81d' : '#287a68');
        ctx.fillStyle = headGradient;
        ctx.strokeStyle = '#042033';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.ellipse(0, 0, radius * 1.08, radius * 0.92, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = this.poisonTimer > 0 ? 'rgba(240, 255, 80, 0.38)' : 'rgba(14, 165, 233, 0.22)';
        for (let scale = -0.44; scale <= 0.44; scale += 0.22) {
            ctx.beginPath();
            ctx.ellipse(-radius * 0.42, radius * scale, radius * 0.13, radius * 0.075, 0.2, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.fillStyle = 'rgba(148, 163, 158, 0.34)';
        ctx.beginPath();
        ctx.ellipse(-radius * 0.26, -radius * 0.34, radius * 0.28, radius * 0.15, -0.4, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#9ca3af';
        ctx.beginPath();
        ctx.arc(radius * 0.28, -radius * 0.28, radius * 0.23, 0, Math.PI * 2);
        ctx.arc(radius * 0.28, radius * 0.28, radius * 0.23, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#082f49';
        ctx.beginPath();
        ctx.arc(radius * 0.34, -radius * 0.28, radius * 0.1, 0, Math.PI * 2);
        ctx.arc(radius * 0.34, radius * 0.28, radius * 0.1, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#6b7280';
        ctx.beginPath();
        ctx.arc(radius * 0.38, -radius * 0.33, radius * 0.035, 0, Math.PI * 2);
        ctx.arc(radius * 0.38, radius * 0.23, radius * 0.035, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = 'rgba(255, 141, 196, 0.7)';
        ctx.beginPath();
        ctx.arc(radius * 0.03, -radius * 0.45, radius * 0.12, 0, Math.PI * 2);
        ctx.arc(radius * 0.03, radius * 0.45, radius * 0.12, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = '#075985';
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.arc(radius * 0.53, 0, radius * 0.18, Math.PI * 0.22, Math.PI * 0.78);
        ctx.stroke();

        ctx.strokeStyle = this.poisonTimer > 0 ? '#f0ff50' : '#a7f3d0';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(radius * 1.02, -2);
        ctx.lineTo(radius * 1.48, -radius * 0.22);
        ctx.moveTo(radius * 1.02, 2);
        ctx.lineTo(radius * 1.48, radius * 0.22);
        ctx.stroke();

        ctx.restore();
    }

    drawFood(food) {
        const ctx = this.ctx;
        food.pulse += 0.04;
        const isCorrect = this.isFoodCorrect(food);
        const showHint = this.hintEnabled && isCorrect;
        const distanceToSnake = Math.hypot(food.x - this.head.x, food.y - this.head.y);
        const snakeIsNear = this.isSurvivalMode() && distanceToSnake < 170;
        const radius = this.isSurvivalMode() ? food.radius : food.radius + Math.sin(food.pulse) * 3;
        const bobX = this.isSurvivalMode() ? Math.cos(food.pulse * 0.45 + food.wavePhase) * 2.5 : Math.cos(food.pulse * 0.7 + food.wavePhase) * 5;
        const bobY = this.isSurvivalMode() ? Math.sin(food.pulse * 0.55 + food.wavePhase) * 3.5 : Math.sin(food.pulse + food.wavePhase) * 7;
        const screenFood = this.worldToScreen(food);
        const drawX = screenFood.x + bobX;
        const drawY = screenFood.y + bobY;
        const spawnAlpha = this.isSurvivalMode() ? Math.min(1, (food.spawnAge || 0) / 28) : 1;

        if (!this.isSurvivalMode()) {
            ctx.save();
            ctx.globalAlpha = 0.36;
            ctx.strokeStyle = '#bae6fd';
            ctx.lineWidth = 2;
            const wakeAngle = Math.atan2(food.vy, food.vx) + Math.PI;
            for (let index = 1; index <= 3; index++) {
                const wakeX = drawX + Math.cos(wakeAngle) * (radius + index * 10);
                const wakeY = drawY + Math.sin(wakeAngle) * (radius + index * 10);
                ctx.beginPath();
                ctx.arc(wakeX, wakeY, radius * (0.52 + index * 0.18), wakeAngle - 0.55, wakeAngle + 0.55);
                ctx.stroke();
            }
            ctx.restore();
        }

        ctx.save();
        ctx.globalAlpha = spawnAlpha;
        ctx.shadowColor = showHint
            ? 'rgba(34, 197, 94, 0.55)'
            : (snakeIsNear ? 'rgba(251, 191, 36, 0.42)' : 'rgba(56, 189, 248, 0.16)');
        ctx.shadowBlur = showHint ? 10 : (snakeIsNear ? 8 : 2);
        ctx.fillStyle = showHint ? 'rgba(34, 197, 94, 0.78)' : 'rgba(15, 23, 42, 0.82)';
        ctx.strokeStyle = showHint ? '#34d399' : 'rgba(125, 211, 252, 0.62)';
        ctx.lineWidth = showHint ? 3 : 1.5;
        ctx.beginPath();
        ctx.arc(drawX, drawY, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.save();
        ctx.globalAlpha = 0.18;
        ctx.fillStyle = '#dbeafe';
        ctx.beginPath();
        ctx.arc(drawX - radius * 0.28, drawY - radius * 0.32, radius * 0.24, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        ctx.font = `bold ${Math.round(radius * 1.12)}px ${this.fontHeading()}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(food.item.emoji || '●', drawX, drawY + 1);
        if (snakeIsNear) {
            ctx.save();
            ctx.globalAlpha = 0.38 + Math.sin(food.pulse * 2.4) * 0.14;
            ctx.strokeStyle = 'rgba(254, 240, 138, 0.82)';
            ctx.lineWidth = 1.4;
            for (let sparkle = 0; sparkle < 4; sparkle++) {
                const angle = food.pulse * 0.9 + sparkle * Math.PI / 2;
                const sx = drawX + Math.cos(angle) * (radius + 9);
                const sy = drawY + Math.sin(angle) * (radius + 8);
                ctx.beginPath();
                ctx.moveTo(sx - 3, sy);
                ctx.lineTo(sx + 3, sy);
                ctx.moveTo(sx, sy - 3);
                ctx.lineTo(sx, sy + 3);
                ctx.stroke();
            }
            ctx.restore();
        }
        if (this.isSurvivalMode() || food.type === 'en') {
            this.drawBubbleText(drawX, drawY - radius - 18, food.item.word, false);
        }
        ctx.restore();
    }

    drawBubbleText(x, y, text, highlight) {
        const ctx = this.ctx;
        ctx.save();
        ctx.font = `700 ${highlight ? 18 : 16}px ${this.fontHeading()}`;
        const maxWidth = Math.min(260, this.width - 40);
        const measuredWidth = Math.min(maxWidth, ctx.measureText(text).width + 28);
        const height = highlight ? 38 : 34;
        if (
            x < -measuredWidth / 2 ||
            x > this.width + measuredWidth / 2 ||
            y < 80 - height ||
            y > this.height + height
        ) {
            ctx.restore();
            return;
        }

        const boxX = x - measuredWidth / 2;
        const boxY = y - height / 2;

        ctx.fillStyle = highlight ? 'rgba(34, 197, 94, 0.18)' : 'rgba(15, 23, 42, 0.74)';
        ctx.strokeStyle = highlight ? 'rgba(52, 211, 153, 0.72)' : 'rgba(125, 211, 252, 0.24)';
        ctx.lineWidth = highlight ? 2 : 1.5;
        ctx.beginPath();
        ctx.roundRect(boxX, boxY, measuredWidth, height, 12);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = highlight ? '#d1fae5' : '#cbd5e1';
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, boxX + measuredWidth / 2, boxY + height / 2 + 1, maxWidth - 22);
        ctx.restore();
    }

    drawParticles() {
        const ctx = this.ctx;
        this.particles.forEach((particle) => {
            const screenParticle = this.worldToScreen(particle);
            ctx.save();
            ctx.globalAlpha = Math.max(0, particle.life / 55);
            ctx.fillStyle = particle.color;
            ctx.shadowColor = particle.color;
            ctx.shadowBlur = 12;
            ctx.beginPath();
            ctx.arc(screenParticle.x, screenParticle.y, particle.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        });
    }

    drawSpeedBoostEffect() {
        if (this.speedMultiplier <= 1 && this.speedBoostFlash <= 0) return;

        const ctx = this.ctx;
        const head = this.worldToScreen(this.head);
        const flashProgress = this.speedBoostFlash > 0 ? 1 - (this.speedBoostFlash / 35) : 1;
        const boostStrength = Math.min(1, (this.speedMultiplier - 1) / (SPEED_BOOST_MULTIPLIER - 1));
        const backAngle = this.head.heading + Math.PI;
        const tailX = head.x + Math.cos(backAngle) * 150;
        const tailY = head.y + Math.sin(backAngle) * 150;
        const flareX = head.x + Math.cos(backAngle) * 44;
        const flareY = head.y + Math.sin(backAngle) * 44;

        ctx.save();
        ctx.globalCompositeOperation = 'lighter';

        if (this.speedBoostFlash > 0) {
            ctx.globalAlpha = Math.max(0, 0.45 * (1 - flashProgress));
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 5;
            ctx.shadowColor = '#38bdf8';
            ctx.shadowBlur = 18;
            ctx.beginPath();
            ctx.arc(head.x, head.y, 24 + flashProgress * 48, 0, Math.PI * 2);
            ctx.stroke();
        }

        const beam = ctx.createLinearGradient(head.x, head.y, tailX, tailY);
        beam.addColorStop(0, `rgba(56, 189, 248, ${0.42 + boostStrength * 0.22})`);
        beam.addColorStop(0.45, 'rgba(0, 255, 136, 0.22)');
        beam.addColorStop(1, 'rgba(56, 189, 248, 0)');

        ctx.globalAlpha = 0.9;
        ctx.strokeStyle = beam;
        ctx.lineWidth = 30 + boostStrength * 12;
        ctx.lineCap = 'round';
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 22;
        ctx.beginPath();
        ctx.moveTo(flareX, flareY);
        ctx.lineTo(tailX, tailY);
        ctx.stroke();

        ctx.globalAlpha = 0.75;
        ctx.strokeStyle = '#e0faff';
        ctx.lineWidth = 4;
        ctx.shadowColor = '#ffffff';
        ctx.shadowBlur = 14;
        ctx.beginPath();
        ctx.moveTo(head.x + Math.cos(backAngle) * 30, head.y + Math.sin(backAngle) * 30);
        ctx.lineTo(head.x + Math.cos(backAngle) * 98, head.y + Math.sin(backAngle) * 98);
        ctx.stroke();

        ctx.restore();
    }

    drawSpeedBoostReadyHint() {
        if (this.state !== 'playing') return;
        if (this.speedMultiplier > 1 || this.elapsedGameSeconds < this.nextSpeedBoostAt) return;

        const ctx = this.ctx;
        const head = this.worldToScreen(this.head);
        const pulse = (Math.sin(this.frame * 0.12) + 1) / 2;
        const radius = this.getSnakeThickness() * (1.45 + pulse * 0.12);

        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        ctx.globalAlpha = 0.16 + pulse * 0.12;
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 18 + pulse * 8;
        ctx.beginPath();
        ctx.arc(head.x, head.y, radius, 0, Math.PI * 2);
        ctx.stroke();

        ctx.globalAlpha = 0.1 + pulse * 0.08;
        ctx.fillStyle = '#00ff88';
        ctx.beginPath();
        ctx.arc(head.x, head.y, radius * 0.72, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    drawOverlayText(text) {
        const ctx = this.ctx;
        ctx.save();
        ctx.fillStyle = 'rgba(2, 6, 12, 0.42)';
        ctx.fillRect(0, 0, this.width, this.height);
        ctx.font = `800 56px ${this.fontHeading()}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#ffffff';
        ctx.shadowColor = '#00f0ff';
        ctx.shadowBlur = 20;
        ctx.fillText(text, this.width / 2, this.height / 2);
        ctx.restore();
    }

    fontHeading() {
        return getComputedStyle(document.documentElement).getPropertyValue('--font-heading') || 'Fredoka, sans-serif';
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const rest = seconds % 60;
        return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
    }

    getStorageKey(prefix) {
        return this.getStorageKeyForMode(prefix, this.mode, this.vocabSource);
    }

    getStorageKeyForMode(prefix, mode, source = this.vocabSource) {
        return `${prefix}_word_snake_${source}_${mode}`;
    }

    resetLearningState() {
        const confirmed = window.confirm('Reset all play history and high scores for every mode?');
        if (!confirmed) return;

        Object.keys(MODE_CONFIG).forEach((mode) => {
            localStorage.removeItem(`hscore_word_snake_${mode}`);
            localStorage.removeItem(`history_word_snake_${mode}`);
            Object.keys(VOCAB_SOURCES).forEach((source) => {
                localStorage.removeItem(this.getStorageKeyForMode('hscore', mode, source));
                localStorage.removeItem(this.getStorageKeyForMode('history', mode, source));
            });
        });

        this.updateStartHighScore();
        this.renderStartPlayHistory();
    }

    updateStartHighScore() {
        document.getElementById('start-high-score').innerText = this.getHighScore();
    }

    getHighScore() {
        return Number(localStorage.getItem(this.getStorageKey('hscore')) || 0);
    }

    saveHighScore() {
        if (this.score > this.getHighScore()) {
            localStorage.setItem(this.getStorageKey('hscore'), String(this.score));
        }
    }

    getPlayHistory() {
        try {
            return JSON.parse(localStorage.getItem(this.getStorageKey('history')) || '[]');
        } catch (error) {
            return [];
        }
    }

    savePlayHistory() {
        const history = this.getPlayHistory();
        const accuracy = this.correct + this.incorrect === 0
            ? 100
            : Math.round((this.correct / (this.correct + this.incorrect)) * 100);

        history.unshift({
            score: this.score,
            accuracy,
            correct: this.correct,
            combo: this.bestCombo,
            playedAt: new Date().toISOString()
        });
        localStorage.setItem(this.getStorageKey('history'), JSON.stringify(history.slice(0, 10)));
    }

    renderStartPlayHistory() {
        this.renderHistoryInto('start-play-history-list');
    }

    renderPlayHistory() {
        this.renderHistoryInto('play-history-list');
    }

    renderHistoryInto(elementId) {
        const container = document.getElementById(elementId);
        if (!container) return;

        const history = this.getPlayHistory();
        container.innerHTML = '';

        if (history.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'history-row';
            empty.innerHTML = '<span class="history-rank">--</span><span class="history-date">No plays yet</span><span class="history-score">0</span>';
            container.appendChild(empty);
            return;
        }

        history.forEach((row, index) => {
            const item = document.createElement('div');
            item.className = 'history-row';
            const date = new Date(row.playedAt).toLocaleDateString();
            item.innerHTML = `
                <span class="history-rank">#${index + 1}</span>
                <span class="history-date">${date} · ${row.accuracy}% · ${row.correct} words</span>
                <span class="history-score">${row.score}</span>
            `;
            container.appendChild(item);
        });
    }
}

window.addEventListener('load', () => {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
    new WordSnakeGame();
});
