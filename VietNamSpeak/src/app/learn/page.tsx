import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { WORDS, getIpaWordGroups } from "@/data/words";

export default function LearnPage() {
  const ipaGroups = getIpaWordGroups();
  const totalGroupedWords = new Set(ipaGroups.flatMap((group) => group.words.map((word) => word.id))).size;

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <Badge>Kho từ theo nhóm IPA</Badge>
        <h1 className="text-4xl font-black tracking-tight">Học từ theo từng âm cần luyện</h1>
        <p className="max-w-2xl text-[var(--muted-foreground)]">
          Thay vì học từ rời rạc, kho từ được chia theo âm IPA. Mỗi nhóm tập trung vào một lỗi
          phát âm người Việt hay gặp: âm dài/ngắn, nguyên âm đôi, TH, SH, CH, J và âm ng cuối.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card className="space-y-2">
          <CardTitle>{WORDS.length} từ</CardTitle>
          <p className="text-sm text-[var(--muted-foreground)]">
            Có IPA, nghĩa, ví dụ, cách đọc kiểu Việt và lỗi cần tránh.
          </p>
        </Card>
        <Card className="space-y-2">
          <CardTitle>{ipaGroups.length} nhóm IPA</CardTitle>
          <p className="text-sm text-[var(--muted-foreground)]">
            Từ được gom theo âm mục tiêu để luyện có hệ thống.
          </p>
        </Card>
        <Card className="space-y-2">
          <CardTitle>{totalGroupedWords} từ có nhóm âm</CardTitle>
          <p className="text-sm text-[var(--muted-foreground)]">
            Một từ có thể xuất hiện ở nhiều nhóm nếu chứa nhiều âm cần luyện.
          </p>
        </Card>
      </section>

      <Card className="space-y-4 bg-blue-50 text-blue-950 dark:bg-blue-950 dark:text-blue-50">
        <CardTitle>Cách học khuyến nghị</CardTitle>
        <div className="grid gap-3 md:grid-cols-4">
          {[
            ["1", "Chọn 1 nhóm âm"],
            ["2", "Nghe từng từ 2 lần"],
            ["3", "Đọc gợi ý kiểu Việt"],
            ["4", "Ghi âm và sửa lỗi"]
          ].map(([step, label]) => (
            <div key={step} className="rounded-2xl bg-white/70 p-3 font-bold dark:bg-white/10">
              <span className="mr-2 rounded-full bg-blue-600 px-2 py-1 text-xs text-white">{step}</span>
              {label}
            </div>
          ))}
        </div>
      </Card>

      <div className="space-y-8">
        {ipaGroups.map((group) => (
          <section key={group.id} className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <Badge>
                  {group.symbol} {"->"} {group.vietnameseHint}
                </Badge>
                <h2 className="mt-2 text-3xl font-black tracking-tight">{group.title}</h2>
                <p className="mt-1 max-w-2xl text-sm text-[var(--muted-foreground)]">
                  {group.description}
                </p>
              </div>
              <span className="rounded-full bg-[var(--muted)] px-3 py-1 text-sm font-bold">
                {group.words.length} từ
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {group.words.map((word) => (
                <Card key={`${group.id}-${word.id}`} className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <Badge>{word.level}</Badge>
                    <span className="text-xs font-bold text-[var(--muted-foreground)]">
                      {word.topic}
                    </span>
                  </div>
                  <CardTitle>{word.word}</CardTitle>
                  <div className="rounded-2xl bg-blue-50 p-3 text-blue-950 dark:bg-blue-950 dark:text-blue-50">
                    <p className="text-xs font-bold opacity-70">Đọc kiểu Việt</p>
                    <p className="text-2xl font-black">{word.vnPronunciation}</p>
                  </div>
                  <p className="font-mono text-sm">{word.ipa}</p>
                  <p className="text-sm text-[var(--muted-foreground)]">{word.meaningVi}</p>
                  <p className="rounded-2xl bg-amber-50 p-3 text-xs font-bold text-amber-950 dark:bg-amber-950 dark:text-amber-50">
                    Tránh: {word.avoid}
                  </p>
                  <Button asChild className="w-full">
                    <Link href={`/learn/${word.id}`}>Học từ này</Link>
                  </Button>
                </Card>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
