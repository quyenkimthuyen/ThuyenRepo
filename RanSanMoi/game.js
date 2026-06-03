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
        speechOrder: ['en'],
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
        this.meaningPopups = [];
        this.fishFrenzyTimer = 0;
        this.lotusBonusTimer = 0;
        this.nextLotusAmbientAt = 0;
        this.autoSnakeEnabled = false;
        this.autoSnake = null;
        this.autoSnakeGrowthTimer = 0;
        this.autoSnakeRespawnTimer = 0;
        this.autoSnakeColorIndex = 0;
        this.particles = [];
        this.currentPromptType = 'vi';
        this.currentItem = null;
        this.speechEnabled = true;
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
        });

        const speechButton = document.getElementById('btn-bilingual-toggle');
        speechButton.addEventListener('click', () => {
            this.speechEnabled = !this.speechEnabled;
            speechButton.classList.toggle('active', this.speechEnabled);
            speechButton.innerText = this.speechEnabled ? 'VOICE' : 'QUIET';
            if (!this.speechEnabled && window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
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

    setMotoMode(enabled) {
        if (this.isSurvivalMode() && this.state === 'playing' && !enabled) {
            const motoButton = document.getElementById('btn-moto-toggle');
            if (motoButton) {
                motoButton.classList.add('active');
                motoButton.title = 'Lotus Pond uses moto camera';
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
            this.autoSnakeRespawnTimer = 0;
            this.initAutoSnake();
            this.fx.tone(440, 0.08, 'triangle', 0.035);
            this.fx.tone(660, 0.1, 'sine', 0.03, 0.06);
        } else {
            this.autoSnake = null;
            this.autoSnakeRespawnTimer = 0;
        }
        this.updateAutoSnakeButton();
    }

    updateAutoSnakeButton() {
        const button = document.getElementById('btn-auto-snake-toggle');
        if (!button) return;
        button.classList.toggle('active', this.autoSnakeEnabled);
        const waiting = this.autoSnakeEnabled && !this.autoSnake;
        button.title = this.autoSnakeEnabled ? 'Auto snake is on' : 'Auto snake is off';
        button.innerText = waiting ? 'AUTO...' : (this.autoSnakeEnabled ? 'AUTO ON' : 'AUTO');
    }

    initAutoSnake() {
        const pond = this.getLotusPondShape(72);
        const angle = this.head.heading + Math.PI;
        let x = pond.cx + Math.cos(angle) * pond.rx * 0.38;
        let y = pond.cy + Math.sin(angle) * pond.ry * 0.38;

        for (let attempt = 0; attempt < 24; attempt++) {
            if (!this.isPointOnSwampLand(x, y, 54) && Math.hypot(x - this.head.x, y - this.head.y) > 240) break;
            const randomAngle = Math.random() * Math.PI * 2;
            const radius = 0.18 + Math.random() * 0.55;
            x = pond.cx + Math.cos(randomAngle) * pond.rx * radius;
            y = pond.cy + Math.sin(randomAngle) * pond.ry * radius;
        }

        const colors = AUTO_SNAKE_COLORS[this.autoSnakeColorIndex % AUTO_SNAKE_COLORS.length];
        this.autoSnakeColorIndex++;
        this.autoSnake = {
            head: { x, y, vx: 0, vy: 0, heading: Math.random() * Math.PI * 2 },
            trail: [{ x, y }],
            segments: 1,
            active: true,
            bodyBiteCooldown: 0,
            colors
        };
        this.autoSnakeRespawnTimer = 0;
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
        document.body.classList.add('snake-mode');
        document.body.classList.toggle('swamp-mode', this.mode === 'swamp');
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
                motoButton.title = 'Lotus Pond uses moto camera';
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
        this.meaningPopups = [];
        this.fishFrenzyTimer = 0;
        this.lotusBonusTimer = 0;
        this.nextLotusAmbientAt = 0;
        this.autoSnakeEnabled = false;
        this.autoSnake = null;
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
            this.generateSwampTerrain();
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
        const driftSpeed = this.isSurvivalMode() ? 0 : (0.35 + Math.random() * 0.75) * 0.5;

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
            wavePhase: Math.random() * Math.PI * 2,
            waveStrength: 0.012 + Math.random() * 0.012,
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
        const margin = 86;
        let tries = 0;

        do {
            food.x = bounds.left + margin + Math.random() * Math.max(1, bounds.right - bounds.left - margin * 2);
            food.y = bounds.top + margin + Math.random() * Math.max(1, bounds.bottom - bounds.top - margin * 2);
            tries++;
        } while (tries < 80 && this.isFoodTooClose(food));
    }

    getFoodBounds() {
        if (this.isSurvivalMode()) {
            const pond = this.getLotusPondShape(48);
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
            return {
                x: b.left + w * x,
                y: b.top + h * y,
                rx: baseRadius * roundnessJitter,
                ry: baseRadius * (1.02 - (roundnessJitter - 0.9) * 0.35),
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
            makePatch(0.77, 0.72, 0.047, 0.1)
        ];

        const flowerRadius = (patchIndex) => {
            const patch = this.swampPatches[patchIndex];
            return Math.max(14, Math.min(patch.rx, patch.ry) * 0.5);
        };

        this.lotusFlowers = [
            makeFlower(0.3, 0.32, flowerRadius(0), -0.2),
            makeFlower(0.7, 0.28, flowerRadius(2), 0.4),
            makeFlower(0.52, 0.47, flowerRadius(3), 0.1),
            makeFlower(0.28, 0.74, flowerRadius(6), -0.55),
            makeFlower(0.72, 0.66, flowerRadius(7), 0.3)
        ];
    }

    isPointOnSwampLand(x, y, padding = 0) {
        if (!this.isSurvivalMode()) return false;

        const b = this.worldBounds;
        const pond = this.getLotusPondShape(padding);
        const nx = (x - pond.cx) / pond.rx;
        const ny = (y - pond.cy) / pond.ry;
        if (nx * nx + ny * ny > 1) {
            return true;
        }

        return this.swampPatches.some(patch => this.isPointInSwampPatch(x, y, patch, padding));
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
            if (this.isSurvivalMode()) {
                this.turnAwayFromLotusPondBank(wallTurnBlend, margin);
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
        if (!this.autoSnake || !this.autoSnake.active) {
            this.autoSnakeRespawnTimer -= deltaFrames;
            if (this.autoSnakeRespawnTimer <= 0) {
                this.initAutoSnake();
            }
            return;
        }

        const snake = this.autoSnake;
        if (snake.bodyBiteCooldown > 0) {
            snake.bodyBiteCooldown -= deltaFrames;
        }

        const target = this.getAutoSnakeTarget();
        let desiredHeading = target
            ? Math.atan2(target.y - snake.head.y, target.x - snake.head.x)
            : snake.head.heading + Math.sin(this.frame * 0.018) * 0.35;
        desiredHeading = this.getAutoSnakeAvoidanceHeading(snake, desiredHeading);
        desiredHeading = this.getSaferAutoSnakeHeading(snake, desiredHeading);
        const turnRate = 5.7 * deltaSeconds;
        const headingDelta = Math.atan2(
            Math.sin(desiredHeading - snake.head.heading),
            Math.cos(desiredHeading - snake.head.heading)
        );
        snake.head.heading += Math.max(-turnRate, Math.min(turnRate, headingDelta));

        this.turnAutoSnakeAwayFromLotusPondBank(snake, 1 - Math.pow(0.82, deltaFrames), 54);
        this.turnAutoSnakeAwayFromLotusLeaves(snake, 1 - Math.pow(0.78, deltaFrames));

        const speed = this.config.speed * 60 * 0.7 * 0.8 * this.speedMultiplier;
        snake.head.vx = Math.cos(snake.head.heading) * speed;
        snake.head.vy = Math.sin(snake.head.heading) * speed;
        snake.head.x += snake.head.vx * deltaSeconds;
        snake.head.y += snake.head.vy * deltaSeconds;

        const bounds = this.worldBounds;
        snake.head.x = Math.max(bounds.left + 24, Math.min(bounds.right - 24, snake.head.x));
        snake.head.y = Math.max(bounds.top + 24, Math.min(bounds.bottom - 24, snake.head.y));
        this.resolveAutoSnakeLandCollision(snake);

        snake.trail.unshift({ x: snake.head.x, y: snake.head.y });
        if (snake.trail.length > 1200) snake.trail.length = 1200;
    }

    getAutoSnakeTarget() {
        if (this.foods.length === 0 || !this.autoSnake) return null;
        const heading = this.autoSnake.head.heading;
        return this.foods.reduce((best, food) => {
            const distance = Math.hypot(food.x - this.autoSnake.head.x, food.y - this.autoSnake.head.y);
            const angle = Math.atan2(food.y - this.autoSnake.head.y, food.x - this.autoSnake.head.x);
            const turn = Math.abs(Math.atan2(Math.sin(angle - heading), Math.cos(angle - heading)));
            const frontBias = Math.cos(turn);
            const score = distance + turn * 190 + (frontBias < -0.15 ? 420 : 0);
            if (!best || score < best.score) return { ...food, distance, score };
            return best;
        }, null);
    }

    getAutoSnakeAvoidanceHeading(snake, desiredHeading) {
        const playerDistance = Math.hypot(this.head.x - snake.head.x, this.head.y - snake.head.y);
        if (playerDistance < 230) {
            const awayFromPlayer = Math.atan2(snake.head.y - this.head.y, snake.head.x - this.head.x);
            const strength = Math.max(0.28, 1 - playerDistance / 230);
            desiredHeading = this.blendHeading(desiredHeading, awayFromPlayer, strength);
        }

        if (this.isAutoSnakeHeadingDangerous(snake, desiredHeading)) {
            const left = snake.head.heading - Math.PI * 0.42;
            const right = snake.head.heading + Math.PI * 0.42;
            desiredHeading = this.scoreAutoSnakeHeading(snake, left) > this.scoreAutoSnakeHeading(snake, right) ? left : right;
        }
        return desiredHeading;
    }

    getSaferAutoSnakeHeading(snake, desiredHeading) {
        const maxTurn = Math.PI * 0.62;
        const delta = Math.atan2(Math.sin(desiredHeading - snake.head.heading), Math.cos(desiredHeading - snake.head.heading));
        let bestHeading = snake.head.heading + Math.max(-maxTurn, Math.min(maxTurn, delta));
        let bestScore = this.scoreAutoSnakeHeading(snake, bestHeading);
        [-0.72, -0.42, -0.22, 0.22, 0.42, 0.72].forEach((offset) => {
            const candidate = snake.head.heading + offset;
            const score = this.scoreAutoSnakeHeading(snake, candidate) - Math.abs(offset - delta) * 22;
            if (score > bestScore) {
                bestScore = score;
                bestHeading = candidate;
            }
        });
        return bestHeading;
    }

    isAutoSnakeHeadingDangerous(snake, heading) {
        return this.scoreAutoSnakeHeading(snake, heading) < -50;
    }

    scoreAutoSnakeHeading(snake, heading) {
        let score = 100;
        const probes = [58, 96, 136];
        probes.forEach((distance, index) => {
            const point = {
                x: snake.head.x + Math.cos(heading) * distance,
                y: snake.head.y + Math.sin(heading) * distance
            };
            if (this.isPointOnSwampLand(point.x, point.y, 34)) score -= 120 - index * 16;
            if (this.isPointNearAutoSnakeBody(point.x, point.y, 34, 112)) score -= 150 - index * 18;
            if (this.isPointNearPlayerBody(point.x, point.y, 42)) score -= 130 - index * 16;
            const playerDistance = Math.hypot(point.x - this.head.x, point.y - this.head.y);
            if (playerDistance < 150) score -= (150 - playerDistance) * 0.9;
        });

        const target = this.getAutoSnakeTarget();
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

    turnAutoSnakeAwayFromLotusLeaves(snake, blendAmount) {
        const hitPatch = this.swampPatches.find(patch => this.isPointInSwampPatch(snake.head.x, snake.head.y, patch, 72));
        if (!hitPatch) return;

        const away = Math.atan2(snake.head.y - hitPatch.y, snake.head.x - hitPatch.x);
        snake.head.heading = this.blendHeading(snake.head.heading, away, Math.max(blendAmount, 0.12));
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
        if (this.isSurvivalMode()) return;

        const bounds = this.isSurvivalMode()
            ? this.getFoodBounds()
            : (this.motoMode ? this.worldBounds : { left: 44, top: 138, right: this.width - 44, bottom: this.height - 46 });
        const foodSpeedScale = this.motoMode ? 0.5 : 1;
        const left = bounds.left + 44;
        const right = bounds.right - 44;
        const top = bounds.top + (this.motoMode ? 44 : 0);
        const bottom = bounds.bottom - 46;

        this.foods.forEach((food, index) => {
            const time = this.frame * 0.018 + food.wavePhase;
            const currentX = Math.cos(time * 0.75 + index) * food.waveStrength;
            const currentY = Math.sin(time + index * 1.7) * food.waveStrength;
            food.vx += currentX * delta;
            food.vy += currentY * delta;

            const speed = Math.hypot(food.vx, food.vy) || 1;
            const maxSpeed = 0.675;
            const minSpeed = 0.14;
            if (speed > maxSpeed) {
                food.vx = (food.vx / speed) * maxSpeed;
                food.vy = (food.vy / speed) * maxSpeed;
            } else if (speed < minSpeed) {
                food.vx += (Math.random() - 0.5) * 0.06;
                food.vy += (Math.random() - 0.5) * 0.06;
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
                const pond = this.getLotusPondShape(food.radius + 48);
                const angleToCenter = Math.atan2(pond.cy - food.y, pond.cx - food.x);
                food.x += Math.cos(angleToCenter) * 24;
                food.y += Math.sin(angleToCenter) * 24;
                food.vx = Math.cos(angleToCenter) * Math.abs(food.vx || 0.24);
                food.vy = Math.sin(angleToCenter) * Math.abs(food.vy || 0.24);
            }
        });
    }

    isFoodCorrect(food) {
        if (this.isSurvivalMode()) return true;
        return food.item.word === this.currentItem.word && food.type === this.getTargetType();
    }

    resolveSwampLandCollision() {
        if (!this.isSurvivalMode()) return;

        const padding = this.getSnakeThickness() * 0.45;
        if (!this.isPointOnSwampLand(this.head.x, this.head.y, padding)) return;

        let bestAngle = this.head.heading + Math.PI;
        let bestDepth = 0;
        const pond = this.getLotusPondShape(padding);
        const nx = (this.head.x - pond.cx) / pond.rx;
        const ny = (this.head.y - pond.cy) / pond.ry;
        if (nx * nx + ny * ny > 1) {
            bestAngle = Math.atan2(pond.cy - this.head.y, pond.cx - this.head.x);
            bestDepth = 999;
        }

        this.swampPatches.forEach(patch => {
            if (!this.isPointInSwampPatch(this.head.x, this.head.y, patch, padding)) return;
            const angle = Math.atan2(this.head.y - patch.y, this.head.x - patch.x);
            const depth = Math.hypot(this.head.x - patch.x, this.head.y - patch.y);
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

        this.head.heading = this.blendHeading(this.head.heading, bestAngle, 0.32);
        this.head.x += Math.cos(bestAngle) * 8;
        this.head.y += Math.sin(bestAngle) * 8;
        this.poisonTimer = Math.max(this.poisonTimer, 12);
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
        if (!this.autoSnakeEnabled || !this.autoSnake || !this.autoSnake.active) return;

        for (let index = this.foods.length - 1; index >= 0; index--) {
            const food = this.foods[index];
            const distance = Math.hypot(food.x - this.autoSnake.head.x, food.y - this.autoSnake.head.y);
            if (distance > food.radius + 22) continue;

            this.autoSnake.segments++;
            this.autoSnakeGrowthTimer = 35;
            this.fishFrenzyTimer = Math.max(this.fishFrenzyTimer, 55);
            this.addParticles(food.x, food.y, this.autoSnake.colors?.particle || '#f97316', 16);
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

    checkInterSnakeCollisions() {
        if (!this.autoSnakeEnabled || !this.autoSnake || !this.autoSnake.active) return;

        const playerThickness = this.getSnakeThickness();
        const autoThickness = this.getAutoSnakeThickness();
        const headDistance = Math.hypot(this.head.x - this.autoSnake.head.x, this.head.y - this.autoSnake.head.y);
        if (headDistance < (playerThickness + autoThickness) * 0.72) {
            this.autoSnake.active = false;
            this.autoSnakeEnabled = false;
            this.updateAutoSnakeButton();
            this.addParticles(this.head.x, this.head.y, '#f97316', 28);
            this.endGame('HEAD CRASH!');
            return;
        }

        if (this.isPointNearAutoSnakeBody(this.head.x, this.head.y, playerThickness * 0.78)) {
            this.autoSnake.active = false;
            this.autoSnakeEnabled = false;
            this.updateAutoSnakeButton();
            this.endGame('RIVAL BITE!');
            return;
        }

        if (this.isPointNearPlayerBody(this.autoSnake.head.x, this.autoSnake.head.y, autoThickness * 0.78)) {
            this.defeatAutoSnake('AUTO SNAKE DOWN');
        }
    }

    checkAutoSnakeSelfCollision() {
        if (!this.autoSnakeEnabled || !this.autoSnake || !this.autoSnake.active || this.autoSnake.segments < 3) return;
        if (this.autoSnake.bodyBiteCooldown > 0) return;

        const biteRadius = this.getAutoSnakeThickness() * 0.92;
        if (this.isPointNearAutoSnakeBody(this.autoSnake.head.x, this.autoSnake.head.y, biteRadius, 88)) {
            this.autoSnake.bodyBiteCooldown = 90;
            this.defeatAutoSnake('AUTO BIT TAIL');
        }
    }

    isPointNearAutoSnakeBody(x, y, radius, safeHeadDistance = 78) {
        if (!this.autoSnake) return false;

        const bodyLength = this.getAutoSnakeBodyLength();
        for (let distance = safeHeadDistance; distance <= bodyLength; distance += 12) {
            const point = this.getAutoPointAtDistance(distance);
            if (Math.hypot(point.x - x, point.y - y) < radius) return true;
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

    defeatAutoSnake(message) {
        if (!this.autoSnake) return;

        const colors = this.autoSnake.colors || AUTO_SNAKE_COLORS[0];
        this.addParticles(this.autoSnake.head.x, this.autoSnake.head.y, colors.particle, 32);
        this.meaningPopups.push({
            x: this.autoSnake.head.x,
            y: this.autoSnake.head.y - 38,
            text: message,
            life: 90,
            maxLife: 90,
            bonus: true
        });
        this.autoSnake.active = false;
        this.autoSnake = null;
        this.autoSnakeRespawnTimer = 95;
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

        window.speechSynthesis.cancel();

        order.forEach((type, index) => {
            const utterance = new SpeechSynthesisUtterance(type === 'vi' ? item.meaning : item.word);
            utterance.lang = type === 'vi' ? 'vi-VN' : 'en-US';
            utterance.rate = type === 'vi' ? 0.9 : 0.95;
            utterance.pitch = 1.05;
            const voices = window.speechSynthesis.getVoices();
            const voice = voices.find(v => (v.lang || '').toLowerCase().startsWith(type === 'vi' ? 'vi' : 'en'));
            if (voice) utterance.voice = voice;

            setTimeout(() => {
                if (this.state === 'playing' && this.speechEnabled && !this.fx.muted) {
                    window.speechSynthesis.speak(utterance);
                }
            }, index * 850);
        });
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
        this.autoSnakeEnabled = false;
        this.autoSnake = null;
        this.updateAutoSnakeButton();
        document.body.classList.remove('snake-mode');
        document.body.classList.remove('swamp-mode');
        this.screenGame.classList.remove('active');
        this.screenStart.classList.add('active');
        this.modalPause.classList.add('hidden');
        this.modalGameOver.classList.add('hidden');
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        this.updateStartHighScore();
        this.renderStartPlayHistory();
    }

    endGame(title, won = false) {
        if (this.state !== 'playing') return;
        this.state = 'gameover';
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
            ? 'LOTUS POND'
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
        this.drawSnake();
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

        this.drawSwampTerrain();
    }

    drawSwampTerrain() {
        if (!this.isSurvivalMode()) return;

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
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate(patch.rot);

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
            ctx.beginPath();
            ctx.ellipse(0, 0, patch.rx, patch.ry, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();
        });

        this.lotusFlowers.forEach((flower, index) => {
            const p = this.worldToScreen(flower);
            const size = flower.radius;
            const bonusPulse = Math.max(0, Math.min(1, this.lotusBonusTimer / 90));
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate(flower.rot + Math.sin(this.frame * 0.018 + index) * 0.04);

            ctx.fillStyle = bonusPulse > 0 ? `rgba(253, 224, 71, ${0.16 + bonusPulse * 0.18})` : 'rgba(255, 229, 239, 0.2)';
            ctx.beginPath();
            ctx.arc(0, 0, size * (1.05 + bonusPulse * 0.35), 0, Math.PI * 2);
            ctx.fill();

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

        for (let school = 0; school < 4; school++) {
            const direction = school % 2 === 0 ? 1 : -1;
            const schoolY = pondCenter.y - pond.ry * 0.35 + school * pond.ry * 0.22;
            const speed = (18 + school * 5) * (1 + frenzy * 0.45);
            for (let fish = 0; fish < 9; fish++) {
                const swimWidth = pond.rx * 2.15;
                const offset = (time * speed + fish * 34 + school * 137) % swimWidth;
                const px = direction > 0
                    ? pondCenter.x - pond.rx * 1.08 + offset
                    : pondCenter.x + pond.rx * 1.08 - offset;
                const py = schoolY + Math.sin(time * (1.6 + frenzy * 0.25) + fish * 0.8 + school) * (16 + frenzy * 3) + (fish % 3) * 7;
                const scale = 0.72 + (fish % 3) * 0.16;

                ctx.save();
                ctx.translate(px, py);
                ctx.rotate((direction > 0 ? 0 : Math.PI) + Math.sin(time * 2 + fish) * 0.06);
                ctx.globalAlpha = 0.2 + frenzy * 0.08;
                ctx.fillStyle = school % 2 === 0 ? '#f6d365' : '#9be7ff';
                ctx.beginPath();
                ctx.ellipse(0, 0, 9 * scale, 4 * scale, 0, 0, Math.PI * 2);
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(-8 * scale, 0);
                ctx.lineTo(-15 * scale, -5 * scale);
                ctx.lineTo(-15 * scale, 5 * scale);
                ctx.closePath();
                ctx.fill();
                ctx.restore();
            }
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
        if (!this.isSurvivalMode() || this.trail.length < 3) return;

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
        if (!this.autoSnakeEnabled || !this.autoSnake || !this.autoSnake.active) return;

        const ctx = this.ctx;
        const bodyLength = this.getAutoSnakeBodyLength();
        const sampleSpacing = 14;
        const worldPositions = [];
        for (let distance = 0; distance <= bodyLength; distance += sampleSpacing) {
            worldPositions.push(this.getAutoPointAtDistance(distance));
        }
        const positions = worldPositions.map(point => this.worldToScreen(point));
        if (positions.length < 2) return;

        const thickness = this.getAutoSnakeThickness();
        const colors = this.autoSnake.colors || AUTO_SNAKE_COLORS[0];
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

        this.drawAutoSnakeHead(positions[0]);
    }

    drawAutoSnakeHead(position) {
        if (!this.autoSnake) return;

        const ctx = this.ctx;
        const radius = this.getAutoSnakeThickness() * 1.14;
        const angle = this.autoSnake.head.heading;
        const pulse = this.autoSnakeGrowthTimer > 0 ? 1 + Math.sin(this.autoSnakeGrowthTimer * 0.28) * 0.05 : 1;
        const colors = this.autoSnake.colors || AUTO_SNAKE_COLORS[0];

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

    getAutoSnakeBodyLength() {
        if (!this.autoSnake) return 0;
        return 100 + Math.max(0, this.autoSnake.segments - 1) * 68;
    }

    getAutoSnakeThickness() {
        if (!this.autoSnake) return 18;
        const base = 19 + Math.min(12, Math.max(0, this.autoSnake.segments - 1) * 0.85);
        const growthPulse = this.autoSnakeGrowthTimer > 0 ? Math.sin(this.autoSnakeGrowthTimer * 0.28) * 3 : 0;
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

    getAutoPointAtDistance(targetDistance) {
        if (!this.autoSnake) return { x: this.head.x, y: this.head.y };
        if (targetDistance <= 0 || this.autoSnake.trail.length < 2) {
            return { x: this.autoSnake.head.x, y: this.autoSnake.head.y };
        }

        let walked = 0;
        for (let index = 1; index < this.autoSnake.trail.length; index++) {
            const prev = this.autoSnake.trail[index - 1];
            const next = this.autoSnake.trail[index];
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

        return this.autoSnake.trail[this.autoSnake.trail.length - 1] || this.autoSnake.head;
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
        const bobX = this.isSurvivalMode() ? 0 : Math.cos(food.pulse * 0.7 + food.wavePhase) * 5;
        const bobY = this.isSurvivalMode() ? 0 : Math.sin(food.pulse + food.wavePhase) * 7;
        const screenFood = this.worldToScreen(food);
        const drawX = screenFood.x + bobX;
        const drawY = screenFood.y + bobY;

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
