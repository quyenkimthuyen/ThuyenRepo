"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { WORDS } from "@/data/words";

const levels = [
  { id: 1, title: "IPA -> Vietnamese Hint", prompt: "/skuːl/", correct: "skuul", options: ["skuul", "sukul", "skun", "sờ-kun"] },
  { id: 2, title: "Word -> IPA", prompt: "school", correct: "/skuːl/", options: ["/skuːl/", "/sʌkul/", "/skuːn/", "/səkuːl/"] },
  { id: 3, title: "Meaning -> Word", prompt: "trường học", correct: "school", options: ["school", "green", "language", "enough"] },
  { id: 4, title: "Audio -> IPA", prompt: "Listen: beautiful", correct: "/ˈbjuːtəfəl/", options: ["/ˈbjuːtəfəl/", "/ˈbɪtɪfʊl/", "/ˈbluːfəl/", "/ˈbʌtər/"] }
];

export function IpaAdventure() {
  const [current, setCurrent] = useState(0);
  const [xp, setXp] = useState(0);
  const [message, setMessage] = useState("Choose the best answer.");
  const level = levels[current];
  const bossChain = useMemo(() => WORDS.slice(0, 4), []);

  function answer(option: string) {
    if (option === level.correct) {
      setXp((value) => value + 10);
      setMessage("+10 XP. Correct!");
      setCurrent((value) => (value + 1) % levels.length);
    } else {
      setMessage(`Try again. Target: ${level.correct}`);
    }
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_0.85fr]">
      <Card className="space-y-5">
        <div className="flex items-center justify-between gap-3">
          <Badge>Level {level.id}</Badge>
          <Badge>{xp} XP</Badge>
        </div>
        <div>
          <CardTitle>{level.title}</CardTitle>
          <p className="mt-4 rounded-3xl bg-[var(--background)] p-8 text-center text-4xl font-black">
            {level.prompt}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {level.options.map((option) => (
            <Button key={option} variant="secondary" className="h-16 text-lg" onClick={() => answer(option)}>
              {option}
            </Button>
          ))}
        </div>
        <p className="rounded-2xl bg-[var(--muted)] p-4 font-bold">{message}</p>
      </Card>
      <Card className="space-y-4">
        <Badge>Boss Battle Preview</Badge>
        <CardTitle>60-second chain</CardTitle>
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
