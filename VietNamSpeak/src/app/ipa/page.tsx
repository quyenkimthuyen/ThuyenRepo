import { IpaVisualizer } from "@/components/ipa-visualizer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { IPA_SOUNDS } from "@/data/ipa-sounds";

export default function IpaCenterPage() {
  return (
    <div className="space-y-6">
      <section>
        <Badge>IPA Learning Center</Badge>
        <h1 className="mt-3 text-4xl font-black tracking-tight">Master each sound one by one</h1>
        <p className="mt-2 max-w-2xl text-[var(--muted-foreground)]">
          Vietnamese hints make IPA symbols less abstract, then practice turns each sound into a habit.
        </p>
      </section>
      <div className="grid gap-4 md:grid-cols-2">
        {IPA_SOUNDS.map((sound, index) => (
          <Card key={sound.id} className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <Badge>{sound.level}</Badge>
                <CardTitle className="mt-3 font-mono text-4xl">{sound.symbol}</CardTitle>
                <p className="text-lg font-black text-blue-600 dark:text-blue-300">
                  {sound.vietnameseHint}
                </p>
              </div>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-black text-emerald-700">
                {70 + index * 4}%
              </span>
            </div>
            <div className="space-y-2">
              {sound.examples.map((example) => (
                <div key={example.word} className="flex justify-between rounded-2xl bg-[var(--background)] p-3">
                  <span className="font-bold">{example.word}</span>
                  <span className="font-black text-blue-600 dark:text-blue-300">{example.hint}</span>
                </div>
              ))}
            </div>
            <Progress value={70 + index * 4} />
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
              {["Listen", "Slow", "Record", "Replay", "Save"].map((action) => (
                <Button key={action} variant="secondary" size="sm">
                  {action}
                </Button>
              ))}
            </div>
          </Card>
        ))}
      </div>
      <IpaVisualizer ipa="/skuːl/" />
    </div>
  );
}
