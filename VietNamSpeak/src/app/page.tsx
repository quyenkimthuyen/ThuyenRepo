import Link from "next/link";

import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { WORDS } from "@/data/words";
import { demoStats } from "@/lib/learning/stats";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <Card className="space-y-5 overflow-hidden bg-gradient-to-br from-blue-600 to-indigo-700 text-white">
          <Badge className="w-fit bg-white/20 text-white">
            English Word {"->"} IPA {"->"} Vietnamese Hint
          </Badge>
          <div className="space-y-3">
            <h1 className="max-w-2xl text-4xl font-black tracking-tight sm:text-5xl">
              Pronounce new English words before you hear them.
            </h1>
            <p className="max-w-2xl text-lg text-blue-50">
              Learn IPA through Vietnamese-friendly sound patterns, then listen, repeat, and reinforce
              with games.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" variant="success">
              <Link href="/learn/school">Start with school</Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <Link href="/game">Play IPA Adventure</Link>
            </Button>
          </div>
        </Card>
        <Card className="space-y-4">
          <CardTitle>Today&apos;s Mission</CardTitle>
          <p className="text-[var(--muted-foreground)]">
            Complete 20 mixed activities: listening, IPA recognition, pronunciation, and quiz.
          </p>
          <Progress value={45} />
          <Button asChild className="w-full">
            <Link href="/daily">Open Daily Challenge</Link>
          </Button>
        </Card>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
        <StatCard label="Streak" value={`${demoStats.streak} days`} detail="Keep the fire alive" />
        <StatCard label="XP" value={demoStats.xp} detail="Level up with practice" />
        <StatCard label="Level" value={demoStats.level} detail="Pronunciation explorer" />
        <StatCard label="Words" value={demoStats.wordsLearned} detail="Seed words learned" />
        <StatCard label="Accuracy" value={`${demoStats.accuracy}%`} detail="Speaking quality" />
        <StatCard label="Reviews" value={demoStats.reviewsDue} detail="Due today" />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {WORDS.slice(0, 3).map((word) => (
          <Card key={word.id} className="space-y-3">
            <Badge>{word.level}</Badge>
            <CardTitle>{word.word}</CardTitle>
            <p className="font-mono text-lg">{word.ipa}</p>
            <p className="text-2xl font-black text-blue-600 dark:text-blue-300">{word.vnPronunciation}</p>
            <p className="text-sm text-[var(--muted-foreground)]">{word.meaningVi}</p>
            <Button asChild variant="secondary" className="w-full">
              <Link href={`/learn/${word.id}`}>Practice</Link>
            </Button>
          </Card>
        ))}
      </section>
    </div>
  );
}
