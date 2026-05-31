"use client";

import { Volume2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { WORDS, type Word } from "@/data/words";
import { useSpeechSynthesis } from "@/hooks/use-speech-synthesis";

type GameQuestion = {
  id: string;
  mode: string;
  title: string;
  prompt: string;
  correct: string;
  options: string[];
  word: Word;
};

const GAME_WORDS = WORDS.filter((word) => word.level !== "advanced").slice(0, 48);

function uniqueOptions(correct: string, distractors: string[]) {
  return [correct, ...distractors.filter((item) => item !== correct)]
    .filter((item, index, arr) => arr.indexOf(item) === index)
    .slice(0, 4);
}

function rotateOptions(options: string[], seed: number) {
  if (options.length === 0) return options;
  const offset = seed % options.length;
  return [...options.slice(offset), ...options.slice(0, offset)];
}

function nearbyWords(word: Word, index: number) {
  return [1, 2, 3, 5, 8]
    .map((offset) => GAME_WORDS[(index + offset) % GAME_WORDS.length])
    .filter((item): item is Word => Boolean(item) && item.id !== word.id);
}

function buildQuestions(): GameQuestion[] {
  return GAME_WORDS.flatMap((word, index) => {
    const nearby = nearbyWords(word, index);

    const questions: GameQuestion[] = [
      {
        id: `${word.id}-ipa-to-vn`,
        mode: "IPA -> Đọc kiểu Việt",
        title: "Nhìn IPA, chọn cách đọc kiểu Việt",
        prompt: word.ipa,
        correct: word.vnPronunciation,
        options: uniqueOptions(word.vnPronunciation, nearby.map((item) => item.vnPronunciation)),
        word
      },
      {
        id: `${word.id}-word-to-ipa`,
        mode: "Từ -> IPA",
        title: "Nhìn từ, chọn IPA đúng",
        prompt: word.word,
        correct: word.ipa,
        options: uniqueOptions(word.ipa, nearby.map((item) => item.ipa)),
        word
      },
      {
        id: `${word.id}-meaning-to-word`,
        mode: "Nghĩa -> Từ",
        title: "Nhìn nghĩa tiếng Việt, chọn từ tiếng Anh",
        prompt: word.meaningVi,
        correct: word.word,
        options: uniqueOptions(word.word, nearby.map((item) => item.word)),
        word
      },
      {
        id: `${word.id}-vn-to-word`,
        mode: "Đọc kiểu Việt -> Từ",
        title: "Nhìn cách đọc kiểu Việt, chọn từ",
        prompt: word.vnPronunciation,
        correct: word.word,
        options: uniqueOptions(word.word, nearby.map((item) => item.word)),
        word
      },
      {
        id: `${word.id}-avoid-to-word`,
        mode: "Sửa lỗi",
        title: "Lỗi này thuộc từ nào?",
        prompt: word.avoid,
        correct: word.word,
        options: uniqueOptions(word.word, nearby.map((item) => item.word)),
        word
      }
    ];

    return questions.map((question, questionIndex) => ({
      ...question,
      options: rotateOptions(question.options, index + questionIndex)
    }));
  });
}

export function IpaAdventure() {
  const [current, setCurrent] = useState(0);
  const [xp, setXp] = useState(0);
  const [streak, setStreak] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [message, setMessage] = useState("Chọn đáp án đúng để nhận XP.");
  const { message: speechMessage, speak, supported: speechSupported } = useSpeechSynthesis();
  const questions = useMemo(() => buildQuestions(), []);
  const level = questions[current];
  const bossChain = useMemo(() => GAME_WORDS.slice(current, current + 8), [current]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      speak(level.word.word, 0.85);
    }, 250);

    return () => window.clearTimeout(timer);
  }, [level.id, level.word.word, speak]);

  function answer(option: string) {
    if (option === level.correct) {
      const bonus = streak >= 4 ? 5 : 0;
      setXp((value) => value + 10 + bonus);
      setStreak((value) => value + 1);
      setAnswered((value) => value + 1);
      setMessage(`Đúng! +${10 + bonus} XP. ${level.word.word} đọc là ${level.word.vnPronunciation}.`);
      setCurrent((value) => (value + 1) % questions.length);
    } else {
      setStreak(0);
      setAnswered((value) => value + 1);
      setMessage(`Chưa đúng. Đáp án là "${level.correct}". Mẹo: ${level.word.mouthTip}`);
    }
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_0.85fr]">
      <Card className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Badge>{level.mode}</Badge>
          <Badge>{xp} XP</Badge>
          <Badge>{streak} streak</Badge>
        </div>
        <div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>{level.title}</CardTitle>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => speak(level.word.word, 0.85)}
              aria-label={`Nghe từ ${level.word.word}`}
            >
              <Volume2 className="h-4 w-4" /> Nghe từ
            </Button>
          </div>
          <p className="mt-4 rounded-3xl bg-[var(--background)] p-8 text-center text-3xl font-black sm:text-4xl">
            {level.prompt}
          </p>
          <p className="mt-2 text-center text-sm font-bold text-[var(--muted-foreground)]">
            Audio: {level.word.word} ·{" "}
            {speechSupported ? speechMessage : "Trình duyệt không hỗ trợ phát audio."}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {level.options.map((option) => (
            <Button
              key={option}
              variant="secondary"
              className="min-h-16 whitespace-normal py-4 text-lg"
              onClick={() => answer(option)}
            >
              {option}
            </Button>
          ))}
        </div>
        <p className="rounded-2xl bg-[var(--muted)] p-4 font-bold">{message}</p>
        <div className="grid gap-3 rounded-3xl border border-[var(--border)] p-4 sm:grid-cols-3">
          <div>
            <p className="text-xs font-bold text-[var(--muted-foreground)]">Đã làm</p>
            <p className="text-2xl font-black">{answered}</p>
          </div>
          <div>
            <p className="text-xs font-bold text-[var(--muted-foreground)]">Tổng câu hỏi</p>
            <p className="text-2xl font-black">{questions.length}</p>
          </div>
          <div>
            <p className="text-xs font-bold text-[var(--muted-foreground)]">Từ hiện tại</p>
            <p className="text-2xl font-black">{level.word.word}</p>
          </div>
        </div>
      </Card>
      <Card className="space-y-4">
        <Badge>Chuỗi từ luyện nhanh</Badge>
        <CardTitle>8 từ tiếp theo</CardTitle>
        <div className="space-y-3">
          {bossChain.map((word) => (
            <div key={word.id} className="rounded-2xl border border-[var(--border)] p-3">
              <div className="font-black">{word.word}</div>
              <div className="font-mono text-sm">{word.ipa}</div>
              <div className="text-sm font-bold text-blue-600 dark:text-blue-300">{word.vnPronunciation}</div>
              <div className="text-sm text-[var(--muted-foreground)]">{word.meaningVi}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
