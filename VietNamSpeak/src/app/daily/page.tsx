import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { WORDS } from "@/data/words";

const activities = ["Listening", "IPA Recognition", "Pronunciation", "Quiz", "Game"];

export default function DailyChallengePage() {
  const dailyWords = Array.from({ length: 20 }, (_, index) => WORDS[index % WORDS.length]);

  return (
    <div className="space-y-6">
      <section>
        <Badge>Daily Challenge</Badge>
        <h1 className="mt-3 text-4xl font-black tracking-tight">20 words for today</h1>
        <p className="mt-2 max-w-2xl text-[var(--muted-foreground)]">
          Earn XP, coins, streak credit, and badges by mixing recognition and speaking tasks.
        </p>
      </section>
      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <Card className="space-y-4">
          <CardTitle>Rewards</CardTitle>
          <div className="grid grid-cols-2 gap-3">
            {["+200 XP", "+40 coins", "Streak +1", "Badge progress"].map((reward) => (
              <div key={reward} className="rounded-2xl bg-[var(--background)] p-4 font-black">
                {reward}
              </div>
            ))}
          </div>
          <Button asChild className="w-full">
            <Link href="/game">Start Game Round</Link>
          </Button>
        </Card>
        <Card className="space-y-4">
          <CardTitle>Activities</CardTitle>
          <div className="grid gap-3 sm:grid-cols-2">
            {dailyWords.slice(0, 10).map((word, index) => (
              <Link
                key={`${word.id}-${index}`}
                href={`/learn/${word.id}`}
                className="rounded-2xl border border-[var(--border)] p-4 transition hover:bg-[var(--muted)]"
              >
                <div className="text-xs font-bold text-[var(--muted-foreground)]">
                  {activities[index % activities.length]}
                </div>
                <div className="font-black">{word.word}</div>
                <div className="font-mono text-sm">{word.ipa}</div>
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
