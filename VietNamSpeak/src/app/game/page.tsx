import { IpaAdventure } from "@/components/ipa-adventure";
import { Badge } from "@/components/ui/badge";

export default function GamePage() {
  return (
    <div className="space-y-6">
      <section>
        <Badge>Main Game</Badge>
        <h1 className="mt-3 text-4xl font-black tracking-tight">IPA Adventure</h1>
        <p className="mt-2 max-w-2xl text-[var(--muted-foreground)]">
          Match IPA, Vietnamese pronunciation hints, English words, and meanings to reinforce the full loop.
        </p>
      </section>
      <IpaAdventure />
    </div>
  );
}
