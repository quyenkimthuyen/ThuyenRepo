import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { convertIpaToVietnamese } from "@/lib/ipa/engine";

export function IpaVisualizer({ ipa }: { ipa: string }) {
  const result = convertIpaToVietnamese(ipa);

  return (
    <Card className="space-y-4">
      <div>
        <CardTitle>IPA Visualizer</CardTitle>
        <p className="text-sm text-[var(--muted-foreground)]">
          Clickable-style mapping from IPA symbols to familiar Vietnamese hints.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {result.tokens
          .filter((token) => token.ipa !== "ˈ")
          .map((token) => (
            <div
              key={`${token.ipa}-${token.index}`}
              className="rounded-2xl border border-[var(--border)] bg-[var(--background)] px-4 py-3 text-center"
            >
              <div className="font-mono text-lg font-black">{token.ipa}</div>
              <div className="text-sm font-bold text-blue-600 dark:text-blue-300">{token.vietnamese}</div>
            </div>
          ))}
      </div>
      <Badge>Result: {result.hint}</Badge>
    </Card>
  );
}
