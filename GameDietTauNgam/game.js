/**
 * Word Submarine Hunter
 * A complete, polished, educational action arcade game.
 * Uses HTML5 Canvas, Web Audio API synthesis, and Spaced Repetition adaptive learning.
 */

// ==========================================================================
// 1. SOUND MANAGER (Web Audio API Synthesizer)
// ==========================================================================
class SoundSynth {
    constructor() {
        this.ctx = null;
        this.muted = false;
        this.savedState = false;
    }

    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    playShoot() {
        if (this.muted || !this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(150, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(60, this.ctx.currentTime + 0.15);

        gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.15);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.15);
    }

    playReload() {
        if (this.muted || !this.ctx) return;
        const now = this.ctx.currentTime;
        const notes = [180, 260, 360];

        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);

            const start = now + idx * 0.09;
            osc.type = 'square';
            osc.frequency.setValueAtTime(freq, start);
            osc.frequency.exponentialRampToValueAtTime(freq * 1.35, start + 0.08);

            gain.gain.setValueAtTime(0.08, start);
            gain.gain.exponentialRampToValueAtTime(0.01, start + 0.11);

            osc.start(start);
            osc.stop(start + 0.11);
        });
    }

    playExplosion() {
        if (this.muted || !this.ctx) return;
        const bufferSize = this.ctx.sampleRate * 0.4;
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        
        // Fill buffer with random noise
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.ctx.createBufferSource();
        noise.buffer = buffer;

        const filter = this.ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(800, this.ctx.currentTime);
        filter.frequency.exponentialRampToValueAtTime(50, this.ctx.currentTime + 0.4);

        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.4);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(this.ctx.destination);

        noise.start();
        noise.stop(this.ctx.currentTime + 0.4);
    }

    playSubmarineSinking() {
        if (this.muted || !this.ctx) return;
        const now = this.ctx.currentTime;

        const rumble = this.ctx.createOscillator();
        const rumbleGain = this.ctx.createGain();
        rumble.connect(rumbleGain);
        rumbleGain.connect(this.ctx.destination);
        rumble.type = 'sawtooth';
        rumble.frequency.setValueAtTime(120, now);
        rumble.frequency.exponentialRampToValueAtTime(32, now + 0.75);
        rumbleGain.gain.setValueAtTime(0.22, now);
        rumbleGain.gain.exponentialRampToValueAtTime(0.01, now + 0.8);
        rumble.start(now);
        rumble.stop(now + 0.8);

        const bufferSize = this.ctx.sampleRate * 0.55;
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
        }

        const noise = this.ctx.createBufferSource();
        const filter = this.ctx.createBiquadFilter();
        const noiseGain = this.ctx.createGain();
        noise.buffer = buffer;
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(500, now);
        filter.frequency.exponentialRampToValueAtTime(90, now + 0.55);
        noiseGain.gain.setValueAtTime(0.18, now);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.55);
        noise.connect(filter);
        filter.connect(noiseGain);
        noiseGain.connect(this.ctx.destination);
        noise.start(now);
        noise.stop(now + 0.55);
    }

    playSplash() {
        if (this.muted || !this.ctx) return;
        // High frequency soft splash
        const bufferSize = this.ctx.sampleRate * 0.25;
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.ctx.createBufferSource();
        noise.buffer = buffer;

        const filter = this.ctx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(2000, this.ctx.currentTime);
        filter.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.25);

        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.25);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(this.ctx.destination);

        noise.start();
        noise.stop(this.ctx.currentTime + 0.25);
    }

    playAlarm() {
        if (this.muted || !this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, this.ctx.currentTime);
        osc.frequency.setValueAtTime(950, this.ctx.currentTime + 0.15);

        gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
        gain.gain.setValueAtTime(0.01, this.ctx.currentTime + 0.28);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.3);
    }

    playLaser() {
        if (this.muted || !this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(2000, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.4);

        gain.gain.setValueAtTime(0.05, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.4);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.4);
    }

    playPowerup() {
        if (this.muted || !this.ctx) return;
        const now = this.ctx.currentTime;
        const notes = [261.63, 329.63, 392.00, 523.25]; // C4, E4, G4, C5
        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);

            gain.gain.setValueAtTime(0.15, now + idx * 0.08);
            gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.08 + 0.15);

            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 0.15);
        });
    }

    playDamage() {
        if (this.muted || !this.ctx) return;
        // Low rumble distortion
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(90, this.ctx.currentTime);
        osc.frequency.linearRampToValueAtTime(30, this.ctx.currentTime + 0.3);

        gain.gain.setValueAtTime(0.25, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.3);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.3);
    }

    playVictory() {
        if (this.muted || !this.ctx) return;
        const now = this.ctx.currentTime;
        const melody = [523.25, 587.33, 659.25, 783.99, 880.00, 1046.50]; // C5, D5, E5, G5, A5, C6
        melody.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.type = 'triangle';
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);

            gain.gain.setValueAtTime(0.15, now + idx * 0.08);
            gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.08 + 0.2);

            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 0.2);
        });
    }

    playDefeat() {
        if (this.muted || !this.ctx) return;
        const now = this.ctx.currentTime;
        const melody = [440.00, 415.30, 392.00, 349.23, 293.66]; // A4, Ab4, G4, F4, D4
        melody.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(freq, now + idx * 0.12);

            gain.gain.setValueAtTime(0.15, now + idx * 0.12);
            gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.12 + 0.25);

            osc.start(now + idx * 0.12);
            osc.stop(now + idx * 0.12 + 0.25);
        });
    }

    toggleMute() {
        this.muted = !this.muted;
        return this.muted;
    }
}

// Global Sound Instance
const sound = new SoundSynth();


// ==========================================================================
// 2. ADAPTIVE LEARNING SYSTEM (Spaced Repetition Vocab)
// ==========================================================================
class VocabularyPool {
    constructor() {
        this.words = [];
        this.learningState = {}; // { word: { correct, incorrect, selected, lastSeenAt, weight } }
        this.correctMatches = 0;
        this.incorrectMatches = 0;
        this.grade = 4;
        this.sourceLabel = 'Global Success Grade 4';
        this.selectionSequence = 0;
    }

    async loadVocab(source = 4) {
        const selectedSource = this.normalizeSource(source);
        const defaultList = [
            { "word": "Dog", "meaning": "Con chó", "emoji": "🐶" },
            { "word": "Cat", "meaning": "Con mèo", "emoji": "🐱" },
            { "word": "Fish", "meaning": "Con cá", "emoji": "🐟" },
            { "word": "Apple", "meaning": "Quả táo", "emoji": "🍎" },
            { "word": "Banana", "meaning": "Quả chuối", "emoji": "🍌" },
            { "word": "Orange", "meaning": "Quả cam", "emoji": "🍊" },
            { "word": "Bird", "meaning": "Con chim", "emoji": "🐦" },
            { "word": "Lion", "meaning": "Sư tử", "emoji": "🦁" },
            { "word": "Elephant", "meaning": "Con voi", "emoji": "🐘" },
            { "word": "Monkey", "meaning": "Con khỉ", "emoji": "🐒" },
            { "word": "Car", "meaning": "Xe ô tô", "emoji": "🚗" },
            { "word": "Bicycle", "meaning": "Xe đạp", "emoji": "🚲" },
            { "word": "Airplane", "meaning": "Máy bay", "emoji": "✈️" },
            { "word": "Boat", "meaning": "Thuyền", "emoji": "⛵" },
            { "word": "Sun", "meaning": "Mặt trời", "emoji": "☀️" },
            { "word": "Moon", "meaning": "Mặt trăng", "emoji": "🌙" },
            { "word": "Star", "meaning": "Ngôi sao", "emoji": "⭐" },
            { "word": "Rain", "meaning": "Mưa", "emoji": "🌧️" },
            { "word": "Snow", "meaning": "Tuyết", "emoji": "❄️" },
            { "word": "Tree", "meaning": "Cái cây", "emoji": "🌳" },
            { "word": "Flower", "meaning": "Bông hoa", "emoji": "🌸" },
            { "word": "House", "meaning": "Ngôi nhà", "emoji": "🏠" },
            { "word": "Book", "meaning": "Quyển sách", "emoji": "📖" },
            { "word": "Pen", "meaning": "Bút mực", "emoji": "🖋️" },
            { "word": "Pencil", "meaning": "Bút chì", "emoji": "✏️" },
            { "word": "School", "meaning": "Trường học", "emoji": "🏫" },
            { "word": "Teacher", "meaning": "Giáo viên", "emoji": "👩‍🏫" },
            { "word": "Doctor", "meaning": "Bác sĩ", "emoji": "👨‍⚕️" },
            { "word": "Run", "meaning": "Chạy", "emoji": "🏃" },
            { "word": "Jump", "meaning": "Nhảy", "emoji": "🤾" },
            { "word": "Swim", "meaning": "Bơi", "emoji": "🏊" },
            { "word": "Sing", "meaning": "Hát", "emoji": "🎤" },
            { "word": "Dance", "meaning": "Nhảy múa", "emoji": "💃" },
            { "word": "Red", "meaning": "Màu đỏ", "emoji": "🟥" },
            { "word": "Blue", "meaning": "Màu xanh dương", "emoji": "🟦" },
            { "word": "Green", "meaning": "Màu xanh lá", "emoji": "🟩" },
            { "word": "Yellow", "meaning": "Màu vàng", "emoji": "🟨" }
        ];

        try {
            // Load Global Success grade data with a timeout to fall back cleanly if file loading errors out.
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), 1500);

            const vocabPath = selectedSource === 'toeic'
                ? 'global-success-vocabulary/toeic.json'
                : `global-success-vocabulary/grade${selectedSource}.json`;
            const response = await fetch(vocabPath, { signal: controller.signal });
            clearTimeout(id);

            if (response.ok) {
                const loadedWords = await response.json();
                this.words = this.normalizeWordList(loadedWords);
                this.grade = selectedSource;
                this.sourceLabel = this.getSourceLabel(selectedSource);
                console.log(`Successfully loaded vocabulary list from ${vocabPath}.`);
            } else {
                this.words = this.normalizeWordList(defaultList);
                this.grade = selectedSource;
                this.sourceLabel = this.getSourceLabel(selectedSource);
                console.warn(`Failed to load ${this.sourceLabel} vocabulary. Falling back to default list.`);
            }
        } catch (e) {
            this.words = this.normalizeWordList(defaultList);
            this.grade = selectedSource;
            this.sourceLabel = this.getSourceLabel(selectedSource);
            console.warn(`Local CORS blocking or network error: using default built-in vocabulary list for ${this.sourceLabel}.`);
        }

        // Initialize learning states
        this.learningState = {};
        const persistedStats = this.loadPersistedStats();
        this.words.forEach(item => {
            const key = item.word.toLowerCase();
            const stored = persistedStats[key] || {};
            this.learningState[key] = {
                item: item,
                correct: Number(stored.correct) || 0,
                incorrect: Number(stored.incorrect) || 0,
                selected: Number(stored.selected) || 0,
                lastSeenAt: Number(stored.lastSeenAt) || 0,
                weight: 1.0
            };
            this.learningState[key].weight = this.calculateWeight(this.learningState[key]);
        });
    }

    normalizeSource(source) {
        if (String(source).toLowerCase() === 'toeic') return 'toeic';
        return Math.min(12, Math.max(1, Number.parseInt(source, 10) || 4));
    }

    getSourceLabel(source = this.grade) {
        return source === 'toeic' ? 'TOEIC' : `Global Success Grade ${source}`;
    }

    getSourceShortLabel(source = this.grade) {
        return source === 'toeic' ? 'TOEIC' : `G${source}`;
    }

    normalizeWordList(words) {
        return words
            .filter(item => item && item.word && item.meaning)
            .map(item => ({
                word: String(item.word).trim(),
                meaning: String(item.meaning).trim(),
                emoji: item.emoji || '🔹',
                topic: item.topic || 'Từ vựng'
            }));
    }

    getStatsStorageKey() {
        return this.grade === 'toeic' ? 'vocab_stats_toeic' : `vocab_stats_grade_${this.grade}`;
    }

    loadPersistedStats() {
        try {
            const parsed = JSON.parse(localStorage.getItem(this.getStatsStorageKey()) || '{}');
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (e) {
            return {};
        }
    }

    savePersistedStats() {
        const stats = {};
        Object.entries(this.learningState).forEach(([key, state]) => {
            stats[key] = {
                correct: state.correct,
                incorrect: state.incorrect,
                selected: state.selected,
                lastSeenAt: state.lastSeenAt
            };
        });
        try {
            localStorage.setItem(this.getStatsStorageKey(), JSON.stringify(stats));
        } catch (e) {
            console.warn('Unable to save vocabulary learning stats.', e);
        }
    }

    clearPersistedStats() {
        try {
            localStorage.removeItem(this.getStatsStorageKey());
        } catch (e) {
            console.warn('Unable to clear vocabulary learning stats.', e);
        }

        Object.values(this.learningState).forEach(state => {
            state.correct = 0;
            state.incorrect = 0;
            state.selected = 0;
            state.lastSeenAt = 0;
            state.weight = this.calculateWeight(state);
        });
        this.correctMatches = 0;
        this.incorrectMatches = 0;
        this.selectionSequence = 0;
    }

    calculateWeight(state) {
        // Prioritize words that have never/rarely appeared, then words often answered incorrectly.
        const selected = Number(state.selected) || 0;
        const correct = Number(state.correct) || 0;
        const incorrect = Number(state.incorrect) || 0;
        const attempts = correct + incorrect;
        const errorRate = attempts > 0 ? incorrect / attempts : 0;
        const unseenBoost = selected === 0 ? 12 : 0;
        const rarityBoost = 8 / Math.sqrt(selected + 1);
        const mistakeBoost = incorrect * 2.5 + errorRate * 4;
        const masteryPenalty = Math.min(correct * 0.35, 4);
        return Math.max(0.2, unseenBoost + rarityBoost + mistakeBoost - masteryPenalty);
    }

    markTargetSelected(item) {
        const key = item.word.toLowerCase();
        const state = this.learningState[key];
        if (!state) return item;

        state.selected++;
        state.lastSeenAt = ++this.selectionSequence;
        state.weight = this.calculateWeight(state);
        this.savePersistedStats();
        return item;
    }

    recordResult(wordText, isCorrect) {
        const key = wordText.toLowerCase();
        if (!this.learningState[key]) return;
        
        const state = this.learningState[key];
        if (isCorrect) {
            state.correct++;
            this.correctMatches++;
        } else {
            state.incorrect++;
            this.incorrectMatches++;
        }

        state.weight = this.calculateWeight(state);
        this.savePersistedStats();
    }

    getAccuracy() {
        const total = this.correctMatches + this.incorrectMatches;
        if (total === 0) return 100;
        return Math.round((this.correctMatches / total) * 100);
    }

    pickNextTarget() {
        if (this.words.length === 0) return null;

        const unseenWords = this.words.filter(item => {
            const state = this.learningState[item.word.toLowerCase()];
            return !state || state.selected === 0;
        });
        if (unseenWords.length > 0) {
            const picked = unseenWords[Math.floor(Math.random() * unseenWords.length)];
            return this.markTargetSelected(picked);
        }

        // Weighted selection: unseen and rarely selected words get large boosts,
        // while frequently missed words stay in rotation until mastered.
        let totalWeight = 0;
        const pool = [];

        this.words.forEach(item => {
            const key = item.word.toLowerCase();
            const state = this.learningState[key];
            const w = state ? this.calculateWeight(state) : 1.0;
            if (state) state.weight = w;
            totalWeight += w;
            pool.push({ item, cumulativeWeight: totalWeight });
        });

        const r = Math.random() * totalWeight;
        for (let i = 0; i < pool.length; i++) {
            if (r <= pool[i].cumulativeWeight) {
                return this.markTargetSelected(pool[i].item);
            }
        }
        return this.markTargetSelected(this.words[Math.floor(Math.random() * this.words.length)]);
    }

    getRandomWrongOptions(correctWordText, count) {
        const wrongPool = this.words.filter(w => w.word.toLowerCase() !== correctWordText.toLowerCase());
        const shuffled = [...wrongPool].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }

    reset() {
        this.correctMatches = 0;
        this.incorrectMatches = 0;
        for (let key in this.learningState) {
            this.learningState[key].weight = this.calculateWeight(this.learningState[key]);
        }
    }
}

// Global Vocab Instance
const vocab = new VocabularyPool();


// ==========================================================================
// 3. PARTICLE SYSTEMS & SHAPES
// ==========================================================================
class Particle {
    constructor(x, y, type, color = '#ff9900', options = {}) {
        this.x = x;
        this.y = y;
        this.type = type; // 'smoke', 'bubble', 'fire', 'splash', 'spark', 'firework', 'wake', 'foam', 'shockwave'
        this.color = color;
        this.life = 1.0;
        this.decay = Math.random() * 0.03 + 0.015;

        switch (type) {
            case 'bubble':
                this.vx = Math.random() * 0.8 - 0.4;
                this.vy = -(Math.random() * 1.5 + 0.5);
                this.size = Math.random() * 4 + 2;
                this.decay = Math.random() * 0.015 + 0.005;
                break;
            case 'smoke':
                this.vx = Math.random() * 0.4 - 0.2;
                this.vy = -(Math.random() * 0.8 + 0.2);
                this.size = Math.random() * 8 + 6;
                break;
            case 'fire':
                const angle = Math.random() * Math.PI * 2;
                const speed = Math.random() * 4 + 1;
                this.vx = Math.cos(angle) * speed;
                this.vy = Math.sin(angle) * speed;
                this.size = Math.random() * 10 + 5;
                this.decay = Math.random() * 0.04 + 0.02;
                break;
            case 'splash':
                this.vx = Math.random() * 3 - 1.5;
                this.vy = -(Math.random() * 4 + 2);
                this.size = Math.random() * 5 + 2;
                this.decay = Math.random() * 0.05 + 0.03;
                break;
            case 'wake':
                const dir = options.dir || 1;
                const intensity = options.intensity || 1;
                this.vx = -dir * (Math.random() * 2.4 + 1.2) * intensity;
                this.vy = -(Math.random() * 1.4 + 0.25) * intensity;
                this.size = (Math.random() * 5 + 4) * intensity;
                this.decay = Math.random() * 0.025 + 0.018;
                this.stretch = (options.stretch || 1) * (Math.random() * 1.8 + 2.6);
                this.gravity = options.gravity ?? 0.025;
                break;
            case 'foam':
                const foamDir = options.dir || 1;
                const foamIntensity = options.intensity || 1;
                this.vx = -foamDir * (Math.random() * 1.4 + 0.6) * foamIntensity;
                this.vy = (Math.random() * 0.4 - 0.2) * foamIntensity;
                this.size = (Math.random() * 8 + 8) * foamIntensity;
                this.decay = Math.random() * 0.018 + 0.012;
                this.stretch = (options.stretch || 1) * (Math.random() * 2.2 + 4.5);
                break;
            case 'shockwave':
                this.vx = 0;
                this.vy = 0;
                this.size = options.size || 18;
                this.maxSize = options.maxSize || 90;
                this.lineWidth = options.lineWidth || 4;
                this.decay = options.decay || 0.045;
                break;
            case 'spark':
                const a = Math.random() * Math.PI * 2;
                const s = Math.random() * 3 + 1;
                this.vx = Math.cos(a) * s;
                this.vy = Math.sin(a) * s;
                this.size = Math.random() * 3 + 1;
                this.decay = Math.random() * 0.06 + 0.03;
                break;
            case 'firework':
                const fAngle = Math.random() * Math.PI * 2;
                const fSpeed = Math.random() * 7 + 3;
                this.vx = Math.cos(fAngle) * fSpeed;
                this.vy = Math.sin(fAngle) * fSpeed;
                this.size = Math.random() * 4 + 2;
                this.decay = Math.random() * 0.025 + 0.01;
                break;
        }
    }

    update() {
        this.x += this.vx;
        this.y += this.vy;
        
        if (this.type === 'bubble') {
            this.vx += Math.sin(this.life * 10) * 0.1; // Wiggle
        } else if (this.type === 'splash' || this.type === 'firework') {
            this.vy += 0.15; // Gravity
        } else if (this.type === 'wake') {
            this.vx *= 0.94;
            this.vy += this.gravity;
        } else if (this.type === 'foam') {
            this.vx *= 0.92;
            this.vy *= 0.92;
        } else if (this.type === 'shockwave') {
            this.size += (this.maxSize - this.size) * 0.18;
        }
        
        this.life -= this.decay;
    }

    draw(ctx) {
        ctx.save();
        ctx.globalAlpha = Math.max(0, this.life);
        ctx.fillStyle = this.color;
        
        if (this.type === 'bubble') {
            ctx.strokeStyle = 'rgba(255,255,255,0.6)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.stroke();
            ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
            ctx.fill();
        } else if (this.type === 'wake' || this.type === 'foam') {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.scale(this.stretch, this.type === 'foam' ? 0.32 : 0.58);
            ctx.beginPath();
            ctx.arc(0, 0, this.size * this.life, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        } else if (this.type === 'shockwave') {
            ctx.strokeStyle = this.color;
            ctx.lineWidth = this.lineWidth * this.life;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.stroke();
        } else {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size * this.life, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();
    }
}

// Floating Score indicators
class FloatingText {
    constructor(x, y, text, color = '#ffdd00', scale = 1.0) {
        this.x = x;
        this.y = y;
        this.text = text;
        this.color = color;
        this.scale = scale;
        this.life = 1.0;
        this.decay = 0.02;
        this.vy = -1.5;
    }

    update() {
        this.y += this.vy;
        this.life -= this.decay;
    }

    draw(ctx) {
        ctx.save();
        ctx.globalAlpha = this.life;
        ctx.fillStyle = this.color;
        ctx.font = `bold ${Math.round(20 * this.scale)}px 'Fredoka', sans-serif`;
        ctx.textAlign = 'center';
        ctx.shadowColor = 'rgba(0,0,0,0.5)';
        ctx.shadowBlur = 6;
        ctx.shadowOffsetY = 2;
        ctx.fillText(this.text, this.x, this.y);
        ctx.restore();
    }
}


// ==========================================================================
// 4. DEPTH CHARGE BOMB
// ==========================================================================
class Bomb {
    constructor(x, y, owner = null) {
        this.x = x;
        this.y = y;
        this.owner = owner;
        this.vy = 2.0; // Falling speed starts slow
        this.radius = 12;
        this.gravity = 0.08;
        this.friction = 0.985;
        this.inWater = false;
        
        this.exploded = false;
        this.explosionRadius = 0;
        this.maxExplosionRadius = 90;
        this.explosionSpeed = 5;
        
        this.waterLine = 0; // Set by game loop
    }

    update(waterY) {
        this.waterLine = waterY;

        if (!this.exploded) {
            // Check if entered water
            if (this.y >= waterY && !this.inWater) {
                this.inWater = true;
                this.vy = 1.5; // Drag slow down
                sound.playSplash();
                return 'splash';
            }

            if (this.inWater) {
                this.vy += this.gravity * 0.6; // slower gravity inside water
                this.vy *= this.friction;
            } else {
                this.vy += this.gravity;
            }

            this.y += this.vy;

            // Trigger explosion at 88% depth of screen
            if (this.y > window.innerHeight * 0.9) {
                this.triggerExplosion();
            }
        } else {
            // Expand explosion circle
            this.explosionRadius += this.explosionSpeed;
            if (this.explosionRadius >= this.maxExplosionRadius) {
                return 'dead';
            }
        }
        return null;
    }

    triggerExplosion() {
        this.exploded = true;
        sound.playExplosion();
    }

    draw(ctx) {
        if (!this.exploded) {
            ctx.save();
            ctx.shadowColor = 'rgba(14, 165, 233, 0.4)';
            ctx.shadowBlur = 6;

            // Torpedo Body (sleek steel/grey cylinder)
            const bodyGrad = ctx.createLinearGradient(this.x - 5, 0, this.x + 5, 0);
            bodyGrad.addColorStop(0, '#64748b');
            bodyGrad.addColorStop(0.5, '#94a3b8');
            bodyGrad.addColorStop(1, '#475569');

            ctx.fillStyle = bodyGrad;
            ctx.strokeStyle = '#0f172a';
            ctx.lineWidth = 1.5;

            // Main cylindrical body
            ctx.beginPath();
            ctx.rect(this.x - 4, this.y - 12, 8, 20);
            ctx.fill();
            ctx.stroke();

            // Nose cone at the bottom (pointing down)
            ctx.fillStyle = '#ef4444'; // Red tip for modern naval look
            ctx.beginPath();
            ctx.arc(this.x, this.y + 8, 4, 0, Math.PI); // half circle pointing down
            ctx.fill();
            ctx.stroke();

            // Tail fins at the top
            ctx.fillStyle = '#334155';
            ctx.beginPath();
            // Left fin
            ctx.moveTo(this.x - 4, this.y - 6);
            ctx.lineTo(this.x - 8, this.y - 12);
            ctx.lineTo(this.x - 4, this.y - 12);
            // Right fin
            ctx.moveTo(this.x + 4, this.y - 6);
            ctx.lineTo(this.x + 8, this.y - 12);
            ctx.lineTo(this.x + 4, this.y - 12);
            // Center fin / cap
            ctx.moveTo(this.x - 2, this.y - 12);
            ctx.lineTo(this.x - 2, this.y - 15);
            ctx.lineTo(this.x + 2, this.y - 15);
            ctx.lineTo(this.x + 2, this.y - 12);
            ctx.fill();
            ctx.stroke();

            // High-tech status LED blinking
            ctx.fillStyle = (Math.floor(Date.now() / 150) % 2 === 0) ? '#22c55e' : '#15803d';
            ctx.beginPath();
            ctx.arc(this.x, this.y - 2, 1.5, 0, Math.PI * 2);
            ctx.fill();

            ctx.restore();
        } else {
            // Draw expanding comic shockwave ring
            ctx.save();
            const ratio = this.explosionRadius / this.maxExplosionRadius;
            
            // Outer glow ring
            const gradient = ctx.createRadialGradient(this.x, this.y, this.explosionRadius * 0.2, this.x, this.y, this.explosionRadius);
            gradient.addColorStop(0, 'rgba(255, 230, 0, 0)');
            gradient.addColorStop(0.5, 'rgba(255, 120, 0, 0.6)');
            gradient.addColorStop(0.9, 'rgba(255, 40, 0, 0.85)');
            gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.explosionRadius, 0, Math.PI * 2);
            ctx.fill();

            // Draw crisp expanding stroke ring
            ctx.strokeStyle = `rgba(255, 255, 255, ${1.0 - ratio})`;
            ctx.lineWidth = 4;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.explosionRadius * 0.95, 0, Math.PI * 2);
            ctx.stroke();

            ctx.restore();
        }
    }
}


// ==========================================================================
// 5. SUPPLY CRATE
// ==========================================================================
class Crate {
    constructor(x, waterY) {
        this.x = x;
        this.y = waterY - 5;
        this.width = 40;
        this.height = 40;
        
        // Pick random powerup type
        const types = ['repair', 'shield', 'freeze', 'emp'];
        this.type = types[Math.floor(Math.random() * types.length)];
        
        this.speedX = Math.random() * 0.6 - 0.3; // drifts slowly
        this.bobOffset = Math.random() * Math.PI * 2;
        this.isCollected = false;
    }

    update(waterY, time) {
        this.x += this.speedX;
        
        // Bobbing on the waves
        const waveBob = Math.sin(time * 0.05 + this.x * 0.02) * 5;
        this.y = waterY - this.height + 15 + waveBob;

        // Keep inside screen boundaries
        if (this.x < 10 || this.x > window.innerWidth - 10) {
            this.speedX = -this.speedX;
        }
    }

    draw(ctx) {
        ctx.save();
        ctx.shadowColor = 'rgba(0,0,0,0.3)';
        ctx.shadowBlur = 6;
        ctx.shadowOffsetY = 4;

        // Crate Box
        ctx.fillStyle = '#b45309'; // Wooden brown
        ctx.strokeStyle = '#78350f';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.roundRect(this.x - this.width/2, this.y, this.width, this.height, 6);
        ctx.fill();
        ctx.stroke();

        // Inner frame wood
        ctx.strokeStyle = '#92400e';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.rect(this.x - this.width/2 + 5, this.y + 5, this.width - 10, this.height - 10);
        ctx.stroke();
        
        // Diagonal cross strut
        ctx.beginPath();
        ctx.moveTo(this.x - this.width/2 + 5, this.y + 5);
        ctx.lineTo(this.x + this.width/2 - 5, this.y + this.height - 5);
        ctx.stroke();

        // Power-up Symbol drawing
        let label = '';
        let color = '#fff';
        switch (this.type) {
            case 'repair':
                label = '❤️';
                color = '#ff3344';
                break;
            case 'shield':
                label = '🛡️';
                color = '#00e1ff';
                break;
            case 'freeze':
                label = '❄️';
                color = '#38bdf8';
                break;
            case 'emp':
                label = '⚡';
                color = '#ffd000';
                break;
        }

        ctx.font = '20px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, this.x, this.y + this.height/2 + 1);

        ctx.restore();
    }
}


// ==========================================================================
// 6. ENEMY SUBMARINE
// ==========================================================================
class Submarine {
    constructor(y, depthIndex, wordObj, speedMultiplier = 1.0, isBoss = false, options = {}) {
        this.y = y;
        this.depthIndex = depthIndex;
        this.word = wordObj; // {word, meaning, emoji}
        this.isBoss = isBoss;
        this.bossLevel = options.bossLevel || 0;
        this.bossStyle = this.getBossStyle(this.bossLevel);
        this.perspectiveScale = this.calculatePerspectiveScale(y, isBoss);

        if (isBoss) {
            this.width = 216 * this.perspectiveScale * this.bossStyle.sizeScale; // 240 * 0.9 = 216
            this.height = 76 * this.perspectiveScale * this.bossStyle.sizeScale; // 85 * 0.9 = 76.5 -> 76
            this.hp = options.hp || 10;
            this.maxHp = this.hp;
            this.speedX = 0.8 * (Math.random() > 0.5 ? 1 : -1);
        } else {
            this.width = 99 * this.perspectiveScale; // 110 * 0.9 = 99
            this.height = 38 * this.perspectiveScale; // 42 * 0.9 = 37.8 -> 38
            this.speedX = (Math.random() * 0.8 + 0.6) * speedMultiplier * (Math.random() > 0.5 ? 1 : -1);
        }

        // Start offscreen
        this.x = this.speedX > 0 ? -this.width : window.innerWidth + this.width;
        this.facingRight = this.speedX > 0;

        this.propellerAngle = 0;
        this.isDying = false;
        this.isWrecked = false;
        this.deathTimer = 0;
        this.deathDuration = isBoss ? 220 : 150;
        this.wreckTargetY = null;
        this.wreckScale = isBoss ? 0.52 : 0.42;
        this.wreckTilt = 0;
        this.damageFlashTimer = 0;
        this.minSpeedX = isBoss ? 0.45 : 0.55;
        
        // Attack related
        this.isWarning = false;
        this.warningTimer = 0;
        this.warningDuration = 60; // 1 second at 60 FPS
        
        // Color variance
        const colors = ['#1e40af', '#065f46', '#111827', '#7c2d12', '#4c1d95'];
        this.subColor = isBoss ? this.bossStyle.hull : colors[depthIndex % colors.length];
    }

    getBossStyle(level) {
        const styles = [
            { hull: '#334155', accent: '#e11d48', glow: 'rgba(225, 29, 72, 0.42)', sizeScale: 1.00 },
            { hull: '#4c1d95', accent: '#f97316', glow: 'rgba(249, 115, 22, 0.48)', sizeScale: 1.08 },
            { hull: '#7f1d1d', accent: '#facc15', glow: 'rgba(250, 204, 21, 0.52)', sizeScale: 1.16 },
            { hull: '#0f766e', accent: '#22d3ee', glow: 'rgba(34, 211, 238, 0.56)', sizeScale: 1.24 },
            { hull: '#111827', accent: '#ec4899', glow: 'rgba(236, 72, 153, 0.65)', sizeScale: 1.34 }
        ];
        return styles[Math.min(styles.length - 1, level)];
    }

    calculatePerspectiveScale(y, isBoss) {
        const minDepth = window.innerHeight * 0.48;
        const maxDepth = window.innerHeight * 0.88;
        const depthRatio = Math.max(0, Math.min(1, (y - minDepth) / (maxDepth - minDepth || 1)));
        const minScale = isBoss ? 0.9 : 0.72;
        const maxScale = isBoss ? 1.12 : 1.28;
        return minScale + depthRatio * (maxScale - minScale);
    }

    normalizeMovementSpeed(speedMultiplier = 1.0) {
        const direction = this.speedX < 0 ? -1 : 1;
        const effectiveMultiplier = Math.max(0.35, speedMultiplier);
        const minSpeed = this.minSpeedX * effectiveMultiplier;

        if (!Number.isFinite(this.speedX) || Math.abs(this.speedX) < minSpeed) {
            this.speedX = minSpeed * direction;
        }
    }

    update(speedMultiplier) {
        if (this.isWrecked) return null;

        if (this.isDying) {
            this.deathTimer++;
            const progress = Math.min(1, this.deathTimer / this.deathDuration);
            this.x += this.speedX * 0.22;
            this.y += 1.2 + progress * 2.8;
            this.speedX *= 0.985;
            this.propellerAngle += Math.max(0.04, Math.abs(this.speedX) * 0.08);

            const seabedY = this.wreckTargetY || (window.innerHeight - this.height * 0.72);
            if (this.y >= seabedY || this.deathTimer > this.deathDuration) {
                const xMargin = this.width * 0.2;
                this.y = seabedY;
                this.x = Math.max(-xMargin, Math.min(window.innerWidth - this.width + xMargin, this.x));
                this.isWrecked = true;
                this.speedX = 0;
                this.propellerAngle = 0;
            }
            return null;
        }

        this.normalizeMovementSpeed(speedMultiplier);
        this.x += this.speedX;

        // Periodic behavior: Randomly change speed slightly or change directions
        if (Math.random() < 0.003 && !this.isBoss) {
            const direction = this.speedX < 0 ? -1 : 1;
            const effectiveMultiplier = Math.max(0.35, speedMultiplier);
            this.speedX = (Math.random() * 0.8 + 0.6) * effectiveMultiplier * direction;
        }
        if (Math.random() < 0.001) {
            this.speedX = -this.speedX;
        }
        this.normalizeMovementSpeed(speedMultiplier);
        this.facingRight = this.speedX > 0;

        // Keep on screen (reverse direction when touching edge)
        if (this.x < -this.width - 20 && this.speedX < 0) {
            this.speedX = -this.speedX;
            this.facingRight = true;
        } else if (this.x > window.innerWidth + 20 && this.speedX > 0) {
            this.speedX = -this.speedX;
            this.facingRight = false;
        }

        // Update propeller rotation
        this.propellerAngle += Math.abs(this.speedX) * 0.25;

        // Flash timer count down
        if (this.damageFlashTimer > 0) this.damageFlashTimer--;

        return null;
    }

    triggerDamageFlash() {
        this.damageFlashTimer = 15;
    }

    draw(ctx, frozen = false) {
        ctx.save();
        
        // Setup glow effects
        ctx.shadowColor = this.isDying ? 'rgba(255, 85, 0, 0.3)' : (this.isBoss ? this.bossStyle.glow : 'rgba(0, 0, 0, 0.4)');
        ctx.shadowBlur = this.isDying ? 14 : (this.isBoss ? 18 + this.bossLevel * 3 : 8);
        ctx.shadowOffsetY = 4;

        const isHeadingRight = this.facingRight;
        const deathProgress = this.isDying ? Math.min(1, this.deathTimer / this.deathDuration) : 0;
        const targetWreckScale = this.wreckScale || 0.42;
        const deathScale = this.isWrecked
            ? targetWreckScale
            : (this.isDying ? 1 - ((1 - targetWreckScale) * deathProgress) : 1);
        const deathTilt = this.isWrecked
            ? this.wreckTilt
            : (this.isDying ? this.wreckTilt * Math.max(0.35, deathProgress) : 0);
        
        // Shift drawing origin for direction scaling (flip sprite)
        ctx.translate(this.x + this.width / 2, this.y + this.height / 2);
        if (this.isDying) {
            ctx.rotate(deathTilt);
            ctx.scale(deathScale, deathScale);
        }
        if (!isHeadingRight) {
            ctx.scale(-1, 1);
        }

        // Damage flash override
        if (this.damageFlashTimer % 4 > 2) {
            ctx.fillStyle = '#ff3344';
        } else if (this.isDying) {
            ctx.fillStyle = deathProgress > 0.55 ? '#2b211d' : '#5b3426';
        } else if (frozen) {
            ctx.fillStyle = '#38bdf8'; // frozen tint
        } else {
            ctx.fillStyle = this.subColor;
        }

        // Submarine geometry (drawn responsive to width and height)
        const w = this.width;
        const h = this.height;

        ctx.strokeStyle = this.isDying ? '#0b0f14' : '#0f172a';
        ctx.lineWidth = this.isBoss ? 4 : 2;

        // 1. Draw Propeller (behind hull)
        ctx.save();
        ctx.translate(-w/2 + 2, 0);
        ctx.rotate(this.propellerAngle);
        ctx.fillStyle = this.isDying ? '#5c4033' : '#94a3b8';
        ctx.beginPath();
        ctx.ellipse(0, 0, 4, h/3, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.restore();

        // Propeller connection shaft
        ctx.fillStyle = this.isDying ? '#3f2a22' : '#475569';
        ctx.beginPath();
        ctx.rect(-w/2, -4, 4, 8);
        ctx.fill();
        ctx.stroke();

        // 2. Main Capsule Hull
        ctx.beginPath();
        ctx.roundRect(-w/2 + 3, -h/2, w - 8, h, h/2);
        ctx.fill();
        ctx.stroke();

        if (this.isDying) {
            ctx.strokeStyle = 'rgba(251, 113, 133, 0.75)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(-w * 0.25, -h * 0.2);
            ctx.lineTo(-w * 0.12, h * 0.1);
            ctx.lineTo(w * 0.04, -h * 0.05);
            ctx.moveTo(w * 0.18, -h * 0.22);
            ctx.lineTo(w * 0.26, h * 0.18);
            ctx.stroke();
        }

        // Boss hazard lines
        if (this.isBoss && !frozen && !(this.damageFlashTimer % 4 > 2)) {
            ctx.save();
            ctx.clip();
            ctx.fillStyle = this.bossStyle.accent;
            ctx.rotate(Math.PI / 4);
            for (let offset = -w; offset < w; offset += 35) {
                ctx.fillRect(offset, -h, 12, h * 2);
            }
            ctx.restore();
        }

        // 3. Conning Tower (Periscope Deck)
        ctx.beginPath();
        ctx.roundRect(-w/8, -h/2 - h/4, w/4, h/3, 4);
        ctx.fill();
        ctx.stroke();

        // 4. Periscope Pipe
        ctx.fillStyle = this.isDying ? '#3f2a22' : '#475569';
        ctx.beginPath();
        ctx.rect(0, -h/2 - h/2.5, 4, h/5);
        ctx.fill();
        // Periscope lens
        ctx.fillStyle = this.isDying ? '#111827' : '#00f0ff';
        ctx.beginPath();
        ctx.arc(3, -h/2 - h/2.5, 3, 0, Math.PI*2);
        ctx.fill();

        // 5. Windows (Portholes)
        ctx.fillStyle = this.isDying ? '#0f172a' : (frozen ? '#cbd5e1' : (this.isBoss ? this.bossStyle.accent : '#00f0ff'));
        ctx.strokeStyle = '#0f172a';
        ctx.lineWidth = 1.5;
        
        const numWindows = this.isBoss ? 4 : 2;
        const spacing = w / (numWindows + 1.5);
        for (let i = 0; i < numWindows; i++) {
            ctx.beginPath();
            ctx.arc(-w/4 + i * spacing + (this.isBoss ? 20 : 0), -2, h/6, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        }

        // Restore flip scale
        ctx.restore();

        // 6. Draw Word bubble (English label) ABOVE the sub
        // Drawn without translation scale to prevent text mirroring
        if (!this.isDying) {
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            // Text size settings
            const text = this.word.word;
            ctx.font = `bold ${this.isBoss ? 24 : 17}px ${varget('--font-heading', "'Fredoka', sans-serif")}`;
            const textWidth = ctx.measureText(text).width;
            
            const paddingX = 14;
            const paddingY = 8;
            const bubbleW = textWidth + paddingX * 2;
            const bubbleH = (this.isBoss ? 24 : 17) + paddingY * 2;
            
            const bubbleX = this.x + this.width / 2 - bubbleW / 2;
            const bubbleY = this.y - bubbleH - 12;

            // Draw bubble container
            ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
            ctx.strokeStyle = this.isBoss ? 'var(--neon-pink)' : 'rgba(255,255,255,0.2)';
            ctx.lineWidth = 2;
            
            ctx.beginPath();
            ctx.roundRect(bubbleX, bubbleY, bubbleW, bubbleH, 10);
            ctx.fill();
            ctx.stroke();

            // Word text
            ctx.fillStyle = '#ffffff';
            ctx.fillText(text, this.x + this.width / 2, bubbleY + bubbleH / 2 + 1);

            ctx.restore();
        }

    }
}

// Utility to retrieve CSS variables dynamically
function varget(cssVar, fallback) {
    if (typeof window === 'undefined') return fallback;
    return getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim() || fallback;
}


// ==========================================================================
// 7. ENEMY MISSILE ATTACKS
// ==========================================================================
class Missile {
    constructor(x, y, targetY, isBossPattern = false, speedMult = 1.0) {
        this.x = x;
        this.y = y;
        this.vy = -(3.8 * speedMult);
        this.width = 10;
        this.height = 25;
        this.targetY = targetY; // stop at ocean surface
        this.exploded = false;
        
        // Boss pattern might weave side to side
        this.isWeaving = isBossPattern && Math.random() > 0.4;
        this.weaveTimer = Math.random() * 100;
        this.vx = 0;
    }

    update() {
        if (this.isWeaving) {
            this.weaveTimer += 0.08;
            this.vx = Math.sin(this.weaveTimer) * 1.5;
        }

        this.x += this.vx;
        this.y += this.vy;

        // If missile exits water, trigger splash particles
        if (this.y <= this.targetY) {
            this.exploded = true;
            return 'splash_surface';
        }
        return null;
    }

    draw(ctx) {
        ctx.save();
        ctx.shadowColor = 'rgba(255, 60, 60, 0.5)';
        ctx.shadowBlur = 6;

        // Missile cylindrical body
        ctx.fillStyle = '#cbd5e1';
        ctx.strokeStyle = '#0f172a';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.rect(this.x - this.width/2, this.y, this.width, this.height);
        ctx.fill();
        ctx.stroke();

        // Rocket nosecone (red)
        ctx.fillStyle = '#ff3c3c';
        ctx.beginPath();
        ctx.moveTo(this.x - this.width/2, this.y);
        ctx.lineTo(this.x, this.y - 8);
        ctx.lineTo(this.x + this.width/2, this.y);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Engine tail fire
        ctx.fillStyle = Math.random() > 0.5 ? '#ff7b00' : '#ffd000';
        ctx.beginPath();
        ctx.moveTo(this.x - this.width/4, this.y + this.height);
        ctx.lineTo(this.x, this.y + this.height + 10 + Math.random()*8);
        ctx.lineTo(this.x + this.width/4, this.y + this.height);
        ctx.closePath();
        ctx.fill();

        ctx.restore();
    }
}


// ==========================================================================
// 8. BATTLESHIP (Player Unit)
// ==========================================================================
class Battleship {
    constructor(waterY, options = {}) {
        this.width = options.width || 135;
        this.height = options.height || 43;
        this.x = options.x || window.innerWidth / 2;
        this.y = waterY - this.height + 10;
        this.speed = 5.2;
        this.playerLabel = options.playerLabel || 'P1';
        this.palette = {
            hullTop: options.hullTop || '#f8fafc',
            hullMid: options.hullMid || '#93c5fd',
            hullBottom: options.hullBottom || '#2563eb',
            stroke: options.stroke || '#e0f2fe',
            keel: options.keel || '#f97316',
            deck: options.deck || '#dbeafe',
            deckStroke: options.deckStroke || '#60a5fa',
            bridgeBottom: options.bridgeBottom || '#bfdbfe',
            bridgeStroke: options.bridgeStroke || '#3b82f6',
            window: options.window || '#0ea5e9',
            windowGlow: options.windowGlow || '#7dd3fc',
            launcher: options.launcher || '#1d4ed8',
            shadow: options.shadow || 'rgba(14, 165, 233, 0.28)'
        };
        
        // Floating motion
        this.targetY = this.y;
        this.bobOffset = 0;

        // Per-ship depth charge loading
        this.fireCooldown = 0;
        this.maxBombsBeforeReload = 2;
        this.bombsRemaining = this.maxBombsBeforeReload;
        this.reloadDuration = 120;
        this.reloadTimer = 0;
        this.score = 0;
        this.lives = 3;
        this.isDisabled = false;
        this.movementDeltaX = 0;
        this.defeatBurnProgress = 0;
        this.defeatSinkProgress = 0;
        this.defeatTilt = 0;

        // Active State power-ups
        this.shieldActive = false;
        this.empActive = false;
        this.frozenSubActive = false;
    }

    update(keys, touchDir, waterY, time, controlMode = 'solo') {
        const previousX = this.x;
        if (this.isDisabled) {
            this.movementDeltaX = 0;
            return;
        }

        // Handle input motion
        let dir = 0;
        if (controlMode === 'secondary') {
            if (keys['a']) dir = -1;
            if (keys['d']) dir = 1;
        } else if (controlMode === 'primaryDuo') {
            if (keys['ArrowLeft']) dir = -1;
            if (keys['ArrowRight']) dir = 1;
        } else {
            if (keys['a'] || keys['ArrowLeft']) dir = -1;
            if (keys['d'] || keys['ArrowRight']) dir = 1;
        }
        
        // Touch overrides keyboard
        if (touchDir !== 0 && controlMode !== 'secondary') dir = touchDir;

        this.x += dir * this.speed;

        // Boundary constraints
        if (this.x < this.width/2 + 10) {
            this.x = this.width/2 + 10;
        }
        if (this.x > window.innerWidth - this.width/2 - 10) {
            this.x = window.innerWidth - this.width/2 - 10;
        }
        this.movementDeltaX = this.x - previousX;

        // Float / Bob along the water waves
        const waveBob = Math.sin(time * 0.05 + this.x * 0.02) * 4;
        this.y = waterY - this.height + 14 + waveBob;
    }

    draw(ctx, reloadProgress = 1, bombsRemaining = 2, maxBombs = 2) {
        ctx.save(); // Outer scaling save
        const transformY = this.isDefeatSinking ? this.y + this.height / 2 : this.y;
        ctx.translate(this.x, transformY);
        if (this.isDefeatSinking) {
            const tilt = this.defeatTilt * this.defeatSinkProgress;
            ctx.rotate(tilt);
        }
        ctx.scale(0.9, 0.9);
        ctx.translate(-this.x, -transformY);

        ctx.save();
        if (this.isDefeatSinking) {
            ctx.globalAlpha = 0.92;
        } else if (this.isDisabled) {
            ctx.globalAlpha = 0.45;
        }
        ctx.shadowColor = this.palette.shadow;
        ctx.shadowBlur = 14;
        ctx.shadowOffsetY = 5;

        const hullGrad = ctx.createLinearGradient(0, this.y, 0, this.y + this.height);
        if (this.isDefeatSinking) {
            hullGrad.addColorStop(0, '#fff1e6');
            hullGrad.addColorStop(0.28, this.defeatBurnProgress < 0.55 ? '#f97316' : '#7f1d1d');
            hullGrad.addColorStop(0.72, '#3f241f');
            hullGrad.addColorStop(1, '#111827');
        } else {
            hullGrad.addColorStop(0, this.palette.hullTop);
            hullGrad.addColorStop(0.45, this.palette.hullMid);
            hullGrad.addColorStop(1, this.palette.hullBottom);
        }

        // Cute rounded escort hull with a soft bow.
        ctx.fillStyle = hullGrad;
        ctx.strokeStyle = this.isDefeatSinking ? '#f97316' : this.palette.stroke;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(this.x - this.width/2 - 12, this.y + 14);
        ctx.quadraticCurveTo(this.x - this.width/2 + 4, this.y + this.height + 4, this.x - 30, this.y + this.height);
        ctx.lineTo(this.x + this.width/2 - 20, this.y + this.height);
        ctx.quadraticCurveTo(this.x + this.width/2 + 25, this.y + this.height - 4, this.x + this.width/2 + 20, this.y + 18);
        ctx.quadraticCurveTo(this.x + this.width/2 + 5, this.y - 2, this.x + this.width/2 - 12, this.y + 1);
        ctx.lineTo(this.x - this.width/2 + 8, this.y + 1);
        ctx.quadraticCurveTo(this.x - this.width/2 - 10, this.y + 3, this.x - this.width/2 - 12, this.y + 14);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Simple cheerful keel stripe.
        ctx.fillStyle = this.isDefeatSinking ? '#7f1d1d' : this.palette.keel;
        ctx.beginPath();
        ctx.roundRect(this.x - this.width/2 + 12, this.y + this.height - 12, this.width * 0.82, 7, 999);
        ctx.fill();

        // Soft deck platform.
        ctx.fillStyle = this.isDefeatSinking ? '#3f241f' : this.palette.deck;
        ctx.strokeStyle = this.isDefeatSinking ? '#fb923c' : this.palette.deckStroke;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(this.x - 56, this.y - 7, 112, 13, 999);
        ctx.fill();
        ctx.stroke();

        // Cute command bridge.
        const bridgeGrad = ctx.createLinearGradient(0, this.y - 44, 0, this.y + 4);
        bridgeGrad.addColorStop(0, this.isDefeatSinking ? '#fed7aa' : '#ffffff');
        bridgeGrad.addColorStop(1, this.isDefeatSinking ? '#451a03' : this.palette.bridgeBottom);
        ctx.fillStyle = bridgeGrad;
        ctx.strokeStyle = this.isDefeatSinking ? '#f97316' : this.palette.bridgeStroke;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(this.x - 30, this.y - 34, 60, 29, 9);
        ctx.fill();
        ctx.stroke();

        // Friendly windows.
        ctx.fillStyle = this.palette.window;
        ctx.shadowColor = this.palette.windowGlow;
        ctx.shadowBlur = 5;
        for (let i = 0; i < 4; i++) {
            ctx.beginPath();
            ctx.roundRect(this.x - 24 + i * 14, this.y - 25, 8, 7, 3);
            ctx.fill();
        }
        ctx.shadowBlur = 0;

        // Escort radar mast for an aircraft-carrier guard ship.
        ctx.strokeStyle = this.palette.bridgeStroke;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(this.x + 22, this.y - 34);
        ctx.lineTo(this.x + 22, this.y - 55);
        ctx.stroke();
        ctx.strokeStyle = this.palette.window;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.ellipse(this.x + 22, this.y - 57, 14, 4, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = '#93c5fd';
        ctx.beginPath();
        ctx.arc(this.x + 22, this.y - 44, 5, 0, Math.PI * 2);
        ctx.fill();

        // Small carrier-escort deck mark and player label.
        ctx.fillStyle = 'rgba(255,255,255,0.82)';
        ctx.font = "bold 12px 'Fredoka', sans-serif";
        ctx.textAlign = 'center';
        ctx.fillText(this.playerLabel, this.x, this.y + 27);

        // Minimal toy-like depth charge launchers.
        ctx.fillStyle = this.palette.launcher;
        ctx.strokeStyle = '#eff6ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(this.x - 64, this.y + 1, 28, 14, 7);
        ctx.roundRect(this.x + 40, this.y + 1, 28, 14, 7);
        ctx.fill();
        ctx.stroke();

        // Reload indicator appears above the ship while depth charges are being loaded.
        const isReloading = reloadProgress < 1;
        ctx.save();
        ctx.shadowBlur = 0;
        ctx.lineWidth = 1.5;
        for (let i = 0; i < maxBombs; i++) {
            ctx.fillStyle = i < bombsRemaining ? '#ffd000' : 'rgba(255, 255, 255, 0.22)';
            ctx.strokeStyle = 'rgba(15, 23, 42, 0.8)';
            ctx.beginPath();
            ctx.roundRect(this.x - 15 + i * 18, this.y + this.height - 8, 10, 14, 4);
            ctx.fill();
            ctx.stroke();
        }

        ctx.restore();

        // 3. Shield Bubble effect
        if (this.shieldActive) {
            ctx.restore(); // Exit shadow save
            ctx.save();
            const shieldGrad = ctx.createRadialGradient(this.x, this.y + 8, this.width * 0.4, this.x, this.y + 8, this.width * 0.7);
            shieldGrad.addColorStop(0, 'rgba(0, 240, 255, 0.05)');
            shieldGrad.addColorStop(0.85, 'rgba(0, 240, 255, 0.25)');
            shieldGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

            ctx.fillStyle = shieldGrad;
            ctx.strokeStyle = 'rgba(0, 240, 255, 0.7)';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.arc(this.x, this.y + 8, this.width * 0.7, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        }

        ctx.restore();
        ctx.restore(); // Restore outer scaling context
    }
}


// ==========================================================================
// 9. GAME ENGINE CORE
// ==========================================================================
class GameEngine {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Navigation overlays
        this.screenStart = document.getElementById('screen-start');
        this.screenGame = document.getElementById('screen-game');
        this.modalPause = document.getElementById('modal-pause');
        this.modalGameover = document.getElementById('modal-gameover');
        
        // HUD text values
        this.hudScoreLabel = document.getElementById('hud-score-label');
        this.hudScore = document.getElementById('hud-score');
        this.hudLivesLabel = document.getElementById('hud-lives-label');
        this.hudHearts = document.getElementById('hud-hearts');
        this.hudP2Stats = document.getElementById('hud-p2-stats');
        this.hudP2ScoreLabel = document.getElementById('hud-p2-score-label');
        this.hudP2Score = document.getElementById('hud-p2-score');
        this.hudP2LivesLabel = document.getElementById('hud-p2-lives-label');
        this.hudP2Hearts = document.getElementById('hud-p2-hearts');
        this.hudDiff = document.getElementById('hud-diff');
        this.hudTime = document.getElementById('hud-time');
        this.hudAccuracy = document.getElementById('hud-accuracy');
        this.hudAmmo = document.getElementById('hud-ammo');
        this.hudReloadFill = document.getElementById('hud-reload-fill');
        this.hudReloadText = document.getElementById('hud-reload-text');
        this.bilingualToggleBtn = document.getElementById('btn-bilingual-toggle');
        this.gradeSelect = document.getElementById('grade-select');
        this.gradeSourceStatus = document.getElementById('grade-source-status');
        this.targetValue = document.getElementById('target-value');
        this.targetTimerText = document.getElementById('target-timer');
        this.stageQuotaText = document.getElementById('stage-quota');
        this.bossHud = document.getElementById('boss-hud');
        this.bossHpText = document.getElementById('boss-hp-text');
        this.bossHpFill = document.getElementById('boss-hp-fill');
        
        this.comboDisplay = document.getElementById('combo-display');
        this.comboCountText = document.getElementById('combo-count');
        this.comboTitleText = document.getElementById('combo-title');

        // Power-up display timers
        this.puShield = document.getElementById('powerup-shield');
        this.puFreeze = document.getElementById('powerup-freeze');
        this.puFreezeVal = document.getElementById('powerup-freeze-timer');
        this.puEmp = document.getElementById('powerup-emp');
        this.puEmpVal = document.getElementById('powerup-emp-timer');

        // Settings / Game State
        this.mode = 'classic'; // classic, survival, practice, duo
        this.selectedGrade = this.getStoredVocabularyGrade();
        this.state = 'start'; // start, playing, paused, gameover
        this.score = 0;
        this.lives = 3;
        this.difficultyStage = 'EASY';
        this.timeElapsed = 0;
        this.maxGameDuration = 5 * 60 * 60; // 5 minutes at 60 FPS
        this.timeMultiplierTimer = 0;
        this.stageDuration = 60 * 60; // 1 minute at 60 fixed steps per second
        this.stageBossSpawnSecond = 40;
        this.finalStageBossSpawnSecond = 30;
        this.currentStageIndex = 0;
        this.levelPhase = 'normal';
        this.levelNormalTarget = 10;
        this.levelNormalActiveTarget = 5;
        this.levelNormalKills = 0;
        this.levelNormalSpawned = 0;
        this.levelBossTarget = 2;
        this.levelBossesDefeated = 0;
        this.stageKillsThisStage = 0;
        this.stageQuotaPenaltyApplied = false;
        this.stageBossTriggered = false;
        this.targetTimerDuration = 20 * 60;
        this.targetTimer = this.targetTimerDuration;
        this.survivalBonusInterval = 30 * 60; // 30 seconds at 60 FPS
        this.nextSurvivalBonusAt = this.survivalBonusInterval;
        this.finalSurvivalBonusAwarded = false;
        this.bilingualSpeechEnabled = true;

        // Stats tracking
        this.correctMatches = 0;
        this.incorrectMatches = 0;
        this.bossesDefeated = 0;
        this.highestCombo = 0;
        this.currentCombo = 0;
        this.wordsLearned = new Set();
        this.wordsMissed = new Set();

        // Controls input
        this.keys = {};
        this.touchDir = 0; // -1: left, 1: right, 0: idle
        this.fireCooldown = 0;
        this.maxBombsBeforeReload = 2;
        this.bombsRemaining = this.maxBombsBeforeReload;
        this.reloadDuration = 120; // 2 seconds at 60 FPS
        this.reloadTimer = 0;

        // Entities arrays
        this.battleship = null;
        this.secondBattleship = null;
        this.bombs = [];
        this.submarines = [];
        this.missiles = [];
        this.crates = [];
        this.particles = [];
        this.floatingTexts = [];

        // Targets selection
        this.currentTarget = null;
        this.manualTargetChangeCooldown = 0;
        this.manualTargetChangeCooldownDuration = 300; // 5 seconds at 60 FPS
        this.manualTargetChangeNoticeTimer = 0;

        // Attack cycle triggers
        this.attackTimer = 0;
        this.activeAttacker = null;
        this.maxConcurrentSubmarineAttackers = 2;

        // Physics Y coordinates
        this.waterY = 0;

        // Powerup Timers
        this.freezeTimer = 0;
        this.empTimer = 0;

        // Screen Shake Frame Count
        this.screenShakeTime = 0;
        this.defeatSequenceTimer = 0;
        this.defeatBurnDuration = 180; // 3 seconds at 60 fixed steps per second
        this.defeatSinkDuration = 300; // half the previous sinking speed
        this.defeatSequenceReason = 'defeat';
        this.defeatedShips = [];
        this.levelUpEffect = null;
        
        // Loop time tracking
        this.gameTime = 0;
        this.fixedStepMs = 1000 / 60;
        this.maxFrameDeltaMs = 250;
        this.frameAccumulatorMs = 0;
        this.lastFrameTimestamp = null;

        // Twinkling stars in the sky
        this.stars = [];
        for (let i = 0; i < 40; i++) {
            this.stars.push({
                x: Math.random(),
                y: Math.random(),
                size: Math.random() * 2 + 0.8,
                phase: Math.random() * Math.PI * 2,
                speed: Math.random() * 0.04 + 0.015
            });
        }
    }

    getStoredVocabularyGrade() {
        const storedSource = localStorage.getItem('vocabulary_grade') || '4';
        if (storedSource === 'toeic') return 'toeic';
        const storedGrade = Number.parseInt(storedSource, 10);
        if (!Number.isInteger(storedGrade) || storedGrade < 1 || storedGrade > 12) return 4;
        return storedGrade;
    }

    async loadSelectedGradeVocabulary() {
        if (this.gradeSelect) {
            this.gradeSelect.value = String(this.selectedGrade);
        }
        const loadingLabel = this.selectedGrade === 'toeic' ? 'TOEIC' : `Grade ${this.selectedGrade}`;
        this.updateGradeSourceStatus(`Loading ${loadingLabel} vocabulary...`);
        await vocab.loadVocab(this.selectedGrade);
        this.updateGradeSourceStatus(`Using ${vocab.sourceLabel} • ${vocab.words.length} words`);
    }

    updateGradeSourceStatus(text) {
        if (this.gradeSourceStatus) {
            this.gradeSourceStatus.innerText = text;
        }
    }

    clearAllSavedProgress() {
        const modes = ['classic', 'survival', 'practice'];
        modes.forEach(mode => {
            localStorage.removeItem(`hscore_${mode}`);
            localStorage.removeItem(`history_${mode}`);
        });

        for (let grade = 1; grade <= 12; grade++) {
            localStorage.removeItem(`vocab_stats_grade_${grade}`);
        }
        localStorage.removeItem('vocab_stats_toeic');

        vocab.clearPersistedStats();
        this.score = 0;
        this.correctMatches = 0;
        this.incorrectMatches = 0;
        this.highestCombo = 0;
        this.wordsLearned.clear();
        this.wordsMissed.clear();
    }

    async init() {
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());

        // Keyboard bindings
        window.addEventListener('keydown', e => {
            if (this.handleMenuKeyboardNavigation(e)) return;

            this.keys[e.key] = true;
            this.keys[e.key.toLowerCase()] = true;
            if (this.state !== 'playing') return;
            // Space or ArrowDown to fire depth charge
            if (e.key === ' ' || e.key === 'ArrowDown') {
                this.fireDepthCharge(this.battleship);
                e.preventDefault();
            }
            // ArrowUp to change target answer
            if (e.key === 'ArrowUp') {
                this.requestManualTargetChange();
                e.preventDefault();
            }
            if (this.mode === 'duo') {
                const key = e.key.toLowerCase();
                if (key === 's') {
                    this.fireDepthCharge(this.secondBattleship);
                    e.preventDefault();
                }
                if (key === 'w') {
                    this.requestManualTargetChange();
                    e.preventDefault();
                }
            }
        });
        window.addEventListener('keyup', e => {
            this.keys[e.key] = false;
            this.keys[e.key.toLowerCase()] = false;
        });

        // Setup DOM event listeners
        this.setupEventListeners();

        // Load vocabulary pool
        await this.loadSelectedGradeVocabulary();
        
        // Update high score text
        this.updateStartHighScore();
        this.renderStartPlayHistory();
        this.focusCurrentMenuDefault();

        // Start requestAnimationFrame core loop
        requestAnimationFrame(timestamp => this.loop(timestamp));
    }

    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.waterY = this.canvas.height * 0.3; // surface line is top 30%
        this.getActiveBattleships().forEach(ship => {
            ship.targetY = this.waterY - ship.height + 10;
        });
    }

    getActiveBattleships() {
        return [this.battleship, this.secondBattleship].filter(Boolean);
    }

    areAllPlayerShipsDisabled() {
        return this.getActiveBattleships().every(ship => ship.isDisabled || ship.lives <= 0);
    }

    getActiveMenuContainer() {
        if (!this.modalPause.classList.contains('hidden')) return this.modalPause;
        if (!this.modalGameover.classList.contains('hidden')) return this.modalGameover;
        if (this.state === 'start' && this.screenStart.classList.contains('active')) return this.screenStart;
        return null;
    }

    getMenuButtons(container) {
        if (!container) return [];
        return Array.from(container.querySelectorAll('button'))
            .filter(btn => !btn.disabled && btn.offsetParent !== null);
    }

    focusCurrentMenuDefault() {
        const container = this.getActiveMenuContainer();
        const buttons = this.getMenuButtons(container);
        if (buttons.length === 0) return;

        const defaultButton = container === this.screenStart
            ? buttons.find(btn => btn.classList.contains('active')) || buttons[0]
            : buttons[0];
        defaultButton.focus();
    }

    handleMenuKeyboardNavigation(e) {
        const navKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Enter'];
        if (!navKeys.includes(e.key)) return false;

        const container = this.getActiveMenuContainer();
        const buttons = this.getMenuButtons(container);
        if (buttons.length === 0) return false;

        e.preventDefault();
        sound.init();

        const currentIndex = buttons.indexOf(document.activeElement);
        if (e.key === 'Enter') {
            const selectedButton = currentIndex >= 0 ? buttons[currentIndex] : buttons[0];
            selectedButton.focus();
            selectedButton.click();
            return true;
        }

        const step = (e.key === 'ArrowDown' || e.key === 'ArrowRight') ? 1 : -1;
        const nextIndex = currentIndex >= 0
            ? (currentIndex + step + buttons.length) % buttons.length
            : 0;
        buttons[nextIndex].focus();
        return true;
    }

    setupEventListeners() {
        // Play button
        document.getElementById('btn-play').addEventListener('click', async () => {
            sound.init();
            await this.loadSelectedGradeVocabulary();
            this.startGame();
        });

        if (this.gradeSelect) {
            this.gradeSelect.value = String(this.selectedGrade);
            this.gradeSelect.addEventListener('change', async () => {
                this.selectedGrade = this.gradeSelect.value === 'toeic'
                    ? 'toeic'
                    : Number.parseInt(this.gradeSelect.value, 10) || 4;
                localStorage.setItem('vocabulary_grade', String(this.selectedGrade));
                await this.loadSelectedGradeVocabulary();
                this.renderStartPlayHistory();
            });
        }

        const resetVocabStateBtn = document.getElementById('btn-reset-vocab-state');
        if (resetVocabStateBtn) {
            resetVocabStateBtn.addEventListener('click', async () => {
                const confirmed = window.confirm('Reset all progress? This will delete word progress, play history, and high scores for every mode and grade.');
                if (!confirmed) return;

                this.clearAllSavedProgress();
                await this.loadSelectedGradeVocabulary();
                this.updateStartHighScore();
                this.renderStartPlayHistory();
                this.updateGradeSourceStatus(`All progress reset • ${vocab.sourceLabel} • ${vocab.words.length} words`);
            });
        }

        // Mode toggling
        const modeButtons = document.querySelectorAll('.mode-btn');
        modeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                modeButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.mode = btn.dataset.mode;
                this.updateStartHighScore();
                this.renderStartPlayHistory();
            });
        });

        // HUD Pause & Sound
        document.getElementById('btn-pause').addEventListener('click', () => this.pauseGame());
        
        const soundBtn = document.getElementById('btn-sound-toggle');
        soundBtn.addEventListener('click', () => {
            const isMuted = sound.toggleMute();
            soundBtn.innerText = isMuted ? '❌' : '🔊';
        });

        if (this.bilingualToggleBtn) {
            this.updateBilingualSpeechButton();
            this.bilingualToggleBtn.addEventListener('click', () => {
                this.bilingualSpeechEnabled = !this.bilingualSpeechEnabled;
                this.updateBilingualSpeechButton();
            });
        }

        // Pause Modal controls
        document.getElementById('btn-resume').addEventListener('click', () => this.resumeGame());
        document.getElementById('btn-restart-paused').addEventListener('click', () => {
            this.resumeGame();
            this.startGame();
        });
        document.getElementById('btn-quit-paused').addEventListener('click', () => {
            this.resumeGame();
            this.quitToMenu();
        });

        // Game Over Controls
        document.getElementById('btn-play-again').addEventListener('click', () => {
            this.modalGameover.classList.add('hidden');
            this.startGame();
        });
        document.getElementById('btn-quit-gameover').addEventListener('click', () => {
            this.modalGameover.classList.add('hidden');
            this.quitToMenu();
        });

        // Mobile touch controls (continuous movement by holding down)
        const btnLeft = document.getElementById('btn-left');
        const btnRight = document.getElementById('btn-right');
        const btnFire = document.getElementById('btn-fire');

        const setTouchDir = (dir) => {
            sound.init();
            this.touchDir = dir;
        };

        btnLeft.addEventListener('mousedown', () => setTouchDir(-1));
        btnLeft.addEventListener('touchstart', (e) => { e.preventDefault(); setTouchDir(-1); });
        btnLeft.addEventListener('mouseup', () => setTouchDir(0));
        btnLeft.addEventListener('touchend', (e) => { e.preventDefault(); setTouchDir(0); });

        btnRight.addEventListener('mousedown', () => setTouchDir(1));
        btnRight.addEventListener('touchstart', (e) => { e.preventDefault(); setTouchDir(1); });
        btnRight.addEventListener('mouseup', () => setTouchDir(0));
        btnRight.addEventListener('touchend', (e) => { e.preventDefault(); setTouchDir(0); });

        btnFire.addEventListener('touchstart', (e) => {
            e.preventDefault();
            sound.init();
            this.fireDepthCharge(this.battleship);
        });
        btnFire.addEventListener('click', () => {
            sound.init();
            this.fireDepthCharge(this.battleship);
        });
    }

    startGame() {
        if (document.activeElement && typeof document.activeElement.blur === 'function') {
            document.activeElement.blur();
        }

        this.state = 'playing';
        this.score = 0;
        this.lives = this.mode === 'practice' ? 999 : 3; // unlimited practically in practice mode
        this.timeElapsed = 0;
        this.timeMultiplierTimer = 0;
        this.currentStageIndex = 0;
        this.levelPhase = 'normal';
        this.levelNormalKills = 0;
        this.levelNormalSpawned = 0;
        this.levelBossesDefeated = 0;
        this.stageKillsThisStage = 0;
        this.stageQuotaPenaltyApplied = false;
        this.stageBossTriggered = false;
        this.targetTimer = this.targetTimerDuration;
        this.nextSurvivalBonusAt = this.survivalBonusInterval;
        this.finalSurvivalBonusAwarded = false;
        this.difficultyStage = 'EASY';
        this.correctMatches = 0;
        this.incorrectMatches = 0;
        this.bossesDefeated = 0;
        this.highestCombo = 0;
        this.currentCombo = 0;
        this.wordsLearned.clear();
        this.wordsMissed.clear();
        this.freezeTimer = 0;
        this.empTimer = 0;
        this.fireCooldown = 0;
        this.bombsRemaining = this.maxBombsBeforeReload;
        this.reloadTimer = 0;
        this.manualTargetChangeCooldown = 0;
        this.manualTargetChangeNoticeTimer = 0;

        this.bombs = [];
        this.submarines = [];
        this.missiles = [];
        this.crates = [];
        this.particles = [];
        this.floatingTexts = [];
        this.frameAccumulatorMs = 0;
        this.lastFrameTimestamp = null;
        this.defeatSequenceTimer = 0;
        this.defeatSequenceReason = 'defeat';
        this.defeatedShips = [];
        this.levelUpEffect = null;
        
        vocab.reset();

        this.battleship = new Battleship(this.waterY, {
            x: this.mode === 'duo' ? window.innerWidth * 0.65 : window.innerWidth / 2,
            playerLabel: 'P1'
        });
        this.secondBattleship = this.mode === 'duo'
            ? new Battleship(this.waterY, {
                x: window.innerWidth * 0.35,
                playerLabel: 'P2',
                hullTop: '#fff7ed',
                hullMid: '#f9a8d4',
                hullBottom: '#db2777',
                stroke: '#fce7f3',
                keel: '#a855f7',
                deck: '#fce7f3',
                deckStroke: '#f472b6',
                bridgeBottom: '#fbcfe8',
                bridgeStroke: '#db2777',
                window: '#a855f7',
                windowGlow: '#f0abfc',
                launcher: '#be185d',
                shadow: 'rgba(236, 72, 153, 0.28)'
            })
            : null;

        this.screenStart.classList.remove('active');
        this.screenGame.classList.add('active');

        this.startLevel(0);

        this.updateHUD();
        this.bossHud.classList.add('hidden');
    }

    pauseGame() {
        if (this.state !== 'playing') return;
        this.state = 'paused';
        this.modalPause.classList.remove('hidden');
        this.focusCurrentMenuDefault();
    }

    resumeGame() {
        if (this.state !== 'paused') return;
        this.state = 'playing';
        this.modalPause.classList.add('hidden');
        if (document.activeElement && typeof document.activeElement.blur === 'function') {
            document.activeElement.blur();
        }
    }

    quitToMenu() {
        this.state = 'start';
        this.screenGame.classList.remove('active');
        this.screenStart.classList.add('active');
        this.updateStartHighScore();
        this.renderStartPlayHistory();
        this.focusCurrentMenuDefault();
    }

    updateStartHighScore() {
        if (this.mode === 'duo') {
            document.getElementById('start-high-score').innerText = 'N/A';
            return;
        }
        const stored = localStorage.getItem(`hscore_${this.mode}`) || 0;
        document.getElementById('start-high-score').innerText = stored;
    }

    saveHighScore() {
        if (this.mode === 'duo') return;
        const key = `hscore_${this.mode}`;
        const stored = parseInt(localStorage.getItem(key) || 0);
        if (this.score > stored) {
            localStorage.setItem(key, this.score);
        }
    }

    getHighScore() {
        if (this.mode === 'duo') return 0;
        return parseInt(localStorage.getItem(`hscore_${this.mode}`) || 0);
    }

    savePlayHistory() {
        if (this.mode === 'duo') return;
        const key = `history_${this.mode}`;
        const history = this.getPlayHistory();
        history.unshift({
            score: this.score,
            grade: vocab.grade || this.selectedGrade,
            sourceLabel: vocab.sourceLabel,
            accuracy: vocab.getAccuracy(),
            correct: this.correctMatches,
            combo: this.highestCombo,
            survivalTime: Math.min(this.timeElapsed, this.maxGameDuration),
            duration: Math.min(this.timeElapsed, this.maxGameDuration),
            playedAt: new Date().toISOString()
        });
        localStorage.setItem(key, JSON.stringify(history.slice(0, 10)));
    }

    getPlayHistory() {
        if (this.mode === 'duo') return [];
        try {
            return JSON.parse(localStorage.getItem(`history_${this.mode}`) || '[]');
        } catch (e) {
            return [];
        }
    }

    formatTime(frameCount) {
        const totalSeconds = Math.max(0, Math.ceil(frameCount / 60));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    getStageName(stageIndex = this.currentStageIndex) {
        const stages = ['EASY', 'MEDIUM', 'HARD', 'INSANE', 'NIGHTMARE'];
        return stages[Math.min(stages.length - 1, stageIndex)];
    }

    startLevel(stageIndex = this.currentStageIndex) {
        this.currentStageIndex = stageIndex;
        this.difficultyStage = this.getStageName(stageIndex);
        this.levelPhase = 'normal';
        this.levelNormalKills = 0;
        this.levelNormalSpawned = 0;
        this.levelBossesDefeated = 0;
        this.stageBossTriggered = false;
        this.stageKillsThisStage = 0;
        this.stageQuotaPenaltyApplied = false;
        this.bossHud.classList.add('hidden');
        this.attackTimer = 0;
        this.missiles = [];

        this.selectNewTarget();
        this.maintainLevelNormalSubmarines();
        this.floatingTexts.push(new FloatingText(this.canvas.width / 2, this.canvas.height * 0.32, `LEVEL ${this.currentStageIndex + 1}: ${this.difficultyStage}`, '#00ffff', 1.35));
        this.updateHUD();
    }

    selectNewTarget() {
        const previousTarget = this.currentTarget;
        
        // During a boss fight, keep the target locked to the visible boss word.
        const activeBoss = this.submarines.find(s => s.isBoss && !s.isDying);
        this.currentTarget = activeBoss ? activeBoss.word : vocab.pickNextTarget();

        // Set top bar target string
        this.targetValue.innerHTML = `${this.currentTarget.emoji || ''} ${this.currentTarget.meaning}`;
        this.targetTimer = this.targetTimerDuration;
        this.updateTargetPressureHUD();
        this.speakCurrentTargetWord();
        
        // Ensure at least one submarine contains the correct English word
        this.guaranteeTargetSubmarinePresence();
    }

    requestManualTargetChange() {
        if (this.manualTargetChangeCooldown > 0) {
            if (this.manualTargetChangeNoticeTimer <= 0 && this.battleship) {
                const secondsLeft = Math.ceil(this.manualTargetChangeCooldown / 60);
                this.floatingTexts.push(new FloatingText(this.battleship.x, this.battleship.y - 48, `TARGET CHANGE IN ${secondsLeft}s`, '#ffd000', 0.8));
                this.manualTargetChangeNoticeTimer = 45;
            }
            return;
        }

        this.selectNewTarget();
        this.manualTargetChangeCooldown = this.manualTargetChangeCooldownDuration;
    }

    updateBilingualSpeechButton() {
        if (!this.bilingualToggleBtn) return;

        this.bilingualToggleBtn.classList.toggle('active', this.bilingualSpeechEnabled);
        this.bilingualToggleBtn.innerText = this.bilingualSpeechEnabled ? 'VI+EN' : 'EN';
        this.bilingualToggleBtn.title = this.bilingualSpeechEnabled
            ? 'Speech: Vietnamese meaning then English word'
            : 'Speech: English word only';
    }

    getSpeechVoice(langPrefix) {
        if (!window.speechSynthesis) return null;

        const voices = window.speechSynthesis.getVoices();
        const prefix = langPrefix.toLowerCase();
        if (prefix === 'vi') {
            return voices.find(v => (v.lang || '').toLowerCase() === 'vi-vn')
                || voices.find(v => (v.lang || '').toLowerCase().startsWith('vi'))
                || voices.find(v => (v.name || '').toLowerCase().includes('vietnam'));
        }
        return voices.find(v => v.lang && v.lang.toLowerCase().startsWith(prefix));
    }

    createSpeechUtterance(text, langPrefix) {
        const utter = new SpeechSynthesisUtterance(text);
        const voice = this.getSpeechVoice(langPrefix);
        utter.lang = langPrefix === 'vi' ? 'vi-VN' : 'en-US';
        utter.rate = langPrefix === 'vi' ? 0.92 : 0.95;
        if (voice) utter.voice = voice;
        return utter;
    }

    speakWithBrowserVoice(text, langPrefix, allowSystemFallback = false) {
        return new Promise(resolve => {
            if (!window.speechSynthesis || !text) {
                resolve(false);
                return;
            }

            if (langPrefix === 'vi' && !allowSystemFallback && !this.getSpeechVoice('vi')) {
                resolve(false);
                return;
            }

            const utter = this.createSpeechUtterance(text, langPrefix);
            utter.onend = () => resolve(true);
            utter.onerror = () => resolve(false);
            window.speechSynthesis.speak(utter);
        });
    }

    getVietnameseTtsUrls(text) {
        const encodedText = encodeURIComponent(text);
        return [
            `https://api.streamelements.com/kappa/v2/speech?voice=vi-VN-HoaiMyNeural&text=${encodedText}`,
            `https://api.streamelements.com/kappa/v2/speech?voice=vi-VN-NamMinhNeural&text=${encodedText}`,
            `https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=vi&q=${encodedText}`
        ];
    }

    playAudioUrl(url, startupTimeoutMs = 2500, maxDurationMs = 8000) {
        return new Promise(resolve => {
            if (!url) {
                resolve(false);
                return;
            }

            if (this.currentVietnameseAudio) {
                this.currentVietnameseAudio.pause();
                this.currentVietnameseAudio = null;
            }

            const audio = new Audio(url);
            this.currentVietnameseAudio = audio;
            let settled = false;
            let started = false;

            const finish = (success) => {
                if (settled) return;
                settled = true;
                clearTimeout(startupTimer);
                clearTimeout(maxTimer);
                resolve(success);
            };

            const startupTimer = setTimeout(() => {
                if (!started) {
                    audio.pause();
                    finish(false);
                }
            }, startupTimeoutMs);
            const maxTimer = setTimeout(() => {
                audio.pause();
                finish(false);
            }, maxDurationMs);

            audio.onplaying = () => {
                started = true;
                clearTimeout(startupTimer);
            };
            audio.onended = () => finish(true);
            audio.onerror = () => finish(false);
            audio.play()
                .then(() => {
                    started = true;
                    clearTimeout(startupTimer);
                })
                .catch(() => finish(false));
        });
    }

    async speakVietnameseText(text) {
        for (const url of this.getVietnameseTtsUrls(text)) {
            const played = await this.playAudioUrl(url);
            if (played) return;
        }

        // Last resort: keep the target meaning audible even if online Vietnamese TTS is blocked.
        await this.speakWithBrowserVoice(text, 'vi', true);
    }

    async speakWordAudio(wordObj) {
        if (!wordObj?.word) return;

        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }

        if (this.bilingualSpeechEnabled && wordObj.meaning) {
            await this.speakVietnameseText(wordObj.meaning);
        }
        await this.speakWithBrowserVoice(wordObj.word, 'en');
    }

    speakCurrentTargetWord() {
        if (!this.currentTarget?.word) return;

        this.speakWordAudio(this.currentTarget);
    }

    guaranteeTargetSubmarinePresence() {
        if (!this.currentTarget) return;

        // Check if any submarine is carrying the current target word
        const targetWordText = this.currentTarget.word.toLowerCase();
        
        // Don't modify submarines if a boss fight is currently active
        const hasBoss = this.submarines.some(s => s.isBoss && !s.isDying);
        if (hasBoss) return;

        const activeSubs = this.submarines.filter(s => !s.isDying && !s.isWarning && !s.isBoss);
        const hasTarget = activeSubs.some(sub => sub.word.word.toLowerCase() === targetWordText);
        
        if (!hasTarget) {
            // Replace word of a random submarine or spawn a new one carrying it
            if (activeSubs.length > 0) {
                const subToReplace = activeSubs[Math.floor(Math.random() * activeSubs.length)];
                subToReplace.word = this.currentTarget;
            } else if (this.levelPhase === 'normal' && this.levelNormalSpawned < this.levelNormalTarget) {
                this.spawnLevelNormalSubmarine(this.currentTarget);
            } else if (this.mode === 'practice') {
                this.spawnSubmarine(0, this.currentTarget);
            }
        }
    }

    spawnSubmarine(depthIndex = null, specificWord = null) {
        // Assign a depth index layer to prevent visual overlapping
        if (depthIndex === null) {
            const occupiedIndices = this.submarines.map(s => s.depthIndex);
            // Search for free index layers between 0 and 5
            for (let i = 0; i < 6; i++) {
                if (!occupiedIndices.includes(i)) {
                    depthIndex = i;
                    break;
                }
            }
            if (depthIndex === null) depthIndex = Math.floor(Math.random() * 5);
        }

        // Depth layers are placed from y = 30% screen to 80% screen
        // Adjust to ensure submarines appear in the lower half of the water area
        const halfDepthStart = this.waterY + (this.canvas.height - this.waterY) / 2;
        const minDepthY = halfDepthStart; // start at halfway down from water surface
        const maxDepthY = this.canvas.height * 0.85; // keep upper bound near bottom
        const subDepthY = minDepthY + (depthIndex * ((maxDepthY - minDepthY) / 6));

        // Get matching or wrong options word
        let wordObj = specificWord;
        if (!wordObj) {
            // 35% chance to spawn the correct target word if it isn't fully saturated
            const targetWordText = this.currentTarget.word.toLowerCase();
            const isTargetPresent = this.submarines.some(s => s.word.word.toLowerCase() === targetWordText);
            
            if (!isTargetPresent && Math.random() < 0.4) {
                wordObj = this.currentTarget;
            } else {
                const wrongOptions = vocab.getRandomWrongOptions(this.currentTarget.word, 1);
                wordObj = wrongOptions[0];
            }
        }

        const mult = this.getDifficultySpeedMultiplier();
        const sub = new Submarine(subDepthY, depthIndex, wordObj, mult, false);
        // Ensure submarine does not spawn too close to player ships horizontally
        this.getActiveBattleships().forEach(ship => {
            const minDist = 150; // minimum horizontal distance in pixels
            if (Math.abs(sub.x - ship.x) < minDist) {
                // Shift submarine to the opposite side
                sub.x = (sub.x < ship.x) ? sub.x - minDist : sub.x + minDist;
                // Clamp within canvas bounds
                sub.x = Math.max(sub.width / 2, Math.min(this.canvas.width - sub.width / 2, sub.x));
            }
        });
        this.submarines.push(sub);
        return sub;
    }

    getActiveNormalSubmarines() {
        return this.submarines.filter(sub => !sub.isDying && !sub.isBoss);
    }

    getActiveLevelBosses() {
        return this.submarines.filter(sub => !sub.isDying && sub.isBoss && sub.isStageBoss);
    }

    spawnLevelNormalSubmarine(specificWord = null) {
        if (this.levelPhase !== 'normal' || this.levelNormalSpawned >= this.levelNormalTarget) return null;
        const sub = this.spawnSubmarine(null, specificWord);
        if (sub) this.levelNormalSpawned++;
        return sub;
    }

    maintainLevelNormalSubmarines() {
        if (this.mode === 'practice' || this.levelPhase !== 'normal') return;

        let activeNormalSubs = this.getActiveNormalSubmarines();
        while (activeNormalSubs.length < this.levelNormalActiveTarget && this.levelNormalSpawned < this.levelNormalTarget) {
            this.spawnLevelNormalSubmarine();
            activeNormalSubs = this.getActiveNormalSubmarines();
        }
    }

    startLevelBossPhase() {
        if (this.levelPhase === 'boss') return;

        this.levelPhase = 'boss';
        this.levelBossesDefeated = 0;
        this.stageBossTriggered = true;
        this.attackTimer = 0;
        this.missiles = [];
        this.currentTarget = vocab.pickNextTarget();
        this.targetValue.innerHTML = `${this.currentTarget.emoji || ''} ${this.currentTarget.meaning}`;
        this.targetTimer = this.targetTimerDuration;
        this.speakCurrentTargetWord();

        for (let i = 0; i < this.levelBossTarget; i++) {
            const boss = this.spawnBossSubmarine({
                hp: 4,
                bossLevel: Math.min(4, this.currentStageIndex),
                isStageBoss: true,
                wordObj: this.currentTarget,
                x: this.canvas.width * (i === 0 ? 0.32 : 0.68),
                message: i === 0 ? `⚠️ ${this.difficultyStage} DOUBLE BOSS ⚠️` : `⚠️ SECOND BOSS ⚠️`
            });
            if (boss) {
                boss.speedX = i === 0 ? Math.abs(boss.speedX) : -Math.abs(boss.speedX);
            }
        }
        this.updateTargetPressureHUD();
    }

    advanceToNextLevel() {
        this.currentCombo = 0;
        this.hideComboOverlay();
        this.triggerVictoryFireworks();
        sound.playVictory();
        this.startLevel(this.currentStageIndex + 1);
        this.triggerLevelUpEffect();
    }

    triggerLevelUpEffect() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height * 0.38;

        this.levelUpEffect = {
            timer: 120,
            duration: 120,
            levelNumber: this.currentStageIndex + 1,
            stageName: this.difficultyStage
        };

        this.triggerScreenShake(18);
        this.floatingTexts.push(new FloatingText(centerX, centerY + 82, `LEVEL ${this.currentStageIndex + 1} START!`, '#7dd3fc', 1.35));

        this.particles.push(new Particle(centerX, centerY, 'shockwave', 'rgba(255, 255, 255, 0.88)', {
            size: 18,
            maxSize: 260,
            lineWidth: 8,
            decay: 0.025
        }));
        this.particles.push(new Particle(centerX, centerY, 'shockwave', 'rgba(34, 211, 238, 0.54)', {
            size: 8,
            maxSize: 340,
            lineWidth: 5,
            decay: 0.02
        }));

        for (let i = 0; i < 80; i++) {
            const color = i % 3 === 0 ? '#facc15' : (i % 3 === 1 ? '#22d3ee' : '#f472b6');
            this.particles.push(new Particle(centerX, centerY, 'firework', color));
        }

        for (let i = 0; i < 18; i++) {
            this.particles.push(new Particle(
                Math.random() * this.canvas.width,
                this.waterY + Math.random() * 18,
                'splash',
                i % 2 === 0 ? 'rgba(236, 253, 255, 0.95)' : 'rgba(125, 211, 252, 0.85)'
            ));
        }
    }

    spawnBossSubmarine(options = {}) {
        // Clear all missiles and warning systems
        this.activeAttacker = null;
        this.attackTimer = 0;
        
        // Spawn boss in middle depth layer
        const bossY = this.canvas.height * 0.55;
        const wordObj = options.wordObj || this.currentTarget;
        
        const boss = new Submarine(bossY, 2, wordObj, 1.0, true, {
            hp: options.hp,
            bossLevel: options.bossLevel || 0
        });
        if (typeof options.x === 'number') {
            boss.x = Math.max(boss.width / 2, Math.min(this.canvas.width - boss.width / 2, options.x));
        }
        boss.isStageBoss = Boolean(options.isStageBoss);
        this.submarines.push(boss);

        // Visual flash trigger
        this.triggerScreenShake(30);
        this.bossHud.classList.remove('hidden');
        this.updateBossHud(boss);

        this.floatingTexts.push(new FloatingText(this.canvas.width/2, this.canvas.height/2 - 50, options.message || "⚠️ BOSS INCOMING ⚠️", "#ff0055", 1.8));
        return boss;
    }

    fireDepthCharge(ship = this.battleship) {
        if (!ship || ship.isDisabled || ship.fireCooldown > 0 || ship.reloadTimer > 0 || ship.bombsRemaining <= 0) return;
        ship.fireCooldown = 22; // 0.36 seconds delay cooldown
        
        const bomb = new Bomb(ship.x, ship.y + ship.height - 10, ship);
        this.bombs.push(bomb);
        ship.bombsRemaining--;
        sound.playShoot();

        if (ship.bombsRemaining <= 0) {
            ship.reloadTimer = ship.reloadDuration;
            this.floatingTexts.push(new FloatingText(ship.x, ship.y - 40, "RELOADING...", '#ffd000', 0.9));
            sound.playReload();
        }
        this.updateAmmoHUD();
    }

    triggerScreenShake(duration) {
        this.screenShakeTime = duration;
        document.body.classList.add('shake-screen');
    }

    // ==========================================================================
    // PROGRESSIVE DIFFICULTY SCALING
    // ==========================================================================
    getDifficultySpeedMultiplier() {
        switch (this.difficultyStage) {
            case 'EASY': return 1.0;
            case 'MEDIUM': return 1.25;
            case 'HARD': return 1.6;
            case 'INSANE': return 2.1;
            case 'NIGHTMARE': return 2.8;
            default: return 1.0;
        }
    }

    getMaxSubmarinesCount() {
        return this.levelNormalActiveTarget;
    }

    getMinSubmarinesCount() {
        return this.levelNormalActiveTarget;
    }

    getAttackCooldown() {
        if (this.mode === 'practice') return 99999; // Never attack in Practice Mode
        switch (this.difficultyStage) {
            case 'EASY': return 240; // 4 seconds at 60 FPS
            case 'MEDIUM': return 180; // 3 seconds
            case 'HARD': return 140; // 2.3 seconds
            case 'INSANE': return 100; // 1.6 seconds
            case 'NIGHTMARE': return 70; // 1.1 seconds
            default: return 240;
        }
    }

    updateDifficultyLevel() {
        if (this.mode === 'practice') {
            this.difficultyStage = 'PRACTICE';
            return;
        }
        this.difficultyStage = this.getStageName();
        this.updateTargetPressureHUD();
    }

    getStageKillQuota(stageIndex = this.currentStageIndex) {
        return [5, 7, 9, 11, 13][Math.min(4, stageIndex)] || 5;
    }

    applyStageQuotaPenalty(stageIndex = this.currentStageIndex) {
        if (this.mode === 'practice' || this.stageQuotaPenaltyApplied) return;
        const quota = this.getStageKillQuota(stageIndex);
        if (this.stageKillsThisStage >= quota) return;

        this.stageQuotaPenaltyApplied = true;
        this.currentCombo = 0;
        this.hideComboOverlay();
        this.floatingTexts.push(new FloatingText(this.canvas.width / 2, this.canvas.height * 0.32, `STAGE QUOTA MISSED! ${this.stageKillsThisStage}/${quota}`, '#ff3c3c', 1.25));
        sound.playDamage();
        this.triggerScreenShake(16);

        if (this.mode === 'duo') {
            this.getActiveBattleships().forEach(ship => {
                if (ship.isDisabled || ship.lives <= 0) return;
                ship.lives--;
                if (ship.lives <= 0) {
                    ship.lives = 0;
                    ship.isDisabled = true;
                }
            });
            if (this.areAllPlayerShipsDisabled()) this.triggerGameOver();
        } else if (this.lives !== 999) {
            this.lives--;
            if (this.lives <= 0) this.triggerGameOver();
        }
        this.updateHUD();
    }

    getCurrentStageElapsedFrames() {
        return this.timeElapsed - (this.currentStageIndex * this.stageDuration);
    }

    getStageBossSpawnFrame() {
        const isFinalStage = this.currentStageIndex >= 4;
        const spawnSecond = isFinalStage ? this.finalStageBossSpawnSecond : this.stageBossSpawnSecond;
        return spawnSecond * 60;
    }

    checkStageBossRequirement() {
        if (this.mode === 'practice' || this.stageBossTriggered) return;
        if (this.getCurrentStageElapsedFrames() < this.getStageBossSpawnFrame()) return;

        this.stageBossTriggered = true;
        this.spawnStageBossForCurrentStage();
    }

    getStageBossHp() {
        return 2 + this.currentStageIndex;
    }

    spawnStageBossForCurrentStage() {
        this.currentTarget = vocab.pickNextTarget();
        this.targetValue.innerHTML = `${this.currentTarget.emoji || ''} ${this.currentTarget.meaning}`;
        this.speakCurrentTargetWord();
        this.spawnBossSubmarine({
            hp: this.getStageBossHp(),
            bossLevel: this.currentStageIndex,
            isStageBoss: true,
            wordObj: this.currentTarget,
            message: `⚠️ ${this.difficultyStage} STAGE BOSS ⚠️`
        });
    }

    recordStageSubmarineKill() {
        if (this.mode === 'practice') return false;
        this.stageKillsThisStage++;
        if (this.levelPhase !== 'normal') {
            this.updateTargetPressureHUD();
            return false;
        }

        this.levelNormalKills = Math.min(this.levelNormalTarget, this.levelNormalKills + 1);
        if (this.levelNormalKills >= this.levelNormalTarget && this.getActiveNormalSubmarines().length === 0) {
            this.startLevelBossPhase();
            return true;
        }

        this.updateTargetPressureHUD();
        return false;
    }

    recordLevelBossDefeat() {
        if (this.mode === 'practice') return false;
        this.levelBossesDefeated = Math.min(this.levelBossTarget, this.levelBossesDefeated + 1);
        this.updateTargetPressureHUD();

        if (this.levelPhase === 'boss' && this.getActiveLevelBosses().length === 0) {
            this.advanceToNextLevel();
            return true;
        }

        return false;
    }

    updateTargetTimer() {
        const activeBoss = this.submarines.some(s => s.isBoss && !s.isDying);
        if (!this.currentTarget || activeBoss) {
            this.updateTargetPressureHUD();
            return;
        }

        if (this.targetTimer > 0) {
            this.targetTimer--;
            if (this.targetTimer <= 0) {
                this.applyTargetTimeoutPenalty();
            }
        }
        this.updateTargetPressureHUD();
    }

    applyTargetTimeoutPenalty() {
        this.currentCombo = 0;
        this.hideComboOverlay();

        if (this.mode === 'duo') {
            this.getActiveBattleships().forEach(ship => {
                if (!ship || ship.isDisabled) return;
                ship.score = Math.max(0, ship.score - 75);
                this.floatingTexts.push(new FloatingText(ship.x, ship.y - 48, "TARGET TIMEOUT -75", '#ff7b00', 0.85));
            });
        } else {
            this.score = Math.max(0, this.score - 75);
            this.floatingTexts.push(new FloatingText(this.battleship.x, this.battleship.y - 48, "TARGET TIMEOUT -75", '#ff7b00', 0.9));
        }

        sound.playDamage();
        this.triggerScreenShake(8);
        this.updateHUD();
        this.selectNewTarget();
    }

    updateTargetPressureHUD() {
        if (this.stageQuotaText) {
            if (this.levelPhase === 'boss') {
                this.stageQuotaText.innerText = `BOSSES ${this.levelBossesDefeated} / ${this.levelBossTarget}`;
                this.stageQuotaText.classList.toggle('complete', this.levelBossesDefeated >= this.levelBossTarget);
            } else {
                this.stageQuotaText.innerText = `KILLS ${this.levelNormalKills} / ${this.levelNormalTarget}`;
                this.stageQuotaText.classList.toggle('complete', this.levelNormalKills >= this.levelNormalTarget);
            }
        }

        if (this.targetTimerText) {
            const activeBoss = this.submarines.some(s => s.isBoss && !s.isDying);
            if (activeBoss) {
                this.targetTimerText.innerText = 'BOSS TARGET';
                this.targetTimerText.classList.remove('warning');
                return;
            }

            const secondsLeft = Math.max(0, Math.ceil(this.targetTimer / 60));
            this.targetTimerText.innerText = `TARGET ${secondsLeft}s`;
            this.targetTimerText.classList.toggle('warning', secondsLeft <= 6);
        }
    }

    // ==========================================================================
    // UPDATES & CORE PROCESSES
    // ==========================================================================
    loop(timestamp) {
        if (this.lastFrameTimestamp === null) {
            this.lastFrameTimestamp = timestamp;
        }

        if (this.state === 'playing') {
            const frameDeltaMs = Math.min(timestamp - this.lastFrameTimestamp, this.maxFrameDeltaMs);
            this.frameAccumulatorMs += frameDeltaMs;

            while (this.frameAccumulatorMs >= this.fixedStepMs && this.state === 'playing') {
                this.runFixedGameStep();
                this.frameAccumulatorMs -= this.fixedStepMs;
            }
        } else if (this.state === 'defeating') {
            const frameDeltaMs = Math.min(timestamp - this.lastFrameTimestamp, this.maxFrameDeltaMs);
            this.frameAccumulatorMs += frameDeltaMs;

            while (this.frameAccumulatorMs >= this.fixedStepMs && this.state === 'defeating') {
                this.updateDefeatSequence();
                this.frameAccumulatorMs -= this.fixedStepMs;
            }
        } else {
            this.frameAccumulatorMs = 0;
        }
        this.lastFrameTimestamp = timestamp;

        this.drawScene();

        // Screen shake class maintenance
        if (this.screenShakeTime > 0) {
            this.screenShakeTime--;
            if (this.screenShakeTime <= 0) {
                document.body.classList.remove('shake-screen');
            }
        }

        requestAnimationFrame(timestamp => this.loop(timestamp));
    }

    runFixedGameStep() {
        this.gameTime++;
        this.timeElapsed++;
        this.updatePhysics();
        this.handleCollisions();
        this.spawnSupplyCratesAndSubmarines();
    }

    updatePhysics() {
        this.updateTimerHUD();
        if (this.manualTargetChangeCooldown > 0) this.manualTargetChangeCooldown--;
        if (this.manualTargetChangeNoticeTimer > 0) this.manualTargetChangeNoticeTimer--;
        this.updateLevelUpEffect();
        this.updateTargetTimer();

        this.getActiveBattleships().forEach(ship => this.updateShipReload(ship));

        // 1. Update Battleship
        this.battleship.update(this.keys, this.touchDir, this.waterY, this.gameTime, this.mode === 'duo' ? 'primaryDuo' : 'solo');
        this.spawnBattleshipWake(this.battleship);
        if (this.secondBattleship) {
            this.secondBattleship.update(this.keys, 0, this.waterY, this.gameTime, 'secondary');
            this.spawnBattleshipWake(this.secondBattleship);
        }

        // 2. Power-up Timers countdown
        if (this.freezeTimer > 0) {
            this.freezeTimer--;
            if (this.freezeTimer <= 0) {
                this.puFreeze.classList.add('hidden');
                this.getActiveBattleships().forEach(ship => ship.frozenSubActive = false);
            } else {
                this.puFreezeVal.innerText = Math.ceil(this.freezeTimer / 60);
            }
        }

        if (this.empTimer > 0) {
            this.empTimer--;
            if (this.empTimer <= 0) {
                this.puEmp.classList.add('hidden');
                this.getActiveBattleships().forEach(ship => ship.empActive = false);
            } else {
                this.puEmpVal.innerText = Math.ceil(this.empTimer / 60);
            }
        }

        // 3. Scale progressive challenges
        this.updateDifficultyLevel();

        // 4. Update Depth Charge Bombs
        for (let i = this.bombs.length - 1; i >= 0; i--) {
            const bomb = this.bombs[i];
            const event = bomb.update(this.waterY);
            
            if (event === 'splash') {
                // Splash particles
                for (let k = 0; k < 12; k++) {
                    this.particles.push(new Particle(bomb.x, this.waterY, 'splash', '#a5f3fc'));
                }
            } else if (event === 'dead') {
                this.bombs.splice(i, 1);
            } else if (!bomb.exploded && bomb.inWater && Math.random() < 0.25) {
                // Bubbles rising from bomb
                this.particles.push(new Particle(bomb.x, bomb.y, 'bubble'));
            }
        }

        // 5. Update Submarines
        const isFrozen = this.freezeTimer > 0;
        const subSpeedMult = this.getDifficultySpeedMultiplier();

        for (let i = this.submarines.length - 1; i >= 0; i--) {
            const sub = this.submarines[i];
            sub.update(isFrozen ? 0.35 : subSpeedMult);

            // Spawn passive submarine bubble streams
            if (!sub.isDying && !isFrozen && Math.random() < 0.02) {
                const bubbleX = sub.speedX > 0 ? sub.x : sub.x + sub.width;
                this.particles.push(new Particle(bubbleX, sub.y + sub.height/2 + Math.random()*8 - 4, 'bubble'));
            }

            if (sub.isDying && !sub.isWrecked && Math.random() < 0.35) {
                const bubbleX = sub.x + sub.width * (0.25 + Math.random() * 0.5);
                const bubbleY = sub.y + sub.height * (0.2 + Math.random() * 0.6);
                this.particles.push(new Particle(bubbleX, bubbleY, 'bubble'));
                if (Math.random() < 0.45) {
                    this.particles.push(new Particle(bubbleX, bubbleY, 'smoke', '#2f241f'));
                }
            }
        }

        // 6. Update Missiles
        const missileSpeedMult = this.getDifficultySpeedMultiplier();
        for (let i = this.missiles.length - 1; i >= 0; i--) {
            const mis = this.missiles[i];
            const event = mis.update(missileSpeedMult);
            
            if (event === 'splash_surface') {
                // Water splash on surface hit
                for (let k = 0; k < 10; k++) {
                    this.particles.push(new Particle(mis.x, this.waterY, 'splash', '#e2e8f0'));
                }
                sound.playSplash();
                
                // Attack battleship check
                this.checkMissileBattleshipCollision(mis);
                this.missiles.splice(i, 1);
            } else if (Math.random() < 0.3) {
                // Smoke/Bubble trails from rocket engine
                this.particles.push(new Particle(mis.x, mis.y + mis.height, 'bubble'));
            }
        }

        // 7. Update Floating Supply Crates
        for (let i = this.crates.length - 1; i >= 0; i--) {
            const crate = this.crates[i];
            crate.update(this.waterY, this.gameTime);
            
            // Check box collections
            const collector = this.getActiveBattleships().find(ship => {
                const dx = Math.abs(ship.x - crate.x);
                const dy = Math.abs(ship.y + ship.height/2 - (crate.y + crate.height/2));
                return dx < (ship.width/2 + crate.width/2) && dy < (ship.height/2 + crate.height/2);
            });

            if (collector) {
                this.applyPowerup(crate.type, collector);
                this.crates.splice(i, 1);
            }
        }

        // 8. Update Particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.update();
            if (p.life <= 0) {
                this.particles.splice(i, 1);
            }
        }

        // 9. Update Floating Scores
        for (let i = this.floatingTexts.length - 1; i >= 0; i--) {
            const ft = this.floatingTexts[i];
            ft.update();
            if (ft.life <= 0) {
                this.floatingTexts.splice(i, 1);
            }
        }

        // 10. Update Enemy missile attack intervals
        const hasBoss = this.submarines.some(s => s.isBoss && !s.isDying);
        if (this.mode !== 'practice' && this.empTimer <= 0) {
            this.attackTimer++;
            
            const cooldownThreshold = this.getAttackCooldown();
            if (this.attackTimer >= cooldownThreshold) {
                this.triggerSubmarineAttack();
                this.attackTimer = 0;
            }
        }
    }

    updateLevelUpEffect() {
        if (!this.levelUpEffect) return;

        this.levelUpEffect.timer--;
        if (this.levelUpEffect.timer <= 0) {
            this.levelUpEffect = null;
        }
    }

    updateShipReload(ship) {
        if (ship.fireCooldown > 0) ship.fireCooldown--;
        if (ship.reloadTimer <= 0) return;

        ship.reloadTimer--;
        if (ship.reloadTimer % 12 === 0) {
            const fx = ship.x + (Math.random() * 44 - 22);
            const fy = ship.y - 8;
            this.particles.push(new Particle(fx, fy, 'spark', '#ffd000'));
            this.particles.push(new Particle(fx, fy, 'smoke', '#facc15'));
        }

        if (ship.reloadTimer <= 0) {
            ship.bombsRemaining = ship.maxBombsBeforeReload;
            this.floatingTexts.push(new FloatingText(ship.x, ship.y - 40, "AMMO READY!", '#33ff88', 0.95));
            this.speakCurrentTargetWord();
        }
        this.updateAmmoHUD();
    }

    spawnBattleshipWake(ship) {
        if (!ship || ship.isDisabled) return;

        const speedRatio = Math.min(1.35, Math.abs(ship.movementDeltaX) / ship.speed);
        if (speedRatio < 0.08) return;

        const direction = ship.movementDeltaX > 0 ? 1 : -1;
        const wakeX = ship.x - direction * (ship.width * 0.52);
        const wakeY = this.waterY + 4 + Math.random() * 6;
        const burstCount = Math.max(2, Math.round(2 + speedRatio * 4));

        this.particles.push(new Particle(
            wakeX - direction * 18,
            wakeY + 5,
            'foam',
            'rgba(224, 248, 255, 0.34)',
            { dir: direction, intensity: 0.75 + speedRatio * 0.45, stretch: 1.15 + speedRatio * 0.65 }
        ));

        for (let i = 0; i < burstCount; i++) {
            const offsetX = (Math.random() * 16 - 8) - direction * i * 4;
            this.particles.push(new Particle(
                wakeX + offsetX,
                wakeY + Math.random() * 6,
                'wake',
                i % 2 === 0 ? 'rgba(255, 255, 255, 0.82)' : 'rgba(125, 211, 252, 0.72)',
                {
                    dir: direction,
                    intensity: 0.55 + speedRatio * 0.65,
                    stretch: 0.95 + speedRatio * 0.45,
                    gravity: 0.018 + speedRatio * 0.03
                }
            ));
        }

        if (speedRatio > 0.65) {
            const sprayCount = Math.round(speedRatio * 2);
            for (let i = 0; i < sprayCount; i++) {
                this.particles.push(new Particle(
                    wakeX + (Math.random() * 18 - 9),
                    wakeY - 2,
                    'splash',
                    'rgba(236, 253, 255, 0.92)'
                ));
            }
        }
    }

    triggerSubmarineAttack() {
        if (this.submarines.length === 0) return;

        const livingAttackers = this.submarines.filter(s => !s.isDying);
        if (livingAttackers.length === 0) return;

        const attackerCount = Math.min(this.maxConcurrentSubmarineAttackers, livingAttackers.length);
        const shuffledSubs = [...livingAttackers].sort(() => Math.random() - 0.5);
        for (let i = 0; i < attackerCount; i++) {
            this.fireMissileFromSub(shuffledSubs[i]);
        }
    }

    fireMissileFromSub(sub) {
        const targetWaterY = this.waterY;
        const speedMult = this.getDifficultySpeedMultiplier();

        if (sub.isBoss) {
            // Boss launches double missiles or wave pattern
            const m1 = new Missile(sub.x + 30, sub.y, targetWaterY, true, speedMult);
            const m2 = new Missile(sub.x + sub.width - 30, sub.y, targetWaterY, true, speedMult);
            this.missiles.push(m1, m2);
        } else {
            const m = new Missile(sub.x + sub.width/2, sub.y, targetWaterY, false, speedMult);
            this.missiles.push(m);
        }
        sound.playLaser();
    }

    checkMissileBattleshipCollision(missile) {
        const hitShip = this.getActiveBattleships().find(ship => {
            if (ship.isDisabled) return false;
            const halfW = ship.width / 2;
            return missile.x >= ship.x - halfW - 5 && missile.x <= ship.x + halfW + 5;
        });

        if (hitShip) {
            // Hit!
            if (hitShip.shieldActive) {
                // Shield saves ship
                hitShip.shieldActive = false;
                this.puShield.classList.add('hidden');
                
                // Explode blue sparks
                for (let k = 0; k < 20; k++) {
                    this.particles.push(new Particle(hitShip.x, hitShip.y, 'spark', '#00f0ff'));
                }
                this.floatingTexts.push(new FloatingText(hitShip.x, hitShip.y - 30, "SHIELD BLOCKED!", '#00f0ff', 1.1));
                sound.playExplosion();
                this.triggerScreenShake(10);
            } else {
                // Lost life
                if (this.mode === 'duo') {
                    hitShip.lives--;
                    if (hitShip.lives <= 0) {
                        hitShip.lives = 0;
                        hitShip.isDisabled = true;
                        this.floatingTexts.push(new FloatingText(hitShip.x, hitShip.y - 48, `${hitShip.playerLabel} DISABLED!`, '#ff3333', 1.4));
                    }
                } else {
                    this.lives--;
                }
                this.triggerScreenShake(24);
                sound.playDamage();
                this.createBattleshipDamageEffect(hitShip, missile.x);
                
                this.floatingTexts.push(new FloatingText(hitShip.x, hitShip.y - 34, "-1 LIFE!", '#ff3333', 1.55));
                this.currentCombo = 0; // Break combo
                this.updateHUD();

                if ((this.mode === 'duo' && this.areAllPlayerShipsDisabled()) || (this.mode !== 'duo' && this.lives <= 0)) {
                    this.triggerGameOver();
                }
            }
        }
    }

    createBattleshipDamageEffect(ship, impactX = ship.x) {
        const impactSide = impactX >= ship.x ? 1 : -1;
        const centerX = ship.x + impactSide * ship.width * 0.18;
        const centerY = ship.y + ship.height * 0.28;
        const waterY = this.waterY + 5;

        this.particles.push(new Particle(centerX, centerY, 'shockwave', 'rgba(255, 255, 255, 0.88)', {
            size: 16,
            maxSize: 92,
            lineWidth: 5,
            decay: 0.05
        }));
        this.particles.push(new Particle(centerX, centerY, 'shockwave', 'rgba(14, 165, 233, 0.45)', {
            size: 8,
            maxSize: 128,
            lineWidth: 3,
            decay: 0.04
        }));

        for (let k = 0; k < 26; k++) {
            const fx = centerX + Math.random() * 28 - 14;
            const fy = centerY + Math.random() * 24 - 12;
            this.particles.push(new Particle(fx, fy, 'fire', k % 2 === 0 ? '#ff3b1f' : '#facc15'));
        }

        for (let k = 0; k < 22; k++) {
            const sx = centerX + Math.random() * 44 - 22;
            const sy = waterY + Math.random() * 8;
            this.particles.push(new Particle(sx, sy, 'splash', k % 2 === 0 ? 'rgba(236, 253, 255, 0.95)' : 'rgba(125, 211, 252, 0.82)'));
        }

        for (let k = 0; k < 8; k++) {
            this.particles.push(new Particle(
                centerX - impactSide * (18 + Math.random() * 30),
                waterY + 4 + Math.random() * 8,
                'foam',
                'rgba(224, 248, 255, 0.36)',
                { dir: impactSide, intensity: 0.8 + Math.random() * 0.5, stretch: 1.3 }
            ));
        }

        for (let k = 0; k < 12; k++) {
            this.particles.push(new Particle(
                centerX + Math.random() * 36 - 18,
                centerY + 12 + Math.random() * 12,
                'smoke',
                'rgba(45, 35, 33, 0.75)'
            ));
        }
    }

    startDefeatSequence(reason = 'defeat') {
        if (this.state === 'defeating' || this.state === 'gameover') return;

        this.state = 'defeating';
        this.defeatSequenceTimer = 0;
        this.defeatSequenceReason = reason;
        this.defeatedShips = this.getActiveBattleships().filter(ship => this.mode === 'duo' ? ship.lives <= 0 : ship === this.battleship);
        if (this.defeatedShips.length === 0 && this.battleship) {
            this.defeatedShips = [this.battleship];
        }
        this.defeatedShips.forEach(ship => {
            ship.isDisabled = true;
            ship.isDefeatSinking = true;
            ship.defeatBurnProgress = 0;
            ship.defeatSinkProgress = 0;
            ship.defeatTilt = (Math.random() > 0.5 ? 1 : -1) * (Math.PI / 2);
            ship.sinkStartY = ship.y;
            ship.sinkTargetY = this.canvas.height + ship.height * 1.8;
            this.createBattleshipDamageEffect(ship, ship.x);
        });
        sound.playDefeat();
        this.triggerScreenShake(35);
    }

    updateDefeatSequence() {
        this.defeatSequenceTimer++;
        const burnProgress = Math.min(1, this.defeatSequenceTimer / this.defeatBurnDuration);
        const sinkFrame = Math.max(0, this.defeatSequenceTimer - this.defeatBurnDuration);
        const sinkProgress = Math.min(1, sinkFrame / this.defeatSinkDuration);

        this.defeatedShips.forEach(ship => {
            ship.defeatBurnProgress = burnProgress;
            ship.defeatSinkProgress = sinkProgress;

            if (sinkProgress <= 0) {
                for (let i = 0; i < 5; i++) {
                    const fx = ship.x + (Math.random() - 0.5) * ship.width * 0.75;
                    const fy = ship.y + Math.random() * ship.height * 0.65;
                    this.particles.push(new Particle(fx, fy, 'fire', Math.random() > 0.45 ? '#ff3b1f' : '#facc15'));
                    if (Math.random() < 0.75) {
                        this.particles.push(new Particle(fx, fy, 'smoke', 'rgba(42, 31, 29, 0.82)'));
                    }
                }
            }

            if (sinkProgress <= 0 && this.defeatSequenceTimer % 8 === 0) {
                this.particles.push(new Particle(ship.x, ship.y + ship.height * 0.4, 'shockwave', 'rgba(255, 100, 20, 0.38)', {
                    size: 10,
                    maxSize: 70 + burnProgress * 45,
                    lineWidth: 3,
                    decay: 0.055
                }));
            }

            if (sinkProgress > 0) {
                ship.y = ship.sinkStartY + (ship.sinkTargetY - ship.sinkStartY) * (sinkProgress * sinkProgress);
                ship.x += Math.sin(this.defeatSequenceTimer * 0.08) * 0.45;
                if (this.defeatSequenceTimer % 5 === 0) {
                    this.particles.push(new Particle(ship.x + (Math.random() - 0.5) * ship.width, ship.y + ship.height * 0.25, 'bubble'));
                    this.particles.push(new Particle(ship.x + (Math.random() - 0.5) * ship.width, ship.y + ship.height * 0.15, 'smoke', 'rgba(42, 31, 29, 0.55)'));
                }
            }
        });

        this.updateNonGameplayEffects();

        if (this.defeatSequenceTimer >= this.defeatBurnDuration + this.defeatSinkDuration) {
            this.showGameOverScreen(this.defeatSequenceReason);
        }
    }

    updateNonGameplayEffects() {
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.update();
            if (p.life <= 0) {
                this.particles.splice(i, 1);
            }
        }

        for (let i = this.floatingTexts.length - 1; i >= 0; i--) {
            const ft = this.floatingTexts[i];
            ft.update();
            if (ft.life <= 0) {
                this.floatingTexts.splice(i, 1);
            }
        }
    }

    applyPowerup(type, ship = this.battleship) {
        sound.playPowerup();
        
        switch (type) {
            case 'repair':
                if (this.mode === 'duo') {
                    ship.lives = Math.min(3, ship.lives + 1);
                    ship.isDisabled = ship.lives <= 0;
                } else if (this.lives < 3 || this.mode === 'practice') {
                    this.lives++;
                }
                this.updateHUD();
                this.floatingTexts.push(new FloatingText(ship.x, ship.y - 30, "+1 LIFE!", '#33ff88', 1.2));
                // green sparks
                for (let k = 0; k < 12; k++) {
                    this.particles.push(new Particle(ship.x, ship.y, 'spark', '#33ff88'));
                }
                break;

            case 'shield':
                ship.shieldActive = true;
                this.puShield.classList.remove('hidden');
                this.floatingTexts.push(new FloatingText(ship.x, ship.y - 30, "SHIELD ACTIVE!", '#00e1ff', 1.2));
                break;

            case 'freeze':
                this.freezeTimer = 300; // 5 seconds at 60 FPS
                ship.frozenSubActive = true;
                this.puFreeze.classList.remove('hidden');
                this.floatingTexts.push(new FloatingText(ship.x, ship.y - 30, "SUBMARINES FROZEN!", '#38bdf8', 1.2));
                break;

            case 'emp':
                this.empTimer = 600; // 10 seconds at 60 FPS
                ship.empActive = true;
                this.puEmp.classList.remove('hidden');
                this.floatingTexts.push(new FloatingText(ship.x, ship.y - 30, "EMP ACTIVATE!", '#ffd000', 1.2));
                
                // Spark animations on all living subs
                this.submarines.forEach(sub => {
                    if (!sub.isDying) {
                        for(let k=0; k<8; k++) {
                            this.particles.push(new Particle(sub.x + sub.width/2, sub.y + sub.height/2, 'spark', '#ffd000'));
                        }
                    }
                });
                break;
        }
    }

    handleCollisions() {
        // Match active bombs against subs
        for (let i = this.bombs.length - 1; i >= 0; i--) {
            const bomb = this.bombs[i];
            if (bomb.exploded) continue; // expanding ring collision is handled separately or in-instant

            for (let k = 0; k < this.submarines.length; k++) {
                const sub = this.submarines[k];
                if (sub.isDying) continue;

                // Simple Box overlapping check for direct hit
                const subLeft = sub.x;
                const subRight = sub.x + sub.width;
                const subTop = sub.y;
                const subBottom = sub.y + sub.height;

                if (bomb.x >= subLeft && bomb.x <= subRight && bomb.y >= subTop && bomb.y <= subBottom) {
                    bomb.triggerExplosion();
                    this.resolveExplosionImpact(bomb.x, bomb.y, bomb.maxExplosionRadius, bomb.owner);
                    break;
                }
            }
        }
    }

    resolveExplosionImpact(expX, expY, expRad, ownerShip = this.battleship) {
        // Verify which submarines are overlapped by this explosion radius
        this.submarines.forEach(sub => {
            if (sub.isDying) return;

            const centerSubX = sub.x + sub.width / 2;
            const centerSubY = sub.y + sub.height / 2;

            // Distance calculation
            const dx = expX - centerSubX;
            const dy = expY - centerSubY;
            const dist = Math.sqrt(dx * dx + dy * dy);

            // Sub overlaps if distance < radius + bounds
            if (dist < (expRad + Math.max(sub.width/2, sub.height/2))) {
                this.processSubmarineHit(sub, ownerShip);
            }
        });
    }

    processSubmarineHit(sub, ownerShip = this.battleship) {
        const isTargetMatch = sub.word.word.toLowerCase() === this.currentTarget.word.toLowerCase();

        if (sub.isBoss) {
            // Boss Battle collision logic
            if (isTargetMatch) {
                sub.hp--;
                sub.triggerDamageFlash();
                this.triggerScreenShake(12);
                sound.playExplosion();

                this.updateBossHpDisplay(sub);
                
                // Add floating hit indicator
                this.floatingTexts.push(new FloatingText(sub.x + sub.width/2, sub.y - 10, "HIT! -1 HP", '#ff3c3c', 1.2));

                if (sub.hp <= 0) {
                    this.destroySubmarine(sub);
                    this.bossesDefeated++;
                    this.addPlayerScore(ownerShip, 800);
                    this.floatingTexts.push(new FloatingText(sub.x + sub.width/2, sub.y - 20, "BOSS DEFEATED! +800", '#ffd000', 1.8));
                    const levelAdvanced = this.recordLevelBossDefeat();
                    if (!levelAdvanced) {
                        const nextBoss = this.getActiveLevelBosses()[0];
                        if (nextBoss) {
                            this.updateBossHud(nextBoss);
                            this.selectNewTarget();
                        } else {
                            this.bossHud.classList.add('hidden');
                            this.selectNewTarget();
                        }
                    }
                    this.updateHUD();
                }
            } else {
                // Incorrect hit during boss fight
                this.applyPenalty(ownerShip);
            }
        } else {
            // Regular submarine logic
            if (isTargetMatch) {
                // Correct target hit
                this.destroySubmarine(sub);
                const levelAdvancedToBoss = this.recordStageSubmarineKill();
                
                this.correctMatches++;
                vocab.recordResult(sub.word.word, true);
                this.wordsLearned.add(sub.word.word);
                this.wordsMissed.delete(sub.word.word);

                // Score scaling with Combo multipliers
                this.currentCombo++;
                if (this.currentCombo > this.highestCombo) {
                    this.highestCombo = this.currentCombo;
                }

                let multiplier = 1;
                let comboMsg = "";
                let comboColor = '#ffffff';

                if (this.currentCombo >= 10) {
                    multiplier = 3.5;
                    comboMsg = "MEGA COMBO!";
                    comboColor = '#ff0077';
                } else if (this.currentCombo >= 5) {
                    multiplier = 2.0;
                    comboMsg = "TRIPLE HIT!";
                    comboColor = '#ffaa00';
                } else if (this.currentCombo >= 3) {
                    multiplier = 1.5;
                    comboMsg = "DOUBLE HIT!";
                    comboColor = '#00f0ff';
                }

                const scoreGained = Math.round(100 * multiplier);
                this.addPlayerScore(ownerShip, scoreGained);

                // Visual Floating points
                this.floatingTexts.push(new FloatingText(sub.x + sub.width/2, sub.y - 10, `+${scoreGained}`, comboColor, 1.1 + (multiplier * 0.1)));

                if (comboMsg !== "") {
                    this.showComboOverlay(comboMsg, this.currentCombo);
                }

                this.updateHUD();
                
                if (!levelAdvancedToBoss) {
                    this.selectNewTarget();
                }
            } else {
                // Incorrect Submarine Hit
                this.applyPenalty(ownerShip);
                // Flag incorrect learning state
                vocab.recordResult(sub.word.word, false);
                this.wordsMissed.add(sub.word.word);
                this.wordsLearned.delete(sub.word.word);
            }
        }
    }

    addPlayerScore(ship, amount) {
        if (this.mode === 'duo' && ship) {
            ship.score += amount;
            return;
        }
        this.score += amount;
    }

    getSurvivingScoreRecipients() {
        if (this.mode === 'duo') {
            return this.getActiveBattleships().filter(ship => !ship.isDisabled && ship.lives > 0);
        }
        return this.battleship && this.lives > 0 ? [this.battleship] : [];
    }

    awardScoreToSurvivors(amount, label, color) {
        const recipients = this.getSurvivingScoreRecipients();
        if (recipients.length === 0) return;

        recipients.forEach(ship => {
            this.addPlayerScore(ship, amount);
            this.floatingTexts.push(new FloatingText(ship.x, ship.y - 56, label, color, 1.05));
        });
        this.updateHUD();
    }

    awardSurvivalBonuses() {
        if (this.timeElapsed < this.nextSurvivalBonusAt) return;

        this.awardScoreToSurvivors(100, "SURVIVAL +100", '#33ff88');
        while (this.nextSurvivalBonusAt <= this.timeElapsed) {
            this.nextSurvivalBonusAt += this.survivalBonusInterval;
        }
    }

    awardFinalSurvivalBonus() {
        if (this.finalSurvivalBonusAwarded) return;

        this.finalSurvivalBonusAwarded = true;
        this.awardScoreToSurvivors(300, "FULL SURVIVAL +300", '#ffd000');
    }

    applyPenalty(ship = this.battleship) {
        this.currentCombo = 0;
        this.hideComboOverlay();
        
        // Small score penalty
        if (this.mode === 'duo' && ship) {
            ship.score = Math.max(0, ship.score - 50);
        } else {
            this.score = Math.max(0, this.score - 50);
        }
        this.updateHUD();
        this.floatingTexts.push(new FloatingText(ship.x, ship.y - 30, "COMBO RESET / -50", '#ff3c3c', 1.0));
        
        // Trigger small vibration
        this.triggerScreenShake(8);
        sound.playDamage();
    }

    destroySubmarine(sub) {
        if (sub.isDying) return;

        sub.isDying = true;
        sub.isWarning = false;
        sub.warningTimer = 0;

        const farSeabedY = this.canvas.height * 0.76;
        const nearSeabedY = this.canvas.height - sub.height * 0.65;
        const minWreckY = Math.min(nearSeabedY, Math.max(farSeabedY, sub.y + sub.height * 0.45));
        const maxWreckY = Math.max(minWreckY, nearSeabedY);
        sub.wreckTargetY = minWreckY + Math.random() * (maxWreckY - minWreckY);

        const depthRatio = Math.max(0, Math.min(1, (sub.wreckTargetY - farSeabedY) / (nearSeabedY - farSeabedY || 1)));
        const minScale = sub.isBoss ? 0.38 : 0.34;
        const maxScale = sub.isBoss ? 0.68 : 0.78;
        sub.wreckScale = minScale + depthRatio * (maxScale - minScale);
        sub.wreckTilt = (sub.facingRight ? 1 : -1) * (0.32 + Math.random() * 0.38);

        // Initial blast followed by a longer sinking animation.
        const numParticles = sub.isBoss ? 55 : 28;
        for (let k = 0; k < numParticles; k++) {
            const rx = sub.x + Math.random() * sub.width;
            const ry = sub.y + Math.random() * sub.height;
            this.particles.push(new Particle(rx, ry, 'fire', k % 2 === 0 ? '#ff6600' : '#ff2d00'));
            this.particles.push(new Particle(rx, ry, 'smoke', '#4b342a'));
            if (k % 3 === 0) {
                this.particles.push(new Particle(rx, ry, 'bubble'));
            }
        }
        
        sound.playSubmarineSinking();
        this.triggerScreenShake(sub.isBoss ? 25 : 10);
    }

    triggerVictoryFireworks() {
        for (let i = 0; i < 4; i++) {
            const fx = Math.random() * this.canvas.width;
            const fy = this.canvas.height * 0.2 + Math.random() * (this.canvas.height * 0.6);
            const colors = ['#00ff00', '#ffd000', '#ff00ff', '#00ffff', '#ff3300'];
            const color = colors[i % colors.length];

            setTimeout(() => {
                for (let k = 0; k < 30; k++) {
                    this.particles.push(new Particle(fx, fy, 'firework', color));
                }
                sound.playVictory();
            }, i * 200);
        }
    }

    showComboOverlay(msg, count) {
        this.comboDisplay.classList.remove('hidden');
        this.comboCountText.innerText = count;
        this.comboTitleText.innerText = msg;
        
        // Clear previous timeouts if applicable
        if (this.__comboTimeout) clearTimeout(this.__comboTimeout);
        this.__comboTimeout = setTimeout(() => {
            this.hideComboOverlay();
        }, 2200);
    }

    hideComboOverlay() {
        this.comboDisplay.classList.add('hidden');
    }

    updateBossHpDisplay(bossSub) {
        const percent = Math.max(0, (bossSub.hp / bossSub.maxHp) * 100);
        this.bossHpFill.style.width = percent + '%';
        this.bossHpText.innerText = `${bossSub.hp} / ${bossSub.maxHp} HP`;
    }

    updateBossHud(bossSub) {
        this.updateBossHpDisplay(bossSub);
    }

    getRoundScoreText() {
        if (this.mode === 'duo' && this.battleship && this.secondBattleship) {
            return `P1 ${this.battleship.score} / P2 ${this.secondBattleship.score}`;
        }
        return this.score;
    }

    getReloadProgress(ship = this.battleship) {
        if (!ship || ship.reloadTimer <= 0) return 1;
        return 1 - (ship.reloadTimer / ship.reloadDuration);
    }

    updateAmmoHUD() {
        if (!this.hudAmmo || !this.hudReloadFill || !this.hudReloadText) return;

        const ship = this.battleship;
        const isReloading = ship && ship.reloadTimer > 0;
        const reloadProgress = this.getReloadProgress(ship);
        this.hudAmmo.innerText = ship ? `${ship.bombsRemaining} / ${ship.maxBombsBeforeReload}` : '0 / 0';
        this.hudReloadFill.style.width = `${Math.round(reloadProgress * 100)}%`;

        if (isReloading) {
            this.hudReloadText.innerText = `P1 RELOAD ${Math.ceil(ship.reloadTimer / 60)}s`;
            this.hudReloadText.classList.add('reloading');
            this.hudReloadText.classList.remove('reload-ready');
        } else {
            this.hudReloadText.innerText = this.secondBattleship ? 'P1 READY' : 'READY';
            this.hudReloadText.classList.add('reload-ready');
            this.hudReloadText.classList.remove('reloading');
        }
    }

    spawnSupplyCratesAndSubmarines() {
        // 1. Maintain exactly five active normal submarines until the level's quota is spawned.
        if (this.mode === 'practice') {
            const activePracticeSubs = this.getActiveNormalSubmarines().length;
            for (let i = activePracticeSubs; i < 4; i++) {
                this.spawnSubmarine();
            }
        } else {
            this.maintainLevelNormalSubmarines();
        }
        this.guaranteeTargetSubmarinePresence();

        // 2. Periodic Floating crates spawn
        // Spawns roughly every 20-30 seconds
        if (Math.random() < 0.0006) {
            const rx = Math.random() * (this.canvas.width - 80) + 40;
            this.crates.push(new Crate(rx, this.waterY));
            this.floatingTexts.push(new FloatingText(rx, this.waterY - 30, "SUPPLY DROP INBOUND", '#33ff88', 1.0));
        }
    }

    updateHUD() {
        const isDuo = this.mode === 'duo' && this.battleship && this.secondBattleship;
        const mainShip = isDuo ? this.secondBattleship : null;
        const sideShip = isDuo ? this.battleship : null;
        const mainScore = isDuo ? mainShip.score : this.score;
        const mainLives = isDuo ? mainShip.lives : this.lives;

        if (this.hudScoreLabel) this.hudScoreLabel.innerText = isDuo ? 'P2 SCORE' : 'SCORE';
        if (this.hudLivesLabel) this.hudLivesLabel.innerText = isDuo ? 'P2 LIVES' : 'LIVES';
        this.hudScore.classList.toggle('neon-pink', isDuo);
        this.hudScore.classList.toggle('neon-blue', !isDuo);

        // Pad score value with zeros
        this.hudScore.innerText = String(mainScore).padStart(5, '0');
        
        // Render heart elements
        let heartsStr = '';
        if (mainLives === 999) {
            heartsStr = '♾️ PRACTICE';
        } else {
            heartsStr = this.renderHearts(mainLives);
        }
        this.hudHearts.innerText = heartsStr;

        if (this.hudP2Stats) {
            this.hudP2Stats.classList.toggle('hidden', !isDuo);
        }
        if (isDuo) {
            if (this.hudP2ScoreLabel) this.hudP2ScoreLabel.innerText = 'P1 SCORE';
            if (this.hudP2LivesLabel) this.hudP2LivesLabel.innerText = 'P1 LIVES';
            this.hudP2Score.classList.add('neon-blue');
            this.hudP2Score.classList.remove('neon-pink');
            this.hudP2Score.innerText = String(sideShip.score).padStart(5, '0');
            this.hudP2Hearts.innerText = this.renderHearts(sideShip.lives);
        }

        this.hudDiff.innerText = `L${this.currentStageIndex + 1} ${this.difficultyStage}`;
        this.updateTimerHUD();
        this.hudAccuracy.innerText = `${vocab.getAccuracy()}%`;
        this.updateTargetPressureHUD();
        this.updateAmmoHUD();
    }

    renderHearts(lives) {
        let heartsStr = '';
        for (let i = 0; i < 3; i++) {
            heartsStr += i < lives ? '❤️' : '🖤';
        }
        return heartsStr;
    }

    updateTimerHUD() {
        this.hudTime.innerText = this.formatTime(this.timeElapsed);
    }

    triggerGameOver(reason = 'defeat') {
        if (this.state === 'gameover' || this.state === 'defeating') return;

        if (reason === 'defeat') {
            this.startDefeatSequence(reason);
            return;
        }

        this.showGameOverScreen(reason);
    }

    showGameOverScreen(reason = 'defeat') {
        if (this.state === 'gameover') return;

        this.state = 'gameover';
        if (reason !== 'defeat') {
            sound.playDefeat();
        }
        this.saveHighScore();
        this.savePlayHistory();

        // Populate game over stats overlay
        document.getElementById('gameover-title').innerText = reason === 'timeup' ? 'TIME UP!' : 'DEFEATED!';
        document.getElementById('go-score').innerText = this.getRoundScoreText();
        document.getElementById('go-best-score').innerText = this.mode === 'duo' ? 'N/A' : this.getHighScore();
        document.getElementById('go-combo').innerText = this.highestCombo;
        document.getElementById('go-accuracy').innerText = `${vocab.getAccuracy()}%`;
        document.getElementById('go-correct').innerText = this.correctMatches;
        document.getElementById('go-incorrect').innerText = this.incorrectMatches;
        document.getElementById('go-bosses').innerText = this.bossesDefeated;

        // Populate learned words panel
        const reviewBox = document.getElementById('learned-words-list');
        reviewBox.innerHTML = '';
        
        if (this.wordsLearned.size === 0 && this.wordsMissed.size === 0) {
            reviewBox.innerHTML = '<span style="color:#64748b; font-size: 0.85rem;">No words matching reviews in this round.</span>';
        } else {
            // Mastered Tags
            this.wordsLearned.forEach(w => {
                const tag = document.createElement('span');
                tag.className = 'learned-word-tag mastered';
                tag.innerHTML = `🟢 ${w}`;
                reviewBox.appendChild(tag);
            });
            // Missed Tags
            this.wordsMissed.forEach(w => {
                const tag = document.createElement('span');
                tag.className = 'learned-word-tag missed';
                tag.innerHTML = `🔴 ${w}`;
                reviewBox.appendChild(tag);
            });
        }

        this.renderPlayHistory();

        // Toggle modals display
        this.modalGameover.classList.remove('hidden');
        this.focusCurrentMenuDefault();
    }

    renderPlayHistory() {
        const historyBox = document.getElementById('play-history-list');
        const history = this.getPlayHistory();
        historyBox.innerHTML = '';

        if (this.mode === 'duo') {
            historyBox.innerHTML = '<span style="color:#64748b; font-size: 0.85rem;">2 Player Mode does not save play history.</span>';
            return;
        }

        if (history.length === 0) {
            historyBox.innerHTML = '<span style="color:#64748b; font-size: 0.85rem;">No play history yet.</span>';
            return;
        }

        history.forEach((entry, idx) => {
            historyBox.appendChild(this.createHistoryRow(entry, idx));
        });
    }

    renderStartPlayHistory() {
        const historyBox = document.getElementById('start-play-history-list');
        if (!historyBox) return;

        const history = this.getPlayHistory();
        historyBox.innerHTML = '';

        if (this.mode === 'duo') {
            historyBox.innerHTML = '<span style="color:#64748b; font-size: 0.85rem;">2 Player Mode does not save play history.</span>';
            return;
        }

        if (history.length === 0) {
            historyBox.innerHTML = '<span style="color:#64748b; font-size: 0.85rem;">No play history yet.</span>';
            return;
        }

        history.forEach((entry, idx) => {
            historyBox.appendChild(this.createHistoryRow(entry, idx));
        });
    }

    createHistoryRow(entry, idx) {
        const row = document.createElement('div');
        row.className = 'history-row';
        const date = new Date(entry.playedAt);
        const dateText = Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString();
        const survivalText = this.formatTime(entry.survivalTime ?? entry.duration ?? 0);
        const gradeText = entry.grade === 'toeic'
            ? 'TOEIC'
            : (entry.grade ? `G${entry.grade}` : vocab.getSourceShortLabel(this.selectedGrade));
        row.innerHTML = `
            <span class="history-rank">#${idx + 1}</span>
            <span class="history-date">${dateText} • ${gradeText} • SURV ${survivalText} • ${entry.accuracy}% ACC • ${entry.correct} OK</span>
            <span class="history-score">${entry.score}</span>
        `;
        return row;
    }

    // ==========================================================================
    // RENDERINGS & GRAPHICS DRAWING
    // ==========================================================================
    drawScene() {
        // Clear frame buffer
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // 1. Draw Water depths gradients background
        const depthGrad = this.ctx.createLinearGradient(0, this.waterY, 0, this.canvas.height);
        
        // Freeze overlay gradient adjustment
        if (this.freezeTimer > 0) {
            depthGrad.addColorStop(0, '#103e68');
            depthGrad.addColorStop(0.3, '#0b2b4e');
            depthGrad.addColorStop(1, '#051427');
        } else {
            depthGrad.addColorStop(0, '#1d5587');
            depthGrad.addColorStop(0.3, '#0d2d54');
            depthGrad.addColorStop(1, '#051424');
        }
        this.ctx.fillStyle = depthGrad;
        this.ctx.fillRect(0, this.waterY, this.canvas.width, this.canvas.height);
        this.drawSeabedDepth();

        // Sky drawing
        const skyGrad = this.ctx.createLinearGradient(0, 0, 0, this.waterY);
        skyGrad.addColorStop(0, '#0c1b35');
        skyGrad.addColorStop(1, '#1b3f74');
        this.ctx.fillStyle = skyGrad;
        this.ctx.fillRect(0, 0, this.canvas.width, this.waterY);

        // Draw twinkling stars
        this.ctx.save();
        this.stars.forEach(star => {
            const x = star.x * this.canvas.width;
            const y = star.y * (this.waterY - 15) + 5; // keep inside sky area with padding
            star.phase += star.speed;
            const alpha = 0.25 + Math.sin(star.phase) * 0.65;
            const size = star.size * (0.85 + Math.sin(star.phase) * 0.15);
            
            this.ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
            this.ctx.shadowColor = '#ffffff';
            this.ctx.shadowBlur = size * 1.5;
            this.ctx.beginPath();
            this.ctx.arc(x, y, size, 0, Math.PI * 2);
            this.ctx.fill();
        });
        this.ctx.restore();

        // Draw background bubbles rising randomly
        if (Math.random() < 0.05) {
            const rx = Math.random() * this.canvas.width;
            const ry = this.waterY + Math.random() * (this.canvas.height - this.waterY);
            this.particles.push(new Particle(rx, ry, 'bubble'));
        }

        // 2. Draw Supply Crates
        this.crates.forEach(c => c.draw(this.ctx));

        // 3. Draw Submarines
        const isFrozen = this.freezeTimer > 0;
        [...this.submarines]
            .sort((a, b) => (a.y + a.height) - (b.y + b.height))
            .forEach(s => s.draw(this.ctx, isFrozen));

        // 4. Draw Depth charge bombs
        this.bombs.forEach(b => b.draw(this.ctx));

        // 5. Draw Missiles
        this.missiles.forEach(m => m.draw(this.ctx));

        // 6. Draw Battleship
        if (this.battleship) {
            this.battleship.draw(this.ctx, this.getReloadProgress(this.battleship), this.battleship.bombsRemaining, this.battleship.maxBombsBeforeReload);
        }
        if (this.secondBattleship) {
            this.secondBattleship.draw(this.ctx, this.getReloadProgress(this.secondBattleship), this.secondBattleship.bombsRemaining, this.secondBattleship.maxBombsBeforeReload);
        }

        // 7. Draw Waves at surface boundary
        this.drawWaterWaves();

        // 8. Draw Particle FX overlays
        this.particles.forEach(p => p.draw(this.ctx));

        // 9. Draw Floating scores
        this.floatingTexts.forEach(ft => ft.draw(this.ctx));

        // 10. Draw level-up celebration overlay
        this.drawLevelUpOverlay();

        // 11. Frost Vignette if Freeze active
        if (isFrozen) {
            this.drawFrostVignette();
        }
    }

    drawLevelUpOverlay() {
        if (!this.levelUpEffect) return;

        const ctx = this.ctx;
        const effect = this.levelUpEffect;
        const progress = 1 - (effect.timer / effect.duration);
        const fadeIn = Math.min(1, progress / 0.18);
        const fadeOut = Math.min(1, effect.timer / 32);
        const alpha = Math.min(fadeIn, fadeOut);
        const pulse = 1 + Math.sin(progress * Math.PI * 6) * 0.04;
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height * 0.34;

        ctx.save();
        ctx.globalAlpha = alpha;

        const flashGrad = ctx.createRadialGradient(cx, cy, 40, cx, cy, this.canvas.width * 0.62);
        flashGrad.addColorStop(0, 'rgba(250, 204, 21, 0.24)');
        flashGrad.addColorStop(0.35, 'rgba(34, 211, 238, 0.16)');
        flashGrad.addColorStop(1, 'rgba(2, 6, 23, 0)');
        ctx.fillStyle = flashGrad;
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        ctx.translate(cx, cy);
        ctx.scale(pulse, pulse);

        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = 'rgba(34, 211, 238, 0.95)';
        ctx.shadowBlur = 28;
        ctx.lineWidth = 8;
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.92)';
        ctx.fillStyle = '#f8fafc';
        ctx.font = "900 64px 'Fredoka', sans-serif";
        ctx.strokeText('LEVEL UP!', 0, -18);
        ctx.fillText('LEVEL UP!', 0, -18);

        ctx.shadowColor = 'rgba(250, 204, 21, 0.9)';
        ctx.shadowBlur = 18;
        ctx.fillStyle = '#facc15';
        ctx.font = "800 30px 'Fredoka', sans-serif";
        ctx.fillText(`LEVEL ${effect.levelNumber} - ${effect.stageName}`, 0, 42);

        ctx.restore();
    }

    drawSeabedDepth() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        const seabedTop = h * 0.78;
        const time = this.gameTime * 0.015;

        ctx.save();

        // Soft shafts of light fade into the deep water for extra depth.
        ctx.globalAlpha = 0.16;
        for (let i = 0; i < 7; i++) {
            const x = ((i * 190 + time * 28) % (w + 260)) - 130;
            const rayGrad = ctx.createLinearGradient(x, this.waterY, x + 95, seabedTop);
            rayGrad.addColorStop(0, 'rgba(125, 211, 252, 0.22)');
            rayGrad.addColorStop(1, 'rgba(125, 211, 252, 0)');
            ctx.fillStyle = rayGrad;
            ctx.beginPath();
            ctx.moveTo(x, this.waterY);
            ctx.lineTo(x + 70, this.waterY);
            ctx.lineTo(x + 210, seabedTop);
            ctx.lineTo(x + 40, seabedTop);
            ctx.closePath();
            ctx.fill();
        }
        ctx.globalAlpha = 1;

        // Far sand shelf with a slow parallax wave shape.
        const farGrad = ctx.createLinearGradient(0, seabedTop - 30, 0, h);
        farGrad.addColorStop(0, 'rgba(30, 64, 92, 0.55)');
        farGrad.addColorStop(1, 'rgba(6, 24, 38, 0.95)');
        ctx.fillStyle = farGrad;
        ctx.beginPath();
        ctx.moveTo(0, h);
        ctx.lineTo(0, seabedTop + Math.sin(time) * 6);
        for (let x = 0; x <= w + 80; x += 80) {
            const y = seabedTop + Math.sin(time + x * 0.012) * 10 + Math.cos(x * 0.018) * 8;
            ctx.quadraticCurveTo(x + 40, y - 12, x + 80, y);
        }
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fill();

        // Foreground dune gives the bottom a stronger 3D edge.
        const frontTop = h * 0.88;
        const frontGrad = ctx.createLinearGradient(0, frontTop - 25, 0, h);
        frontGrad.addColorStop(0, '#1f4f64');
        frontGrad.addColorStop(0.5, '#12384c');
        frontGrad.addColorStop(1, '#071d2e');
        ctx.fillStyle = frontGrad;
        ctx.beginPath();
        ctx.moveTo(0, h);
        ctx.lineTo(0, frontTop);
        for (let x = 0; x <= w + 100; x += 100) {
            const y = frontTop + Math.sin(time * 1.4 + x * 0.01) * 12;
            ctx.quadraticCurveTo(x + 50, y - 16, x + 100, y);
        }
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fill();

        this.drawSeabedProps(seabedTop, frontTop);
        ctx.restore();
    }

    drawSeabedProps(seabedTop, frontTop) {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const time = this.gameTime * 0.04;
        const rockColors = ['#0f2f44', '#173f55', '#254f5f', '#0b2638'];

        // Back layer rocks are dimmer and smaller.
        for (let i = 0; i < 14; i++) {
            const x = (i * 137) % (w + 120) - 40;
            const y = seabedTop + 28 + (i % 4) * 13;
            const rw = 28 + (i % 5) * 9;
            const rh = 12 + (i % 3) * 7;
            ctx.fillStyle = rockColors[i % rockColors.length];
            ctx.globalAlpha = 0.55;
            ctx.beginPath();
            ctx.ellipse(x, y, rw, rh, 0, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.globalAlpha = 1;
        for (let i = 0; i < 18; i++) {
            const baseX = (i * 103) % (w + 160) - 60;
            const baseY = frontTop + 24 + (i % 4) * 18;
            const sway = Math.sin(time + i) * 5;

            // Sea grass ribbons.
            ctx.strokeStyle = i % 2 === 0 ? '#1faa75' : '#2dd4bf';
            ctx.lineWidth = 3;
            ctx.globalAlpha = 0.72;
            for (let blade = 0; blade < 3; blade++) {
                const bx = baseX + blade * 7;
                ctx.beginPath();
                ctx.moveTo(bx, baseY);
                ctx.quadraticCurveTo(bx + sway, baseY - 24, bx + sway * 1.6, baseY - 48 - blade * 6);
                ctx.stroke();
            }

            // Coral clusters and foreground rocks.
            if (i % 3 === 0) {
                ctx.strokeStyle = i % 2 === 0 ? '#f472b6' : '#fb7185';
                ctx.lineWidth = 4;
                ctx.globalAlpha = 0.78;
                const coralX = baseX + 24;
                const coralY = baseY + 5;
                ctx.beginPath();
                ctx.moveTo(coralX, coralY);
                ctx.lineTo(coralX, coralY - 35);
                ctx.moveTo(coralX, coralY - 18);
                ctx.lineTo(coralX - 13, coralY - 29);
                ctx.moveTo(coralX, coralY - 23);
                ctx.lineTo(coralX + 14, coralY - 36);
                ctx.stroke();
            }

            ctx.globalAlpha = 0.95;
            ctx.fillStyle = rockColors[(i + 1) % rockColors.length];
            ctx.beginPath();
            ctx.ellipse(baseX + 12, baseY + 8, 24 + (i % 4) * 5, 10 + (i % 3) * 4, 0, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.globalAlpha = 1;
    }

    drawWaterWaves() {
        this.ctx.save();
        this.ctx.fillStyle = 'rgba(142, 197, 214, 0.4)'; // light wave reflection
        this.ctx.beginPath();
        this.ctx.moveTo(0, this.waterY);
        
        const waveCount = 12;
        const widthPerWave = this.canvas.width / waveCount;
        
        // Double overlapping wave loops
        for (let i = 0; i <= waveCount; i++) {
            const px = i * widthPerWave;
            // Bobbing sine formula offset by gameTime
            const py = this.waterY + Math.sin(this.gameTime * 0.05 + i) * 6;
            this.ctx.lineTo(px, py);
        }
        
        this.ctx.lineTo(this.canvas.width, this.canvas.height);
        this.ctx.lineTo(0, this.canvas.height);
        this.ctx.closePath();
        this.ctx.fill();

        // Crisp surface wave outline
        this.ctx.strokeStyle = '#8ec5d6';
        this.ctx.lineWidth = 4.0;
        this.ctx.beginPath();
        this.ctx.moveTo(0, this.waterY);
        for (let i = 0; i <= waveCount; i++) {
            const px = i * widthPerWave;
            const py = this.waterY + Math.sin(this.gameTime * 0.05 + i) * 6;
            this.ctx.lineTo(px, py);
        }
        this.ctx.stroke();
        
        this.ctx.restore();
    }

    drawFrostVignette() {
        this.ctx.save();
        
        // Blue glowing border representing ice freeze
        const gradient = this.ctx.createRadialGradient(
            this.canvas.width / 2, this.canvas.height / 2, this.canvas.width * 0.35,
            this.canvas.width / 2, this.canvas.height / 2, this.canvas.width * 0.65
        );
        
        gradient.addColorStop(0, 'rgba(56, 189, 248, 0)');
        gradient.addColorStop(0.8, 'rgba(56, 189, 248, 0.12)');
        gradient.addColorStop(1, 'rgba(56, 189, 248, 0.35)');

        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.restore();
    }
}

// Instantiate and start engine
window.addEventListener('load', () => {
    const game = new GameEngine();
    game.init();
});
