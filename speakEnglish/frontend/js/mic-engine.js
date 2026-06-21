/**
 * Mic pipeline — VAD năng lượng + FSM utterance (một luồng, ổn định)
 */

import {
  extractSpokenWord,
  createVadState,
  updateEnergyVad,
  canStartProcessing,
  buildUtteranceBlob,
  PROCESS_COOLDOWN_MS,
  MIN_SPEECH_MS,
} from './core.js';

export const MIC_PHASE = {
  OFF: 'off',
  READY: 'ready',
  HEARING: 'hearing',
  PROCESSING: 'processing',
  COOLDOWN: 'cooldown',
  SAMPLE: 'sample',
};

/**
 * @typedef {object} MicEngineOptions
 * @property {number} hangoverMs — im lặng bao lâu thì kết thúc câu
 * @property {number} [cooldownMs]
 * @property {(phase: string, label?: string) => void} [onPhaseChange]
 * @property {(rms: number, pct: number) => void} [onLevel]
 * @property {(payload: { spoken: string, getBlob: (mime: string) => Blob|null }) => Promise<void>} [onUtteranceComplete]
 * @property {() => void} [onSpeechStart]
 */

export class MicEngine {
  /** @param {MicEngineOptions} options */
  constructor(options) {
    this.hangoverMs = options.hangoverMs;
    this.cooldownMs = options.cooldownMs ?? PROCESS_COOLDOWN_MS;
    this.onPhaseChange = options.onPhaseChange;
    this.onLevel = options.onLevel;
    this.onUtteranceComplete = options.onUtteranceComplete;
    this.onSpeechStart = options.onSpeechStart;

    this.phase = MIC_PHASE.OFF;
    this.paused = false;
    this.vad = createVadState();
    this.transcriptFinal = '';
    this.transcriptInterim = '';
    this.utteranceChunks = [];
    this.capturing = false;
    this.lastProcessAt = 0;
    this.cooldownTimer = null;
    this._processing = false;
  }

  setHangoverMs(ms) {
    this.hangoverMs = ms;
  }

  start() {
    this.resetSession();
    this.setPhase(MIC_PHASE.READY, 'Sẵn sàng thu âm');
  }

  stop() {
    this.clearCooldown();
    this.phase = MIC_PHASE.OFF;
    this.paused = false;
    this.capturing = false;
    this._processing = false;
    this.onPhaseChange?.(MIC_PHASE.OFF, 'Micro tắt');
  }

  pause() {
    this.paused = true;
    this.capturing = false;
    this.vad = createVadState();
  }

  resume() {
    this.paused = false;
    this.setPhase(MIC_PHASE.READY, 'Sẵn sàng thu âm');
  }

  resetSession() {
    this.transcriptFinal = '';
    this.transcriptInterim = '';
    this.utteranceChunks = [];
    this.capturing = false;
    this.vad = createVadState();
    this._processing = false;
  }

  clearTranscript() {
    this.transcriptFinal = '';
    this.transcriptInterim = '';
  }

  /** @param {Blob[]} preRoll — vài chunk trước khi phát hiện giọng nói */
  beginCapture(preRoll = []) {
    this.capturing = true;
    this.utteranceChunks = preRoll.filter((c) => c?.size > 0);
  }

  pushAudioChunk(blob) {
    if (this.capturing && blob?.size > 0) {
      this.utteranceChunks.push(blob);
    }
  }

  pushTranscript(finalPart, interimPart) {
    if (finalPart) this.transcriptFinal += `${finalPart} `;
    if (interimPart !== undefined) this.transcriptInterim = interimPart;
  }

  getSpokenWord() {
    return extractSpokenWord(this.transcriptFinal, this.transcriptInterim);
  }

  /** Gọi mỗi animation frame với RMS từ AnalyserNode */
  tick(rms, nowMs = Date.now()) {
    if (this.paused || this.phase === MIC_PHASE.SAMPLE) {
      this.onLevel?.(rms, 0);
      return;
    }
    if (this._processing || this.phase === MIC_PHASE.PROCESSING) {
      this.onLevel?.(rms, Math.min(100, rms * 400));
      return;
    }

    const vad = updateEnergyVad(this.vad, rms, nowMs, { hangoverMs: this.hangoverMs });
    this.vad = vad;

    if (vad.speechStarted) {
      this.capturing = true;
      this.utteranceChunks = [];
      this.onSpeechStart?.();
      this.setPhase(MIC_PHASE.HEARING, 'Đang nghe bạn nói...');
    }

    if (vad.isSpeech) {
      if (this.phase !== MIC_PHASE.HEARING) {
        this.setPhase(MIC_PHASE.HEARING, 'Đang nghe bạn nói...');
      }
    } else if (vad.speaking && vad.silentFor > 0) {
      const left = Math.max(0, this.hangoverMs - vad.silentFor);
      if (left > 0 && left <= this.hangoverMs) {
        this.onPhaseChange?.(MIC_PHASE.HEARING, `Chờ ${(left / 1000).toFixed(1)}s...`);
      }
    } else if (!vad.speaking && this.phase === MIC_PHASE.HEARING) {
      this.setPhase(MIC_PHASE.READY, 'Sẵn sàng thu âm');
    } else if (this.phase === MIC_PHASE.READY || this.phase === MIC_PHASE.COOLDOWN) {
      this.onPhaseChange?.(this.phase, 'Sẵn sàng thu âm');
    }

    if (vad.speechEnded) {
      this.handleSpeechEnd(nowMs, vad);
    }

    this.onLevel?.(rms, Math.min(100, rms * 400));
  }

  async handleSpeechEnd(nowMs, vad) {
    if (this._processing) return;

    const duration = vad.lastSpeechAt - vad.speechStartAt;
    if (duration < MIN_SPEECH_MS) {
      this.endCapture();
      return;
    }

    if (!canStartProcessing(this.lastProcessAt, nowMs, this.cooldownMs)) {
      this.endCapture();
      return;
    }

    const spoken = this.getSpokenWord();
    const hasAudio = this.utteranceChunks.length > 0;
    if (!spoken && !hasAudio) {
      this.endCapture();
      return;
    }

    this._processing = true;
    this.lastProcessAt = nowMs;
    this.setPhase(MIC_PHASE.PROCESSING, 'Đang xử lý...');

    const chunks = [...this.utteranceChunks];
    const payload = {
      spoken,
      getBlob: (mimeType) => buildUtteranceBlob(chunks, mimeType),
    };

    try {
      await this.onUtteranceComplete?.(payload);
    } finally {
      this._processing = false;
      this.endCapture();
      this.enterCooldown();
    }
  }

  endCapture() {
    this.capturing = false;
    this.utteranceChunks = [];
    if (this.vad.speaking) {
      this.vad = createVadState();
    }
  }

  enterCooldown() {
    this.clearCooldown();
    this.setPhase(MIC_PHASE.COOLDOWN, 'Sẵn sàng thu âm');
    this.cooldownTimer = setTimeout(() => {
      this.cooldownTimer = null;
      if (!this.paused && this.phase === MIC_PHASE.COOLDOWN) {
        this.setPhase(MIC_PHASE.READY, 'Sẵn sàng thu âm');
      }
    }, this.cooldownMs);
  }

  clearCooldown() {
    if (this.cooldownTimer) {
      clearTimeout(this.cooldownTimer);
      this.cooldownTimer = null;
    }
  }

  getBlob(mimeType) {
    return buildUtteranceBlob(this.utteranceChunks, mimeType);
  }

  setPhase(phase, label) {
    this.phase = phase;
    if (label) this.onPhaseChange?.(phase, label);
  }

  setSampleMode(active) {
    if (active) {
      this.pause();
      this.setPhase(MIC_PHASE.SAMPLE, 'Đang phát mẫu...');
    }
  }
}
