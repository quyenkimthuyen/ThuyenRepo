"use client";

import { ArrowRight, Mic, Pause, Play, RotateCcw, Volume2 } from "lucide-react";
import Link from "next/link";

import { IpaVisualizer } from "@/components/ipa-visualizer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type { Word } from "@/data/words";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { useSpeechRecognition } from "@/hooks/use-speech-recognition";
import { useSpeechSynthesis } from "@/hooks/use-speech-synthesis";

export function WordLearningCard({ word, nextWordId }: { word: Word; nextWordId: string }) {
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
    <div className="space-y-5">
      <Card className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Badge>{word.topic}</Badge>
          <Button asChild variant="secondary">
            <Link href="/learn">Kho từ</Link>
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-3xl bg-[var(--background)] p-5">
            <p className="text-sm font-black text-[var(--muted-foreground)]">1. Từ tiếng Anh</p>
            <h1 className="mt-2 text-5xl font-black tracking-tight">{word.word}</h1>
            <p className="mt-2 text-lg font-bold">{word.meaningVi}</p>
          </div>

          <div className="rounded-3xl bg-blue-50 p-5 text-blue-950 dark:bg-blue-950 dark:text-blue-50">
            <p className="text-sm font-black opacity-70">2. Cách đọc kiểu Việt</p>
            <p className="mt-2 text-4xl font-black">{word.vnPronunciation}</p>
            <p className="mt-2 font-mono text-lg opacity-80">{word.ipa}</p>
          </div>

          <div className="rounded-3xl bg-amber-50 p-5 text-amber-950 dark:bg-amber-950 dark:text-amber-50">
            <p className="text-sm font-black opacity-70">3. Mẹo nói đúng</p>
            <p className="mt-2 font-bold">{word.mouthTip}</p>
            <p className="mt-3 text-sm">
              <b>Tránh:</b> {word.avoid}
            </p>
          </div>
        </div>

        <div className="rounded-3xl border border-[var(--border)] p-4">
          <p className="text-sm font-black text-[var(--muted-foreground)]">Câu ví dụ</p>
          <p className="mt-2 text-xl font-bold">{word.exampleEn}</p>
          <p className="text-[var(--muted-foreground)]">{word.exampleVi}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Button onClick={() => speech.speak(word.word)} aria-label={`Listen to ${word.word}`}>
            <Volume2 className="h-4 w-4" /> Nghe từ
          </Button>
          <Button onClick={() => speech.speak(word.word, 0.65)} variant="secondary">
            <Play className="h-4 w-4" /> Nghe chậm
          </Button>
          <Button onClick={() => speech.speak(word.exampleEn, 0.85)} variant="secondary">
            <Volume2 className="h-4 w-4" /> Nghe câu
          </Button>
          <Button onClick={toggleRecord} variant={recorder.isRecording ? "success" : "secondary"}>
            {recorder.isRecording ? <Pause className="h-4 w-4" /> : <Mic className="h-4 w-4" />} Ghi âm
          </Button>
          <Button onClick={recorder.replay} variant="secondary">
            <RotateCcw className="h-4 w-4" /> Nghe lại
          </Button>
        </div>

        <div className="rounded-3xl bg-[var(--muted)] p-4 text-sm font-semibold">
          <p>{recorder.message}</p>
          <p>{speech.message}</p>
          <p>
            {recognition.transcript ? `Bạn vừa nói: "${recognition.transcript}". ` : ""}
            {recognition.supported
              ? recognition.message
              : "Nếu trình duyệt không nhận giọng nói, bạn vẫn có thể ghi âm và tự nghe lại."}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href={`/learn/${nextWordId}`}>
              Từ tiếp theo <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/game">Ôn bằng trò chơi</Link>
          </Button>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
        <IpaVisualizer ipa={word.ipa} />
        <Card className="space-y-3">
          <CardTitle>Công thức học nhanh</CardTitle>
          <ol className="space-y-3 text-[var(--muted-foreground)]">
            <li>
              <b className="text-[var(--foreground)]">Nghe chậm 2 lần</b> để bắt âm chính.
            </li>
            <li>
              <b className="text-[var(--foreground)]">Đọc gợi ý Việt</b> nhưng cố không thêm âm
              “ờ” sau phụ âm cuối.
            </li>
            <li>
              <b className="text-[var(--foreground)]">Ghi âm 1 lần</b>, nghe lại, sửa đúng lỗi trong
              ô “Tránh”.
            </li>
          </ol>
        </Card>
      </div>
    </div>
  );
}
