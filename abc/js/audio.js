let preferredVoice = null;

function pickVietnameseVoice() {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  preferredVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("vi")) || voices[0] || null;
}

if ("speechSynthesis" in window) {
  pickVietnameseVoice();
  window.speechSynthesis.onvoiceschanged = pickVietnameseVoice;
}

function speak(text, enabled = true) {
  if (!enabled || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "vi-VN";
  utterance.rate = 0.82;
  utterance.pitch = 1.18;
  if (preferredVoice) utterance.voice = preferredVoice;
  window.speechSynthesis.speak(utterance);
}

window.AudioGuide = { speak };
