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
const SPEED_BOOST_DURATION_SECONDS = 3;
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
    }
};

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
        try {
            const response = await fetch('vocab.json');
            if (response.ok) {
                const data = await response.json();
                this.vocab = data.filter(item => item.word && item.meaning);
            }
        } catch (error) {
            console.warn('Using fallback vocabulary because vocab.json could not be loaded.', error);
        }

        this.state = 'start';
        this.updateStartHighScore();
        this.renderStartPlayHistory();
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

        document.getElementById('btn-play').addEventListener('click', () => {
            this.fx.init();
            this.startGame();
        });
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

        document.getElementById('btn-meaning-audio').addEventListener('click', () => {
            this.fx.init();
            this.speakCurrentTarget('vi');
        });

        document.getElementById('btn-word-audio').addEventListener('click', () => {
            this.fx.init();
            this.speakCurrentTarget('en');
        });

        const hintButton = document.getElementById('btn-hint-toggle');
        hintButton.addEventListener('click', () => {
            this.hintEnabled = !this.hintEnabled;
            hintButton.classList.toggle('active', this.hintEnabled);
            hintButton.title = this.hintEnabled ? 'Hint is on' : 'Hint is off';
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

    setMotoMode(enabled) {
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

    configureWorldBounds() {
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
        this.screenStart.classList.remove('active');
        this.screenGame.classList.add('active');
        this.modalPause.classList.add('hidden');
        this.modalGameOver.classList.add('hidden');
        this.bossHud.classList.add('hidden');

        this.config = MODE_CONFIG[this.mode] || MODE_CONFIG['vi-en'];
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

        this.spawnFoods();
        this.selectRandomTargetFromFoods();
        this.updateHUD();
        this.state = 'playing';
        this.speakPair(this.currentItem, this.currentPromptType);
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
        if (this.mode === 'en-vi') return 'vi';
        return 'en';
    }

    getPromptTypeForMode() {
        if (this.mode === 'en-vi') return 'en';
        if (this.mode === 'mixed') return 'en';
        return 'vi';
    }

    spawnFoods() {
        const targetType = this.getTargetType();
        this.foods = this.shuffle(this.vocab)
            .slice(0, 4)
            .map((item, index) => this.createFood(item, targetType, index));
        this.foods.forEach((food) => this.placeFood(food));
    }

    createFood(item, type, index = 0) {
        const angle = Math.random() * Math.PI * 2;
        const driftSpeed = (0.35 + Math.random() * 0.75) * 0.5;

        return {
            item,
            type,
            label: this.getLabel(item, type),
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

        return this.foods.some(other => (
            other !== food &&
            other.x &&
            Math.hypot(food.x - other.x, food.y - other.y) < 150
        ));
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

        this.updateSnake(deltaSeconds, delta);
        this.updateFoods(delta);
        this.updateParticles(delta);
        this.checkBoundaryCollision();
        this.checkSelfCollision();
        this.checkFoodCollisions();
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
        } else {
            this.head.x = Math.max(28, Math.min(this.width - 28, this.head.x));
            this.head.y = Math.max(120, Math.min(this.height - 32, this.head.y));
        }

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
        const bounds = this.motoMode ? this.worldBounds : { left: 44, top: 138, right: this.width - 44, bottom: this.height - 46 };
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
        });
    }

    isFoodCorrect(food) {
        return food.item.word === this.currentItem.word && food.type === this.getTargetType();
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
        this.foods.splice(index, 1);
        this.nextChallenge();
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
        this.selectRandomTargetFromFoods();
        this.addRandomFood();
        this.speakPair(this.currentItem, this.currentPromptType);
    }

    replayPromptAudioIfNeeded() {
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

    speakCurrentTarget(type) {
        this.lastPromptSpeechFrame = this.frame;
        this.lastPromptSpeechTimeMs = performance.now();
        this.lastPromptSpeechGameSecond = this.elapsedGameSeconds;
        this.speakTypes(this.currentItem, [type]);
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
        document.body.classList.remove('snake-mode');
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

        this.targetValue.innerText = this.mode === 'mixed'
            ? '🔊 LISTEN'
            : this.getLabel(this.currentItem || this.vocab[0], this.currentPromptType);
    }

    trySpeedBoost() {
        if (this.state !== 'playing' || this.elapsedGameSeconds < this.nextSpeedBoostAt) return;

        this.speedMultiplier = SPEED_BOOST_MULTIPLIER;
        this.speedBoostUntil = this.elapsedGameSeconds + SPEED_BOOST_DURATION_SECONDS;
        this.nextSpeedBoostAt = this.elapsedGameSeconds + SPEED_BOOST_COOLDOWN_SECONDS;
        this.speedBoostFlash = 50;
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
        document.querySelector('.gameover-subtitle').innerText = won
            ? 'You survived the full 5-minute word swim!'
            : (title === 'POISONED!' ? 'The snake ate the wrong food three times.' : 'The snake bit its own tail.');
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

    draw() {
        this.drawBackground();

        if (this.state === 'start' || this.state === 'loading') {
            return;
        }

        this.drawWorldBoundary();
        this.foods.forEach(food => this.drawFood(food));
        this.drawSnake();
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
        gradient.addColorStop(0, '#173d6f');
        gradient.addColorStop(0.55, '#071a31');
        gradient.addColorStop(1, '#020711');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, this.width, this.height);

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
    }

    drawWorldBoundary() {
        if (!this.motoMode) return;

        const ctx = this.ctx;
        const camera = this.getCamera();
        const bounds = this.worldBounds;
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

    getSnakeBodyLength() {
        return 100 + Math.max(0, this.segments.length - 1) * 68;
    }

    getSnakeThickness() {
        const base = 21 + Math.min(13, Math.max(0, this.segments.length - 1) * 0.85);
        const growthPulse = this.growthTimer > 0 ? Math.sin(this.growthTimer * 0.28) * 3 : 0;
        const poisonShrink = this.poisonTimer > 0 ? 5 : 0;
        return Math.max(18, base + growthPulse - poisonShrink);
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
        const radius = food.radius + Math.sin(food.pulse) * 3;
        const bobX = Math.cos(food.pulse * 0.7 + food.wavePhase) * 5;
        const bobY = Math.sin(food.pulse + food.wavePhase) * 7;
        const screenFood = this.worldToScreen(food);
        const drawX = screenFood.x + bobX;
        const drawY = screenFood.y + bobY;

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

        ctx.save();
        ctx.shadowColor = showHint ? '#00ff88' : food.color;
        ctx.shadowBlur = showHint ? 20 : 12;
        ctx.fillStyle = showHint ? 'rgba(0, 255, 136, 0.92)' : 'rgba(15, 23, 42, 0.9)';
        ctx.strokeStyle = showHint ? '#00ff88' : food.color;
        ctx.lineWidth = showHint ? 4 : 2;
        ctx.beginPath();
        ctx.arc(drawX, drawY, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.save();
        ctx.globalAlpha = 0.32;
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(drawX - radius * 0.28, drawY - radius * 0.32, radius * 0.24, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        ctx.font = `bold ${Math.round(radius * 1.12)}px ${this.fontHeading()}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(food.item.emoji || '●', drawX, drawY + 1);
        if (food.type === 'en') {
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
        const boxX = Math.max(12, Math.min(this.width - measuredWidth - 12, x - measuredWidth / 2));
        const boxY = Math.max(96, y - height / 2);

        ctx.fillStyle = highlight ? 'rgba(0, 255, 136, 0.18)' : 'rgba(5, 13, 24, 0.86)';
        ctx.strokeStyle = highlight ? '#00ff88' : 'rgba(255,255,255,0.18)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(boxX, boxY, measuredWidth, height, 12);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
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
        const flashProgress = this.speedBoostFlash > 0 ? 1 - (this.speedBoostFlash / 50) : 1;
        const boostStrength = Math.min(1, (this.speedMultiplier - 1) / (SPEED_BOOST_MULTIPLIER - 1));
        const streakCount = 5 + Math.round(boostStrength * 8);
        const backAngle = this.head.heading + Math.PI;
        const sideAngle = this.head.heading + Math.PI / 2;

        ctx.save();
        ctx.globalCompositeOperation = 'lighter';

        if (this.speedBoostFlash > 0) {
            ctx.globalAlpha = Math.max(0, 0.55 * (1 - flashProgress));
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 4;
            ctx.shadowColor = '#38bdf8';
            ctx.shadowBlur = 22;
            ctx.beginPath();
            ctx.arc(head.x, head.y, 32 + flashProgress * 64, 0, Math.PI * 2);
            ctx.stroke();
        }

        for (let index = 0; index < streakCount; index++) {
            const sideOffset = (index - (streakCount - 1) / 2) * 9;
            const startDistance = 28 + index * 5;
            const length = 55 + this.speedMultiplier * 28 + index * 4;
            const startX = head.x + Math.cos(backAngle) * startDistance + Math.cos(sideAngle) * sideOffset;
            const startY = head.y + Math.sin(backAngle) * startDistance + Math.sin(sideAngle) * sideOffset;
            const endX = head.x + Math.cos(backAngle) * (startDistance + length) + Math.cos(sideAngle) * sideOffset;
            const endY = head.y + Math.sin(backAngle) * (startDistance + length) + Math.sin(sideAngle) * sideOffset;

            ctx.globalAlpha = 0.16 + boostStrength * 0.22;
            ctx.strokeStyle = index % 2 === 0 ? '#38bdf8' : '#00ff88';
            ctx.lineWidth = 2 + boostStrength * 3;
            ctx.shadowColor = ctx.strokeStyle;
            ctx.shadowBlur = 16;
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.lineTo(endX, endY);
            ctx.stroke();
        }

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
        return `${prefix}_word_snake_${this.mode}`;
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
