"use client";

import { Volume2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { IpaSound } from "@/data/ipa-sounds";
import { useSpeechSynthesis } from "@/hooks/use-speech-synthesis";

type IpaSoundGroup = {
  group: IpaSound["group"];
  label: string;
  sounds: IpaSound[];
};

export function IpaSoundTable({ groups }: { groups: IpaSoundGroup[] }) {
  const speech = useSpeechSynthesis();
  const [activeSoundId, setActiveSoundId] = useState<string | null>(null);

  function playSound(sound: IpaSound) {
    const exampleWord = sound.examples[0]?.word ?? sound.symbol;
    setActiveSoundId(sound.id);
    speech.speak(exampleWord, 0.8);
  }

  return (
    <Card className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Badge>Bấm vào ô để nghe</Badge>
          <CardTitle className="mt-2">Bảng tóm gọn IPA</CardTitle>
          <p className="mt-2 max-w-2xl text-sm text-[var(--muted-foreground)]">
            Mỗi ô phát âm từ ví dụ đại diện cho âm đó. Học nhanh bằng cách nhìn ký hiệu, đọc gợi ý
            kiểu Việt, rồi bấm nghe.
          </p>
        </div>
        <p className="rounded-2xl bg-[var(--muted)] px-4 py-2 text-sm font-bold">
          {speech.supported ? speech.message : "Trình duyệt không hỗ trợ phát âm tự động."}
        </p>
      </div>

      <div className="space-y-5">
        {groups.map((group) => (
          <section key={group.group} className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-black">{group.label}</h3>
              <span className="text-xs font-bold text-[var(--muted-foreground)]">
                {group.sounds.length} âm
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6">
              {group.sounds.map((sound) => {
                const example = sound.examples[0];
                const isActive = activeSoundId === sound.id;

                return (
                  <button
                    key={sound.id}
                    type="button"
                    onClick={() => playSound(sound)}
                    className={[
                      "group rounded-2xl border p-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--ring)]",
                      isActive
                        ? "border-blue-500 bg-blue-50 text-blue-950 shadow-sm dark:bg-blue-950 dark:text-blue-50"
                        : "border-[var(--border)] bg-[var(--background)] hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950"
                    ].join(" ")}
                    aria-label={`Nghe âm ${sound.symbol} qua từ ${example?.word ?? sound.symbol}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-mono text-2xl font-black">{sound.symbol}</span>
                      <Volume2 className="mt-1 h-4 w-4 text-blue-600 opacity-70 transition group-hover:opacity-100 dark:text-blue-300" />
                    </div>
                    <p className="mt-1 text-sm font-black text-blue-600 dark:text-blue-300">
                      {sound.vietnameseHint}
                    </p>
                    {example ? (
                      <p className="mt-2 text-xs font-bold text-[var(--muted-foreground)]">
                        {example.word} {"->"} {example.hint}
                      </p>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </Card>
  );
}
