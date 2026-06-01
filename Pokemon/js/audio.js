export class GameAudio {
  constructor(state) {
    this.state = state;
    this.context = null;
    this.voice = null;
    this.refreshVoice();
    window.speechSynthesis?.addEventListener?.("voiceschanged", () => this.refreshVoice());
  }

  refreshVoice() {
    const voices = window.speechSynthesis?.getVoices?.() || [];
    this.voice =
      voices.find((voice) => voice.lang.toLowerCase().startsWith("en-us")) ||
      voices.find((voice) => voice.lang.toLowerCase().startsWith("en")) ||
      null;
  }

  speak(word) {
    if (!this.state.settings.speech || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = "en-US";
    utterance.rate = 0.78;
    utterance.pitch = 1.08;
    if (this.voice) utterance.voice = this.voice;
    window.speechSynthesis.speak(utterance);
    this.state.pronunciationPlays += 1;
  }

  play(name) {
    if (!this.state.settings.sfx) return;
    const patterns = {
      correct: [660, 880],
      wrong: [210, 160],
      capture: [523, 659, 784, 1046],
      treasure: [784, 988, 1175],
      level: [523, 659, 784, 1046, 1318],
      achievement: [880, 1175, 1567],
      step: [190]
    };
    this.sequence(patterns[name] || patterns.correct);
  }

  sequence(frequencies) {
    const context = this.getContext();
    if (!context) return;
    const now = context.currentTime;
    frequencies.forEach((frequency, index) => {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.001, now + index * 0.1);
      gain.gain.exponentialRampToValueAtTime(0.12, now + index * 0.1 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, now + index * 0.1 + 0.09);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(now + index * 0.1);
      oscillator.stop(now + index * 0.1 + 0.11);
    });
  }

  startAmbience() {
    if (!this.state.settings.sfx) return;
    const context = this.getContext();
    if (!context || this.ambience) return;

    const gain = context.createGain();
    gain.gain.value = 0.018;
    const oscillator = context.createOscillator();
    oscillator.type = "triangle";
    oscillator.frequency.value = 196;
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    this.ambience = { oscillator, gain };
  }

  getContext() {
    if (this.context) return this.context;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return null;
    this.context = new AudioContext();
    return this.context;
  }
}
