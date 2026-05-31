"use client";

import { useCallback, useMemo, useState } from "react";

export function useSpeechSynthesis() {
  const [message, setMessage] = useState("Ready to listen.");
  const supported = useMemo(
    () => typeof window !== "undefined" && "speechSynthesis" in window,
    []
  );

  const speak = useCallback(
    (text: string, rate = 1) => {
      if (!supported) {
        setMessage("This browser does not support speech synthesis.");
        return;
      }

      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      utterance.rate = rate;
      utterance.pitch = 1;
      utterance.onend = () => setMessage("Listening complete. Now repeat it.");
      window.speechSynthesis.speak(utterance);
      setMessage(rate < 1 ? "Playing slow audio..." : "Playing audio...");
    },
    [supported]
  );

  return { supported, speak, message };
}
