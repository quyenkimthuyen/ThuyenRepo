import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { PRONUNCIATION_RULES } from "@/data/pronunciation-rules";

export default function RulesPage() {
  return (
    <div className="space-y-6">
      <section>
        <Badge>Rule Library</Badge>
        <h1 className="mt-3 text-4xl font-black tracking-tight">Decode spelling patterns</h1>
        <p className="mt-2 max-w-2xl text-[var(--muted-foreground)]">
          Learners compare English spelling with IPA so they stop reading words letter by letter.
        </p>
      </section>
      <div className="grid gap-4 md:grid-cols-2">
        {PRONUNCIATION_RULES.map((rule) => (
          <Card key={rule.id} className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <Badge>Rule: {rule.pattern}</Badge>
                <CardTitle className="mt-3">{rule.ipa}</CardTitle>
              </div>
              <span className="rounded-2xl bg-blue-100 px-4 py-2 text-xl font-black text-blue-700 dark:bg-blue-950 dark:text-blue-200">
                {rule.vietnameseHint}
              </span>
            </div>
            <p className="text-[var(--muted-foreground)]">{rule.explanation}</p>
            <div className="flex flex-wrap gap-2">
              {rule.examples.map((example) => (
                <span key={example} className="rounded-full bg-[var(--muted)] px-3 py-1 text-sm font-bold">
                  {example}
                </span>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
