"use client";

import { useCallback, useRef, useState } from "react";

export function useAudioRecorder() {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [message, setMessage] = useState("Record your voice to replay it.");

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setMessage("This browser cannot record audio.");
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      setAudioUrl(URL.createObjectURL(blob));
      stream.getTracks().forEach((track) => track.stop());
      setMessage("Recording saved. Replay and compare with the target.");
    };

    recorder.start();
    setIsRecording(true);
    setMessage("Recording... keep the final consonant clear.");
  }, []);

  const stop = useCallback(() => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setIsRecording(false);
  }, []);

  const replay = useCallback(() => {
    if (!audioUrl) {
      setMessage("No recording yet.");
      return;
    }
    new Audio(audioUrl).play();
  }, [audioUrl]);

  return { audioUrl, isRecording, message, start, stop, replay };
}
