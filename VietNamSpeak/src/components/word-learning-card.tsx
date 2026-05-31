"use client";

import { Heart, Mic, Pause, Play, RotateCcw, Volume2 } from "lucide-react";

import { IpaVisualizer } from "@/components/ipa-visualizer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type { Word } from "@/data/words";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { useSpeechRecognition } from "@/hooks/use-speech-recognition";
import { useSpeechSynthesis } from "@/hooks/use-speech-synthesis";

export function WordLearningCard({ word }: { word: Word }) {
  const speech = useSpeechSynthesis();
  const recorder = useAudioRecorder();
  const recognition = useSpeechRecognition();

  function toggleRecord() {
    if (recorder.isRecording) {
      recorder.stop();
      recognition.listen(word.word);
    } else {
      void recorder.start();
    }
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
      <Card className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Badge>{word.topic}</Badge>
            <h1 className="mt-3 text-5xl font-black tracking-tight">{word.word}</h1>
          </div>
          <Button variant="ghost" aria-label="Favorite word">
            <Heart className="h-5 w-5" />
          </Button>
        </div>
        <div className="rounded-3xl bg-[var(--background)] p-5">
          <p className="text-sm font-bold text-[var(--muted-foreground)]">IPA</p>
          <p className="font-mono text-3xl font-black">{word.ipa}</p>
        </div>
        <div className="rounded-3xl bg-blue-50 p-5 text-blue-950 dark:bg-blue-950 dark:text-blue-50">
          <p className="text-sm font-bold opacity-75">Vietnamese Pronunciation</p>
          <p className="text-4xl font-black">{word.vnPronunciation}</p>
        </div>
        <div>
          <CardTitle>Meaning</CardTitle>
          <p className="text-lg">{word.meaningVi}</p>
          <p className="mt-3 font-semibold">{word.exampleEn}</p>
          <p className="text-[var(--muted-foreground)]">{word.exampleVi}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Button onClick={() => speech.speak(word.word)} aria-label={`Listen to ${word.word}`}>
            <Volume2 className="h-4 w-4" /> Listen
          </Button>
          <Button onClick={() => speech.speak(word.word, 0.65)} variant="secondary">
            <Play className="h-4 w-4" /> Slow Audio
          </Button>
          <Button onClick={toggleRecord} variant={recorder.isRecording ? "success" : "secondary"}>
            {recorder.isRecording ? <Pause className="h-4 w-4" /> : <Mic className="h-4 w-4" />} Record
          </Button>
          <Button onClick={recorder.replay} variant="secondary">
            <RotateCcw className="h-4 w-4" /> Replay
          </Button>
        </div>
        <p className="rounded-2xl bg-[var(--muted)] p-4 text-sm font-semibold">
          {recorder.message} {recognition.transcript ? `You said: "${recognition.transcript}".` : ""}{" "}
          {recognition.message} Target: {word.vnPronunciation}. {speech.message}
        </p>
      </Card>
      <IpaVisualizer ipa={word.ipa} />
    </div>
  );
}
