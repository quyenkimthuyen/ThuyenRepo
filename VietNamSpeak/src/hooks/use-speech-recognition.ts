"use client";

import { useCallback, useMemo, useState } from "react";

type SpeechRecognitionResultEvent = {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
};

type BrowserSpeechRecognition = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onerror: (() => void) | null;
  start: () => void;
};

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

export function useSpeechRecognition() {
  const [transcript, setTranscript] = useState("");
  const [message, setMessage] = useState("Speech recognition is optional in this MVP.");
  const Recognition = useMemo(
    () =>
      typeof window === "undefined"
        ? undefined
        : window.SpeechRecognition ?? window.webkitSpeechRecognition,
    []
  );
  const supported = Boolean(Recognition);

  const listen = useCallback(
    (targetWord: string) => {
      if (!Recognition) {
        setMessage("This browser does not support speech recognition.");
        return;
      }

      const recognition = new Recognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onresult = (event) => {
        const heard = event.results[0]?.[0]?.transcript ?? "";
        setTranscript(heard);
        const close = heard.toLowerCase().includes(targetWord.toLowerCase());
        setMessage(close ? "Great match. Keep practicing vowel length." : "Close, but compare IPA and final sounds.");
      };
      recognition.onerror = () => setMessage("Speech recognition could not analyze that attempt.");
      recognition.start();
      setMessage("Listening for your pronunciation...");
    },
    [Recognition]
  );

  return { supported, transcript, message, listen };
}
